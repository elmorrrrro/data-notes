"""Hormuz went dark, not empty: what open ship-tracking data sees vs the oil that still gets through.

Input:  raw/ (from collect.py: IMF PortWatch daily chokepoint transits, FRED Brent)
Output: src/data/hormuz-shipping-2026-10/*.json   -> the web page
        exports/*.csv                             -> Power BI
        public/data/hormuz-shipping-2026-10/*.csv -> download link on the page

Three questions:
1. How many ships did open AIS data see crossing Hormuz before and after the US-Israeli strikes on Iran (Feb 28, 2026)?
2. How does that compare with the crude that commercial trackers (Kpler, Windward) say still gets through?
3. Did the open count miss ships before the war too? (Jebel Ali port calls vs Hormuz transits, winter 2025-26)
4. Do governments' own export figures agree? (Kuwait's crude exports in JODI: Kuwait has no route around Hormuz)
"""

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
RAW = HERE / "raw"
SLUG = "hormuz-shipping-2026-10"
ROOT = HERE.parents[1]
OUT_WEB = ROOT / "src" / "data" / SLUG
OUT_BI = HERE / "exports"
OUT_PUBLIC = ROOT / "public" / "data" / SLUG

PORTWATCH = "https://portwatch.imf.org/pages/cb5856222a5b4105adc6ee7e880a1730"
FRED = "https://fred.stlouisfed.org/series/DCOILBRENTEU"
WIKI_IR = "https://en.wikipedia.org/wiki/2025%E2%80%932026_Iran%E2%80%93United_States_negotiations"

WAR = "2026-02-28"  # US and Israel strike Iran
START = "2025-01-01"  # first day shown on the page
CHOKEPOINTS = {
    "strait_of_hormuz": "Strait of Hormuz",
    "suez_canal": "Suez Canal",
    "bab_el_mandeb_strait": "Bab el-Mandeb",
    "cape_of_good_hope": "Cape of Good Hope",
}
EVENTS = [
    {"date": "2025-06-13", "label": "Israel strikes Iran", "short": "12-day war"},
    {"date": "2026-02-28", "label": "US and Israel strike Iran", "short": "Strikes"},
    {"date": "2026-04-07", "label": "Two-week ceasefire", "short": "Ceasefire"},
    {"date": "2026-06-17", "label": "Islamabad Memorandum signed", "short": "Memorandum"},
    {"date": "2026-07-08", "label": "Ceasefire breaks over Hormuz", "short": "Truce breaks"},
]
# Peace windows (start, end): the two-week ceasefire, and the Islamabad Memorandum until the truce broke.
# Commercial tracker figures as published by CNBC on Oct 6, 2026 (crude through Hormuz, million barrels a day).
CNBC = "https://www.cnbc.com/2026/10/06/crude-oil-tanker-strait-hormuz-iran-attack.html"
KPLER = {"label": "Crude through, Kpler", "now": 10.3, "prewar": 13.5, "week": ("2026-09-27", "2026-10-03")}
WINDWARD = {"label": "Crude through, Windward", "now": 9.5, "prewar": 14.5}  # "9-10 million bpd", midpoint
PREWAR = ("2026-01-01", "2026-02-27")  # PortWatch baseline for the same comparison
# Blind spot before the war: autumn vs winter, Hormuz transits and Jebel Ali port calls.
AUTUMN = ("2025-07-01", "2025-10-31")
WINTER = ("2025-11-01", "2026-01-31")
JODI = "https://www.jodidata.org/oil/"
KUWAIT_PREWAR = ("2025-07", "2026-02")  # months in JODI before the war
PEACE = [("Two-week ceasefire", "2026-04-07", "2026-04-21"), ("Islamabad Memorandum", "2026-06-17", "2026-07-08")]


