#!/bin/bash -l

#SBATCH --time=5:00:00
#SBATCH --ntasks=1
#SBATCH --mem=25g
#SBATCH --tmp=10g
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=kula0049@umn.edu
#SBATCH --output=logs/slurm-%A.out

cd ~/urban-cooling

module load python3
module load conda
source ~/.bashrc
source activate gdalfix

urban_area='New York-Newark-Jersey City, NY-NJ-PA'

echo "Running urban_area: $urban_area"
python run_fuck_my_life.py "$urban_area"
