#!/bin/bash -l
#SBATCH --job-name=urban_cooling
#SBATCH --time=00:30:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --mem=50g
#SBATCH --tmp=30g
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=kula0049@umn.edu
#SBATCH --output=logs/slurm-%A-%x.out

# Usage: sbatch --job-name=urban_cooling_ARG urban_cooling_country.sh ARG
# (logs/ must exist before submitting, or Slurm drops the output)
# Override time for a test run: sbatch --time=04:00:00 urban_cooling_country.sh KIR

cd ~/urban-cooling
module load conda
source ~/.bashrc
conda activate /users/3/kula0049/.conda/envs/gdalfix

COUNTRY=${1:?usage: sbatch urban_cooling_country.sh <ISO3>}
# CSV="/users/3/kula0049/urban-cooling/Data/urbanspatial-guppd-v1-gpkg/${COUNTRY,,}_smod_id.csv"
CSV="/users/3/kula0049/urban-cooling/missing_urban_areas_usa.txt"

mkdir -p logs

# Fail loudly on a missing CSV (no more silent "COMPLETED" with nothing run)
if [ ! -f "$CSV" ]; then
    echo "ERROR: no CSV for $COUNTRY at $CSV" | tee -a logs/missing_csv.txt >&2
    exit 1
fi

mapfile -t URBAN_AREAS < <(awk -F',' 'NR>1 {print $1}' "$CSV")

echo "Running multiprocessing for country: $COUNTRY, ${#URBAN_AREAS[@]} urban areas"

URBAN_LIST=$(printf "%s " "${URBAN_AREAS[@]}")

# Per-area failure logs go here
mkdir -p logs/errors_${COUNTRY}

# NOTE: this heredoc is unquoted, so bash expands $ and backticks inside it.
# Only ${COUNTRY} and ${URBAN_LIST} are meant to be expanded. Avoid other $ or
# backticks in the Python below.
# Python stderr (warnings, wrapper crashes) goes to logs/<ISO3>_warnings.log
/users/3/kula0049/.conda/envs/gdalfix/bin/python <<EOF 2> logs/${COUNTRY}_warnings.log
import subprocess, os, warnings, time, threading, shutil
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

warnings.filterwarnings("ignore")

country = "${COUNTRY}"
log_dir = f"logs/errors_{country}"
urban_areas = "${URBAN_LIST}".split()
print(f"Loaded {len(urban_areas)} urban areas from bash", flush=True)

PY = "/users/3/kula0049/.conda/envs/gdalfix/bin/python"

# ---- tunables ----
need = {"mem": 10.0}          # GB of free memory required to start another area
MIN_FREE_DISK_GB = 20         # GB free required on each watched path
LAUNCH_DELAY = 20             # seconds between launches, so memory ramp-up shows
DISK_WAIT_LIMIT = 600         # give up if disk stays low with nothing running
AREA_TIMEOUT = 3 * 3600       # seconds; kill any single area that runs longer
# Where a finished area's result lands; if it exists, the area is skipped on rerun.
# Adjust to your real final output file.
DONE_FILE = "/users/3/kula0049/urban-cooling/output/valuation_10_12_2026/{area}_2019.csv"
# Watch node-local TMPDIR only if Slurm set one (from --tmp), never the shared /tmp
DISK_PATHS = [p for p in [os.environ.get("TMPDIR"), "output", "logs"]
              if p and os.path.exists(p)]

def mem_state():
    """(limit, used) in bytes for THIS job's cgroup (v1 or v2), not the whole node."""
    limit, used = None, None
    mb = os.environ.get("SLURM_MEM_PER_NODE")
    if mb:
        limit = int(mb) * 1024 * 1024
    try:
        lines = open("/proc/self/cgroup").read().splitlines()
        # --- cgroup v1 ---
        mem_line = next((l for l in lines if ":memory:" in l), None)
        if mem_line:
            rel = mem_line.split(":", 2)[2]
            d = "/sys/fs/cgroup/memory" + rel
            while d.startswith("/sys/fs/cgroup/memory") and d != "/sys/fs/cgroup/memory":
                lim_f = os.path.join(d, "memory.limit_in_bytes")
                if os.path.exists(lim_f):
                    v = int(open(lim_f).read())
                    if v < 2**60:                      # skip "unlimited"
                        limit = v if limit is None else min(limit, v)
                        stat = {}
                        for line in open(os.path.join(d, "memory.stat")):
                            k, val = line.split()
                            stat[k] = int(val)
                        used = stat.get("total_rss", stat.get("rss", 0)) \
                             + stat.get("total_shmem", stat.get("shmem", 0))
                        break
                d = os.path.dirname(d)
        else:
            # --- cgroup v2 ---
            rel = next(l.split("::", 1)[1] for l in lines if l.startswith("0::"))
            d = "/sys/fs/cgroup" + rel
            while d.startswith("/sys/fs/cgroup") and d != "/sys/fs/cgroup":
                mx = os.path.join(d, "memory.max")
                if os.path.exists(mx):
                    v = open(mx).read().strip()
                    if v != "max":
                        limit = int(v) if limit is None else min(limit, int(v))
                        stat = {}
                        for line in open(os.path.join(d, "memory.stat")):
                            k, val = line.split()
                            stat[k] = int(val)
                        used = stat.get("anon", 0) + stat.get("shmem", 0)
                        break
                d = os.path.dirname(d)
    except Exception:
        pass
    if used is None or limit is None:
        limit = limit or 100 * 1024**3
        used = 0          # can't measure, so don't throttle on memory
    return limit, used

