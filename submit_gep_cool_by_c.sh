#!/bin/bash -l
#SBATCH --job-name=urban_cooling_ARG
#SBATCH --time=1:00:00
#SBATCH --ntasks=1
#SBATCH --mem=10g
#SBATCH --tmp=10g
#SBATCH --array=0-673
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=kula0049@umn.edu
#SBATCH --output=logs/slurm-%A_%a.out

# Change to working directory
cd ~/urban-cooling

# Load conda (depends on your cluster’s setup)
module load conda

# Activate your environment
source ~/.bashrc
conda activate /users/3/kula0049/.conda/envs/gdalfix

# Read SMOD_IDs
csv="/users/3/kula0049/urban-cooling/Data/urbanspatial-guppd-v1-gpkg/arg_smod_id.csv"
mapfile -t URBAN_AREAS < <(awk -F',' 'NR>1 {print $2}' "$csv")

# URBAN_AREAS=(30_207)

# Select this task's SMOD_ID
urban_area="${URBAN_AREAS[$SLURM_ARRAY_TASK_ID]}"
echo "Running urban_area: $urban_area"

# Run Python script within the activated environment
/users/3/kula0049/.conda/envs/gdalfix/bin/python run_gep_cooling_by_c.py "$urban_area"
