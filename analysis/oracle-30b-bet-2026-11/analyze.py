"""Oracle's $30B free-cash-flow target for fiscal 2029 vs the $5.9B consensus: what has to be true for each.

Free cash flow (Oracle's definition) = operating cash flow - capital expenditures.
Fiscal years end May 31 (fiscal 2029 = June 2028 - May 2029).

Inputs: raw/annual.csv (from collect.py) and figures from Oracle's press releases; every figure taken from a release is
checked against that release's text in raw/*.txt.

Output: src/data/oracle-30b-bet-2026-11/{summary,history,capex,prepay}.json
        public/data/oracle-30b-bet-2026-11/oracle-cash-math.csv
"""

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
RAW = HERE / "raw"
ROOT = HERE.parents[1]
SLUG = "oracle-30b-bet-2026-11"
DATA = ROOT / "src" / "data" / SLUG
PUBLIC = ROOT / "public" / "data" / SLUG

# --- Figures from Oracle's releases ($ millions unless noted), each checked against the release text below ---
FY26_PREPAY = 4_592  # customer prepayments with significant financing component, inside FY26 operating cash flow
FY26_NET_CAPEX = 47_726  # "net cash outlay for capital expenditures", FY26
Q1 = {"revenue": 19_345, "ocf": 23_103, "prepay": 11_363, "capex": 28_499, "fcf": -5_396, "net_capex": 17_966}
CHECKS = {
    "fy26_q4": ["31,977", "4,592"],
    "fy27_q1": ["19,345", "23,103", "11,363", "28,499", "17,966", "47,726"],
    "investor_day": [
        "$225 billion or more in FY30",
        "free cash flow target of $30 billion+ for FY29",
        "positive free cash flow during the second half of FY28",
        "capital expenditures are expected to step-down in FY29",
        "Vendor financing, customer-provided hardware and customer prepayments are expected to reduce upfront cash requirements",
        "$10 billion in equity and $10 billion in gross debt",
    ],
}

# --- Targets and outside estimates ($ billions) ---
FY27_REVENUE = 90  # "at least $90 billion", reaffirmed at Investor Day
FY27_CAPEX = (90, 95)  # guidance on the Q1 FY27 call, Sep 10, 2026 (CNBC, erp.today)
FY27_NET_CAPEX_MAX = 70  # "not more than $70 billion net cash capex" (same call)
FY30_REVENUE = 225
TARGET = 30  # Oracle, FY29
CONSENSUS = 5.9  # TIKR consensus of 43 analysts before Investor Day (TIKR, Oct 29, 2026)


def check_quotes():
    for name, needles in CHECKS.items():
        text = (RAW / f"{name}.txt").read_text(encoding="utf-8")
        for n in needles:
            assert n in text, f"{n!r} not found in {name}"


