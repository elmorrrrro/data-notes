"""Fetch daily ship transits through the Strait of Hormuz (and comparison chokepoints) from IMF PortWatch.

Saves the raw API pages to raw/ (git-ignored). Source: IMF PortWatch, Daily Chokepoints Data
(https://portwatch.imf.org/), built from AIS satellite ship positions.
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path

RAW = Path(__file__).parent / "raw"
URL = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Chokepoints_Data/FeatureServer/0/query"
UA = "Data Notes research contact@datanotes.org"
PORTS = ["Strait of Hormuz", "Bab el-Mandeb Strait", "Suez Canal", "Cape of Good Hope"]
PAGE = 1000  # the service's maximum record count
# Jebel Ali (Dubai) port calls: ships there must cross Hormuz, so it checks whether the transit count misses ships.
PORT_URL = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Ports_Data/FeatureServer/0/query"
JEBEL_ALI = "port744"
# JODI Oil World Database: monthly crude exports reported by governments (Kuwait can only export through Hormuz).
JODI = "https://www.jodidata.org/_resources/files/downloads/oil-data/annual-csv/primary/{}.csv"
JODI_FILES = ["2025", "primaryyear2026"]


def fetch(where: str, url: str = URL) -> list[dict]:
    rows, offset = [], 0
    while True:
        q = urllib.parse.urlencode({
            "where": where,
            "outFields": "*",
            "orderByFields": "date",
            "resultOffset": offset,
            "resultRecordCount": PAGE,
            "f": "json",
        })
        with urllib.request.urlopen(urllib.request.Request(f"{url}?{q}", headers={"User-Agent": UA})) as r:
            page = json.load(r)
        feats = page.get("features", [])
        rows += [f["attributes"] for f in feats]
        if not page.get("exceededTransferLimit") or not feats:
            return rows
        offset += len(feats)


def main():
    RAW.mkdir(exist_ok=True)
    for old in RAW.glob("hormuz_*.json"):
        old.unlink()
    for port in PORTS:
        rows = fetch(f"portname='{port}'")
        name = port.lower().replace(" ", "_").replace("-", "_")
        (RAW / f"{name}.json").write_text(json.dumps(rows), encoding="utf-8")
        print(f"{port:22} {len(rows):5} days  {rows[0]['date']} .. {rows[-1]['date']}")
    rows = fetch(f"portid='{JEBEL_ALI}' AND date >= '2025-01-01'", PORT_URL)
    (RAW / "jebel_ali.json").write_text(json.dumps(rows), encoding="utf-8")
    print(f"{'Jebel Ali (port calls)':22} {len(rows):5} days")
    (RAW / "jodi").mkdir(exist_ok=True)
    for f in JODI_FILES:
        with urllib.request.urlopen(urllib.request.Request(JODI.format(f), headers={"User-Agent": UA})) as r:
            (RAW / "jodi" / f"{f}.csv").write_bytes(r.read())
    print("JODI primary oil      ", ", ".join(JODI_FILES))


if __name__ == "__main__":
    main()
