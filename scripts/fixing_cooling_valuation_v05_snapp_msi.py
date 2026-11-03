# Libby Kula
# 3/24/2026
# Purpose: Fixing Urban InVEST urban cooling valuation results using cooling degree days method from Roxon et al., 2020
# Update: Updating for SNAPP

import logging
import numpy as np
import os
import pygeoprocessing as pygeo
import pandas as pd
import geopandas as gpd
import re 
import sys
import time
from osgeo import gdal
import shutil
import pygeoprocessing.kernels
from multiprocessing import Pool
import itertools
import collections
from scripts import buildings_api_v08
import tempfile


output_dir = '/projects/standard/jajohns/shared/Files/urban_cooling/workspace'
data_dir = '/projects/standard/jajohns/shared/Files/urban_cooling/base_data'

def run_month_year(args):
    urban_area, year, month = args
    print(f"Running {urban_area} for {year}-{month}")
    # Your actual model logic here
    # cooling_model.run(urban_area=urban_area, year=year, month=month)
    return f"Done {urban_area} {year}-{month}"

def compress_tifs(path):
    #Open the input raster
    input_raster_path = path
    output_raster_path = re.sub('.tif', '_compress.tif', path)

    # Open the dataset
    src_ds = gdal.Open(input_raster_path)

    # Define the output options, including compression
    creation_options = ["COMPRESS=LZW", "TILED=YES", "BIGTIFF=IF_SAFER"]

    # Use gdal.Translate to apply the compression
    gdal.Translate(output_raster_path, src_ds, creationOptions=creation_options)

    # Close the dataset
    src_ds = None
    
    os.remove(input_raster_path)

def smoothstep01(t):
    # clamp to [0,1], then smoothstep 3t^2 - 2t^3 (C¹ continuous)
    t = np.clip(t, 0.0, 1.0)
    return t*t*(3 - 2*t)

def monthly_temp_degC_to_cdd_smooth(temp_series, window=1.0):
    avg_temp_f = temp_series * 9/5 + 32
    thr = 70.0

    # Original formulas (unchanged)
    cdd_below = 1.07e-18 * avg_temp_f**10.96
    cdd_above = 29.58 * avg_temp_f - 1905.0

    # Base piecewise (use the *unrounded* temp for the branch)
    base = np.where(avg_temp_f >= thr, cdd_above, cdd_below)

    # Blend in [70 - window, 70 + window]
    t = (avg_temp_f - (thr - window)) / (2*window)  # maps [thr-window, thr+window] → [0,1]
    w = smoothstep01(t)  # 0 below band, 1 above band, smooth in between

    cdd_m = (1 - w) * cdd_below + w * cdd_above
    cdd_m = pd.Series(cdd_m, index=temp_series.index).clip(lower=0)

    return cdd_m * (5/9)


# Saving the coefficient as the cooling gradient m_c
mc = 0.010582177510612831 # ran code elsewhere to get this

### Fixing my energy savings valuation ### 
uhi_data = pd.read_csv(os.path.join(data_dir, 'uhi_2_20_2026.csv'))
build_heights = pd.read_csv(os.path.join(data_dir, 'Energy Consumption Table/Continental_building_height/OutputData_CombinedModel/us/Metros/metros_build_height.csv'))

months = ['06', '07', '08']
# years = ['2001', '2011', '2021']
years = ['2011']
# scenarios = ['all', 'public', 'private']
scenarios = ['all', 'public']

combos = list(itertools.product(years, months, scenarios))
year_month_combos = list(itertools.product(years, months))

def run(c):
    if c == 'Louisville-Jefferson County, KY-IN':
        c = 'Louisville/Jefferson County, KY-IN'
    
    c_orig = c
    c = re.sub(r'\/', '-', c)  # path-safe version

    filtered_df = build_heights[build_heights['metro'] == c_orig]
    avg_floors = filtered_df['avg_build_floors'].iloc[0]

    metro_consump = pd.read_csv(os.path.join(data_dir, f'Energy Consumption Table/Metro tables/{c}.csv'))
    building_cost = metro_consump['cost'].iloc[0]
    
    # saves buildings vector, do once per metro 
    buildings_api_v08.save_buildings_api(c)

    # Prepare argument list for multiprocessing
    partial_args_list = [
        (c, c_orig, avg_floors, building_cost, year, month)
        for year, month in year_month_combos
    ]

    building_path = os.path.join(data_dir, 'Buildings/buildings_' + c + '.gpkg')
    buildings_gdf = gpd.read_file(building_path)
    building_area_m2 = buildings_gdf.area

    n_procs = int(os.environ.get("SLURM_CPUS_PER_TASK", 6)) 

    for scen in scenarios:
        args_list = [
            (c, c_orig, avg_floors, building_cost, year, month, scen, buildings_gdf, building_area_m2)
            for (c, c_orig, avg_floors, building_cost, year, month) in partial_args_list
        ]
        with Pool(processes=n_procs) as pool:
            pool.map(process_combo, args_list)
    
    # for args in args_list:
    #     process_combo(args, buildings_gdf, building_area_m2)

    # Remove the buildings without results added to them to save space
    building_path = os.path.join(data_dir, 'Buildings/buildings_' + c + '.gpkg')
    os.remove(building_path)


