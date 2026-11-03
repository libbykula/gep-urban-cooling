import glob
import os

base_dir = '/projects/standard/jajohns/shared/Files/urban_cooling/workspace/0_combined'
code_dir = '/users/3/kula0049/urban-cooling/'

paths = glob.glob(os.path.join(base_dir, '*_buildings.parquet'))


# Extract the 'c' part
done_list = [
    os.path.basename(p).replace('_buildings.parquet', '')
    for p in paths
]
# print(done_list)

output_file = os.path.join(code_dir, 'done_list.txt')

with open(output_file, 'w') as f:
    f.write('\n'.join(done_list))
