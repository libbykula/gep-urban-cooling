import subprocess
import fiona
import os
from tqdm import tqdm
import re
from osgeo import gdal

# raster_path = r"/users/8/boxxx032/lulc_glc_fcs30d_2019.tif"
# shapefile_path = r"/users/8/boxxx032/country_shape/global_country_sel1.shp"
# output_dir = r"/users/8/boxxx032/clipped_by_country"

# raster_path = r"/users/3/kula0049/urban-cooling/Data/lulc_glc_fcs30d_2019.tif"
# shapefile_path = r"/users/3/kula0049/urban-cooling/Data/global_country_235/global_country_235.shp"
# shapefile_path = r"/users/3/kula0049/urban-cooling/Data/global_country_235/contig_235.gpkg"
output_dir = r"/users/3/kula0049/urban-cooling/Data/clipped_by_country_v02"

# # Create output directory if not exists
# os.makedirs(output_dir, exist_ok=True)

# # Load shapefile
# with fiona.open(shapefile_path, "r") as shapefile:
#     crs = shapefile.crs
#     for i, feature in enumerate(tqdm(shapefile, desc="Clipping with gdalwarp")):
#         # Try to extract unique ID
#         try:
#             raw_id = feature["properties"]["ee_r264_id"]
#             name_clean = str(int(float(raw_id)))  # remove .0 if float
#         except Exception:
#             name_clean = f"poly_{i}"

#         # Create temporary single-feature shapefile
#         temp_shp_dir = os.path.join(output_dir, f"_temp_{name_clean}")
#         os.makedirs(temp_shp_dir, exist_ok=True)
#         temp_shp_path = os.path.join(temp_shp_dir, f"{name_clean}.shp")

#         # Write single polygon to temp shapefile
#         schema = shapefile.schema
#         with fiona.open(temp_shp_path, 'w', driver='ESRI Shapefile', crs=crs, schema=schema) as temp:
#             temp.write(feature)

#         # Output raster path
#         output_path = os.path.join(output_dir, f"{name_clean}.tif")

#         # gdalwarp command
#         cmd = [
#             "gdalwarp",
#             "-cutline", temp_shp_path,
#             "-crop_to_cutline",
#             "-of", "GTiff",
#             "-dstalpha",  # optional: adds alpha band
#             "-overwrite",
#             "-multi", "-wo", "NUM_THREADS=ALL_CPUS",  # multithreading
#             raster_path,
#             output_path
#         ]

#         # Run gdalwarp
#         try:
#             subprocess.run(cmd, check=True)
#         except subprocess.CalledProcessError as e:
#             print(f"Failed to clip {name_clean}: {e}")

#         # Clean up temp shapefile (optional)
#         for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
#             try:
#                 os.remove(os.path.join(temp_shp_dir, f"{name_clean}{ext}"))
#             except FileNotFoundError:
#                 pass
#         try:
#             os.rmdir(temp_shp_dir)
#         except OSError:
#             pass

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

compress_tifs(os.path.join(output_dir, "235.tif"))