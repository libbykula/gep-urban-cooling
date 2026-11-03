import os
import geopandas as gpd
import pandas as pd
import re

output_dir = '/projects/standard/jajohns/shared/Files/urban_cooling/workspace'

year_list = ['2001', '2011', '2021']
month_list = ['06', '07', '08']
scenario_list = ['all', 'public', 'private']


def run(c):
    c_orig = c
    c = re.sub(r'\/', '-', c)

    base_geom = None
    dfs = []

    for year in year_list:
        for month in month_list:
            for scen in scenario_list:
                print(year, month, scen)
                path = os.path.join(
                    output_dir,
                    '0_buildings',
                    f"{c}_{year}_{month}_{scen}_buildings.gpkg"
                )

                # read only once per file
                gdf = gpd.read_file(path)

                gdf['fid'] = gdf.index.astype('int64')

                # store geometry once (assumes identical geometry/order)
                if base_geom is None:
                    base_geom = gdf[['fid', 'geometry']].copy()

                # drop geometry ASAP to save memory
                gdf = gdf.drop(columns='geometry')

                # create suffix
                suffix = f"{year}_{month}_{scen}"

                # rename columns except key
                gdf = gdf.rename(columns={
                    col: f"{col}_{suffix}"
                    for col in gdf.columns
                    if col != 'fid'
                })

                # set index for fast concat
                gdf = gdf.set_index('fid')

                dfs.append(gdf)

                # explicitly free memory
                del gdf

                os.remove(path)

    # 🔥 single concat (fast + memory efficient)
    merged_df = pd.concat(dfs, axis=1)

    # free list
    del dfs

    # restore geometry
    merged = base_geom.set_index('fid').join(merged_df)

    merged = gpd.GeoDataFrame(merged, geometry='geometry')

    result = merged.reset_index()

    result.to_parquet(
    f"{output_dir}/0_combined/{c}_buildings.parquet",
    compression="zstd"   # best balance of speed + size
    )

