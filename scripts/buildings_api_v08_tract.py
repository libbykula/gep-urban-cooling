import planetary_computer
import pystac_client
import shapely.geometry
import geopandas as gpd
import pandas as pd
import mercantile
from deltalake import DeltaTable
import os

def buildings_api_get_total_area(tract_id, year):
    # int_tract_id = tract_id
    # tract_id = str(tract_id)

    # int_year = year
    # year = str(year)
    # ---------------------------
    # 1. AOI
    # ---------------------------
    input_dir = '/users/3/kula0049/urban-cooling/Data'
    output_dir = f'/users/3/kula0049/urban-cooling/results/{year}'

    os.makedirs(output_dir, exist_ok=True)

    # tracts_gdf = gpd.read_file(f"/users/3/kula0049/urban-cooling/results/cooling_nature_results_esi_6_12_26_{year}_nodups.gpkg")

    # create tract gpkg first 
    # aoi_gdf = tracts_gdf[tracts_gdf['GEOID'] == int_tract_id]
    # aoi_gdf = aoi_gdf.drop_duplicates()
    # aoi_gdf = aoi_gdf.to_crs('EPSG:4326')
    # print(aoi_gdf.head())
    aoi_path = os.path.join(input_dir, 'Polygon_vectors/tracts/', year, tract_id + '.gpkg')
    # aoi_gdf.to_file(aoi_path)

    aoi_gdf = gpd.read_file(aoi_path)

    # dissolve all features into one geometry (important!)
    aoi = aoi_gdf.union_all()
    print(aoi.bounds)
    # ---------------------------
    # 2. STAC catalog
    # ---------------------------
    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )

    collection = catalog.get_collection("ms-buildings")

    # ---------------------------
    # 3. Delta table + credentials
    # ---------------------------
    asset = collection.assets["delta"]  

    storage_options = {
        "account_name": asset.extra_fields["table:storage_options"]["account_name"],
        "sas_token": asset.extra_fields["table:storage_options"]["credential"],
    }

    table = DeltaTable(asset.href, storage_options=storage_options)

    # ---------------------------
    # 4. Convert AOI → quadkeys
    # ---------------------------
    quadkeys = [
        int(mercantile.quadkey(tile))
        for tile in mercantile.tiles(*aoi.bounds, zooms=9)
    ]

    print(f"{len(quadkeys)} quadkeys")

    # ---------------------------
    # 5. Query only relevant files
    # ---------------------------
    region = "UnitedStates"

    uris = table.file_uris([
        ("RegionName", "=", region),
        ("quadkey", "in", quadkeys)
    ])

    print(f"{len(uris)} parquet files")

    # ---------------------------
    # 6. Read only those files
    # ---------------------------
    gdfs = []

    for uri in uris:
        print(f"Reading: {uri}")
        
        gdf = gpd.read_parquet(
            uri,
            storage_options=storage_options
        )
        
        # clip precisely
        gdf = gdf[gdf.intersects(aoi)]
        
        if len(gdf) > 0:
            gdfs.append(gdf)

    # ---------------------------
    # 7. Save
    # ---------------------------
    if gdfs:
        buildings = gpd.GeoDataFrame(
            pd.concat(gdfs, ignore_index=True),
        )
        
        buildings = buildings.to_crs("EPSG:5070")
        os.makedirs(os.path.join(input_dir, 'Buildings', year), exist_ok=True)
        building_path = os.path.join(input_dir, 'Buildings', year, 'buildings_' + tract_id + '.gpkg')
        buildings.to_file(building_path, driver="GPKG")

        print(f"Saved {len(buildings)} buildings")

        building_area_m2 = buildings.area

        total_area = building_area_m2.sum()

        area_dict = {'GEOID': tract_id, 'total_build_area': total_area}
        area_df = pd.DataFrame([area_dict])

        area_df.to_csv(os.path.join(output_dir, f'tract_{tract_id}_total_build_area.csv'))

        print(f"Computed average area of {len(buildings)} buildings in {tract_id}")

        os.remove(building_path)
        os.remove(aoi_path)

    else:
        print("No buildings found")

# buildings_api_get_total_area(35001003001, 2001)