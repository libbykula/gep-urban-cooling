import numpy as np
import os
import pandas as pd
import geopandas as gpd

base_dir = "/users/3/kula0049/urban-cooling"

# first I just need a list of all the tracts 
for year in ['2001', '2011', '2021']:
    results = gpd.read_file(os.path.join(base_dir, 'results', f'cooling_nature_results_esi_6_12_26_{year}_nodups.gpkg')) # get all tracts

    results['GEOID'].to_csv(os.path.join(base_dir, f'tract_geoids_{year}.txt'), index=False, header=False)

