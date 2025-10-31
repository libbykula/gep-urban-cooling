import pandas as pd
from pathlib import Path

# Folder containing your CSVs
folder = Path("/users/3/kula0049/urban-cooling/output/valuation")

# List all CSVs that look like "22_82.csv"
csv_files = sorted(folder.glob("*.csv"))

# Read and concatenate
dfs = []
for f in csv_files:
    try:
        df = pd.read_csv(f)
        dfs.append(df)
    except Exception as e:
        print(f"⚠️ Skipping {f.name} due to error: {e}")

# Combine all dataframes
combined = pd.concat(dfs, ignore_index=True)

# Save the combined CSV
out_path = folder / "0_ARG_valuation_results.csv"
combined.to_csv(out_path, index=False)

print(f"✅ Combined {len(dfs)} files into {out_path}")
print(f"Total rows: {len(combined):,}")
