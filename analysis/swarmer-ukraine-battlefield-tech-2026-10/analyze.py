"""Swarmer and Ukraine's battlefield-tech boom: the money, the multiples, the stock, and the war the talks don't stop.

Input:  raw/ (from collect.py) + the sourced constants below (press figures and filing lines typed by hand)
Output: src/data/swarmer-ukraine-battlefield-tech-2026-10/*.json   -> the web page
        exports/*.csv                                              -> Power BI
        public/data/swarmer-ukraine-battlefield-tech-2026-10/*.csv -> download link on the page

Four questions:
1. Why Ukraine: how fast did drone making and defense-tech funding grow?
2. Is Swarmer's tiny revenue unusual for a young listed hardware company? (no: Joby and Archer listed with none)
3. What is the market paying per dollar of sales, for Swarmer alone and with Ratel Robotics, vs listed peers?
4. Talks vs reality: did Russia's monthly drone and missile launches fall around US-Russia and US-Iran talks?
"""

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
RAW = HERE / "raw"
SLUG = "swarmer-ukraine-battlefield-tech-2026-10"
ROOT = HERE.parents[1]
OUT_WEB = ROOT / "src" / "data" / SLUG
OUT_BI = HERE / "exports"
OUT_PUBLIC = ROOT / "public" / "data" / SLUG

END_DATE = "2026-10-05"  # last close before publication
IPO_PRICE = 5.00
EDGAR = "https://www.sec.gov/Archives/edgar/data/2092574"
PROXY = f"{EDGAR}/000110465926111047/tm2625952-1_prem14a.htm"
TENQ = f"{EDGAR}/000119312526352312/swmr-20260630.htm"

# Swarmer figures that XBRL doesn't carry (or carries only in the S-1), typed from the filings.
SWARMER = {
    "ipo_date": "2026-03-17",
    "ipo_shares": 3_450_000,
    "ipo_gross": 17_250_000,
    "revenue_2024": 329_410,
    "revenue_2025": 309_920,
    "net_loss_2025": -8_530_000,
    "shares_record_date": 16_610_264,  # proxy: outstanding at the 11 Sep 2026 record date
    "shares_end_2025": 911_255,  # before preferred converted at the IPO
    "ratel_closing_shares": 1_064_942,
    "ratel_cash": 7_399_928,
    "ratel_earnout_max_shares": 4_422_125,
    "ratel_revenue_2025": 18_635_667,
    "ratel_revenue_h1_2026": 9_602_328,
    "ratel_net_income_2025": 1_965_911,
    "ratel_advances_jun_2026": 86_600_000,
    "ratel_advances_dec_2025": 4_700_000,
    "ratel_gov_share_h1_2026": 0.86,
    "ratel_earnout_revenue_2026": 77_000_000,
    "vote_date": "2026-10-30",
}

# Why Ukraine. Press figures; each row carries its source.
DRONE_PRODUCTION = [  # drones made in Ukraine per year
    {"year": 2024, "drones": 2_200_000, "source": "https://www.osw.waw.pl/en/publikacje/osw-commentary/2025-10-14/game-drones-production-and-use-ukrainian-battlefield-unmanned"},
    {"year": 2025, "drones": 4_000_000, "source": "https://aviationweek.com/defense/supply-chain/ukraine-eyes-drone-production-topping-7-million-units"},
    {"year": 2026, "drones": 7_000_000, "target": True, "source": "https://aviationweek.com/defense/supply-chain/ukraine-eyes-drone-production-topping-7-million-units"},
]
VENTURE = [  # venture money into Ukrainian defense tech per year, $M (lower bounds: "over")
    {"year": 2023, "usd_m": 5, "source": "https://www.kyivpost.com/post/65810"},
    {"year": 2024, "usd_m": 40, "source": "https://www.kyivpost.com/post/65810"},
    {"year": 2025, "usd_m": 105, "source": "https://www.kyivpost.com/post/65810"},
]
CONTEXT = {
    "manufacturers_before": 7,
    "manufacturers_now": 500,
    "manufacturers_source": "https://gssr.georgetown.edu/the-forum/regions/eurasia/a-first-point-view-examining-ukraines-drone-industry/",
    "drone_casualty_share": 0.80,
    "drone_casualty_source": "https://www.army-technology.com/news/drones-now-account-for-80-of-casualties-in-ukraine-russia-war/",
    "brave1_drones_9m_2026": 590_000,
    "brave1_source": "https://www.aerotime.aero/articles/ukraines-troops-order-590000-drones-interceptors-overtake-fpvs",
}

