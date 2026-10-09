"""Freeze Toyota / BYD / Tesla share prices "at time of writing".

The makers of the cars that won from the oil shock: Toyota (hybrids), BYD (EVs and plug-ins)
and the best-known EV maker, Tesla.

The post is dated Fri 2026-10-09, so the reference is the last close before it (Thu 2026-10-08).
The history starts at the last close before the oil shock (Fri 2026-02-27), so the tracker chart shows
the war and everything after. Run once; the page compares this frozen snapshot with the live /api/quote.
"""

import json
from pathlib import Path

import yfinance as yf

POST_DATE = "2026-10-09"
HISTORY_START = "2026-02-27"
# Home listing of each carmaker: Yahoo symbol -> (currency, exchange time zone, label for "last trade" times).
TICKERS = {
    "7203.T": ("JPY", "Asia/Tokyo", "Tokyo time"),
    "1211.HK": ("HKD", "Asia/Hong_Kong", "Hong Kong time"),
    "TSLA": ("USD", "America/New_York", "ET"),
}
OUT = Path(__file__).parents[2] / "src" / "data" / "ev-vs-petrol-2026-10" / "stocks_snapshot.json"


def main():
    snapshot = {"post_date": POST_DATE, "source": "Yahoo Finance via yfinance (daily close, unadjusted)", "tickers": {}}
    for t, (currency, tz, tz_label) in TICKERS.items():
        hist = yf.Ticker(t).history(start=HISTORY_START, end=POST_DATE, auto_adjust=False)["Close"].dropna()
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
