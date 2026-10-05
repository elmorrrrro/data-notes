"""Download Swarmer's SEC filings data, peer financials, share prices, the Russian strike log and the talks timelines.

Output: raw/company_tickers.json   SEC ticker -> CIK map
        raw/facts/<TICKER>.json    XBRL company facts (revenue, net loss, cash, shares) from SEC EDGAR
        raw/subs/<TICKER>.json     filing index (IPO prospectus, 10-Q, 8-K dates)
        raw/swmr/*.htm             Swarmer's 424B4 prospectus, latest 10-Q and the 8-Ks quoted in the post
        raw/prices/<TICKER>.csv    daily close (Yahoo Finance via yfinance)
        raw/peers_info.json        market cap and share count (Yahoo Finance)
        raw/mma.zip                "Massive Missile Attacks on Ukraine" (Kaggle, piterfm, CC BY-NC-SA 4.0): launches per attack
        raw/wiki/*.txt             Wikipedia plain-text extracts of the talks timelines (a pointer to primary sources)
"""

import json
import time
import zipfile
from pathlib import Path

import requests
import yfinance as yf

HERE = Path(__file__).parent
RAW = HERE / "raw"

# SEC asks automated clients to identify themselves and stay under 10 requests a second.
SEC_HEADERS = {"User-Agent": "Data Notes research contact@datanotes.org"}
PRICES_FROM = "2015-01-01"
PRICES_TO = "2026-10-06"  # exclusive: last close is Mon 2026-10-05

TARGET = "SWMR"
# Listed drone and defense-tech names (price of expectations), plus young listed hardware companies whose
# revenue was also tiny at listing (early revenue is supposed to be small).
PEERS = ["AVAV", "KTOS", "PLTR", "RCAT", "ONDS"]
EARLY = ["JOBY", "ACHR", "RKLB"]
SWMR_CIK = 2092574

KAGGLE_ZIP = "https://www.kaggle.com/api/v1/datasets/download/piterfm/massive-missile-attacks-on-ukraine"
WIKI_PAGES = {
    "russia_ukraine_talks": "Peace negotiations in the Russo-Ukrainian war (2022–present)",
    "iran_us_talks": "2025–2026 Iran–United States negotiations",
}


def get(url, path, headers=SEC_HEADERS, params=None):
    if path.exists():
        return path.read_bytes()
    for attempt in range(3):
        try:
            res = requests.get(url, headers=headers, params=params, timeout=120)
            res.raise_for_status()
            break
        except requests.RequestException as err:
            print(f"{path.name}: attempt {attempt + 1} failed ({err})")
            time.sleep(2)
    else:
        raise SystemExit(f"could not download {url}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(res.content)
    time.sleep(0.15)
    return res.content


def sec_company(ticker, cik):
    get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", RAW / "facts" / f"{ticker}.json")
    return json.loads(get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", RAW / "subs" / f"{ticker}.json"))


def swmr_documents(subs):
    """The prospectus, the latest 10-Q and every 8-K since listing."""
    recent = subs["filings"]["recent"]
    latest_10q = None
    for form, acc, doc, date in zip(recent["form"], recent["accessionNumber"], recent["primaryDocument"], recent["filingDate"]):
        keep = form in ("424B4", "8-K") or (form == "10-Q" and latest_10q is None)
        if form == "10-Q" and latest_10q is None:
            latest_10q = acc
        if not keep:
            continue
        url = f"https://www.sec.gov/Archives/edgar/data/{SWMR_CIK}/{acc.replace('-', '')}/{doc}"
        get(url, RAW / "swmr" / f"{date}_{form}_{doc}")


def main():
    tickers = json.loads(get("https://www.sec.gov/files/company_tickers.json", RAW / "company_tickers.json"))
    ciks = {row["ticker"]: int(row["cik_str"]) for row in tickers.values()}
    ciks.setdefault(TARGET, SWMR_CIK)

    swmr_documents(sec_company(TARGET, ciks[TARGET]))
    for t in PEERS + EARLY:
        sec_company(t, ciks[t])

    (RAW / "prices").mkdir(parents=True, exist_ok=True)
    info = {}
    for t in [TARGET] + PEERS + EARLY:
        path = RAW / "prices" / f"{t}.csv"
        if not path.exists():
            yf.Ticker(t).history(start=PRICES_FROM, end=PRICES_TO, auto_adjust=False)[["Close", "Adj Close"]].to_csv(path)
        i = yf.Ticker(t).info
        info[t] = {k: i.get(k) for k in ("marketCap", "sharesOutstanding", "totalRevenue", "longName")}
    (RAW / "peers_info.json").write_text(json.dumps(info, indent=1))

    zip_path = RAW / "mma.zip"
    get(KAGGLE_ZIP, zip_path, headers={"User-Agent": "Mozilla/5.0"})
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(RAW / "mma")

    for key, title in WIKI_PAGES.items():
        params = {"action": "query", "prop": "extracts", "explaintext": 1, "titles": title, "format": "json", "formatversion": 2}
        data = json.loads(get("https://en.wikipedia.org/w/api.php", RAW / "wiki" / f"{key}.json", {"User-Agent": SEC_HEADERS["User-Agent"]}, params))
        (RAW / "wiki" / f"{key}.txt").write_text(data["query"]["pages"][0]["extract"], encoding="utf-8")


if __name__ == "__main__":
    main()
