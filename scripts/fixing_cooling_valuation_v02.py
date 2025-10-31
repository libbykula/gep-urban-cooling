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


# inputdir = 'G:/Shared drives/NatCapTEEMs/Files/base_data/submissions'
inputdir = '/users/3/kula0049/urban-cooling/inputs'

results_path = os.path.join(inputdir, 'InVEST Results/cooling workspace/3_16_2024_fixed_multistate/')
multistate_metro_list = [
    foldername
    for foldername in os.listdir(results_path) 
]
multistate_metro_list = multistate_metro_list + ['Louisville/Jefferson County, KY-IN']

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

def monthly_temp_degC_to_cdd(temp_series):
    # Convert average temperature from Celsius to Fahrenheit
    avg_temp_c = temp_series
    avg_temp_f = avg_temp_c * 9/5 + 32

    # Define the threshold temperature in Fahrenheit
    threshold_temp_degf = 70

    # Create an empty Series for the results
    cdd_m = pd.Series(index=avg_temp_c.index)

    # Apply the condition and calculate cdd_m
    above_threshold = avg_temp_f >= threshold_temp_degf
    below_threshold = avg_temp_f < threshold_temp_degf

    cdd_m[above_threshold] = 29.58 * avg_temp_f[above_threshold] - 1905
    cdd_m[below_threshold] = 1.07 * (10**(-18)) * avg_temp_f[below_threshold]**10.96

    # Getting it back in Celsius 
    cdd_m = cdd_m*(5/9) 

    return cdd_m


# Saving the coefficient as the cooling gradient m_c
mc = 0.010582177510612831 # ran code elsewhere to get this

### Fixing my energy savings valuation ### 

uhi_data = pd.read_csv(os.path.join(inputdir, 'Results/uhi_4_29_2024_v03.csv'))
# uhi_data = pd.read_csv(os.path.join(inputdir, 'Results/uhi_buffered_7_01_2024.csv'))
consump_fixed_table = pd.read_csv(os.path.join(inputdir, 'Results/Metros/consumption_fixed.csv'))
build_heights = pd.read_csv(os.path.join(inputdir, 'Energy Consumption Table/Continental_building_height/OutputData_CombinedModel/us/Metros/metros_build_height.csv'))

