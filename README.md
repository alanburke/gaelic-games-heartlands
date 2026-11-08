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
