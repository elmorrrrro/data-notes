"""How richly big tech IPOs were priced, what their shares did next, and where listed tech trades on growth.

Input:  raw/ (from collect.py) + the SHARES_AFTER_IPO table below, typed from each final prospectus
Output: src/data/anthropic-ipo-2026-10/{ipos,peers,basket,race,cisco,gdp,stats}.json  -> the web page
        exports/*.csv                                                                 -> Power BI
        public/data/anthropic-ipo-2026-10/*.csv                                       -> download link on the page

Four comparisons (same price, speed, the Cisco lesson, size against countries) and two questions:
1. IPOs: does a higher price-to-sales multiple at the offer price predict weaker returns over the next 1 and 3 years?
2. Peers: how does the price-to-sales multiple of listed tech companies rise with revenue growth today?
Anthropic itself is not in either sample: its figures are private and come from press reports, so the page places
it next to the fitted lines as scenarios rather than as a data point.
"""

import json
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from universe import ANTHROPIC_FOUNDED, BASKET, BENCHMARK, CISCO, FOUNDED, GONE, IPOS, PEERS

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

HERE = Path(__file__).parent
RAW = HERE / "raw"
SLUG = "anthropic-ipo-2026-10"
ROOT = HERE.parents[1]
OUT_WEB = ROOT / "src" / "data" / SLUG
OUT_BI = HERE / "exports"
OUT_PUBLIC = ROOT / "public" / "data" / SLUG

END_DATE = "2026-10-02"  # last close before publication
RNG = np.random.default_rng(2026)
PERMUTATIONS = 20_000

# Shares of all classes outstanding right after the IPO, from "The Offering" summary of each 424B4 (before any
# underwriters' option). Market value at IPO = offer price x these shares. This is the basic count; press figures
# are often "fully diluted" (with options and RSUs), which is higher: Facebook's widely quoted $104 billion vs
# $81 billion here.
SHARES_AFTER_IPO = {
    "GRPN": (637_803_328, "Total shares of Class A common stock and Class B common stock to be outstanding after this offering 637,803,328 shares"),
    "META": (2_138_085_037, "Total Class A and Class B common stock to be outstanding after our initial public offering 2,138,085,037 shares"),
    "WDAY": (160_290_031, "Total Class A and Class B common stock to be outstanding after our initial public offering 160,290,031 shares"),
    "BABA": (2_465_005_966, "Ordinary shares outstanding immediately after this offering 2,465,005,966 ordinary shares (one ADS = one ordinary share)"),
    "XYZ": (327_944_711, "Total Class A common stock and Class B common stock to be outstanding after this offering 327,944,711 shares"),
    "SNAP": (1_157_213_232, "Class A 661,834,416 + Class B 279,490,968 + Class C 215,887,848 shares to be outstanding after this offering"),
    "DBX": (391_903_011, "Class A 52,579,153 + Class B 339,323,858 shares to be outstanding after this offering and the concurrent private placement"),
    "LYFT": (285_877_300, "Class A and Class B common stock to be outstanding after this offering 285,877,300 shares"),
    "PINS": (529_372_774, "Total Class A common stock and Class B common stock to be outstanding after this offering 529,372,774 shares"),
    "ZM": (256_388_371, "Total Class A and Class B common stock to be outstanding after this offering and the concurrent private placement 256,388,371 shares"),
    "UBER": (1_682_521_965, "Common stock to be outstanding after this offering and the private placement 1,682,521,965 shares"),
    "CRWD": (196_688_971, "Total Class A and Class B common stock to be outstanding after this offering 196,688,971 shares"),
    "DDOG": (289_834_665, "Total Class A common stock and Class B common stock to be outstanding after this offering 289,834,665 shares"),
    "PTON": (279_390_508, "Total Class A and Class B common stock to be outstanding after this offering and the private placement 279,390,508 shares"),
    "SNOW": (276_694_828, "Class A 36,208,709 + Class B 240,486,119 shares to be outstanding after this offering, the concurrent private placements, and the secondary transaction"),
    "U": (263_366_733, "Common stock to be outstanding after this offering 263,366,733 shares"),
    "DASH": (317_656_521, "Class A 286,343,071 + Class B 31,313,450 shares to be outstanding after this offering"),
    "ABNB": (597_448_251, "Class A 98,682,548 + Class B 489,565,703 + Class H 9,200,000 shares to be outstanding after this offering"),
    "AFRM": (242_746_771, "Total shares of common stock to be outstanding after this offering 242,746,771 shares"),
    "BMBL": (184_613_467, "Class A common stock outstanding after this offering assuming exchange of all Common Units held by the Pre-IPO Common Unitholders 184,613,467"),
    "CPNG": (1_715_140_797, "Total Class A common stock and Class B common stock to be outstanding after this offering 1,715,140,797 shares"),
    "PATH": (519_153_731, "Total Class A common stock and Class B common stock to be outstanding after this offering 519,153,731 shares"),
    "S": (256_371_279, "Class A 36,428,568 + Class B 219,942,711 shares to be outstanding after this offering and the private placement"),
    "HOOD": (842_404_025, "Total common stock to be outstanding after this offering 842,404,025 shares"),
    "TOST": (499_332_681, "Total Class A common stock and Class B common stock to be outstanding after this offering 499,332,681 shares"),
    "GTLB": (143_014_821, "Total Class A and Class B common stock to be outstanding after this offering 143,014,821 shares"),
    "RIVN": (868_277_142, "Total Class A and Class B common stock to be outstanding after this offering 868,277,142 shares"),
    "MBLY": (795_761_905, "Total shares of common stock to be outstanding after this offering and the concurrent private placement 795,761,905 shares"),
    "ARM": (1_026_054_856, "1,026,054,856 ordinary shares outstanding after this offering, including the ordinary shares represented by ADSs"),
    "CART": (276_653_464, "Common stock to be outstanding after this offering 276,653,464 shares"),
    "ALAB": (152_503_008, "Common stock to be outstanding immediately after this offering 152,503,008 shares"),
    "RDDT": (158_993_090, "Class A 36,879,787 + Class B 122,113,303 shares to be outstanding immediately after this offering"),
    "CRWV": (464_099_446, "Class A 345,997,406 + Class B 118,102,040 shares to be outstanding after this offering and the concurrent share issuance"),
}

