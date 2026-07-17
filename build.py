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
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_XLSX = ROOT / "data" / "league_finish.xlsx"
TEMPLATE = ROOT / "src" / "template.html"
OUT = ROOT / "dist" / "index.html"

# Generational suffixes stripped when grouping draft picks, so "Will Fuller V"
# and "Will Fuller" count as the same guy.
_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def norm_name(n: str) -> str:
    parts = str(n).strip().split()
    if len(parts) > 1 and parts[-1].lower().strip(".") in _SUFFIXES:
        parts = parts[:-1]
    return " ".join(parts)


def load_seasons(path: Path) -> list[dict]:
    df = pd.read_excel(path, sheet_name="League_Summary")
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


def load_draft(path: Path) -> list[dict]:
    df = pd.read_excel(path, sheet_name="Draft_Results")
    df.columns = [c.strip() for c in df.columns]
    picks = []
    for _, r in df.iterrows():
        picks.append(dict(
            season=int(r["season"]), overall=int(r["overall_pick"]),
            round=int(r["round"]), pick=int(r["pick"]),
            player=str(r["player_name"]).strip(), manager=str(r["manager"]).strip()))
    return picks


def build_draft(picks: list[dict], seasons: list[dict]) -> dict:
    finish_by = {(s["player"], s["year"]): s["finish"] for s in seasons}

    # First-overall curse — each year's #1 pick and how that manager finished.
    firstOverall = sorted(
        (dict(year=p["season"], manager=p["manager"], player=p["player"],
              finish=finish_by.get((p["manager"], p["season"])))
         for p in picks if p["overall"] == 1),
        key=lambda d: d["year"])
    titles = sum(1 for d in firstOverall if d["finish"] == 1)
    missed = sum(1 for d in firstOverall if d["finish"] is None)
    # Longest run of consecutive years the #1 pick missed the playoffs (the boards
    # are one per year with no gaps, so index adjacency is year adjacency).
    longest = cur = 0
    best_end = -1
    for i, d in enumerate(firstOverall):
        cur = cur + 1 if d["finish"] is None else 0
        if cur > longest:
            longest, best_end = cur, i
    streakStart = firstOverall[best_end - longest + 1]["year"] if longest else None
    streakEnd = firstOverall[best_end]["year"] if longest else None
    fo_counts = Counter(d["player"] for d in firstOverall)
    top_name, top_cnt = fo_counts.most_common(1)[0]
    top_missed = sum(1 for d in firstOverall
                     if d["player"] == top_name and d["finish"] is None)
    meta = dict(n=len(firstOverall), titles=titles, missed=missed,
                streak=longest, streakStart=streakStart, streakEnd=streakEnd,
                topName=top_name, topCount=top_cnt, topMissed=top_missed)

    # "Your Guy" — each manager's most-repeatedly-drafted player.
    pair = Counter((p["manager"], norm_name(p["player"])) for p in picks)
    by_mgr: dict[str, tuple[str, int]] = {}
    for (mgr, pl), c in pair.items():
        cur = by_mgr.get(mgr)
        if cur is None or c > cur[1] or (c == cur[1] and pl < cur[0]):
            by_mgr[mgr] = (pl, c)
    crushes = sorted(
        (dict(manager=m, player=pl, count=c) for m, (pl, c) in by_mgr.items() if c >= 3),
        key=lambda d: (-d["count"], d["manager"]))

    # League darlings — most-drafted players across every board.
    darl = Counter(norm_name(p["player"]) for p in picks)
    darlings = [dict(player=pl, count=c) for pl, c in darl.most_common(8)]

    return dict(firstOverall=firstOverall, crushes=crushes, darlings=darlings, meta=meta)


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


