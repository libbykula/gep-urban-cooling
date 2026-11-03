import os, re, time, glob
import geopandas as gpd
from multiprocessing import Pool
import itertools


output_dir = '/projects/standard/jajohns/shared/Files/urban_cooling/workspace'
data_dir = '/projects/standard/jajohns/shared/Files/urban_cooling/base_data'

tract_dir = os.path.join(output_dir, '0_tract')
os.makedirs(tract_dir, exist_ok=True)

months = ['06', '07', '08']
years = ['2001', '2011', '2021']
scenarios = ['all', 'public', 'private']

combos = list(itertools.product(years, months, scenarios))

# Getting metro_list
folder_path = os.path.join(output_dir, '3_30_2026_all_nature')

metro_list = [f for f in os.listdir(folder_path)
           if os.path.isdir(os.path.join(folder_path, f))]

def run(c):
    c_orig = c
    c = re.sub(r'\/', '-', c)

    args_list = [
        (c, c_orig, year, month, scen)
        for year, month, scen in combos
    ]
    
    n_procs = int(os.environ.get("SLURM_CPUS_PER_TASK", 27))
    with Pool(processes=n_procs) as pool:
        pool.map(summ_cooling_sav_tract, args_list)

    for args in args_list:
        c, c_orig, year, month, scen = args
        out_path = os.path.join(tract_dir, f"{c}_{year}_{month}_{scen}_tract_energy_savings.csv")
        if os.path.exists(out_path):
            print('done already')
        else:
            summ_cooling_sav_tract(args)

def summ_cooling_sav_tract(args):
    c, c_orig, year, month, scen = args
    out_path = os.path.join(tract_dir, f"{c}_{year}_{month}_{scen}_tract_energy_savings.csv")
    
    if os.path.exists(out_path):
        return
    else:
        t = time.localtime()
        print(f"[{time.strftime('%H:%M:%S', t)}] Processing {c} {year}-{month}")

        last_year = str(int(year) - 1)
        tract_path = os.path.join(data_dir, f'Tract/{last_year}/{c}_valid_v02.gpkg')
        if not os.path.exists(tract_path):
            print(f"Missing tract file: {tract_path}")
            return

        tract_gdf = gpd.read_file(tract_path).to_crs('EPSG:4326')

        if year == '2001':
            tract_gdf['GEOID'] = tract_gdf['CTIDFP00']
        elif year == '2011':
            tract_gdf['GEOID'] = tract_gdf['GEOID10']

        # savings_path = os.path.join(output_dir, '0_buildings', c + '_' + year + '_' + month + '_' + scen + '_buildings.parquet')
        combined_path = os.path.join(output_dir, '0_combined', c + '_buildings.parquet')

        # ok now I need to read just the ones for the given year + month + scen 

        col_name = f'dollars_saved_{year}_{month}_{scen}'

        # Read only needed columns (faster!)
        savings_data = gpd.read_parquet(
            combined_path,
            columns=['geometry', col_name]
        ).to_crs('EPSG:4326')

        # Drop rows with missing values in that column (important!)
        savings_data = savings_data.dropna(subset=[col_name])

        tract_gdf = tract_gdf[tract_gdf.geometry.is_valid]

        joined_gdf = gpd.sjoin(
            savings_data,
            tract_gdf,
            how='right',
            predicate="within"
        )

        # Use dynamic column name here
        summary_stats = (
            joined_gdf
            .groupby('GEOID')[col_name]
            .sum()
            .reset_index()
            .rename(columns={col_name: 'dollars_saved'})
        )

        summary_stats.to_csv(out_path, index=False)
        print(f"Saved {out_path}")

# run_all()
for c in metro_list:
    run(c)
