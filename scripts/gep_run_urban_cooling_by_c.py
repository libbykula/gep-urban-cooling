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
import natcap.invest.urban_cooling_model
import natcap.invest.utils

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
    # if os.path.exists(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras)) == 0:
    gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras), 
        raster_dataset, cutlineDSName=os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg'), cropToCutline=True)
    # if os.path.exists(re.sub(r'\.(.*?)$', r'_clipped_{}_mollweide.\1'.format(c), ras)) == 0:
    gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}_mollweide.\1'.format(c), ras), 
        re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras), dstSRS='+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs')

def calc_uhi_buffered(c, month, year, buffer_size):    
    # Keep only polygons (Polygon or MultiPolygon)
    urban_gdf = vector_gdf[
        (vector_gdf['SMOD_ID'] == c) &
        (vector_gdf.geometry.type.isin(['Polygon', 'MultiPolygon']))
    ]

    urban_gdf = urban_gdf.to_crs('EPSG:4326')
    urban_gdf.to_file(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg'))
    urban_gdf.to_file(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.shp'))

    urban_gdf = urban_gdf.to_crs('+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs')

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

    os.remove(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), raster_path))
    os.remove(re.sub(r'\.(.*?)$', r'_clipped_{}_mollweide.\1'.format(c), raster_path))
    os.remove(re.sub(r'\.(.*?)$', r'_rural_ref_{}.\1'.format(c), raster_path))
    os.remove(ref_buffered_path)
    # os.remove(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg'))
    # os.remove(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.shp'))

    return [uhi, rural_ref_temp]

def get_raster_paths(inputdir, year, month):
    # Candidates for ET0 file (V3 vs v3)
    et0_candidates = [
        os.path.join(inputdir, f'Data/Evapotranspiration/Global-ET0_monthly_v3/Global-ET0_v3_monthly/et0_V3_{month}.tif'),
        os.path.join(inputdir, f'Data/Evapotranspiration/Global-ET0_monthly_v3/Global-ET0_v3_monthly/et0_v3_{month}.tif')
    ]
    
    # Pick the one that exists (or raise error if neither)
    et0_file = next((f for f in et0_candidates if os.path.exists(f)), None)
    if et0_file is None:
        raise FileNotFoundError(f"No ET0 raster found for month {month} in {et0_candidates}")

    tmean_file = os.path.join(
        inputdir, f'Data/Tmean_stitched/tmean_stitched_{year}_{month}_compress.tif'
    )
    
    return [et0_file, tmean_file]

def calculate_uhi(c):
    ##### CREATING THE UHI TABLES ####    
    pathlist = [os.path.join(inputdir, 'Data/Polygon_vectors/rural_refs/rural_ref_' + c + '.shp'),
                os.path.join(inputdir,'Results/brokens/uhi_broken_global_gep_' + c + '.csv'),
                os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg'),
                os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.shp')]
    
    for path in pathlist:
        if os.path.exists(path):
            os.remove(path)

    month_list = [f'{i:02}' for i in range(1, 13)]
    for month in month_list:
        year = '2019'
        raster_path = os.path.join(inputdir, 'Data/Tmean_stitched/tmean_stitched_' + year + '_' + month + '_compress.tif')
        for path in [re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), raster_path),
                    re.sub(r'\.(.*?)$', r'_clipped_{}_mollweide.\1'.format(c), raster_path),
                    re.sub(r'\.(.*?)$', r'_rural_ref_{}.\1'.format(c), raster_path)]:
            if os.path.exists(path):
                os.remove(path)

    try:
        month_list = [f'{i:02}' for i in range(1, 13)]
        columns = ['urban', 'year', 'month', 'uhi', 't_ref']
        results_df = pd.DataFrame(columns=columns)

        for month in month_list:
            uhi_results = calc_uhi_buffered(c, month = month, year = '2019', buffer_size=10000)

            uhi = uhi_results[0]
            t_ref = uhi_results[1]
            row = [c, '2019', month, uhi, t_ref]
            row_df = pd.DataFrame([row], columns=columns)
            results_df = pd.concat([results_df, row_df])

        results_df.to_csv(os.path.join(inputdir,'Data/uhi/uhi_global_gep_' + c + '.csv'))

        return [uhi, t_ref]

    except:
        # Keep only polygons (Polygon or MultiPolygon)
        urban_gdf = vector_gdf[
            (vector_gdf['SMOD_ID'] == c) &
            (vector_gdf.geometry.type.isin(['Polygon', 'MultiPolygon']))
        ]

        columns_broken = ['urban', 'area'] #saving the urban id and the area in km2
        brokens_df = pd.DataFrame(columns=columns_broken)
        row_broken = [c, urban_gdf['AREA_SQM'].iloc[0]] 
        row_broken_df = pd.DataFrame([row_broken], columns=columns_broken)
        row_broken_df.to_csv(os.path.join(inputdir,'Data/uhi/brokens/uhi_broken_global_gep_' + c + '.csv'))

