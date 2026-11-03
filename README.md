# README GLOBAL GEP LOCAL CLIMATE MITIGATION 
To run all countries, use:
sbatch submit_all_countries.sh
which will run the code for all countries with lists of their urban areas (called SMOD_ID's in the GUPPD dataset) included in the CSV directory. 

To run one specific country, use:
sbatch urban_cooling_country.sh "$COUNTRY"
where $COUNTRY is a three-letter ISO3 abbreviation for the country of interest. 

This code will initiate the run file "run_gep_cooling_by_c_v02.py" for each urban area within a country in parallel. The run file initiates scripts/gep_fixing_cooling_valuation_v11.run_valuation_c(urban_area) to run the bulk of the work, and scripts/delete_files.delete_files_for_urban_area(urban_area) to save space on intermediate files. 

To concatenate the individual urban area results and save country-level summaries, run concat_by_country_from_smodlists_v02.py

Finally, to aggregate the data for Global GEP reporting, run saving_gep_summary.py