# Alibaba reports in renminbi; its prospectus converts at the noon buying rate of Sep 12, 2014.
FX_TO_USD = {"BABA": ("CNY", 6.1344, "On September 12, 2014, the noon buying rate for Renminbi was RMB6.1344 to US$1.00")}

# Alibaba filed only annual reports (20-F) in XBRL, so its last quarter before the IPO is typed from the 424B4.
QUARTER_FROM_PROSPECTUS = {
    "BABA": dict(rev=15_771e6 / 6.1344, end=pd.Timestamp("2014-06-30"), rev_year_ago=10_778e6 / 6.1344,
                 quote="Revenue breakdown ... Three months ended June 30, 2013 2014 (in millions of RMB) ... Total 10,778 15,771"),
}

# Anthropic is private: preliminary, unaudited figures from its shareholder updates as reported by the press.
ANTHROPIC = dict(
    q2_2026_revenue=11.5e9, q2_2025_revenue=0.787e9, q1_2026_revenue=4.73e9, run_rate_july_2026=65e9,
    valuations={"Series H, May 2026": 965e9, "IPO target reported by the FT": 2000e9},
    sources={
        "quarters": "https://www.cnbc.com/2026/08/15/anthropic-revenue-jumps-to-over-11point5-billion-in-q2-report.html",
        "run_rate": "https://www.cnbc.com/2026/08/17/anthropic-says-annualized-revenue-climbed-to-65-billion-in-july.html",
        "series_h": "https://www.anthropic.com/news/series-h",
    },
)

REVENUE_CONCEPTS = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet",
                    "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueServicesNet"]


# ---------------------------------------------------------------- revenue from XBRL company facts

def revenue_periods(ticker):
    """All reported revenue periods as rows (start, end, days, usd). For each period, the latest filed value of
    each concept, then the largest across concepts: some companies tag only part of revenue with one concept
    (Robinhood's contract revenue excludes net interest) and the total with another."""
    facts = json.loads((RAW / "facts" / f"{ticker}.json").read_text())["facts"].get("us-gaap", {})
    unit, rate = ("USD", 1.0)
    if ticker in FX_TO_USD:
        unit, rate = FX_TO_USD[ticker][0], FX_TO_USD[ticker][1]
    rows = []
    for c in REVENUE_CONCEPTS:
        for f in facts.get(c, {}).get("units", {}).get(unit, []):
            if "start" in f:
                rows.append((c, f["start"], f["end"], f["val"] / rate, f["filed"]))
    df = pd.DataFrame(rows, columns=["concept", "start", "end", "usd", "filed"])
    df = df.sort_values("filed").groupby(["concept", "start", "end"]).last().reset_index()
    df = df.groupby(["start", "end"], as_index=False)["usd"].max()
    df["start"], df["end"] = pd.to_datetime(df["start"]), pd.to_datetime(df["end"])
    df["days"] = (df["end"] - df["start"]).dt.days
    return df


