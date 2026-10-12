# Ireland Data Atlas

An animated map of the island of Ireland. It opens as a flat map with every layer
stacked on top of each other, then lifts apart into an exploded axonometric so each
layer can be read on its own:

| # | Layer | Source |
|---|-------|--------|
| 05 | Data centres | OpenStreetMap |
| 04 | Broadband speed | Ookla open data, Q2 2026 |
| 03 | Wind farms | OpenStreetMap |
| 02 | Peatland (bog) | OpenStreetMap, summarised to a ~1.3 km grid |
| 01 | Island and counties | Natural Earth |

Made for GIS for Design Practices (G4DP), Assignment 01, GSAPP. This is the first
piece of a larger narrative atlas.

**New to code? Start with [HOW_IT_WORKS.md](HOW_IT_WORKS.md).** It walks through
every step in plain language.

## Quick start

1. Install the **Live Server** extension in VS Code.
2. Right-click `index.html` → **Open with Live Server**.

The processed data is already in `data/processed/`, so the map works straight away.
To rebuild the data yourself, see "Re-running the data pipeline" in HOW_IT_WORKS.md.

## Folder map

```
index.html            the page skeleton
css/style.css         the look, including the 3D axonometric
js/map.js             loads data, draws layers, runs the animation
scripts/01..04_*.py   Python steps that download and clean the data
data/raw/             untouched downloads (made by script 01)
data/processed/       clean GeoJSON files the map reads
```

## Data notes and limits

- **OpenStreetMap is mapped by volunteers.** It shows what people have mapped, which
  is not always everything that exists. The peatland layer in particular shows *less*
  bog than official land-cover maps (such as CORINE or the EPA's peatland maps), because
  many bogs are not yet drawn in OSM.
- **Data centre counts are counts of mapped features.** One campus can be mapped as
  several buildings, so "85 near Dublin" means 85 mapped features, not 85 companies.
- **Ookla speeds come from speed tests people chose to run.** They show the average
  speed people actually get, which depends on the plan they pay for, not only on what
  the network can deliver. Squares with no tests are left blank.
- Data downloaded 12 October 2026.

## Credits and licences

- Data centres, wind farms, bogs: © OpenStreetMap contributors, available under the
  [Open Database License (ODbL)](https://www.openstreetmap.org/copyright).
- Broadband: Speedtest® by Ookla® Global Fixed and Mobile Network Performance Maps.
  Based on analysis by Ookla of Speedtest Intelligence® data for Q2 2026.
  [CC BY-NC-SA 4.0](https://github.com/teamookla/ookla-open-data). Non-commercial use only.
- Boundaries: [Natural Earth](https://www.naturalearthdata.com/) (public domain).
- Code: MIT License (see `LICENSE`).
