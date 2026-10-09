"""Electric, hybrid or petrol after the 2026 oil shock: what 100 km costs, what buyers did, what the shares did.

Input:  raw/ (from collect.py)
Output: src/data/ev-vs-petrol-2026-10/*.json   -> the web page
        exports/*.csv                          -> Power BI
        public/data/ev-vs-petrol-2026-10/*.csv -> download link on the page

Questions:
1. How much more does 100 km cost on petrol and diesel since the US-Israeli strikes on Iran (Feb 28, 2026),
   and how much did charging at home change?
2. Country by country: what does 100 km cost on each fuel, and up to what charger price is an EV still cheaper?
3. Did EU buyers switch? (ACEA monthly registrations by power source)
4. Did the stock market reward the carmakers selling the cars people switched to?
"""

import itertools
import json
import re
from pathlib import Path

import pandas as pd
import pypdf

HERE = Path(__file__).parent
RAW = HERE / "raw"
SLUG = "ev-vs-petrol-2026-10"
ROOT = HERE.parents[1]
OUT_WEB = ROOT / "src" / "data" / SLUG
OUT_BI = HERE / "exports"
OUT_PUBLIC = ROOT / "public" / "data" / SLUG

WAR = "2026-02-28"  # US and Israel strike Iran
BASE_DAY = "2026-02-27"  # last close before the strikes
PREWAR_WEEK = "2026-02-23"  # last Oil Bulletin week before the strikes
START = "2025-01-01"

# A typical compact car, real-world use. The page lets readers type their own numbers.
# Petrol and diesel: WLTP for a VW Golf-sized car plus the real-world gap TNO measured (about 15% petrol, 10% diesel).
# Hybrid: ADAC EcoTest, Toyota Corolla 1.8 Hybrid, 5.0 l/100 km.
# Electric: about 14.5 kWh WLTP plus the ~25% real-world gap TNO measured for EVs, charging losses included.
USE = {"petrol": 6.5, "diesel": 5.5, "hybrid": 5.0, "ev": 18.0}
KM_YEAR = 15_000

COUNTRY = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CY": "Cyprus", "CZ": "Czechia", "DE": "Germany",
    "DK": "Denmark", "EE": "Estonia", "ES": "Spain", "FI": "Finland", "FR": "France", "GR": "Greece",
    "HR": "Croatia", "HU": "Hungary", "IE": "Ireland", "IT": "Italy", "LT": "Lithuania", "LU": "Luxembourg",
    "LV": "Latvia", "MT": "Malta", "NL": "Netherlands", "PL": "Poland", "PT": "Portugal", "RO": "Romania",
    "SE": "Sweden", "SI": "Slovenia", "SK": "Slovakia",
}
EUROSTAT_GEO = {"GR": "EL"}  # Eurostat calls Greece EL

POWER = ["bev", "phev", "hev", "other", "petrol", "diesel", "total"]  # column order in ACEA tables
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]

CARMAKERS = {  # Yahoo symbol -> name, home market index, index name
    "TSLA": ("Tesla", "^GSPC", "S&P 500"),
    "1211.HK": ("BYD", "^HSI", "Hang Seng"),
    "7203.T": ("Toyota", "^N225", "Nikkei 225"),
    "VOW3.DE": ("Volkswagen", "^STOXX", "STOXX Europe 600"),
    "BMW.DE": ("BMW", "^STOXX", "STOXX Europe 600"),
    "STLAM.MI": ("Stellantis", "^STOXX", "STOXX Europe 600"),
    "RNO.PA": ("Renault", "^STOXX", "STOXX Europe 600"),
    "GM": ("General Motors", "^GSPC", "S&P 500"),
}
# What each sells most of, for the page (from the ACEA and company figures cited in the post).
SELLS = {
    "Tesla": "electric only", "BYD": "electric and plug-in hybrid", "Toyota": "hybrids and petrol",
    "Volkswagen": "petrol, diesel, electric", "BMW": "petrol, diesel, electric", "Stellantis": "petrol, hybrid, electric",
    "Renault": "petrol, hybrid, electric", "General Motors": "mostly petrol pickups and SUVs",
}

SOURCES = {
    "oil_bulletin": "https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en",
    "electricity": "https://ec.europa.eu/eurostat/databrowser/view/nrg_pc_204/default/table",
    "hicp": "https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_minr/default/table",
    "acea": "https://www.acea.auto/nav/?content=passenger-car-registrations",
    "yahoo": "https://finance.yahoo.com",
}


# ---------- fuel ----------

