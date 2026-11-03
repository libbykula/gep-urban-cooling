#!/bin/bash -l
# Usage: bash submit_country_jobs.sh ARG

COUNTRY=${1:-ARG}
CSV="/users/3/kula0049/urban-cooling/Data/urbanspatial-guppd-v1-gpkg/${COUNTRY,,}_smod_id.csv"

# Count number of urban areas (excluding header)
NUM_AREAS=$(($(wc -l < "$CSV") - 1))
ARRAY_MAX=$((NUM_AREAS - 1))

echo "Submitting array job for $COUNTRY with $NUM_AREAS urban areas"

# Submit array job and capture job ID
JOB_ID=$(sbatch --parsable --array=0-${ARRAY_MAX} urban_cooling_array.sh "$COUNTRY")
echo "Submitted job array ${JOB_ID} for $COUNTRY"

# Submit concatenation job to run after all array tasks finish successfully
sbatch --dependency=afterok:${JOB_ID} concat_country_summary.sh "$COUNTRY"
echo "Submitted dependent summary job for $COUNTRY"
