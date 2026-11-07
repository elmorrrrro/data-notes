"""Build the page data for the defense analysts study.

Input:  raw/prices/<TICKER>.csv (collect.py) and RATINGS / CUTS below (stockanalysis.com, read 2026-11-07)
Output: src/data/defense-analysts-2026-11/*.json      page data
        exports/*.csv                                  Power BI (git-ignored)
        public/data/defense-analysts-2026-11/*.csv     public download
"""

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
SLUG = "defense-analysts-2026-11"
RAW = HERE / "raw" / "prices"
OUT_DATA = ROOT / "src" / "data" / SLUG
OUT_PUBLIC = ROOT / "public" / "data" / SLUG
OUT_BI = HERE / "exports"

ASOF = "2026-11-06"          # last close before publication
YEAR_START = "2025-12-31"    # close used for "since the start of 2026"
HIGH_FROM = "2025-11-07"     # 52-week window for the high
ELECTION = ("2026-11-03", "2026-11-04")  # close before the midterm result -> close after

# Analyst ratings from the stockanalysis.com forecast pages, read 2026-11-07.
# buy = Strong Buy + Buy, sell = Sell + Strong Sell; targets are the average, lowest and highest 12-month target.
RATINGS = [
    # ticker, name, group, buy, hold, sell, avg, low, high
    ("LMT", "Lockheed Martin", "prime", 11, 12, 1, 660.86, 498, 835),
    ("RTX", "RTX", "prime", 16, 8, 0, 227.91, 200, 250),
    ("NOC", "Northrop Grumman", "prime", 16, 9, 1, 636.00, 430, 815),
    ("GD", "General Dynamics", "prime", 14, 9, 1, 418.59, 320, 480),
    ("LHX", "L3Harris", "prime", 13, 9, 0, 335.20, 241, 443),
    ("HII", "Huntington Ingalls", "prime", 6, 6, 0, 358.33, 281, 407),
    ("KTOS", "Kratos", "drones", 24, 1, 0, 89.56, 50, 150),
    ("AVAV", "AeroVironment", "drones", 19, 5, 0, 212.20, 148.57, 315),
    ("PLTR", "Palantir", "software", 22, 9, 2, 222.25, 80, 273),
]

# Kratos target cuts, Oct 30 - Nov 6, 2026. Every firm kept its Buy-equivalent rating.
CUTS = [
    ("2026-10-30", "B. Riley", "Buy", 128, 91),
    ("2026-11-02", "KeyBanc", "Overweight", 130, 75),
    ("2026-11-06", "Baird", "Outperform", 110, 75),
    ("2026-11-06", "BTIG", "Buy", 104, 65),
]

# Dated Kratos events marked on the price chart (sources in the post's Methodology).
EVENTS = [
    ("2026-02-27", "Sells ~$1B of new shares"),
    ("2026-11-04", "Midterms: Democrats take Congress"),
    ("2026-11-05", "Q3: sales +36%, cash flow negative"),
]


def prices(t):
    return pd.read_csv(RAW / f"{t}.csv", index_col="date")


def pct(a, b):
    return round((a / b - 1) * 100, 1)


