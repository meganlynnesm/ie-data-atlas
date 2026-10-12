# Ireland Data Atlas

An animated map of the island of Ireland. It opens as a flat map with every layer
stacked on top of each other, then lifts apart into an exploded axonometric so each
layer can be read on its own:

| # | Layer | Source |
|---|-------|--------|
| 05 | Data centres | OpenStreetMap |
| 04 | Broadband speed | Ookla open data, Q2 2026 |
| 03 | Wind farms | OpenStreetMap |
| 02 | Peat soils, by type | Irish Peat Soils Map (Gilet et al. 2024), summarised to a ~1.3 km grid. Northern Ireland: OpenStreetMap bogs |
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
scripts/01..05_*.py   Python steps that download and clean the data
data/raw/             untouched downloads (made by script 01)
data/processed/       clean GeoJSON files the map reads
```

## Data notes and limits

- **OpenStreetMap is mapped by volunteers.** It shows what people have mapped, which
  is not always everything that exists.
- **The peat layer has two sources.** The Irish Peat Soils Map covers the Republic only.
  It uses a broad definition of peat (at least 10 cm of soil with 8.6% or more organic
  matter), so it includes shallow peat soils that older maps left out. Northern Ireland
  is filled with OpenStreetMap bogs, drawn as outlines, which show much less peat than
  really exists there.
- **Data centre counts are counts of mapped features.** One campus can be mapped as
  several buildings, so "85 near Dublin" means 85 mapped features, not 85 companies.
- **Ookla speeds come from speed tests people chose to run.** They show the average
  speed people actually get, which depends on the plan they pay for, not only on what
  the network can deliver. Squares with no tests are left blank.
- Data downloaded 12 October 2026.

## Credits and licences

- Peat soils: Gilet, L., Morley, T. and Flynn, R. (2024). *Geoderma*. Irish Peat
  Soils Map, [osf.io/27hj3](https://osf.io/27hj3/), CC BY 4.0.
- Data centres, wind farms, Northern Ireland bogs: © OpenStreetMap contributors, available under the
  [Open Database License (ODbL)](https://www.openstreetmap.org/copyright).
- Broadband: Speedtest® by Ookla® Global Fixed and Mobile Network Performance Maps.
  Based on analysis by Ookla of Speedtest Intelligence® data for Q2 2026.
  [CC BY-NC-SA 4.0](https://github.com/teamookla/ookla-open-data). Non-commercial use only.
- Boundaries: [Natural Earth](https://www.naturalearthdata.com/) (public domain).
- Code: MIT License (see `LICENSE`).
