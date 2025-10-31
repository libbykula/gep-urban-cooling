import re
import os
import time
import geopandas as gpd

from multiprocessing import Pool
import os
import itertools

months = ['06', '07', '08']
years = ['2001', '2011', '2021']

combos = list(itertools.product(years, months))

inputdir = '/users/3/kula0049/urban-cooling'

def run(c):
    if c == 'Louisville-Jefferson County, KY-IN':
        c = 'Louisville/Jefferson County, KY-IN'
    c_orig = c
    c = re.sub(r'\/', '-', c)  # path-safe version

    # Prepare argument list for multiprocessing
    args_list = [
        (c, c_orig, year, month)
        for year, month in combos
    ]

    n_procs = int(os.environ.get("SLURM_CPUS_PER_TASK", 9))
    with Pool(processes=n_procs) as pool:
        pool.map(summ_cooling_sav_tract, args_list)

    for args in args_list:
        c, _, year, month = args
        savings_path = os.path.join(
            inputdir, 'inputs/InVEST Results/cooling workspace/8_14_2025_building_savings',
            f"{c}_{year}_{month}_buildings.gpkg"
        )
        if os.path.exists(savings_path):
            os.remove(savings_path)

def summ_cooling_sav_tract(args):
    c, c_orig, year, month = args

    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)
    print(current_time)
    
    for year in ['2001', '2011', '2021']:
        last_year = str(int(year) -1)

        tract_gdf = gpd.GeoDataFrame(gpd.read_file(os.path.join(inputdir,'Data/Tract/' + last_year + '/' + c + '_valid_v02.gpkg')))
        tract_gdf = tract_gdf.to_crs('EPSG:4326')

        if year == '2001':
            tract_gdf['GEOID'] = tract_gdf['CTIDFP00'] 
        if year == '2011':
            tract_gdf['GEOID'] = tract_gdf['GEOID10']       

        for month in ['06', '07', '08']:
            savings_path = os.path.join(inputdir, 'inputs/InVEST Results/cooling workspace/8_14_2025_building_savings/' + c + '_' + year + '_' + month + '_buildings.gpkg')

            if os.path.exists(savings_path):
                savings_data = gpd.GeoDataFrame(gpd.read_file(savings_path))
                savings_data = savings_data.to_crs('EPSG:4326')

                tract_gdf = tract_gdf[tract_gdf.geometry.is_valid]
                
                joined_gdf = gpd.sjoin( 
                    savings_data, 
                    tract_gdf, 
                    how='right',
                    predicate="within",
                )
                
                summary_stats = joined_gdf.groupby('GEOID')['dollars_saved'].agg(['sum']).reset_index()
                summary_stats.to_csv(os.path.join(inputdir, 'inputs/InVEST Results/cooling workspace/8_14_2025_tract_savings/' + c + '_' + year + '_' + month + '_tract_energy_savings.csv'))
