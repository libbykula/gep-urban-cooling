import os 
import pandas as pd

user_dir = '/users/3/kula0049/urban-cooling'
output_dir = '/projects/standard/jajohns/shared/Files/urban_cooling/workspace'

years = ['2001', '2011', '2021']
months = ['06', '07', '08']
scenarios = ['all', 'public', 'private']

with open(os.path.join(user_dir, "some_metros.txt"), "r") as f:
    metro_list = [line.strip() for line in f]

for c in metro_list:
    for year in years:
        for month in months:
            for scen in scenarios:
                intermediate_folder = os.path.join(output_dir, '3_30_2026_' + scen + '_nature', c, year, month, 'intermediate') 
                keep_files_contain = 'T_air_' + c + '_' + year + '_' + month + '.tif'

                for filename in os.listdir(intermediate_folder):
                    file_path = os.path.join(intermediate_folder, filename)
                    if os.path.isfile(file_path) and keep_files_contain not in filename:
                        os.remove(file_path)