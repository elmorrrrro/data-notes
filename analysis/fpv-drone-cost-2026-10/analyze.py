"""How much one drone costs, and how far it now reaches: Operation Spiderweb, the Baltic port strikes, the price ladder
from a $400 FPV to a $193,000 Javelin, and the listed US companies that sell small drones or what they replace.

Input:  raw/ (from collect.py) + the sourced constants below (press figures and budget lines typed by hand)
Output: src/data/fpv-drone-cost-2026-10/*.json   -> the web page
        exports/*.csv                            -> Power BI
        public/data/fpv-drone-cost-2026-10/*.csv -> download link on the page

Three questions:
1. How far from Ukraine were the targets of Spiderweb and the 2026 port strikes? (nearest point of the border)
2. What does a small attack drone cost next to the weapons it competes with?
3. How did the listed companies tied to small drones trade since Spiderweb, against the market?
"""

import json
import math
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
RAW = HERE / "raw"
SLUG = "fpv-drone-cost-2026-10"
ROOT = HERE.parents[1]
OUT_WEB = ROOT / "src" / "data" / SLUG
OUT_BI = HERE / "exports"
OUT_PUBLIC = ROOT / "public" / "data" / SLUG

BASE_DATE = "2025-05-30"  # last close before Spiderweb (Sun 2025-06-01)
END_DATE = "2026-10-07"  # last close before publication
WIKI_SW = "https://en.wikipedia.org/wiki/Operation_Spiderweb"
GEOBOUNDARIES = "https://www.geoboundaries.org/countryDownloads.html"

# Spiderweb, as reported. The $2,000 per drone and the $7B are Ukrainian officials' figures (WSJ, via Wikipedia);
# the US count is two US officials speaking to Reuters.
SPIDERWEB = {
    "date": "2025-06-01",
    "drones": 117,
    "drone_usd": 2_000,
    "claimed_hit": 41,
    "claimed_share_of_carriers": 0.34,
    "claimed_damage_usd": 7_000_000_000,
    "us_hit": 20,
    "us_destroyed": 10,
    "reported_belaya_km": 4_300,
    "source": WIKI_SW,
}

# Targets: Spiderweb's five air bases and the two Baltic oil ports. Coordinates come from Wikipedia (raw/wiki).
TARGETS = [
    {"title": "Belaya air base", "name": "Belaya", "kind": "air base", "event": "Spiderweb", "dates": "2025-06-01",
     "status": "hit", "note": "Tu-22M3 bombers, Irkutsk region", "source": WIKI_SW},
    {"title": "Olenya airbase", "name": "Olenya", "kind": "air base", "event": "Spiderweb", "dates": "2025-06-01",
     "status": "hit", "note": "Tu-95 bombers, Murmansk region, beyond the Arctic Circle", "source": WIKI_SW},
    {"title": "Ivanovo Severny air base", "name": "Ivanovo", "kind": "air base", "event": "Spiderweb", "dates": "2025-06-01",
     "status": "hit", "note": "A-50 radar planes", "source": WIKI_SW},
    {"title": "Dyagilevo air base", "name": "Dyagilevo", "kind": "air base", "event": "Spiderweb", "dates": "2025-06-01",
     "status": "hit", "note": "Ryazan region", "source": WIKI_SW},
    {"title": "Ukrainka (air base)", "name": "Ukrainka", "kind": "air base", "event": "Spiderweb", "dates": "2025-06-01",
     "status": "failed", "note": "the truck carrying the drones caught fire before launch", "source": WIKI_SW},
    {"title": "Ust-Luga", "name": "Ust-Luga", "kind": "oil port", "event": "Port strikes", "dates": "2026-03-31; 2026-08-14; 2026-09-01",
     "status": "hit", "note": "Russia's largest Baltic port, about 700,000 barrels of crude a day",
     "source": "https://www.themoscowtimes.com/2026/09/01/ukrainian-drone-attack-sparks-fire-at-ust-luga-port-a93612"},
    {"title": "Primorsk, Leningrad Oblast", "name": "Primorsk", "kind": "oil port", "event": "Port strikes", "dates": "2026-03-23; 2026-04-05; 2026-05-03",
     "status": "hit", "note": "oil terminal for about 1 million barrels a day",
     "source": "https://www.wsls.com/news/world/2026/05/03/ukraine-hits-key-russian-oil-loading-port-and-3-shadow-fleet-tankers/"},
]

