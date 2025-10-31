import os, re, time, glob
import geopandas as gpd
from multiprocessing import Pool

inputdir = '/users/3/kula0049/urban-cooling'
savings_dir = os.path.join(inputdir, 'inputs/InVEST Results/cooling workspace/8_14_2025_building_savings')
outdir = os.path.join(inputdir, 'inputs/InVEST Results/cooling workspace/8_14_2025_tract_savings')

os.makedirs(outdir, exist_ok=True)


def collect_all_args():
    """Scan savings_dir and build arg tuples (c_safe, c_orig, year, month)."""
    args_list = []
    for f in glob.glob(os.path.join(savings_dir, '*_buildings.gpkg')):
        fname = os.path.basename(f)
        m = re.match(r"(.+)_(\d{4})_(\d{2})_buildings\.gpkg", fname)
        if not m:
            continue
        c_safe, year, month = m.groups()
        # reverse the safe city name back to original
        c_orig = c_safe.replace('-', '/')
        args_list.append((c_safe, c_orig, year, month))
    return args_list


def run_all():
    args_list = collect_all_args()
    print(f"Found {len(args_list)} files to process")

    # n_procs = int(os.environ.get("SLURM_CPUS_PER_TASK", 9))
    n_procs = os.cpu_count()

    with Pool(processes=n_procs) as pool:
        pool.map(summ_cooling_sav_tract, args_list)


def summ_cooling_sav_tract(args):
    c, c_orig, year, month = args
    out_path = os.path.join(outdir, f"{c}_{year}_{month}_tract_energy_savings.csv")
    if os.path.exists(out_path):
        return
    else:
        t = time.localtime()
        print(f"[{time.strftime('%H:%M:%S', t)}] Processing {c} {year}-{month}")

        last_year = str(int(year) - 1)
        tract_path = os.path.join(inputdir, f'Data/Tract/{last_year}/{c}_valid_v02.gpkg')
        if not os.path.exists(tract_path):
            print(f"Missing tract file: {tract_path}")
            return

        tract_gdf = gpd.read_file(tract_path).to_crs('EPSG:4326')

        if year == '2001':
            tract_gdf['GEOID'] = tract_gdf['CTIDFP00']
        elif year == '2011':
            tract_gdf['GEOID'] = tract_gdf['GEOID10']

        savings_path = os.path.join(savings_dir, f"{c}_{year}_{month}_buildings.gpkg")
        if not os.path.exists(savings_path):
            print(f"Missing savings file: {savings_path}")
            return

        savings_data = gpd.read_file(savings_path).to_crs('EPSG:4326')
        tract_gdf = tract_gdf[tract_gdf.geometry.is_valid]

        joined_gdf = gpd.sjoin(
            savings_data,
            tract_gdf,
            how='right',
            predicate="within"
        )

        summary_stats = joined_gdf.groupby('GEOID')['dollars_saved'].agg(['sum']).reset_index()

        summary_stats.to_csv(out_path, index=False)
        print(f"Saved {out_path}")

run_all()
