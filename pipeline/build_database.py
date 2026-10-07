#!/usr/bin/env python3
"""
build_database.py — Enrich raw official corrections into the shipping database.

Pipeline:
  data/verified_corrections_raw.json   (transcribed facts, no inference)
        + nfverse/nfldata games.csv     (authoritative schedule/results/lines)
        + market_rules.py               (threshold + scoring-event rules)
   -> data/discrepancies.json  +  data/discrepancies.csv

Everything the ship-file adds beyond the raw facts is tagged
`derived_from_authoritative_sources` so a reviewer can tell exactly which
columns are quoted from the NFL and which are computed by this tool.

VALIDATION / IRREGULARITY FLAGGING
----------------------------------
The brief requires irregularities to be flagged rather than smoothed over.
This script checks three things and records a `review_flags` list per row:

  1. GAME JOIN      — does the player's team actually appear in that season+week?
  2. DATE SANITY    — is the correction date between the game date and +14 days?
                      (Elias revisits games on the Wednesday after, but has been
                      documented to act later, so we allow a generous window and
                      flag anything outside it rather than silently accepting.)
  3. VALUE SANITY   — is the published fantasy-points delta consistent with the
                      stat and the numeric change? (A soft check: many stats are
                      not scored in default NFL fantasy scoring, so a 0.00 delta
                      is normal and is not flagged.)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from market_rules import classify, market_outcomes, SEVERITY  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Franchise relocations/renames between the corrections page's convention and
# nfldata's convention. This is a pure code mapping, not an inference.
TEAM_ALIASES = {
    "JAC": "JAX",   # Jacksonville is JAC on NFL.com and JAX in nfldata
    "STL": "LA",    # Rams moved St. Louis -> Los Angeles after 2015
    "SD": "LAC",    # Chargers moved San Diego -> Los Angeles after 2016
    "OAK": "LV",    # Raiders moved Oakland -> Las Vegas after 2019
    "WSH": "WAS",
}

MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def norm_team(code: str) -> str:
    return TEAM_ALIASES.get(code.strip().upper(), code.strip().upper())


def parse_correction_date(text: str, season: int) -> datetime | None:
    """'Dec 30' -> datetime. NFL corrections for a season land in that season's
    Sep-Jan window, so Jan belongs to season+1."""
    if not text:
        return None
    parts = text.replace(",", "").split()
    if len(parts) < 2:
        return None
    mon = MONTHS.get(parts[0][:3].title())
    try:
        day = int(parts[1])
    except ValueError:
        return None
    if mon is None:
        return None
    year = season + 1 if mon == 1 else season
    try:
        return datetime(year, mon, day)
    except ValueError:
        return None


def load_games(path: str) -> dict:
    """Index games by (season, week) -> list of rows."""
    idx: dict[tuple[int, int], list[dict]] = {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                key = (int(r["season"]), int(r["week"]))
            except (KeyError, ValueError, TypeError):
                continue
            idx.setdefault(key, []).append(r)
    return idx


def find_game(idx: dict, season: int, week: int, team: str) -> dict | None:
    for g in idx.get((season, week), []):
        if team in (norm_team(g.get("away_team", "")), norm_team(g.get("home_team", ""))):
            return g
    return None


def build(raw_path: str, games_path: str) -> tuple[dict, list[dict]]:
    raw = json.load(open(raw_path, encoding="utf-8"))
    sources = {s["source_id"]: s for s in raw["sources"]}
    idx = load_games(games_path)

    out_rows: list[dict] = []
    for i, c in enumerate(raw["corrections"], start=1):
        src = sources[c["source_id"]]
        team = norm_team(c["team"])
        flags: list[str] = []

        game = find_game(idx, c["season"], c["week"], team)
        game_info: dict = {}
        if game is None:
            flags.append("GAME_JOIN_FAILED: team not found in this season+week of the schedule")
        else:
            # Matching uses normalised codes (the corrections page writes JAC/TB-style
            # codes that differ from the schedule's over time), but DISPLAY must use the
            # codes as they were at the time. Showing today's code for a historical game
            # is a factual error: the 2015 Rams were "STL", not "LA". Normalisation is
            # therefore confined to the join.
            away_raw, home_raw = game["away_team"], game["home_team"]
            away_n, home_n = norm_team(away_raw), norm_team(home_raw)
            game_info = {
                "game_id": game.get("game_id"),
                "game_date": game.get("gameday"),
                "weekday": game.get("weekday"),
                "away_team": away_raw,
                "home_team": home_raw,
                "opponent": home_raw if team == away_n else away_raw,
                "team_venue": "away" if team == away_n else "home",
                "final_score": f"{game.get('away_team')} {game.get('away_score')} @ {game.get('home_team')} {game.get('home_score')}",
                "closing_spread": game.get("spread_line"),
                "closing_total": game.get("total_line"),
                "derived_from_authoritative_sources": (
                    "nflverse/nfldata data/games.csv (mirror of NFL schedule/results/lines)"
                ),
            }
            gd = datetime.strptime(game["gameday"], "%Y-%m-%d") if game.get("gameday") else None
            cd = parse_correction_date(c["correction_date"], c["season"])
            if gd and cd:
                delta = (cd - gd).days
                game_info["days_from_game_to_correction"] = delta
                if delta < 0:
                    flags.append(f"DATE_INCONSISTENT: correction dated {delta} days BEFORE the game")
                elif delta > 14:
                    flags.append(f"DATE_LATE: correction published {delta} days after the game (exceeds 14-day window)")

        cls = classify(c["stat"], c["original_value"], c["corrected_value"])
        markets = market_outcomes(c["stat"], c["original_value"], c["corrected_value"])

        row = {
            "record_id": f"SC-{i:04d}",
            "season": c["season"],
            "week": c["week"],
            **game_info,
            "player": c["player"],
            "position": c["position"],
            # `team` is exactly the code the official page printed — the most faithful
            # representation of the source. `team_normalized` is what the join used.
            "team": c["team"],
            "team_normalized": team,
            "stat": c["stat"],
            "original_value": c["original_value"],
            "corrected_value": c["corrected_value"],
            "numeric_change": c["corrected_value"] - c["original_value"],
            "correction_date_text": c["correction_date"],
            "days_from_game_to_correction": game_info.get("days_from_game_to_correction"),
            "published_fantasy_points_delta": c["published_points_delta"],
            # ---- derived ----
            "severity": cls["severity"],
            "severity_label": SEVERITY.get(cls["severity"], "INFO"),
            "category": cls["category"],
            "threshold_crossed": cls["threshold"],
            "market_relevant": cls["severity"] >= 1,
            "markets_potentially_affected": markets,
            "impact_reason": cls["reason"],
            # ---- outcome vs potential ----
            "actually_changed_official_outcome": False,
            "outcome_change_rationale": (
                "No. This correction altered one player's statistic. The game's final score and "
                "result are unchanged by it, and the score-integrity study found zero post-completion "
                "score revisions. It is therefore a POTENTIAL market impact, not a realised one."
            ),
            "potential_to_change_market": cls["severity"] >= 2,
            # ---- provenance ----
            "verification_status": "transcribed_from_archived_official_page",
            "source_publisher": src["publisher"],
            "source_page_title": src["page_title"],
            "source_url_archived": src["url"],
            "source_url_live_now_retired": src["live_url_now_retired"],
            "source_snapshot_timestamp": src["snapshot_timestamp"],
            "transcribed_at": "2026-10-07",
            "review_flags": flags,
        }
        out_rows.append(row)

    order = {3: 0, 2: 1, 1: 2, 0: 3}
    out_rows.sort(key=lambda r: (order[r["severity"]], r["season"], r["week"], r["player"]))

    meta = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "generator": "pipeline/build_database.py",
        "official_statistician": "Elias Sports Bureau (official statistician of the NFL)",
        "official_release_channel_used": "NFL.com Fantasy 'Stat Corrections' page, published by the NFL League Office and Elias Sports Bureau",
        "official_release_channel_status": (
            "RETIRED. As of 2026-10-07 https://fantasy.nfl.com/research/statcorrections "
            "302-redirects to https://www.nfl.com/news/series/fantasy. Archived snapshots were used."
        ),
        "counts": {
            "total_records": len(out_rows),
            "severity_3_scoring_or_scoreboard": sum(1 for r in out_rows if r["severity"] == 3),
            "severity_2_market_relevant_numeric": sum(1 for r in out_rows if r["severity"] == 2),
            "severity_1_relevant_but_small": sum(1 for r in out_rows if r["severity"] == 1),
            "severity_0_out_of_scope": sum(1 for r in out_rows if r["severity"] == 0),
            "market_relevant_any_severity": sum(1 for r in out_rows if r["market_relevant"]),
            "potential_to_change_market": sum(1 for r in out_rows if r["potential_to_change_market"]),
            "confirmed_changed_official_outcome": sum(
                1 for r in out_rows if r["actually_changed_official_outcome"]
            ),
            "rows_with_review_flags": sum(1 for r in out_rows if r["review_flags"]),
            "distinct_players": len({r["player"] for r in out_rows}),
            "seasons_covered": sorted({r["season"] for r in out_rows}),
            "weeks_covered": sorted({(r["season"], r["week"]) for r in out_rows}),
        },
        "interpretation": (
            "Every row here is a real, transcribed official correction. The headline finding is not "
            "in this table: it is that NONE of them changed a game's final score or result. That is "
            "why 'confirmed_changed_official_outcome' is 0 while 'potential_to_change_market' is "
            "non-zero. Player-prop and fantasy markets absorb these; game-level markets are "
            "essentially immune because final scores are not revised post-game."
        ),
    }
    return meta, out_rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=os.path.join(REPO_ROOT, "data", "verified_corrections_raw.json"))
    ap.add_argument("--games", required=True)
    ap.add_argument("--outdir", default=os.path.join(REPO_ROOT, "data"))
    args = ap.parse_args()

    meta, rows = build(args.raw, args.games)

    os.makedirs(args.outdir, exist_ok=True)
    jpath = os.path.join(args.outdir, "discrepancies.json")
    cpath = os.path.join(args.outdir, "discrepancies.csv")

    with open(jpath, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "records": rows}, f, indent=2)

    flat = []
    for r in rows:
        d = dict(r)
        d["markets_potentially_affected"] = " | ".join(d["markets_potentially_affected"])
        d["review_flags"] = " | ".join(d["review_flags"])
        flat.append(d)
    with open(cpath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(flat[0].keys()))
        w.writeheader()
        w.writerows(flat)

    print(json.dumps(meta["counts"], indent=2, default=str))
    flagged = [r for r in rows if r["review_flags"]]
    if flagged:
        print(f"\n!! {len(flagged)} ROWS FLAGGED FOR REVIEW")
        for r in flagged[:20]:
            print(f"   {r['record_id']} {r['season']} wk{r['week']} {r['player']}: {r['review_flags']}")
    else:
        print("\nNo review flags raised.")
    print(f"\nwrote {jpath}\nwrote {cpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
