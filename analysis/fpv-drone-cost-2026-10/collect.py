"""Download the map outlines, share prices and SEC filings data for the FPV drone cost study.

Output: raw/ukraine.geojson         Ukraine's internationally recognised border (geoBoundaries gbOpen, CC BY 4.0)
        raw/company_tickers.json    SEC ticker -> CIK map
        raw/facts/<TICKER>.json     XBRL company facts (annual revenue) from SEC EDGAR
        raw/prices/<TICKER>.csv     daily close (Yahoo Finance via yfinance)
        raw/wiki/*.txt              Wikipedia plain-text extracts (a pointer to the primary reporting they cite)
        raw/wiki/coordinates.json   coordinates of the air bases and ports (Wikipedia)
"""

import json
import time
from pathlib import Path

import requests
import yfinance as yf

HERE = Path(__file__).parent
RAW = HERE / "raw"

# SEC asks automated clients to identify themselves and stay under 10 requests a second.
SEC_HEADERS = {"User-Agent": "Data Notes research contact@datanotes.org"}
UKRAINE = "https://github.com/wmgeolab/geoBoundaries/raw/main/releaseData/gbOpen/UKR/ADM0/geoBoundaries-UKR-ADM0_simplified.geojson"
PRICES_FROM = "2025-01-01"
PRICES_TO = "2026-10-08"  # exclusive: last close is Wed 2026-10-07

# Listed US companies tied to small attack drones: makers (AVAV, RCAT), a parts supplier (UMAC),
# and the maker of the missile a drone replaces (LMT, Javelin). SPY is the market for comparison.
TICKERS = ["AVAV", "RCAT", "UMAC", "LMT"]
BENCHMARK = "SPY"
WIKI_PAGES = {
    "spiderweb": "Operation Spiderweb",
    "tu95": "Tupolev Tu-95",
    "tu22m": "Tupolev Tu-22M",
}
# Spiderweb's five air bases and the oil ports on the Baltic Sea hit by long-range drones in 2026.
PLACES = [
    "Belaya air base", "Olenya airbase", "Dyagilevo air base", "Ivanovo Severny air base", "Ukrainka (air base)",
    "Ust-Luga", "Primorsk, Leningrad Oblast",
]


def get(url, path, headers=SEC_HEADERS, params=None):
    if path.exists():
        return path.read_bytes()
    for attempt in range(3):
        try:
            res = requests.get(url, headers=headers, params=params, timeout=120)
            res.raise_for_status()
            break
        except requests.RequestException as err:
            print(f"{path.name}: attempt {attempt + 1} failed ({err})")
            time.sleep(2)
    else:
        raise SystemExit(f"could not download {url}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(res.content)
    time.sleep(0.15)
    return res.content


def main():
    get(UKRAINE, RAW / "ukraine.geojson", headers={"User-Agent": SEC_HEADERS["User-Agent"]})

    tickers = json.loads(get("https://www.sec.gov/files/company_tickers.json", RAW / "company_tickers.json"))
    ciks = {row["ticker"]: int(row["cik_str"]) for row in tickers.values()}
    for t in TICKERS:
        get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{ciks[t]:010d}.json", RAW / "facts" / f"{t}.json")

    (RAW / "prices").mkdir(parents=True, exist_ok=True)
    for t in TICKERS + [BENCHMARK]:
        path = RAW / "prices" / f"{t}.csv"
        if not path.exists():
            yf.Ticker(t).history(start=PRICES_FROM, end=PRICES_TO, auto_adjust=False)[["Close", "Adj Close"]].to_csv(path)

    for key, title in WIKI_PAGES.items():
        params = {"action": "query", "prop": "extracts", "explaintext": 1, "titles": title, "format": "json", "formatversion": 2}
        data = json.loads(get("https://en.wikipedia.org/w/api.php", RAW / "wiki" / f"{key}.json", {"User-Agent": SEC_HEADERS["User-Agent"]}, params))
        (RAW / "wiki" / f"{key}.txt").write_text(data["query"]["pages"][0]["extract"], encoding="utf-8")

    params = {"action": "query", "prop": "coordinates", "titles": "|".join(PLACES), "format": "json", "formatversion": 2}
    get("https://en.wikipedia.org/w/api.php", RAW / "wiki" / "coordinates.json", {"User-Agent": SEC_HEADERS["User-Agent"]}, params)


if __name__ == "__main__":
    main()