# Early revenue: young listed hardware companies, revenue in the year they listed (fiscal year) vs now.
EARLY = {
    "JOBY": ("Joby Aviation", 2021, "air taxis, listed via SPAC merger Aug 2021"),
    "ACHR": ("Archer Aviation", 2021, "air taxis, listed via SPAC merger Sep 2021"),
    "ONDS": ("Ondas", 2020, "drones and networks, Nasdaq from Dec 2020"),
    "RCAT": ("Red Cat", 2021, "military drones, Nasdaq from Apr 2021 (fiscal year to April)"),
}
PEERS = {
    "AVAV": "AeroVironment",
    "KTOS": "Kratos",
    "PLTR": "Palantir",
    "RCAT": "Red Cat",
    "ONDS": "Ondas",
    "JOBY": "Joby Aviation",
    "ACHR": "Archer Aviation",
    "RKLB": "Rocket Lab",
}

# Talks vs reality. Dates from the two Wikipedia timelines (which cite the primary reports), checked against the
# extracts in raw/wiki/; one 2026 event that the extract lacks is sourced to Axios.
WIKI_RU = "https://en.wikipedia.org/wiki/Peace_negotiations_in_the_Russo-Ukrainian_war_(2022%E2%80%93present)"
WIKI_IR = "https://en.wikipedia.org/wiki/2025%E2%80%932026_Iran%E2%80%93United_States_negotiations"
W = lambda t: "https://en.wikipedia.org/wiki/" + t
W_NUKE = W("Nuclear_risk_during_the_Russo-Ukrainian_war_(2022%E2%80%93present)")
W_CN_RU = W("Support_for_Russia_in_the_Russo-Ukrainian_war")
EVENTS = [
    ("russia", "2025-02-18", "US and Russia meet in Riyadh", "talks", WIKI_RU),
    ("russia", "2025-03-18", "Trump-Putin call: 30-day energy truce", "pause", WIKI_RU),
    ("russia", "2025-07-14", "Trump gives Russia 50 days", "deadline", WIKI_RU),
    ("russia", "2025-08-15", "Alaska summit", "talks", WIKI_RU),
    ("russia", "2025-10-16", "Budapest summit announced, later cancelled", "talks", WIKI_RU),
    ("russia", "2025-11-19", "28-point plan reported", "talks", WIKI_RU),
    ("russia", "2026-01-23", "First US-Russia-Ukraine round, Abu Dhabi", "talks", WIKI_RU),
    ("russia", "2026-02-17", "Trilateral round, Geneva", "talks", WIKI_RU),
    ("russia", "2026-04-11", "32-hour Easter truce", "pause", WIKI_RU),
    ("russia", "2026-05-08", "48-hour Victory Day truce", "pause", WIKI_RU),
    ("russia", "2026-09-05", "Witkoff and Kushner meet Putin", "talks", "https://www.axios.com/2026/09/05/putin-witkoff-kushner-trump-ukraine-war"),
    ("iran", "2025-04-12", "First US-Iran round, Oman", "talks", WIKI_IR),
    ("iran", "2025-06-13", "Israel strikes Iran", "war", WIKI_IR),
    ("iran", "2026-02-06", "US-Iran talks, Muscat", "talks", WIKI_IR),
    ("iran", "2026-02-28", "US and Israel strike Iran", "war", WIKI_IR),
    ("iran", "2026-04-07", "Two-week ceasefire", "pause", WIKI_IR),
    ("iran", "2026-06-17", "Islamabad Memorandum signed", "talks", WIKI_IR),
    ("iran", "2026-07-08", "Ceasefire breaks over Hormuz", "war", WIKI_IR),
]

