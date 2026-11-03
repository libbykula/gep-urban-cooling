# run_fixing_cooling.py            # print(f"Deleting unnecessary files for {urban_area}")
            # delete_files.delete_files_for_urban_area(urban_area)
            # print("Completed deletion of unnecessary files.\n")
import sys
import os

from scripts import gep_run_urban_cooling_by_c_v04
from scripts import hm_air_mixing
from scripts import gep_fixing_cooling_valuation_v11
from scripts import delete_files


def process_urban_area(urban_area):

    # if os.path.exists(f"/users/3/kula0049/urban-cooling/output/valuation_10_12_2026/{urban_area}_2019.csv") ==0:
        # try:
    print(f"Running valuation for {urban_area}")
    gep_fixing_cooling_valuation_v11.run_valuation_c(urban_area)
    print("Completed valuation.\n")

    print(f"Deleting unnecessary files for {urban_area}")
    delete_files.delete_files_for_urban_area(urban_area)
    print("Completed deletion of unnecessary files.\n")

    #     except Exception as e:
    #         print("ERROR:", e)
    #         delete_files.delete_files_for_urban_area(urban_area)
    # else:
    #     delete_files.delete_files_for_urban_area(urban_area)
    #     print('already done')

if __name__ == "__main__":
    urban_area = sys.argv[1]
    process_urban_area(urban_area) 

# process_urban_area('23_29220')