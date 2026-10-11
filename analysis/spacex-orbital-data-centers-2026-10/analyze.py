"""Turn the SpaceX prospectus and Musk's past deadlines into the numbers behind the orbital-data-centers post.

Inputs:  raw/s1.txt, raw/prices.csv (from collect.py)
Outputs: src/data/spacex-orbital-data-centers-2026-10/summary.json   headline numbers (all checked against the S-1 text)
         src/data/spacex-orbital-data-centers-2026-10/promises.json  Musk's dated promises vs what happened
         src/data/spacex-orbital-data-centers-2026-10/lift.json      tonnes to orbit: 2012, 2025, the plan's yearly need
         exports/promises.csv, exports/spcx.csv                      for Power BI (git-ignored)
         public/data/spacex-orbital-data-centers-2026-10/musk-promises.csv   public download
"""

import csv
import json
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
SLUG = "spacex-orbital-data-centers-2026-10"
DATA = ROOT / "src" / "data" / SLUG
PUBLIC = ROOT / "public" / "data" / SLUG
EXPORTS = HERE / "exports"
TODAY = date(2026, 10, 11)

# Every number below is quoted from the S-1; `check` fails loudly if the wording is not in the filing.
S1_FACTS = {
    "first_deploy": ("as early as 2028", "We expect to begin deploying our orbital AI compute satellites as early as 2028."),
    "goal_gw_per_year": (100, "Deployment of 100 gigawatts per year via satellites carrying over 100 kilowatts of compute power per metric ton"),
    "tonnes_per_year": (1_000_000, "the transport of approximately one million metric tons to orbit annually"),
    "world_tonnes_2012": (220, "approximately 220 metric tons of payload launched to orbit in 2012"),
    "world_tonnes_2025": (2_600, "increasing to approximately 2,600 metric tons in 2025"),
    "spacex_share_2025": (0.8, "of which over 80% was launched b y SpaceX"),
    "starship_tonnes": (100, "Starship V3 is designed to deliver 100 metric tons to Earth’s orbit"),
    "falcon9_launches_2025": (165, "in 2025, we launched 165 Falcon 9 rockets"),
    "ai_revenue_2025_musd": (3_201, "In 2025 , our AI segment generated revenue of $3,201 million"),
    "ai_op_loss_2025_musd": (6_355, "loss from operations of $(6,355) million"),
    "ai_capex_2025_musd": (12_727, "for our AI segment was $12,727 million"),
    "earth_compute_gw_q1_2026": (1, "Nameplate compute draw (in gigawatts) (1) .................................... 1 0.3 0.8 0.3 0"),
}
S1_QUOTES = {
    "viability": "involve significant technical complexity, unproven technologies or technologies that do not exist, "
                 "and such initiatives may not achieve commercial viability",
    "timeline": "the timeline for certain of our initiatives involving unproven or new innovations, including our goal of "
                "deploying 100 gigawatts of 12 Table of Contents annual compute power to orbit",
    "impossible": "may be difficult or impossible to determine",
    "untested": "we have not, and no one else has, previously operated or attempted to operate orbital AI compute",
}

# Musk's dated promises. `due` is the last day of the promised period; `done` is when it happened (None = not yet).
# status: on_time | late | not_yet | dropped
PROMISES = [
    dict(id="selfdrive", what="A Tesla drives itself from Los Angeles to New York", said="2016-10-19", due="2017-12-31",
         done="2025-12-31", status="late",
         outcome="December 2025: an owner crossed the US on FSD (Supervised) with no interventions; still a driver-assist system",
         src="https://en.wikipedia.org/wiki/List_of_predictions_for_autonomous_Tesla_vehicles_by_Elon_Musk",
         src2="https://www.notateslaapp.com/news/3862/tesla-highlights-2700-mile-fsd-trip-with-zero-interventions"),
    dict(id="reddragon", what="Red Dragon lands on Mars", said="2016-04-27", due="2018-12-31", done="2017-07-19",
         status="dropped", outcome="Cancelled in July 2017 before it flew",
         src="https://www.space.com/37563-spacex-drops-plans-for-powered-dragon-landings.html", src2=""),
    dict(id="semi", what="Tesla Semi in production", said="2017-11-16", due="2019-12-31", done="2022-12-01",
         status="late", outcome="First trucks delivered to PepsiCo on December 1, 2022",
         src="https://www.freightwaves.com/news/musk-1st-tesla-semi-trucks-going-to-pepsi-in-december", src2=""),
    dict(id="roadster", what="New Tesla Roadster on sale", said="2017-11-16", due="2020-12-31", done=None,
         status="not_yet", outcome="Not on sale; the reveal moved again, to October 15, 2026",
         src="https://electrek.co/2026/04/22/tesla-roadster-unveil-delayed-again-earnings-call/", src2=""),
    dict(id="marscargo", what="First Starship cargo flights to Mars", said="2017-09-29", due="2022-12-31", done="2026-02-09",
         status="dropped", outcome="Never flew; in February 2026 SpaceX put Mars off by 5 to 7 years to focus on the Moon",
         src="https://engadget.com/2017/09/29/spacex-mars-bfr",
         src2="https://phys.org/news/2026-02-spacex-shifts-focus-mars-moon.html"),
    dict(id="marscrew", what="First crew flies to Mars", said="2017-09-29", due="2024-12-31", done=None,
         status="not_yet", outcome="Not yet; Mars is now behind the Moon in SpaceX's plans",
         src="https://engadget.com/2017/09/29/spacex-mars-bfr",
         src2="https://phys.org/news/2026-02-spacex-shifts-focus-mars-moon.html"),
    dict(id="robotaxi", what="A million Tesla robotaxis on the road", said="2019-04-22", due="2020-12-31", done=None,
         status="not_yet", outcome="About 300 run without a safety driver in 2026 (independent tracker)",
         src="https://www.thedrive.com/tech/27605/tesla-network-promises-one-million-robotaxis-on-the-road-by-2020",
         src2="https://eletric-vehicles.com/tesla/tesla-robotaxi-fleet-tops-1000-vehicles-tracking-site-shows/"),
    dict(id="starship", what="Starship reaches orbit", said="2022-02-10", due="2022-12-31", done="2026-09-28",
         status="late", outcome="First orbit and first real payload (26 Starlink satellites) on September 28, 2026",
         src="https://www.cbsnews.com/amp/news/elon-musk-spacex-first-orbital-starship-flight/",
         src2="https://www.cnn.com/2026/09/28/science/live-news/spacex-starship-flight-14-launch"),
    dict(id="payload", what="Starship delivers payload to orbit (prospectus)", said="2026-05-20", due="2026-12-31",
         done="2026-09-28", status="on_time", outcome="Done on September 28, 2026: on time",
         src="https://www.sec.gov/Archives/edgar/data/1181412/000162828026036936/spaceexplorationtechnologi.htm",
         src2="https://www.cnn.com/2026/09/28/science/live-news/spacex-starship-flight-14-launch"),
]


