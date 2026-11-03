#!/bin/bash -l
# Usage: bash submit_all_countries.sh

# Folder with the country CSV files
CSV_DIR="/users/3/kula0049/urban-cooling/Data/urbanspatial-guppd-v1-gpkg"

# Countries to skip
SKIP_COUNTRIES=("USA" "RUS")

# Automatically list all *_smod_id.csv files, extract the country codes, convert to uppercase
mapfile -t COUNTRIES < <(
    ls "$CSV_DIR"/*_smod_id.csv \
    | xargs -n1 basename \
    | sed 's/_smod_id\.csv//' \
    | tr '[:lower:]' '[:upper:]'
)

# Remove skipped countries
for SKIP in "${SKIP_COUNTRIES[@]}"; do
    COUNTRIES=("${COUNTRIES[@]/$SKIP}")
done

# Sort in reverse alphabetical order
IFS=$'\n' COUNTRIES=($(sort -r <<<"${COUNTRIES[*]}"))
unset IFS

echo "Found ${#COUNTRIES[@]} countries to process."

# Submit one SLURM job per country
for COUNTRY in "${COUNTRIES[@]}"; do
    echo "Submitting job for $COUNTRY"
    sbatch urban_cooling_country.sh "$COUNTRY"
done
