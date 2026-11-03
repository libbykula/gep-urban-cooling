#!/bin/bash
# master_submit.sh

DATADIR="/users/3/kula0049/urban-cooling/Data/urbanspatial-guppd-v1-gpkg/"
RUNSCRIPT="run_urban_cooling_country.sbatch"
SUMMARYSCRIPT="concat_country_summary.sbatch"

# Skip specific countries (by ISO3 code)
SKIP_COUNTRIES=("USA" "RUS")

for csv in ${DATADIR}/*_smod_id.csv; do

    COUNTRY=$(basename "$csv" | cut -d'_' -f1 | tr '[:lower:]' '[:upper:]')

    # Skip excluded
    if [[ " ${SKIP_COUNTRIES[@]} " =~ " ${COUNTRY} " ]]; then
        echo "⏭️  Skipping ${COUNTRY} (excluded)"
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

done