# Ok, need to get this pulling the AOI's buildings from the API    

def process_combo(args):
    c, c_orig, avg_floors, building_cost, year, month, scen, buildings_gdf, building_area_m2 = args
    
    invest_dir = os.path.join(output_dir, '3_30_2026_' + scen + '_nature', c, year, month)
    # # if os.path.exists(out_csv):
    # #     return
    # tract_csv = os.path.join(inputdir, f'InVEST Results/cooling workspace/8_14_2025_tract_savings/{c}_{year}_{month}_tract_energy_savings.csv')
    # if os.path.exists(tract_csv):
    #     return

    print(year, month, scen)

    # Cooling valuation
    t_air_mixed_path = os.path.join(invest_dir, 'intermediate', 'T_air_' + c + '_' + year + '_' + month + '.tif')

    uhi_max = uhi_data[(uhi_data['metro'] == c_orig) & (uhi_data['month'] == int(month))]['uhi'].iloc[0]
    air_ref_temp = uhi_data[(uhi_data['metro'] == c_orig) & (uhi_data['month'] == int(month))]['t_ref'].iloc[0]
    
    building_path = os.path.join(data_dir, 'Buildings/buildings_' + c + '.gpkg')

    print('running zonal statistics', )
    print(time.ctime()) 

    chunk_size = 10000
    results = []

    all_stats = []

    for i in range(0, len(buildings_gdf), chunk_size):
        chunk = buildings_gdf.iloc[i:i+chunk_size]
        tmp_gpkg_path = os.path.join(invest_dir, "tmp.gpkg")
        chunk.to_file(tmp_gpkg_path)

        stats = pygeo.zonal_statistics(
            base_raster_path_band=(t_air_mixed_path, 1),
            aggregate_vector_path= tmp_gpkg_path,  # OR proper temp file
            ignore_nodata=True
        )

        all_stats.extend(stats.values())
        os.remove(tmp_gpkg_path)

    # NOW use all_stats (not stats)
    buildings_gdf['build_t_air'] = [
        s['sum'] / s['count'] if s and s.get('count', 0) > 0 else 0
        for s in all_stats
    ]

    # Get air_ref_temp and uhi_max from uhi file 
    build_temp_wo_nat = pd.Series(air_ref_temp + uhi_max, index=range(len(buildings_gdf))) # this is just going to be a number, 
    build_temp_w_nat = buildings_gdf['build_t_air']
    deg_cooling = build_temp_wo_nat-build_temp_w_nat

    build_consump_saved = (
        monthly_temp_degC_to_cdd_smooth(build_temp_wo_nat) -
        monthly_temp_degC_to_cdd_smooth(build_temp_w_nat) 
    ) * mc

    # print('monthly_temp_degC_to_cdd_smooth(build_temp_wo_nat)', monthly_temp_degC_to_cdd_smooth(build_temp_wo_nat))
    # print('monthly_temp_degC_to_cdd_smooth(build_temp_w_nat)', monthly_temp_degC_to_cdd_smooth(build_temp_w_nat))


    buildings_gdf['kwh_saved'] = build_consump_saved * building_area_m2 * avg_floors
    buildings_gdf['dollars_saved'] =  buildings_gdf['kwh_saved'] * building_cost

    results_dict = {
        'metro': c,
        'year': year,
        'month': month,
        'kwh_saved_sum': buildings_gdf['kwh_saved'].sum(),
        'dollars_saved_sum': buildings_gdf['dollars_saved'].sum(),
        'avg_deg_cooling': deg_cooling.mean()
    }

    os.makedirs(os.path.join(output_dir, '0_valuation'), exist_ok=True)
    out_csv = os.path.join(output_dir, f'0_valuation/{scen}_{c}_{year}_{month}_{scen}.csv')
    pd.DataFrame.from_dict(results_dict, orient='index').to_csv(out_csv)

    os.makedirs(os.path.join(output_dir, '0_buildings'), exist_ok=True)
    buildings_gdf.to_parquet(os.path.join(output_dir, '0_buildings', c + '_' + year + '_' + month + '_' + scen + '_buildings.parquet'), compression="zstd")

    del build_consump_saved
    del deg_cooling


 