def quarters(periods):
    """Quarterly revenue by quarter end. Fourth quarters are rarely tagged; derive them as the fiscal year minus
    the first nine months (or minus the three tagged quarters)."""
    q = periods[periods["days"].between(80, 100)].set_index("end")["usd"]
    q = q[~q.index.duplicated(keep="last")].sort_index()
    starts = periods[periods["days"].between(80, 100)].set_index("end")["start"]
    starts = starts[~starts.index.duplicated(keep="last")]
    out, out_start = q.to_dict(), starts.to_dict()
    for _, y in periods[periods["days"].between(350, 380)].iterrows():
        if y["end"] in out:
            continue
        nine = periods[(periods["start"] == y["start"]) & periods["days"].between(260, 285)]
        if not nine.empty:
            n = nine.iloc[-1]
            out[y["end"]] = y["usd"] - n["usd"]
            out_start[y["end"]] = n["end"] + pd.Timedelta(days=1)
            continue
        inside = [e for e in out if out_start[e] >= y["start"] and e < y["end"]]
        if len(inside) == 3:
            out[y["end"]] = y["usd"] - sum(out[e] for e in inside)
            out_start[y["end"]] = max(inside) + pd.Timedelta(days=1)
    s = pd.Series(out, dtype=float, index=pd.DatetimeIndex(list(out))).sort_index()
    return s, pd.Series(out_start, index=pd.DatetimeIndex(list(out_start))).reindex(s.index)


def last_quarter(periods, as_of):
    """The last quarter that ended on or before `as_of` (if it ended within 150 days of it) and the same quarter
    a year earlier. Quarter x 4 is the "run rate" that Anthropic's own figures are quoted on, and it exists for
    IPOs whose earlier quarters never appeared in XBRL (DoorDash's first filing after its IPO was a 10-K)."""
    q, _ = quarters(periods)
    q = q[(q.index <= as_of) & (q.index > as_of - pd.Timedelta(days=150))]
    if q.empty:
        return None
    end = q.index[-1]
    full, _ = quarters(periods)
    year_ago = full[(full.index - (end - pd.DateOffset(years=1))).map(lambda d: abs(d.days) <= 10)]
    return dict(rev=float(q.iloc[-1]), end=end, rev_year_ago=float(year_ago.iloc[0]) if len(year_ago) else None)


def trailing(periods, as_of):
    """Revenue for the 12 months to the last quarter that ended on or before `as_of`, the same 12 months a year
    earlier, and the last quarter alone. Falls back to fiscal years when quarters are missing (Alibaba)."""
    q, qs = quarters(periods)
    q, qs = q[q.index <= as_of], qs[qs.index <= as_of]

    def ttm(end_idx):
        if end_idx < 3:
            return None
        ends = q.index[end_idx - 3:end_idx + 1]
        gaps = [(qs[ends[i + 1]] - ends[i]).days for i in range(3)]
        if all(0 <= g <= 10 for g in gaps):
            return float(q[ends].sum()), ends[0], ends[-1]
        return None

    cur = ttm(len(q) - 1) if len(q) else None
    years = periods[periods["days"].between(350, 380) & (periods["end"] <= as_of)].sort_values("end")
    if cur and (years.empty or cur[2] >= years["end"].iloc[-1]):
        idx = len(q) - 1
        prev_end = cur[2] - pd.DateOffset(years=1)
        prev_idx = [i for i, e in enumerate(q.index) if abs((e - prev_end).days) <= 10]
        prev = ttm(prev_idx[0]) if prev_idx else None
        if prev is None and not years.empty and abs((years["end"].iloc[-1] - prev_end).days) <= 10:
            prev = (float(years["usd"].iloc[-1]), None, None)
        return dict(rev=cur[0], rev_prev=prev[0] if prev else None, last_q=float(q.iloc[idx]),
                    period_end=cur[2], basis="last 4 quarters")
    if years.empty:
        return None
    y = years.iloc[-1]
    prev = years[(years["end"] - y["end"]).dt.days.between(-380, -350)]
    return dict(rev=float(y["usd"]), rev_prev=float(prev["usd"].iloc[-1]) if not prev.empty else None,
                last_q=None, period_end=y["end"], basis="fiscal year")


# ---------------------------------------------------------------- prices and returns

def prices(ticker):
    p = pd.read_csv(RAW / "prices" / f"{ticker}.csv", index_col="date", parse_dates=True)
    return p[p.index <= END_DATE]


