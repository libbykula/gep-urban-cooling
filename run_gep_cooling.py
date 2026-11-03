# run_fixing_cooling.py
import sys

from scripts import gep_run_urban_cooling_v03
# from scripts import gep_urban_cooling_stitch_temps
# from scripts import gep_urban_cooling_v02

# inputdir = '/users/3/kula0049/urban-cooling/inputs/InVEST Results/carbon workspace/'

# Stitching temperature rasters together for each month
# def main():
#     gep_urban_cooling_stitch_temps.run() # wait, i should parallelize over the months? No, pretty quick. 
#     print("Completed.\n")

# Running the urban cooling model, first calculating UHI and rural reference temp
def main():
    gep_run_urban_cooling_v03.run()
    print("Completed.\n")   

if __name__ == "__main__":
    main()