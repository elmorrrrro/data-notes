"""Download everything the EV-vs-petrol study needs into raw/ (git-ignored, third-party content stays local).

Output: raw/oil_bulletin_history.xlsx   EU Weekly Oil Bulletin, pump prices with taxes, every EU country, 2005 onwards
        raw/eurostat_nrg_pc_204.json    household electricity prices by country, half-yearly (Eurostat)
        raw/eurostat_hicp_cp0451.json   EU monthly consumer price index for electricity (Eurostat)
        raw/acea/<Month_Year>.pdf       ACEA monthly new-car registration press releases (EU, by power source)
        raw/prices.csv                  daily closes for carmakers, their home stock markets and Brent (Yahoo Finance)
"""

from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

HERE = Path(__file__).parent
RAW = HERE / "raw"

OIL_BULLETIN = (
    "https://energy.ec.europa.eu/document/download/906e60ca-8b6a-44e7-8589-652854d2fd3f_en"
    "?filename=Weekly_Oil_Bulletin_Prices_History_maxTax_2005_onwards.xlsx"
)
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
# Band DC (2,500-4,999 kWh a year) is Eurostat's "typical household"; all taxes and levies included.
ELECTRICITY = dict(format="JSON", lang="EN", siec="E7000", nrg_cons="KWH2500-4999", unit="KWH", tax="I_TAX",
                   currency="EUR", sinceTimePeriod="2024-S1")
HICP = dict(format="JSON", lang="EN", coicop18="CP0451", geo="EU27_2020", unit="I25", sinceTimePeriod="2024-12")

# ACEA blocks plain scripts; a browser user agent gets the public PDFs.
ACEA_PDF = "https://www.acea.auto/files/Press_release_car_registrations_{}.pdf"
# July 2026 has no PDF at that address; analyze.py derives July from the year-to-date tables (Aug YTD - Jun YTD).
ACEA_MONTHS = [f"{m}_{y}" for y in (2025, 2026) for m in (
    "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
    if not (y == 2026 and m in ("July", "September", "October", "November", "December"))]
BROWSER = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/130.0 Safari/537.36"}

# Each carmaker on its home listing (local currency), its home market index, and Brent front-month futures.
TICKERS = ["TSLA", "1211.HK", "7203.T", "VOW3.DE", "BMW.DE", "STLAM.MI", "RNO.PA", "GM",
           "^GSPC", "^STOXX", "^N225", "^HSI", "BZ=F"]
PRICES_FROM = "2026-01-02"
PRICES_TO = "2026-10-09"  # exclusive: last close is Thu 2026-10-08


def get(url, path, **kw):
    if path.exists():
        return
    res = requests.get(url, timeout=120, **kw)
    res.raise_for_status()
    path.write_bytes(res.content)
    print(path.name, len(res.content))


def main():
    (RAW / "acea").mkdir(parents=True, exist_ok=True)
    get(OIL_BULLETIN, RAW / "oil_bulletin_history.xlsx")
    get(EUROSTAT + "nrg_pc_204", RAW / "eurostat_nrg_pc_204.json", params=ELECTRICITY)
    get(EUROSTAT + "prc_hicp_minr", RAW / "eurostat_hicp_cp0451.json", params=HICP)
    for m in ACEA_MONTHS:
        get(ACEA_PDF.format(m), RAW / "acea" / f"{m}.pdf", headers=BROWSER)

    closes = yf.download(TICKERS, start=PRICES_FROM, end=PRICES_TO, auto_adjust=False, progress=False)["Close"]
    closes.to_csv(RAW / "prices.csv")
    print("prices", closes.shape, closes.index.max().date())


if __name__ == "__main__":
    main()
