"""Build the small-area files the club map needs for one county.

Inputs
  data/clubs/<county>_clubs.csv     club, places (";"-separated; "Name@lat lon" pins one), confidence, note
  source/census2022/SAPS_2022_CSOED.csv      CSO Census 2022 SAPS by electoral division
  source/census2022/cso_ed_2022_20m.geojson  CSO Electoral Divisions 2022, generalised 20m
                                             (Tailte Éireann, CC BY 4.0, Irish Transverse Mercator)

Outputs
  data/clubs/<county>_eds.topo.json  electoral divisions with population by sex
  data/clubs/<county>_anchors.json   geocoded places for each club
  data/clubs/<county>_areas.json     which club each electoral division belongs to.
                                     Only written if missing (or with --reset), so edits
                                     made in club-areas.html are kept.

First guess at areas: each electoral division goes to the club with the nearest place,
if one is within MAX_KM. Edit the result in club-areas.html.

Places are geocoded with OpenStreetMap Nominatim (one request a second, cached in
source/geocode_cache.json).

Usage (from the repo root):  python3 scripts/build_club_areas.py galway [--reset]
"""
import csv
import json
import math
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source/census2022"
CACHE = ROOT / "source/geocode_cache.json"
MAX_KM = 12
UA = "gaelic-games-heartlands/0.1 (+https://github.com/alanburke/gaelic-games-heartlands)"
ITM = "+proj=tmerc +lat_0=53.5 +lon_0=-8 +k=0.99982 +x_0=600000 +y_0=750000 +ellps=GRS80 +units=m +no_defs"
# CSO county names that make up each GAA county (add Dublin, Cork etc. as needed)
CSO_COUNTIES = {
    "galway": {"GALWAY", "GALWAY CITY"},
    "cork": {"CORK", "CORK CITY"},
    "limerick": {"LIMERICK CITY AND COUNTY"},
    "waterford": {"WATERFORD CITY AND COUNTY"},
    "dublin": {"DUBLIN CITY", "FINGAL", "SOUTH DUBLIN", "DÚN LAOGHAIRE-RATHDOWN"},
    "tipperary": {"TIPPERARY"},
}


def geocode(place, county, cache):
    key = f"{place}|{county}"
    if key not in cache:
        q = urllib.parse.urlencode({"q": f"{place}, County {county.title()}, Ireland",
                                    "format": "jsonv2", "limit": 1, "countrycodes": "ie"})
        req = urllib.request.Request(f"https://nominatim.openstreetmap.org/search?{q}", headers={"User-Agent": UA})
        res = json.load(urllib.request.urlopen(req, timeout=30))
        time.sleep(1.1)
        cache[key] = [float(res[0]["lat"]), float(res[0]["lon"])] if res else None
        CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
    return cache[key]


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))


def centroid(geom):
    rings = [geom["coordinates"][0]] if geom["type"] == "Polygon" else [p[0] for p in geom["coordinates"]]
    pts = [pt for r in rings for pt in r]
    return [sum(p[1] for p in pts) / len(pts), sum(p[0] for p in pts) / len(pts)]


def main():
    county = sys.argv[1].lower()
    reset = "--reset" in sys.argv
    out = ROOT / "data/clubs"

    # 1. club places
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    anchors = {}
    for row in csv.DictReader(open(out / f"{county}_clubs.csv", encoding="utf-8")):
        pts = []
        for place in filter(None, (p.strip() for p in row["places"].split(";"))):
            # "Name@lat lon" pins a place by hand when the geocoder gets it wrong
            name, _, pin = place.partition("@")
            ll = [float(x) for x in pin.split()] if pin else geocode(name, county, cache)
            place = name
            if ll:
                pts.append({"place": place, "lat": ll[0], "lon": ll[1]})
            else:
                print(f"  not found: {place} ({row['club']})")
        anchors[row["club"]] = {"points": pts, "confidence": row["confidence"], "note": row["note"]}
    (out / f"{county}_anchors.json").write_text(json.dumps(anchors, indent=1, ensure_ascii=False))

    # 2. electoral divisions with population
    pop = {}
    for r in csv.DictReader(open(SRC / "SAPS_2022_CSOED.csv", encoding="latin-1")):
        pop[r["GUID"]] = (int(r["T1_1AGETF"]), int(r["T1_1AGETM"]))
    names = CSO_COUNTIES[county]
    eds = json.load(open(SRC / "cso_ed_2022_20m.geojson"))
    feats = []
    for f in eds["features"]:
        p = f["properties"]
        if p["COUNTY_ENGLISH"] not in names:
            continue
        pf, pm = pop[p["ED_GUID"]]
        feats.append({"type": "Feature", "geometry": f["geometry"],
                      "properties": {"id": p["ED_GUID"], "name": p["ED_ENGLISH"].title(), "f": pf, "m": pm}})
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "eds.geojson"
        raw.write_text(json.dumps({"type": "FeatureCollection", "features": feats}))
        wgs = Path(tmp) / "eds_wgs.geojson"
        ms = ["npx", "-y", "mapshaper@0.6.102", str(raw), "-proj", f"from={ITM}", "crs=wgs84",
              "-simplify", "8%", "keep-shapes"]
        subprocess.run(ms + ["-o", "precision=0.0001", str(wgs)], check=True)
        subprocess.run(ms + ["-rename-layers", "eds", "-o", "precision=0.0001", "format=topojson",
                             str(out / f"{county}_eds.topo.json")], check=True)
        feats = json.load(open(wgs))["features"]

    # 3. first guess at club areas
    areas_file = out / f"{county}_areas.json"
    if areas_file.exists() and not reset:
        print(f"Kept existing {areas_file.name} (use --reset to rebuild it)")
    else:
        assign = {}
        for f in feats:
            c = centroid(f["geometry"])
            best = min(((km(c, [pt["lat"], pt["lon"]]), club) for club, a in anchors.items() for pt in a["points"]),
                       default=(None, None))
            if best[0] is not None and best[0] <= MAX_KM:
                assign[f["properties"]["id"]] = best[1]
        areas_file.write_text(json.dumps({"county": county.title(), "method": f"nearest club place within {MAX_KM} km, then edited by hand",
                                          "assignments": assign}, indent=1, ensure_ascii=False))
        print(f"Assigned {len(assign)} of {len(feats)} electoral divisions")
    print(f"{len(feats)} electoral divisions, female population {sum(f['properties']['f'] for f in feats):,}")


if __name__ == "__main__":
    main()
