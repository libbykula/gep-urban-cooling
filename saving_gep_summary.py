import os
import glob
import pandas as pd
import geopandas as gpd
from pyogrio import list_layers


BASE_DIR = "/users/3/kula0049/urban-cooling"
SUMMARY_DIR = os.path.join(BASE_DIR, "output", "valuations_12_19_2025", "summaries")
countries_path = os.path.join(BASE_DIR, "Data/cartographic/ee/ee_r250_correspondence.gpkg")

# 1. Read all summary CSVs and concatenate
summary_files = glob.glob(os.path.join(SUMMARY_DIR, "*_summary.csv"))
df_list = []

for f in summary_files:
    df = pd.read_csv(f)
    df_list.append(df)

summary_df = pd.concat(df_list, ignore_index=True)

# 2. Read geopackage (replace with correct layer name if needed)
# Choose the correct layer name from the list

# Read the geopackage, ignoring bad encodings
gdf = gpd.read_file(countries_path)

# 3. Merge on iso3_r250_label
merged = gdf.merge(summary_df, on="iso3_r250_label", how="left")

# 4. Keep only desired columns
final = merged[["iso3_r250_id", "iso3_r250_label", "iso3_r250_name", "local_climate_regulation"]]

# 5. Save to CSV
output_path = os.path.join(BASE_DIR, "output", "valuations_12_19_2025", "local_climate_regulation_gep_12_19_25.csv")
final.to_csv(output_path, index=False)

print(f"Saved merged CSV to: {output_path}")
