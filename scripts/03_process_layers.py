"""
STEP 3: Clean the raw OSM downloads into map-ready GeoJSON
==========================================================

What this script does
---------------------
Reads the raw files from step 1 (data/raw/osm_*.json) and writes clean
GeoJSON files to data/processed/:

    data_centres.geojson  -> one point per data centre, with name and operator
    wind_farms.geojson    -> one point per wind farm, with name and capacity (MW)
    peatland_osm_grid.geojson -> a grid of ~1.3 km squares; each square says
                             what share of it (0 to 1) is mapped as bog in OSM.
                             (Step 5 swaps in the better IPSM peat map and keeps
                             these OSM squares only for Northern Ireland.)

Why turn bogs into a grid?
--------------------------
OSM has thousands of detailed bog outlines. Drawing all of them makes a
heavy web page. Summarising them into squares ("binning") keeps the pattern
but makes the file light, and the pixel look matches the broadband layer.

What is GeoJSON?
----------------
A plain-text map format that web pages read easily. Open any .geojson file
in VS Code and you will see it is just nested lists and dictionaries:
    {"type": "Feature",
     "geometry": {"type": "Point", "coordinates": [longitude, latitude]},
     "properties": {"name": "..."}}
Note: GeoJSON always puts LONGITUDE first, then latitude.

Run with:
    python scripts/03_process_layers.py
"""

import json
import re
from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import polygonize, unary_union

REPO = Path(__file__).parent.parent
RAW = REPO / "data" / "raw"
OUT = REPO / "data" / "processed"

# EPSG codes are ID numbers for coordinate systems.
#   4326 = plain latitude/longitude in degrees (what GPS and GeoJSON use)
#   2157 = Irish Transverse Mercator (ITM), measured in METRES.
# To measure AREA we must use metres, so we switch to 2157 for that step.
LATLON = "EPSG:4326"
IRISH_METRES = "EPSG:2157"

# Grid settings for the peatland layer, in degrees.
# At Ireland's latitude, 0.02 deg of longitude ~ 1.3 km and
# 0.012 deg of latitude ~ 1.3 km, so the cells come out roughly square.
GRID_WEST, GRID_NORTH = -10.7, 55.45
GRID_EAST, GRID_SOUTH = -5.4, 51.4
CELL_W, CELL_H = 0.02, 0.012


# ---------------------------------------------------------------------------
# Small helper functions
# ---------------------------------------------------------------------------
def load_raw(name: str) -> list:
    """Open data/raw/osm_<name>.json and return its list of features."""
    path = RAW / f"osm_{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))["elements"]


def point_of(element: dict) -> Point:
    """
    OSM points (nodes) have lat/lon directly. Shapes (ways/relations)
    downloaded with "out center" have them inside a "center" dictionary.
    This function handles both cases.
    """
    if "lat" in element:
        return Point(element["lon"], element["lat"])
    return Point(element["center"]["lon"], element["center"]["lat"])


def parse_megawatts(text: str):
    r"""
    OSM capacity tags are typed by volunteers, so they vary:
    "57.6 MW", "7500 kW", "12.5MW", "yes". Turn them into a number of MW,
    or None if there is no number.

    re.search() looks for a pattern in text (a "regular expression"):
        ([\d.]+)   one or more digits or dots  -> the number
        \s*        optional spaces
        (k|M|G)?   an optional unit letter
    """
    match = re.search(r"([\d.]+)\s*(k|M|G)?W?", text or "")
    if not match:
        return None
    number = float(match.group(1))
    unit = match.group(2) or "M"          # assume MW if no unit given
    return round(number * {"k": 0.001, "M": 1, "G": 1000}[unit], 2)


# ---------------------------------------------------------------------------
# Layer 1 and 2: points
# ---------------------------------------------------------------------------
def make_data_centres():
    elements = load_raw("data_centres")

    # A "list comprehension": builds a list in one line.
    # Read it as: "for each element e, make this dictionary".
    rows = [
        {
            "name": e["tags"].get("name", ""),         # .get() = value, or "" if missing
            "operator": e["tags"].get("operator", ""),
            "geometry": point_of(e),
        }
        for e in elements
    ]
    gdf = gpd.GeoDataFrame(rows, crs=LATLON)
    gdf.to_file(OUT / "data_centres.geojson", driver="GeoJSON")
    print(f"  data centres: {len(gdf)}")