def on_or_before(p, day):
    p = p[p.index <= day]
    return p.iloc[-1] if len(p) else None


def ipo_returns(ticker, ipo_date, offer):
    """Total returns (dividends reinvested) from the offer price and from the first close, after 1 and 3 years,
    plus the same windows for the Nasdaq-100 ETF. Yahoo's Close is split-adjusted, so the offer price is too."""
    p, b = prices(ticker), prices(BENCHMARK)
    day0 = pd.Timestamp(ipo_date)
    first = p.loc[day0]
    splits = p.loc[p.index > day0, "Stock Splits"]
    split_factor = float(np.prod(splits[splits > 0])) if (splits > 0).any() else 1.0
    offer_adj = offer / split_factor * first["Adj Close"] / first["Close"]
    b0 = b.loc[day0, "Adj Close"]
    out = dict(first_close=float(first["Close"] * split_factor), first_day_pop=float(first["Close"] * split_factor / offer - 1))
    for years in (1, 3):
        end = day0 + pd.DateOffset(years=years)
        if end > pd.Timestamp(END_DATE):
            out |= {f"ret_offer_{years}y": None, f"ret_first_{years}y": None, f"qqq_{years}y": None}
            continue
        pe, be = on_or_before(p, end), on_or_before(b, end)
        out[f"ret_offer_{years}y"] = float(pe["Adj Close"] / offer_adj - 1)
        out[f"ret_first_{years}y"] = float(pe["Adj Close"] / first["Adj Close"] - 1)
        out[f"qqq_{years}y"] = float(be["Adj Close"] / b0 - 1)
    return out


# ---------------------------------------------------------------- statistics without scipy

