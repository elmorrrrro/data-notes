"""Download everything the Russian-diesel-deal study needs into raw/ (git-ignored, third-party content stays local).

Output: raw/<EIA series>.xls   EIA history files (public domain):
          EMD_EPD2D_PTE_NUS_DPGw       US retail diesel, weekly ($/gal)
          EMM_EPMR_PTE_NUS_DPGw        US retail regular gasoline, weekly ($/gal)
          EER_EPD2DXL0_PF4_Y35NY_DPGd  New York Harbor ultra-low-sulfur diesel spot, daily ($/gal)
          WDIUPUS2w / WDIEXUS2w / WDIIMUS2w   US distillate product supplied / exports / imports, weekly (kb/d)
        raw/prices.csv          daily closes: diesel futures, Brent, refiners, product tankers, truckers, S&P 500 (Yahoo)
        raw/routes.json         sea distance from Russia's diesel ports to New York Harbor (searoute, nautical miles)
"""

import json
from pathlib import Path

import requests
import searoute
import yfinance as yf

HERE = Path(__file__).parent
RAW = HERE / "raw"

EIA = "https://www.eia.gov/dnav/pet/hist_xls/{}.xls"
SERIES = ["EMD_EPD2D_PTE_NUS_DPGw", "EMM_EPMR_PTE_NUS_DPGw", "EER_EPD2DXL0_PF4_Y35NY_DPGd",
          "WDIUPUS2w", "WDIEXUS2w", "WDIIMUS2w"]
BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/130.0 Safari/537.36"}

# HO=F: NYMEX ULSD (NY Harbor diesel) front month. Refiners: Valero, Marathon Petroleum, Phillips 66.
# Product tankers: Scorpio Tankers, International Seaways. Diesel buyers: Old Dominion, J.B. Hunt (trucking).
TICKERS = ["HO=F", "BZ=F", "VLO", "MPC", "PSX", "STNG", "INSW", "ODFL", "JBHT", "^GSPC"]
PRICES_FROM = "2026-01-02"
PRICES_TO = "2026-10-10"  # exclusive: last close is Fri 2026-10-09, the day of the deal

# Main Russian diesel export ports (Baltic and Black Sea) -> New York Harbor, [lon, lat].
PORTS = {"Primorsk": [28.62, 60.35], "Novorossiysk": [37.80, 44.72]}
NEW_YORK = [-74.05, 40.65]


def get(url, path, **kw):
    if path.exists():
        return
    res = requests.get(url, timeout=120, **kw)
    res.raise_for_status()
    path.write_bytes(res.content)
    print(path.name, len(res.content))


def main():
    RAW.mkdir(exist_ok=True)
    for s in SERIES:
        get(EIA.format(s), RAW / f"{s}.xls", headers=BROWSER)

    closes = yf.download(TICKERS, start=PRICES_FROM, end=PRICES_TO, auto_adjust=False, progress=False)["Close"]
    closes.to_csv(RAW / "prices.csv")
    print("prices", closes.shape, closes.index.max().date())

    routes = {p: round(searoute.searoute(o, NEW_YORK, units="naut").properties["length"]) for p, o in PORTS.items()}
    (RAW / "routes.json").write_text(json.dumps(routes, indent=1))
    print(routes)


if __name__ == "__main__":
    main()
