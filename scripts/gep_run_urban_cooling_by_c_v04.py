# Libby Kula
#  Global GEP Urban Cooling
# 07/14/2025

import logging
import numpy as np
import os
import pygeoprocessing as pygeo
import pandas as pd
import geopandas as gpd
from osgeo import gdal, osr
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

vector_gdf = gpd.read_file(os.path.join(inputdir, 'Data/urbanspatial-guppd-v1-gpkg/urbanspatial-guppd-v1-gpkg.gpkg'),
                           layer='urbanspatial_guppd_v1_polygons')
urban_list = vector_gdf['SMOD_ID'].unique().tolist()
urban_list.sort()

def clip_to_urban(ras, c):
    c = str(c)
    raster_dataset = gdal.Open(ras)
    gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras), 
        raster_dataset, cutlineDSName=os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg'), cropToCutline=True)
    # gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}_mollweide.\1'.format(c), ras), 
    #     re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras), dstSRS='+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs')

def calc_uhi_buffered(c, month, year, buffer_size):    
    # Keep only polygons (Polygon or MultiPolygon)
    urban_gdf = vector_gdf[
        (vector_gdf['SMOD_ID'] == c) &
        (vector_gdf.geometry.type.isin(['Polygon', 'MultiPolygon']))
    ]

    urban_gdf = urban_gdf.to_crs('+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs')
    raster_path = os.path.join(inputdir, 'Data/Tmean_stitched/tmean_stitched_' + year + '_' + month + '_compress.tif')

    temp_mean = gdal.Open(raster_path)
    
    # Tmax
    clip_to_urban(raster_path, c)
    clipped_path = re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), raster_path)
    urban_temps = gdal.Open(clipped_path)
    urban_temp_band = urban_temps.GetRasterBand(1)
    urban_ref_stats = urban_temp_band.GetStatistics(True, True)
    urban_max = urban_ref_stats[1] # max 

    temp_diffs = -(urban_temps - urban_max)
    # pathlist = [re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), raster_path),
    #             re.sub(r'\.(.*?)$', r'_rural_ref_{}.\1'.format(c), raster_path),
    #             ref_buffered_path]
   # for path in pathlist:
     #   if os.path.exists(path):
       #     os.remove(path)

    return [urban_max, rural_ref_temp]

def calculate_uhi(c):
    ##### CREATING THE UHI TABLES ####    
    pathlist = [os.path.join(inputdir, 'Data/Polygon_vectors/rural_refs/rural_ref_' + c + '.shp'),
                os.path.join(inputdir,'Results/brokens/uhi_broken_global_gep_' + c + '.csv'),
                os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg'),
                os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.shp')]
    
   # for path in pathlist:
     #   if os.path.exists(path):
       #     os.remove(path)
    
    urban_gdf = vector_gdf[
        (vector_gdf['SMOD_ID'] == c) &
        (vector_gdf.geometry.type.isin(['Polygon', 'MultiPolygon']))
    ]

    urban_gdf = urban_gdf.to_crs('EPSG:4326')
    urban_gdf.to_file(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg'))

    month_list = [f'{i:02}' for i in range(1, 13)]
    # for month in month_list:
    #     year = '2019'
    #     raster_path = os.path.join(inputdir, 'Data/Tmean_stitched/tmean_stitched_' + year + '_' + month + '_compress.tif')
    #     for path in [re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), raster_path),
    #                 re.sub(r'\.(.*?)$', r'_clipped_{}_mollweide.\1'.format(c), raster_path),
    #                 re.sub(r'\.(.*?)$', r'_rural_ref_{}.\1'.format(c), raster_path)]:
            # if os.path.exists(path):
            #     os.remove(path)

    # try:
    month_list = [f'{i:02}' for i in range(1, 13)]
    columns = ['urban', 'year', 'month', 't_max', 't_ref']
    results_df = pd.DataFrame(columns=columns)

    for month in month_list:
        uhi_results = calc_uhi_buffered(c, month = month, year = '2019', buffer_size=10000)

        urban_max = uhi_results[0]
        t_ref = uhi_results[1]
        row = [c, '2019', month, urban_max, t_ref]
        row_df = pd.DataFrame([row], columns=columns)
        results_df = pd.concat([results_df, row_df])

    results_df.to_csv(os.path.join(inputdir,'Data/uhi/uhi_global_gep_' + c + '.csv'))

    return [urban_max, t_ref]

    # except:
    #     # Keep only polygons (Polygon or MultiPolygon)
    #     urban_gdf = vector_gdf[
    #         (vector_gdf['SMOD_ID'] == c) &
    #         (vector_gdf.geometry.type.isin(['Polygon', 'MultiPolygon']))
    #     ]

    #     columns_broken = ['urban', 'area'] #saving the urban id and the area in km2
    #     brokens_df = pd.DataFrame(columns=columns_broken)
    #     row_broken = [c, urban_gdf['AREA_SQM'].iloc[0]] 
    #     row_broken_df = pd.DataFrame([row_broken], columns=columns_broken)
    #     row_broken_df.to_csv(os.path.join(inputdir,'Data/uhi/brokens/uhi_broken_global_gep_' + c + '.csv'))