def make_wind_farms():
    elements = load_raw("wind_farms")
    rows = [
        {
            "name": e["tags"].get("name", ""),
            "mw": parse_megawatts(e["tags"].get("plant:output:electricity")),
            "geometry": point_of(e),
        }
        for e in elements
    ]
    gdf = gpd.GeoDataFrame(rows, crs=LATLON)
    gdf.to_file(OUT / "wind_farms.geojson", driver="GeoJSON")
    known = gdf["mw"].notna().sum()
    print(f"  wind farms: {len(gdf)} ({known} with capacity, {gdf['mw'].sum():.0f} MW total)")


# ---------------------------------------------------------------------------
# Layer 3: peatland grid
# ---------------------------------------------------------------------------
def bog_shapes(elements: list) -> list:
    """
    Turn OSM bog features into shapely Polygons.
      - A "way" is a single closed outline: a list of points.
      - A "relation" is a big bog drawn from several pieces ("members").
        Pieces with role "outer" form the edge; "inner" pieces are holes.
        polygonize() glues the pieces into closed shapes.
    """
    shapes = []
    for e in elements:
        if e["type"] == "way":
            coords = [(p["lon"], p["lat"]) for p in e["geometry"]]
            if len(coords) >= 4:                    # a polygon needs 4+ points
                shapes.append(Polygon(coords))
        else:  # relation
            outers, inners = [], []
            for m in e.get("members", []):
                if "geometry" not in m:
                    continue
                line = LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
                (inners if m.get("role") == "inner" else outers).append(line)
            outer = unary_union(list(polygonize(outers)))
            holes = unary_union(list(polygonize(inners)))
            shapes.append(outer.difference(holes))
    # .buffer(0) is a common trick that repairs slightly broken shapes.
    return [s.buffer(0) for s in shapes if not s.is_empty]


def make_grid() -> gpd.GeoDataFrame:
    """Make every grid cell over Ireland as a rectangle, row by row."""
    cells = []
    n_cols = round((GRID_EAST - GRID_WEST) / CELL_W)
    n_rows = round((GRID_NORTH - GRID_SOUTH) / CELL_H)
    for row in range(n_rows):              # range(3) gives 0, 1, 2
        for col in range(n_cols):
            west = GRID_WEST + col * CELL_W
            north = GRID_NORTH - row * CELL_H
            cells.append({"row": row, "col": col,
                          "geometry": box(west, north - CELL_H, west + CELL_W, north)})
    return gpd.GeoDataFrame(cells, crs=LATLON)


def make_peatland_grid():
    print("  building bog shapes...")
    bogs = gpd.GeoDataFrame(geometry=bog_shapes(load_raw("bogs")), crs=LATLON)

    # Merge overlapping bogs so no area is counted twice.
    bogs = gpd.GeoDataFrame(geometry=[bogs.union_all()], crs=LATLON).explode()

    grid = make_grid()

    # Switch both layers to metres so .area gives square metres.
    bogs_m = bogs.to_crs(IRISH_METRES)
    grid_m = grid.to_crs(IRISH_METRES)
    grid_m["cell_area"] = grid_m.area

    # OVERLAY "intersection" = QGIS "Intersection" tool:
    # cuts the bogs along the grid lines, so each piece knows its cell.
    print("  cutting bogs by grid (this is the slow step)...")
    pieces = gpd.overlay(grid_m, bogs_m, how="intersection", keep_geom_type=True)
    pieces["bog_area"] = pieces.area

    # GROUP BY: add up all bog pieces inside each cell
    # (like a pivot table in Excel).
    per_cell = pieces.groupby(["row", "col", "cell_area"], as_index=False)["bog_area"].sum()
    per_cell["coverage"] = (per_cell["bog_area"] / per_cell["cell_area"]).clip(upper=1).round(2)

    # Join the numbers back onto the cell rectangles (in lat/lon again).
    result = grid.merge(per_cell[["row", "col", "coverage"]], on=["row", "col"])
    result = result[result["coverage"] >= 0.05]     # skip near-empty cells
    result.to_file(OUT / "peatland_osm_grid.geojson", driver="GeoJSON",
                   COORDINATE_PRECISION=4)
    print(f"  peatland cells: {len(result)}")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    print("Processing layers...")
    make_data_centres()
    make_wind_farms()
    if (RAW / "osm_bogs.json").exists():
        make_peatland_grid()
    else:
        print("  (no data/raw/osm_bogs.json yet, skipping peatland)")
    print("Next, run: python scripts/04_fetch_broadband.py")