def main():
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    OUT_PUBLIC.mkdir(parents=True, exist_ok=True)
    OUT_BI.mkdir(parents=True, exist_ok=True)

    stocks = []
    for t, name, group, buy, hold, sell, avg, low, high in RATINGS:
        p = prices(t)
        price = float(p.loc[ASOF, "Close"])
        hi = float(p.loc[HIGH_FROM:ASOF, "High"].max())
        stocks.append({
            "ticker": t, "name": name, "group": group,
            "buy": buy, "hold": hold, "sell": sell, "total": buy + hold + sell,
            "price": round(price, 2), "target_avg": avg, "target_low": low, "target_high": high,
            "upside_pct": pct(avg, price), "low_upside_pct": pct(low, price),
            "high_52w": round(hi, 2), "from_high_pct": pct(price, hi),
            "ytd_pct": pct(price, float(p.loc[YEAR_START, "Close"])),
            "election_pct": pct(float(p.loc[ELECTION[1], "Close"]), float(p.loc[ELECTION[0], "Close"])),
        })
    stocks.sort(key=lambda s: -s["upside_pct"])

    market = []
    for t, name in [("SPY", "S&P 500 (SPY)"), ("ITA", "US aerospace & defense ETF (ITA)")]:
        p = prices(t)
        market.append({"ticker": t, "name": name,
                       "election_pct": pct(float(p.loc[ELECTION[1], "Close"]), float(p.loc[ELECTION[0], "Close"])),
                       "ytd_pct": pct(float(p.loc[ASOF, "Close"]), float(p.loc[YEAR_START, "Close"]))})

    k = prices("KTOS")
    ktos_hist = k.loc[HIGH_FROM:ASOF, "Close"]
    kratos = {
        "prices": [{"date": d, "close": round(float(v), 2)} for d, v in ktos_hist.items()],
        "cuts": [{"date": d, "firm": f, "rating": r, "from": a, "to": b, "cut_pct": pct(b, a),
                  "close": round(float(k.loc[d, "Close"]), 2)} for d, f, r, a, b in CUTS],
        "events": [{"date": d, "label": lab, "close": round(float(k.loc[d, "Close"]), 2),
                    "day_pct": pct(float(k.loc[d, "Close"]), float(k["Close"].shift(1).loc[d]))} for d, lab in EVENTS],
    }
    hi_day = k.loc[HIGH_FROM:ASOF, "High"].idxmax()

    by = {s["ticker"]: s for s in stocks}
    totals = {x: sum(s[x] for s in stocks) for x in ("buy", "hold", "sell", "total")}
    stats = {
        "asof": ASOF, **totals,
        "ktos_high": by["KTOS"]["high_52w"], "ktos_high_date": hi_day, "ktos_price": by["KTOS"]["price"],
        "ktos_from_high_pct": by["KTOS"]["from_high_pct"], "ktos_ytd_pct": by["KTOS"]["ytd_pct"],
        "ktos_upside_pct": by["KTOS"]["upside_pct"], "cuts": len(CUTS),
        "lmt_election_pct": by["LMT"]["election_pct"], "spy_election_pct": market[0]["election_pct"],
        "rtx_low_upside_pct": by["RTX"]["low_upside_pct"],
        "primes_kept_low_above_price": [s["ticker"] for s in stocks if s["group"] == "prime" and s["target_low"] > s["price"]],
        "corr_upside_vs_drop": round(pd.DataFrame(stocks)[["upside_pct", "from_high_pct"]].corr().iloc[0, 1], 2),
    }

    def dump(name, obj):
        (OUT_DATA / f"{name}.json").write_text(json.dumps(obj, indent=1), encoding="utf-8")

    dump("stocks", stocks)
    dump("market", market)
    dump("kratos", kratos)
    dump("stats", stats)

    frames = {
        "ratings": pd.DataFrame(stocks),
        "election_day": pd.DataFrame([{"ticker": s["ticker"], "name": s["name"], "election_pct": s["election_pct"]} for s in stocks]
                                     + [{"ticker": m["ticker"], "name": m["name"], "election_pct": m["election_pct"]} for m in market]),
        "kratos_price": pd.DataFrame(kratos["prices"]),
        "kratos_target_cuts": pd.DataFrame(kratos["cuts"]),
    }
    for name, df in frames.items():
        df.to_csv(OUT_BI / f"{name}.csv", index=False)
        df.to_csv(OUT_PUBLIC / f"{name}.csv", index=False)

    print(json.dumps(stats, indent=1))
    for s in stocks:
        print(f"{s['ticker']:5} up {s['upside_pct']:6} high {s['high_52w']:8} from_high {s['from_high_pct']:6} ytd {s['ytd_pct']:6} nov4 {s['election_pct']:5}")
    print(market)
    print(kratos["events"])


if __name__ == "__main__":
    main()
