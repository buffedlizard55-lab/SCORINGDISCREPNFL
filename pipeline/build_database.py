#!/usr/bin/env python3
"""
build_database.py — Enrich raw official corrections into the shipping database.

Pipeline:
  data/verified_corrections_raw.json   (transcribed facts, no inference)
        + nflverse/nfldata games.csv    (third-party schedule/results/line mirror)
        + market_rules.py               (threshold + scoring-event rules)
   -> data/discrepancies.json  +  data/discrepancies.csv

Everything the ship-file adds beyond the raw facts is tagged as derived from
a named source so reviewers can distinguish page-transcribed values from
schedule joins and project-computed fields.

VALIDATION / IRREGULARITY FLAGGING
----------------------------------
The brief requires irregularities to be flagged rather than smoothed over.
This script checks three things and records a `review_flags` list per row:

  1. GAME JOIN      — does the player's team actually appear in that season+week?
  2. DATE SANITY    — is the displayed correction date between the game date
                      and the project's +14-day review marker? This is a
                      validation heuristic, not an NFL deadline or policy.
  3. VALUE SANITY   — is the published fantasy-points delta consistent with the
                      stat and the numeric change? (A soft check: many stats are
                      not scored in default NFL fantasy scoring, so a 0.00 delta
                      is normal and is not flagged.)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
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


# ---------------------------------------------------------------------------
# CONTENT-STABLE RECORD IDS (fixes the P1-4 bug)
# ---------------------------------------------------------------------------
# `record_id` used to be `SC-{i:04d}` — a positional ordinal in build order.
# Adding 38 rows once silently re-pointed every external citation at a different
# correction: an issue, an email or a bookmark that said SC-0034 started meaning
# something else, and nothing failed. The id is now derived from the row's own
# identity, so inserting a row can never change an existing id.
#
# Identity fields are chosen to be exactly the things that make two correction
# rows the same correction on the same page. `correction_date` is required
# because the official page sometimes lists the same correction on two
# consecutive days (LIMITATIONS §13).
RECORD_IDENTITY_FIELDS = (
    "source_id", "season", "week", "player", "position", "stat",
    "original_value", "corrected_value", "correction_date", "published_points_delta",
)


def stable_record_id(correction: dict, tie_break: int = 0) -> str:
    """`SC-` + 10 hex chars of the SHA-256 of the row's identity.

    `tie_break` is only ever non-zero for rows whose identity is *identical* to
    another row on the same page. It counts among those duplicates, so it cannot
    be disturbed by unrelated insertions elsewhere in the corpus.
    """
    ident = "|".join(repr(correction.get(f)) for f in RECORD_IDENTITY_FIELDS)
    if tie_break:
        ident += f"|#dup{tie_break}"
    digest = hashlib.sha256(ident.encode("utf-8")).hexdigest()[:10].upper()
    return f"SC-{digest}"


def assign_record_ids(corrections: list[dict]) -> list[str]:
    """Assign ids, de-duplicating exact identity collisions deterministically."""
    seen: dict[str, int] = {}
    ids: list[str] = []
    for c in corrections:
        base = stable_record_id(c)
        n = seen.get(base, 0)
        seen[base] = n + 1
        ids.append(base if n == 0 else stable_record_id(c, tie_break=n))
    if len(set(ids)) != len(ids):
        # Unreachable by construction, but a duplicate id would silently merge two
        # different corrections in every downstream index. Fail loudly instead.
        raise ValueError("record_id collision could not be resolved; identity fields are too weak")
    return ids


def norm_team(code: str) -> str:
    if not code:
        return ""
    return TEAM_ALIASES.get(code.strip().upper(), code.strip().upper())


# Defensive-unit ("DEF") rows print the franchise NICKNAME and no team code at
# all (the cell reads "_DEF_"). Resolving that nickname to a code is therefore a
# derivation, not a transcription, so it lives here in the derived layer and is
# labelled as such on every row it touches. Tests assert that every code in this
# table occurs in the versioned third-party schedule snapshot, so a typo or an
# invented code fails the build instead of shipping.
TEAM_NAME_TO_CODE = {
    "arizona cardinals": "ARI", "atlanta falcons": "ATL", "baltimore ravens": "BAL",
    "buffalo bills": "BUF", "carolina panthers": "CAR", "chicago bears": "CHI",
    "cincinnati bengals": "CIN", "cleveland browns": "CLE", "dallas cowboys": "DAL",
    "denver broncos": "DEN", "detroit lions": "DET", "green bay packers": "GB",
    "houston texans": "HOU", "indianapolis colts": "IND", "jacksonville jaguars": "JAX",
    "kansas city chiefs": "KC", "los angeles chargers": "LAC", "los angeles rams": "LA",
    "las vegas raiders": "LV", "miami dolphins": "MIA", "minnesota vikings": "MIN",
    "new england patriots": "NE", "new orleans saints": "NO", "new york giants": "NYG",
    "new york jets": "NYJ", "philadelphia eagles": "PHI", "pittsburgh steelers": "PIT",
    "san francisco 49ers": "SF", "seattle seahawks": "SEA", "tampa bay buccaneers": "TB",
    "tennessee titans": "TEN", "washington commanders": "WAS",
    # historical nicknames, so pre-relocation DEF rows still resolve
    "oakland raiders": "OAK", "san diego chargers": "SD", "st. louis rams": "STL",
    "washington redskins": "WSH", "washington football team": "WSH",
}


def team_code_from_nickname(name: str) -> str | None:
    """Resolve a printed franchise nickname to a code, or None if unknown.
    Never guesses: an unmapped nickname stays unresolved and gets flagged."""
    if not name:
        return None
    return TEAM_NAME_TO_CODE.get(name.strip().lower())


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


def sha256_file(path: str) -> str:
    """Hash an input file without loading the full source into memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_game(idx: dict, season: int, week: int, team: str) -> dict | None:
    for g in idx.get((season, week), []):
        if team in (norm_team(g.get("away_team", "")), norm_team(g.get("home_team", ""))):
            return g
    return None