# What one shot costs, US$ per unit. Budget lines are the Army's "all-up round"; press figures are as reported.
PRICES = [
    {"item": "Ukrainian FPV drone", "short": "Ukrainian FPV", "usd": 400, "kind": "small drone", "basis": "typical unit price, as reported",
     "source": "https://defence-blog.com/what-ukraines-drones-really-cost/"},
    {"item": "Osa drone used in Spiderweb", "short": "Spiderweb drone", "usd": 2_000, "kind": "small drone", "basis": "Ukrainian officials, via WSJ",
     "source": WIKI_SW},
    {"item": "US Army FPV target price", "short": "US Army FPV goal", "usd": 2_000, "kind": "small drone", "basis": "ceiling the Army asked industry for",
     "source": "https://www.govconwire.com/articles/neros-500m-army-archer-fpv-contract"},
    {"item": "US Marines FPV target price", "short": "US Marines FPV goal", "usd": 4_000, "kind": "small drone", "basis": "ceiling in a Dec 2025 request for 10,000",
     "source": "https://www.twz.com/air/marines-seeking-10000-first-person-view-drones-at-4k-a-pop"},
    {"item": "Switchblade 300 (AeroVironment)", "short": "Switchblade 300", "usd": 58_063, "kind": "loitering munition", "basis": "US Army FY2022 budget",
     "source": "https://www.19fortyfive.com/2023/04/the-u-s-army-wont-buy-anymore-switchblade-300-kamikaze-drones/"},
    {"item": "Javelin missile (Lockheed Martin / RTX)", "short": "Javelin missile", "usd": 192_772, "kind": "missile", "basis": "US Army FY2022 budget",
     "source": "https://www.twz.com/45132/as-ukraine-pummels-russians-with-javelin-missiles-can-production-keep-pace-with-demand"},
]

# Listed US companies tied to small attack drones. Roles as described in their filings and the cited reports.
COMPANIES = [
    {"ticker": "AVAV", "name": "AeroVironment", "role": "makes Switchblade loitering munitions",
     "source": "https://www.19fortyfive.com/2023/04/the-u-s-army-wont-buy-anymore-switchblade-300-kamikaze-drones/"},
    {"ticker": "RCAT", "name": "Red Cat", "role": "makes Black Widow for the US Army and FANG FPV drones",
     "source": "https://www.therobotreport.com/red-cat-wins-u-s-army-next-gen-drone-contract-over-skydio/"},
    {"ticker": "UMAC", "name": "Unusual Machines", "role": "makes FPV parts, including motors in Orlando",
     "source": "https://www.accessnewswire.com/newsroom/en/aerospace-and-defense/unusual-machines-accelerates-motor-factory-output-at-orlando-campus-1156555"},
    {"ticker": "LMT", "name": "Lockheed Martin", "role": "makes Javelin (with RTX), the missile FPVs undercut",
     "source": "https://www.twz.com/45132/as-ukraine-pummels-russians-with-javelin-missiles-can-production-keep-pace-with-demand"},
]
BENCHMARK = ("SPY", "S&P 500 (SPY)")


