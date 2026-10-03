# Data Notes — project guide

Public blog of data studies by Illia Hrebenko, made with AI agents and reviewed by him.
Live: https://data-notes.data-notes.workers.dev · Repo: https://github.com/elmorrrrro/data-notes (public)

## Conventions
- Site, code and commits are in English.
- Every number needs a source link in the post's Methodology section. Verify claims in the text against the data.
- Owner-specific conventions are in `CLAUDE.local.md` (git-ignored); if it is missing, ask the owner.

## Adding a new study (slug example: `nvidia-vs-amd-gpus-2026-11`)
1. **Analysis** in `analysis/<slug>/`, plain Python scripts (no notebooks):
   - `collect.py`: fetch sources, save raw pages to `raw/` (git-ignored, third-party content stays local).
   - `analyze.py`: write `src/data/<slug>/*.json` for the page, `exports/*.csv` for Power BI (git-ignored),
     and a public download in `public/data/<slug>/` — without data whose terms forbid redistribution (e.g. PassMark scores).
   - If the study tracks shares: `snapshot_stocks.py` freezes closes at publication into `src/data/<slug>/stocks_snapshot.json`
     (run once; publication on a weekend = last Friday close). Tickers must be in `ALLOWED` in `src/pages/api/quote.ts`.
2. **Post** `src/content/posts/<slug>/index.mdx`, frontmatter:
   ```yaml
   title: "..."
   description: "..."
   date: 2026-11-01
   tags: [lowercase, tags]
   accents: ['#hex1', '#hex2']   # or CSS vars; drives glow, badges, section numbers
   stocks: [NVDA, AMD]           # optional; shows "at publication -> now" on the home card
   ```
   Structure that works: short answer → `<KeyNumbers>`-style scoreboard → numbered `##` sections, each with one chart and
   a paragraph of interpretation → "What the numbers leave out" → Data table + download → Methodology (sources, exclusions,
   trademarks).
3. **Charts**: components in `src/components/charts/`, wrapped in `Figure.astro`, drawn with Observable Plot via `mount()`
   from `src/lib/chart.ts` (theme tokens, resize, dark mode). Follow the dataviz skill: validate any new palette with its
   validator (light + dark), thin marks, direct labels only where they don't collide, tooltips on every chart.
   Study-specific components should read that study's `src/data/<slug>/` files.
4. **Check visually**: screenshot light, dark and 390px mobile (headless Edge or playwright-core with channel `msedge`),
   look for label collisions and overflow.
5. **Publish**: `git add -A && git commit && git push` to `main`. Cloudflare Workers Builds deploys automatically
   (~1 min). Verify with `npx wrangler deployments list` and by opening the live URL.
6. **Newsletter**: pushing a NEW `src/content/posts/<slug>/index.mdx` triggers `.github/workflows/newsletter.yml`, which
   runs `scripts/notify-new-posts.mjs` and creates a Buttondown email (newsletter `datanotes`) from the post's title and
   description. Default is a draft the owner reviews and sends; repo variable `NEWSLETTER_MODE=send` makes it automatic.
   Edits to existing posts never send. Manual test: Actions → Newsletter → Run workflow (always a `[TEST]` draft).
   Study-update emails are sent by hand to the post's tag (signups are tagged with the post slug).

## Gotchas (learned the hard way)
- Never run `astro build` while `astro dev` is running: it wipes Vite's deps cache and the dev server's charts go blank.
  Stop dev first (`npx astro dev stop`), restart after.
- After changing `src/content.config.ts` (schema), restart dev with the content cache cleared: `rm -rf .astro`.
- Git Bash mangles URL paths in curl: prefix with `MSYS_NO_PATHCONV=1`. PowerShell 5.1 can't do modern TLS; use curl.
- Fonts are self-hosted via `@fontsource` (GDPR); don't add Google Fonts links.
- `src/lib/site.ts` holds socials, `CF_ANALYTICS_TOKEN` and `NEWSLETTER_USERNAME` (subscribe forms render only when set).
- Secrets never go in files: `BUTTONDOWN_API_KEY` is a GitHub Actions secret (`gh secret set BUTTONDOWN_API_KEY`).
- `gh` is installed at `C:\Program Files\GitHub CLI\gh.exe` (may not be on PATH in older shells).
- RSS: `/rss.xml` (`src/pages/rss.xml.ts`) lists every post automatically.

## Development

When starting the dev server, use background mode:

```
astro dev --background
```

Manage the background server with `astro dev stop`, `astro dev status`, and `astro dev logs`.

## Documentation

Full documentation: https://docs.astro.build

Consult these guides before working on related tasks:

- [Adding pages, dynamic routes, or middleware](https://docs.astro.build/en/guides/routing/)
- [Working with Astro components](https://docs.astro.build/en/basics/astro-components/)
- [Using React, Vue, Svelte, or other framework components](https://docs.astro.build/en/guides/framework-components/)
- [Adding or managing content](https://docs.astro.build/en/guides/content-collections/)
- [Adding styles or using Tailwind](https://docs.astro.build/en/guides/styling/)
- [Supporting multiple languages](https://docs.astro.build/en/guides/internationalization/)
