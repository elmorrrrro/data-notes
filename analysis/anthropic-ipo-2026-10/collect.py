"""Download SEC filings data and daily prices for the IPO sample and the listed peers.

Output: raw/company_tickers.json   SEC ticker -> CIK map
        raw/facts/<TICKER>.json    XBRL company facts (revenue, shares outstanding) from SEC EDGAR
        raw/subs/<TICKER>.json     filing index, used to find each IPO's final prospectus
        raw/424b4/<TICKER>.htm     final prospectus (Form 424B4) with the offer price
        raw/prices/<TICKER>.csv    daily close, adjusted close and splits (Yahoo Finance via yfinance)
        raw/peers_info.json, raw/basket_info.json   share counts of all classes (Yahoo Finance)
        raw/cisco/*.txt|htm        Cisco's 10-Q for the quarter of its March 2000 peak, its 2000 10-K and the annual reports whose
                                   five-year tables give its revenue before XBRL (fiscal 1996-2009)
        raw/facts/GOOG-INC.json    Google Inc.'s XBRL facts (2009-2015, before Alphabet)
        raw/founding/*             Amazon's and Google's IPO prospectuses (year of incorporation)
        raw/imf_gdp.json, raw/imf_countries.json    IMF World Economic Outlook, GDP in current US dollars
"""

import json
import time
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

from universe import BASKET, BENCHMARK, CISCO, IPOS, PEERS

HERE = Path(__file__).parent
RAW = HERE / "raw"

# SEC asks automated clients to identify themselves and stay under 10 requests a second.
SEC_HEADERS = {"User-Agent": "Data Notes research contact@datanotes.org"}
PRICES_FROM = "2011-01-01"
PRICES_TO = "2026-10-03"  # exclusive: last close is Fri 2026-10-02


def get(url, path):
    if path.exists():
        return path.read_bytes()
    for attempt in range(3):
        try:
            res = requests.get(url, headers=SEC_HEADERS, timeout=90)
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


def all_filings(ticker, cik, subs):
    """The submissions file lists the latest 1,000 filings; older ones sit in extra pages."""
    rows = [subs["filings"]["recent"]]
    for i, page in enumerate(subs["filings"].get("files", [])):
        url = f"https://data.sec.gov/submissions/{page['name']}"
        rows.append(json.loads(get(url, RAW / "subs" / f"{ticker}-{i + 1}.json")))
    out = pd.concat([pd.DataFrame(r) for r in rows], ignore_index=True)
    out["cik"] = cik
    return out


CISCO_FILINGS = {
    "10q_2000-01.txt": "https://www.sec.gov/Archives/edgar/data/858877/0000891618-00-001422.txt",
    "10k_2000.txt": "https://www.sec.gov/Archives/edgar/data/858877/000109581100003692/f65797e10-k.txt",
    "ar_2004.htm": "https://www.sec.gov/Archives/edgar/data/858877/000119312504158427/dex131.htm",
    "ar_2009.htm": "https://www.sec.gov/Archives/edgar/data/858877/000119312509190326/dex131.htm",
}

# For "speed": Google's revenue before 2015 sits under Google Inc. (Alphabet has a new CIK), and each company's
# first prospectus states when it was incorporated.
GOOGLE_INC_CIK = 1288776
FIRST_PROSPECTUS = {
    "AMZN": "https://www.sec.gov/Archives/edgar/data/1018724/0000891020-97-000868.txt",
    "GOOGL": "https://www.sec.gov/Archives/edgar/data/1288776/000119312504143377/d424b4.htm",
}


def quote_info(tickers, path):
    """Share counts move daily; keep the first download so reruns give the same numbers."""
    if path.exists():
        return
    info = {}
    for t in tickers:
        q = yf.Ticker(t).info
        info[t] = {k: q.get(k) for k in ["marketCap", "regularMarketPrice", "sharesOutstanding",
                                         "impliedSharesOutstanding", "longName", "industry"]}
    path.write_text(json.dumps({"retrieved": pd.Timestamp.now().isoformat(), "quotes": info}, indent=1))
    print(path.name, len(info))


def main():
    tickers_map = json.loads(get("https://www.sec.gov/files/company_tickers.json", RAW / "company_tickers.json"))
    cik_of = {row["ticker"].replace("-", "."): row["cik_str"] for row in tickers_map.values()}

    ipo_dates = {t: d for t, _, d, _ in IPOS}
    for t in sorted(set(ipo_dates) | set(PEERS) | set(BASKET) | {CISCO}):
        cik = cik_of[t]
        get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", RAW / "facts" / f"{t}.json")
        if t not in ipo_dates:
            continue
        subs = json.loads(get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", RAW / "subs" / f"{t}.json"))
        filings = all_filings(t, cik, subs)
        filings["filingDate"] = pd.to_datetime(filings["filingDate"])
        day = pd.Timestamp(ipo_dates[t])
        near = filings[(filings["form"] == "424B4") & (filings["filingDate"].between(day - pd.Timedelta(days=5),
                                                                                       day + pd.Timedelta(days=10)))]
        if near.empty:
            print(f"{t}: no 424B4 near {day.date()}")
            continue
        f = near.sort_values("filingDate").iloc[0]
        acc = f["accessionNumber"].replace("-", "")
        get(f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{f['primaryDocument']}", RAW / "424b4" / f"{t}.htm")
        print(f"{t}: 424B4 filed {f['filingDate'].date()}")

    (RAW / "prices").mkdir(parents=True, exist_ok=True)
    for t in sorted(set(ipo_dates) | set(PEERS) | set(BASKET) | {BENCHMARK, CISCO}):
        if (RAW / "prices" / f"{t}.csv").exists():
            continue
        start = {CISCO: "1990-01-01", BENCHMARK: "1999-03-10"}.get(t, PRICES_FROM)  # Cisco and QQQ: back to before the 2000 peak
        h = yf.Ticker(t).history(start=start, end=PRICES_TO, auto_adjust=False, actions=True)
        h.index = h.index.strftime("%Y-%m-%d")
        h[["Close", "Adj Close", "Stock Splits"]].to_csv(RAW / "prices" / f"{t}.csv", index_label="date")
        print(f"{t}: {len(h)} days from {h.index[0]}")

    # Share counts across all classes (Alphabet, Meta and others have several), from Yahoo's quote data.
    # analyze.py turns them into a market value at the last close before publication.
    quote_info(PEERS, RAW / "peers_info.json")
    quote_info(BASKET, RAW / "basket_info.json")

    for name, url in CISCO_FILINGS.items():
        get(url, RAW / "cisco" / name)

    get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{GOOGLE_INC_CIK:010d}.json", RAW / "facts" / "GOOG-INC.json")
    for t, url in FIRST_PROSPECTUS.items():
        get(url, RAW / "founding" / f"{t}{Path(url).suffix}")

    get("https://www.imf.org/external/datamapper/api/v1/NGDPD", RAW / "imf_gdp.json")
    get("https://www.imf.org/external/datamapper/api/v1/countries", RAW / "imf_countries.json")


if __name__ == "__main__":
    main()
