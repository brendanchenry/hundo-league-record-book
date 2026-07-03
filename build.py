#!/usr/bin/env python3
"""Build the Hundo League Record Book.

Reads the league data (Excel) + the HTML template, computes all stats, injects
them as JSON into the template, and writes the final page to dist/index.html.

Usage:
    python build.py

The Excel file in data/ is the single source of truth. Edit it (fix names, add a
new season) and re-run this script to regenerate the page. Then re-publish
dist/index.html as the artifact.
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_XLSX = ROOT / "data" / "league_finish.xlsx"
TEMPLATE = ROOT / "src" / "template.html"
OUT = ROOT / "dist" / "index.html"


def load_seasons(path: Path) -> list[dict]:
    df = pd.read_excel(path)
    df.columns = [c.strip() for c in df.columns]
    df["Player"] = df["Player"].fillna("Unknown")
    seasons = []
    for _, r in df.iterrows():
        seasons.append(dict(
            player=r["Player"], team=str(r["Team Name"]),
            wins=int(r["Wins"]), losses=int(r["Losses"]),
            pf=round(float(r["Points for"]), 2), pa=round(float(r["Points Against"]), 2),
            draft=None if pd.isna(r["Draft Position"]) else int(r["Draft Position"]),
            year=int(r["Year"]),
            finish=None if pd.isna(r["Finish"]) else int(r["Finish"]),
            moves=int(r["Moves"]), trades=int(r["Trades"]),
            donk=(r["Donk"] == "Yes")))
    return seasons


def build_managers(seasons: list[dict]) -> list[dict]:
    mgr: dict[str, dict] = {}
    for s in seasons:
        p = s["player"]
        a = mgr.setdefault(p, dict(player=p, seasons=0, wins=0, losses=0, pf=0.0, pa=0.0,
            titles=0, runnerups=0, thirds=0, podiums=0, playoffs=0, trades=0, moves=0,
            donks=0, titleYears=[], history=[]))
        a["seasons"] += 1; a["wins"] += s["wins"]; a["losses"] += s["losses"]
        a["pf"] += s["pf"]; a["pa"] += s["pa"]; a["trades"] += s["trades"]; a["moves"] += s["moves"]
        if s["donk"]:
            a["donks"] += 1
        f = s["finish"]
        if f is not None:
            a["playoffs"] += 1
            if f == 1:
                a["titles"] += 1; a["titleYears"].append(s["year"])
            if f == 2:
                a["runnerups"] += 1
            if f == 3:
                a["thirds"] += 1
            if f <= 3:
                a["podiums"] += 1
        a["history"].append(dict(year=s["year"], team=s["team"], wins=s["wins"], losses=s["losses"],
            pf=s["pf"], pa=s["pa"], finish=f, draft=s["draft"], trades=s["trades"], moves=s["moves"],
            donk=s["donk"]))

    managers = []
    for a in mgr.values():
        g = a["wins"] + a["losses"]
        a["games"] = g
        a["winpct"] = round(a["wins"] / g, 4) if g else 0
        a["ppg"] = round(a["pf"] / g, 2) if g else 0
        a["papg"] = round(a["pa"] / g, 2) if g else 0
        a["playoffRate"] = round(a["playoffs"] / a["seasons"], 4) if a["seasons"] else 0
        a["pf"] = round(a["pf"], 2); a["pa"] = round(a["pa"], 2)
        a["history"].sort(key=lambda h: h["year"])
        a["titleYears"].sort()
        managers.append(a)
    managers.sort(key=lambda a: (-a["titles"], -a["winpct"]))
    return managers


def build_payload(seasons: list[dict]) -> dict:
    managers = build_managers(seasons)
    champByYear, runnerByYear = {}, {}
    for s in seasons:
        if s["finish"] == 1:
            champByYear[s["year"]] = s["player"]
        if s["finish"] == 2:
            runnerByYear[s["year"]] = s["player"]
    years = sorted({s["year"] for s in seasons})

    best = lambda key, rev=True: sorted(seasons, key=lambda s: s[key], reverse=rev)[0]
    best_rec = sorted(seasons, key=lambda s: (s["wins"] - s["losses"], s["pf"]), reverse=True)[0]
    worst_rec = sorted(seasons, key=lambda s: (s["wins"] - s["losses"], s["pf"]))[0]
    superlatives = dict(
        hi_pf=best("pf"), lo_pf=best("pf", rev=False),
        best_rec=best_rec, worst_rec=worst_rec,
        most_trades=best("trades"), most_moves=best("moves"),
        donks=[s for s in seasons if s["donk"]])

    tradeTrend = []
    for y in years:
        sub = [s for s in seasons if s["year"] == y]
        tradeTrend.append(dict(year=y, avg=round(sum(s["trades"] for s in sub) / len(sub), 2),
                               total=sum(s["trades"] for s in sub)))

    return dict(
        seasons=seasons, managers=managers, champByYear=champByYear,
        runnerByYear=runnerByYear, years=years, superlatives=superlatives,
        tradeTrend=tradeTrend,
        meta=dict(nSeasons=len(years), firstYear=years[0], lastYear=years[-1],
                  nManagerSeasons=len(seasons),
                  nManagers=len([m for m in managers if m["player"] != "Unknown"])))


def main() -> None:
    seasons = load_seasons(DATA_XLSX)
    payload = build_payload(seasons)
    data_json = json.dumps(payload, separators=(",", ":"))
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/", data_json)
    OUT.write_text(html, encoding="utf-8")
    print(f"Built {OUT.relative_to(ROOT)}  ({len(html):,} bytes, "
          f"{len(seasons)} seasons, {len(payload['managers'])} managers)")


if __name__ == "__main__":
    main()
