# Libby Kula
# 4/4/2025
# Purpose: Fixing Urban InVEST urban cooling valuation results using cooling degree days method from Roxon et al., 2020
# Update: Using NatCapTEEMS base data

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

# inputdir = 'G:/Shared drives/NatCapTEEMs/Files/base_data/submissions'
inputdir = '/users/3/kula0049/urban-cooling/inputs'

results_path = os.path.join(inputdir, 'InVEST Results/cooling workspace/3_16_2024_fixed_multistate/')
multistate_metro_list = [
    foldername
    for foldername in os.listdir(results_path) 
]
multistate_metro_list = multistate_metro_list + ['Louisville/Jefferson County, KY-IN']

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

uhi_data = pd.read_csv(os.path.join(inputdir, 'Results/uhi_4_29_2024_v03.csv'))
# uhi_data = pd.read_csv(os.path.join(inputdir, 'Results/uhi_buffered_7_01_2024.csv'))
consump_fixed_table = pd.read_csv(os.path.join(inputdir, 'Results/Metros/consumption_fixed.csv'))
build_heights = pd.read_csv(os.path.join(inputdir, 'Energy Consumption Table/Continental_building_height/OutputData_CombinedModel/us/Metros/metros_build_height.csv'))

months = ['06', '07', '08']
years = ['2001', '2011', '2021']

combos = list(itertools.product(years, months))

def run(c):
    if c == 'Louisville-Jefferson County, KY-IN':
        c = 'Louisville/Jefferson County, KY-IN'
    c_orig = c
    c = re.sub(r'\/', '-', c)  # path-safe version

    prev_energy_table = pd.read_csv(os.path.join(inputdir, f'Energy Consumption Table/Metro tables/{c}.csv'))
    prev_consump = prev_energy_table['consumption'].iloc[0]

    filtered_df = build_heights[build_heights['metro'] == c_orig]
    avg_floors = filtered_df['avg_build_floors'].iloc[0]

    metro_consump = pd.read_csv(os.path.join(inputdir, f'Energy Consumption Table/Metro tables/{c}.csv'))
    building_cost = metro_consump['cost'].iloc[0]

    # Prepare argument list for multiprocessing
    args_list = [
        (c, c_orig, avg_floors, building_cost, prev_consump, year, month)
        for year, month in combos
    ]

    # for args in args_list:
    #     process_combo(args)
    n_procs = int(os.environ.get("SLURM_CPUS_PER_TASK", 9))
    with Pool(processes=n_procs) as pool:
        pool.map(process_combo, args_list)

    # Clean up after all combos finish
    if c_orig in multistate_metro_list:
        base_subdir = 'InVEST Results/cooling workspace/3_16_2024_fixed_multistate'
    else:
        base_subdir = 'InVEST Results/cooling workspace/11_21_2023_metros'
    # shutil.rmtree(os.path.join(inputdir, base_subdir, c))

    

