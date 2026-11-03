#!/bin/bash -l
# Usage: bash submit_all_countries.sh

# Folder with the country CSV files
CSV_DIR="/users/3/kula0049/urban-cooling/Data/urbanspatial-guppd-v1-gpkg"

# Automatically list all *_smod_id.csv files and extract the country codes
mapfile -t COUNTRIES < <(ls "$CSV_DIR"/*_smod_id.csv | xargs -n1 basename | sed 's/_smod_id\.csv//' | tr '[:lower:]' '[:upper:]')

echo "Found ${#COUNTRIES[@]} countries to process."

# Submit one SLURM job per country
for COUNTRY in "${COUNTRIES[@]}"; do
    echo "Submitting job for $COUNTRY"
    sbatch urban_cooling_country.sh "$COUNTRY"
done