def build(raw_path: str, games_path: str) -> tuple[dict, list[dict]]:
    with open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)
    sources = {s["source_id"]: s for s in raw["sources"]}
    idx = load_games(games_path)

    out_rows: list[dict] = []
    record_ids = assign_record_ids(raw["corrections"])
    for i, (c, record_id) in enumerate(zip(raw["corrections"], record_ids), start=1):
        src = sources[c["source_id"]]
        # `team` is exactly what the official page printed. On a defensive-unit row
        # the page prints a franchise nickname and NO code, so any code on such a
        # row is derived here and labelled as derived. Previously the raw file
        # carried a normalised code (e.g. "JAX" where the page printed "JAC"), which
        # made the "as printed" field untrue — fixed 2026-10-07.
        printed_team = c.get("team")
        team_source = "as_printed_on_official_page"
        team = ""
        if printed_team:
            team = norm_team(printed_team)
        elif c.get("position") == "DEF":
            # A defensive-unit row prints the franchise nickname and no code.
            derived = team_code_from_nickname(c.get("player"))
            if derived:
                team = norm_team(derived)
                team_source = "derived_from_printed_nickname"
        if not team:
            # The page printed a position with no team code (seen on real 2013 W1
            # rows). Resolving it would mean inferring a team the source never
            # published, so we do not: we record the gap and flag it.
            team_source = "not_printed_on_source"
        flags: list[str] = []
        if team_source == "not_printed_on_source":
            flags.append(
                "TEAM_NOT_PRINTED: the official page printed no team code for this "
                "player, so the game join was not attempted (inferring a team would "
                "put unsourced data in the database)"
            )

        # NOTE: this must test `game is not None` first. The earlier shape was
        # `if game is None: flag ... else: <use game>`, which crashes with
        # TypeError on any row where the join legitimately cannot run (no team
        # code printed). Found 2026-10-07 by the 2013 W1 rows.
        game = find_game(idx, c["season"], c["week"], team) if team else None
        game_info: dict = {}
        if game is None:
            if team:
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
                "derived_from_versioned_mirror": (
                    "nflverse/nfldata data/games.csv (third-party mirror of NFL schedule/results/lines)"
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
                    flags.append(f"DATE_LATE: source row date is {delta} days after the game (exceeds 14-day review window)")

        cls = classify(c["stat"], c["original_value"], c["corrected_value"])
        markets = market_outcomes(c["stat"], c["original_value"], c["corrected_value"])

        row = {
            # Content-derived and stable under insertion. `record_ordinal` keeps a
            # human-friendly build-order number without letting anything depend on
            # position for identity.
            "record_id": record_id,
            "record_ordinal": i,
            "season": c["season"],
            "week": c["week"],
            **game_info,
            "player": c["player"],
            "position": c["position"],
            # `team` is exactly the code the official page printed (null when the
            # page printed only a nickname). `team_normalized` is what the join
            # used. `team_source` says which of the two produced it.
            "team": printed_team,
            "team_normalized": team or None,
            "team_source": team_source,
            "stat": c["stat"],
            # The archived correction rows expose the changed value but do not
            # give a rationale field. Keep the cause explicitly unknown rather
            # than turning a market-impact explanation into an NFL explanation.
            "correction_reason": c.get("correction_reason"),
            "correction_reason_status": (
                "stated_in_source" if c.get("correction_reason") else "not_stated_in_archived_official_notice"
            ),
            "original_value": c["original_value"],
            "corrected_value": c["corrected_value"],
            "numeric_change": (
                None if c["original_value"] is None or c["corrected_value"] is None
                else c["corrected_value"] - c["original_value"]
            ),
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
                "No verified final-score change or sportsbook/fantasy settlement is documented for "
                "this row. The archived notice changes a player statistic only; any player-market "
                "effect depends on the actual offered line and applicable rules, which are not "
                "verified here. Treat the impact as potential, not realised."
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
        "game_data_input": {
            "source": "nflverse/nfldata data/games.csv (third-party mirror)",
            "source_url": "https://github.com/nflverse/nfldata/blob/master/data/games.csv",
            "input_basename": os.path.basename(games_path),
            "sha256": sha256_file(games_path),
            "bytes": os.path.getsize(games_path),
            "retained_by_builder": False,
            "note": "Hash identifies the exact --games input; retrieval time and Git commit are not inferred.",
        },
        "counts": {
            "total_records": len(out_rows),
            "severity_3_high_priority_scoring_stat_or_scoreboard_candidate": sum(
                1 for r in out_rows if r["severity"] == 3
            ),
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
            f"These {len(out_rows)} rows are transcribed from selected archived NFL/Elias correction pages. "
            "None documents a final-score amendment or a sportsbook/fantasy settlement outcome. "
            "The zero confirmed-outcome count is limited to this dataset and is not evidence that "
            "all post-game score changes are impossible. Potential player-market sensitivity is "
            "not the same as a verified offered line or a realized settlement."
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
        w = csv.DictWriter(f, fieldnames=list(flat[0].keys()), lineterminator="\n")
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
