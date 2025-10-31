import pandas as pd
from pathlib import Path
import glob
import os 

inputdir = Path('/users/3/kula0049/urban-cooling/inputs/InVEST Results/cooling workspace')
input_folder = Path(os.path.join(inputdir, '8_14_2025'))
records = []

# for file in input_folder.glob('*.csv'):
#     try:
#         df = pd.read_csv(file, header=None)
#         if df.empty:
#             print(f'Skipping empty file: {file.name}')
#             continue
#         record = {}
#         for i in range(min(7, len(df))):  # avoid index errors
#             record[df.iloc[i, 0]] = df.iloc[i, 1]
#         records.append(record)
#     except pd.errors.EmptyDataError:
#         print(f'Skipping empty file (error): {file.name}')
#     except Exception as e:
#         print(f'Error reading {file.name}: {e}')

# combined_df = pd.DataFrame(records)

# combined_df.to_csv(
#     Path('/users/3/kula0049/urban-cooling/inputs/InVEST Results/cooling workspace/combined_metros_8_20_2025.csv'),
#     index=False
# )


# # --- Step 1: Get all folder names ---
# folders_1 = Path(r'C:/Users/kibby/OneDrive/Desktop/Research/DOI/Code/cooling workspace/3_16_2024_fixed_multistate')
# folders_2 = Path(r'C:/Users/kibby/OneDrive/Desktop/Research/DOI/Code/cooling workspace/11_21_2023_metros')

# # Only take subdirectories
# folder_names_1 = [f.name for f in folders_1.iterdir() if f.is_dir()]
# folder_names_2 = [f.name for f in folders_2.iterdir() if f.is_dir()]

# all_folder_names = set(folder_names_1 + folder_names_2)

# # --- Step 2: Load combined CSV and get unique metros ---
# combined_csv_path = Path(r'C:/Users/kibby/OneDrive/Desktop/Research/DOI/Code/cooling workspace/combined_metros.csv')
# df = pd.read_csv(combined_csv_path)

# # Make sure the column is named correctly
# if 'metro' not in df.columns:
#     raise ValueError(f''metro' column not found in CSV. Columns are: {df.columns.tolist()}')

# csv_metros = set(df['metro'].dropna().unique())

# # --- Step 3: Compare ---
# folders_not_in_csv = sorted(all_folder_names - csv_metros)
# metros_not_in_folders = sorted(csv_metros - all_folder_names)

# # --- Step 4: Output results ---
# print(f'Total unique folder names: {len(all_folder_names)}')
# print(f'Total unique metros in CSV: {len(csv_metros)}/n')

# print('Folders missing in CSV:')
# for name in folders_not_in_csv:
#     print('  ', name)

# print('/nCSV metros missing in folders:')
# for name in metros_not_in_folders:
#     print('  ', name)

####### WHICH TRACT SAVINGS ARE MISSING? ####
# # paths
# tract_dir = os.path.join(inputdir, '8_14_2025_tract_savings')
# combined_csv = os.path.join(inputdir, 'combined_metros_8_19_2025.csv') 

# # --- Step 1: parse filenames in tract_savings folder
# tract_files = os.listdir(tract_dir)

# # only keep .csv files in expected format
# triplets_from_files = set()
# for f in tract_files:
#     if f.endswith('_tract_energy_savings.csv'):
#         parts = f.replace('_tract_energy_savings.csv', '').split('_')
#         # metro might contain underscores itself, so year = -2, month = -1
#         year, month = parts[-2], parts[-1]
#         metro = '_'.join(parts[:-2])
#         triplets_from_files.add((metro, int(year), int(month)))

# # --- Step 2: load combined_metros reference
# df = pd.read_csv(combined_csv)

# triplets_from_combined = set(zip(df['metro'], df['year'], df['month']))

# # --- Step 3: find missing ones
# missing = triplets_from_combined - triplets_from_files

# print(f'Total in combined: {len(triplets_from_combined)}')
# print(f'Total from files: {len(triplets_from_files)}')
# print(f'Missing count: {len(missing)}')

# # Save missing list for inspection
# missing_df = pd.DataFrame(list(missing), columns=['metro', 'year', 'month'])
# missing_df = missing_df.sort_values(['metro', 'year', 'month'])
# missing_df.to_csv(os.path.join(inputdir, 'missing_metro_year_month.csv'), index=False)
# print('Missing triplets written to missing_metro_year_month.csv')

######## Concat all the tracts csvs #########
# folder path
folder = os.path.join(inputdir, '8_14_2025_tract_savings')

# get all matching CSV files
files = glob.glob(os.path.join(folder, '*_tract_energy_savings.csv'))

dfs = []
for f in files:
    # strip folder + suffix
    base = os.path.basename(f).replace('_tract_energy_savings.csv', '')
    # split: metro, year, month
    metro, year, month = base.split('_')
    
    df = pd.read_csv(f)
    df['metro'] = metro
    df['year'] = year
    df['month'] = month
    dfs.append(df)

# concatenate all into one DataFrame
all_df = pd.concat(dfs, ignore_index=True)

# reorder columns
all_df = all_df[['metro', 'year', 'month', 'GEOID', 'sum']]

# save to CSV
all_df.to_csv(os.path.join(inputdir, 'all_tract_energy_savings_8_21.csv'), index=False)