# Threats and strikes since 2022 (the "escalation" rows of the timeline). Dates checked against the linked
# Wikipedia articles; precision "month" where the article gives only the month.
ESCALATION = [
    ("russia", "2022-02-24", "Full-scale invasion of Ukraine", "day", W("Russian_invasion_of_Ukraine")),
    ("russia", "2022-02-27", "Putin puts nuclear forces on high alert", "day", W_NUKE),
    ("russia", "2022-09-21", "Mobilization of reservists", "day", W("2022_Russian_mobilization")),
    ("russia", "2022-09-30", "Russia declares four Ukrainian regions annexed", "day", W("Russian_annexation_of_Donetsk,_Kherson,_Luhansk_and_Zaporizhzhia_oblasts")),
    ("russia", "2023-02-21", "Russia suspends the New START nuclear treaty", "day", W_NUKE),
    ("russia", "2023-03-25", "Putin plans nuclear weapons in Belarus", "day", W_NUKE),
    ("russia", "2024-02-29", "Putin warns the West of nuclear war", "day", W_NUKE),
    ("russia", "2024-10-25", "North Korean troops reach Kursk region", "day", W("North_Korean_involvement_in_the_Russian_invasion_of_Ukraine")),
    ("russia", "2024-11-19", "New doctrine lowers the nuclear threshold", "day", W_NUKE),
    ("russia", "2024-11-21", "First Oreshnik missile hits Dnipro", "day", W("Oreshnik_(missile)")),
    ("russia", "2025-09-09", "Russian drones enter Poland", "day", W("2025_Russian_drone_incursion_into_Poland")),
    ("russia", "2025-10-21", "Nuclear-powered Burevestnik missile test", "day", W("9M730_Burevestnik")),
    ("russia", "2025-12-30", "Oreshnik on combat duty in Belarus", "day", W("Oreshnik_(missile)")),
    ("russia", "2026-01-08", "Oreshnik hits Lviv", "day", W("Oreshnik_(missile)")),
    ("russia", "2026-05-24", "Two Oreshniks and 600 drones in one night", "day", W("Oreshnik_(missile)")),
    ("iran", "2024-04-13", "Iran's first direct attack on Israel", "day", W("April_2024_Iranian_strikes_on_Israel")),
    ("iran", "2024-10-01", "Iran fires about 200 missiles at Israel", "day", W("October_2024_Iranian_strikes_on_Israel")),
    ("iran", "2025-06-22", "US bombs Iran's nuclear sites", "day", W("2025_United_States_strikes_on_Iranian_nuclear_sites")),
    ("china", "2022-08-04", "Largest drills around Taiwan to date", "day", W("2022_Chinese_military_exercises_around_Taiwan")),
    ("china", "2023-02-15", "Chinese dual-use goods reach Russian arms makers (WSJ)", "month", W_CN_RU),
    ("china", "2023-04-08", "Joint Sword drills around Taiwan", "day", W("Joint_Sword_(2023)")),
    ("china", "2024-05-23", "Joint Sword-2024A drills", "day", W("Joint_Sword-2024A")),
    ("china", "2024-07-15", "NATO calls China a decisive enabler of Russia's war", "month", W_CN_RU),
    ("china", "2024-10-14", "Joint Sword-2024B drills", "day", W("Joint_Sword-2024B")),
    ("china", "2024-10-16", "Evidence of Chinese attack drones for Russia", "month", W_CN_RU),
    ("china", "2025-04-01", "Strait Thunder-2025A drills", "day", W("Strait_Thunder-2025A")),
    ("china", "2025-04-15", "Ukraine sanctions Chinese makers of Iskander parts", "month", W_CN_RU),
    ("china", "2025-12-29", "Justice Mission-2025 drills", "day", W("Justice_Mission-2025")),
]
KAGGLE = "https://www.kaggle.com/datasets/piterfm/massive-missile-attacks-on-ukraine"


