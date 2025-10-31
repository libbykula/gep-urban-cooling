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
import rasterio
import rioxarray as rxr

# inputdir = 'G:/Shared drives/NatCapTEEMs/Files/base_data/submissions'
inputdir = '/users/3/kula0049/urban-cooling/'

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

def temp_degC_to_cdd_smooth(temp_degC, window=1.0):
    """
    Compute smoothed cooling degree days (CDD) for a single temperature (°C).
    """
    avg_temp_f = temp_degC * 9/5 + 32
    thr = 70.0

    # Original piecewise formulas
    cdd_below = 1.07e-18 * avg_temp_f**10.96
    cdd_above = 29.58 * avg_temp_f - 1905.0

    # Smooth transition across threshold ± window
    t = (avg_temp_f - (thr - window)) / (2 * window)
    w = smoothstep01(t)

    # Smooth blend
    cdd_m = (1 - w) * cdd_below + w * cdd_above

    # Clip to non-negative and convert back to °C-equivalent scale
    return max(cdd_m, 0) * (5/9)

# Saving the coefficient as the cooling gradient m_c
# ISO3_r250_name 

# def calc_monthly_temps_countries(yearlist, monthlist):
    # for year in yearlist:
    #     for month in monthlist:
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

# calc_monthly_temps_countries(['2019'],
#                              [f'{i:02}' for i in range(1, 13)])
# months = [f'{i:02}' for i in range(1, 13)]
# n_procs = int(os.environ.get("SLURM_CPUS_PER_TASK", 12))
# with Pool(processes=n_procs) as pool:
#     pool.map(calc_monthly_temps_countries, months)


def calculate_mc():
    all_months = []

    for year in ['2019']:
        for month in [f'{i:02}' for i in range(1, 13)]:
            # csv_path = os.path.join(inputdir, f'Data/avg_temp_by_iso3_r250_{year}_{month}_wcode.csv')

            csv_path = os.path.join(inputdir, f'Data/avg_temp_by_iso3_r250_{year}_{month}.csv')
            df = pd.read_csv(csv_path)

            # compute CDD for that month
            df['cdd_m'] = monthly_temp_degC_to_cdd_smooth(df['avg_temp'])
            df['year'] = year
            df['month'] = month
            all_months.append(df[['iso3_r250_name', 'cdd_m', 'year', 'month']])
    
    # Combine all months
    all_data = pd.concat(all_months, ignore_index=True)

    # Aggregate to annual CDD by country (iso3)
    annual_data = (
        all_data.groupby('iso3_r250_name', as_index=False)['cdd_m']
        .sum()
        .rename(columns={'cdd_m': 'cdd'})
    )
    
    # energy_df = pd.read_csv(os.path.join(inputdir, 'Data/per-capita-energy-use/per-capita-energy-use.csv'))
    # energy_df = pd.read_csv(os.path.join(inputdir, 'Data/electricity-air-conditioning/merged_country_GEP_IEA_kWh_pop_percap_oct_17_imputed.csv'),
    #                         encoding='latin1')
    # energy_df = energy_df[energy_df['Year'] == 2019]
    energy_df = energy_df[['iso3_r250_name', '2019_percap_kwh']]

    # energy_cdd_df = pd.merge(annual_data, energy_df,
    #                         how='inner', left_on='iso3_r250_name', right_on='Entity') # grrrr.... merge by iso code or name?
    annual_data['iso3_r250_name'] = (
        annual_data['iso3_r250_name']
        .astype(str)
        .str.strip()
        .str.upper()
    )

    energy_df['iso3_r250_name'] = (
        energy_df['iso3_r250_name']
        .astype(str)
        .str.strip()
        .str.upper()
    )
    energy_cdd_df = pd.merge(annual_data, energy_df,
                        how='inner', on='iso3_r250_name') 
    print("Merged shape:", energy_cdd_df.shape)
    print(energy_cdd_df.head())
    print(energy_cdd_df.dtypes)

    # Performing the regression and fitting the model
    # result = sm.OLS(energy_cdd_df['2019_percap_kwh'], energy_cdd_df['cdd']).fit()

    # Saving the coefficient as the cooling gradient m_c
    # mc = result.params[0]
    # print(result.summary())
    # print(mc)
    X = sm.add_constant(energy_cdd_df['cdd'])
    y = energy_cdd_df['2019_percap_kwh']

    result = sm.OLS(y, X, missing='drop').fit()
    print(result.summary())

    # Coefficient (slope)
    mc = result.params['cdd']
    print("m_c:", mc)


calculate_mc() 
# mc = 1.7173746591646857 

# ### Fixing my energy savings valuation ### 

# months = [f'{i:02}' for i in range(1, 13)]
# years = ['2019']

# combos = list(itertools.product(years, months))

# def run(c):

#     # Prepare argument list for multiprocessing
#     args_list = [
#         (c, year, month)
#         for year, month in combos
#     ]

#     # for args in args_list:
#     #     process_combo(args)
#     n_procs = int(os.environ.get("SLURM_CPUS_PER_TASK", 9))
#     with Pool(processes=n_procs) as pool:
#         pool.map(process_combo, args_list)