def haversine(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def ukraine_rings():
    geo = json.loads((RAW / "ukraine.geojson").read_text(encoding="utf-8"))["features"][0]["geometry"]
    polys = geo["coordinates"] if geo["type"] == "MultiPolygon" else [geo["coordinates"]]
    return [[(x, y) for x, y, *_ in poly[0]] for poly in polys]


def nearest_border(lat, lon, rings):
    """Shortest great-circle distance to Ukraine's border, with the border densified to ~1 km steps."""
    best = (float("inf"), None)
    for ring in rings:
        for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
            steps = max(1, int(haversine(y1, x1, y2, x2)))
            for k in range(steps + 1):
                x, y = x1 + (x2 - x1) * k / steps, y1 + (y2 - y1) * k / steps
                d = haversine(lat, lon, y, x)
                if d < best[0]:
                    best = (d, (round(x, 3), round(y, 3)))
    return best


def fy_revenue(ticker):
    """Latest full-year revenue from 10-K XBRL facts: (fiscal year end, US$)."""
    facts = json.loads((RAW / "facts" / f"{ticker}.json").read_text())["facts"].get("us-gaap", {})
    best = None
    for tag in ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"]:
        for u in facts.get(tag, {}).get("units", {}).get("USD", []):
            if u["form"].startswith("10-K") and "start" in u and 350 < (pd.Timestamp(u["end"]) - pd.Timestamp(u["start"])).days < 380:
                if best is None or u["end"] > best[0]:
                    best = (u["end"], u["val"])
    return best


def closes(ticker):
    px = pd.read_csv(RAW / "prices" / f"{ticker}.csv")
    px["date"] = px["Date"].str[:10]
    return px.set_index("date")["Close"]


def main():
    coords = {p["title"]: p["coordinates"][0] for p in json.loads((RAW / "wiki" / "coordinates.json").read_text())["query"]["pages"]}
    rings = ukraine_rings()
    targets = []
    for t in TARGETS:
        c = coords[t["title"]]
        km, (blon, blat) = nearest_border(c["lat"], c["lon"], rings)
        targets.append({**{k: v for k, v in t.items() if k != "title"}, "lat": c["lat"], "lon": c["lon"],
                        "km": round(km), "border_lat": blat, "border_lon": blon})
        print(f"{t['name']:10} {km:6.0f} km")

    # Outline for the map: every 4th vertex of the largest ring is plenty at page scale. geoBoundaries winds rings
    # counter-clockwise (RFC 7946); d3-geo reads that as "everything but Ukraine", so the ring is reversed.
    main_ring = max(rings, key=len)
    ring = [[round(x, 3), round(y, 3)] for x, y in main_ring[::4]]
    ring = (ring + ring[:1])[::-1]
    outline = {"type": "Feature", "properties": {"name": "Ukraine"}, "geometry": {"type": "Polygon", "coordinates": [ring]}}

    prices = [{**p, "x_fpv": round(p["usd"] / PRICES[0]["usd"], 1)} for p in PRICES]

    series, companies = [], []
    for ticker, label in [(c["ticker"], c["name"]) for c in COMPANIES] + [BENCHMARK]:
        s = closes(ticker)
        s = s[(s.index >= BASE_DATE) & (s.index <= END_DATE)]
        base = s.loc[BASE_DATE]
        for d, v in s.items():
            series.append({"ticker": ticker, "label": label, "date": d, "close": round(float(v), 2), "index": round(float(v / base * 100), 1)})
        if ticker != BENCHMARK[0]:
            info = next(c for c in COMPANIES if c["ticker"] == ticker)
            fy_end, rev = fy_revenue(ticker)
            companies.append({**info, "close_base": round(float(base), 2), "close_end": round(float(s.loc[END_DATE]), 2),
                              "change": round(float(s.loc[END_DATE] / base - 1), 4), "revenue_usd": rev, "fy_end": fy_end})
        else:
            spy_change = round(float(s.loc[END_DATE] / base - 1), 4)

    belaya = next(t for t in targets if t["name"] == "Belaya")
    stats = {
        **SPIDERWEB,
        "drones_cost_usd": SPIDERWEB["drones"] * SPIDERWEB["drone_usd"],
        "claimed_to_cost": round(SPIDERWEB["claimed_damage_usd"] / (SPIDERWEB["drones"] * SPIDERWEB["drone_usd"])),
        "belaya_km": belaya["km"],
        "ports_km": {t["name"]: t["km"] for t in targets if t["kind"] == "oil port"},
        "javelin_per_fpv": round(PRICES[-1]["usd"] / PRICES[0]["usd"]),
        "switchblade_per_fpv": round(PRICES[-2]["usd"] / PRICES[0]["usd"]),
        "base_date": BASE_DATE,
        "end_date": END_DATE,
        "spy_change": spy_change,
    }

    def dump(name, obj):
        (OUT_WEB / f"{name}.json").write_text(json.dumps(obj, indent=1, default=float), encoding="utf-8")

    for d in (OUT_WEB, OUT_BI, OUT_PUBLIC):
        d.mkdir(parents=True, exist_ok=True)
    dump("targets", targets)
    dump("ukraine", outline)
    dump("prices", prices)
    dump("stocks", series)
    dump("companies", companies)
    dump("stats", stats)

    frames = {"targets": pd.DataFrame(targets), "prices": pd.DataFrame(prices), "stock_index": pd.DataFrame(series),
              "companies": pd.DataFrame(companies)}
    for name, df in frames.items():
        df.to_csv(OUT_BI / f"{name}.csv", index=False)
        df.to_csv(OUT_PUBLIC / f"{name}.csv", index=False)

    print(json.dumps({k: v for k, v in stats.items() if k != "source"}, indent=1))
    for c in companies:
        print(c["ticker"], f"{c['change']:+.1%}", c["revenue_usd"], c["fy_end"])


if __name__ == "__main__":
    main()
