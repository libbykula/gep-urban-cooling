import pygeoprocessing as pygeo
import pygeoprocessing.kernels
from osgeo import gdal
import os
import re
import shutil


inputdir = '/users/3/kula0049/urban-cooling/output'
metros_dir = '/users/3/kula0049/urban-cooling/inputs/metro_boundaries/Metros/'

# clipped_path = 'inputs/InVEST Results/cooling workspace/clipped/' + c + '_' + year + '_' + month + '_compress.tif
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

# def clip_to_urban(ras, c):
#     raster_dataset = gdal.Open(ras)
#     if os.path.exists(re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras)) == 0:
#         gdal.Warp(
#         destNameOrDestDS=re.sub(r'\.(.*?)$', r'_clipped_{}.\1'.format(c), ras),
#         srcDSOrSrcDSTab=raster_dataset,
#         cutlineDSName=os.path.join(metros_dir, c + '_nad83.shp'),
#         cropToCutline=True,
#         dstSRS='EPSG:54009',     # Ensures consistent CRS, Mollweide
#         xRes=30, yRes=30        # Forces output resolution
#     )

def add_air_mixing(c):
    for year in ['2019']:

        month_list = [f'{i:02}' for i in range(1, 13)]
        for month in month_list:
            if os.path.exists(os.path.join(inputdir, 'mixed_output/hm_' + c + '_' + year + '_' + month + '_mixed_compress.tif')) == 0:
                tempdir = os.path.join(inputdir, 'temp/')
                os.makedirs(tempdir, exist_ok=True)  # creates the folder and parents if needed
                os.makedirs(os.path.join(inputdir, 'mixed_output/'), exist_ok=True)  

                signal_raster_path = os.path.join(inputdir, 'invest_results/' + c + '/hm_' + c + '_' + year + '_' + month + '.tif')
                exponential_kernel_path = os.path.join(tempdir, 'exponential_kernel.tif')
                target_convolve_raster_path = os.path.join(inputdir, 'mixed_output/hm_'+ c + '_' + year + '_' + month + '_mixed.tif')
                decay_kernel_distance = 600

                if os.path.exists(exponential_kernel_path) == 0:
                    pygeo.kernels.exponential_decay_kernel(
                            target_kernel_path=exponential_kernel_path,
                            max_distance=decay_kernel_distance * 5,
                            expected_distance=decay_kernel_distance)
                    print('made exponential raster')
                else:
                    print('exponential raster exists')
                pygeo.convolve_2d((signal_raster_path, 1), (exponential_kernel_path, 1),
                        target_convolve_raster_path, working_dir=tempdir,
                        ignore_nodata_and_edges=True)
                print('convolved')
                compress_tifs(target_convolve_raster_path)
                print('done!')

                os.remove(signal_raster_path)
                # shutil.rmtree(tempdir)