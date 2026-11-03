#!/usr/bin/env python3
"""
concat_by_country_from_smodlists.py

For each <iso>_smod_id.csv produced by prep_countries.py, find valuation CSVs in:
    /users/3/kula0049/urban-cooling/output/valuation/
whose filename prefix (the SMOD_ID, e.g. "23_101" in "23_101_2019.csv")
matches an ID in the country's SMOD list.

Concatenate those CSVs, drop rows with non-positive valuation, detect a valuation column,
and save both a merged CSV and a one-row summary CSV with the summed valuation.

Usage:
    python concat_by_country_from_smodlists.py           # process all ISO SMOD lists found
    python concat_by_country_from_smodlists.py ABW       # process only ABW
"""

import os
import sys
import re
import glob
import pandas as pd

BASE_DIR = "/users/3/kula0049/urban-cooling"
SMOD_LIST_DIR = os.path.join(BASE_DIR, "Data", "urbanspatial-guppd-v1-gpkg")
VALUATION_DIR = os.path.join(BASE_DIR, "output", "valuation_10_12_2026")
OUT_SUMMARY_DIR = os.path.join(BASE_DIR, "output", "valuations_10_12_2026", "summaries")
OUT_MERGED_DIR = os.path.join(BASE_DIR, "output", "valuations_10_12_2026", "merged")

os.makedirs(OUT_SUMMARY_DIR, exist_ok=True)
os.makedirs(OUT_MERGED_DIR, exist_ok=True)


def read_smod_list(path):
    """
    Read the per-country SMOD ID CSV. The file may be a single-column CSV with or without header.
    Return a list of strings (SMOD IDs).
    """
    df = pd.read_csv(path, header=0)
    if "SMOD_ID" in df.columns:
        series = df["SMOD_ID"]
    else:
        series = df.iloc[:, 0]
    smod_ids = series.astype(str).str.strip().tolist()
    smod_ids = [s for s in smod_ids if s]
    return smod_ids


def detect_val_column(df):
    """
    Heuristic to detect valuation column in a DataFrame.
    Returns column name or raises ValueError.
    """
    for c in df.columns:
        lower = c.lower()
        if "climate" in lower or "valuation" in lower or (lower == "value") or ("val" in lower and "id" not in lower):
            return c
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if numeric_cols:
        sums = {c: df[c].abs().sum() for c in numeric_cols}
        return max(sums, key=sums.get)
    raise ValueError("Could not detect a valuation column.")


def extract_smod_id_from_filename(filename):
    """
    Extract SMOD_ID from valuation filename like '23_101_2019.csv' → '23_101'.
    """
    base = os.path.basename(filename)
    match = re.match(r"(\d+_\d+)_\d{4}\.csv$", base)
    if match:
        return match.group(1)
    return None


def process_country(iso):
    iso_lower = iso.lower()
    smod_csv = os.path.join(SMOD_LIST_DIR, f"{iso_lower}_smod_id.csv")
    summary_out = os.path.join(OUT_SUMMARY_DIR, f"{iso}_summary.csv")
    merged_out = os.path.join(OUT_MERGED_DIR, f"{iso}_all_urban_valuations.csv")

    # Remove stale outputs so a failed run can't leave old values behind
    for p in (summary_out, merged_out):
        if os.path.exists(p):
            os.remove(p)

    if not os.path.exists(smod_csv):
        print(f"⚠️ SMOD list not found for {iso}: {smod_csv}")
        return

    smod_set = set(read_smod_list(smod_csv))
    if not smod_set:
        print(f"⚠️ No SMOD IDs found in {smod_csv}")
        return

    # Match files, keeping the file -> ID mapping for debugging
    matched = {}
    for f in glob.glob(os.path.join(VALUATION_DIR, "*.csv")):
        sid = extract_smod_id_from_filename(f)
        if sid in smod_set:
            matched[f] = sid

    print(f"{iso}: {len(smod_set)} SMOD IDs in list, {len(matched)} files matched")
    print(f"  sample matches: {[os.path.basename(f) for f in list(matched)[:3]]}")

    dfs = []
    for f, sid in matched.items():
        try:
            df = pd.read_csv(f)
        except Exception as e:
            print(f"  - error reading {f}: {e}")
            continue
        if df.empty:
            continue
        df["source_file"] = os.path.basename(f)
        df["smod_id"] = sid
        dfs.append(df)

    if not dfs:
        print("⚠️ No valid dataframes to merge.")
        return

    merged = pd.concat(dfs, ignore_index=True, sort=False)

    # If the valuation files carry a country column, filter on it
    for col in ("iso3", "ISO3", "iso3_r250_label", "iso"):
        if col in merged.columns:
            print(f"  filtering on '{col}' == {iso}")
            merged = merged[merged[col].astype(str).str.upper() == iso.upper()]
            break
    else:
        print("  ⚠️ no ISO column in valuation files; cross-border IDs will be double counted")

    VAL_COL = "total_savings_usd"

    # --- Validate valuation column ---
    if VAL_COL not in merged.columns:
        print(f"❌ '{VAL_COL}' not in columns: {list(merged.columns)}")
        return
    val_col = VAL_COL

    # --- Filter ---
    merged[val_col] = pd.to_numeric(merged[val_col], errors="coerce")
    before_rows = len(merged)
    merged = merged[merged[val_col] > 0].copy()
    print(f"🧹 Filtered non-positive rows: {before_rows - len(merged)} removed, {len(merged)} remain")
    merged[val_col] = pd.to_numeric(merged[val_col], errors="coerce")
    merged = merged[merged[val_col] > 0].copy()

    merged.to_csv(merged_out, index=False)

    total_val = merged[val_col].sum()
    pd.DataFrame([{
        "iso3_r250_label": iso,
        "local_climate_regulation": f"${total_val:,.2f}",
    }]).to_csv(summary_out, index=False)
    print(f"✅ {iso}: {len(merged)} rows, total {total_val:,.2f}")


def main():
    cli_iso = sys.argv[1].upper() if len(sys.argv) > 1 else None

    if cli_iso:
        process_country(cli_iso)
        return

    pattern = os.path.join(SMOD_LIST_DIR, "*_smod_id.csv")
    files = glob.glob(pattern)
    if not files:
        print(f"⚠️ No per-country SMOD list CSVs found in {SMOD_LIST_DIR}. Run prep_countries.py first.")
        return

    isos = [os.path.basename(p).split("_", 1)[0].upper() for p in files]
    print(f"Found {len(isos)} SMOD lists: {', '.join(isos)}")

    for iso in isos:
        try:
            process_country(iso)
        except Exception as e:
            print(f"❌ Error processing {iso}: {e}")


if __name__ == "__main__":
    main()
