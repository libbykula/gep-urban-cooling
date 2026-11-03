import geopandas as gpd
import pandas as pd
import os

chunk_size = 100  # adjust as needed
base_dir = "/users/3/kula0049/urban-cooling"

# for year in ['2001', '2011', '2021']:
for year in ['2021']:
    results = gpd.read_file(os.path.join(base_dir, 'results', f'cooling_nature_results_esi_6_12_26_{year}_nodups.gpkg')) # get all tracts

    os.makedirs(f'tracts/{year}', exist_ok=True)
    geoids = results['GEOID'].tolist()
    chunks = [geoids[i:i+chunk_size] for i in range(0, len(geoids), chunk_size)]
    for i, chunk in enumerate(chunks):
        with open(f'tracts/{year}/chunk_{i+1}.txt', 'w') as f: # saving in scripts/tracts
            f.write('\n'.join(map(str, chunk)))
