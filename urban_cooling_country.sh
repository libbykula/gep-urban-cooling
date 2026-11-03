#!/bin/bash -l
#SBATCH --job-name=urban_cooling_${COUNTRY}
#SBATCH --time=02:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --mem=100g
#SBATCH --tmp=100g
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=kula0049@umn.edu
#SBATCH --output=logs/slurm-%A-%x.out

cd ~/urban-cooling
module load conda
source ~/.bashrc
conda activate /users/3/kula0049/.conda/envs/gdalfix

COUNTRY=${1:-ARG}
CSV="/users/3/kula0049/urban-cooling/Data/urbanspatial-guppd-v1-gpkg/${COUNTRY,,}_smod_id.csv"

# Skip missing CSVs
if [ ! -f "$CSV" ]; then
    echo "No CSV found for $COUNTRY, skipping"
    exit 0
fi

mapfile -t URBAN_AREAS < <(awk -F',' 'NR>1 {print $1}' "$CSV")

echo "Running multiprocessing for country: $COUNTRY, ${#URBAN_AREAS[@]} urban areas"

URBAN_LIST=$(printf "%s " "${URBAN_AREAS[@]}")

# Redirect stderr from Python to a log file to silence warnings in SLURM output
mkdir -p logs/errors_${COUNTRY}

/users/3/kula0049/.conda/envs/gdalfix/bin/python <<EOF 2> logs/${COUNTRY}_warnings.log
import subprocess, os, warnings
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed

warnings.filterwarnings("ignore")

country = "${COUNTRY}"
log_dir = f"logs/errors_{country}"
urban_areas = "${URBAN_LIST}".split()
print(f"Loaded {len(urban_areas)} urban areas from bash", flush=True)

def run_urban(area):
    cmd = ["/users/3/kula0049/.conda/envs/gdalfix/bin/python",
           "run_gep_cooling_by_c_v02.py", area]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        return area, "error", f"could not launch: {e!r}"

    if r.returncode == 0:
        return area, "success", ""

    # Save full output for failed areas
    with open(f"{log_dir}/{area}.log", "w") as fh:
        fh.write(f"CMD: {' '.join(cmd)}\n")
        fh.write(f"RETURN CODE: {r.returncode}\n\n")
        fh.write(f"--- STDOUT ---\n{r.stdout}\n\n--- STDERR ---\n{r.stderr}\n")

    lines = [l for l in r.stderr.strip().splitlines() if l.strip()]
    last = lines[-1] if lines else "(no stderr)"
    return area, "failed", f"rc={r.returncode} | {last}"

max_workers = int(os.environ.get("SLURM_CPUS_PER_TASK", 24))
print(f"Using {max_workers} parallel workers", flush=True)

reasons = Counter()
with ProcessPoolExecutor(max_workers=max_workers) as executor:
    futures = {executor.submit(run_urban, a): a for a in urban_areas}
    for f in as_completed(futures):
        area, status, detail = f.result()
        print(f"{area}: {status} {detail}", flush=True)
        if status != "success":
            reasons[detail] += 1

print("\n=== Failure summary ===", flush=True)
for reason, n in reasons.most_common():
    print(f"{n:4d} x {reason}", flush=True)
EOF