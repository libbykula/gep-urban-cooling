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
    files_list = []
    for year in year_list:
        for month in month_list:
            for scen in scenario_list:
                savings_path = os.path.join(output_dir, '0_buildings', c + '_' + year + '_' + month + '_' + scen + '_buildings.gpkg')

                files_list = files_list.append(savings_path)

    # Merging a geodataframe and pandas dataframe based on a column
    merged_gdf = spatial_df.merge(tab_df, on='common_id', how='left')

# list of file paths
files = [f"file_{i}.gpkg" for i in range(27)]

# read all GeoDataFrames
gdfs = [gpd.read_file(f) for f in files]

# ensure same CRS
gdfs = [gdf.to_crs(gdfs[0].crs) for gdf in gdfs]

# reduce with merge on key column
merged = reduce(
    lambda left, right: left.merge(right.drop(columns='geometry'),
                                    on='GEOID', how='outer'),
    gdfs
)

# keep geometry from first gdf
merged = gpd.GeoDataFrame(merged, geometry=gdfs[0].geometry, crs=gdfs[0].crs)
