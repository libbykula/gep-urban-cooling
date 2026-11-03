#!/bin/bash -l        
# Specifies the shell to use for the script (bash in this case), and the -l option makes it a login shell

# Slurm directives to request resources
#SBATCH --time=8:10:00  # Set the maximum runtime for the job 
#SBATCH --ntasks=1      # Request 1 tasks (process) for this job
#SBATCH --array=0-133   # Adjust this based on the number of METROS you have, parallelizing
#SBATCH --mem=10g       # Request 10GB of RAM
#SBATCH --tmp=10g       # Request 10GB of temporary (scratch) disk space
#SBATCH --mail-type=ALL  # Receive emails on all events (start, end, fail)
#SBATCH --mail-user=kula0049@umn.edu  # Set email address to receive notifications
#SBATCH --output=logs/slurm-%A_%a.out    # For array jobs
#SBATCH --error=logs/slurm-%A_%a.err     # Optional, separate error log

# Change to the specified working directory
cd ~/urban-cooling

# Load the necessary software modules
module load python3  # Load the Python 3 module
module load conda    # Load the Conda module
#source activate teems01

# Read subfolder names into the METROS array
mapfile -t METROS < <(find "inputs/InVEST Results/cooling workspace/11_21_2023_metros" -mindepth 1 -maxdepth 1 -type d -exec basename {} \;)

metro="${METROS[$SLURM_ARRAY_TASK_ID]}"
echo "Running metro: $metro"
python run_fixing_cooling.py "$metro"