def fy_revenue(ticker):
    """Annual revenue by fiscal-year end, from 10-K XBRL facts (full-year periods only)."""
    tags = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"]
    facts = json.loads((RAW / "facts" / f"{ticker}.json").read_text())["facts"].get("us-gaap", {})
    out = {}
    for tag in tags:
        for u in facts.get(tag, {}).get("units", {}).get("USD", []):
            if u["form"].startswith("10-K") and "start" in u:
                days = (pd.Timestamp(u["end"]) - pd.Timestamp(u["start"])).days
                if 350 < days < 380:
                    out.setdefault(int(u["end"][:4]), u["val"])
    return out


def launches():
    """Monthly launches of Russian drones and missiles at Ukraine, from the Air Force reports in the Kaggle log."""
    daily = pd.read_csv(RAW / "mma" / "missile_attacks_daily.csv")
    models = pd.read_csv(RAW / "mma" / "missiles_and_uavs.csv")[["model", "category"]].rename(columns={"category": "kind"})
    d = daily.merge(models, on="model", how="left")
    # Shahed-type drones, decoys and drones the reports don't name ("Unknown UAV") all count as drones; everything
    # else in the log is a missile (cruise, ballistic, guided, or an S-300/S-400 fired at ground targets).
    shahed = d["model"].str.contains("Shahed|Geran", case=False, na=False) | (d["is_shahed"] == 1)
    uav = shahed | d["kind"].eq("UAV") | d["model"].str.contains("UAV|Lancet|Молнія", case=False, na=False)
    d["type"] = uav.map({True: "drones", False: "missiles"})
    d["month"] = d["time_start"].str[:7]
    m = d.pivot_table(index="month", columns="type", values="launched", aggfunc="sum", fill_value=0).reset_index()
    m = m[m["month"] >= "2023-01"].copy()
    last_day = d["time_start"].max()[:10]
    m["partial"] = m["month"] == last_day[:7]
    m[["drones", "missiles"]] = m[["drones", "missiles"]].astype(int)
    return m, last_day


