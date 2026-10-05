"""The two samples used by collect.py and analyze.py.

IPOS: large US-listed tech IPOs (a priced offering, not a direct listing or a SPAC) from 2011 on, so that the
filings carry XBRL data. Offer prices are checked against each final prospectus (Form 424B4) in analyze.py.
Companies later taken private or acquired (LinkedIn, Twitter, Zynga, Qualtrics) have no price history on Yahoo
and are left out; analyze.py lists them so the survivorship bias is visible.

PEERS: listed US tech companies that file 10-Ks with the SEC, from mega caps to fast-growing mid caps, for the
growth vs. valuation chart.
"""

# ticker on Yahoo today, name, first trading day, offer price in USD as stated in the 424B4
IPOS = [
    ("GRPN", "Groupon", "2011-11-04", 20.00),
    ("META", "Facebook (Meta)", "2012-05-18", 38.00),
    ("WDAY", "Workday", "2012-10-12", 28.00),
    ("BABA", "Alibaba", "2014-09-19", 68.00),
    ("XYZ", "Square (Block)", "2015-11-19", 9.00),
    ("SNAP", "Snap", "2017-03-02", 17.00),
    ("DBX", "Dropbox", "2018-03-23", 21.00),
    ("LYFT", "Lyft", "2019-03-29", 72.00),
    ("PINS", "Pinterest", "2019-04-18", 19.00),
    ("ZM", "Zoom", "2019-04-18", 36.00),
    ("UBER", "Uber", "2019-05-10", 45.00),
    ("CRWD", "CrowdStrike", "2019-06-12", 34.00),
    ("DDOG", "Datadog", "2019-09-19", 27.00),
    ("PTON", "Peloton", "2019-09-26", 29.00),
    ("SNOW", "Snowflake", "2020-09-16", 120.00),
    ("U", "Unity", "2020-09-18", 52.00),
    ("DASH", "DoorDash", "2020-12-09", 102.00),
    ("ABNB", "Airbnb", "2020-12-10", 68.00),
    ("AFRM", "Affirm", "2021-01-13", 49.00),
    ("BMBL", "Bumble", "2021-02-11", 43.00),
    ("CPNG", "Coupang", "2021-03-11", 35.00),
    ("PATH", "UiPath", "2021-04-21", 56.00),
    ("S", "SentinelOne", "2021-06-30", 35.00),
    ("HOOD", "Robinhood", "2021-07-29", 38.00),
    ("TOST", "Toast", "2021-09-22", 40.00),
    ("GTLB", "GitLab", "2021-10-14", 77.00),
    ("RIVN", "Rivian", "2021-11-10", 78.00),
    ("MBLY", "Mobileye", "2022-10-26", 21.00),
    ("ARM", "Arm", "2023-09-14", 51.00),
    ("CART", "Instacart (Maplebear)", "2023-09-19", 30.00),
    ("ALAB", "Astera Labs", "2024-03-20", 36.00),
    ("RDDT", "Reddit", "2024-03-21", 34.00),
    ("CRWV", "CoreWeave", "2025-03-28", 40.00),
]

# Large tech IPOs left out because the company no longer trades (no price history to measure returns).
GONE = ["LinkedIn (2011, bought by Microsoft 2016)", "Zynga (2011, bought by Take-Two 2022)",
        "Twitter (2013, taken private 2022)", "Qualtrics (2021, taken private 2023)",
        "Confluent (2021, bought by IBM 2026)"]

PEERS = [
    "NVDA", "MSFT", "AAPL", "GOOGL", "AMZN", "META", "AVGO", "TSLA", "ORCL", "NFLX",
    "PLTR", "AMD", "CRM", "NOW", "ADBE", "INTU", "IBM", "QCOM", "MU", "INTC",
    "ANET", "PANW", "CRWD", "SNPS", "CDNS", "APP", "UBER", "ABNB", "DELL", "SMCI",
    "SNOW", "DDOG", "NET", "MDB", "ZS", "HUBS", "TEAM", "CRWV", "RDDT", "ALAB",
]

BENCHMARK = "QQQ"  # Nasdaq-100 ETF, total return via Yahoo's adjusted close

# ---------------------------------------------------------------- the four comparisons

# "Same price": household-name US companies (10-K filers), stacked in this order until they add up to the
# valuation Anthropic is reported to seek.
BASKET = ["KO", "PEP", "MCD", "SBUX", "NKE", "DIS", "NFLX", "BA", "F", "GM", "COST"]

# "Speed": month of incorporation, as stated in each company's IPO prospectus (checked in analyze.py).
# facts: which XBRL file holds the quarters around the crossing (Google's before 2015 sit under Google Inc.).
FOUNDED = {
    "AMZN": dict(name="Amazon", month="1994-07", facts="AMZN", quote="The Company was incorporated in Washington in July 1994"),
    "GOOGL": dict(name="Google", month="1998-09", facts="GOOG-INC", quote="We were incorporated in California in September 1998"),
    "META": dict(name="Facebook", month="2004-07", facts="META", quote="We were incorporated in Delaware in July 2004"),
}
ANTHROPIC_FOUNDED = "2021-01"  # founded in 2021; counting from January is the least flattering choice for Anthropic

# "The Cisco lesson": the most valuable company in the world at the peak of the dot-com bubble.
CISCO = "CSCO"
