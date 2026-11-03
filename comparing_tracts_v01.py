import os
import pandas as pd
import geopandas as gpd

jajohns_dir = '/projects/standard/jajohns/shared/Files/urban_cooling/'
user_dir = '/users/3/kula0049/urban-cooling/'

jajohns_folder = os.path.join(jajohns_dir, 'workspace/0_tract') # only want the ones with "_all_" in the title
user_folder = os.path.join(user_dir, 'inputs/InVEST Results/cooling workspace/8_14_2025_tract_savings')

# print('hello?')
def parse_filename(fname, is_all):
    parts = fname.replace(".csv", "").split("_")
    c = parts[0]
    year = parts[1]
    month = parts[2]
    return c, year, month

def load_csv(path):
    df = pd.read_csv(path)

    # Drop unnamed index columns
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]

    # Standardize column names
    if "sum" in df.columns:
        df = df.rename(columns={"sum": "dollars_saved"})

    # Ensure GEOID is string
    df["GEOID"] = df["GEOID"].astype(str)

    return df

results = []

files_a = [
    f for f in os.listdir(jajohns_folder)
    if f.endswith(".csv") and "_all_tract_energy_savings" in f
]

for fa in files_a:
    c, year, month = parse_filename(fa, is_all=True)

    fb = f"{c}_{year}_{month}_tract_energy_savings.csv"
    path_a = os.path.join(jajohns_folder, fa)
    path_b = os.path.join(user_folder, fb)

    if not os.path.exists(path_b):
        print(f"Missing in B: {fb}")
        continue

    df_a = load_csv(path_a)
    df_b = load_csv(path_b)

    merged = df_a.merge(df_b, on="GEOID", how="outer", suffixes=("_a", "_b"), indicator=True)

    missing_in_a = merged[merged["_merge"] == "right_only"]
    missing_in_b = merged[merged["_merge"] == "left_only"]

    # Value comparison
    # Compute difference
    merged["diff"] = merged["dollars_saved_a"] - merged["dollars_saved_b"]
    merged["abs_diff"] = merged["diff"].abs()

    # Treat NaNs as 0 for this check (optional, but usually helpful)
    merged["a"] = merged["dollars_saved_a"].fillna(0)
    merged["b"] = merged["dollars_saved_b"].fillna(0)

    # Exact zero mismatches
    a_zero_b_nonzero = merged[(merged["a"] == 0) & (merged["b"] != 0)]
    b_zero_a_nonzero = merged[(merged["b"] == 0) & (merged["a"] != 0)]

    # Counts
    n_a_zero_b_nonzero = len(a_zero_b_nonzero)
    n_b_zero_a_nonzero = len(b_zero_a_nonzero)

    # --- GEOID with max difference ---
    if not merged["abs_diff"].isna().all():
        max_idx = merged["abs_diff"].idxmax()
        max_geoid = merged.loc[max_idx, "GEOID"]
        max_diff = merged.loc[max_idx, "abs_diff"]
    else:
        max_geoid = None
        max_diff = None

    # --- Correlation (only on overlapping rows) ---
    overlap = merged.dropna(subset=["dollars_saved_a", "dollars_saved_b"])

    if len(overlap) > 1:
        corr = overlap["dollars_saved_a"].corr(overlap["dollars_saved_b"])
    else:
        corr = None


    results.append({
        "file": fa,
        "n_a": len(df_a),
        "n_b": len(df_b),
        "missing_in_a": len(missing_in_a),
        "missing_in_b": len(missing_in_b),
        "a_zero_b_nonzero": n_a_zero_b_nonzero,
        "b_zero_a_nonzero": n_b_zero_a_nonzero,
        "mean_diff": merged["diff"].mean(),
        "max_abs_diff": max_diff,
        "max_diff_geoid": max_geoid,
        "correlation": corr
    })

    # Optional: save mismatches
    if len(missing_in_a) or len(missing_in_b):
        merged.to_csv(f"diff_{c}_{year}_{month}.csv", index=False)

summary = pd.DataFrame(results)
summary.to_csv(os.path.join(jajohns_dir, "comparing_tracts_5_15.csv"), index=False)

print(summary)