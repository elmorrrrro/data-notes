"""Download the filings and results each hedge figure comes from, plus daily prices.

Output: raw/<name>.<ext>  the source documents (git-ignored, third-party content stays local)
        raw/prices.csv     daily closes for the 10 airlines and Brent crude (Yahoo Finance via yfinance)

The hedge percentages themselves are typed into analyze.py with the exact quote and the
source name, because they sit in PDFs and earnings calls rather than in a machine-readable table.
"""

from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

HERE = Path(__file__).parent
RAW = HERE / "raw"

# SEC asks automated clients to identify themselves with a name and an email address.
SEC_HEADERS = {"User-Agent": "Data Notes research contact@datanotes.org"}
WEB_HEADERS = {"User-Agent": "Mozilla/5.0 (Data Notes research)"}

SOURCES = {
    "aal-10q-2026q2.htm": "https://www.sec.gov/Archives/edgar/data/6201/000000620126000052/aal-20260630.htm",
    "aal-10k-2025.htm": "https://www.sec.gov/Archives/edgar/data/6201/000000620126000014/aal-20251231.htm",
    "ual-10q-2026q2.htm": "https://www.sec.gov/Archives/edgar/data/100517/000010051726000139/ual-20260630.htm",
    "ual-10k-2025.htm": "https://www.sec.gov/Archives/edgar/data/100517/000010051726000023/ual-20251231.htm",
    "dal-10q-2026q2.htm": "https://www.sec.gov/Archives/edgar/data/27904/000002790426000031/dal-20260630.htm",
    "luv-10q-2026q2.htm": "https://www.sec.gov/Archives/edgar/data/92380/000009238026000077/luv-20260630.htm",
    "alk-10q-2026q2.htm": "https://www.sec.gov/Archives/edgar/data/766421/000076642126000041/alk-20260630.htm",
    "alk-10k-2025.htm": "https://www.sec.gov/Archives/edgar/data/766421/000076642126000010/alk-20251231.htm",
    "ryanair-q1-fy27.pdf": "https://investor.ryanair.com/wp-content/uploads/2026/07/Q1-FY27-Ryanair-Results.pdf",
    "easyjet-q3-fy26.pdf": "https://s203.q4cdn.com/522538739/files/doc_financials/2026/q3/FY26-Q3-RNS-vf.pdf",
    "lufthansa-q2-2026-charts.pdf": "https://investor-relations.lufthansagroup.com/fileadmin/downloads/en/charts-speeches/LH-QR-2026-2-charts.pdf",
    "iag-h1-2026.pdf": "https://www.iairgroup.com/press-releases/2026/iag-half-year-results-2026/",
    "afklm-q2-2026.pdf": "https://www.airfranceklm.com/sites/default/files/2026-07/20260729-2026-q2-afklm-press-release-1.pdf",
}

# Yahoo symbols: each airline on its main listing (local currency), Brent front-month futures,
# and each region's broad market (S&P 500, STOXX Europe 600) to separate the fuel story from the market.
TICKERS = ["DAL", "UAL", "AAL", "LUV", "ALK", "RYA.IR", "IAG.L", "LHA.DE", "AF.PA", "EZJ.L", "BZ=F", "^GSPC", "^STOXX"]
PRICES_FROM = "2026-01-02"
PRICES_TO = "2026-10-03"  # exclusive: last close is Fri 2026-10-02


def main():
    RAW.mkdir(exist_ok=True)
    for name, url in SOURCES.items():
        if (RAW / name).exists():
            continue
        headers = SEC_HEADERS if "sec.gov" in url else WEB_HEADERS
        for attempt in range(3):
            try:
                res = requests.get(url, headers=headers, timeout=90)
                res.raise_for_status()
                break
            except requests.RequestException as err:
                print(f"{name}: attempt {attempt + 1} failed ({err})")
        else:
            print(f"{name}: SKIPPED, download it by hand from {url}")
            continue
        (RAW / name).write_bytes(res.content)
        print(f"{name}: {len(res.content) // 1024} KB")

    closes = {}
    for t in TICKERS:
        closes[t] = yf.Ticker(t).history(start=PRICES_FROM, end=PRICES_TO, auto_adjust=False)["Close"]
        # Exchanges sit in different time zones; keep the trading date only.
        closes[t].index = closes[t].index.strftime("%Y-%m-%d")
    pd.DataFrame(closes).sort_index().to_csv(RAW / "prices.csv", index_label="date")
    print("prices.csv:", {t: len(c) for t, c in closes.items()})


if __name__ == "__main__":
    main()
