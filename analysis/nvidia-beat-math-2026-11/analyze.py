"""How big a beat does Nvidia need for its stock to go up after earnings?

For each of Nvidia's last 10 reports: revenue vs the analyst consensus, the forecast for the next quarter vs the
consensus for that quarter, and the stock's move from the close before the report to the next day's close.
Reports come after the US close, so the next trading day is the first full reaction.

Inputs: raw/prices.csv, raw/eps.csv, raw/estimates.json (from collect.py) and the table REPORTS below, collected by hand
from CNBC's earnings articles (LSEG consensus); the URL is kept next to every row.

Output: src/data/nvidia-beat-math-2026-11/{reports,summary}.json
        public/data/nvidia-beat-math-2026-11/nvidia-earnings-beats.csv
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
RAW = HERE / "raw"
ROOT = HERE.parents[1]
SLUG = "nvidia-beat-math-2026-11"
DATA = ROOT / "src" / "data" / SLUG
PUBLIC = ROOT / "public" / "data" / SLUG

# date, fiscal quarter, revenue, consensus, next-quarter guidance (midpoint), consensus for that quarter ($B), source.
# Consensus is LSEG as quoted by CNBC unless the note says otherwise.
REPORTS = [
    ("2024-05-22", "Q1 FY25", 26.04, 24.65, 28.0, 26.66, "https://www.business-standard.com/companies/news/nvidia-forecasts-quarterly-revenue-above-estimates-unveils-stock-split-124052301333_1.html", "Reuters (LSEG)"),
    ("2024-08-28", "Q2 FY25", 30.04, 28.70, 32.5, 31.77, "https://www.cnbc.com/2024/08/28/nvidia-nvda-earnings-report-q2-2025.html", "CNBC (LSEG); guidance consensus LSEG via Wccftech"),
    ("2024-11-20", "Q3 FY25", 35.08, 33.16, 37.5, 37.08, "https://www.cnbc.com/2024/11/20/nvidia-nvda-earnings-report-q3-2025.html", "CNBC (LSEG)"),
    ("2025-02-26", "Q4 FY25", 39.33, 38.05, 43.0, 41.78, "https://www.cnbc.com/2025/02/26/nvidia-nvda-earnings-report-q4-2025.html", "CNBC (LSEG)"),
    ("2025-05-28", "Q1 FY26", 44.06, 43.31, 45.0, 45.90, "https://www.cnbc.com/2025/05/28/nvidia-nvda-earnings-report-q1-2026.html", "CNBC (LSEG)"),
    ("2025-08-27", "Q2 FY26", 46.74, 46.06, 54.0, 53.10, "https://www.cnbc.com/2025/08/27/nvidia-nvda-earnings-report-q2-2026.html", "CNBC (LSEG)"),
    ("2025-11-19", "Q3 FY26", 57.01, 54.92, 65.0, 61.66, "https://www.cnbc.com/2025/11/19/nvidia-nvda-earnings-report-q3-2026.html", "CNBC (LSEG)"),
    ("2026-02-25", "Q4 FY26", 68.13, 66.20, 78.0, 72.60, "https://www.cnbc.com/investingclub/2026/02/25/nvidia-keeps-the-ai-party-alive-with-a-booming-quarter-and-even-better-outlook.html", "CNBC (LSEG)"),
    ("2026-05-20", "Q1 FY27", 81.62, 78.89, 91.0, 86.84, "https://www.cnbc.com/investingclub/2026/05/20/were-raising-our-price-target-on-nvidia-after-another-knockout-quarter-and-guide-.html", "CNBC (LSEG)"),
    ("2026-08-26", "Q2 FY27", 96.22, 92.165, 108.0, 104.20, "https://www.cnbc.com/investingclub/2026/08/26/nvidia-wows-wall-street-with-a-strong-quarter-eye-popping-sales-forecast.html", "CNBC (LSEG)"),
]
NEXT_REPORT = "2026-11-17"
GUIDE_Q3 = 108.0  # Nvidia's own forecast for the quarter it reports on Nov 17, $B (Aug 26, 2026 release)
RUN_DAYS = 20  # trading days before a report used for "how the stock ran into it"


def main():
    prices = pd.read_csv(RAW / "prices.csv", index_col="date", parse_dates=True)["close"]
    eps = pd.read_csv(RAW / "eps.csv", index_col="date", parse_dates=True)
    est = json.loads((RAW / "estimates.json").read_text(encoding="utf-8"))

    rows = []
    for d, q, rev, rev_c, guide, guide_c, url, src in REPORTS:
        day = pd.Timestamp(d)
        before, after = prices[:day], prices[day + pd.Timedelta(days=1):]
        e = eps.loc[day]
        rows.append({
            "date": d,
            "label": day.strftime("%b '%y"),
            "quarter": q,
            "revenue": rev,
            "revenue_consensus": rev_c,
            "revenue_beat_pct": round((rev / rev_c - 1) * 100, 2),
            "guidance": guide,
            "guidance_consensus": guide_c,
            "guidance_beat_pct": round((guide / guide_c - 1) * 100, 2),
            "eps": float(e["Reported EPS"]),
            "eps_consensus": float(e["EPS Estimate"]),
            "close_before": round(float(before.iloc[-1]), 2),
            "close_after": round(float(after.iloc[0]), 2),
            "move_pct": round((after.iloc[0] / before.iloc[-1] - 1) * 100, 2),
            "run_in_pct": round((before.iloc[-1] / before.iloc[-1 - RUN_DAYS] - 1) * 100, 2),
            "source": url,
            "source_note": src,
        })
    df = pd.DataFrame(rows)
    assert (df.eps > df.eps_consensus).all(), "every report should beat the EPS consensus"
    assert (df.revenue_beat_pct > 0).all(), "every report should beat the revenue consensus"

    # The split that best separates rises from falls on the revenue beat (checked, not assumed).
    cut = 4.4
    big, small = df[df.revenue_beat_pct >= cut], df[df.revenue_beat_pct < cut]
    street = est["0q"]["avg"] / 1e9
    corr = {c: round(float(np.corrcoef(df[c], df.move_pct)[0, 1]), 2) for c in ("revenue_beat_pct", "guidance_beat_pct", "run_in_pct")}
    now = prices[:"2026-11-09"]
    summary = {
        "n": len(df),
        "rises": int((df.move_pct > 0).sum()),
        "falls": int((df.move_pct < 0).sum()),
        "cut": cut,
        "big": {"n": len(big), "rises": int((big.move_pct > 0).sum())},
        "small": {"n": len(small), "rises": int((small.move_pct > 0).sum())},
        "corr": corr,
        "avg_rev_beat": round(float(df.revenue_beat_pct.mean()), 1),
        "max_guide_beat": df.loc[df.guidance_beat_pct.idxmax()][["label", "guidance_beat_pct", "move_pct"]].to_dict(),
        "next": {
            "date": NEXT_REPORT,
            "street": round(street, 1),
            "analysts": est["0q"]["analysts"],
            "guide": GUIDE_Q3,
            "need": round(street * (1 + cut / 100), 1),
            "avg_beat_rev": round(street * (1 + df.revenue_beat_pct.mean() / 100), 1),
            "street_next_q": round(est["+1q"]["avg"] / 1e9, 1),
            "run_in_pct": round(float(now.iloc[-1] / now.iloc[-1 - RUN_DAYS] - 1) * 100, 1),
            "close": round(float(now.iloc[-1]), 2),
            "close_date": now.index[-1].strftime("%Y-%m-%d"),
        },
        "min_run_in": round(float(df.run_in_pct.min()), 1),
    }
    DATA.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (DATA / "reports.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    (DATA / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    df.drop(columns=["label"]).to_csv(PUBLIC / "nvidia-earnings-beats.csv", index=False)
    print(df[["label", "revenue_beat_pct", "guidance_beat_pct", "run_in_pct", "move_pct"]].to_string(index=False))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