def main():
    check_quotes()
    a = pd.read_csv(RAW / "annual.csv")
    a["fy"] = pd.to_datetime(a["fiscal_year_end"]).dt.year
    for c in ["revenue", "operating_cash_flow", "capex"]:
        a[c] = a[c] / 1e9
    a["fcf"] = a["operating_cash_flow"] - a["capex"]
    a["cash_share"] = a["operating_cash_flow"] / a["revenue"]
    a["capex_share"] = a["capex"] / a["revenue"]
    fy26 = a[a.fy == 2026].iloc[0]
    assert round(fy26.fcf, 1) == -23.7

    # Revenue path: Oracle's two anchors, FY27 at least $90B and FY30 at least $225B, joined at a constant growth rate.
    g = (FY30_REVENUE / FY27_REVENUE) ** (1 / 3)
    rev29 = FY27_REVENUE * g**2

    # Cash share of revenue (operating cash flow / revenue): two reference points from Oracle's own history.
    pre_ai = a[a.fy.isin([2023, 2024, 2025])]["cash_share"].mean()
    last = fy26.cash_share
    last_ex_prepay = (fy26.operating_cash_flow - FY26_PREPAY / 1000) / fy26.revenue
    cases = []
    for key, label, share in [
        ("pre_ai", "Cash share like fiscal 2023-2025", pre_ai),
        ("last", "Cash share like fiscal 2026", last),
    ]:
        ocf = rev29 * share
        cases.append({
            "key": key,
            "label": label,
            "cash_share": round(share, 3),
            "ocf": round(ocf, 1),
            "capex_for_target": round(ocf - TARGET, 1),
            "capex_for_consensus": round(ocf - CONSENSUS, 1),
        })
    lo, hi = cases[0], cases[1]
    capex27_mid = sum(FY27_CAPEX) / 2

    history = [
        {"fy": int(r.fy), "revenue": round(r.revenue, 1), "ocf": round(r.operating_cash_flow, 1), "capex": round(r.capex, 1), "fcf": round(r.fcf, 1)}
        for r in a.itertuples()
    ]
    capex_chart = [{"label": f"FY{h['fy'] % 100}", "kind": "actual", "lo": h["capex"], "hi": h["capex"]} for h in history] + [
        {"label": "FY27 plan", "kind": "plan", "lo": FY27_CAPEX[0], "hi": FY27_CAPEX[1]},
        {"label": "FY29 for $6B", "kind": "bonds", "lo": lo["capex_for_consensus"], "hi": hi["capex_for_consensus"]},
        {"label": "FY29 for $30B", "kind": "stocks", "lo": lo["capex_for_target"], "hi": hi["capex_for_target"]},
    ]
    prepay = [
        {"period": "Fiscal 2026", "reported": round(fy26.fcf, 1), "without": round(fy26.fcf - FY26_PREPAY / 1000, 1), "prepay": round(FY26_PREPAY / 1000, 1)},
        {"period": "Q1 fiscal 2027", "reported": round(Q1["fcf"] / 1000, 1), "without": round((Q1["fcf"] - Q1["prepay"]) / 1000, 1), "prepay": round(Q1["prepay"] / 1000, 1)},
    ]
    summary = {
        "target": TARGET,
        "consensus": CONSENSUS,
        "gap": round(TARGET - CONSENSUS, 1),
        "fy26": {"revenue": round(fy26.revenue, 1), "ocf": round(fy26.operating_cash_flow, 1), "capex": round(fy26.capex, 1), "fcf": round(fy26.fcf, 1),
                 "cash_share": round(last, 3), "cash_share_ex_prepay": round(last_ex_prepay, 3), "prepay": round(FY26_PREPAY / 1000, 1),
                 "net_capex": round(FY26_NET_CAPEX / 1000, 1)},
        "q1": {k: round(v / 1000, 1) for k, v in Q1.items()},
        "fy27": {"revenue": FY27_REVENUE, "capex_lo": FY27_CAPEX[0], "capex_hi": FY27_CAPEX[1], "capex_mid": capex27_mid,
                 "net_capex_max": FY27_NET_CAPEX_MAX, "capex_share": round(capex27_mid / FY27_REVENUE, 2)},
        "fy30_revenue": FY30_REVENUE,
        "growth": round(g - 1, 3),
        "rev28": round(FY27_REVENUE * g, 1),
        "rev29": round(rev29, 1),
        "cases": cases,
        "capex_cut_lo": round(1 - hi["capex_for_target"] / capex27_mid, 2),
        "capex_cut_hi": round(1 - lo["capex_for_target"] / capex27_mid, 2),
        "capex_share_needed": [round(lo["capex_for_target"] / rev29, 2), round(hi["capex_for_target"] / rev29, 2)],
        "fy24_capex_share": round(a[a.fy == 2024].iloc[0].capex_share, 2),
    }

    DATA.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    for name, obj in [("summary", summary), ("history", history), ("capex", capex_chart), ("prepay", prepay)]:
        (DATA / f"{name}.json").write_text(json.dumps(obj, indent=1), encoding="utf-8")

    rows = [{"item": f"FY{h['fy']} actual", "revenue_bn": h["revenue"], "operating_cash_flow_bn": h["ocf"], "capex_bn": h["capex"], "free_cash_flow_bn": h["fcf"]} for h in history]
    rows.append({"item": "FY2027 guidance", "revenue_bn": FY27_REVENUE, "capex_bn": f"{FY27_CAPEX[0]}-{FY27_CAPEX[1]}"})
    for c in cases:
        for name, fcf, capex in [("Oracle target", TARGET, c["capex_for_target"]), ("consensus", CONSENSUS, c["capex_for_consensus"])]:
            rows.append({"item": f"FY2029 {name}, {c['label'].lower()}", "revenue_bn": summary["rev29"], "operating_cash_flow_bn": c["ocf"],
                         "capex_bn": capex, "free_cash_flow_bn": fcf, "cash_share": c["cash_share"]})
    pd.DataFrame(rows).to_csv(PUBLIC / "oracle-cash-math.csv", index=False)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
