import sys
import traceback

from scripts import gep_run_urban_cooling_by_c_v04
from scripts import hm_air_mixing
from scripts import gep_fixing_cooling_valuation_v11
from scripts import delete_files

from pathlib import Path

DONE = set(Path("/users/3/kula0049/urban-cooling/done_urban_areas.txt").read_text().split())

def process_urban_area(urban_area):
    if urban_area in DONE:
        print(f"Skipping {urban_area}: already succeeded", flush=True)
        return True
    ok = True
    try:
        print(f"Running valuation for {urban_area}", flush=True)
        gep_fixing_cooling_valuation_v11.run_valuation_c(urban_area)
        print("Completed valuation.\n", flush=True)
    except Exception:
        ok = False
        print(f"ERROR: valuation failed for {urban_area}", file=sys.stderr)
        traceback.print_exc()          # full traceback goes to stderr
    finally:
        # Runs on success, on failure, and on most interruptions
        try:
            print(f"Deleting unnecessary files for {urban_area}", flush=True)
            delete_files.delete_files_for_urban_area(urban_area)
            print("Completed deletion of unnecessary files.\n", flush=True)
        except Exception:
            ok = False
            print(f"ERROR: deletion failed for {urban_area}", file=sys.stderr)
            traceback.print_exc()
    return ok


if __name__ == "__main__":
    urban_area = sys.argv[1]
    sys.exit(0 if process_urban_area(urban_area) else 1)