def load(name: str) -> pd.DataFrame:
    df = pd.DataFrame(json.loads((RAW / f"{name}.json").read_text(encoding="utf-8")))
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def main():
    for p in (OUT_WEB, OUT_BI, OUT_PUBLIC):
        p.mkdir(parents=True, exist_ok=True)

    ports = {k: load(k) for k in CHOKEPOINTS}
    h = ports["strait_of_hormuz"]
    h["other"] = h["n_total"] - h["n_tanker"]
    h["avg7"] = h["n_total"].rolling(7).mean()

    # 1. Before and after.
    y2025 = h[h.date.dt.year == 2025]
    war = h[h.date > WAR]
    last = h.date.max()
    last30 = h[h.date > last - pd.Timedelta(days=30)]
    yearly = h.groupby(h.date.dt.year)["n_total"].mean().round(1)
    monthly = h.set_index("date")[["n_total", "n_tanker"]].resample("MS").mean().round(1)

    # 2. Control group: every chokepoint's monthly average as a share of its own 2025 average.
    idx = []
    for k, name in CHOKEPOINTS.items():
        d = ports[k]
        base = d[d.date.dt.year == 2025]["n_total"].mean()
        m = d[d.date >= START].set_index("date")["n_total"].resample("MS").mean()
        for month, v in m.items():
            idx.append({"chokepoint": name, "month": month.strftime("%Y-%m-%d"), "ships_per_day": round(v, 1),
                        "vs_2025": round(v / base, 3), "avg_2025": round(base, 1)})
    idx = pd.DataFrame(idx)

    # 3. Brent.
    b = pd.read_csv(RAW / "brent.csv", parse_dates=["observation_date"]).rename(
        columns={"observation_date": "date", "DCOILBRENTEU": "brent"}).dropna()
    b = b[b.date >= START]
    pre = b[(b.date >= "2026-02-01") & (b.date <= WAR)]
    after = b[b.date > WAR]
    peak = after.loc[after.brent.idxmax()]

    stats = {
        "last_date": last.strftime("%Y-%m-%d"),
        "avg_2025": round(y2025.n_total.mean(), 1),
        "tankers_2025": round(y2025.n_tanker.mean(), 1),
        "avg_2022_2024": round(h[h.date.dt.year.between(2022, 2024)].n_total.mean(), 1),
        "avg_since_war": round(war.n_total.mean(), 1),
        "tankers_since_war": round(war.n_tanker.mean(), 1),
        "avg_last30": round(last30.n_total.mean(), 1),
        "tankers_last30": round(last30.n_tanker.mean(), 1),
        "drop_last30": round(1 - last30.n_total.mean() / y2025.n_total.mean(), 3),
        "zero_days_since_war": int((war.n_total == 0).sum()),
        "days_since_war": int(len(war)),
        "best_day_since_war": {"date": war.loc[war.n_total.idxmax(), "date"].strftime("%Y-%m-%d"),
                               "ships": int(war.n_total.max())},
        "eve_of_war": {"date": "2026-02-27", "ships": int(h.loc[h.date == "2026-02-27", "n_total"].iloc[0])},
        "first_zero": h.loc[(h.date > WAR) & (h.n_total == 0), "date"].min().strftime("%Y-%m-%d"),
        "since_war": [{"chokepoint": name,
                       "avg_2025": round(ports[k][ports[k].date.dt.year == 2025].n_total.mean(), 1),
                       "avg_since_war": round(ports[k][ports[k].date > WAR].n_total.mean(), 1),
                       "change": round(ports[k][ports[k].date > WAR].n_total.mean()
                                       / ports[k][ports[k].date.dt.year == 2025].n_total.mean() - 1, 3)}
                      for k, name in CHOKEPOINTS.items()],
        "brent_feb_2026": round(pre.brent.mean(), 1),
        "brent_peak": round(float(peak.brent), 2),
        "brent_peak_date": peak.date.strftime("%Y-%m-%d"),
        "brent_last": round(float(b.brent.iloc[-1]), 2),
        "brent_last_date": b.date.iloc[-1].strftime("%Y-%m-%d"),
        # The two peace windows: ships a day vs the lowest Brent inside each.
        "peace": [{"label": label, "start": s0, "end": s1,
                   "ships": round(h[(h.date > s0) & (h.date < s1)].n_total.mean(), 1),
                   "brent_low": round(float(b[(b.date > s0) & (b.date < s1)].brent.min()), 2),
                   "brent_low_date": b.loc[b[(b.date > s0) & (b.date < s1)].brent.idxmin(), "date"].strftime("%Y-%m-%d")}
                  for label, s0, s1 in PEACE],
        "sources": {"portwatch": PORTWATCH, "fred": FRED, "wiki_iran": WIKI_IR, "cnbc": CNBC, "jodi": JODI},
    }

    # 2. The gap: open data vs commercial trackers, each as a share of its own prewar level.
    span = lambda d, a, z: d[(d.date >= a) & (d.date <= z)]
    pre_h = span(h, *PREWAR)
    wk = span(h, *KPLER["week"])
    stats["gap_week"] = {"start": KPLER["week"][0], "end": KPLER["week"][1], "tankers_seen": int(wk.n_tanker.sum()),
                         "ships_seen": int(wk.n_total.sum()), "barrels_kpler_m": round(KPLER["now"] * 7, 1)}
    stats["gap"] = [
        {"label": "Ships seen, PortWatch", "group": "Open data", "share": round(wk.n_total.mean() / pre_h.n_total.mean(), 3),
         "detail": f"{wk.n_total.mean():.1f} a day in the week to Oct 3 vs {pre_h.n_total.mean():.0f} in Jan-Feb 2026"},
        {"label": "Tanker capacity seen, PortWatch", "group": "Open data",
         "share": round(wk.capacity_tanker.mean() / pre_h.capacity_tanker.mean(), 3),
         "detail": f"{wk.capacity_tanker.mean() / 1e3:,.0f}k dwt a day vs {pre_h.capacity_tanker.mean() / 1e6:.1f}M in Jan-Feb 2026"},
        {"label": KPLER["label"], "group": "Commercial trackers", "share": round(KPLER["now"] / KPLER["prewar"], 3),
         "detail": f"{KPLER['now']} million barrels a day in the week to Oct 3 vs {KPLER['prewar']} prewar"},
        {"label": WINDWARD["label"], "group": "Commercial trackers", "share": round(WINDWARD["now"] / WINDWARD["prewar"], 3),
         "detail": f"9-10 million barrels a day vs {WINDWARD['prewar']} prewar"},
    ]

    # 3. Blind spot: did Hormuz transits fall while a port that can only be reached through Hormuz stayed busy?
    ja = load("jebel_ali")
    stats["blind_spot"] = {
        "hormuz_autumn": round(span(h, *AUTUMN).n_total.mean(), 1), "hormuz_winter": round(span(h, *WINTER).n_total.mean(), 1),
        "jebel_ali_autumn": round(span(ja, *AUTUMN).portcalls.mean(), 1),
        "jebel_ali_winter": round(span(ja, *WINTER).portcalls.mean(), 1),
    }

    # 4. Government check: Kuwait's crude exports (JODI, thousand barrels a day) vs tanker capacity PortWatch saw.
    j = pd.concat([pd.read_csv(f) for f in sorted((RAW / "jodi").glob("*.csv"))])
    j = j[(j.REF_AREA == "KW") & (j.ENERGY_PRODUCT == "CRUDEOIL") & (j.UNIT_MEASURE == "KBD")]
    j["v"] = pd.to_numeric(j.OBS_VALUE, errors="coerce")
    kw = j.pivot_table(index="TIME_PERIOD", columns="FLOW_BREAKDOWN", values="v")[["TOTEXPSB", "INDPROD"]].dropna()
    kw_pre = kw.loc[KUWAIT_PREWAR[0]:KUWAIT_PREWAR[1]]
    cap = h.set_index("date")["capacity_tanker"].resample("MS").mean()
    cap.index = cap.index.strftime("%Y-%m")
    cap_pre = cap.loc[KUWAIT_PREWAR[0]:KUWAIT_PREWAR[1]].mean()  # same months as Kuwait's baseline
    stats["kuwait"] = {
        "prewar": f"{KUWAIT_PREWAR[0]} to {KUWAIT_PREWAR[1]}",
        "prewar_exports_kbd": round(kw_pre.TOTEXPSB.mean()),
        "prewar_production_kbd": round(kw_pre.INDPROD.mean()),
        "months": [{"month": m, "exports_kbd": round(r.TOTEXPSB), "production_kbd": round(r.INDPROD),
                    "exports_share": round(r.TOTEXPSB / kw_pre.TOTEXPSB.mean(), 3),
                    "tanker_capacity_seen_share": round(cap[m] / cap_pre, 3)}
                   for m, r in kw.loc[KUWAIT_PREWAR[0]:].iterrows()],
    }

    daily = h[h.date >= START]
    web = {
        "daily": [{"date": r.date.strftime("%Y-%m-%d"), "n": int(r.n_total), "tankers": int(r.n_tanker),
                   "other": int(r.other), "avg7": round(r.avg7, 1)} for r in daily.itertuples()],
        "events": EVENTS,
        "chokepoints": idx.to_dict(orient="records"),
        "brent": [{"date": r.date.strftime("%Y-%m-%d"), "usd": r.brent} for r in b.itertuples()],
        "stats": stats,
    }
    (OUT_WEB / "hormuz.json").write_text(json.dumps(web, separators=(",", ":")), encoding="utf-8")

    # Power BI + public downloads (PortWatch: IMF terms, attribution; Brent: EIA via FRED, public domain).
    cols = ["date", "n_total", "n_tanker", "n_container", "n_dry_bulk", "n_general_cargo", "n_roro",
            "capacity", "capacity_tanker"]
    full = h[cols].assign(date=h.date.dt.strftime("%Y-%m-%d"))
    full.to_csv(OUT_BI / "hormuz_daily.csv", index=False)
    full.to_csv(OUT_PUBLIC / "hormuz_daily.csv", index=False)
    idx.to_csv(OUT_BI / "chokepoints_monthly.csv", index=False)
    idx.to_csv(OUT_PUBLIC / "chokepoints_monthly.csv", index=False)
    b.assign(date=b.date.dt.strftime("%Y-%m-%d")).to_csv(OUT_BI / "brent_daily.csv", index=False)

    print("yearly ships/day:", yearly.to_dict())
    print(monthly.tail(14).to_string())
    print(json.dumps({k: v for k, v in stats.items() if k != "sources"}, indent=1))


if __name__ == "__main__":
    main()
