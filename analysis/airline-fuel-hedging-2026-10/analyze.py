"""Fuel hedging at 10 US and European airlines, and how their shares moved through the 2026 oil shock.

Input:  raw/prices.csv (from collect.py) + the HEDGES table below, typed from each source document
Output: src/data/airline-fuel-hedging-2026-10/airlines.json  -> the web page
        exports/airlines.csv                                 -> Power BI
        public/data/airline-fuel-hedging-2026-10/airlines.csv -> download link on the page
"""

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
SLUG = "airline-fuel-hedging-2026-10"
OUT_WEB = HERE.parents[1] / "src" / "data" / SLUG / "airlines.json"
OUT_BI = HERE / "exports" / "airlines.csv"
OUT_PUBLIC = HERE.parents[1] / "public" / "data" / SLUG / "airlines.csv"

# Last close before the US and Israeli strikes on Iran (Sat 2026-02-28), and the last close before publication.
BASE_DATE = "2026-02-27"
END_DATE = "2026-10-02"

# Share of expected fuel use already hedged for the nearest period each airline reports, from its latest
# results before publication. Periods differ (calendar vs fiscal years), so `period` says what each covers.
HEDGES = [
    dict(airline="Lufthansa Group", ticker="LHA.DE", region="Europe", currency="EUR",
         hedged=82, period="Q3–Q4 2026", next_hedged="just over 50%", next_period="2027",
         note="Expects a hedge gain of about €1.5 billion for 2026. Part of its hedges are in crude oil and gasoil, which lagged jet fuel; the CFO said this 'highlighted certain limitations'.",
         source="Q2 2026 results presentation, Aug 4, 2026; 2027 cover and hedge gain from the CFO on the Q2 call",
         url="https://investor-relations.lufthansagroup.com/fileadmin/downloads/en/charts-speeches/LH-QR-2026-2-charts.pdf",
         quote="Hedge ratio [%] - YTG only 82% (as of July 27, 2026)"),
    dict(airline="Ryanair", ticker="RYA.IR", region="Europe", currency="EUR",
         hedged=80, period="Apr 2026–Mar 2027 (FY27)", next_hedged="15%", next_period="FY28 (from Apr 2027)",
         note="Hedged at about $67 a barrel; its unhedged fuel cost about $150 a barrel in April–June.",
         source="Q1 FY27 results, Jul 20, 2026",
         url="https://investor.ryanair.com/wp-content/uploads/2026/07/Q1-FY27-Ryanair-Results.pdf",
         quote="FY27 jet-fuel is 80% hedged @ $67bbl. FY28 now 15% hedged at $85bbl."),
    dict(airline="easyJet", ticker="EZJ.L", region="Europe", currency="GBp",
         hedged=79, period="Jul–Sep 2026 (Q4 FY26)", next_hedged="62% / 37%", next_period="Oct 2026–Mar 2027 / Apr–Sep 2027",
         note="Hedged at $786 a tonne against a spot price of $1,275 on Jul 20. Shares are distorted by takeover bids (Castlelake, then Apollo, in July).",
         source="Q3 FY26 trading update, Jul 23, 2026",
         url="https://s203.q4cdn.com/522538739/files/doc_financials/2026/q3/FY26-Q3-RNS-vf.pdf",
         quote="Q4 FY26 Fuel CASK ... 79% hedged at $786/MT; H1'27 62%, H2'27 37%"),
    dict(airline="IAG (British Airways, Iberia)", ticker="IAG.L", region="Europe", currency="GBp",
         hedged=70, period="Jul–Dec 2026", next_hedged="about 40%", next_period="2027",
         note="Fuel hedging gains of €769 million in the first half of 2026.",
         source="H1 2026 results call, Jul 31, 2026 (CFO); gains from the H1 2026 report",
         url="https://www.iairgroup.com/press-releases/2026/iag-half-year-results-2026/",
         quote="we are around 70% hedged for the remainder of 2026 and around 40% hedged for 2027"),
    dict(airline="Air France-KLM", ticker="AF.PA", region="Europe", currency="EUR",
         hedged=67, period="Full year 2026", next_hedged="40%", next_period="2027",
         note="Expects a $1.6 billion hedging gain for 2026; its hedging policy was suspended in April and partly resumed in May.",
         source="Q2 2026 results, Jul 30, 2026",
         url="https://www.globenewswire.com/news-release/2026/07/30/3335784/0/en/air-france-klm-q2-2026-results.html",
         quote="The percentage of fuel consumption already hedged for 2026 is 67% and 40% for 2027"),
    dict(airline="Delta Air Lines", ticker="DAL", region="US", currency="USD",
         hedged=0, period="2026", next_hedged="0%", next_period="2027",
         note="No hedges on its fuel use, but it owns the Monroe refinery near Philadelphia, which supplies part of its jet fuel. Its only fuel derivatives cover the refinery's inventory.",
         source="Form 10-Q, quarter ended Jun 30, 2026",
         url="https://www.sec.gov/Archives/edgar/data/27904/000002790426000031/dal-20260630.htm",
         quote="Our derivative contracts to hedge the financial risk from changing fuel prices are related to inventory at ... Monroe Energy"),
    dict(airline="United Airlines", ticker="UAL", region="US", currency="USD",
         hedged=0, period="2026", next_hedged="0%", next_period="2027",
         note="Policy is not to hedge fuel.",
         source="Form 10-K for 2025, Feb 12, 2026",
         url="https://www.sec.gov/Archives/edgar/data/100517/000010051726000023/ual-20251231.htm",
         quote="The Company's current strategy is to not enter into transactions to hedge fuel price volatility"),
    dict(airline="American Airlines", ticker="AAL", region="US", currency="USD",
         hedged=0, period="2026", next_hedged="0%", next_period="2027",
         note="A 1¢ a gallon rise in fuel adds about $50 million to its annual fuel bill.",
         source="Form 10-Q, quarter ended Jun 30, 2026",
         url="https://www.sec.gov/Archives/edgar/data/6201/000000620126000052/aal-20260630.htm",
         quote="As of June 30, 2026, we did not have any fuel hedging contracts outstanding to hedge our fuel consumption."),
    dict(airline="Southwest Airlines", ticker="LUV", region="US", currency="USD",
         hedged=0, period="2026", next_hedged="0%", next_period="2027",
         note="Ended its decades-old hedging program in 2025, closing contracts that ran through 2027.",
         source="Form 10-Q, quarter ended Jun 30, 2026",
         url="https://www.sec.gov/Archives/edgar/data/92380/000009238026000077/luv-20260630.htm",
         quote="discontinued its fuel hedging program and terminated its remaining portfolio of fuel hedging contracts ... The Company does not intend to add additional fuel derivatives."),
    dict(airline="Alaska Air Group", ticker="ALK", region="US", currency="USD",
         hedged=0, period="2026", next_hedged="0%", next_period="2027",
         note="Suspended hedging in 2023 (Hawaiian in 2025); the last positions settled in 2025.",
         source="Form 10-K for 2025, Feb 12, 2026",
         url="https://www.sec.gov/Archives/edgar/data/766421/000076642126000010/alk-20251231.htm",
         quote="No hedge positions remain open as of December 31, 2025."),
]

