import pandas as pd
import os
import geopandas as gpd
from functools import reduce


# Combine building results 
output_dir = '/projects/standard/jajohns/shared/Files/urban_cooling/workspace'

year_list = ['2001', '2011', '2021']
month_list = ['06', '07', '08']
scenario_list = ['all', 'public', 'private']

def run(c):       
    records = []

    for year in year_list:
        for month in month_list:
            for scen in scenario_list:
                savings_path = os.path.join(output_dir, '0_buildings', c + '_' + year + '_' + month + '_' + scen + '_buildings.gpkg')

                gdf = gpd.read_file(savings_path)

                gdf['year'] = year
                gdf['month'] = month
                gdf['scenario'] = scen

                records.append(gdf)

    long_gdf = pd.concat(records, ignore_index=True)
