# run_fixing_cooling.py
import sys
import os

from scripts import gep_run_urban_cooling_by_c
# from scripts import gep_urban_cooling_stitch_temps
# from scripts import gep_urban_cooling_v02
from scripts import hm_air_mixing
from scripts import gep_fixing_cooling_valuation_v07
from scripts import delete_files


# Stitching temperature rasters together for each month
# def main():
#     gep_urban_cooling_stitch_temps.run() # wait, i should parallelize over the months? No, pretty quick. 
#     print("Completed.\n")

# Running the urban cooling model, first calculating UHI and rural reference temp
def process_urban_area(urban_area):
    # print(f"Calculating UHI & rural ref for Urban InVEST cooling for {urban_area}")
    # gep_run_urban_cooling_by_c.calculate_uhi(urban_area)
    # print("Completed.\n")

    if os.path.exists(f"/users/3/kula0049/urban-cooling/output/valuation_12_17_2025/{urban_area}_2019.csv") ==0:
        # try:
        # print(f"Running Urban InVEST cooling for {urban_area}")
        # gep_run_urban_cooling_by_c.prep_and_run_cooling(urban_area)
        # print("Completed prep and run cooling.\n")

        # print(f"Running heat mitigation air mixing for {urban_area}")
        # hm_air_mixing.add_air_mixing(urban_area)
        # print("Completed air mixing.\n")

        # if urban_area != '30_207':
        print(f"Running valuation for {urban_area}")
        gep_fixing_cooling_valuation_v07.run_valuation_c(urban_area)
        print("Completed valuation.\n")

        print(f"Deleting unnecessary files for {urban_area}")
        delete_files.delete_files_for_urban_area(urban_area)
        print("Completed deletion of unnecessary files.\n")

        # except Exception as e:
        #     print("ERROR:", e)
        #     delete_files.delete_files_for_urban_area(urban_area)
    else:
        print('already done')

if __name__ == "__main__":
    urban_area = sys.argv[1]
    process_urban_area(urban_area) 
