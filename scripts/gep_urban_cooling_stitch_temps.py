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
import multiprocessing as mp
# import hazelbean as hb
# import ineqpy
import rasterio
from rasterio.mask import mask
import re 
import requests
import sys
import time
import rioxarray as rxr

# set wd
# os.chdir("C:/Users/kibby/OneDrive/Desktop/Research/GEP")

month_list = [f'{i:02}' for i in range(1, 13)]

inputdir = '/users/3/kula0049/urban-cooling/'

def run():
    # month_list = ['01']

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

    for year in ['2019']:
        for month in month_list:
            temp_path_1 = os.path.join(inputdir, 'Data/Tmean/Tmean_' + year + month + '-0000000000-0000000000.tif')
            temp_path_2 = os.path.join(inputdir, 'Data/Tmean/Tmean_' + year + month + '-0000000000-0000023296.tif')

            temp_1 = rxr.open_rasterio(temp_path_1, chunks=2048)
            temp_2 = rxr.open_rasterio(temp_path_2, chunks=2048)

            for path in [temp_path_1, temp_path_2]:
                if os.path.exists(re.sub('.tif', '_al_compress.tif', path)) == 0:
                    gdal.Warp(re.sub('.tif', '_al.tif', path), path, xRes=0.008333333333333329748, yRes=0.008333333333333329748)
                    compress_tifs(re.sub('.tif', '_al.tif', path))

            stitched_path = os.path.join(inputdir, 'Data/tmean_stitched_' + year + '_' + month + '.tif')
            
            if os.path.exists(re.sub('.tif', '_compress.tif', stitched_path)) == 0:
                print('making new raster')
                pygeo.new_raster_from_base(
                    base_path = os.path.join(inputdir, 'Data/gpw_v4_population_count_rev11_2020_30_sec.tif'), 
                    target_path = stitched_path, 
                    datatype = gdal.GDT_Float32, 
                    band_nodata_list = [-9999]
                )
                
                print('stitching rasters')
                compressed_clipped_paths = [(re.sub('.tif', '_al_compress.tif', temp_path_1), 1),
                                            (re.sub('.tif', '_al_compress.tif', temp_path_2), 1)]
                
                resample_methods = ['bilinear', 'bilinear']

                pygeo.stitch_rasters(compressed_clipped_paths, resample_methods,
                                    target_stitch_raster_path_band=(stitched_path, 1))

                print('compressing stitched raster')
                compress_tifs(stitched_path)
