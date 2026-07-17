# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A historical archive for a 12-manager fantasy football league — 17 seasons
(2009–2025) of champions, records, and superlatives. It's a **legacy/analytics**
site (past seasons only, no live scoring), shipped as a single self-contained
`dist/index.html` served from GitHub Pages and also hand-published as a private
Claude artifact.

## Commands

```bash
pip install pandas openpyxl          # one-time setup

python build.py                      # regenerate dist/index.html from the Excel + template
python scripts/preview.py            # screenshot dark, light, mobile -> scripts/_shots/ (needs Chrome)
python scripts/preview.py dark       # just one view
```

There are no tests and no linter.

**Windows/PowerShell gotcha:** player names and section labels contain emoji, so
any Python that *prints* league data (ad-hoc inspection, `print(df...)`) will
crash with a `cp1252` `UnicodeEncodeError`. Prefix with `PYTHONIOENCODING=utf-8`.
`build.py` itself is unaffected (it writes UTF-8 to a file, not the console).

## Architecture — the build contract

The whole app is a data-injection pipeline across three files that **move
together**:

1. **`data/league_finish.xlsx`** — the single source of truth, one row per
   manager-season. Columns: `Player, Team Name, Wins, Losses, Points for,
   Points Against, Draft Position, Year, Finish, Moves, Trades, Donk`.
   Note the real header is `Finish ` (trailing space); `build.py` strips all
   headers on load, so don't "fix" the sheet to match code — the code adapts.
2. **`build.py`** — reads the Excel, computes **every** stat in Python (career
   records, titles/podiums, leaderboards, extremes, per-manager histories,
   trade trend, donk championships), serializes it all into one compact JSON
   blob, and injects it into the template by replacing the literal
   `/*__DATA__*/` marker.
3. **`src/template.html`** — all markup, CSS, and JS. It renders **everything
   client-side** from the injected `DATA` object. It ships with `/*__DATA__*/`
   where the JSON lands.

`dist/index.html` is the generated output. It is **committed** (Pages serves it
and re-derives it), so after any change to the data or template, run
`python build.py` and commit the rebuilt `dist/` alongside your source edit.

**Consequence for any new stat or section:** you almost always touch *two*
files — add/extend the field in the `build_payload`/`build_managers` computation
in `build.py`, then consume `DATA.<field>` in the template's JS. Neither file is
useful alone.

## Conventions that aren't obvious from one file

- **Sections are numbered chapters** (roman numerals I, II, … in
  `src/template.html`). Inserting a section means renumbering the ones after it.
- **`finish`** is recorded only for places 1–6; `null`/blank means missed the
  playoffs (there is no full 7–12 ranking). `finish==1` champion, `2` runner-up,
  `3` third.
- **`donk`** is the last-place punishment — awarded to whoever *loses the
  loser's bracket*, not necessarily the worst record. `Yes`/`No` in Excel →
  bool. Framed site-wide as "King of Donks"; avoid "last place" language.
- **`Player == "Unknown"`** covers four 2009 teams with no recorded manager;
  they're carried in the data but excluded from `meta.nManagers` and the dossier
  picker.
- Data corrections happen **in the Excel**, then rebuild — e.g. a manager rename
  merges seasons automatically (there is no name-mapping table in code).

## Deploy

Pushing to `master` triggers `.github/workflows/deploy.yml`, which installs
deps, runs `build.py`, and deploys `dist/` to GitHub Pages (~1 min). Live at
https://brendanchenry.github.io/hundo-league-record-book/ — this repo commits
straight to `master`.

The **Ask the Archive** section (bring-your-own-AI, clipboard hand-off to
Claude/ChatGPT) relies on clipboard + opening a new tab. It works on the Pages
build but the Claude-artifact build's CSP blocks external navigation/network, so
treat that feature as Pages-only.
