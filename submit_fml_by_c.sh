#!/bin/bash
#SBATCH --time=1:00:00
#SBATCH --ntasks=1
#SBATCH --mem=50g
#SBATCH --tmp=10g
#SBATCH --array=0
#SBATCH --cpus-per-task=9
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=kula0049@umn.edu
#SBATCH --output=logs/slurm-%A_%a.out

cd ~/urban-cooling

module load python3
module load conda
source ~/.bashrc
source activate gdalfix

# FOLDER="/users/3/kula0049/urban-cooling/inputs/InVEST Results/cooling workspace/3_16_2024_fixed_multistate"
FOLDER="/users/3/kula0049/urban-cooling/inputs/InVEST Results/cooling workspace/11_21_2023_metros"

# Build list of subfolders, excluding Boston and Duluth
mapfile -t URBAN_AREAS < <(
    find "$FOLDER" -mindepth 1 -maxdepth 1 -type d -printf "%f\n" |
    sort
)

# URBAN_AREAS=("${URBAN_AREAS[@]: -40}")


# mapfile -t URBAN_AREAS < <(
#     printf "%s\n" "${URBAN_AREAS[@]}" |
#     grep -v -x -F -e "Cincinnati, OH-KY-IN" 
# )
# URBAN_AREAS=("${URBAN_AREAS[@]: 1}")

# URBAN_AREAS=(
#     "Oshkosh-Neenah, WI"
# )


# Safety check
if (( SLURM_ARRAY_TASK_ID >= ${#URBAN_AREAS[@]} )); then
    echo "SLURM_ARRAY_TASK_ID $SLURM_ARRAY_TASK_ID is out of bounds (max: $((${#URBAN_AREAS[@]} - 1)))"
    exit 1
fi

urban_area="${URBAN_AREAS[$SLURM_ARRAY_TASK_ID]}"

echo "Running urban_area: $urban_area"
python run_fuck_my_life_v02.py "$urban_area"
