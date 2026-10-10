"""Freeze Valero / Old Dominion / Scorpio Tankers share prices "at time of writing".

Who should feel cheaper diesel: a refiner that sells it (Valero), a trucker that burns it (Old Dominion)
and a tanker owner that carries it (Scorpio Tankers).

The post is dated Sat 2026-10-10, so the reference is the last close before it (Fri 2026-10-09, the day of the deal).
The history starts at the last close before the oil shock (Fri 2026-02-27), so the tracker chart shows
the war and everything after. Run once; the page compares this frozen snapshot with the live /api/quote.
"""

import json
from pathlib import Path

import yfinance as yf

POST_DATE = "2026-10-10"
HISTORY_START = "2026-02-27"
TICKERS = {t: ("USD", "America/New_York", "ET") for t in ("VLO", "ODFL", "STNG")}
OUT = Path(__file__).parents[2] / "src" / "data" / "russian-diesel-deal-2026-10" / "stocks_snapshot.json"


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
