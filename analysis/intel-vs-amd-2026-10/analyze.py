"""Price/performance analysis: Intel vs AMD current desktop CPUs.

Input:  raw/cpus_collected.csv (from collect.py)
Output: src/data/intel-vs-amd-2026-10/cpus.json  -> the web page
        exports/cpus.csv                         -> Power BI
        public/data/intel-vs-amd-2026-10/cpus.csv -> download link on the page (no PassMark scores)
"""

import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
OUT_WEB = HERE.parents[1] / "src" / "data" / "intel-vs-amd-2026-10" / "cpus.json"
OUT_BI = HERE / "exports" / "cpus.csv"
OUT_PUBLIC = HERE.parents[1] / "public" / "data" / "intel-vs-amd-2026-10" / "cpus.csv"

# PassMark's terms only allow personal, non-commercial reproduction of their data, so the
# public download keeps prices, specs and a link to each PassMark page, but not the scores.
PASSMARK_COLUMNS = ["cpu_mark", "single_thread", "samples", "mark_per_dollar"]

MIN_SAMPLES = 50  # PassMark averages with fewer samples are too noisy
BUDGET_STEPS = range(150, 925, 5)


def exclusion_reason(r) -> str | None:
    if pd.isna(r.price_usd):
        return "No current US retail price"
    if r.price_stale:
        return "Price not refreshed recently (PassMark *)"
    if r.samples < MIN_SAMPLES:
        return f"Only {int(r.samples)} benchmark samples"
    return None


def main():
    df = pd.read_csv(HERE / "raw" / "cpus_collected.csv")
    df["short"] = df.cpu.str.replace(r"^(AMD Ryzen|Intel Core Ultra) ", "", regex=True)
    df["excluded"] = df.apply(exclusion_reason, axis=1)
    df["mark_per_dollar"] = (df.cpu_mark / df.price_usd).round(1)
    df["price_gap_vs_toms"] = (df.price_usd - df.toms_best_price_usd).round(2)

    ok = df[df.excluded.isna()].copy()
    ok["value_rank"] = ok.mark_per_dollar.rank(ascending=False).astype(int)

    by_brand = ok.groupby("brand").agg(
        models=("cpu", "count"),
        median_mark_per_dollar=("mark_per_dollar", "median"),
        best_mark_per_dollar=("mark_per_dollar", "max"),
        top_mark=("cpu_mark", "max"),
        cheapest=("price_usd", "min"),
    ).round(1)
    best = ok.loc[ok.groupby("brand").mark_per_dollar.idxmax(), ["brand", "short", "price_usd", "cpu_mark", "mark_per_dollar"]]

    # "Best you can buy for $X": the fastest chip of each brand priced at or under X.
    frontier = []
    for budget in BUDGET_STEPS:
        for brand, g in ok.groupby("brand"):
            fit = g[g.price_usd <= budget]
            if len(fit):
                top = fit.loc[fit.cpu_mark.idxmax()]
                frontier.append({"budget": budget, "brand": brand, "cpu_mark": top.cpu_mark, "cpu": top.short})

    print(ok.sort_values("mark_per_dollar", ascending=False)[["short", "price_usd", "cpu_mark", "mark_per_dollar"]].to_string(index=False))
    print("\n", by_brand, "\n\n", best.to_string(index=False))
    print("\nExcluded:\n", df[df.excluded.notna()][["cpu", "excluded"]].to_string(index=False))

    OUT_WEB.parent.mkdir(parents=True, exist_ok=True)
    OUT_BI.parent.mkdir(exist_ok=True)
    OUT_PUBLIC.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_BI, index=False)
    df.drop(columns=["short", *PASSMARK_COLUMNS]).to_csv(OUT_PUBLIC, index=False)
    payload = {
        "cpus": json.loads(ok.to_json(orient="records")),
        "excluded": json.loads(df[df.excluded.notna()][["cpu", "short", "brand", "excluded"]].to_json(orient="records")),
        "by_brand": json.loads(by_brand.reset_index().to_json(orient="records")),
        "best_value": json.loads(best.to_json(orient="records")),
        "frontier": frontier,
        "meta": {
            "price_retrieved": df.price_retrieved.iloc[0],
            "toms_updated": df.toms_updated.iloc[0],
            "min_samples": MIN_SAMPLES,
        },
    }
    OUT_WEB.write_text(json.dumps(payload, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