def build_payload(seasons: list[dict], picks: list[dict]) -> dict:
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
        most_trades=best("trades"), most_moves=best("moves"))

    tradeTrend = []
    for y in years:
        sub = [s for s in seasons if s["year"] == y]
        tradeTrend.append(dict(year=y, avg=round(sum(s["trades"] for s in sub) / len(sub), 2),
                               total=sum(s["trades"] for s in sub)))

    # Donk championships — the last-place "title" race. Count each manager's
    # donks and the years they earned them; most donks is the Donk Champion.
    donk_years: dict[str, list[int]] = {}
    for s in seasons:
        if s["donk"]:
            donk_years.setdefault(s["player"], []).append(s["year"])
    donkChamps = [dict(player=p, donks=len(ys), years=sorted(ys))
                  for p, ys in donk_years.items()]
    donkChamps.sort(key=lambda d: (-d["donks"], d["years"][0]))

    named = [m for m in managers if m["player"] != "Unknown"]
    lastYear = years[-1]

    # Within-season points-for rank (1 = top scorer that year) so scoring across
    # different eras / league sizes compares fairly. Keyed by id() of the season.
    pf_rank: dict[int, tuple[int, int]] = {}
    for y in years:
        sub = sorted((s for s in seasons if s["year"] == y),
                     key=lambda s: s["pf"], reverse=True)
        for i, s in enumerate(sub):
            pf_rank[id(s)] = (i + 1, len(sub))

    def luck_row(s: dict) -> dict:
        r, n = pf_rank[id(s)]
        return dict(player=s["player"], year=s["year"], team=s["team"],
                    wins=s["wins"], losses=s["losses"], pf=s["pf"],
                    rank=r, of=n, finish=s["finish"])

    # The Luck Lens. "Robbed": high scorers who still missed the playoffs.
    # "Backed In": weak scorers who reached the playoffs anyway.
    real = [s for s in seasons if s["player"] != "Unknown"]
    robbed = sorted((luck_row(s) for s in real if s["finish"] is None),
                    key=lambda d: (d["rank"], -d["pf"]))[:6]
    backed_in = sorted((luck_row(s) for s in real if s["finish"] is not None),
                       key=lambda d: (-d["rank"], d["pf"]))[:6]
    luck = dict(robbed=robbed, backedIn=backed_in)

    # Redemption arcs — a donk followed by a podium (top-3) within three seasons.
    redemption = []
    for m in named:
        h = m["history"]
        for i, d in enumerate(h):
            if not d["donk"]:
                continue
            for g in h[i + 1:]:
                if g["year"] - d["year"] > 3:
                    break
                if g["finish"] is not None and g["finish"] <= 3:
                    redemption.append(dict(player=m["player"], donkYear=d["year"],
                        gloryYear=g["year"], finish=g["finish"], team=g["team"],
                        gap=g["year"] - d["year"]))
                    break
    redemption.sort(key=lambda d: (d["finish"], d["gap"], d["gloryYear"]))

    # The Near-Miss Club — podium finishes but never a title.
    nearMiss = [dict(player=m["player"], seasons=m["seasons"], runnerups=m["runnerups"],
                     thirds=m["thirds"], podiums=m["podiums"], pf=m["pf"])
                for m in named if m["titles"] == 0 and m["podiums"] > 0]
    nearMiss.sort(key=lambda d: (-d["runnerups"], -d["podiums"], -d["seasons"]))

    # Title droughts — years since each champion last won (as of the latest season).
    droughts = [dict(player=m["player"], titles=m["titles"], lastTitle=m["titleYears"][-1],
                     drought=lastYear - m["titleYears"][-1])
                for m in named if m["titles"] > 0]
    droughts.sort(key=lambda d: (-d["drought"], -d["titles"]))

    # Cinderella champions — weakest regular seasons that still won it all,
    # plus how many rings came out of each draft slot.
    champ_seasons = [s for s in seasons if s["finish"] == 1]
    cindyChamps = [dict(player=s["player"], year=s["year"], team=s["team"], wins=s["wins"],
                        losses=s["losses"], pf=s["pf"], draft=s["draft"], rank=pf_rank[id(s)][0],
                        of=pf_rank[id(s)][1])
                   for s in sorted(champ_seasons, key=lambda s: (s["wins"], s["pf"]))[:5]]
    draft_counts: dict[int, int] = {}
    for s in champ_seasons:
        if s["draft"] is not None:
            draft_counts[s["draft"]] = draft_counts.get(s["draft"], 0) + 1
    championsByDraft = [dict(slot=k, count=draft_counts[k]) for k in sorted(draft_counts)]
    cinderella = dict(champs=cindyChamps, byDraft=championsByDraft)

    return dict(
        seasons=seasons, managers=managers, champByYear=champByYear,
        runnerByYear=runnerByYear, years=years, superlatives=superlatives,
        tradeTrend=tradeTrend, donkChamps=donkChamps,
        luck=luck, redemption=redemption, nearMiss=nearMiss,
        droughts=droughts, cinderella=cinderella,
        draft=build_draft(picks, seasons),
        meta=dict(nSeasons=len(years), firstYear=years[0], lastYear=years[-1],
                  nManagerSeasons=len(seasons),
                  nManagers=len([m for m in managers if m["player"] != "Unknown"])))


def main() -> None:
    seasons = load_seasons(DATA_XLSX)
    picks = load_draft(DATA_XLSX)
    payload = build_payload(seasons, picks)
    data_json = json.dumps(payload, separators=(",", ":"))
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/", data_json)
    OUT.write_text(html, encoding="utf-8")
    print(f"Built {OUT.relative_to(ROOT)}  ({len(html):,} bytes, "
          f"{len(seasons)} seasons, {len(payload['managers'])} managers)")


if __name__ == "__main__":
    main()