def oil_bulletin():
    """Weekly pump prices with taxes, euro per litre, one row per (date, country)."""
    raw = pd.read_excel(RAW / "oil_bulletin_history.xlsx", sheet_name="Prices with taxes", header=None)
    cols = list(raw.iloc[0])
    data = raw.iloc[3:].reset_index(drop=True)
    dates = pd.to_datetime(data[0], errors="coerce")
    rows = []
    for cc in ["EU", *COUNTRY]:
        p = pd.to_numeric(data[cols.index(f"{cc}_price_with_tax_euro95")], errors="coerce")
        d = pd.to_numeric(data[cols.index(f"{cc}_price_with_tax_diesel")], errors="coerce")
        # Prices are already in euro per 1,000 litres for every country (the exchange-rate column is informative).
        rows.append(pd.DataFrame({"date": dates, "cc": cc, "petrol": p / 1000, "diesel": d / 1000}))
    df = pd.concat(rows).dropna(subset=["date"])
    return df[df.date >= START].sort_values(["cc", "date"])


# ---------- electricity ----------

def eurostat(path):
    d = json.loads(path.read_text(encoding="utf-8"))
    dims = d["id"]
    cats = [sorted(d["dimension"][k]["category"]["index"].items(), key=lambda x: x[1]) for k in dims]
    rows = []
    for i, combo in enumerate(itertools.product(*[[c for c, _ in cs] for cs in cats])):
        v = d["value"].get(str(i))
        if v is not None:
            rows.append({**dict(zip(dims, combo)), "value": v})
    return pd.DataFrame(rows)


def electricity():
    """Latest household price per country (2026-S1, else 2025-S2), euro per kWh, all taxes."""
    df = eurostat(RAW / "eurostat_nrg_pc_204.json").pivot(index="geo", columns="time", values="value")
    out = {}
    for cc in ["EU", *COUNTRY]:
        geo = "EU27_2020" if cc == "EU" else EUROSTAT_GEO.get(cc, cc)
        row = df.loc[geo]
        period = "2026-S1" if pd.notna(row.get("2026-S1")) else "2025-S2"
        out[cc] = {"price": float(row[period]), "period": period, "prewar": float(row["2025-S2"])}
    return out


def electricity_monthly(eu_price_2025s2):
    """EU household electricity, euro per kWh, monthly: the 2025-S2 Eurostat price moved by the electricity CPI."""
    hicp = eurostat(RAW / "eurostat_hicp_cp0451.json").set_index("time")["value"]
    h2 = hicp.loc["2025-07":"2025-12"].mean()
    return (hicp / h2 * eu_price_2025s2).rename("ev_price")


# ---------- registrations ----------

NUM = r"\d{1,3}(?:,\d{3})*"


def eu_row(text):
    """The EUROPEAN UNION row of an ACEA table -> dict of this year's counts by power source."""
    line = next(l for l in text.splitlines() if l.startswith("EUROPEAN UNION"))
    s = line.replace("EUROPEAN UNION", "").replace(" ", "")  # PDF text sometimes splits digits with spaces
    groups = re.findall(rf"({NUM})({NUM})([+-]\d+\.\d)?", s)
    if len(groups) != 7:
        raise ValueError(f"unexpected row: {line}")
    cur = [int(g[0].replace(",", "")) for g in groups]
    if abs(sum(cur[:6]) - cur[6]) > 10:  # ACEA's own totals are sometimes off by a car or two
        raise ValueError(f"power sources do not add up to the total: {line}")
    return dict(zip(POWER, cur))


def acea_table(pdf, kind):
    for page in pypdf.PdfReader(pdf).pages:
        t = page.extract_text()
        if "BY MARKET AND POWER SOURCE" in t and kind in t.replace("YEAR TO DATE", "YEAR-TO-DATE"):
            return eu_row(t)
    raise ValueError(f"{pdf.name}: no {kind} table")


def registrations():
    rows = []
    for pdf in sorted((RAW / "acea").glob("*.pdf")):
        month, year = pdf.stem.split("_")
        rows.append({"month": f"{year}-{MONTHS.index(month) + 1:02d}", **acea_table(pdf, "MONTHLY")})
    # No July 2026 release PDF: July = Jan-Aug minus Jan-Jun minus August.
    aug_ytd = acea_table(RAW / "acea" / "August_2026.pdf", "YEAR-TO-DATE")
    jun_ytd = acea_table(RAW / "acea" / "June_2026.pdf", "YEAR-TO-DATE")
    aug = acea_table(RAW / "acea" / "August_2026.pdf", "MONTHLY")
    rows.append({"month": "2026-07", **{k: aug_ytd[k] - jun_ytd[k] - aug[k] for k in POWER}})
    df = pd.DataFrame(rows).sort_values("month").reset_index(drop=True)
    for k in POWER[:-1]:
        df[f"{k}_share"] = (df[k] / df.total * 100).round(1)
    df["fossil_share"] = ((df.petrol + df.diesel) / df.total * 100).round(1)
    return df


