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
import statsmodels.api as sm
import statsmodels.formula.api as smf

import rasterio
import rioxarray as rxr

# inputdir = 'G:/Shared drives/NatCapTEEMs/Files/base_data/submissions'
inputdir = '/users/3/kula0049/urban-cooling/'
vector_gdf = gpd.read_file(os.path.join(inputdir, 'Data/urbanspatial-guppd-v1-gpkg/urbanspatial-guppd-v1-gpkg.gpkg'),
                           layer='urbanspatial_guppd_v1_polygons')
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
    return t * t * (3 - 2 * t)


def temp_degC_to_cdd_smooth(temp_degC, window=1.0):
    """
    Smoothed cooling degree days (CDD) from temperature in °C.

    Behavior:
      - Below 60°F: CDD = 0
      - 60–70°F: uses cdd_below equation
      - Around/above 70°F: smoothly blends to cdd_above across thr ± window
    """
    avg_temp_f = temp_degC * 9/5 + 32
    thr = 70.0
    floor_f = 60.0

    # Piecewise formulas
    cdd_below = 1.07e-18 * avg_temp_f**10.96
    cdd_above = 29.58 * avg_temp_f - 1905.0

    # Smooth transition across threshold ± window
    t = (avg_temp_f - (thr - window)) / (2 * window)
    w = smoothstep01(t)

    # Smooth blend around 70F
    cdd_m = (1 - w) * cdd_below + w * cdd_above

    # Force CDD = 0 below 60F (works with numpy, xarray, dask-backed DataArray)
    if hasattr(cdd_m, "where"):   # xarray DataArray
        cdd_m = cdd_m.where(avg_temp_f >= floor_f, 0.0)
    else:                         # numpy/scalars
        cdd_m = np.where(avg_temp_f >= floor_f, cdd_m, 0.0)

    # Clamp to non-negative and convert to °C-equivalent scale
    return np.maximum(cdd_m, 0) * (5/9)

# print(temp_degC_to_cdd_smooth(11.63))

def calc_monthly_temps_countries(month):
    year = '2019'
    tmean_path = os.path.join(inputdir, 'Data/Tmean_stitched/tmean_stitched_' + year + '_' + month + '_compress.tif')
    tmean_fixed = os.path.join(inputdir, 'Data/Tmean_stitched/tmean_stitched_' + year + '_' + month + '_compress_fixed.tif')
    with rasterio.open(tmean_path) as src:
        data = src.read(1).astype(float)
        profile = src.profile.copy()

        # Mask pixels that are effectively -273.15 (with a tiny tolerance)
        data[np.isclose(data, -273.15, atol=1e-3)] = np.nan

        # Also mask original nodata values if needed
        if src.nodata is not None:
            data[np.isclose(data, src.nodata, atol=1e-6)] = np.nan

        # Update profile to mark nodata as NaN (or a numeric nodata value if preferred)
        profile.update(nodata=np.nan)

        # Save the cleaned raster
        with rasterio.open(tmean_fixed, 'w', **profile) as dst:
            dst.write(data, 1)

    countries_vector_path = os.path.join(inputdir, 'Data/cartographic/ee/ee_r250_correspondence.gpkg')
    countries_gdf = gpd.read_file(countries_vector_path)
    print(month)
    
    temp_stats = pygeo.zonal_statistics(
        base_raster_path_band=(tmean_fixed, 1),
        aggregate_vector_path=countries_vector_path,
        ignore_nodata=True
    )

    # need to save the average temps somehow 
    countries_gdf['avg_temp'] = [ # in degC 
        stat['sum'] / stat['count'] if stat and stat.get('count', 0) > 0 else 0
        for stat in temp_stats.values()
    ]

    countries_df = countries_gdf[['iso3_r250_name', 'iso3_r250_label', 'avg_temp']] 
    countries_df.to_csv(os.path.join(inputdir, 'Data/avg_temp_by_iso3_r250_' + year + '_' + month + '_wcode.csv'))

def clip_to_urban(ras, c):
    c = str(c)
    # if os.path.exists(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras)) == 0:
    raster_dataset = gdal.Open(ras)
    gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras), 
        raster_dataset, cutlineDSName=os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg'), cropToCutline=True)

