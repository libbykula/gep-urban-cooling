import os
import sys
import pandas as pd
import geopandas as gpd
import glob

def concat_and_summarize(
    country_iso: str,
    base_dir: str = "/users/3/kula0049/urban-cooling",
    gpkg_path: str = "Data/urbanspatial-guppd-v1-gpkg/urbanspatial-guppd-v1-gpkg.gpkg"
):
    """
    Concatenate all valuation CSVs for a given country (ISO code),
    exclude negative values, and compute total valuation.
    Automatically pulls country metadata (id, name) from the geopackage.
    """
    country_iso = country_iso.upper()
    valuation_dir = os.path.join(base_dir, "output", "valuation")
    out_dir = os.path.join(base_dir, "output", "valuations", "summaries")
    os.makedirs(out_dir, exist_ok=True)

    # --- Load metadata from geopackage ---
    gdf_path = os.path.join(base_dir, gpkg_path)
    print(f"🔍 Reading country metadata from {gdf_path} ...")
    urbans_gdf = gpd.read_file(gdf_path)

    # Drop duplicates (one record per country)
    meta_df = urbans_gdf.drop_duplicates(subset="ISO")

    # Lookup ID and name
    row = meta_df.loc[meta_df["ISO"] == country_iso]
    if row.empty:
        raise ValueError(f"Country {country_iso} not found in {gdf_path}")

    iso_id = row["iso3_r250_id"].iloc[0] if "iso3_r250_id" in row.columns else ""
    iso_name = row["iso3_r250_name"].iloc[0] if "iso3_r250_name" in row.columns else country_iso

    print(f"✅ Found metadata: {iso_id} | {country_iso} | {iso_name}")

    # --- Filter urban areas for this country ---
    country_SMOD_IDs = urbans_gdf.loc[urbans_gdf["ISO"] == country_iso, "SMOD_ID"].astype(str).tolist()

    # --- Find all CSVs that match the country's urban IDs ---
    all_files = glob.glob(os.path.join(valuation_dir, "*.csv"))
    files = [f for f in all_files if os.path.basename(f).split("_")[0] in country_SMOD_IDs]

    if not files:
        print(f"⚠️ No valuation files found for {country_iso} in {valuation_dir}")
        return

    print(f"🧩 Found {len(files)} valuation CSVs for {country_iso}")

    # --- Concatenate all urban-level valuation CSVs ---
    dfs = []
    for f in files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f"⚠️ Skipping {f}: {e}")

    if not dfs:
        print("⚠️ No valid dataframes to merge.")
        return

    merged = pd.concat(dfs, ignore_index=True)

    # --- Detect valuation column ---
    val_col = None
    for c in merged.columns:
        if "climate" in c.lower() or "valuation" in c.lower() or "value" in c.lower():
            val_col = c
            break

    if val_col is None:
        raise ValueError("Could not find a valuation column in the CSVs.")

    # --- Filter out negative values ---
    merged = merged[merged[val_col] > 0]

    # --- Save merged CSV ---
    concat_out = os.path.join(out_dir, f"{country_iso}_all_urban_valuations_11_06_25.csv")
    merged.to_csv(concat_out, index=False)
    print(f"✅ Saved merged CSV: {concat_out}")

    # --- Compute total valuation ---
    total_val = merged[val_col].sum()

    # --- Save summary CSV ---
    summary_df = pd.DataFrame([{
        "iso3_r250_id": iso_id,
        "iso3_r250_label": country_iso,
        "iso3_r250_name": iso_name,
        "local_climate_regulation": f"${total_val:,.2f}"
    }])

    summary_out = os.path.join(out_dir, f"{country_iso}_summary_11_06_25.csv")
    summary_df.to_csv(summary_out, index=False)
    print(f"✅ Saved summary CSV: {summary_out}")
    print(summary_df)

    # --- delete all SMOD_ID level CSVs for this country now that we are done ---
    print(f"🧹 Deleting {len(files)} SMOD_ID CSVs for {country_iso} ...")
    for f in files:
        try:
            os.remove(f)
        except Exception as e:
            print(f"⚠️ could not delete {f}: {e}")
    print("✅ cleanup complete.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python concat_country_results.py <ISO3>")
        sys.exit(1)

    iso = sys.argv[1]
    concat_and_summarize(iso)
