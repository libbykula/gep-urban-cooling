import os, re, time, glob
import geopandas as gpd
import pandas as pd
from multiprocessing import Pool
import itertools
from collections import defaultdict


output_dir = '/projects/standard/jajohns/shared/Files/urban_cooling/workspace'
data_dir = '/projects/standard/jajohns/shared/Files/urban_cooling/base_data'

tract_dir = os.path.join(output_dir, '0_tract')

# folder_path = os.path.join(output_dir, '3_30_2026_all_nature')

# metro_list = [f for f in os.listdir(folder_path)
#            if os.path.isdir(os.path.join(folder_path, f))]
vector_gdf = gpd.read_file(os.path.join(data_dir, "Polygon_vectors/tl_2019_us_cbsa/metros_boundaries.gpkg"))
metro_list = vector_gdf['NAME'].unique().tolist()

metro_list.remove('Barnstable Town, MA')
metro_list.remove('Michigan City-La Porte, IN')

months = ['06', '07', '08']
# years = ['2001', '2011', '2021']
years = ['2021']
# scenarios = ['all', 'public', 'private']
scenarios = ['all', 'public']

merged = {}

for year in years:
    tracts_by_year_path = os.path.join(data_dir, 'Tract/combined_' + year + '.gpkg')
    tracts_by_year = gpd.read_file(tracts_by_year_path)

    base_gdf = tracts_by_year.copy()

    if year == '2001':
        base_gdf['GEOID'] = base_gdf['CTIDFP00'] 
    if year == '2011':
        base_gdf['GEOID'] = base_gdf['GEOID10']  

    base_gdf['GEOID'] = base_gdf['GEOID'].astype(str).str.zfill(11)

    for scen in scenarios:
        print(year, scen)
        dfs = []

        for c in metro_list:  # your 380 metro IDs
            for month in months:
                fname = f"{c}_{year}_{month}_{scen}_tract_energy_savings.csv"
                fpath = os.path.join(tract_dir, fname)

                if not os.path.exists(fpath):
                    continue

                df = pd.read_csv(fpath)
                # standardize column names
                if 'sum' in df.columns:
                    df = df.rename(columns={'sum': 'dollars_saved'})

                # enforce consistent schema
                if 'dollars_saved' not in df.columns:
                    raise ValueError(f"Missing expected column in {fpath}")
                
                # enforce join key consistency
                df['GEOID'] = df['GEOID'].astype(str).str.zfill(11)
                df['month'] = month
                df['c'] = c   # optional but VERY useful for debugging
                dfs.append(df)

        if not dfs:
            print(f"No data for {year}-{scen}")
            continue

        # stack everything (metros + months)
        combined = pd.concat(dfs, ignore_index=True)
        
        # check duplicates at GEOID + month level
        # dups = combined[combined.duplicated(['GEOID', 'month'], keep=False)]

        # example = dups.iloc[0]['GEOID']
        # month_ex = dups.iloc[0]['month']

        # print(combined[
        #     (combined['GEOID'] == example) &
        #     (combined['month'] == month_ex)
        # ][['GEOID', 'month', 'c']])

        combined['weight'] = 1 / combined.groupby(['GEOID', 'month'])['c'].transform('nunique')

        combined['total_dollars_saved'] = combined['dollars_saved'] * combined['weight']

        agg = combined.groupby('GEOID')['total_dollars_saved'].sum().reset_index()

        # merge onto correct-year geometry
        merged[(year, scen)] = base_gdf.merge(
            agg,
            on='GEOID',
            how='left'
        )

        merged[(year, scen)].to_file(os.path.join(output_dir, scen + '_tracts_' + year + '.gpkg'), driver="GPKG")