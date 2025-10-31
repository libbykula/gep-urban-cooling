# prep_countries.py
import os
import geopandas as gpd

inputdir = '/users/3/kula0049/urban-cooling/'
urbans_gdf = gpd.read_file(os.path.join(inputdir, 'Data/urbanspatial-guppd-v1-gpkg/urbanspatial-guppd-v1-gpkg.gpkg'))

# Get unique country ISO codes
countries = sorted(urbans_gdf['ISO'].unique())

outdir = os.path.join(inputdir, 'Data/urbanspatial-guppd-v1-gpkg/')
os.makedirs(outdir, exist_ok=True)

for iso in countries:
    sub = urbans_gdf[urbans_gdf['ISO'] == iso]
    csv_path = os.path.join(outdir, f"{iso.lower()}_smod_id.csv")
    sub['SMOD_ID'].to_csv(csv_path, index=False)
    print(f"Wrote {csv_path} ({len(sub)} urban areas)")
