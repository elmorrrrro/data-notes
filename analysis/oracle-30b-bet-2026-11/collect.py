"""Download everything the Oracle $30B-vs-$6B study needs into raw/ (git-ignored, third-party content stays local).

Output: raw/fy26_q4.htm, raw/fy27_q1.htm, raw/investor_day.htm   Oracle press releases (8-K Exhibit 99.1) from SEC EDGAR
        raw/*.txt              the same releases as plain text, for checking quoted figures
        raw/annual.csv         yearly revenue, operating cash flow and capital spending, fiscal 2023-2026 (Yahoo)
        raw/prices.csv         daily closes of Oracle (ORCL) since October 1, 2026 (Yahoo)
"""

import html
import re
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

HERE = Path(__file__).parent
RAW = HERE / "raw"

RELEASES = {
    # Q4 and full fiscal 2026 results, June 10, 2026
    "fy26_q4": "https://www.sec.gov/Archives/edgar/data/1341439/000119312526265848/orcl-ex99_1.htm",
    # Q1 fiscal 2027 results, September 10, 2026
    "fy27_q1": "https://www.sec.gov/Archives/edgar/data/1341439/000119312526387905/orcl-ex99_1.htm",
    # Investor Day, October 28, 2026
    "investor_day": "https://www.sec.gov/Archives/edgar/data/0001341439/000119312526435853/d75538dex991.htm",
}
# SEC asks automated tools to declare who they are: https://www.sec.gov/os/accessing-edgar-data
SEC_HEADERS = {"User-Agent": "DataNotes research@datanotes.org", "Accept-Encoding": "gzip, deflate"}

PRICES_FROM = "2026-10-01"
PRICES_TO = "2026-11-07"  # exclusive: last close is Fri 2026-11-06


def to_text(raw_html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw_html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def main():
    RAW.mkdir(exist_ok=True)
    for name, url in RELEASES.items():
        path = RAW / f"{name}.htm"
        if not path.exists():
            res = requests.get(url, headers=SEC_HEADERS, timeout=120)
            res.raise_for_status()
            path.write_bytes(res.content)
        (RAW / f"{name}.txt").write_text(to_text(path.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")

    t = yf.Ticker("ORCL")
    cf, inc = t.cashflow, t.income_stmt
    rows = []
    for col in cf.columns:
        ocf, capex = cf.at["Operating Cash Flow", col], cf.at["Capital Expenditure", col]
        rev = inc.at["Total Revenue", col] if col in inc.columns else float("nan")
        if pd.notna(ocf) and pd.notna(capex) and pd.notna(rev):
            rows.append({"fiscal_year_end": col.strftime("%Y-%m-%d"), "revenue": rev, "operating_cash_flow": ocf, "capex": -capex})
    pd.DataFrame(rows).sort_values("fiscal_year_end").to_csv(RAW / "annual.csv", index=False)

    hist = t.history(start=PRICES_FROM, end=PRICES_TO, auto_adjust=False)["Close"].dropna()
    hist.rename("close").to_csv(RAW / "prices.csv", index_label="date")
    print(f"releases: {len(RELEASES)}, years: {len(rows)}, closes: {len(hist)}")


if __name__ == "__main__":
    main()