def main():
    for p in (OUT_WEB, OUT_BI, OUT_PUBLIC):
        p.mkdir(parents=True, exist_ok=True)
    info = json.loads((RAW / "peers_info.json").read_text())

    # --- stock -------------------------------------------------------------------------------------------------
    px = pd.read_csv(RAW / "prices" / "SWMR.csv")
    px["date"] = px["Date"].str[:10]
    px = px[px["date"] <= END_DATE][["date", "Close"]].rename(columns={"Close": "close"})
    px["close"] = px["close"].round(2)
    peak = px.loc[px["close"].idxmax()]
    last = px.iloc[-1]
    shares_now = SWARMER["shares_record_date"]
    mcap = shares_now * last["close"]
    shares_points = [
        {"date": "2026-03-31", "shares": 10_798_722, "source": TENQ},
        {"date": "2026-06-30", "shares": 11_284_769, "source": TENQ},
        {"date": "2026-08-10", "shares": 11_922_750, "source": TENQ},
        {"date": "2026-09-11", "shares": shares_now, "source": PROXY},
    ]

    # --- Swarmer's own numbers (XBRL, 10-Q for the six months to 30 June 2026) -----------------------------------
    facts = json.loads((RAW / "facts" / "SWMR.json").read_text())["facts"]["us-gaap"]

    def val(tag, start, end):
        rows = [u for u in facts[tag]["units"]["USD"] if u.get("start") == start and u["end"] == end]
        return rows[-1]["val"]

    h1 = ("2026-01-01", "2026-06-30")
    q2 = ("2026-04-01", "2026-06-30")
    rev_q2 = val("Revenues", *q2)
    rev_h1 = val("Revenues", *h1)
    net_h1 = val("NetIncomeLoss", *h1) if any(u.get("start") == h1[0] and u["end"] == h1[1] for u in facts["NetIncomeLoss"]["units"]["USD"]) else val("ProfitLoss", *h1)
    opcf_h1 = val("NetCashProvidedByUsedInOperatingActivities", *h1)
    cash = [u for u in facts["CashAndCashEquivalentsAtCarryingValue"]["units"]["USD"] if u["end"] == "2026-06-30"][-1]["val"]
    ttm_rev = SWARMER["revenue_2025"] - 248_910 + rev_h1  # 2025 minus H1 2025 plus H1 2026
    runway_months = cash / (-opcf_h1 / 6)

    # Pro forma: Swarmer + Ratel, the combined revenue in the proxy, and the share count after the closing shares.
    pf_rev_2025 = SWARMER["revenue_2025"] + SWARMER["ratel_revenue_2025"]
    pf_shares = shares_now + SWARMER["ratel_closing_shares"]
    pf_mcap = pf_shares * last["close"]

    # --- valuation vs peers (Yahoo: market cap and trailing 12-month revenue, read on collect day) -------------------
    val_rows = []
    for t, name in PEERS.items():
        i = info[t]
        val_rows.append({"ticker": t, "name": name, "market_cap_bn": i["marketCap"] / 1e9, "revenue_ttm_m": i["totalRevenue"] / 1e6, "ps": i["marketCap"] / i["totalRevenue"], "group": "peer"})
    val_rows.append({"ticker": "SWMR", "name": "Swarmer alone", "market_cap_bn": mcap / 1e9, "revenue_ttm_m": ttm_rev / 1e6, "ps": mcap / ttm_rev, "group": "swarmer"})
    val_rows.append({"ticker": "SWMR+R", "name": "Swarmer + Ratel", "market_cap_bn": pf_mcap / 1e9, "revenue_ttm_m": pf_rev_2025 / 1e6, "ps": pf_mcap / pf_rev_2025, "group": "swarmer"})
    valuation = pd.DataFrame(val_rows).sort_values("ps", ascending=False)

    # --- early revenue ------------------------------------------------------------------------------------------
    early_rows = []
    for t, (name, year, note) in EARLY.items():
        rev = fy_revenue(t)
        early_rows.append({"ticker": t, "name": name, "listed_year": year, "revenue_listing_year_m": rev.get(year, 0) / 1e6, "revenue_ttm_m": info[t]["totalRevenue"] / 1e6, "market_cap_bn": info[t]["marketCap"] / 1e9, "note": note})
    early_rows.append({"ticker": "SWMR", "name": "Swarmer", "listed_year": 2026, "revenue_listing_year_m": ttm_rev / 1e6, "revenue_ttm_m": ttm_rev / 1e6, "market_cap_bn": mcap / 1e9, "note": "drone-swarm software, Nasdaq IPO Mar 2026; revenue = last 12 months"})
    early = pd.DataFrame(early_rows)

    # --- launches and events -------------------------------------------------------------------------------------
    m, last_day = launches()
    m["total"] = m["drones"] + m["missiles"]
    full = m[~m["partial"]]
    peak_m = full.loc[full["drones"].idxmax()]
    events = [{"track": tr, "date": dt, "label": lb, "kind": k, "source": src} for tr, dt, lb, k, src in EVENTS]
    # Launches in the 30 days after each event vs the 30 days before (daily log, so event-level windows).
    daily = pd.read_csv(RAW / "mma" / "missile_attacks_daily.csv")
    daily["day"] = pd.to_datetime(daily["time_start"].str[:10])
    per_day = daily.groupby("day")["launched"].sum()
    per_day = per_day.reindex(pd.date_range("2022-09-01", last_day), fill_value=0)
    for e in events:
        t0 = pd.Timestamp(e["date"])
        before = per_day[t0 - pd.Timedelta(days=30) : t0 - pd.Timedelta(days=1)].sum()
        after = per_day[t0 : t0 + pd.Timedelta(days=29)].sum()
        e["launched_30d_before"] = int(before)
        e["launched_30d_after"] = int(after)
        e["change"] = round(after / before - 1, 3) if before else None
    up_after = sum(1 for e in events if e["change"] is not None and e["change"] > 0)
    # The bigger picture: launches in the year before the first US-Russia meeting vs every 12 months since.
    t0 = pd.Timestamp(EVENTS[0][1])
    year_before = int(per_day[t0 - pd.DateOffset(years=1) : t0 - pd.Timedelta(days=1)].sum())
    year_after = int(per_day[t0 : t0 + pd.DateOffset(years=1) - pd.Timedelta(days=1)].sum())
    year_two = int(per_day[t0 + pd.DateOffset(years=1) : t0 + pd.DateOffset(years=2) - pd.Timedelta(days=1)].sum())

    y = lambda yr: int(m[m["month"].str.startswith(str(yr)) & ~m["partial"]]["drones"].sum())
    stats = {
        "end_date": END_DATE,
        "price": float(last["close"]),
        "ipo_price": IPO_PRICE,
        "first_close": float(px.iloc[0]["close"]),
        "peak_close": float(peak["close"]),
        "peak_date": peak["date"],
        "vs_ipo": float(last["close"]) / IPO_PRICE - 1,
        "vs_peak": float(last["close"]) / float(peak["close"]) - 1,
        "shares_now": shares_now,
        "market_cap": mcap,
        "revenue_q2_2026": rev_q2,
        "revenue_h1_2026": rev_h1,
        "revenue_ttm": ttm_rev,
        "net_loss_h1_2026": net_h1,
        "op_cash_flow_h1_2026": opcf_h1,
        "cash_jun_2026": cash,
        "runway_months": runway_months,
        "ps_alone": mcap / ttm_rev,
        "ps_with_ratel": pf_mcap / pf_rev_2025,
        "pf_revenue_2025": pf_rev_2025,
        "pf_market_cap": pf_mcap,
        **{k: v for k, v in SWARMER.items()},
        "drones_launched_2023": y(2023),
        "drones_launched_2024": y(2024),
        "drones_launched_2025": y(2025),
        "drones_peak_month": peak_m["month"],
        "drones_peak": int(peak_m["drones"]),
        "launch_log_last_day": last_day,
        "events": len(events),
        "events_followed_by_more": up_after,
        "launched_year_before_talks": year_before,
        "launched_first_year_of_talks": year_after,
        "launched_second_year_to_date": year_two,
        "second_year_to": last_day,
        **CONTEXT,
        "sources": {"proxy": PROXY, "tenq": TENQ, "kaggle": KAGGLE, "wiki_ru": WIKI_RU, "wiki_ir": WIKI_IR},
    }

    def dump(name, obj):
        (OUT_WEB / f"{name}.json").write_text(json.dumps(obj, indent=1, default=float), encoding="utf-8")

    dump("stats", stats)
    dump("price", px.to_dict("records"))
    dump("shares", shares_points)
    dump("valuation", valuation.round(4).to_dict("records"))
    dump("early", early.round(4).to_dict("records"))
    dump("launches", m.to_dict("records"))
    dump("events", events)
    esc = [{"track": tr, "date": dt, "label": lb, "precision": pr, "source": src} for tr, dt, lb, pr, src in ESCALATION]
    dump("escalation", esc)
    dump("production", DRONE_PRODUCTION)
    dump("venture", VENTURE)

    for name, df in {"price": px, "valuation": valuation, "early_revenue": early, "launches": m, "events": pd.DataFrame(events)}.items():
        df.to_csv(OUT_BI / f"{name}.csv", index=False)
    # Public download. The launch counts derive from a CC BY-NC-SA 4.0 dataset, so that file keeps the same licence.
    px.to_csv(OUT_PUBLIC / "swmr_price.csv", index=False)
    valuation.round(4).to_csv(OUT_PUBLIC / "valuation.csv", index=False)
    early.round(4).to_csv(OUT_PUBLIC / "early_revenue.csv", index=False)
    with open(OUT_PUBLIC / "launches_by_month.csv", "w", encoding="utf-8", newline="") as f:
        f.write(f"# Derived from 'Massive Missile Attacks on Ukraine' by piterfm ({KAGGLE}), CC BY-NC-SA 4.0. Same licence applies.\n")
        m.to_csv(f, index=False)
    pd.DataFrame(events).to_csv(OUT_PUBLIC / "talks_events.csv", index=False)
    pd.DataFrame(esc).to_csv(OUT_PUBLIC / "escalation_events.csv", index=False)

    print(json.dumps({k: v for k, v in stats.items() if k != "sources"}, indent=1, default=float))
    print(valuation.round(2).to_string(index=False))
    print(early.round(2).to_string(index=False))
    print(pd.DataFrame(events)[["date", "label", "launched_30d_before", "launched_30d_after", "change"]].to_string(index=False))


if __name__ == "__main__":
    main()
