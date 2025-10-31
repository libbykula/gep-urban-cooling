# Libby Kula
#  Global GEP Urban Cooling
# 07/14/2025

import logging
import numpy as np
import os
import pandas as pd
import geopandas as gpd

# set wd
inputdir = '/users/3/kula0049/urban-cooling/'

urbans_gdf = gpd.read_file(os.path.join(inputdir, 'Data/urbanspatial-guppd-v1-gpkg/urbanspatial-guppd-v1-gpkg.gpkg'))

arg_gdf = urbans_gdf[urbans_gdf['ISO'] == 'ARG']

arg_gdf['SMOD_ID'].to_csv(os.path.join(inputdir, 'Data/urbanspatial-guppd-v1-gpkg/arg_smod_id.csv'))