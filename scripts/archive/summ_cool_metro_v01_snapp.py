import pandas as pd
import glob
import os


output_dir = '/projects/standard/jajohns/shared/Files/urban_cooling/workspace'
data_dir = '/projects/standard/jajohns/shared/Files/urban_cooling/base_data'

folder = os.path.join(output_dir, '0_valuation')
files = glob.glob(os.path.join(folder, "*.csv"))

all_data = []

for f in files:
    # --- extract metadata from filename ---
    base = os.path.basename(f)
    name = base.replace(".csv", "")
    
    # example: all_Abilene, TX_2001_06_all
    parts = name.split("_")
    
    scen = parts[0]
    year = parts[-3]
    month = parts[-2]
    
    # metro may contain underscores because of comma + space issues
    metro = "_".join(parts[1:-3]).replace(",", "").strip()
    
    # --- read key-value csv ---
    df = pd.read_csv(f, header=None, names=["key", "value"])
    
    # pivot to single row
    row = df.set_index("key")["value"].to_dict()
    
    # add metadata from filename
    row["scenario"] = scen
    row["metro"] = metro
    row["year"] = int(year)
    row["month"] = int(month)
    
    all_data.append(row)

# combine everything
final_df = pd.DataFrame(all_data)

# optional: reorder columns nicely
cols = ["scenario", "metro", "year", "month"] + [
    c for c in final_df.columns if c not in ["scenario", "metro", "year", "month"]
]
final_df = final_df[cols]

# save
final_df.to_excel(os.path.join(output_dir, "combined_valuation.xlsx"), index=False)

