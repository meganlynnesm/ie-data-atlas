"""
STEP 1: Download data from OpenStreetMap
========================================

What this script does
---------------------
Asks OpenStreetMap (OSM) for three things on the island of Ireland:
    1. data centres
    2. wind farms
    3. bogs (our "peatland" layer)
and saves each answer as a raw JSON file in data/raw/.

"Raw" means we save exactly what OSM sends back, untouched. Cleaning happens
in step 3. Keeping the raw file means you can re-run the cleaning step as
many times as you like without downloading everything again.

How we talk to OSM: the Overpass API
------------------------------------
OSM is a huge database. The "Overpass API" is a free website that lets you
send it a question (a "query") and get back only the features you asked for.
You can test any query below by pasting it into https://overpass-turbo.eu
and clicking "Run". That is the best way to learn the query language.

How to run this script
----------------------
In the VS Code terminal (Terminal > New Terminal), from the repo folder:
    python scripts/01_fetch_osm.py
"""

# ---------------------------------------------------------------------------
# IMPORTS
# "import" loads code other people wrote so we can use it.
#   json    -> read and write .json files (built into Python)
#   time    -> lets us pause between requests (built into Python)
#   pathlib -> handles file and folder paths on Windows and Mac (built in)
#   requests-> sends web requests (install once with: pip install requests)
# ---------------------------------------------------------------------------
import json
import time
from pathlib import Path

import requests


# ---------------------------------------------------------------------------
# SETTINGS
# Variables written in ALL_CAPS are a Python convention meaning
# "a setting that doesn't change while the script runs".
# ---------------------------------------------------------------------------

# The web address we send our questions to.
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Path(__file__) is the location of THIS script. .parent goes up one folder
# (to scripts/), and .parent again goes up to the repo folder.
# The "/" operator joins folder names together into a path.
REPO = Path(__file__).parent.parent
RAW_FOLDER = REPO / "data" / "raw"

# This snippet of Overpass language defines our study area and names it ".a".
# It joins two areas:
#   - the Republic of Ireland (ISO country code IE)
#   - Northern Ireland (ISO region code GB-NIR)
# so together they cover the whole island.
AREA = """
(
  area["ISO3166-1"="IE"][admin_level=2];
  area["ISO3166-2"="GB-NIR"];
)->.a;
"""

# A dictionary ({ key: value }) holding one query per layer.
# The key becomes part of the output file name.
#
# Overpass syntax cheat sheet:
#   nwr            = nodes, ways AND relations (points, lines/shapes, groups)
#   ["key"="value"]  = only keep features with this OSM tag
#   ["key"~"a|b"]    = tag value matches a OR b (a "regular expression")
#   (area.a)       = only inside the area we named ".a" above
#   out center     = for shapes, just send back their centre point
#   out geom       = send back the full geometry (every vertex)
QUERIES = {
    # Data centres are tagged in a few different ways by different mappers,
    # so we ask for all three common tags and combine them inside ( ... ).
    "data_centres": """
        (
          nwr["telecom"="data_center"](area.a);
          nwr["building"="data_center"](area.a);
          nwr["man_made"="data_center"](area.a);
        );
        out center tags;
    """,

    # A wind FARM is tagged as a power plant whose source is wind.
    # (Individual turbines are power=generator. We want whole farms.)
    "wind_farms": """
        nwr["power"="plant"]["plant:source"="wind"](area.a);
        out center tags;
    """,

    # Bogs are wetlands with a "bog" type. We need their full outline
    # (out geom), not just a centre point, because we will measure area.
    "bogs": """
        (
          way["natural"="wetland"]["wetland"~"^(bog|string_bog|blanket_bog|raised_bog)$"](area.a);
          relation["natural"="wetland"]["wetland"~"^(bog|string_bog|blanket_bog|raised_bog)$"](area.a);
        );
        out geom;
    """,
}


# ---------------------------------------------------------------------------
# A FUNCTION is a reusable block of code. "def" defines it.
# This one takes a query (text) and returns the answer from Overpass.
# The "-> dict" part is a "type hint": a note saying it returns a dictionary.
# ---------------------------------------------------------------------------
def ask_overpass(query: str) -> dict:
    # Every query needs a header: answer in JSON, and allow up to 180 seconds.
    # The f"..." is an "f-string": anything inside { } gets filled in.
    full_query = f"[out:json][timeout:180];{AREA}{query}"

    # Overpass is a free shared service and sometimes says "too busy".
    # So we try up to 4 times, waiting a bit longer each time.
    for attempt in range(1, 5):
        print(f"  asking Overpass (attempt {attempt})...")
        response = requests.post(OVERPASS_URL, data={"data": full_query}, timeout=300)

        # Status code 200 means "OK". Anything else means try again.
        if response.status_code == 200:
            return response.json()  # turn the JSON text into a Python dict

        print(f"  server said {response.status_code}, waiting {attempt * 15}s")
        time.sleep(attempt * 15)

    # If we get here, all 4 attempts failed. "raise" stops the script
    # with an error message so you know something went wrong.
    raise RuntimeError("Overpass did not answer. Try again in a few minutes.")


# ---------------------------------------------------------------------------
# MAIN PART OF THE SCRIPT
# This "if" line means: only run the code below when this file is run
# directly (not when another script imports it). It is a Python habit.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Make the data/raw folder if it doesn't exist yet.
    RAW_FOLDER.mkdir(parents=True, exist_ok=True)

    # .items() gives us each (key, value) pair from the dictionary in turn.
    for name, query in QUERIES.items():
        print(f"Downloading {name}...")
        data = ask_overpass(query)

        # Save the answer to a file, e.g. data/raw/osm_wind_farms.json
        out_path = RAW_FOLDER / f"osm_{name}.json"
        out_path.write_text(json.dumps(data), encoding="utf-8")

        # len() counts items in a list.
        print(f"  saved {len(data['elements'])} features to {out_path.name}")

        # Be polite to the free server: pause before the next request.
        time.sleep(5)

    print("Done. Next, run: python scripts/02_make_base.py")
