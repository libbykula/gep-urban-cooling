# run_fixing_cooling.py
import sys

from scripts import fixing_cooling_valuation_multistate
# inputdir = "/Users/sumilthakrar/UMN/Projects/landd2/pkg" # sumil local
# inputdir = "G:/Shared drives/NatCapTEEMs/Files/base_data/submissions/air_quality" # teems drive
inputdir = "urban-cooling"

def process_metro(metro_area):
    # Your processing logic here
    print(f"Processing {metro_area}")
    fixing_cooling_valuation_multistate.run_fixing_cooling(metro_area)
    print("Completed.\n")


if __name__ == "__main__":
    metro = sys.argv[1]
    process_metro(metro)