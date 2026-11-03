#!/bin/bash
#SBATCH --time=6:00:00
#SBATCH --ntasks=1
#SBATCH --mem=100g
#SBATCH --tmp=100g
#SBATCH --array=0
#SBATCH --cpus-per-task=6
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=kula0049@umn.edu
#SBATCH --output=logs/slurm-%A_%a.out

cd ~/urban-cooling

module load python3
module load conda
source ~/.bashrc
source activate gdalfix

USA_METROS="fix_metros_v02.txt"

# Read metros from file (one per line)
mapfile -t URBAN_AREAS < "$USA_METROS"

# Safety check
if (( SLURM_ARRAY_TASK_ID >= ${#URBAN_AREAS[@]} )); then
    echo "SLURM_ARRAY_TASK_ID $SLURM_ARRAY_TASK_ID is out of bounds (max: $((${#URBAN_AREAS[@]} - 1)))"
    exit 1
fi

urban_area="${URBAN_AREAS[$SLURM_ARRAY_TASK_ID]}"

echo "Running urban_area: $urban_area"
/users/3/kula0049/.conda/envs/gdalfix/bin/python run_snapp_msi.py 
# "$urban_area"

# for urban_area in "${URBAN_AREAS[@]}"; do
#     echo "Running urban_area: $urban_area"
#     /users/3/kula0049/.conda/envs/gdalfix/bin/python run_snapp_msi.py "$urban_area"
# done
