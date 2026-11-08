"""Build data/participation.json for the county-level prototype.

Population
  * Republic of Ireland: CSO table F1001 (population by county and sex, every
    census), read from source/cso_F1001_population_by_county_sex.json.
  * Northern Ireland: 2011 census population by historic county, scaled to the
    NI totals for 2001, 2011 and 2021. Female share assumed at 51%. Replace
    with NISRA small-area data aggregated to county when available.
  Years between censuses are interpolated linearly; years after the last
  census continue the last inter-census trend.

Players
  ILLUSTRATIVE ONLY. The per-county rates below are placeholders shaped to
  look plausible (strong hurling in the south-east, strong football in the
  west and Ulster, faster growth in female codes, a 2020-21 dip). Swap in real
  registration or team-entry figures by replacing PLAYER_RATES / trend() with
  data read from a CSV.

Usage: python3 scripts/build_data.py   (run from the gaa-map folder)
"""
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
YEARS = list(range(2005, 2026))

# ---------- population ----------

def roi_population():
    d = json.loads((ROOT / "source/cso_F1001_population_by_county_sex.json").read_text())
    dims = d["id"]
    sizes = d["size"]
    cats = {k: d["dimension"][k]["category"] for k in dims}
    idx = {k: cats[k]["index"] for k in dims}
    labels = {k: cats[k]["label"] for k in dims}
    county_dim = next(k for k in dims if d["dimension"][k]["label"] == "County")
    sex_dim = next(k for k in dims if d["dimension"][k]["label"] == "Sex")
    year_dim = next(k for k in dims if k.startswith("TLIST"))
    values = d["value"]

    def at(coords):
        pos = 0
        for k, s in zip(dims, sizes):
            pos = pos * s + coords.get(k, 0)
        return values[pos]

    out = {}
    for ci, ccode in enumerate(idx[county_dim]):
        name = labels[county_dim][ccode]
        if name == "State":
            continue
        out[name] = {}
        for yi, y in enumerate(idx[year_dim]):
            if int(y) < 2002:
                continue
            m = at({county_dim: ci, year_dim: yi, sex_dim: idx[sex_dim].index("1")})
            f = at({county_dim: ci, year_dim: yi, sex_dim: idx[sex_dim].index("2")})
            out[name][int(y)] = (m, f)
    return out


NI_2011 = {"Antrim": 618108, "Armagh": 174792, "Down": 531665,
           "Fermanagh": 61805, "Derry": 247132, "Tyrone": 177986}
NI_TOTAL = {2001: 1685267, 2011: 1810863, 2021: 1903175}


def ni_population():
    base = sum(NI_2011.values())
    out = {}
    for name, p in NI_2011.items():
        out[name] = {}
        for y, tot in NI_TOTAL.items():
            pop = p / base * tot
            out[name][y] = (round(pop * 0.49), round(pop * 0.51))
    return out


def interpolate(points, year):
    ys = sorted(points)
    if year <= ys[0]:
        lo, hi = ys[0], ys[1]
    elif year >= ys[-1]:
        lo, hi = ys[-2], ys[-1]
    else:
        lo = max(y for y in ys if y <= year)
        hi = min(y for y in ys if y > year)
        if lo == year:
            return points[lo]
    t = (year - lo) / (hi - lo)
    return tuple(round(a + (b - a) * t) for a, b in zip(points[lo], points[hi]))

# ---------- illustrative players ----------

# Players per 1,000 people of the same sex in 2025: hurling, football, camogie, ladies football
PLAYER_RATES = {
    "Antrim": (14, 14, 10, 6), "Armagh": (6, 38, 6, 22), "Carlow": (22, 22, 10, 14),
    "Cavan": (3, 40, 2, 22), "Clare": (38, 24, 22, 14), "Cork": (34, 28, 24, 22),
    "Derry": (12, 40, 12, 16), "Donegal": (4, 34, 3, 22), "Down": (10, 28, 8, 14),
    "Dublin": (9, 14, 5, 11), "Fermanagh": (3, 36, 2, 16), "Galway": (34, 30, 22, 18),
    "Kerry": (12, 50, 6, 26), "Kildare": (10, 20, 6, 12), "Kilkenny": (48, 6, 30, 6),
    "Laois": (22, 24, 12, 16), "Leitrim": (2, 42, 1, 18), "Limerick": (34, 18, 18, 12),
    "Longford": (4, 34, 2, 16), "Louth": (4, 24, 3, 14), "Mayo": (6, 44, 4, 28),
    "Meath": (10, 30, 6, 22), "Monaghan": (3, 40, 2, 26), "Offaly": (30, 26, 18, 14),
    "Roscommon": (6, 40, 4, 18), "Sligo": (4, 34, 2, 14), "Tipperary": (46, 20, 28, 12),
    "Tyrone": (6, 42, 4, 26), "Waterford": (34, 18, 22, 20), "Westmeath": (18, 26, 8, 14),
    "Wexford": (32, 22, 22, 14), "Wicklow": (10, 24, 4, 14),
}
CODES = ["hurling", "football", "camogie", "ladies"]
START_FACTOR = {"hurling": 0.95, "football": 0.97, "camogie": 0.66, "ladies": 0.50}
COVID = {2020: 0.78, 2021: 0.9}


def trend(code, year, rng_offset):
    t = (year - YEARS[0]) / (YEARS[-1] - YEARS[0])
    start = START_FACTOR[code] * rng_offset
    # female codes grow along an S-curve, male codes drift gently
    s = 1 / (1 + math.exp(-8 * (t - 0.45))) if code in ("camogie", "ladies") else t
    f = start + (1 - start) * s
    return f * COVID.get(year, 1.0)


def main():
    pop_points = {**roi_population(), **ni_population()}
    juris = {n: ("NI" if n in NI_2011 else "ROI") for n in pop_points}
    rng = random.Random(42)
    counties = {}
    for name in sorted(pop_points):
        rates = dict(zip(CODES, PLAYER_RATES[name]))
        offsets = {c: rng.uniform(0.85, 1.15) for c in CODES}
        pop, players = {}, {c: {} for c in CODES}
        for y in YEARS:
            m, f = interpolate(pop_points[name], y)
            pop[y] = {"m": m, "f": f}
            for c in CODES:
                base = m if c in ("hurling", "football") else f
                noise = 1 + rng.uniform(-0.03, 0.03)
                players[c][y] = round(base / 1000 * rates[c] * trend(c, y, offsets[c]) * noise)
        counties[name] = {"juris": juris[name], "population": pop, "players": players}
    out = {
        "years": YEARS,
        "illustrative": True,
        "sources": {
            "population_roi": "CSO table F1001, census 2002-2022, interpolated",
            "population_ni": "2011 census by historic county, scaled to NISRA NI totals 2001/2011/2021; 51% female assumed",
            "players": "Illustrative placeholder figures, not real registrations",
            "boundaries": "Tailte Éireann county boundaries 2019, CC BY 4.0 (Republic); OpenStreetMap historic counties, ODbL (NI); simplified",
        },
        "counties": counties,
    }
    (ROOT / "data/participation.json").write_text(json.dumps(out, separators=(",", ":")))
    print(f"Wrote {len(counties)} counties x {len(YEARS)} years")


if __name__ == "__main__":
    main()
