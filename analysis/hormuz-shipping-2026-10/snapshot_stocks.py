"""Freeze Frontline (FRO) and the Brent oil fund (BNO) "at time of writing" for the home card and the post.

Frontline is one of the largest crude tanker owners; BNO tracks Brent futures, so the pair shows who is paid for the
closed strait and what the oil itself does. The post is dated Tue 2026-10-06, so the reference is the last close before
it (Mon 2026-10-05). The history starts at the last close before the war (Fri 2026-02-27).
Run once; the page compares this frozen snapshot with the live /api/quote.
"""

import json
from pathlib import Path

import yfinance as yf

POST_DATE = "2026-10-06"
HISTORY_START = "2026-02-27"
TICKERS = {"FRO": ("USD", "America/New_York", "ET"), "BNO": ("USD", "America/New_York", "ET")}
OUT = Path(__file__).parents[2] / "src" / "data" / "hormuz-shipping-2026-10" / "stocks_snapshot.json"


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
