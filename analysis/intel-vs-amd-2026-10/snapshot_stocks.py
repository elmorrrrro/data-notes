"""Freeze INTC / AMD share prices "at time of writing".

The post is dated Sat 2026-10-03, so the reference is the last close before it
(Fri 2026-10-02). Also stores a short history window for the indexed chart.
Run once; the page compares this frozen snapshot with the live /api/quote.
"""

import json
from pathlib import Path

import yfinance as yf

POST_DATE = "2026-10-03"
HISTORY_START = "2026-07-01"
TICKERS = ["INTC", "AMD"]
OUT = Path(__file__).parents[2] / "src" / "data" / "intel-vs-amd-2026-10" / "stocks_snapshot.json"


def main():
    snapshot = {"post_date": POST_DATE, "source": "Yahoo Finance via yfinance (daily close, unadjusted)", "tickers": {}}
    for t in TICKERS:
        hist = yf.Ticker(t).history(start=HISTORY_START, end=POST_DATE, auto_adjust=False)["Close"]
        last_day = hist.index[-1]
        snapshot["tickers"][t] = {
            "close_date": last_day.strftime("%Y-%m-%d"),
            "close": round(float(hist.iloc[-1]), 2),
            "history": [{"date": d.strftime("%Y-%m-%d"), "close": round(float(v), 2)} for d, v in hist.items()],
        }
        print(t, last_day.date(), round(float(hist.iloc[-1]), 2))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