def run(c):
    if c == 'Louisville-Jefferson County, KY-IN':
        c = 'Louisville/Jefferson County, KY-IN'
    c_orig = c
    c = re.sub(r'\/', '-', c) # Replacing slashes with dashes for paths' sake

    prev_energy_table = pd.read_csv(os.path.join(inputdir, 'Energy Consumption Table/Metro tables/' + c + '.csv'))
    prev_consump = prev_energy_table['consumption'].iloc[0]

    filtered_df = build_heights[build_heights['metro'] == c_orig]
    avg_floors = filtered_df['avg_build_floors'].iloc[0] # need to include to get from consumption by floor area to footprint area

    metro_consump = pd.read_csv(os.path.join(inputdir, 'Energy Consumption Table/Metro tables/' + c + '.csv'))
    building_cost = metro_consump['cost'].iloc[0]

    for month in ['06', '07', '08']:
        for year in ['2001', '2011', '2021']:
            if os.path.exists(os.path.join(inputdir, 'InVEST Results/cooling workspace/7_31_25/' + c + '_' + year + '_' + month + '.csv')) == 0:
                # Setting file names
                base_subdir = (
                    os.path.join(inputdir, 'InVEST Results/cooling workspace/3_16_2024_fixed_multistate')
                    if c in multistate_metro_list
                    else os.path.join(inputdir, 'InVEST Results/cooling workspace/11_21_2023_metros')
                )
                base_path = os.path.join(inputdir, base_subdir, c)

                # Heatmap path
                hm_path = os.path.join(base_path, f'hm_{c}_{year}_{month}_al_compress.tif')

                # Building path with fallback options
                building_filenames = [
                    f'buildings_with_stats_{c}_{year}_{month}_Aug30.shp',
                    f'buildings_with_stats_{c}_{year}_{month}_fixed.shp',
                    f'buildings_with_stats_{c}_{year}_{month}_Aug30.gpkg'
                ]

                for filename in building_filenames:
                    building_path = os.path.join(base_path, filename)
                    if os.path.exists(building_path):
                        break
                
                # deleting unnecessary files 
                if os.path.exists(os.path.join(base_path, f'hm_{c}_{year}_{month}.tif')):
                    os.remove(os.path.join(base_path, f'hm_{c}_{year}_{month}.tif'))
                for filename in os.listdir(base_path): 
                    if 'uhi_results' in filename:
                        file_path = os.path.join(base_path, filename)
                        if os.path.isfile(file_path):
                            os.remove(file_path)

                ### CREATING AIR MIXING HM ####
                hm_mixed_path = os.path.join(inputdir, 'mixed/hm_' + c + '_' + year + '_' + month + '_mixed_compress.tif')
                if os.path.exists(hm_mixed_path) == 0:                    
                    tempdir = os.path.join(inputdir, 'temp/' + c)
                    os.makedirs(tempdir, exist_ok=True)  # creates the folder and parents if needed

                    signal_raster_path = hm_path
                    exponential_kernel_path = os.path.join(tempdir, 'exponential_kernel.tif')
                    target_convolve_raster_path = os.path.join(inputdir, 'mixed/hm_'+ c + '_' + year + '_' + month + '_mixed.tif')
                    decay_kernel_distance = 600

                    pygeo.kernels.exponential_decay_kernel(
                            target_kernel_path=exponential_kernel_path,
                            max_distance=decay_kernel_distance * 5,
                            expected_distance=decay_kernel_distance)
                    print('made exponential raster')
                    
                    pygeo.convolve_2d((signal_raster_path, 1), (exponential_kernel_path, 1),
                            target_convolve_raster_path, working_dir=tempdir,
                            ignore_nodata_and_edges=True)
                    print('convolved')

                    compress_tifs(target_convolve_raster_path)
                    os.remove(signal_raster_path)
                    shutil.rmtree(tempdir)

                ### USING MIXED HM FOR COOLING VALUATION ####
                results_dict = {}
                                    
                buildings_gdf = gpd.read_file(building_path)
                buildings_gdf = buildings_gdf.to_crs('EPSG:5070')
                building_area_m2 = buildings_gdf.area 

                uhi_max = uhi_data['uhi'][(uhi_data['metro'] == c_orig) & (uhi_data['month'] == int(month))].iloc[0]
                
                # buildings_gdf_wgs84 = buildings_gdf.to_crs('EPSG:4326')
                # buildings_wgs84_path = re.sub('.shp', '_fixed.gpkg', building_path)
                # buildings_wgs84_path = os.path.join(inputdir, 'InVEST Results/cooling workspace/4_9_25_gpkgs/buildings_' + c + '_' + year + '_' + month + '_wgs84.gpkg')
                # buildings_gdf_wgs84.to_file(buildings_wgs84_path) # why did I make this wgs84 when hm is in epsg:5070?

                hm_stats = pygeo.zonal_statistics(base_raster_path_band = (hm_mixed_path, 1),
                                                            aggregate_vector_path = building_path,
                                                            ignore_nodata = True)
                os.remove(building_path)
                os.remove(hm_mixed_path)

                buildings_gdf['avg_cc'] = 0
                for i in range(len(buildings_gdf) + 1):
                    try:
                        stat = hm_stats[i]
                        if stat and stat.get('count', 0) > 0:
                            buildings_gdf.at[i, 'avg_cc'] = stat['sum'] / stat['count']
                    except (IndexError, TypeError, KeyError):
                        # Skip or log as needed
                        pass

                # build_temp_w_nat = build_temp_df['build_temp_w_nat']
                build_temp_w_nat = buildings_gdf['mean_t_air']
                build_deg_cooling = uhi_max*buildings_gdf['avg_cc']  
                build_temp_wo_nat = build_temp_w_nat + build_deg_cooling

                build_consump_saved = (monthly_temp_degC_to_cdd(build_temp_wo_nat) - monthly_temp_degC_to_cdd(build_temp_w_nat))*mc 
                buildings_gdf['sav_upd'] = build_consump_saved*building_area_m2*building_cost*avg_floors # Updated/fixed savings results
                
                results_dict['metro'] = c
                results_dict['year'] = year
                results_dict['month'] = month
                results_dict['sav_upd_sum'] = buildings_gdf['sav_upd'].sum()

                row_df = pd.DataFrame.from_dict(results_dict, orient='index') 
                row_df.to_csv(os.path.join(inputdir, 'InVEST Results/cooling workspace/7_31_25/' + c + '_' + year + '_' + month + '.csv'))
                
    shutil.rmtree(os.path.join(base_subdir, c))
