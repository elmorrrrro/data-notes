"""Download everything the SpaceX orbital-data-centers study needs into raw/ (git-ignored, third-party content stays local).

Output: raw/s1.htm      SpaceX's IPO prospectus (Form S-1, filed 2026-05-20, file no. 333-296070) from SEC EDGAR
        raw/s1.txt      the same prospectus as plain text, for quoting
        raw/prices.csv  daily closes of SpaceX (SPCX) and the Nasdaq-100 ETF (QQQ) since the IPO (Yahoo)
"""

import html
import re
from pathlib import Path

import requests
import yfinance as yf

HERE = Path(__file__).parent
RAW = HERE / "raw"

S1 = "https://www.sec.gov/Archives/edgar/data/1181412/000162828026036936/spaceexplorationtechnologi.htm"
# SEC asks automated tools to declare who they are: https://www.sec.gov/os/accessing-edgar-data
SEC_HEADERS = {"User-Agent": "DataNotes research@datanotes.org", "Accept-Encoding": "gzip, deflate"}

TICKERS = ["SPCX", "QQQ"]
PRICES_FROM = "2026-06-12"  # first trading day of SPCX (IPO priced June 11 at $135)
PRICES_TO = "2026-10-11"  # exclusive: last close is Fri 2026-10-09


def to_text(raw_html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw_html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def main():
    RAW.mkdir(exist_ok=True)
    s1 = RAW / "s1.htm"
    if not s1.exists():
        res = requests.get(S1, headers=SEC_HEADERS, timeout=120)
        res.raise_for_status()
        s1.write_bytes(res.content)
    (RAW / "s1.txt").write_text(to_text(s1.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")
    print("s1", s1.stat().st_size)

    closes = yf.download(TICKERS, start=PRICES_FROM, end=PRICES_TO, auto_adjust=False, progress=False)["Close"]
    closes.to_csv(RAW / "prices.csv")
    print("prices", closes.shape, closes.index.max().date())


if __name__ == "__main__":
    main()
