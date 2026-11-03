# Libby Kula
# NCA and Equity
# 3/30/2026
# Purpose: 
# Update: re-running shit for Baltimore and other places that are broken and getting ready for SNAPP


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
import multiprocessing as mp
# import hazelbean as hb
import rasterio
from rasterio.mask import mask
import re 
import shutil
import sys
import itertools
from multiprocessing import Pool


import natcap.invest.urban_cooling_model
import natcap.invest.utils

# import fiona
# # from fiona.ogrext import SHAPE_RESTORE_SHX

# fiona.Env(SHAPE_RESTORE_SHX='YES')

output_dir = '/projects/standard/jajohns/shared/Files/urban_cooling/workspace'
data_dir = '/projects/standard/jajohns/shared/Files/urban_cooling/base_data'

# Valid metros list 
vector_gdf = gpd.read_file(os.path.join(data_dir, 'Polygon_vectors/tl_2019_us_cbsa/metros_boundaries.gpkg'))

######## RUNNING INVEST COOLING MODEL, LOOPING THROUGH CITIES ##########
def clip_to_metro(ras, c):
    raster_dataset = gdal.Open(ras)
    gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras), 
            raster_dataset, cutlineDSName=os.path.join(data_dir, 'Polygon_vectors/Metros/' + c + '.gpkg'), cropToCutline=True)
    gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}_nad83.\1'.format(c), ras), 
        re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras), dstSRS='EPSG:5070')

uhi_df = pd.read_csv(os.path.join(data_dir, 'uhi_2_20_2026.csv'))

months = ['06', '07', '08']
# years = ['2001', '2011', '2021']
years = ['2011']
scenarios = ['all', 'public']

combos = list(itertools.product(years, months, scenarios))

def run(c):
    c_orig = c
    c = re.sub(r'\/', '-', c)

    # Preparing data
    metro_gdf = vector_gdf[vector_gdf['NAME'] == c_orig] 
    metro_gdf = metro_gdf.to_crs('EPSG:4326')
    
    for index, row in metro_gdf.iterrows():
        geom = row['geometry']
        if not geom.is_valid:
            fixed_geom = geom.buffer(0)
            metro_gdf.at[index, 'geometry'] = fixed_geom
    
    metro_gdf.to_file(os.path.join(data_dir, 'Polygon_vectors/Metros/' + c + '.gpkg'))
    metro_gdf.to_file(os.path.join(data_dir, 'Polygon_vectors/Metros/' + c + '.shp'))

    for year in years:        
        nlcd_wgs84_path = os.path.join(data_dir, 'SNAPP_Public_NLCD/SNAPP_Public_NLCD_' + year + '_' + c + '.tif')
        nlcd_dataset = gdal.Open(nlcd_wgs84_path) 
        gdal.Warp(re.sub(r'.tif', r'_nad83.tif', nlcd_wgs84_path), nlcd_wgs84_path, dstSRS='EPSG:5070')
            
    # Masking input rasters to metro
    for month in months:
        evapo_path = os.path.join(data_dir, 'Evapotranspiration/et0_V3_' + month + '_aligned_wgs84.tif')
        raster_dataset = gdal.Open(evapo_path)
        gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), evapo_path), 
                        raster_dataset, cutlineDSName=os.path.join(data_dir, 'Polygon_vectors/Metros/' + c + '.gpkg'), cropToCutline=True)
        gdal.Warp(re.sub(r'\.(.*?)$', r'_clipped_{}_nad83.\1'.format(c), evapo_path), 
                        re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), evapo_path), dstSRS='EPSG:5070')


    args_list = [
        (c, c_orig, year, month, scen)
        for year, month, scen in combos
    ]

    n_procs = int(os.environ.get("SLURM_CPUS_PER_TASK", 6))
    with Pool(processes=n_procs) as pool:
        pool.map(prep_and_run_cooling_lists, args_list)

    # Removing city-clipped inputs to save on space     
    for month in months:
        if os.path.exists(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), evapo_path)):
            os.remove(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), evapo_path))
        if os.path.exists(re.sub(r'\.(.*?)$', r'_clipped_{}_nad83.\1'.format(c), evapo_path)):
            os.remove(re.sub(r'\.(.*?)$', r'_clipped_{}_nad83.\1'.format(c), evapo_path))



def prep_and_run_cooling_lists(args):
    c, c_orig, year, month, scen = args
    print(f'Processing {year}-{month}-{scen}')

    workspace_dir = os.path.join(output_dir, '3_30_2026_' + scen + '_nature', c, year, month) 
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir)
    # Getting rural reference temperature and UHIs
    ##### PRE-CALCULATED
    rural_ref_temp = uhi_df.loc[
        (uhi_df['metro'] == c_orig) & (uhi_df['month'] == int(month)),
        't_ref'
    ].iloc[0]

    uhi = uhi_df.loc[
        (uhi_df['metro'] == c_orig) & (uhi_df['month'] == int(month)),
        'uhi'
    ].iloc[0]

    nlcd_wgs84_path = os.path.join(data_dir, 'SNAPP_Public_NLCD/SNAPP_Public_NLCD_' + year + '_' + c + '.tif')
    evapo_path = os.path.join(data_dir, 'Evapotranspiration/et0_V3_' + month + '_aligned_wgs84.tif')

    ### CALCULATING HERE
    # Runnng the cooling Urban InVEST model
    args = {
        'aoi_vector_path': os.path.join(data_dir,'Polygon_vectors/Metros/' + c + '.gpkg'),
        'biophysical_table_path': os.path.join(data_dir, 'Biophysical Tables/nlcd_biophysical_table_' + scen + '_nature.csv'), 
        'cc_method': 'factors',
        'cc_weight_albedo': '',
        'cc_weight_eti': '',
        'cc_weight_shade': '',
        'do_energy_valuation': False,
        'do_productivity_valuation': False,
        'energy_consumption_table_path': os.path.join(data_dir, 'Energy Consumption Table/Metro tables', c + '.csv'),
        'green_area_cooling_distance': '50',
        'lulc_raster_path': re.sub(r'.tif', r'_nad83.tif', nlcd_wgs84_path),
        'n_workers': '-1',
        'ref_eto_raster_path': re.sub(r'\.(.*?)$', r'_clipped_{}_nad83.\1'.format(c), evapo_path),
        'results_suffix': c + '_' + year + '_' + month,
        't_air_average_radius': '600',
        't_ref': str(rural_ref_temp),
        'uhi_max': str(uhi),
        'workspace_dir':workspace_dir,
        }
    natcap.invest.urban_cooling_model.execute(args)

    intermediate_folder = os.path.join(output_dir, '3_30_2026_' + scen + '_nature', c, year, month, 'intermediate') 
    keep_files_contain = 'T_air_' + c + '_' + year + '_' + month + '.tif'

    for filename in os.listdir(intermediate_folder):
        file_path = os.path.join(intermediate_folder, filename)
        if os.path.isfile(file_path) and keep_files_contain not in filename:
            os.remove(file_path)



