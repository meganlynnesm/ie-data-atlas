"""
STEP 2: Make the base map (the island outline and county lines)
===============================================================

What this script does
---------------------
Downloads free boundary data from Natural Earth (a public-domain map
dataset), keeps only the parts on the island of Ireland, and saves:
    data/processed/ireland_outline.geojson  -> one shape: the whole island
    data/processed/counties.geojson         -> county / district boundaries

Key idea: GeoDataFrames
-----------------------
We use a library called geopandas. Think of it as a spreadsheet (a table)
where one column holds shapes. Each row is one feature, for example one
county, and the "geometry" column holds its outline. Everything you would
do in the QGIS attribute table (filter, dissolve, simplify) can be done
here with one line of code.

Run with:
    python scripts/02_make_base.py
"""

from pathlib import Path

import geopandas as gpd           # "as gpd" is a nickname so we type less
from shapely.geometry import box  # box() makes a rectangle shape

REPO = Path(__file__).parent.parent
OUT = REPO / "data" / "processed"

# Natural Earth "admin 1" = states / provinces / counties for the whole world.
# geopandas can read a file straight from a web address.
NATURAL_EARTH_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_10m_admin_1_states_provinces.geojson"
)

# A rectangle around Ireland: box(west, south, east, north) in degrees.
# Longitude = east/west (negative = west of Greenwich).
# Latitude  = north/south.
IRELAND_BOX = box(-10.8, 51.3, -5.35, 55.45)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)

    print("Reading Natural Earth (about 40 MB, may take a minute)...")
    world = gpd.read_file(NATURAL_EARTH_URL)

    # --- FILTER ROWS ---------------------------------------------------------
    # Keep rows where the country is Ireland, or the region is Northern Ireland.
    # The "|" means OR. Each test gives a True/False column, and
    # world[ ... ] keeps only the True rows. Same idea as a filter in Excel.
    is_ireland = world["adm0_a3"] == "IRL"
    is_northern_ireland = world["geonunit"] == "Northern Ireland"
    counties = world[is_ireland | is_northern_ireland]

    # Keep only the two columns we need.
    counties = counties[["name", "geometry"]]

    # --- CLIP ----------------------------------------------------------------
    # Cut everything to our rectangle (removes stray offshore bits).
    counties = counties.clip(IRELAND_BOX)

    # --- SIMPLIFY ------------------------------------------------------------
    # Fewer points = smaller file = faster web page.
    # 0.002 degrees is roughly 150 m, which is invisible at island scale.
    counties["geometry"] = counties.simplify(0.002)

    # --- DISSOLVE ------------------------------------------------------------
    # Merge all counties into ONE shape for the island outline.
    # union_all() is the code version of QGIS "Dissolve".
    island = counties.union_all()
    outline = gpd.GeoDataFrame({"name": ["Ireland"]}, geometry=[island], crs=counties.crs)

    # --- SAVE ----------------------------------------------------------------
    counties.to_file(OUT / "counties.geojson", driver="GeoJSON")
    outline.to_file(OUT / "ireland_outline.geojson", driver="GeoJSON")

    print(f"Saved {len(counties)} counties/districts and the island outline.")
    print("Next, run: python scripts/03_process_layers.py")
