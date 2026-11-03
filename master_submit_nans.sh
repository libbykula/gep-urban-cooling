#!/bin/bash
# master_submit_nans.sh

DATADIR="/users/3/kula0049/urban-cooling/Data/urbanspatial-guppd-v1-gpkg"
NANSFILE="/users/3/kula0049/urban-cooling/nans.csv"   # adjust if nans.csv lives elsewhere
RUNSCRIPT="run_urban_cooling_country.sbatch"
SUMMARYSCRIPT="concat_country_summary.sbatch"

# Read ISO3 codes: first column, strip CR/quotes/whitespace, uppercase
while IFS=, read -r iso3 _; do
    COUNTRY=$(echo "$iso3" | tr -d '\r"[:space:]' | tr '[:lower:]' '[:upper:]')

    # Skip blanks and the header row (anything not exactly 3 letters)
    [[ "$COUNTRY" =~ ^[A-Z]{3}$ ]] || continue

    # Make sure the input file for this country exists
    csv="${DATADIR}/${COUNTRY}_smod_id.csv"
    if [[ ! -f "$csv" ]]; then
        echo "⚠️  ${csv} not found, skipping ${COUNTRY}"
        continue
    fi

    # quota sanity guard (check scratch)
    CURR_USAGE=$(df -h /scratch.global/$USER | awk 'NR==2 {gsub("%","",$5); print $5}')
    MAX_ALLOWED=80
    if (( CURR_USAGE > MAX_ALLOWED )); then
        echo "❌ Storage too full (${CURR_USAGE}%). Stopping submissions."
        exit 1
    fi

    echo "Submitting ${COUNTRY} ..."

    # one job per country - NO ARRAY
    JOB_ID=$(sbatch --parsable "$RUNSCRIPT" "$COUNTRY")
    echo "Submitted run job ${JOB_ID} for ${COUNTRY}"

    # dependent summary job
    sbatch --dependency=afterok:${JOB_ID} "$SUMMARYSCRIPT" "$COUNTRY"
    echo "Submitted dependent summary job for ${COUNTRY}"
    echo "------------------------------------------------------"

done < "$NANSFILE"
