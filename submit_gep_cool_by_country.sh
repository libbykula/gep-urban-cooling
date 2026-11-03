#!/bin/bash -l
#SBATCH --job-name=urban_cooling_${COUNTRY}
#SBATCH --time=4:00:00
#SBATCH --ntasks=1
#SBATCH --mem=12g
#SBATCH --tmp=10g
#SBATCH --array=0-XXX
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=kula0049@umn.edu
#SBATCH --output=logs/slurm-%A_%a-${COUNTRY}.out

# Load and activate environment
cd ~/urban-cooling
module load conda
source ~/.bashrc
conda activate /users/3/kula0049/.conda/envs/gdalfix

# Country name passed as variable
COUNTRY=${1:-ARG}
CSV="/users/3/kula0049/urban-cooling/Data/urbanspatial-guppd-v1-gpkg/${COUNTRY,,}_smod_id.csv"

# Read SMOD_IDs for this country
mapfile -t URBAN_AREAS < <(awk -F',' 'NR>1 {print $1}' "$CSV")

# Set urban area for this array task
urban_area="${URBAN_AREAS[$SLURM_ARRAY_TASK_ID]}"
echo "Running country: $COUNTRY, urban_area: $urban_area"

# Run processing
/users/3/kula0049/.conda/envs/gdalfix/bin/python run_gep_cooling_by_c_v02.py "$urban_area"
