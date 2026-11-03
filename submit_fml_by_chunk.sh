#!/bin/bash -l

#SBATCH --time=3:00:00
#SBATCH --ntasks=1
#SBATCH --mem=50g
#SBATCH --tmp=10g
#SBATCH --array=0-27  # Adjust based on number of chunks desired
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=kula0049@umn.edu
#SBATCH --output=logs/slurm-%A_%a.out

cd ~/urban-cooling

module load python3
module load conda
source ~/.bashrc
source activate gdalfix

FOLDER="/users/3/kula0049/urban-cooling/inputs/InVEST Results/cooling workspace/3_16_2024_fixed_multistate"

# Build list of unique urban area names
mapfile -t URBAN_AREAS < <(
    find "$FOLDER" -mindepth 1 -maxdepth 1 -type d -printf "%f\n" | sort
)


# Set chunk size (number of urban areas per job)
CHUNK_SIZE=18  # Change this depending on load and array size

# Calculate start and end index for this SLURM task
START_INDEX=$((SLURM_ARRAY_TASK_ID * CHUNK_SIZE))
END_INDEX=$((START_INDEX + CHUNK_SIZE - 1))

# Cap end index at length of URBAN_AREAS
TOTAL=${#URBAN_AREAS[@]}
if [ "$END_INDEX" -ge "$TOTAL" ]; then
    END_INDEX=$((TOTAL - 1))
fi

# Run your script for each urban area in this chunk
for ((i = START_INDEX; i <= END_INDEX; i++)); do
    urban_area="${URBAN_AREAS[$i]}"
    echo "Running urban_area: $urban_area"
    python run_fuck_my_life.py "$urban_area"
done
