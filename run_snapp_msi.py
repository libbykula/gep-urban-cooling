import sys

from scripts import metros_running_invest_code_v27_snapp_msi
from scripts import fixing_cooling_valuation_v05_snapp_msi 
from scripts import summ_cool_tract_v03_snapp
from scripts import combine_building_results_v04
from scripts import summ_cool_tract_v04_snapp

def process_metro(c):
    print('Running Urban Cooling InVEST for ', c)
    metros_running_invest_code_v27_snapp_msi.run(c)
    print('Completed Urban Cooling InVEST for ', c)   

    print('Running valuation for ', c)
    fixing_cooling_valuation_v05_snapp_msi.run(c)
    print('Completed valuation for ', c)

    print('Running tract-level results for ', c)
    summ_cool_tract_v03_snapp.run(c)
    print('Completed tract-level results for ', c)

# if __name__ == "__main__":
#     c = sys.argv[1]
#     process_metro(c) 
metro_list = ['Atlanta-Sandy Springs-Alpharetta, GA', 
            'Augusta-Richmond County, GA-SC'
]
# metro_list = ['Dallas-Fort Worth-Arlington, TX']

for c in metro_list:
    process_metro(c)