def calculate_consumption_per_cdd_from_iea():
    print('hi')
    # --- Load IEA–CMCC CDD dataset ---
    cdd_path = os.path.join(
        inputdir,
        "Data/IEA CMCC/IEA-CMCC-WeatherForEnergy-CDDhum18dailybypop-from-2019-01-to-2019-12.csv"
    )
    cdd_df = pd.read_csv(cdd_path)

    # Standardize column names
    cdd_df = cdd_df.rename(columns={
        "Country": "iso3_r250_label", # why did I do it on name? Isn't the abbreviation more consistent?
        "CDDhum18dailybypop": "cdd_m"
    })

    # Convert monthly CDDs to numeric
    cdd_df["cdd_m"] = pd.to_numeric(cdd_df["cdd_m"], errors="coerce")

    # --- Aggregate to annual CDD by country ---
    annual_cdd = (
        cdd_df.groupby("iso3_r250_label", as_index=False)["cdd_m"]
        .sum()
        .rename(columns={"cdd_m": "cdd"})
    )

    # --- Load per-capita cooling energy data ---
    energy_df = pd.read_csv(
        os.path.join(inputdir, "Data/per-capita-energy-use/primary_energy_percap_cooling_share_2019_CORRECTED.csv")
    )
    energy_df = energy_df[["iso3", "entity", "cooling_percap_2019_estimated_potential", "region_wb"]]

    # --- Standardize country names ---
    annual_cdd["iso3_r250_label"] = annual_cdd["iso3_r250_label"].astype(str).str.strip().str.upper()
    energy_df["iso3_r250_label"] = energy_df["iso3"].astype(str).str.strip().str.upper()

    # --- Merge on country code ---
    merged = pd.merge(annual_cdd, energy_df, how="inner", on="iso3_r250_label")
    print("Merged shape:", merged.shape)

    # --- Compute consumption per CDD ---
    merged["consumption_per_cdd"] = merged["cooling_percap_2019_estimated_potential"] / merged["cdd"]
    merged.loc[merged["cdd"] <= 0, "consumption_per_cdd"] = pd.NA

    # --- Save to CSV ---
    out_csv = os.path.join(inputdir, "Data/consumption_per_cdd_by_country_iea_v03.csv")
    merged.to_csv(out_csv, index=False)
    print(f"Saved: {out_csv}")

calculate_consumption_per_cdd_from_iea()

def scaling_down_results():
    # Scaling down the GEP results using the fixed per capita residential cooling usage by country that Nfamara sent 07/2026
    new_consump = pd.read_csv(os.path.join(inputdir, "Data/consumption_per_cdd_by_country_iea_v03.csv"))
    old_consump = pd.read_csv(os.path.join(inputdir, "Data/consumption_per_cdd_by_country_iea_v02.csv"))

    new_consump = new_consump.sort_values('iso3_r250_label')
    old_consump = old_consump.sort_values('iso3_r250_label')

    new_consump['scaling_factor'] = new_consump['consumption_per_cdd']/old_consump['consumption_per_cdd']

    old_results = pd.read_csv(os.path.join(inputdir, f'output/local_climate_regulation_gep_12_19_25.csv'))

    merged = pd.merge(old_results, new_consump, how='left', on='iso3_r250_label')
    
    merged['old_local_climate_regulation'] = (
        merged[' local_climate_regulation ']
        .astype(str)
        .str.strip()
        .str.replace(r'[\$,]', '', regex=True)      # strip currency formatting
        .str.replace(r'^[-–—]+$', '', regex=True)   # any-length dash placeholder -> empty
        .replace({'': None, 'nan': None, 'N/A': None, 'n/a': None, 'NA': None})
        .pipe(pd.to_numeric, errors='coerce')        # anything still bad -> NaN
    )
    
    merged['fixed_local_climate_regulation'] = merged['old_local_climate_regulation']*merged['scaling_factor']

    merged.to_csv(os.path.join(inputdir, f'output/local_climate_regulation_gep_7_13_2026.csv'))


scaling_down_results()


months = [f'{i:02}' for i in range(1, 13)]
years = ['2019']

combos = list(itertools.product(years, months))

def run(c):

    # Prepare argument list for multiprocessing
    args_list = [
        (c, year, month)
        for year, month in combos
    ]

    # for args in args_list:
    #     process_combo(args)
    n_procs = int(os.environ.get("SLURM_CPUS_PER_TASK", 9))
    with Pool(processes=n_procs) as pool:
        pool.map(get_cdd_diff, args_list)