def prep_and_run_cooling(c):
    # urban_gdf = gpd.read_file('Polygon_vectors/urbans/' + re.sub(r'\/', '-', c) + '.gpkg') # regex for replacing slashes in urban names with dashes for paths to work
    # Keep only polygons (Polygon or MultiPolygon)
    urban_gdf = vector_gdf[
        (vector_gdf['SMOD_ID'] == c) &
        (vector_gdf.geometry.type.isin(['Polygon', 'MultiPolygon']))
    ]

    urban_gdf = urban_gdf.to_crs('EPSG:4326')
    # print(urban_gdf.head())
    for index, row in urban_gdf.iterrows():
        geom = row['geometry']
        if not geom.is_valid:
            fixed_geom = geom.buffer(0)
            urban_gdf.at[index, 'geometry'] = fixed_geom
    
    # if os.path.exists(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg')) == 0:
    urban_gdf.to_file(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg'))
    # if os.path.exists(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.shp')) == 0:
    urban_gdf.to_file(os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.shp'))
    
    year_list = ['2019']
        
    for year in year_list:    
        lulc_path = os.path.join(inputdir, 'Data/lulc/lulc_glc_fcs30d_' + year + '.tif')
        lulc_dataset = gdal.Open(lulc_path) 

        gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), lulc_path), 
                            lulc_dataset, cutlineDSName=os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg'), cropToCutline=True)
        gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}_mollweide.\1'.format(c), lulc_path), 
                        re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), lulc_path), dstSRS='+proj=moll +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs')
        
        month_list = [f'{i:02}' for i in range(1, 13)]

        # Looping through months 
        for month in month_list:
            print(f'Processing {year}-{month}')
            
            raster_paths = get_raster_paths(inputdir, year, month)

            # Masking input rasters to urban
            for ras in raster_paths:
                clip_to_urban(ras, c)

            # Getting rural reference temperature and UHIs
            # uhi_vars = calc_uhi_buffered(c, month, year, buffer_size=10000) # 10km buffer for rural reference area
            uhi_vars = calculate_uhi(c)
            uhi = uhi_vars[0]
            rural_ref_temp = uhi_vars[1]

            # Prepping biophysical table
            country_abbr = urban_gdf['ISO'].iloc[0]
            ee_r264_country_ids = pd.read_csv(os.path.join(inputdir, 'Data/cartographic/ee/ee_r264_correspondence.csv'))
            ee_r264_id = ee_r264_country_ids.loc[
                ee_r264_country_ids['ee_r264_label'] == country_abbr, 'ee_r264_id'
            ].iloc[0]

            input_biophys = pd.read_csv(os.path.join(inputdir, 'Data/biophysical_tables/without_green_indicator/' + str(int(ee_r264_id)) + '_' + month + '.csv')) # EXCEPT for US and Russia
            output_biophys_path = os.path.join(inputdir, 'Data/biophysical_tables/final_biophys_tables/' + str(int(ee_r264_id)) + '_' + month + '.csv')

            green_areas_ind = pd.read_csv(os.path.join(inputdir, 'Data/biophysical_tables/glc_30_green_areas.csv'))

            # Merge on lucode (input_biophys) and ID (green_areas_ind), keep only green_area
            merged = input_biophys.merge(
                green_areas_ind[['ID', 'green_area']], 
                left_on='lucode', 
                right_on='ID', 
                how='left'
            ).drop(columns=['ID'])  # Drop extra ID col after merge

            # divide shade by 100 to get 0-1 proportion
            merged['shade'] = merged['shade']/100

            # Save result
            merged.to_csv(output_biophys_path, index=False)

            # Runnng the cooling Urban InVEST model
            args = {
                'aoi_vector_path': os.path.join(inputdir, 'Data/Polygon_vectors/urbans/' + c + '.gpkg'),
                # 'avg_rel_humidity': str(avg_humid),
                'biophysical_table_path': output_biophys_path,
                # 'building_vector_path': 'C:\\Users\\kibby\\OneDrive\\Desktop\\Research\\DOI\\Data\\Built '
                #                                                     'Infrastructure\\Microsoft\\urbans\\' + c + '.gpkg', 
                'cc_method': 'factors',
                'cc_weight_albedo': '',
                'cc_weight_eti': '',
                'cc_weight_shade': '',
                'do_energy_valuation': False,
                'do_productivity_valuation': False, # maybe true? need humidity if so 
                # 'energy_consumption_table_path': 'C:\\Users\\kibby\\OneDrive\\Desktop\\Research\\DOI\\Data\\Energy '
                #                                                     'Consumption '
                #                                                     'Table\\urban '
                #                                                     'tables\\' + c + '.csv',
                'green_area_cooling_distance': '50',
                'lulc_raster_path': re.sub(r'\.(.*?)$', r'_clipped_{}_mollweide.\1'.format(c), lulc_path),
                'n_workers': '-1',
                'ref_eto_raster_path': re.sub(r'\.(.*?)$', r'_clipped_{}_mollweide.\1'.format(c), raster_paths[0]),
                'results_suffix': c + '_' + year + '_' + month,
                't_air_average_radius': '600',
                't_ref': str(rural_ref_temp),
                'uhi_max': str(uhi),
                'workspace_dir': inputdir + 'output/invest_results/' + c,
                }
            natcap.invest.urban_cooling_model.execute(args)
            # Removing city-clipped inputs to save on space 
            # for ras in raster_paths:

    # shutil.rmtree('C:/Users/kibby/OneDrive/Desktop/Research/DOI/Code/cooling workspace/3_29_2024/' + c + '/intermediate')

# prep_and_run_cooling("30_168")
