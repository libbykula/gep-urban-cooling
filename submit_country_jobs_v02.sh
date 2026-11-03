#!/bin/bash -l
# Usage: bash submit_country_jobs.sh ARG

COUNTRY=${1:-ARG}
echo "Submitting single multiprocessing job for $COUNTRY"

# Submit one job per country (no array)
JOB_ID=$(sbatch --parsable urban_cooling_multiproc.sh "$COUNTRY")
echo "Submitted job ${JOB_ID} for $COUNTRY"

# Still run summary concatenation after this job completes successfully
sbatch --dependency=afterok:${JOB_ID} concat_country_summary.sh "$COUNTRY"
echo "Submitted dependent summary job for $COUNTRY"
