# run_fixing_cooling.py
import sys

from scripts import running_carbon
# inputdir = "/Users/sumilthakrar/UMN/Projects/landd2/pkg" # sumil local
# inputdir = "G:/Shared drives/NatCapTEEMs/Files/base_data/submissions/air_quality" # teems drive
inputdir = '/users/3/kula0049/urban-cooling/inputs/InVEST Results/carbon workspace/'

def main():
    running_carbon.run(inputdir)
    print("Completed.\n")


if __name__ == "__main__":
    main()