gate = threading.Lock()
running_lock = threading.Lock()
running = 0

def acquire_slot():
    """Block until there is headroom, then claim a slot. False = gave up (disk)."""
    global running
    with gate:                      # one launcher at a time = staggered starts
        waited = 0
        while True:
            limit, used = mem_state()
            free_mem = (limit - used) / 1e9
            mem_low = free_mem < need["mem"]
            disk_low = [p for p in DISK_PATHS
                        if shutil.disk_usage(p).free / 1e9 < MIN_FREE_DISK_GB]
            with running_lock:
                n = running
            # with nothing running, waiting on memory can't help, so go ahead
            if not disk_low and (not mem_low or n == 0):
                break
            if disk_low and n == 0 and waited >= DISK_WAIT_LIMIT:
                return False
            if waited % 60 == 0:
                print(f"throttled: free mem {free_mem:.0f} GB (need {need['mem']:.0f}), "
                      f"low disk: {disk_low}, running: {n}", flush=True)
            time.sleep(15)
            waited += 15
        with running_lock:
            running += 1
        time.sleep(LAUNCH_DELAY)    # still holding the gate
    return True

def release_slot():
    global running
    with running_lock:
        running -= 1

def cleanup(area):
    """Belt and braces: delete temp files even if the child was killed."""
    try:
        subprocess.run(
            [PY, "-c",
             f"from scripts import delete_files; "
             f"delete_files.delete_files_for_urban_area('{area}')"],
            capture_output=True)
    except Exception:
        pass

def run_urban(area):
    # Resume support: skip areas whose result already exists
    if os.path.exists(DONE_FILE.format(area=area)):
        return area, "success", "already done"

    cmd = [PY, "run_gep_cooling_by_c_v02.py", area]
    r = None
    elapsed = 0.0
    for attempt in range(1, 4):
        if not acquire_slot():
            return area, "failed", "skipped: disk space stayed low"
        t0 = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=AREA_TIMEOUT)
        except subprocess.TimeoutExpired:
            cleanup(area)
            return area, "failed", f"timeout after {AREA_TIMEOUT // 60} min"
        except Exception as e:
            return area, "error", f"could not launch: {e!r}"
        finally:
            release_slot()
        elapsed = time.time() - t0
        if r.returncode not in (-9, 137):       # not a SIGKILL / OOM
            break
        need["mem"] = min(need["mem"] * 1.25, 40)
        print(f"{area}: killed (likely OOM), attempt {attempt}; "
              f"free-memory floor now {need['mem']:.0f} GB", flush=True)

    cleanup(area)                               # runs once, after the final attempt

    if r.returncode == 0:
        return area, "success", f"{elapsed / 60:.1f} min"

    with open(f"{log_dir}/{area}.log", "w") as fh:
        fh.write(f"CMD: {' '.join(cmd)}\n")
        fh.write(f"RETURN CODE: {r.returncode}\n")
        fh.write(f"ELAPSED: {elapsed / 60:.1f} min\n\n")
        fh.write(f"--- STDOUT ---\n{r.stdout}\n\n--- STDERR ---\n{r.stderr}\n")
    lines = [l for l in r.stderr.strip().splitlines() if l.strip()]
    last = lines[-1] if lines else "(no stderr)"
    return area, "failed", f"rc={r.returncode} after {elapsed / 60:.1f} min | {last}"

max_workers = int(os.environ.get("MAX_WORKERS", os.environ.get("SLURM_CPUS_PER_TASK", 12)))
print(f"Up to {max_workers} workers, throttled by memory and disk", flush=True)
print(f"Watching disk on: {DISK_PATHS}", flush=True)

reasons = Counter()
n_ok = 0
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = {executor.submit(run_urban, a): a for a in urban_areas}
    for f in as_completed(futures):
        area, status, detail = f.result()
        print(f"{area}: {status} {detail}", flush=True)
        if status == "success":
            n_ok += 1
        else:
            reasons[detail] += 1

print(f"\n=== {n_ok} of {len(urban_areas)} succeeded ===", flush=True)
print("=== Failure summary ===", flush=True)
for reason, n in reasons.most_common():
    print(f"{n:4d} x {reason}", flush=True)
EOF