# easyJet's share price since July reflects competing takeover offers, not fuel; keep it out of group averages.
EXCLUDE_FROM_SHARES = {"EZJ.L": "Takeover bids from Castlelake and Apollo in July 2026"}

# Each airline is compared with its own region's broad market over the same days.
MARKET = {"US": "^GSPC", "Europe": "^STOXX"}
MARKET_NAME = {"US": "S&P 500", "Europe": "STOXX Europe 600"}

# Short labels for charts.
SHORT = {"LHA.DE": "Lufthansa", "RYA.IR": "Ryanair", "EZJ.L": "easyJet", "IAG.L": "IAG", "AF.PA": "Air France-KLM",
         "DAL": "Delta", "UAL": "United", "AAL": "American", "LUV": "Southwest", "ALK": "Alaska"}

# The three airlines the page tracks live, one per scenario: most fuel hedged for 2027 (Lufthansa),
# least (Ryanair, 15% from April 2027) and none (United: no hedges, no refinery).
TRACKED = ["LHA.DE", "RYA.IR", "UAL"]


def main():
    prices = pd.read_csv(HERE / "raw" / "prices.csv", index_col="date")
    window = prices.loc[BASE_DATE:END_DATE]

    def move(ticker):
        s = window[ticker].dropna()
        return s.iloc[0], s.iloc[-1], s

    market = {}
    for region, t in MARKET.items():
        base, end, s = move(t)
        market[region] = {"name": MARKET_NAME[region], "change_pct": round((end / base - 1) * 100, 1), "low_pct": round((s.min() / base - 1) * 100, 1)}

    rows = []
    for h in HEDGES:
        s = window[h["ticker"]].dropna()
        base, end = s.iloc[0], s.iloc[-1]
        low_date = s.idxmin()
        rows.append({
            **h,
            "short": SHORT[h["ticker"]],
            "base_close": round(base, 2),
            "end_close": round(end, 2),
            "change_pct": round((end / base - 1) * 100, 1),
            "low_close": round(s.min(), 2),
            "low_date": low_date,
            "low_pct": round((s.min() / base - 1) * 100, 1),
            # Percentage points above (+) or below (-) the region's market index over the same window.
            "vs_market_pts": round((end / base - 1) * 100 - market[h["region"]]["change_pct"], 1),
            "excluded": EXCLUDE_FROM_SHARES.get(h["ticker"]),
            "tracked": h["ticker"] in TRACKED,
        })
    df = pd.DataFrame(rows)

    hedged = df[(df.hedged > 0) & df.excluded.isna()]
    unhedged = df[df.hedged == 0]
    groups = {
        name: {
            "airlines": int(len(g)),
            "avg_hedged": round(g.hedged.mean(), 0),
            "avg_change_pct": round(g.change_pct.mean(), 1),
            "avg_low_pct": round(g.low_pct.mean(), 1),
            "avg_vs_market_pts": round(g.vs_market_pts.mean(), 1),
        }
        for name, g in [("hedged", hedged), ("unhedged", unhedged)]
    }

    brent = prices["BZ=F"].dropna()
    crisis = brent.loc[BASE_DATE:END_DATE]
    brent_summary = {
        "base": round(crisis.iloc[0], 2),
        "peak": round(crisis.max(), 2),
        "peak_date": crisis.idxmax(),
        "end": round(crisis.iloc[-1], 2),
        "low_after_peak": round(crisis.loc[crisis.idxmax():].min(), 2),
        "low_after_peak_date": crisis.loc[crisis.idxmax():].idxmin(),
    }

    # Share paths indexed to the Feb 27 close (= 100), for the chart; easyJet included but flagged.
    paths = {
        t: [{"date": d, "index": round(v / window[t].dropna().iloc[0] * 100, 2)} for d, v in window[t].dropna().items()]
        for t in df.ticker
    }

    OUT_WEB.parent.mkdir(parents=True, exist_ok=True)
    OUT_WEB.write_text(json.dumps({
        "base_date": BASE_DATE,
        "end_date": END_DATE,
        "airlines": df.astype(object).where(df.notna(), None).to_dict("records"),
        "groups": groups,
        "market": market,
        "brent": {"summary": brent_summary, "history": [{"date": d, "close": round(v, 2)} for d, v in brent.items()]},
        "paths": paths,
    }, indent=1, ensure_ascii=False, allow_nan=False), encoding="utf-8")

    cols = ["airline", "ticker", "region", "hedged", "period", "next_hedged", "next_period", "currency",
            "base_close", "end_close", "change_pct", "low_close", "low_date", "low_pct", "vs_market_pts", "excluded", "source", "url"]
    OUT_BI.parent.mkdir(exist_ok=True)
    df[cols].to_csv(OUT_BI, index=False)
    OUT_PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    df[cols].to_csv(OUT_PUBLIC, index=False)

    print(df[["airline", "hedged", "change_pct", "vs_market_pts", "low_pct", "low_date"]].to_string(index=False))
    print(market)
    print(json.dumps(groups, indent=1))
    print(brent_summary)


if __name__ == "__main__":
    main()
