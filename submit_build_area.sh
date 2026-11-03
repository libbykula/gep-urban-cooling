#!/bin/bash
#SBATCH --job-name=buildings
#SBATCH --time=1:00:00  # Set the maximum runtime for the job to 10 minutes
#SBATCH --cpus-per-task=10        # match this to n_workers below
#SBATCH --output=build_logs/%A_%a.out
#SBATCH --error=build_logs/%A_%a.err

# Change to working directory
cd ~/urban-cooling

# Load conda (depends on your cluster’s setup)
module load conda

# Activate your environment
source ~/.bashrc
conda activate /users/3/kula0049/.conda/envs/gdalfix

# YEAR=$1
# CHUNK_DIR=scripts/tracts/$YEAR
# CHUNK_FILE=$CHUNK_DIR/chunk_${SLURM_ARRAY_TASK_ID}.txt

YEAR='2001'
CHUNK_FILE='scripts/tracts/2001/chunk_1.txt'
/users/3/kula0049/.conda/envs/gdalfix/bin/python run_building_areas_v02.py $CHUNK_FILE $YEAR