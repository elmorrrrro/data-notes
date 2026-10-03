"""Collect CPU benchmark scores and US retail prices for the Intel vs AMD study.

Sources
- PassMark CPU Mark (multi-thread) + listed US price: cpubenchmark.net
- Tom's Hardware CPU Price Index (weekly "best US price"), used as a cross-check

Every run saves the raw HTML into raw/ so numbers can be re-derived later,
then writes raw/cpus_collected.csv.
"""

import csv
import html
import re
import time
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
RAW = HERE / "raw"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36"

# Current desktop generations: AMD Zen 5 (AM5) vs Intel Arrow Lake / Arrow Lake Refresh (LGA1851).
# Value = PassMark CPU id (name search alone resolves to the wrong SKU, e.g. 9950X -> 9950X3D2).
CPUS = {
    "AMD Ryzen 9 9950X3D2": 7115,
    "AMD Ryzen 9 9950X3D": 6549,
    "AMD Ryzen 9 9950X": 6211,
    "AMD Ryzen 9 9900X3D": 6548,
    "AMD Ryzen 9 9900X": 6171,
    "AMD Ryzen 7 9850X3D": 7074,
    "AMD Ryzen 7 9800X3D": 6344,
    "AMD Ryzen 7 9700X": 6205,
    "AMD Ryzen 5 9600X": 6199,
    "AMD Ryzen 5 9600": 6590,
    "Intel Core Ultra 9 290K Plus": 7210,
    "Intel Core Ultra 9 285K": 6296,
    "Intel Core Ultra 7 270K Plus": 7114,
    "Intel Core Ultra 7 265K": 6326,
    "Intel Core Ultra 7 265KF": 6338,
    "Intel Core Ultra 5 250K Plus": 7221,
    "Intel Core Ultra 5 245K": 6324,
    "Intel Core Ultra 5 245KF": 6336,
    "Intel Core Ultra 5 225": 6469,
}

PASSMARK_LISTS = ["high_end_cpus.html", "mid_range_cpus.html", "desktop.html"]
TOMS_URL = "https://www.tomshardware.com/news/lowest-cpu-prices"


def fetch(url: str, cache: Path) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    text = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    cache.write_text(text, encoding="utf-8")
    return text


def to_text(s: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()


def num(s: str | None) -> float | None:
    return float(s.replace(",", "").replace("$", "")) if s else None


def passmark_list_prices() -> dict[str, tuple[float | None, bool]]:
    """name -> (price, stale). PassMark marks prices it hasn't refreshed recently with '*'."""
    prices = {}
    for page in PASSMARK_LISTS:
        s = fetch(f"https://www.cpubenchmark.net/{page}", RAW / f"passmark_{page}")
        for m in re.finditer(r'<span class="prdname">([^<]+)</span>.*?<span class="price-neww">([^<]+)</span>', s, re.S):
            name, price = m.group(1).strip(), m.group(2).strip()
            prices[name] = (None, False) if price == "NA" else (num(price.rstrip("*")), price.endswith("*"))
        time.sleep(1)
    return prices


def passmark_detail(name: str, cpu_id: int) -> dict:
    url = f"https://www.cpubenchmark.net/cpu.php?cpu={name.replace(' ', '+')}&id={cpu_id}"
    t = to_text(fetch(url, RAW / f"passmark_{cpu_id}.html"))

    def g(p):
        m = re.search(p, t)
        return m.group(1) if m else None

    return {
        "cpu_mark": num(g(r"Multithread Rating:?\s*([\d,]+)")),
        "single_thread": num(g(r"Single Thread Rating:?\s*([\d,]+)")),
        "cores": num(g(r"Cores:\s*(\d+)")),
        "threads": num(g(r"Threads:\s*(\d+)")),
        "tdp_w": num(g(r"Typical TDP:\s*([\d.]+)\s*W")),
        "first_seen": g(r"First Seen on Charts:\s*(Q\d \d{4})"),
        "samples": num(g(r"Samples:\s*([\d,]+)")),
        "passmark_url": url,
    }


def toms_prices() -> tuple[dict[str, float | None], str | None]:
    s = fetch(TOMS_URL, RAW / "toms_price_index.html")
    updated = re.search(r'"dateModified"\s*:\s*"([^"]+)"', s)
    prices = {}
    for table in re.findall(r"<table.*?</table>", s, re.S):
        for row in re.findall(r"<tr.*?</tr>", table, re.S):
            cells = [to_text(c) for c in re.findall(r"<t[hd].*?</t[hd]>", row, re.S)]
            if len(cells) >= 2 and cells[1].startswith(("$", "Out")):
                # Tom's drops "Ultra" in Core Ultra names ("Intel Core 9 285K").
                name = re.sub(r"^Intel Core (\d) ", r"Intel Core Ultra \1 ", cells[0])
                prices[name] = num(cells[1]) if cells[1].startswith("$") else None
    return prices, updated.group(1)[:10] if updated else None


def main():
    RAW.mkdir(exist_ok=True)
    today = date.today().isoformat()
    pm_prices = passmark_list_prices()
    toms, toms_updated = toms_prices()

    rows = []
    for name, cpu_id in CPUS.items():
        d = passmark_detail(name, cpu_id)
        price, stale = pm_prices.get(name, (None, False))
        rows.append({
            "cpu": name,
            "brand": name.split()[0],
            **d,
            "threads": d["threads"] or d["cores"],  # Arrow Lake has no Hyper-Threading
            "price_usd": price,
            "price_stale": stale,
            "price_source": "PassMark listed US price",
            "price_retrieved": today,
            "toms_best_price_usd": toms.get(name),
            "toms_updated": toms_updated,
        })
        print(f"{name:32} mark={d['cpu_mark']:>8} price={price} toms={toms.get(name)}")
        time.sleep(1)

    with open(RAW / "cpus_collected.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
