# Data Notes

Data studies, one post per folder, organised by tags. Astro 7 + MDX + Observable Plot, deployed to Cloudflare.

## Run locally

```sh
npm install
npm run dev          # http://localhost:4321
```

## How a study is built

```
analysis/<slug>/          Python: collect -> analyze -> JSON/CSV
  collect.py              scrapes sources, saves raw HTML to raw/
  analyze.py              writes src/data/<slug>/*.json, exports/*.csv (Power BI), public/data/<slug>/*.csv
src/data/<slug>/          data the charts import
src/content/posts/<slug>/index.mdx   the article (frontmatter: title, description, date, tags)
src/components/charts/    chart components (Observable Plot, theme-aware)
src/pages/api/quote.ts    live stock quotes (server function, Yahoo Finance)
```

Intel vs AMD (2026-10):

```sh
cd analysis/intel-vs-amd-2026-10
python collect.py          # re-scrape PassMark + Tom's Hardware
python analyze.py          # recompute metrics and export
python snapshot_stocks.py  # only once: freezes share prices at publication
```

## Add a new study

1. `analysis/<slug>/` with your Python scripts writing to `src/data/<slug>/`.
2. `src/content/posts/<slug>/index.mdx` with frontmatter and tags.
3. Tag pages and the home list update automatically.

## Deploy (Cloudflare)

```sh
npm run build
npx wrangler deploy
```

Colors live in `src/styles/global.css` (`--intel`, `--amd`, and the rest); charts read them at runtime, so light and dark themes stay in sync.