# ---------- shares ----------

def stocks():
    px = pd.read_csv(RAW / "prices.csv", index_col=0, parse_dates=True)
    out, series = [], []
    for sym, (name, idx, idx_name) in CARMAKERS.items():
        s, m = px[sym].dropna(), px[idx].dropna()
        last = s.index[-1]
        chg = (s.iloc[-1] / s.loc[BASE_DAY] - 1) * 100
        mchg = (m.loc[:last].iloc[-1] / m.loc[BASE_DAY] - 1) * 100
        out.append({"symbol": sym, "name": name, "sells": SELLS[name], "base": round(float(s.loc[BASE_DAY]), 2),
                    "last": round(float(s.iloc[-1]), 2), "last_date": str(last.date()), "change_pct": round(chg, 1),
                    "market": idx_name, "market_pct": round(mchg, 1), "vs_market_pts": round(chg - mchg, 1)})
        for d, v in s.loc[BASE_DAY:].items():
            series.append({"symbol": sym, "date": str(d.date()), "index": round(v / s.loc[BASE_DAY] * 100, 1)})
    b = px["BZ=F"].dropna()
    brent = {"base": round(float(b.loc[BASE_DAY]), 2), "last": round(float(b.iloc[-1]), 2), "last_date": str(b.index[-1].date()),
             "change_pct": round((b.iloc[-1] / b.loc[BASE_DAY] - 1) * 100, 1)}
    return sorted(out, key=lambda r: r["change_pct"]), series, brent


# ---------- main ----------

def cost(fuel_price, kind):
    return fuel_price * USE[kind]


