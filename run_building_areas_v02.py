import sys, os
import geopandas as gpd
from concurrent.futures import ProcessPoolExecutor, as_completed
from scripts import buildings_api_v08_tract

chunk_file = sys.argv[1]
year = sys.argv[2]

with open(chunk_file) as f:
    tract_geoids = [line.strip() for line in f if line.strip()]

input_dir = '/users/3/kula0049/urban-cooling/Data'
tracts_gdf = gpd.read_file(f"/users/3/kula0049/urban-cooling/results/cooling_nature_results_esi_6_12_26_{year}_nodups.gpkg")
tracts_gdf = tracts_gdf[['GEOID', 'geometry']]
os.makedirs(os.path.join(input_dir, 'Polygon_vectors/tracts', year), exist_ok=True)
             
def process_tract(geoid):
    # create tract gpkg first 
    gdf = tracts_gdf[tracts_gdf['GEOID'] == int(geoid)]
    gdf_clean = gdf.drop_duplicates()
    gdf_clean = gdf_clean.to_crs('EPSG:4326')
    gdf_clean.to_file(os.path.join(input_dir, 'Polygon_vectors/tracts', year, geoid + '.gpkg'))
    
    buildings_api_v08_tract.buildings_api_get_total_area(geoid, year)
    return geoid

n_workers = int(os.environ.get('SLURM_CPUS_PER_TASK', 10))

with ProcessPoolExecutor(max_workers=n_workers) as executor:
    futures = {executor.submit(process_tract, geoid): geoid for geoid in tract_geoids}
    for future in as_completed(futures):
        geoid = futures[future]
        try:
            future.result()
        except Exception as e:
            print(f"ERROR on {geoid}: {e}")