"""
STEP 5: Peat soils from the Irish Peat Soils Map (IPSM)
=======================================================

Why this replaces the OpenStreetMap bogs
----------------------------------------
OSM only shows bogs that volunteers have drawn. The Irish Peat Soils Map
(Gilet, Morley & Flynn, 2024, Geoderma) is a scientific map that combines
soil, geology and land-cover data. It finds peat under about 1.66 million
hectares, roughly 23% of the Republic. It also sorts peat into TYPES,
which we use for colour.
Licence: CC BY 4.0 (free to use with credit). Download: https://osf.io/27hj3/

Coverage gap: the IPSM covers the REPUBLIC of Ireland only. For Northern
Ireland we keep the OSM bogs from step 3, and mark them with
source = "osm" so the map can draw them differently and be honest about it.

Before running
--------------
1. Download IPSM_shared_june24.zip from https://osf.io/download/jwg6f/
2. Unzip it into data/raw/ so this file exists:
   data/raw/IPSM_shared_june24/raster_dataset/IPSM_soiltype.tif
3. Run step 3 first (it makes the OSM bog grid used for Northern Ireland).

Then run (install once: pip install rasterio):
    python scripts/05_peat_soils.py

Key idea: RASTER vs VECTOR
--------------------------
So far every layer was VECTOR: points and shapes. The IPSM is a RASTER:
a grid of pixels, like a photo, where each pixel is 100 m x 100 m
(1 hectare) and holds a number. In IPSM_soiltype.tif:
    0  = not peat           3 = mountain blanket bog
    1  = raised bog          4 = fen
    2  = lowland Atlantic    5 = other peat soils
         blanket bog         15 = no data (sea, Northern Ireland)
To use it on our map we "resample" it: we drop the 100 m pixels into our
~1.3 km grid squares and count them, like sorting coins into jars.
"""

from pathlib import Path

import geopandas as gpd
import numpy as np                    # numpy = fast maths on big grids of numbers
import pandas as pd                   # pandas = tables (geopandas is built on it)
import rasterio                       # rasterio = reads raster files like GeoTIFFs
from pyproj import Transformer        # pyproj = converts between coordinate systems
from shapely.geometry import box

REPO = Path(__file__).parent.parent
RASTER = REPO / "data" / "raw" / "IPSM_shared_june24" / "raster_dataset" / "IPSM_soiltype.tif"
OUT = REPO / "data" / "processed"

# Same grid as the OSM peat layer in step 3, so the two line up exactly.
GRID_WEST, GRID_NORTH = -10.7, 55.45
CELL_W, CELL_H = 0.02, 0.012

PEAT_TYPES = {
    1: "Raised bog",
    2: "Lowland Atlantic blanket bog",
    3: "Mountain blanket bog",
    4: "Fen",
    5: "Other peat soil",
}


if __name__ == "__main__":
    # ---- 1. Read the raster ------------------------------------------------
    # "with ... as r:" opens the file and closes it again when we're done.
    with rasterio.open(RASTER) as r:
        pixels = r.read(1)            # band 1 as a 2D numpy array (rows x columns)
        transform = r.transform       # the maths linking pixel (row, col) to map x/y
        crs = r.crs                   # EPSG:29902, the old Irish Grid, in metres
    print(f"Raster: {pixels.shape[0]} rows x {pixels.shape[1]} columns, CRS {crs}")

    # ---- 2. Find every land pixel and where it is -------------------------
    # np.nonzero gives the row and column of every pixel where the test is True.
    # "Land" = any value from 0 to 5 (15 means no data).
    rows, cols = np.nonzero(pixels <= 5)
    values = pixels[rows, cols]

    # Pixel row/col -> map x/y in metres (the centre of each pixel, hence + 0.5).
    xs, ys = rasterio.transform.xy(transform, rows, cols, offset="center")

    # Metres on the Irish Grid -> longitude/latitude. always_xy=True means
    # "I'll give you x (east) first, then y (north)", which avoids a classic mix-up.
    to_lonlat = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    lons, lats = to_lonlat.transform(np.array(xs), np.array(ys))

    # ---- 3. Drop each pixel into a grid square ----------------------------
    # Which column/row of OUR grid is each pixel in? Floor division (//)
    # rounds down, so every pixel in the same square gets the same numbers.
    grid_col = ((lons - GRID_WEST) // CELL_W).astype(int)
    grid_row = ((GRID_NORTH - lats) // CELL_H).astype(int)

    # Put the pixels in a table so we can group them (like a pivot table).
    table = pd.DataFrame({"row": grid_row, "col": grid_col, "value": values})
    table["is_peat"] = table["value"] > 0

    # For each square: how many land pixels, how many peat pixels.
    per_cell = table.groupby(["row", "col"]).agg(
        land=("value", "size"), peat=("is_peat", "sum")
    ).reset_index()

    # For each square: the most common peat type (the "mode").
    peat_only = table[table["is_peat"]]
    main_type = (peat_only.groupby(["row", "col"])["value"]
                 .agg(lambda v: v.value_counts().idxmax())
                 .rename("type_code").reset_index())
    per_cell = per_cell.merge(main_type, on=["row", "col"])

    # Coverage = share of the square's LAND that is peat (0 to 1).
    # Using land (not the whole square) keeps coastal squares fair.
    per_cell["coverage"] = (per_cell["peat"] / per_cell["land"]).round(2)
    per_cell = per_cell[(per_cell["coverage"] >= 0.05) & (per_cell["land"] >= 20)]
    per_cell["type"] = per_cell["type_code"].map(PEAT_TYPES)
    per_cell["source"] = "ipsm"

    # Grid numbers -> square shapes.
    per_cell["geometry"] = [
        box(GRID_WEST + c * CELL_W, GRID_NORTH - (r + 1) * CELL_H,
            GRID_WEST + (c + 1) * CELL_W, GRID_NORTH - r * CELL_H)
        for r, c in zip(per_cell["row"], per_cell["col"])
    ]
    ipsm = gpd.GeoDataFrame(per_cell, crs="EPSG:4326")
    print(f"IPSM squares with peat: {len(ipsm)}")
    print("  peat area in raster:", int(table["is_peat"].sum()), "ha")

    # ---- 4. Fill Northern Ireland from the OSM bog grid -------------------
    # The raster has no data for NI, so keep only OSM squares that the
    # IPSM does not cover at all.
    osm = gpd.read_file(OUT / "peatland_osm_grid.geojson")
    covered = set(zip(table["row"], table["col"]))           # squares the IPSM covers
    osm = osm[[(r, c) not in covered for r, c in zip(osm["row"], osm["col"])]]
    osm = osm.assign(type="Bog (OpenStreetMap)", type_code=9, source="osm")
    print(f"OSM squares kept for Northern Ireland: {len(osm)}")

    # ---- 5. Combine and save ----------------------------------------------
    # pd.concat stacks two tables on top of each other.
    # We keep only the columns the map needs: with ~20,000 squares, every
    # extra column makes the file noticeably bigger and the page slower.
    # (The type NAMES live in map.js; here we store just the short code.)
    keep = ["coverage", "type_code", "source", "geometry"]
    peat = gpd.GeoDataFrame(pd.concat([ipsm[keep], osm[keep]]), crs="EPSG:4326")
    # 3 decimal places (~100 m) is plenty: our grid lines fall on exact
    # multiples of 0.02 and 0.012 degrees anyway.
    peat.to_file(OUT / "peatland_grid.geojson", driver="GeoJSON", COORDINATE_PRECISION=3)
    print(f"Saved {len(peat)} squares to peatland_grid.geojson")