def main():
    for d in (OUT_WEB, OUT_BI, OUT_PUBLIC):
        d.mkdir(parents=True, exist_ok=True)

    fuel = oil_bulletin()
    elec = electricity()
    eu = fuel[fuel.cc == "EU"].set_index("date")[["petrol", "diesel"]]
    ev_m = electricity_monthly(elec["EU"]["prewar"])

    # 1. EU weekly cost of 100 km.
    weekly = eu.copy()
    weekly["month"] = weekly.index.strftime("%Y-%m")
    weekly = weekly.join(ev_m, on="month")
    weekly["ev_price"] = weekly["ev_price"].ffill()  # the newest weeks reuse the latest CPI month
    weekly = weekly.reset_index()
    week_rows = [{
        "date": str(r.date.date()),
        "petrol_l": round(r.petrol, 3), "diesel_l": round(r.diesel, 3), "kwh": round(r.ev_price, 3),
        "petrol": round(cost(r.petrol, "petrol"), 2), "diesel": round(cost(r.diesel, "diesel"), 2),
        "hybrid": round(cost(r.petrol, "hybrid"), 2), "ev": round(r.ev_price * USE["ev"], 2),
    } for r in weekly.itertuples()]
    pre = next(w for w in week_rows if w["date"] == PREWAR_WEEK)
    now = week_rows[-1]
    hicp_last = ev_m.index[-1]

    # 2. Countries, latest week.
    latest_date = fuel.date.max()
    countries = []
    for cc, name in COUNTRY.items():
        f = fuel[(fuel.cc == cc)].set_index("date")
        if latest_date not in f.index or pd.isna(f.loc[latest_date, "petrol"]):
            continue
        p, dsl = f.loc[latest_date, "petrol"], f.loc[latest_date, "diesel"]
        p0 = f.loc[PREWAR_WEEK, "petrol"]
        e = elec[cc]
        petrol100 = cost(p, "petrol")
        countries.append({
            "cc": cc, "country": name,
            "petrol_l": round(p, 3), "diesel_l": round(dsl, 3), "kwh": round(e["price"], 3), "kwh_period": e["period"],
            "petrol": round(petrol100, 2), "diesel": round(cost(dsl, "diesel"), 2), "hybrid": round(cost(p, "hybrid"), 2),
            "ev_home": round(e["price"] * USE["ev"], 2),
            "breakeven_kwh": round(petrol100 / USE["ev"], 3),
            "breakeven_kwh_prewar": round(cost(p0, "petrol") / USE["ev"], 3),
            "petrol_change_pct": round((p / p0 - 1) * 100, 1),
            "saving_year_home": round((petrol100 - e["price"] * USE["ev"]) * KM_YEAR / 100),
        })
    countries.sort(key=lambda c: c["petrol"] - c["ev_home"], reverse=True)

    # 3. Registrations.
    reg = registrations()
    reg_rows = reg[["month", "bev_share", "hev_share", "phev_share", "fossil_share", "petrol_share", "diesel_share", "total"]].to_dict("records")
    r_aug, r_aug25 = reg.set_index("month").loc["2026-08"], reg.set_index("month").loc["2025-08"]
    r_feb = reg.set_index("month").loc["2026-02"]

    # 4. Shares.
    st, st_series, brent = stocks()

    summary = {
        "prewar_week": PREWAR_WEEK, "latest_week": now["date"], "hicp_last_month": hicp_last,
        "use": USE, "km_year": KM_YEAR,
        "petrol_l": {"prewar": pre["petrol_l"], "now": now["petrol_l"], "change_pct": round((now["petrol_l"] / pre["petrol_l"] - 1) * 100, 1)},
        "diesel_l": {"prewar": pre["diesel_l"], "now": now["diesel_l"], "change_pct": round((now["diesel_l"] / pre["diesel_l"] - 1) * 100, 1)},
        "kwh": {"prewar": pre["kwh"], "now": now["kwh"], "change_pct": round((now["kwh"] / pre["kwh"] - 1) * 100, 1),
                "eu_2025s2": elec["EU"]["prewar"]},
        "per100": {k: {"prewar": pre[k], "now": now[k]} for k in ("petrol", "diesel", "hybrid", "ev")},
        "breakeven_kwh": {"prewar": round(pre["petrol"] / USE["ev"], 3), "now": round(now["petrol"] / USE["ev"], 3)},
        "saving_year": {
            # From the published per-unit prices (not the rounded per-100 km costs), so the page calculator matches.
            "ev_home_vs_petrol": round((now["petrol_l"] * USE["petrol"] - now["kwh"] * USE["ev"]) * KM_YEAR / 100),
            "hybrid_vs_petrol": round(now["petrol_l"] * (USE["petrol"] - USE["hybrid"]) * KM_YEAR / 100),
            "ev_home_vs_petrol_prewar": round((pre["petrol_l"] * USE["petrol"] - pre["kwh"] * USE["ev"]) * KM_YEAR / 100),
        },
        "registrations": {
            "aug_2026_bev": round(float(r_aug.bev_share), 1), "aug_2025_bev": round(float(r_aug25.bev_share), 1),
            "feb_2026_bev": round(float(r_feb.bev_share), 1),
            "aug_2026_fossil": round(float(r_aug.fossil_share), 1), "aug_2025_fossil": round(float(r_aug25.fossil_share), 1),
            "aug_2026_hev": round(float(r_aug.hev_share), 1),
        },
        "brent": brent,
        "stocks_up": [s["name"] for s in st if s["change_pct"] > 0],
    }

    (OUT_WEB / "costs.json").write_text(json.dumps({"summary": summary, "weekly": week_rows, "countries": countries}, indent=1), encoding="utf-8")
    (OUT_WEB / "registrations.json").write_text(json.dumps(reg_rows, indent=1), encoding="utf-8")
    (OUT_WEB / "stocks.json").write_text(json.dumps({"base_day": BASE_DAY, "brent": brent, "stocks": st, "series": st_series}, indent=1), encoding="utf-8")

    # Power BI and public download. ACEA forbids reproducing its documents, so the public file carries only
    # our own cost calculations from EU open data, not the registration tables.
    pd.DataFrame(week_rows).to_csv(OUT_BI / "weekly.csv", index=False)
    pd.DataFrame(countries).to_csv(OUT_BI / "countries.csv", index=False)
    reg.to_csv(OUT_BI / "registrations.csv", index=False)
    pd.DataFrame(st).to_csv(OUT_BI / "stocks.csv", index=False)
    pd.DataFrame(countries).to_csv(OUT_PUBLIC / "cost-per-100km-by-country.csv", index=False)
    pd.DataFrame(week_rows).to_csv(OUT_PUBLIC / "cost-per-100km-eu-weekly.csv", index=False)

    print(json.dumps(summary, indent=1))
    print(pd.DataFrame(countries)[["country", "petrol", "diesel", "hybrid", "ev_home", "kwh_period", "breakeven_kwh", "petrol_change_pct", "saving_year_home"]].to_string())
    print(reg[["month", "bev_share", "hev_share", "phev_share", "fossil_share", "total"]].to_string())
    print(pd.DataFrame(st)[["name", "change_pct", "market", "market_pct", "vs_market_pts", "last_date"]].to_string())


if __name__ == "__main__":
    main()
