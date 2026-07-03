# Hundo League Record Book

A historical archive for our 12-manager fantasy football league — 17 seasons
(2009–2025) of champions, career records, and superlatives. It's a **legacy /
analytics** site: previous seasons only, no live scoring.

The whole thing is a single self-contained HTML page (works offline, opens in any
browser, easy to share). It's published as a private Claude artifact and can be
shared with the league.

## Project layout

```
fantasy-league-record-book/
├── data/
│   └── league_finish.xlsx     # SOURCE OF TRUTH — one row per manager-season
├── src/
│   └── template.html          # page markup, CSS, and JS (data injected at build)
├── dist/
│   └── index.html             # generated output — this is what gets published
├── scripts/
│   └── preview.py             # headless-Chrome screenshots for visual QA
├── build.py                   # reads data + template -> writes dist/index.html
└── README.md
```

## How it works

`build.py` reads `data/league_finish.xlsx`, computes every stat (career records,
titles, podiums, leaderboards, extremes, per-manager histories), serializes them
to JSON, and injects that JSON into `src/template.html` (replacing the
`/*__DATA__*/` marker). The template renders everything client-side from that data
— so the page is data-driven and the Excel file stays the single source of truth.

## Common tasks

**Rebuild the page after any change:**

```bash
python build.py
```

**Add a new season or fix data** — edit `data/league_finish.xlsx`, then rebuild.
Columns: `Player, Team Name, Wins, Losses, Points for, Points Against,
Draft Position, Year, Finish, Moves, Trades, Donk`.
(`Finish` is recorded for places 1–6 only; blank = missed playoffs. `Donk` is
`Yes`/`No` for the last-place punishment.)

**Preview / screenshot locally** (needs Chrome):

```bash
python scripts/preview.py           # dark, light, mobile
```

**Publish** — the generated `dist/index.html` is what you deploy or hand back to
Claude to re-publish as the artifact.

## Setup

```bash
pip install pandas openpyxl
```

## Hosting (GitHub Pages)

`.github/workflows/deploy.yml` auto-publishes the site on every push to the
default branch: it installs deps, runs `build.py`, and deploys `dist/` to
GitHub Pages. No manual steps after the first push.

Live URL (after the first successful deploy):
**https://brendanchenry.github.io/fantasy-league-record-book/**

To update the public site: edit `data/league_finish.xlsx` (or the template),
commit, and `git push`. The Action rebuilds and redeploys in ~1 minute.

> Note: Pages serves a **public** URL even though the repo is private. If the
> first deploy is blocked because the repo is private on a free plan, make the
> repo public (`gh repo edit --visibility public`) — the page only contains
> fantasy nicknames and stats.

## Known data gaps / roadmap

- Four 2009 teams have no manager name and show as **Unknown** — fill them in
  `data/league_finish.xlsx` when known.
- Final placements exist only for 1st–6th; missed-playoff seasons are shown as
  unranked (no full 7–12 ranking available).
- Trades are a per-season **count**, not who-traded-with-whom. True head-to-head
  matchup data and a trade log would unlock a rivalries / H2H section — the main
  thing missing for a full legacy platform.
