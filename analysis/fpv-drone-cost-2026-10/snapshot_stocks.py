"""Freeze the four small-drone stocks "at time of writing" for the home card and the post.

The post is dated Thu 2026-10-08, so the reference is the last close before it (Wed 2026-10-07). The history starts
on 2026-07-01 (the full run since Spiderweb is in the post's own chart). Run once; the page compares this snapshot with the live
/api/quote.
"""

import json
from pathlib import Path

import yfinance as yf

POST_DATE = "2026-10-08"
HISTORY_START = "2026-07-01"
TICKERS = {t: ("USD", "America/New_York", "ET") for t in ["UMAC", "RCAT", "AVAV", "LMT"]}
OUT = Path(__file__).parents[2] / "src" / "data" / "fpv-drone-cost-2026-10" / "stocks_snapshot.json"


def main():
    snapshot = {"post_date": POST_DATE, "source": "Yahoo Finance via yfinance (daily close, unadjusted)", "tickers": {}}
    for t, (currency, tz, tz_label) in TICKERS.items():
        hist = yf.Ticker(t).history(start=HISTORY_START, end=POST_DATE, auto_adjust=False)["Close"]
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
