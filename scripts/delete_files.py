import os
import glob
import shutil
import sys

base_dir: str = "/users/3/kula0049/urban-cooling"

def delete_files_for_urban_area(urban_id: str):
    """
    Deletes intermediate data files and folders for a given urban area (e.g., '22_82'),
    including all month-specific files (01–12) where applicable.
    """

    print(f"\n🧹 Deleting temporary files for {urban_id}...\n")

    # --- File patterns (some include months) ---
    static_patterns = [
        f"Data/Polygon_vectors/urbans/{urban_id}.*",
        f"Data/Polygon_vectors/rural_refs/rural_ref_{urban_id}.*",
        f"Data/uhi/uhi_global_gep_{urban_id}.csv",
        f"Data/lulc/lulc_glc_fcs30d_2019_clipped_{urban_id}.tif",
        f"Data/Lulc_glc_fcs30d_2019_clipped_{urban_id}_mollweide.tif",
        f"Data/population/global_pop_2019_CN_1km_R2025A_UA_v1_clipped_{urban_id}.tif"
    ]

    # Month-dependent patterns (01–12)
    month_patterns = [
        f"Data/Tmean_stitched/tmean_stitched_2019_{{month}}_compress_rural_ref_{urban_id}.tif",
        f"Data/Tmean_stitched/tmean_stitched_2019_{{month}}_compress_fixed_clipped_{urban_id}.tif",
        f"Data/Tmean_stitched/tmean_stitched_2019_{{month}}_compress_fixed_clipped_{urban_id}_cdd_diff_{urban_id}.tif",
        f"Data/Tmean_stitched/tmean_stitched_2019_{{month}}_compress_fixed_clipped_{urban_id}_cdd_pop_diff_{urban_id}.tif",
        f"output/mixed_output/hm_{urban_id}_2019_{{month}}_mixed_compress.tif",
        f"Data/Evapotranspiration/Global-ET0_monthly_v3/Global-ET0_v3_monthly/et0_V3_{{month}}_clipped_{urban_id}.tif",
        f"Data/Evapotranspiration/Global-ET0_monthly_v3/Global-ET0_v3_monthly/et0_V3_{{month}}_clipped_{urban_id}_mollweide.tif",
    ]

    # Folders to delete entirely
    folders = [
        f"output/invest_results/{urban_id}"
    ]

    # --- Delete static files ---
    for pattern in static_patterns:
        full_pattern = os.path.join(base_dir, pattern)
        for path in glob.glob(full_pattern):
            try:
                os.remove(path)
                print(f"✅ Deleted: {os.path.relpath(path, base_dir)}")
            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"⚠️ Could not delete {path}: {e}")

    # --- Delete month-specific files ---
    for month in [f"{m:02d}" for m in range(1, 13)]:
        for pattern in month_patterns:
            full_pattern = os.path.join(base_dir, pattern.format(month=month))
            for path in glob.glob(full_pattern):
                try:
                    os.remove(path)
                    print(f"✅ Deleted: {os.path.relpath(path, base_dir)}")
                except FileNotFoundError:
                    pass
                except Exception as e:
                    print(f"⚠️ Could not delete {path}: {e}")

    # --- Delete folders recursively ---
    for folder in folders:
        full_folder = os.path.join(base_dir, folder)
        if os.path.exists(full_folder):
            try:
                shutil.rmtree(full_folder)
                print(f"🗑️  Deleted folder and contents: {os.path.relpath(full_folder, base_dir)}")
            except Exception as e:
                print(f"⚠️ Could not delete folder {full_folder}: {e}")

    # --- Clean up empty parents ---
    for folder in folders:
        parent = os.path.dirname(os.path.join(base_dir, folder))
        try:
            if os.path.isdir(parent) and not os.listdir(parent):
                os.rmdir(parent)
                print(f"Removed empty parent folder: {os.path.relpath(parent, base_dir)}")
        except Exception:
            pass

    print(f"\n✅ Cleanup complete for {urban_id}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python delete_files.py <urban_id>")
        sys.exit(1)

    urban_id = sys.argv[1]
    delete_files_for_urban_area(urban_id)
