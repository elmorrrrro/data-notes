"""Download what the "How big a beat does Nvidia need?" study needs into raw/ (git-ignored).

Output: raw/prices.csv      daily closes of NVDA since Jan 2024 (Yahoo Finance, unadjusted)
        raw/eps.csv         EPS estimate vs reported EPS for every report (Yahoo Finance earnings calendar)
        raw/estimates.json  current revenue consensus for this quarter and next (Yahoo Finance)
"""

import json
from pathlib import Path

import yfinance as yf

HERE = Path(__file__).parent
RAW = HERE / "raw"
PRICES_FROM = "2024-01-01"
PRICES_TO = "2026-11-10"  # exclusive: last close is Mon 2026-11-09


def main():
    RAW.mkdir(exist_ok=True)
    t = yf.Ticker("NVDA")
    hist = t.history(start=PRICES_FROM, end=PRICES_TO, auto_adjust=False)["Close"].dropna()
    hist.index = hist.index.strftime("%Y-%m-%d")
    hist.rename("close").to_csv(RAW / "prices.csv", index_label="date")

    eps = t.get_earnings_dates(limit=16)
    eps.index = eps.index.strftime("%Y-%m-%d")
    eps.to_csv(RAW / "eps.csv", index_label="date")

    est = t.revenue_estimate
    out = {p: {"avg": float(est.at[p, "avg"]), "analysts": int(est.at[p, "numberOfAnalysts"])} for p in ("0q", "+1q")}
    (RAW / "estimates.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"closes: {len(hist)}, reports: {len(eps)}, estimates: {out}")


if __name__ == "__main__":
    main()