def get_cdd_diff(args):
    c, year, month = args
    out_csv = os.path.join(inputdir, f'valuation_6_30_2026/{c}_{year}_{month}.csv')
    if os.path.exists(out_csv):
        return

    print(year, month)

    tmean_fixed = os.path.join(inputdir, 'Data/Tmean_stitched/tmean_stitched_' + year + '_' + month + '_compress_fixed.tif')
    clip_to_urban(tmean_fixed, c)
    clipped_temps = re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), tmean_fixed)
    clipped_temps_da = rxr.open_rasterio(clipped_temps, masked=True)

    # multiplying by pop per pixel 
    pop_ras = os.path.join(inputdir, 'Data/population/global_pop_2019_CN_1km_R2025A_UA_v1.tif')
    clip_to_urban(pop_ras, c)
    clipped_pops = re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), pop_ras)
    clipped_pops_da = rxr.open_rasterio(clipped_pops, masked=True)

    # After loading clipped rasters:
    clipped_temps_da = clipped_temps_da.squeeze()
    clipped_pops_da = clipped_pops_da.squeeze()

    # Make temps match population grid (or the other way around)
    clipped_temps_da = clipped_temps_da.rio.reproject_match(clipped_pops_da)
    
    max_temp = float(clipped_temps_da.max().compute())
    print(max_temp)
    cdd_diff = temp_degC_to_cdd_smooth(max_temp) - temp_degC_to_cdd_smooth(clipped_temps_da)
    print(cdd_diff.mean())
    cdd_pop_diff = cdd_diff * clipped_pops_da

    # output path
    out_tif = re.sub(r'\.(.*?)$', r'_cdd_pop_diff_{}.\1'.format(c), clipped_temps)

    # write to disk
    cdd_pop_diff.rio.to_raster(
        out_tif,
        compress="lzw",
        dtype="float32"
    )

    # return cdd_pop_diff
    total_cdd_pop_diff = float(cdd_pop_diff.sum().compute())
    return total_cdd_pop_diff

# print(get_cdd_diff(['22_9653', '2019', '07']))

def run_valuation_c(c):
    results = []  # store results from each loop

    # Read the urban shapefile once per city
    urban_vector_path = os.path.join(inputdir, f'Data/Polygon_vectors/urbans/{c}.gpkg')
    if os.path.exists(urban_vector_path):
        urban_gdf = gpd.read_file(urban_vector_path)
    else:
        urban_gdf = vector_gdf[
        (vector_gdf['SMOD_ID'] == c) &
        (vector_gdf.geometry.type.isin(['Polygon', 'MultiPolygon']))
        ]
        urban_gdf.to_file(urban_vector_path, driver="GPKG")
    country_abbr = urban_gdf['ISO'].iloc[0]
    # population = urban_gdf['GHSPOP_R23_2015'].iloc[0]

    # Lookup country → iso3_r250_id
    iso3_r250_country_data = gpd.read_file(os.path.join(inputdir, 'Data/cartographic/ee/ee_r250_correspondence.gpkg'))
    iso3_r250_id = iso3_r250_country_data.loc[
        iso3_r250_country_data['iso3_r250_label'] == country_abbr, 'iso3_r250_id'
    ].iloc[0]

    iso3_r250_name = iso3_r250_country_data.loc[
        iso3_r250_country_data['iso3_r250_label'] == country_abbr, 'iso3_r250_name'
    ].iloc[0]

    # Read electricity price data once
    price_data = pd.read_excel(os.path.join(inputdir, 'Data/electricity-price/WB_electricity_price_data.xlsx'), sheet_name='WB_price_data')

    # Energy consumption per CDD by country
    consump_data = pd.read_csv(os.path.join(inputdir, 'Data/consumption_per_cdd_by_country_iea_v02.csv'))

    mc = consump_data.loc[
        consump_data['entity'] == iso3_r250_name, 'consumption_per_cdd'
    ].iloc[0]

    for year in ['2019']:
        for month in [f'{i:02}' for i in range(1, 13)]:
            # try:
            price_cents = price_data.loc[
                (price_data['Economy ISO3'] == country_abbr) & 
                (price_data['Year'] == int(year)),
                'Price (Nominal USD cents per kWh)'
            ].iloc[0]
            price = price_cents / 100

            cdd_pop_diff = get_cdd_diff([c, year, month])
            kwh_diff = cdd_pop_diff * mc
            total_savings = kwh_diff * price
            
            # append results as dict
            results.append({
                'city': c,
                'country_iso': country_abbr,
                'iso3_r250_id': iso3_r250_id,
                'year': year,
                'month': month,
                # 'cdd_diff': cdd_diff, ### grrrrr why didn't I keep this???
                'kwh_diff': kwh_diff,
                'price_usd_per_kwh': price,
                'total_savings_usd': total_savings
            })

            # except Exception as e:
            #     print(f"Error processing {c} {year}-{month}: {e}")
            #     continue

    # Convert results to DataFrame and save to CSV
    output_csv = os.path.join(inputdir, f'output/valuation_6_30_2026/{c}_{year}.csv')
    
    if results:
        df = pd.DataFrame(results)
        df.to_csv(output_csv, index=False)
        print(f"Saved results for {c} to {output_csv}")
    else:
        print(f"No results for {c}")
        
# run_valuation_c('22_15572')