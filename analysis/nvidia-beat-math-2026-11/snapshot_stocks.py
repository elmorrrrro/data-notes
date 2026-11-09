"""Freeze the Nvidia (NVDA) share price "at time of writing".

The post is dated Mon 2026-11-09 and written after the close, so the reference is that day's close.
The history starts on 2026-09-01, a month before the record close of Oct 6.
Run once; the page compares this frozen snapshot with the live /api/quote.
"""

import json
from pathlib import Path

import yfinance as yf

POST_DATE = "2026-11-09"
HISTORY_END = "2026-11-10"  # exclusive
HISTORY_START = "2026-09-01"
TICKERS = {"NVDA": ("USD", "America/New_York", "ET")}
OUT = Path(__file__).parents[2] / "src" / "data" / "nvidia-beat-math-2026-11" / "stocks_snapshot.json"


def main():
    snapshot = {"post_date": POST_DATE, "source": "Yahoo Finance via yfinance (daily close, unadjusted)", "tickers": {}}
    for t, (currency, tz, tz_label) in TICKERS.items():
        hist = yf.Ticker(t).history(start=HISTORY_START, end=HISTORY_END, auto_adjust=False)["Close"].dropna()
        last_day = hist.index[-1]
        snapshot["tickers"][t] = {
            "currency": currency,
            "tz": tz,
            "tz_label": tz_label,
            "close_date": last_day.strftime("%Y-%m-%d"),
            "close": round(float(hist.iloc[-1]), 2),
            "history": [{"date": d.strftime("%Y-%m-%d"), "close": round(float(v), 2)} for d, v in hist.items()],
        }
        print(t, last_day.date(), round(float(hist.iloc[-1]), 2), len(hist))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
