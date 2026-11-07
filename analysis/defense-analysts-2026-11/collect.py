"""Download daily prices for the defense analysts study.

Output: raw/prices/<TICKER>.csv   daily open/high/low/close, unadjusted (Yahoo Finance via yfinance)

Analyst ratings and targets are not scraped: they were read from the stockanalysis.com forecast pages on
2026-11-07 and are typed into analyze.py (RATINGS), with the date of each target cut.
"""

from pathlib import Path

import yfinance as yf

HERE = Path(__file__).parent
RAW = HERE / "raw" / "prices"
PRICES_FROM = "2025-10-01"
PRICES_TO = "2026-11-07"  # exclusive: last close is Fri 2026-11-06

# Six old prime contractors, two drone makers and Palantir; SPY (S&P 500) and ITA (US aerospace & defense ETF) for comparison.
TICKERS = ["LMT", "RTX", "NOC", "GD", "LHX", "HII", "KTOS", "AVAV", "PLTR", "SPY", "ITA"]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for t in TICKERS:
        hist = yf.Ticker(t).history(start=PRICES_FROM, end=PRICES_TO, auto_adjust=False)
        hist.index = hist.index.strftime("%Y-%m-%d")
        hist[["Open", "High", "Low", "Close"]].round(4).to_csv(RAW / f"{t}.csv", index_label="date")
        print(t, len(hist), hist.index[-1], round(float(hist["Close"].iloc[-1]), 2))


if __name__ == "__main__":
    main()
