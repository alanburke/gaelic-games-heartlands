# Gaelic Games Heartlands

An interactive map of where hurling, camogie, Gaelic football and ladies football are strongest across Ireland's 32 counties, measured against the population of the same sex in each county. Toggle the code, men or women (or women compared with men), and drag the timeline from 2005 to 2025.

**The player numbers are illustrative placeholders, not real registrations.** Population figures are real census data. Real registration figures have been requested from the GAA, the Camogie Association and the LGFA.

## Running locally

```sh
python3 -m http.server 8000
```

Then open http://localhost:8000.

## Data

- **Population (Republic):** CSO table F1001, census 2002–2022, by county and sex, interpolated between census years.
- **Population (Northern Ireland):** 2011 census by historic county, scaled to NISRA totals for 2001, 2011 and 2021, with a 51% female share assumed.
- **Boundaries (Republic):** Counties, National Statutory Boundaries 2019, © Tailte Éireann, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- **Boundaries (Northern Ireland):** historic counties © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL.

`scripts/build_data.py` builds `data/participation.json` and `scripts/build_boundaries.sh` builds `data/counties.geojson`. Both expect the raw source files in a `source/` folder, which isn't included here.

## Club map (work in progress)

`clubs.html` maps real registrations by club against the population of each club's area, as players per head or as total players. `club-areas.html` is an editor for which census electoral divisions belong to each club.

- **Player figures** live in `data/players/` (one CSV per county and code, listed in `manifest.json`). Anything in `data/private/` stays out of git.
- **Club areas:** `python3 scripts/build_club_areas.py galway` geocodes each club's places from `data/clubs/galway_clubs.csv` and gives every electoral division to the nearest club as a first guess. Fix it in the editor.
- **Run locally** with `python3 scripts/serve.py`, then open http://127.0.0.1:8766/clubs.html. This server also lets the editor save.
- **Population:** CSO Census 2022 Small Area Population Statistics by electoral division (CC BY 4.0). Electoral division boundaries © Tailte Éireann, CC BY 4.0. The raw downloads go in `source/`, which is excluded from git.
