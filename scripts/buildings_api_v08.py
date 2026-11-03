import planetary_computer
import pystac_client
import shapely.geometry
import geopandas as gpd
import pandas as pd
import mercantile
from deltalake import DeltaTable
import os

def save_buildings_api(c):
    # ---------------------------
    # 1. AOI
    # ---------------------------
    input_dir = '/projects/standard/jajohns/shared/Files/urban_cooling/base_data'

    aoi_path = os.path.join(input_dir, 'Polygon_vectors/Metros', c + '.shp')
    aoi_gdf = gpd.read_file(aoi_path)

    # dissolve all features into one geometry (important!)
    aoi = aoi_gdf.unary_union

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

        buildings.to_file(os.path.join(input_dir, 'Buildings/buildings_' + c + '.gpkg'), driver="GPKG")

        print(f"Saved {len(buildings)} buildings")
    else:
        print("No buildings found")
