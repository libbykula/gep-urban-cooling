#!/bin/bash -l        
# Specifies the shell to use for the script (bash in this case), and the -l option makes it a login shell

# Slurm directives to request resources
#SBATCH --time=0:30:00  # Set the maximum runtime for the job to 10 minutes
#SBATCH --ntasks=1      # Request 1 task (process) for this job
#SBATCH --mem=50g       # Request 10GB of RAM
#SBATCH --tmp=10g       # Request 10GB of temporary (scratch) disk space
#SBATCH --array=0-654   # 
#SBATCH --cpus-per-task=36
#SBATCH --mail-type=ALL  # Receive emails on all events (start, end, fail)
#SBATCH --mail-user=kula0049@umn.edu  # Set email address to receive notifications
#SBATCH --output=logs/slurm-%A_%a.out

# Change to the specified working directory
cd ~/urban-cooling

# Load the necessary software modules
module load python3  # Load the Python 3 module
module load conda    # Load the Conda module

# Manually source the .bashrc file to initialize Conda
source ~/.bashrc  # Ensures that Conda is properly initialized before use

# Activate the Conda environment where dependencies are set up
# source activate investenv  # Activate the Conda environment "teems01"
source activate gdalfix

python run_gep_cooling_chunking.py 