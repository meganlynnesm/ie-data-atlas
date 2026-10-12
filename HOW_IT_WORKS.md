# How it works

This guide explains the whole project in plain language, from downloading data to
the 3D animation. Read it alongside the code: every file also has comments that
explain each block as you go.

---

## The big picture

The project has two halves, written in two languages:

```
 PYTHON (scripts/)                         WEB PAGE (index.html, css/, js/)
 runs once, on your computer               runs every time someone opens the page

 01_fetch_osm.py      download from OSM
        │
 02_make_base.py      island + counties
        │
 03_process_layers.py clean + grid          ──►  data/processed/*.geojson  ──►  map.js reads them,
        │                                                                        draws 5 layers,
 04_fetch_broadband.py Ookla speeds                                              animates them
        │
 05_peat_soils.py     IPSM peat raster
```

**Why split it like this?** Downloading and cleaning data is slow and only needs to
happen once. Python is good at that. Drawing and animating is what web pages are good
at, and a web page can be shared with a link. The two halves only meet through the
GeoJSON files in `data/processed/`.

This is the same workflow you'd use in QGIS (download → clip → dissolve → export →
lay out), written as steps you can re-run with one command.

---

## Part 1: The data pipeline (Python)

### Setting up Python (once)

1. Install Python from [python.org](https://www.python.org/downloads/). On Windows,
   **tick "Add python.exe to PATH"** on the first screen of the installer.
2. In VS Code, install the **Python** extension (by Microsoft).
3. Open a terminal in VS Code: **Terminal → New Terminal**. Check Python works:
   ```
   python --version
   ```
4. Install the packages this project uses:
   ```
   pip install -r requirements.txt
   ```
   `requirements.txt` is just a list of package names. `pip` is Python's app store.

### Re-running the data pipeline

From the terminal, in the repo folder, run each step in order:

```
python scripts/01_fetch_osm.py
python scripts/02_make_base.py
python scripts/03_process_layers.py
python scripts/04_fetch_broadband.py
python scripts/05_peat_soils.py
```

Step 5 needs one manual download first: get `IPSM_shared_june24.zip` from
[osf.io/download/jwg6f](https://osf.io/download/jwg6f/) and unzip it into `data/raw/`.

Each one prints what it did and tells you the next step.

### What each step does

**01 · Fetch from OpenStreetMap.** OSM is a giant map database. We send it questions
through the *Overpass API*, in a small query language. For example, "every wind farm
in Ireland" is:

```
nwr["power"="plant"]["plant:source"="wind"](area.a);
out center tags;
```

Read it as: *nodes, ways and relations (`nwr`) tagged `power=plant` AND
`plant:source=wind`, inside area `a`; send back their centre points and tags.*
Try pasting queries into [overpass-turbo.eu](https://overpass-turbo.eu): it shows the
result on a map, which is the fastest way to learn.

**02 · Base map.** Downloads Natural Earth boundaries, keeps Ireland and Northern
Ireland, clips, simplifies, and dissolves the counties into one island outline.
`geopandas` works like a QGIS attribute table you control with code:

| QGIS | geopandas |
|------|-----------|
| Select by attribute | `world[world["adm0_a3"] == "IRL"]` |
| Clip | `.clip(box)` |
| Simplify | `.simplify(0.002)` |
| Dissolve | `.union_all()` |
| Reproject | `.to_crs("EPSG:2157")` |
| Export | `.to_file("x.geojson")` |

**03 · Clean the layers.**
- Turns raw OSM answers into tidy GeoJSON with only the columns we need.
- Reads messy capacity tags ("57.6 MW", "7500 kW") into numbers using a
  *regular expression*, a pattern for finding text.
- Turns thousands of bog outlines into a grid. Each ~1.3 km square gets a number
  from 0 to 1: how much of it is bog. To measure area properly it switches to
  **Irish Transverse Mercator (EPSG:2157)**, which is in metres. Degrees are not
  equal sizes on the ground, so you can't measure area in them.

**04 · Broadband.** Ookla publishes speed-test averages for the whole world as one
huge *Parquet* file. **DuckDB** can run a SQL query on that file over the internet
and download only the rows inside Ireland's box. The query also averages the small
Ookla tiles into bigger 0.05° squares, *weighted by the number of tests*.

**05 · Peat soils (raster).** Every layer so far was *vector* (points and shapes).
The Irish Peat Soils Map is a *raster*: a grid of 100 m pixels, like a photo, where
each pixel holds a number (0 = not peat, 1 = raised bog, 2 = lowland blanket bog, and
so on). The script reads it with `rasterio`, finds where every pixel is, converts
those positions from the Irish Grid (EPSG:29902, in metres) to longitude/latitude with
`pyproj`, and counts the pixels inside each of our ~1.3 km squares. Each square ends
up with two numbers: how much of its land is peat, and the most common peat type. In
QGIS terms, this is like *Zonal statistics* with a *majority* rule. The map only covers
the Republic, so the script fills Northern Ireland with the OSM bog squares from step 3.

### GeoJSON in 30 seconds

Open any file in `data/processed/` in VS Code. It is plain text:

```json
{ "type": "Feature",
  "geometry": { "type": "Point", "coordinates": [-6.38, 53.36] },
  "properties": { "name": "Equinix DB1", "operator": "Equinix" } }
```

Two things to remember: **longitude comes first**, and `properties` is the attribute
table row.

---

## Part 2: The web page

Three files, three jobs:

| File | Language | Job | Architecture analogy |
|------|----------|-----|----------------------|
| `index.html` | HTML | what is on the page | the plan: rooms and walls |
| `css/style.css` | CSS | how it looks | materials and finishes |
| `js/map.js` | JavaScript | what it does | the building systems: things that move |

### Why you need Live Server

Browsers block a page from reading files off your hard drive directly, for security.
Live Server runs a tiny local web server, so the page can load the GeoJSON files.
Opening `index.html` by double-clicking will show an error message instead of the map.

### How the map is drawn (map.js, steps 2 to 4)

1. **Load data.** `d3.json()` fetches each GeoJSON file. Because files take time to
   arrive, the code uses `async`/`await`, which means "wait here until it arrives".
2. **Project.** `d3.geoTransverseMercator().rotate([8, -53.5])` reproduces the Irish
   Transverse Mercator projection. It turns `[longitude, latitude]` into `[x, y]`
   pixels. `fitExtent` picks the zoom so Ireland fills the box.
3. **Draw.** Each layer is an SVG (a vector drawing, like an Illustrator file inside
   the page). D3's core pattern is:
   ```js
   g.selectAll("circle")
     .data(windFarms)        // one item per wind farm
     .join("circle")         // make one <circle> per item
     .attr("r", (f) => r(f.properties.mw));   // size from data
   ```
   Read it as: *for every wind farm, make a circle, and set its radius from its MW.*
   This "data → shapes → attributes from data" idea is what D3 is about.

**The winding-order gotcha.** In `map.js` you'll find `fixWinding()`. Python saves
polygon outlines anticlockwise, D3 expects clockwise, and if they disagree D3 fills
the whole planet *except* Ireland. Every D3 mapper hits this once.

### How the animation works (style.css section 5, map.js step 7)

This is the key trick: **the whole animation is one number.**

`--t` is a CSS variable that goes from `0` (flat) to `1` (axonometric). Every 3D
setting is written as *something × t*:

```css
.stack {
  transform:
    rotateX(calc(var(--t) * var(--tilt)))   /* tip back: 0° → 60° */
    rotateZ(calc(var(--t) * var(--spin)));  /* turn: 0° → -38° */
}
.plane {
  transform: translateZ(calc(var(--i) * var(--gap) * var(--t)));  /* lift layer i */
}
```

At `t = 0` everything is multiplied by zero, so it's a flat map. At `t = 1` you get
the full exploded view. Anything in between is part-way. JavaScript only has to move
`t` smoothly, which `animateTo()` does about 60 times a second with
`requestAnimationFrame`. The slider sets `t` directly, so you can scrub through it.

**Why it's a true axonometric:** there is no CSS `perspective`, so things further
away don't get smaller. Parallel lines stay parallel, like a hand-drawn axon.

**The poles** (vertical lines through Dublin, Cork and so on) are thin `div`s stood
upright with `rotateX(90deg)`. Their labels are rotated back by the same angles in
reverse, so the text always faces you.

---

## Things to try (good ways to learn)

Start easy, then go further. Save the file and Live Server reloads by itself.

1. **Change the camera.** In `style.css`, edit `--tilt`, `--spin` and `--gap` at the
   top. Try `--tilt: 45deg` or `--gap: 220px`.
2. **Change a colour.** In `map.js`, find the peatland layer and change
   `C.pistache` to `C.rose`.
3. **Change the timing.** In `setupAnimation()`, change `animateTo(1)` to
   `animateTo(1, 5000)` for a slow 5-second expand.
4. **Add a pole.** Add a line to `POLES` in `map.js`, for example
   `{ lonlat: [-8.63, 52.66], label: "Limerick", side: "right" },`.
5. **Ask OSM something new.** Open overpass-turbo.eu and try
   `nwr["power"="substation"]({{bbox}}); out center;` over Dublin.
6. **Add a whole layer.** Add a query in `01_fetch_osm.py`, a cleaning function in
   `03_process_layers.py`, then a new entry in the `LAYERS` list in `map.js`. The
   legend, label and plane are built for you from that list.

When something breaks, open the browser's developer tools (**F12** → **Console**).
Errors there say which file and line went wrong.

---

## Saving your work to GitHub

In VS Code's **Source Control** panel: type a short message, click **Commit**, then
**Sync Changes**. To share a live link, turn on GitHub Pages: on GitHub, go to
**Settings → Pages**, choose branch **main**, folder **/ (root)**, and save.