def process_combo(args):
    c, c_orig, avg_floors, building_cost, prev_consump, year, month = args
    out_csv = os.path.join(inputdir, f'InVEST Results/cooling workspace/8_14_2025/{c}_{year}_{month}.csv')
    # if os.path.exists(out_csv):
    #     return
    tract_csv = os.path.join(inputdir, f'InVEST Results/cooling workspace/8_14_2025_tract_savings/{c}_{year}_{month}_tract_energy_savings.csv')
    if os.path.exists(tract_csv):
        return

    print(year, month)
    # Set base path
    if c_orig in multistate_metro_list:
        base_subdir = 'InVEST Results/cooling workspace/3_16_2024_fixed_multistate'
    else:
        base_subdir = 'InVEST Results/cooling workspace/11_21_2023_metros'
    base_path = os.path.join(inputdir, base_subdir, c)
    
    hm_path = os.path.join(base_path, f'hm_{c}_{year}_{month}_al_compress.tif')

    if os.path.exists(hm_path) == 0:
        hm_path = os.path.join(base_path, f'hm_{c}_{year}_{month}.tif')
    # elif os.path.exists(os.path.join(base_path, f'hm_{c}_{year}_{month}_{c}_wgs84.tif')):
    #     hm_path = os.path.join(base_path, f'hm_{c}_{year}_{month}_{c}_wgs84.tif')
    else:
        uncompressed = os.path.join(base_path, f'hm_{c}_{year}_{month}.tif')
        # if os.path.exists(uncompressed):
        #     os.remove(uncompressed)

    def find_building_path_or_csv(base_path, c, year, month, fallback_tried=False):
        # Try shapefiles and geopackages
        building_filenames = [ 
            f'buildings_with_stats_{c}_{year}_{month}_Aug30.shp',
            f'buildings_with_stats_{c}_{year}_{month}_fixed.shp',
            f'buildings_with_stats_{c}_{year}_{month}_Aug30.gpkg',
            f'buildings_with_stats_{c}_{year}_{month}_Sept10.gpkg',
            f'buildings_with_stats_{c}_{year}_{month}.shp',
            f'buildings_with_stats_{c}_{year}_{month}.gpkg'
        ]

        for fname in building_filenames:
            candidate = os.path.join(base_path, fname)
            if os.path.exists(candidate):
                return {'building_path': candidate, 'build_temp_df': None}

        # Try CSV
        csv_path = f'Results/Metros/building_avg_temps/build_temp_w_nat_{c}_{month}.csv'
        if os.path.exists(csv_path):
            build_temp_df = pd.read_csv(csv_path)
            return {'building_path': None, 'build_temp_df': build_temp_df}

        # If not already tried fallback to year "2021", try that now
        if not fallback_tried and year != "2021":
            return find_building_path_or_csv(base_path, c, '2021', month, fallback_tried=True)

        # Nothing found
        return {'building_path': None, 'build_temp_df': None}

    # Example usage:
    result = find_building_path_or_csv(base_path, c, year, month)

    if result['building_path']:
        building_path = result['building_path']
        print(building_path)
        # use building_path
    elif result['build_temp_df'] is not None:
        build_temp_df = result['build_temp_df']
        # use DataFrame
    else:
        print(f"No building data found for {c}, {year}, {month}, or fallback year 2021.")
    # print(f"No building file found for {c}, {year}-{month}")
    # return

    # Delete unneeded files
    for f in os.listdir(base_path):
        if 'uhi_results' in f:
            try:
                os.remove(os.path.join(base_path, f))
            except:
                pass

    # Air mixing raster
    hm_mixed_path = os.path.join(inputdir, f'mixed/hm_{c}_{year}_{month}_mixed_compress.tif')
    if not os.path.exists(hm_mixed_path):
        tempdir = os.path.join(inputdir, 'temp/')
        os.makedirs(tempdir, exist_ok=True)

        kernel_path = os.path.join(tempdir, f"exponential_kernel_{year}_{month}_{c}.tif")

        mixed_out = os.path.join(inputdir, f'mixed/hm_{c}_{year}_{month}_mixed.tif')
        
        pygeo.kernels.exponential_decay_kernel(
                target_kernel_path=kernel_path,
                max_distance=20,
                expected_distance=20)

        pygeo.convolve_2d(
            (hm_path, 1), (kernel_path, 1),
            mixed_out, working_dir=tempdir,
            ignore_nodata_and_edges=True
        )
        compress_tifs(mixed_out)
        # os.remove(hm_path)
        os.remove(kernel_path)

    # Cooling valuation
    buildings_gdf = gpd.read_file(building_path).to_crs('EPSG:5070')
    buildings_gdf = buildings_gdf[buildings_gdf.geom_type.isin(["Polygon", "MultiPolygon"]) & (~buildings_gdf.is_empty)]
    # buildings_gdf = buildings_gdf.buffer(0)
    # print(buildings_gdf.columns)  # before .to_file
    buildings_gdf.to_file(building_path)
    # gdf2 = gpd.read_file(building_path)
    # print(gdf2.columns)  # after reload

    building_area_m2 = buildings_gdf.area
    
    uhi_max = uhi_data[(uhi_data['metro'] == c_orig) & (uhi_data['month'] == int(month))]['uhi'].iloc[0]
    # print(uhi_max)

    stats = pygeo.zonal_statistics(
        base_raster_path_band=(hm_mixed_path, 1),
        aggregate_vector_path=building_path,
        ignore_nodata=True
    )
    # os.remove(building_path)
    # os.remove(hm_mixed_path)
    # print(stats)
    # print(type(stats))
    # print(len(stats))
    # print(collections.Counter(type(s) for s in stats))
    # print(stats[:10])  # first 10 entries
    buildings_gdf['avg_cc'] = [
        stat['sum'] / stat['count'] if stat and stat.get('count', 0) > 0 else 0
        for stat in stats.values()
    ]


    # # Assign average cooling contribution back to the same GeoDataFrame
    # buildings_gdf['avg_cc'] = [
    #     stat['sum'] / stat['count'] if isinstance(stat, dict) and stat.get('count', 0) > 0 else 0
    #     for stat in stats
    # ]
    
    if os.path.exists(building_path):
        build_temp_w_nat = buildings_gdf['mean_t_air']
    else:
        build_temp_w_nat = build_temp_df['build_temp_w_nat']
    # print(build_temp_w_nat)
    build_deg_cooling = uhi_max * buildings_gdf['avg_cc']
    build_temp_wo_nat = build_temp_w_nat + build_deg_cooling
    # print('build_temp_wo_nat', build_temp_wo_nat)
    # print('build_temp_w_nat', build_temp_w_nat)

    build_consump_saved = (
        monthly_temp_degC_to_cdd_smooth(build_temp_wo_nat) -
        monthly_temp_degC_to_cdd_smooth(build_temp_w_nat)
    ) * mc
    
    print('monthly_temp_degC_to_cdd_smooth(build_temp_wo_nat)', monthly_temp_degC_to_cdd_smooth(build_temp_wo_nat))
    print('monthly_temp_degC_to_cdd_smooth(build_temp_w_nat)', monthly_temp_degC_to_cdd_smooth(build_temp_w_nat))


    buildings_gdf['kwh_saved'] = build_consump_saved * building_area_m2 * avg_floors
    buildings_gdf['dollars_saved'] =  buildings_gdf['kwh_saved'] * building_cost

    results_dict = {
        'metro': c,
        'year': year,
        'month': month,
        'kwh_saved_sum': buildings_gdf['kwh_saved'].sum(),
        'dollars_saved_sum': buildings_gdf['dollars_saved'].sum(),
        'avg_deg_cooling': build_deg_cooling.mean()
    }

    pd.DataFrame.from_dict(results_dict, orient='index').to_csv(out_csv)

    buildings_gdf = buildings_gdf.drop(columns=['sav_upd', 'energy_sav'])
    buildings_gdf.to_file(os.path.join(inputdir, 'InVEST Results/cooling workspace/8_14_2025_building_savings/' + c + '_' + year + '_' + month + '_buildings.gpkg'), driver='GPKG')