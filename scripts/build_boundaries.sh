#!/bin/sh
# Build data/counties.geojson: the 32 traditional counties used by the GAA.
#
#   Republic (26): Tailte Éireann, Counties - National Statutory Boundaries 2019,
#                  generalised 20m. © Tailte Éireann, CC BY 4.0.
#                  Supplied in Irish Transverse Mercator (EPSG:2157).
#   Northern Ireland (6): OpenStreetMap historic county relations, via
#                  polygons.openstreetmap.fr. © OpenStreetMap contributors, ODbL.
#
# Run from the gaa-map folder:  sh scripts/build_boundaries.sh
set -e
SRC=source/boundaries
TMP=$(mktemp -d)
ITM="+proj=tmerc +lat_0=53.5 +lon_0=-8 +k=0.99982 +x_0=600000 +y_0=750000 +ellps=GRS80 +units=m +no_defs"
MS="npx -y mapshaper@0.6.102"

# 1. Republic: reproject ITM -> WGS84, keep a title-case name
$MS "$SRC/tailte_eireann_counties_2019_20m.geojson" \
  -proj from="$ITM" crs=wgs84 \
  -each 'name = COUNTY.charAt(0) + COUNTY.slice(1).toLowerCase(), juris = "ROI"' \
  -filter-fields name,juris \
  -o "$TMP/roi.geojson"

# 2. Northern Ireland: wrap each OSM relation geometry as a named feature
python3 -I - "$SRC" "$TMP/ni.geojson" <<'EOF'
import json, sys
src, out = sys.argv[1], sys.argv[2]
ni = {1117773: "Tyrone", 1118085: "Fermanagh", 1119533: "Down",
      1119534: "Antrim", 1119535: "Armagh", 1959598: "Derry"}
feats = [{"type": "Feature", "properties": {"name": n, "juris": "NI"},
          "geometry": json.load(open(f"{src}/osm_relation_{i}.geojson"))} for i, n in ni.items()]
json.dump({"type": "FeatureCollection", "features": feats}, open(out, "w"))
EOF

# 3. Merge, simplify for the web, write
$MS -i "$TMP/roi.geojson" "$TMP/ni.geojson" combine-files \
  -merge-layers force \
  -clean \
  -simplify 4% keep-shapes \
  -filter-slivers min-area=2km2 \
  -o precision=0.001 format=geojson data/counties.geojson

rm -rf "$TMP"
