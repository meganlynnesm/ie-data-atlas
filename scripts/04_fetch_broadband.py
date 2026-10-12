"""
STEP 4: Broadband speeds from Ookla open data
=============================================

Where the data comes from
-------------------------
Ookla (the company behind speedtest.net) publishes the average speeds from
millions of speed tests, grouped into small map tiles (~600 m), every
three months, free under a CC BY-NC-SA licence. Docs:
https://github.com/teamookla/ookla-open-data

The catch: each file covers the WHOLE WORLD and is hundreds of MB.
We don't want to download all of it to get Ireland.

The trick: DuckDB
-----------------
DuckDB is a small database that can run SQL directly on a file sitting on
the internet. The files are in "Parquet" format, which is organised so
DuckDB can read just the columns and chunks it needs. So we write a
query that says "only tiles inside Ireland's box" and DuckDB downloads
only those parts.

SQL in one minute
-----------------
SQL is the standard language for asking tables questions:
    SELECT  the columns you want (you can calculate new ones)
    FROM    which table/file
    WHERE   only rows that pass this test
    GROUP BY  squash rows with the same value into one summary row

What this script makes
----------------------
data/processed/broadband_grid.geojson: squares of 0.05 x 0.05 degrees
(~3.3 km x 5.5 km) with the average fixed-broadband download speed.

Run with (install once: pip install duckdb):
    python scripts/04_fetch_broadband.py
"""

from pathlib import Path

import duckdb
import geopandas as gpd
from shapely.geometry import box

REPO = Path(__file__).parent.parent
OUT = REPO / "data" / "processed"

# Which quarter to use. Ookla names files by the first day of the quarter.
YEAR, QUARTER, START_DATE = 2026, 2, "2026-04-01"
URL = (
    "https://ookla-open-data.s3.amazonaws.com/parquet/performance/"
    f"type=fixed/year={YEAR}/quarter={QUARTER}/{START_DATE}_performance_fixed_tiles.parquet"
)

CELL = 0.05  # size of our summary squares, in degrees


def speed_class(mbps: float) -> int:
    """Put a speed into one of 6 groups, used for colour on the map.
    30 Mbps is the EU's old 'basic broadband' line, so it is a key break."""
    if mbps < 10:
        return 1
    if mbps < 30:
        return 2
    if mbps < 100:
        return 3
    if mbps < 250:
        return 4
    if mbps < 500:
        return 5
    return 6


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()                 # start an in-memory database
    con.execute("INSTALL httpfs; LOAD httpfs;")   # lets DuckDB read web files

    # The triple-quoted f-string lets us write a long SQL query over many lines.
    #
    # floor((tile_x + 11) / 0.05) turns a longitude into a column number:
    # every tile in the same 0.05 degree strip gets the same number, which
    # is how we group ~600 m tiles into bigger squares.
    #
    # The average is WEIGHTED by number of tests, so a tile with 500 tests
    # counts more than a tile with 2.
    # avg_d_kbps is kilobits per second; divide by 1000 for megabits.
    query = f"""
        SELECT
            floor((tile_x + 11) / {CELL})::INT   AS gx,
            floor((tile_y - 51) / {CELL})::INT   AS gy,
            sum(avg_d_kbps * tests) / sum(tests) / 1000  AS mbps,
            sum(tests)::INT                       AS tests
        FROM read_parquet('{URL}')
        WHERE tile_x BETWEEN -10.7 AND -5.4
          AND tile_y BETWEEN 51.35 AND 55.45
        GROUP BY gx, gy
    """
    print("Querying Ookla (only Ireland's tiles are downloaded)...")
    table = con.execute(query).df()   # .df() gives a pandas table
    print(f"  got {len(table)} grid squares")

    # Turn each (gx, gy) number pair back into a square on the map.
    # .apply(..., axis=1) runs a function on every ROW of the table.
    table["geometry"] = table.apply(
        lambda r: box(-11 + r.gx * CELL, 51 + r.gy * CELL,
                      -11 + (r.gx + 1) * CELL, 51 + (r.gy + 1) * CELL),
        axis=1,
    )
    # "lambda" is a tiny unnamed function: lambda r: ... means "given row r, return ...".

    grid = gpd.GeoDataFrame(table, crs="EPSG:4326")
    grid["mbps"] = grid["mbps"].round(0)
    grid["speed_class"] = grid["mbps"].apply(speed_class)

    # Keep only squares whose centre is on (or very near) the island,
    # which drops tiles from Scotland's Kintyre peninsula and the sea.
    island = gpd.read_file(OUT / "ireland_outline.geojson").union_all().buffer(0.03)
    grid = grid[grid.representative_point().within(island)]

    grid[["mbps", "tests", "speed_class", "geometry"]].to_file(
        OUT / "broadband_grid.geojson", driver="GeoJSON", COORDINATE_PRECISION=4
    )
    print(f"  saved {len(grid)} squares. Median speed: {grid['mbps'].median():.0f} Mbps")
    print("All data ready. Open index.html with the Live Server extension in VS Code.")