def process_combo(args):
    c, year, month = args
    out_csv = os.path.join(inputdir, f'valuation/{c}_{year}_{month}.csv')
    if os.path.exists(out_csv):
        return

    print(year, month)

    base_dir = os.path.join(inputdir, 'output/invest_results/', c)

    # Delete unneeded files
    # for f in os.listdir(base_dir):
    #     if 'uhi_results' in f:
    #         try:
    #             os.remove(os.path.join(base_dir, f))
    #         except:
    #             pass

    # Air mixing raster
    hm_mixed_path = os.path.join(inputdir, f'output/mixed_output/hm_{c}_{year}_{month}_mixed_compress.tif')
    hm_raster = rxr.open_rasterio(hm_mixed_path, masked=True)
    avg_hm_mixed = hm_raster.mean().item()     # Averaging by urban area

    # Temperature with nature (observed) 
    vector_results = gpd.read_file(os.path.join(inputdir, 'output/invest_results/' + c + '/uhi_results_' + c + '_' + year + '_' + month + '.shp'))
    temp_w_nat = vector_results['avg_tmp_v'].iloc[0] # not positive if this is right
    # print(temp_w_nat)
    # Cooling valuation 
    uhi_df = pd.read_csv(os.path.join(inputdir, 'Data/uhi/uhi_global_gep_' + c + '.csv'))
    uhi_max = uhi_df['t_ref'][(uhi_df['year'] == int(year)) & (uhi_df['month'] == int(month))].iloc[0]
    avg_deg_cooling = uhi_max * avg_hm_mixed
    temp_wo_nat = temp_w_nat + avg_deg_cooling
    # print(temp_wo_nat)

    # consump_saved_percap = (
    #     temp_degC_to_cdd_smooth(temp_wo_nat) -
    #     temp_degC_to_cdd_smooth(temp_w_nat)
    # ) * mc * 0.05 # argentina approx 5% spent toward cooling
    
    # print('monthly_temp_degC_to_cdd_smooth(build_temp_wo_nat)', temp_degC_to_cdd_smooth(temp_wo_nat))
    # print('monthly_temp_degC_to_cdd_smooth(build_temp_w_nat)', temp_degC_to_cdd_smooth(temp_w_nat))

    cdd_diff = temp_degC_to_cdd_smooth(temp_wo_nat) - temp_degC_to_cdd_smooth(temp_w_nat)
    # print('cdd diff', cdd_diff)
    return cdd_diff
    # results_dict = {
    #     'metro': c,
    #     'year': year,
    #     'month': month,
    #     'kwh_saved_percap': consump_saved_percap,
    #     'dollars_saved': dollars_saved,
    #     'avg_deg_cooling': avg_deg_cooling
    # }

    # pd.DataFrame.from_dict(results_dict, orient='index').to_csv(out_csv)

# # process_combo(args=['30_168', '2019', '01'])

# # for c in ['30_168']:
# def run_valuation_c(c):
#     results = []  # store results from each loop

#     # Read the urban shapefile once per city
#     urban_gdf = gpd.read_file(os.path.join(inputdir, f'Data/Polygon_vectors/urbans/{c}.gpkg'))
#     country_abbr = urban_gdf['ISO'].iloc[0]

#     population = urban_gdf['GHSPOP_R23_2015'].iloc[0]

#     # Lookup country → ee_r264_id
#     ee_r264_country_ids = pd.read_csv(os.path.join(inputdir, 'Data/cartographic/ee/ee_r264_correspondence.csv'))
#     ee_r264_id = ee_r264_country_ids.loc[
#         ee_r264_country_ids['ee_r264_label'] == country_abbr, 'ee_r264_id'
#     ].iloc[0]

#     # Read electricity price data once
#     price_data = pd.read_excel(os.path.join(inputdir, 'Data/electricity-price/WB_electricity_price_data.xlsx'), sheet_name='WB_price_data')

#     for year in ['2019']:
#         for month in [f'{i:02}' for i in range(1, 13)]:
#             try:
#                 price_cents = price_data.loc[
#                     (price_data['Economy ISO3'] == country_abbr) & 
#                     (price_data['Year'] == int(year)),
#                     'Price (Nominal USD cents per kWh)'
#                 ].iloc[0]
#                 price = price_cents / 100

#                 cdd_diff = process_combo([c, year, month])
#                 kwh_diff = cdd_diff * mc
#                 savings_percap = kwh_diff * price
                
#                 total_savings = savings_percap*population

#                 # append results as dict
#                 results.append({
#                     'city': c,
#                     'country_iso': country_abbr,
#                     'ee_r264_id': ee_r264_id,
#                     'year': year,
#                     'month': month,
#                     'cdd_diff': cdd_diff,
#                     'kwh_diff': kwh_diff,
#                     'price_usd_per_kwh': price,
#                     'savings_percap_usd': savings_percap,
#                     'total_savings_usd': total_savings
#                 })

#             except Exception as e:
#                 print(f"Error processing {c} {year}-{month}: {e}")
#                 continue

#     # Convert results to DataFrame and save to CSV
#     output_csv = os.path.join(inputdir, f'output/valuation/{c}_{year}.csv')
    
#     if results:
#         df = pd.DataFrame(results)
#         df.to_csv(output_csv, index=False)
#         print(f"Saved results for {c} to {output_csv}")
#     else:
#         print(f"No results for {c}")
        



