# Libby Kula
#  Global GEP Urban Cooling
# 07/14/2025

import logging
import numpy as np
import os
import pygeoprocessing as pygeo
import pandas as pd
import geopandas as gpd
from osgeo import gdal
from osgeo import gdalconst
from osgeo import gdalnumeric
from osgeo import ogr
import matplotlib.pyplot as plt
# import multiprocessing as mp
# import hazelbean as hb
# import ineqpy
import rasterio
# from rasterio.mask import mask
import re 
import requests
import sys
import time
# from scipy.stats import ttest_ind
# import statsmodels.api as sm
import glob
# from sklearn.ensemble import RandomForestRegressor
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import r2_score, mean_squared_error
# import shap
# from scipy.optimize import curve_fit
# from sklearn.metrics import r2_score
# import natcap.invest.urban_cooling_model
# import natcap.invest.utils

# set wd
# os.chdir('C:/Users/kibby/OneDrive/Desktop/Research/GEP/')

inputdir = '/users/3/kula0049/urban-cooling/'

def run():
    vector_gdf = gpd.read_file(os.path.join(inputdir, 'Data/Urban Boundaries/GUB_Global_2018/GUB_Global_2018.shp'))
    urban_list = vector_gdf['ORIG_FID'].unique().tolist()
    # print(urban_list)
    urban_list.sort()

    def clip_to_urban(ras, c):
        raster_dataset = gdal.Open(ras)
        if os.path.exists(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras)) == 0:
            gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras), 
                raster_dataset, cutlineDSName=os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg'), cropToCutline=True)
        if os.path.exists(re.sub(r'\.(.*?)$', r'_clipped_{}_nad83.\1'.format(c), ras)) == 0:
            gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}_nad83.\1'.format(c), ras), 
                re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras), dstSRS='EPSG:5070')
            
    def calc_uhi_buffered(c_orig, month, year, buffer_size):
        c = str(c_orig)  
        
        urban_gdf = vector_gdf[vector_gdf['ORIG_FID'] == c_orig] 
        urban_gdf = urban_gdf.to_crs('EPSG:4326')

        # for index, row in urban_gdf.iterrows():
        #     geom = row['geometry']
        #     if not geom.is_valid:
        #         fixed_geom = geom.buffer(0)
        #         urban_gdf.at[index, 'geometry'] = fixed_geom
       
        if os.path.exists(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg')) == 0:
            urban_gdf.to_file(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg'))
        if os.path.exists(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.shp')) == 0:
            urban_gdf.to_file(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.shp'))

        urban_gdf = urban_gdf.to_crs('EPSG:5070')
        raster_path = os.path.join(inputdir, 'Data/Tmean_stitched/tmean_stitched_' + year + '_' + month + '_compress.tif')
            
        # adding buffers to urban_gdf for all cities to take care of those with small reference areas 
        buffers = urban_gdf.geometry.buffer(distance = buffer_size)
        buffered_minus_original = buffers.difference(urban_gdf.geometry)
        ref_buffered = gpd.GeoDataFrame(geometry=buffered_minus_original, crs=urban_gdf.crs)
        ref_buffered = ref_buffered.to_crs('EPSG:4326')
        ref_buffered_path = os.path.join(inputdir, 'Data/Polygon_vectors/rural_refs/rural_ref_' + c + '.shp')
        ref_buffered.to_file(ref_buffered_path)

        temp_mean = gdal.Open(raster_path)
        gdal.Warp(re.sub(r'\.(.*?)$', r'_rural_ref_{}.\1'.format(c), raster_path), 
                            temp_mean, cutlineDSName=ref_buffered_path, cropToCutline=True) 
                    
        rural_ref_stats = pygeo.zonal_statistics(base_raster_path_band = (re.sub(r'\.(.*?)$', r'_rural_ref_{}.\1'.format(c), raster_path), 1),
                                                            aggregate_vector_path = ref_buffered_path,
                                                            ignore_nodata = True)
        rural_ref_temp = rural_ref_stats[0]['sum']/rural_ref_stats[0]['count']

        clip_to_urban(raster_path, c)

        urban_ref_stats = pygeo.zonal_statistics(base_raster_path_band = (re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), raster_path), 1),
                                                            aggregate_vector_path =os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.shp'), 
                                                            ignore_nodata = True)
        urban_max = urban_ref_stats[0]['max'] # using max of the averages here to get a baseline UHI change
        uhi = urban_max - rural_ref_temp
        return [uhi, rural_ref_temp]
    
    month_list = [f'{i:02}' for i in range(1, 13)]
    # columns = ['urban', 'year', 'month', 'uhi', 't_ref']
    # results_df = pd.DataFrame(columns=columns)

    # Define the folder path
    folder_path = os.path.join(inputdir, "Results/brokens")

    # Use glob to find all CSV files in the folder
    csv_files = glob.glob(os.path.join(folder_path, "*.csv"))

    # List to store DataFrames
    df_list = []

    # Loop through each CSV file and read it
    for file in csv_files:
        df = pd.read_csv(file)
        df_list.append(df)

    # Concatenate all DataFrames
    combined_df = pd.concat(df_list, ignore_index=True)

    # Optionally, save the combined DataFrame
    combined_df.to_csv(os.path.join(inputdir, "uhi_results_broken.csv"), index=False)
    
    # for c in [urban_list[0]]: # trying the first one
    #     c_orig = c
    #     c = str(c)
    #     print(c)
    #     for month in month_list:
    #         uhi_results = calc_uhi_buffered(c_orig= c_orig, month = month, year = '2019', buffer_size=10000)
    #         uhi = uhi_results[0]
    #         t_ref = uhi_results[1]
    #         row = [c, '2019', month, uhi, t_ref]
    #         row_df = pd.DataFrame([row], columns=columns)
    #         results_df = pd.concat([results_df, row_df])

    #     results_df.to_csv(os.path.join(inputdir,'Results/uhi_global_gep_' + c + '.csv'))
    # def prep_and_run_cooling_lists(c):
    #     # print(c)
    #     c_orig = c
    #     # urban_gdf = gpd.read_file('Polygon_vectors/urbans/' + re.sub(r'\/', '-', c) + '.gpkg') # regex for replacing slashes in urban names with dashes for paths to work
    #     urban_gdf = vector_gdf[vector_gdf['ORIG_FID'] == c] 
    #     c = re.sub(r'\/', '-', c)  
    #     urban_gdf = urban_gdf.to_crs('EPSG:4326')
    #     # print(urban_gdf.head())
    #     for index, row in urban_gdf.iterrows():
    #         geom = row['geometry']
    #         if not geom.is_valid:
    #             fixed_geom = geom.buffer(0)
    #             urban_gdf.at[index, 'geometry'] = fixed_geom
        
    #     if os.path.exists(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg')) == 0:
    #         urban_gdf.to_file(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg'))
    #     if os.path.exists(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.shp')) == 0:
    #         urban_gdf.to_file(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.shp'))
        
    #     # year_list = ['2001', '2011', '2021']
    #     year_list = ['2019']
            
    #     for year in year_list:    
    #         lulc_path = os.path.join(inputdir, 'Data/lulc_glc_fcs30d_' + year + '.tif')
    #         lulc_dataset = gdal.Open(lulc_path) 

    #         gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), lulc_path), 
    #                             lulc_dataset, cutlineDSName=os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg', cropToCutline=True))
    #         gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}_nad83.\1'.format(c), lulc_path), 
    #                         re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), lulc_path), dstSRS='EPSG:5070')
            
    #         month_list = [f'{i:02}' for i in range(1, 13)]

    #         # Looping through months 
    #         for month in month_list:
    #             print(f'Processing {year}-{month}')
                
    #             raster_paths = [os.path.join(inputdir, 'Data/Evapotranspiration/Global-ET0_monthly_v3/Global-ET0_v3_monthly/et0_V3_' + month + '_aligned_wgs84.tif'), 
    #                             os.path.join(inputdir, 'Data/Reference Air Temperature/PRISM_tmean_30yr_normal_800mM4_' + month + '_bil/PRISM_tmean_30yr_normal_800mM4_' + month + '_bil_wgs84.bil')] 

    #             # Masking input rasters to urban
    #             for ras in raster_paths:
    #                 raster_dataset = gdal.Open(ras)
    #                 gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras), 
    #                                 raster_dataset, cutlineDSName='Polygon_vectors/urbans/' + c + '.gpkg', cropToCutline=True)
    #                 gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}_nad83.\1'.format(c), ras), 
    #                                 re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras), dstSRS='EPSG:5070')

    #             # Getting rural reference temperature and UHIs
    #             uhi_vars = calc_uhi_buffered(c, month, buffer_size=10000) # 10km buffer for rural reference area
    #             uhi = uhi_vars[0]
    #             rural_ref_temp = uhi_vars[1]

    #             # Runnng the cooling Urban InVEST model
    #             args = {
    #                 'aoi_vector_path': os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg'),
    #                 # 'avg_rel_humidity': str(avg_humid),
    #                 'biophysical_table_path': 'Biophysical Tables/biophysical_cooling_v03.csv',
    #                 # 'building_vector_path': 'C:\\Users\\kibby\\OneDrive\\Desktop\\Research\\DOI\\Data\\Built '
    #                 #                                                     'Infrastructure\\Microsoft\\urbans\\' + c + '.gpkg', 
    #                 'cc_method': 'factors',
    #                 'cc_weight_albedo': '',
    #                 'cc_weight_eti': '',
    #                 'cc_weight_shade': '',
    #                 'do_energy_valuation': False,
    #                 'do_productivity_valuation': False, # maybe true? need humidity if so 
    #                 # 'energy_consumption_table_path': 'C:\\Users\\kibby\\OneDrive\\Desktop\\Research\\DOI\\Data\\Energy '
    #                 #                                                     'Consumption '
    #                 #                                                     'Table\\urban '
    #                 #                                                     'tables\\' + c + '.csv',
    #                 'green_area_cooling_distance': '50',
    #                 'lulc_raster_path': re.sub(r'\.(.*?)$', r'_clipped_{}_nad83.\1'.format(c), lulc_path),
    #                 'n_workers': '-1',
    #                 'ref_eto_raster_path': re.sub(r'\.(.*?)$', r'_clipped_{}_nad83.\1'.format(c), raster_paths[0]),
    #                 'results_suffix': c + '_' + year + '_' + month,
    #                 't_air_average_radius': '600',
    #                 't_ref': str(rural_ref_temp),
    #                 'uhi_max': str(uhi),
    #                 'workspace_dir': 'output/' + c,
    #                 }
    #             natcap.invest.urban_cooling_model.execute(args)
    #             # Removing city-clipped inputs to save on space 
    #             # for ras in raster_paths:
    #             #     os.remove(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras))
    #             #     os.remove(re.sub(r'\.(.*?)$', r'_clipped_{}_nad83.\1'.format(c), ras))
    #             # os.remove(re.sub(r'\.(.*?)$', r'_rural_ref_{}.\1'.format(c), raster_paths[1]))
    #     # shutil.rmtree('C:/Users/kibby/OneDrive/Desktop/Research/DOI/Code/cooling workspace/3_29_2024/' + c + '/intermediate')