import sys
import os
from multiprocessing import Pool
from scripts import gep_run_urban_cooling_by_c

array_task_id = int(os.environ.get("SLURM_ARRAY_TASK_ID", 0))
chunk_size = 100  # or whatever you choose

start = array_task_id * chunk_size
end = start + chunk_size
urban_ids = list(range(start, end))  # these are the ones this task should process

print(f"Task {array_task_id} processing IDs from {start} to {end - 1}")

# for uid in urban_ids:
#     gep_run_urban_cooling_by_c.run(uid)

with Pool(processes=36) as pool:
    pool.map(gep_run_urban_cooling_by_c.prep_and_run_nature, urban_ids)