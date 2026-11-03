#!/bin/bash -l
# Usage: bash submit_nan_countries.sh

NANS_FILE="/users/3/kula0049/urban-cooling/nan_countries_rerun.csv"

if [[ ! -f "$NANS_FILE" ]]; then
    echo "ERROR: nans.csv not found at: '$NANS_FILE'"
    exit 1
fi

mapfile -t COUNTRIES < <(
    tr -d '\r' < "$NANS_FILE" \
    | cut -d',' -f1 \
    | tr '[:upper:]' '[:lower:]' \
    | grep -E '^[a-z]{3}$' \
    | sort -u
)

echo "Found ${#COUNTRIES[@]} countries to process."
printf 'First few: %s\n' "${COUNTRIES[@]:0:3}"

for COUNTRY in "${COUNTRIES[@]}"; do
    echo "Submitting job for $COUNTRY"
    sbatch urban_cooling_country.sh "$COUNTRY"
done