def check(text: str):
    for key, (_, phrase) in S1_FACTS.items():
        assert phrase in text, f"S-1 phrase not found for {key}: {phrase!r}"
    for key, phrase in S1_QUOTES.items():
        assert phrase in text, f"S-1 quote not found for {key}: {phrase!r}"


def years(a: str, b: date | str) -> float:
    b = date.fromisoformat(b) if isinstance(b, str) else b
    return round((b - date.fromisoformat(a)).days / 365.25, 1)


def main():
    text = (HERE / "raw" / "s1.txt").read_text(encoding="utf-8")
    check(text)
    f = {k: v for k, (v, _) in S1_FACTS.items()}

    for p in PROMISES:
        # Years past the deadline: when it happened, or until today if it has not (a lower bound).
        p["late_years"] = 0.0 if p["status"] == "on_time" else years(p["due"], p["done"] if p["status"] == "late" else TODAY)
        if p["status"] == "dropped":
            p["late_years"] = None
    delivered = [p for p in PROMISES if p["status"] in ("on_time", "late")]
    late = [p["late_years"] for p in PROMISES if p["status"] == "late"]

    flights_per_year = f["tonnes_per_year"] / f["starship_tonnes"]
    prices = pd.read_csv(HERE / "raw" / "prices.csv", index_col=0, parse_dates=True)
    spcx = prices["SPCX"].dropna()
    summary = {
        "s1_url": PROMISES[-1]["src"],
        "s1_filed": "2026-05-20",
        **f,
        "times_2025_world": round(f["tonnes_per_year"] / f["world_tonnes_2025"]),
        "starship_flights_per_year": round(flights_per_year),
        "starship_flights_per_day": round(flights_per_year / 365),
        "minutes_between_launches": round(365 * 24 * 60 / flights_per_year),
        "promises": len(PROMISES),
        "delivered": len(delivered),
        "on_time": sum(p["status"] == "on_time" for p in PROMISES),
        "late_min_years": min(late),
        "late_max_years": max(late),
        # The two hardware programmes that shipped late (Semi, Starship to orbit) slipped about 3 to 4 years.
        "hardware_slip_years": [p["late_years"] for p in PROMISES if p["id"] in ("semi", "starship")],
        "spcx": {
            "ipo_price": 135.0,
            "first_close": round(float(spcx.iloc[0]), 2),
            "high_close": round(float(spcx.max()), 2),
            "low_close": round(float(spcx.min()), 2),
            "last_close": round(float(spcx.iloc[-1]), 2),
            "last_date": spcx.index[-1].strftime("%Y-%m-%d"),
        },
    }
    slip = summary["hardware_slip_years"]
    summary["musk_clock_first_deploy"] = [2028 + round(min(slip)), 2028 + round(max(slip))]

    lift = [
        {"label": "Whole world, 2012", "tonnes": f["world_tonnes_2012"], "kind": "past"},
        {"label": "Whole world, 2025", "tonnes": f["world_tonnes_2025"], "kind": "past"},
        {"label": "The plan, every year", "tonnes": f["tonnes_per_year"], "kind": "plan"},
    ]

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    (DATA / "promises.json").write_text(json.dumps(PROMISES, indent=1, ensure_ascii=False), encoding="utf-8")
    (DATA / "lift.json").write_text(json.dumps(lift, indent=1), encoding="utf-8")

    cols = ["what", "said", "due", "status", "done", "late_years", "outcome", "src", "src2"]
    for path in (EXPORTS / "promises.csv", PUBLIC / "musk-promises.csv"):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(PROMISES)
    prices.to_csv(EXPORTS / "spcx.csv")

    print(json.dumps(summary, indent=1))
    for p in PROMISES:
        print(f"{p['status']:8} {str(p['late_years']):5} {p['what']}")


if __name__ == "__main__":
    main()
