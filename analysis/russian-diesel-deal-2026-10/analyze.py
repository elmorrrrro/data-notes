"""Can Russian diesel lower US pump prices before the November 3 midterms?

Reads raw/ (see collect.py) and writes:
  src/data/russian-diesel-deal-2026-10/summary.json   headline numbers for the scoreboard and the text
  src/data/russian-diesel-deal-2026-10/batches.json   the four promised batches: size, earliest landing window
  src/data/russian-diesel-deal-2026-10/pump.json      weekly US pump prices in 2026 plus the deal's best case to Nov 2
  src/data/russian-diesel-deal-2026-10/market.json    one-day moves on the day of the deal (Oct 8 -> Oct 9 close)
  src/data/russian-diesel-deal-2026-10/arrivals.json  cumulative diesel landed by date, against the political calendar
  src/data/russian-diesel-deal-2026-10/sensitivity.json  how much each share moves when diesel futures move 1%
  public/data/russian-diesel-deal-2026-10/*.csv       public download (EIA data and our batch timeline)
  exports/*.csv                                       for Power BI
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
RAW = HERE / "raw"
ROOT = HERE.parents[1]
SLUG = "russian-diesel-deal-2026-10"
OUT = ROOT / "src" / "data" / SLUG
PUBLIC = ROOT / "public" / "data" / SLUG
EXPORTS = HERE / "exports"

DEAL = pd.Timestamp("2026-10-09")       # Trump's Truth Social post and the OFAC general license
ELECTION = pd.Timestamp("2026-11-03")
LAST_SURVEY = pd.Timestamp("2026-11-02")  # EIA's last weekly pump-price survey before the vote
PRE_WAR = pd.Timestamp("2026-02-23")    # last EIA survey before the strikes on Iran (Feb 28)
LICENSE_ENDS = pd.Timestamp("2027-04-07")
NEW_CONGRESS = pd.Timestamp("2027-01-03")  # the Congress elected on Nov 3 is sworn in

BBL_PER_TONNE = 7.46   # gasoil/diesel, Energy Institute Statistical Review conversion factor
KNOTS = 13             # typical laden speed of a medium-range product tanker
LOADING_DAYS = 3       # charter, berth and load before sailing (optimistic)

# The schedule as Trump posted it on Truth Social on 2026-10-09 (CBS: the 1 Mt batch in December).
BATCHES = [
    dict(id="b1", label="Batch 1", when="“immediately”", tonnes=300_000, load_from=DEAL, load_to=pd.Timestamp("2026-10-31")),
    dict(id="b2", label="Batch 2", when="November", tonnes=500_000, load_from=pd.Timestamp("2026-11-01"), load_to=pd.Timestamp("2026-11-30")),
    dict(id="b3", label="Batch 3", when="“immediately thereafter” (December)", tonnes=1_000_000, load_from=pd.Timestamp("2026-12-01"), load_to=pd.Timestamp("2026-12-31")),
    dict(id="b4", label="Batch 4", when="later, “depending on the condition of Russia's refineries”", tonnes=3_000_000, load_from=pd.Timestamp("2027-01-01"), load_to=LICENSE_ENDS),
]


def eia(series):
    df = pd.read_excel(RAW / f"{series}.xls", sheet_name="Data 1", skiprows=2)
    df.columns = ["date", "value"]
    return df.dropna().set_index("date")["value"]


def pass_through(retail, spot, lags=6):
    """Cumulative share of a wholesale (NY Harbor spot) move that reaches the weekly US pump price, 2015-2026.

    Distributed-lag regression of the weekly change in the retail price on this and earlier weeks' change in the
    average spot price (week ending the Friday before each Monday survey)."""
    sw = spot.resample("W-FRI").mean()
    sw.index = sw.index + pd.Timedelta(days=3)
    df = pd.concat({"retail": retail, "spot": sw}, axis=1, join="inner").loc["2015":]
    dr, ds = df.retail.diff(), df.spot.diff()
    X = pd.concat({k: ds.shift(k) for k in range(lags + 1)}, axis=1)
    d = pd.concat([dr.rename("y"), X], axis=1).dropna()
    coef = np.linalg.lstsq(np.c_[np.ones(len(d)), d.drop(columns="y").values], d.y.values, rcond=None)[0][1:]
    return np.cumsum(coef), len(d)


def main():
    for p in (OUT, PUBLIC, EXPORTS):
        p.mkdir(parents=True, exist_ok=True)

    diesel, gasoline = eia("EMD_EPD2D_PTE_NUS_DPGw"), eia("EMM_EPMR_PTE_NUS_DPGw")
    spot = eia("EER_EPD2DXL0_PF4_Y35NY_DPGd")
    use, exports, imports = eia("WDIUPUS2w"), eia("WDIEXUS2w"), eia("WDIIMUS2w")
    prices = pd.read_csv(RAW / "prices.csv", index_col=0, parse_dates=True)
    routes = json.loads((RAW / "routes.json").read_text())

    # --- How much diesel is it, in days of US use -------------------------------------------------------------
    y26 = slice("2026-01-01", None)
    use_bpd = use[y26].mean() * 1000
    exp_bpd, imp_bpd = exports[y26].mean() * 1000, imports[y26].mean() * 1000
    days = lambda t: t * BBL_PER_TONNE / use_bpd

    # --- When could each batch land in New York Harbor ---------------------------------------------------------
    sail = math.ceil(routes["Primorsk"] / (KNOTS * 24))  # days at sea from the Baltic, the shortest route
    batches, cum = [], 0
    for b in BATCHES:
        cum += b["tonnes"]
        land_from = b["load_from"] + pd.Timedelta(days=LOADING_DAYS + sail)
        land_to = min(b["load_to"] + pd.Timedelta(days=LOADING_DAYS + sail), LICENSE_ENDS)
        batches.append(dict(
            id=b["id"], label=b["label"], when=b["when"], tonnes=b["tonnes"],
            barrels=round(b["tonnes"] * BBL_PER_TONNE), days_of_us_use=round(days(b["tonnes"]), 1),
            cum_tonnes=cum, cum_days=round(days(cum), 1),
            load_from=b["load_from"].strftime("%Y-%m-%d"), land_from=land_from.strftime("%Y-%m-%d"),
            land_to=land_to.strftime("%Y-%m-%d"), before_election=bool(land_from < ELECTION),
        ))
    total_t = sum(b["tonnes"] for b in BATCHES)

    # --- How fast a wholesale drop reaches the pump ------------------------------------------------------------
    cum_pt, n_weeks = pass_through(diesel, spot)
    surveys = pd.date_range(DEAL + pd.Timedelta(days=3), LAST_SURVEY, freq="7D")  # Mondays Oct 12 .. Nov 2
    ho = prices["HO=F"].dropna()
    deal_drop = float(ho.loc[DEAL] - ho.loc[:DEAL].iloc[-2])  # $/gal, Oct 8 close -> Oct 9 close
    pump_cut = [round(deal_drop * cum_pt[i], 3) for i in range(len(surveys))]

    # --- Pump prices -------------------------------------------------------------------------------------------
    last = diesel.index.max()
    pump = [dict(date=d.strftime("%Y-%m-%d"), diesel=round(float(diesel[d]), 3),
                 gasoline=round(float(gasoline.get(d, np.nan)), 3)) for d in diesel.loc["2026-01-01":].index]
    best_case = [dict(date=last.strftime("%Y-%m-%d"), diesel=round(float(diesel[last]), 3))] + [
        dict(date=d.strftime("%Y-%m-%d"), diesel=round(float(diesel[last]) + c, 3)) for d, c in zip(surveys, pump_cut)]

    peak_d = diesel.loc["2026"].idxmax()
    summary = dict(
        deal_date=DEAL.strftime("%Y-%m-%d"), election=ELECTION.strftime("%Y-%m-%d"),
        days_to_election=(ELECTION - DEAL).days,
        total_tonnes=total_t, total_days_of_us_use=round(days(total_t), 1),
        before_election_tonnes=sum(b["tonnes"] for b in batches if b["before_election"]),
        before_election_days=round(sum(b["days_of_us_use"] for b in batches if b["before_election"]), 1),
        us_use_bpd=round(use_bpd), us_exports_bpd=round(exp_bpd), us_imports_bpd=round(imp_bpd),
        sail_days_primorsk=sail, sail_days_novorossiysk=math.ceil(routes["Novorossiysk"] / (KNOTS * 24)),
        route_nm=routes, first_landing=batches[0]["land_from"],
        pass_through=[round(float(x), 2) for x in cum_pt], pass_through_weeks_fitted=n_weeks,
        pass_through_by_vote=round(float(cum_pt[len(surveys) - 1]), 2), surveys_before_vote=len(surveys),
        futures_drop=round(deal_drop, 3), futures_drop_pct=round(deal_drop / float(ho.loc[:DEAL].iloc[-2]) * 100, 1),
        pump_cut_by_vote=round(-pump_cut[-1], 2),
        diesel=dict(pre_war=round(float(diesel[PRE_WAR]), 2), peak=round(float(diesel[peak_d]), 2),
                    peak_date=peak_d.strftime("%Y-%m-%d"), now=round(float(diesel[last]), 2),
                    now_date=last.strftime("%Y-%m-%d"), best_case_vote=best_case[-1]["diesel"]),
        gasoline=dict(pre_war=round(float(gasoline[PRE_WAR]), 2), now=round(float(gasoline[last]), 2)),
    )
    summary["diesel"]["rise"] = round(summary["diesel"]["now"] - summary["diesel"]["pre_war"], 2)
    summary["share_of_rise_undone"] = round(summary["pump_cut_by_vote"] / summary["diesel"]["rise"] * 100)

    # --- The market on the day of the deal ---------------------------------------------------------------------
    names = {"HO=F": ("Diesel futures", "fuel"), "BZ=F": ("Brent crude", "fuel"),
             "VLO": ("Valero", "refiner"), "MPC": ("Marathon Petroleum", "refiner"), "PSX": ("Phillips 66", "refiner"),
             "STNG": ("Scorpio Tankers", "tanker"), "INSW": ("International Seaways", "tanker"),
             "ODFL": ("Old Dominion", "trucker"), "JBHT": ("J.B. Hunt", "trucker"), "^GSPC": ("S&P 500", "market")}
    base_war = pd.Timestamp("2026-02-27")
    market = []
    for t, (name, group) in names.items():
        s = prices[t].dropna()
        prev, now = float(s.loc[:DEAL].iloc[-2]), float(s.loc[DEAL])
        market.append(dict(ticker=t, name=name, group=group, prev=round(prev, 2), close=round(now, 2),
                           day_pct=round((now / prev - 1) * 100, 1),
                           since_war_pct=round((now / float(s.loc[base_war]) - 1) * 100)))

    # --- When the diesel lands, against the political calendar ------------------------------------------------
    # Each batch lands evenly across its earliest landing window (a tanker every few days, not one big delivery).
    cal = pd.date_range(DEAL, LICENSE_ENDS, freq="D")
    landed = pd.Series(0.0, index=cal)
    firm = pd.Series(0.0, index=cal)  # batches 1-3; batch 4 depends on "the condition of Russia's refineries"
    for b in batches:
        win = pd.date_range(b["land_from"], b["land_to"], freq="D")
        landed[win] += b["tonnes"] / len(win)
        if b["id"] != "b4":
            firm[win] += b["tonnes"] / len(win)
    cum_landed, cum_firm = landed.cumsum(), firm.cumsum()
    by = lambda day: float(cum_landed.loc[:day - pd.Timedelta(days=1)].iloc[-1]) if day > DEAL else 0.0
    periods = [
        dict(id="before_vote", label="Before the vote", start=DEAL, end=ELECTION),
        dict(id="lame_duck", label="After the vote, old Congress", start=ELECTION, end=NEW_CONGRESS),
        dict(id="new_congress", label="New Congress sits", start=NEW_CONGRESS, end=LICENSE_ENDS + pd.Timedelta(days=1)),
    ]
    for q in periods:
        q["tonnes"] = round(by(q["end"]) - by(q["start"]))
        q["share"] = round(q["tonnes"] / total_t * 100, 1)
        q["start"], q["end"] = q["start"].strftime("%Y-%m-%d"), (q["end"] - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    arrivals = dict(
        daily=[dict(date=d.strftime("%Y-%m-%d"), tonnes=round(float(cum_landed[d])), firm=round(float(cum_firm[d])))
               for d in list(cal[::3]) + ([cal[-1]] if (len(cal) - 1) % 3 else [])],
        periods=periods,
        new_congress=NEW_CONGRESS.strftime("%Y-%m-%d"), license_ends=LICENSE_ENDS.strftime("%Y-%m-%d"),
    )
    # Gross value at the New York wholesale price on the day of the deal (Russia keeps less: freight, discounts).
    summary["deal_value_bn"] = round(total_t * BBL_PER_TONNE * 42 * float(ho.loc[DEAL]) / 1e9, 1)
    summary["after_vote_share"] = round(100 - periods[0]["share"])
    summary["new_congress_share"] = round(periods[2]["share"])
    summary["refinery_dependent_share"] = round(BATCHES[-1]["tonnes"] / total_t * 100)

    # --- How much each share follows the diesel price -----------------------------------------------------------
    # Daily log returns since the war began; regress each share on diesel futures and the S&P 500 together, so the
    # diesel number is what is left after the whole market's move is taken out.
    r = np.log(prices).diff().loc["2026-03-02":].dropna()
    X = np.c_[np.ones(len(r)), r["HO=F"], r["^GSPC"]]
    sensitivity = []
    for t in ["VLO", "MPC", "STNG", "INSW", "ODFL", "JBHT"]:
        coef, res, *_ = np.linalg.lstsq(X, r[t].values, rcond=None)
        sigma2 = res[0] / (len(r) - X.shape[1])
        se = np.sqrt(np.diag(sigma2 * np.linalg.inv(X.T @ X)))
        name, group = names[t]
        sensitivity.append(dict(ticker=t, name=name, group=group, beta=round(float(coef[1]), 3),
                                lo=round(float(coef[1] - 1.96 * se[1]), 3), hi=round(float(coef[1] + 1.96 * se[1]), 3),
                                corr=round(float(r[t].corr(r["HO=F"])), 2), days=len(r)))

    # --- Write -------------------------------------------------------------------------------------------------
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1))
    (OUT / "batches.json").write_text(json.dumps(batches, indent=1))
    (OUT / "pump.json").write_text(json.dumps(dict(weekly=pump, best_case=best_case), indent=1))
    (OUT / "market.json").write_text(json.dumps(market, indent=1))
    (OUT / "arrivals.json").write_text(json.dumps(arrivals, indent=1))
    (OUT / "sensitivity.json").write_text(json.dumps(sensitivity, indent=1))

    pd.DataFrame(pump).to_csv(PUBLIC / "us-pump-prices-weekly-2026.csv", index=False)
    pd.DataFrame(batches).drop(columns=["id"]).to_csv(PUBLIC / "russian-diesel-batches.csv", index=False)
    pd.DataFrame(pump).to_csv(EXPORTS / "pump.csv", index=False)
    pd.DataFrame(batches).to_csv(EXPORTS / "batches.csv", index=False)
    pd.DataFrame(market).to_csv(EXPORTS / "market.csv", index=False)

    print(json.dumps(summary, indent=1))
    for b in batches:
        print(b["label"], b["tonnes"], b["days_of_us_use"], b["land_from"], b["land_to"])
    for m in market:
        print(f"{m['name']:22} {m['day_pct']:+5.1f}%  since war {m['since_war_pct']:+d}%")
    print(json.dumps(periods, indent=1))
    for x in sensitivity:
        print(x)


if __name__ == "__main__":
    main()