def ols(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    slope, intercept = np.polyfit(x, y, 1)
    r = float(np.corrcoef(x, y)[0, 1])
    return float(slope), float(intercept), r


def ranks(a):
    return pd.Series(a).rank().to_numpy()


def permutation_p(x, y, stat):
    """Two-sided p-value: how often shuffled pairs give a statistic at least as far from zero. With 20-30 points
    this is safer than a t-test, which assumes normal errors."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    obs = abs(stat(x, y))
    hits = sum(abs(stat(x, RNG.permutation(y))) >= obs for _ in range(PERMUTATIONS))
    return (hits + 1) / (PERMUTATIONS + 1)


def bootstrap_slope(x, y, n=5000):
    x, y = np.asarray(x, float), np.asarray(y, float)
    idx = RNG.integers(0, len(x), size=(n, len(x)))
    slopes = [np.polyfit(x[i], y[i], 1)[0] for i in idx if np.ptp(x[i]) > 0]
    return [float(v) for v in np.percentile(slopes, [5, 95])]


def relation(df, xcol, ycol):
    d = df[[xcol, ycol]].dropna()
    x, y = d[xcol].to_numpy(), d[ycol].to_numpy()
    slope, intercept, r = ols(x, y)
    rho = float(np.corrcoef(ranks(x), ranks(y))[0, 1])
    return dict(n=len(d), slope=slope, intercept=intercept, r=r, r2=r * r,
                p_pearson=permutation_p(x, y, lambda a, b: np.corrcoef(a, b)[0, 1]),
                spearman=rho, p_spearman=permutation_p(ranks(x), ranks(y), lambda a, b: np.corrcoef(a, b)[0, 1]),
                slope_90ci=bootstrap_slope(x, y))


# ---------------------------------------------------------------- the two samples

def prospectus_check(ticker, offer):
    txt = re.sub(r"\s+", " ", BeautifulSoup((RAW / "424b4" / f"{ticker}.htm").read_bytes(), "lxml").get_text(" "))
    m = re.search(r"initial public offering price[^$]{0,80}\$\s?(\d{1,3}\.\d{2})", txt, re.I)
    assert m and float(m.group(1)) == offer, f"{ticker}: offer price {offer} not found in the 424B4"
    shares, quote = SHARES_AFTER_IPO[ticker]
    for n in re.findall(r"\d{1,3}(?:,\d{3})+", quote):
        assert n in txt, f"{ticker}: {n} not found in the 424B4"


def ipo_table():
    subs_url = {}
    rows = []
    for t, name, day, offer in IPOS:
        prospectus_check(t, offer)
        shares, quote = SHARES_AFTER_IPO[t]
        value = offer * shares
        lq = QUARTER_FROM_PROSPECTUS.get(t) or last_quarter(revenue_periods(t), pd.Timestamp(day) - pd.Timedelta(days=30))
        cik = json.loads((RAW / "subs" / f"{t}.json").read_text())["cik"].lstrip("0")
        row = dict(ticker=t, company=name, ipo_date=day, offer_price=offer, shares_after_ipo=shares,
                   value_at_offer_bn=value / 1e9,
                   quarter_end=lq["end"].date().isoformat() if lq else None,
                   run_rate_bn=lq["rev"] * 4 / 1e9 if lq else None,
                   quarter_growth=(lq["rev"] / lq["rev_year_ago"] - 1) if lq and lq["rev_year_ago"] else None,
                   ps_run_rate=value / (lq["rev"] * 4) if lq else None,
                   prospectus=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=424B4",
                   shares_quote=quote)
        row |= ipo_returns(t, day, offer)
        for y in (1, 3):
            if row[f"ret_offer_{y}y"] is not None:
                row[f"excess_offer_{y}y"] = (1 + row[f"ret_offer_{y}y"]) / (1 + row[f"qqq_{y}y"]) - 1
                row[f"excess_first_{y}y"] = (1 + row[f"ret_first_{y}y"]) / (1 + row[f"qqq_{y}y"]) - 1
        rows.append(row)
    return pd.DataFrame(rows)


def peer_table():
    quotes = json.loads((RAW / "peers_info.json").read_text())["quotes"]
    rows = []
    for t in PEERS:
        q = quotes[t]
        close = float(on_or_before(prices(t), pd.Timestamp(END_DATE))["Close"])
        shares = q["impliedSharesOutstanding"] or q["sharesOutstanding"]
        rev = trailing(revenue_periods(t), pd.Timestamp(END_DATE))
        cap = close * shares
        rows.append(dict(ticker=t, company=q["longName"], industry=q["industry"], close=close,
                         shares_all_classes=shares, market_cap_bn=cap / 1e9, revenue_ttm_bn=rev["rev"] / 1e9,
                         revenue_basis=rev["basis"], revenue_period_end=rev["period_end"].date().isoformat(),
                         revenue_growth=(rev["rev"] / rev["rev_prev"] - 1) if rev["rev_prev"] else None,
                         ps_ttm=cap / rev["rev"]))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- the four comparisons

def fiscal_years(ticker, concepts=REVENUE_CONCEPTS):
    """Annual values by fiscal-year end: latest filing per concept, then the largest across concepts."""
    facts = json.loads((RAW / "facts" / f"{ticker}.json").read_text())["facts"].get("us-gaap", {})
    rows = [(c, f["start"], f["end"], f["val"], f["filed"]) for c in concepts
            for f in facts.get(c, {}).get("units", {}).get("USD", []) if "start" in f]
    df = pd.DataFrame(rows, columns=["concept", "start", "end", "usd", "filed"])
    df["start"], df["end"] = pd.to_datetime(df["start"]), pd.to_datetime(df["end"])
    df = df[(df["end"] - df["start"]).dt.days.between(350, 380)]
    df = df.sort_values("filed").groupby(["concept", "end"])["usd"].last().reset_index()
    return df.groupby("end")["usd"].max().sort_index()


def basket_table():
    """Market value at the last close, and revenue and net income of the latest fiscal year (10-K)."""
    quotes = json.loads((RAW / "basket_info.json").read_text())["quotes"]
    rows = []
    for t in BASKET:
        close = float(on_or_before(prices(t), pd.Timestamp(END_DATE))["Close"])
        shares = quotes[t]["impliedSharesOutstanding"] or quotes[t]["sharesOutstanding"]
        rev = fiscal_years(t)
        rev = rev[rev.index <= END_DATE]
        # Net income attributable to the company; Ford tags it only as "available to common stockholders".
        income = next(v for c in ["NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"]
                      if rev.index[-1] in (v := fiscal_years(t, [c])))
        rows.append(dict(ticker=t, company=quotes[t]["longName"], market_cap_bn=close * shares / 1e9,
                         fiscal_year_end=rev.index[-1].date().isoformat(), revenue_bn=rev.iloc[-1] / 1e9,
                         net_income_bn=income[rev.index[-1]] / 1e9))
    df = pd.DataFrame(rows)
    df["cumulative_cap_bn"] = df["market_cap_bn"].cumsum()
    return df


def race_table():
    """Years from incorporation to the first quarter whose revenue x 4 reached Anthropic's latest quarter x 4."""
    target = ANTHROPIC["q2_2026_revenue"] * 4
    rows = []
    for t, f in FOUNDED.items():
        doc = next((RAW / "founding").glob(f"{t}.*"), None) or RAW / "424b4" / f"{t}.htm"
        txt = re.sub(r"\s+", " ", BeautifulSoup(doc.read_bytes(), "lxml").get_text(" "))
        assert f["quote"] in txt, f"{t}: incorporation sentence not found"
        q, _ = quarters(revenue_periods(f["facts"]))
        hit = q[q * 4 >= target]
        assert hit.index[0] > q.index[0], f"{t}: crossing is before the first XBRL quarter"
        start = pd.Timestamp(f["month"] + "-01")
        rows.append(dict(ticker=t, company=f["name"], incorporated=f["month"], quarter_end=hit.index[0].date().isoformat(),
                         quarter_bn=hit.iloc[0] / 1e9, run_rate_bn=hit.iloc[0] * 4 / 1e9,
                         previous_quarter_bn=q[q.index < hit.index[0]].iloc[-1] / 1e9,
                         years=(hit.index[0] - start).days / 365.25))
    start, end = pd.Timestamp(ANTHROPIC_FOUNDED + "-01"), pd.Timestamp("2026-06-30")
    rows.append(dict(ticker="ANTHROPIC", company="Anthropic", incorporated=ANTHROPIC_FOUNDED, quarter_end=end.date().isoformat(),
                     quarter_bn=ANTHROPIC["q2_2026_revenue"] / 1e9, run_rate_bn=target / 1e9,
                     previous_quarter_bn=ANTHROPIC["q1_2026_revenue"] / 1e9, years=(end - start).days / 365.25))
    return pd.DataFrame(rows), target


# Cisco before XBRL: fiscal years (ending late July) from five-year tables, typed with the text they come from.
CISCO_REVENUE_TYPED = {
    "10k_2000.txt": ([1996, 1997, 1998, 1999, 2000], [4_101, 6_452, 8_489, 12_173, 18_928],
                     "Net sales $18,928 $12,173 $8,489 $6,452 $4,101"),
    "ar_2004.htm": ([2001, 2002, 2003, 2004], [22_293, 18_915, 18_878, 22_045],
                    "Net sales $ 22,045 $ 18,878 $ 18,915 $ 22,293 $ 18,928"),
    "ar_2009.htm": ([2005, 2006, 2007, 2008, 2009], [24_801, 28_484, 34_922, 39_540, 36_117],
                    "Net sales $ 36,117 $ 39,540 $ 34,922 $ 28,484 $ 24,801"),
}
# The quarter before the March 2000 peak, from the 10-Q for the quarter ended January 29, 2000. The share count
# date (Feb 25) is before the 2-for-1 split of March 22, 2000, so it is doubled.
CISCO_PEAK = dict(
    date="2000-03-27", shares_before_split=3_468_815_049, split=2,
    quarter=4_350e6, quarter_year_ago=2_845e6, six_months=8_264e6, six_months_year_ago=5_443e6, fiscal_1999=12_173e6,
    quotes=["As of February 25, 2000, 3,468,815,049 shares of the Registrant's common stock were outstanding",
            "Net sales $4,350 $2,845 $8,264 $5,443"],
)


def cisco_table():
    txt = {}
    for name in [*CISCO_REVENUE_TYPED, "10q_2000-01.txt"]:
        raw = (RAW / "cisco" / name).read_bytes()
        txt[name] = re.sub(r"\s+", " ", BeautifulSoup(raw, "lxml").get_text(" ") if name.endswith(".htm") else raw.decode("latin-1"))
    revenue = {}
    for name, (years, vals, quote) in CISCO_REVENUE_TYPED.items():
        assert quote in txt[name], f"Cisco: '{quote}' not found in {name}"
        revenue |= {y: v * 1e6 for y, v in zip(years, vals)}
    for q in CISCO_PEAK["quotes"]:
        assert q in txt["10q_2000-01.txt"], f"Cisco: '{q}' not found in the 10-Q"
    for end, v in fiscal_years(CISCO).items():
        revenue.setdefault(end.year, v)

    pk = CISCO_PEAK
    p, b = prices(CISCO), prices(BENCHMARK)
    peak_day = pd.Timestamp(pk["date"])
    peak = p.loc[peak_day]
    assert peak["Close"] == p.loc[:"2001", "Close"].max(), "Cisco: peak date is not the highest close"
    cap = peak["Close"] * pk["shares_before_split"] * pk["split"]
    ttm = pk["fiscal_1999"] - pk["six_months_year_ago"] + pk["six_months"]
    after = p[p.index > peak_day]
    regained = after[after["Close"] >= peak["Close"]].index
    yearly = pd.DataFrame([dict(fiscal_year=y, revenue_bn=v / 1e9) for y, v in sorted(revenue.items())])
    yearly = yearly[yearly["fiscal_year"] <= pd.Timestamp(END_DATE).year]
    # Split-adjusted close at each fiscal-year end (late July), for the revenue vs share price chart.
    yearly["close_at_fy_end"] = [float(on_or_before(p, pd.Timestamp(f"{y}-07-31"))["Close"]) for y in yearly["fiscal_year"]]
    summary = dict(
        peak_date=pk["date"], peak_close=float(peak["Close"]), market_cap_bn=cap / 1e9,
        revenue_ttm_bn=ttm / 1e9, ps_ttm=cap / ttm, run_rate_bn=pk["quarter"] * 4 / 1e9,
        ps_quarter_x4=cap / (pk["quarter"] * 4), quarter_growth=pk["quarter"] / pk["quarter_year_ago"] - 1,
        low_date=after["Close"].idxmin().date().isoformat(), low_close=float(after["Close"].min()),
        drawdown=float(after["Close"].min() / peak["Close"] - 1),
        regained_date=regained[0].date().isoformat() if len(regained) else None,
        years_to_regain=(regained[0] - peak_day).days / 365.25 if len(regained) else None,
        close_end=float(p["Close"].iloc[-1]), total_return_since_peak=float(p["Adj Close"].iloc[-1] / peak["Adj Close"] - 1),
        qqq_total_return_since_peak=float(b["Adj Close"].iloc[-1] / b.loc[peak_day, "Adj Close"] - 1),
        latest_fiscal_year=int(yearly["fiscal_year"].iloc[-1]),
        revenue_multiple_since_2000=float(yearly["revenue_bn"].iloc[-1] * 1e9 / revenue[2000]),
        sources=dict(q10="https://www.sec.gov/Archives/edgar/data/858877/0000891618-00-001422.txt",
                     k10_2000="https://www.sec.gov/Archives/edgar/data/858877/000109581100003692/f65797e10-k.txt",
                     ar_2004="https://www.sec.gov/Archives/edgar/data/858877/000119312504158427/dex131.htm",
                     ar_2009="https://www.sec.gov/Archives/edgar/data/858877/000119312509190326/dex131.htm"),
    )
    return yearly, summary


def gdp_table():
    """IMF World Economic Outlook: GDP in current US dollars (billions) for 2026, an IMF estimate for this year."""
    names = json.loads((RAW / "imf_countries.json").read_text())["countries"]
    gdp = json.loads((RAW / "imf_gdp.json").read_text())["values"]["NGDPD"]
    df = pd.DataFrame([dict(iso=k, country=names[k]["label"], gdp_2026_bn=v["2026"]) for k, v in gdp.items()
                       if k in names and v.get("2026") is not None])
    df = df.sort_values("gdp_2026_bn", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    return df


def main():
    ipos, peers = ipo_table(), peer_table()

    # Rivian had almost no revenue before its IPO (a multiple in the thousands): shown, but left out of the fits.
    ipos["pre_revenue"] = ipos["ps_run_rate"].isna() | (ipos["ps_run_rate"] > 500)
    ipos["log_ps"] = np.where(ipos["pre_revenue"], np.nan, np.log(ipos["ps_run_rate"]))
    for y in (1, 3):
        for base in ("offer", "first"):
            ipos[f"log_excess_{base}_{y}y"] = np.log1p(ipos[f"excess_{base}_{y}y"])
    peers["log_ps"] = np.log(peers["ps_ttm"])

    stats = dict(
        end_date=END_DATE, gone=GONE, permutations=PERMUTATIONS,
        ipo_n=len(ipos), ipo_n_fit=int((~ipos["pre_revenue"]).sum()),
        ipo_vs_excess={f"{base}_{y}y": relation(ipos, "log_ps", f"log_excess_{base}_{y}y")
                       for y in (1, 3) for base in ("offer", "first")},
        ipo_share_beating_qqq={f"{base}_{y}y": float((ipos[f"excess_{base}_{y}y"].dropna() > 0).mean())
                               for y in (1, 3) for base in ("offer", "first")},
        ipo_median={c: float(ipos[c].median()) for c in ["ps_run_rate", "first_day_pop", "excess_first_1y", "excess_first_3y",
                                                          "excess_offer_1y", "excess_offer_3y"]},
        peers_growth_vs_ps=relation(peers, "revenue_growth", "log_ps"),
        peers_median_ps=float(peers["ps_ttm"].median()),
    )

    # Where Anthropic would sit. Its quarter x 4 matches the IPO sample's run-rate multiple; its year-on-year
    # quarterly growth stands in for the peers' trailing growth (both measure the same 12-month change, but the
    # peers' figure is smoothed over four quarters).
    a = ANTHROPIC
    run_rate = a["q2_2026_revenue"] * 4
    growth = a["q2_2026_revenue"] / a["q2_2025_revenue"] - 1
    fit = stats["peers_growth_vs_ps"]
    fitted_ps = ipos.loc[~ipos["pre_revenue"], "ps_run_rate"]
    scenarios = []
    for label, v in a["valuations"].items():
        ps = v / run_rate
        scenarios.append(dict(label=label, valuation_bn=v / 1e9, ps_quarter_x4=ps, ps_july_run_rate=v / a["run_rate_july_2026"],
                              ipo_rank=int((fitted_ps > ps).sum()) + 1, ipo_n=int(len(fitted_ps)),
                              times_largest_ipo=v / (ipos["value_at_offer_bn"].max() * 1e9),
                              growth_line_needs=(np.log(ps) - fit["intercept"]) / fit["slope"]))
    stats["anthropic"] = dict(run_rate_bn=run_rate / 1e9, growth=growth, max_peer_growth=float(peers["revenue_growth"].max()),
                              scenarios=scenarios, sources=a["sources"])

    basket, (race, race_target), (cisco_years, cisco), gdp = basket_table(), race_table(), cisco_table(), gdp_table()
    ipo_target = a["valuations"]["IPO target reported by the FT"] / 1e9
    series_h = a["valuations"]["Series H, May 2026"] / 1e9
    stats["comparisons"] = dict(
        basket=dict(n=len(basket), cap_bn=float(basket["market_cap_bn"].sum()), revenue_bn=float(basket["revenue_bn"].sum()),
                    net_income_bn=float(basket["net_income_bn"].sum()),
                    n_to_reach_series_h=int((basket["cumulative_cap_bn"] < series_h).sum()) + 1),
        race=dict(target_run_rate_bn=race_target / 1e9),
        cisco=cisco,
        gdp=dict(source="https://www.imf.org/external/datamapper/NGDPD@WEO", countries=int(len(gdp)),
                 **{f"rank_of_{int(v)}bn": int((gdp["gdp_2026_bn"] > v).sum()) + 1 for v in (series_h, ipo_target)},
                 **{f"countries_below_{int(v)}bn": int((gdp["gdp_2026_bn"] < v).sum()) for v in (series_h, ipo_target)}),
    )

    for d in (OUT_WEB, OUT_BI, OUT_PUBLIC):
        d.mkdir(parents=True, exist_ok=True)
    for name, df in dict(basket=basket, race=race, cisco=cisco_years, gdp=gdp).items():
        df.to_json(OUT_WEB / f"{name}.json", orient="records", indent=1)
        df.to_csv(OUT_BI / f"{name}.csv", index=False)
        df.round(4).to_csv(OUT_PUBLIC / f"{name}.csv", index=False)
    ipos.to_json(OUT_WEB / "ipos.json", orient="records", indent=1)
    peers.to_json(OUT_WEB / "peers.json", orient="records", indent=1)
    (OUT_WEB / "stats.json").write_text(json.dumps(stats, indent=1))
    ipos.to_csv(OUT_BI / "ipos.csv", index=False)
    peers.to_csv(OUT_BI / "peers.csv", index=False)
    public_ipo = ["ticker", "company", "ipo_date", "offer_price", "shares_after_ipo", "value_at_offer_bn",
                  "quarter_end", "run_rate_bn", "quarter_growth", "ps_run_rate", "first_close",
                  "ret_offer_1y", "ret_first_1y", "qqq_1y", "ret_offer_3y", "ret_first_3y", "qqq_3y", "prospectus"]
    ipos[public_ipo].round(4).to_csv(OUT_PUBLIC / "ipos.csv", index=False)
    peers.drop(columns=["log_ps"]).round(4).to_csv(OUT_PUBLIC / "peers.csv", index=False)

    pd.set_option("display.width", 250, "display.max_columns", 30)
    print(ipos[["ticker", "ipo_date", "value_at_offer_bn", "quarter_end", "run_rate_bn", "quarter_growth",
                "ps_run_rate", "first_day_pop", "excess_offer_3y", "excess_first_1y", "excess_first_3y"]].round(2).to_string())
    print(peers[["ticker", "market_cap_bn", "revenue_ttm_bn", "revenue_basis", "revenue_period_end", "revenue_growth",
                 "ps_ttm"]].round(2).to_string())
    for df in (basket, race, cisco_years, gdp.head(25)):
        print(df.round(2).to_string())
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
