#!/usr/bin/env python3
"""
market_sensitivity.py — Which games were VULNERABLE to a scoring correction?

WHY THIS MATTERS
----------------
The brief asks us to separate corrections that ACTUALLY changed an official
outcome from corrections that merely had the POTENTIAL to change a market.
The second half of that cannot be answered by looking at corrections alone:
you also have to know which games were close enough to a market line that any
scoreboard change would have flipped a bet.

This script computes exactly that, from real closing lines, for every game in
the nflverse/nfldata record. Output is a reproducible table of
"correction-sensitive" games.

METHOD (and its arithmetic, so anyone can recompute it by hand)
---------------------------------------------------------------
For each game we take the final scores and the closing lines:

  result     = home_score - away_score            (home margin)
  total      = home_score + away_score
  abs_spread = |spread_line|                      (magnitude of the handicap)

  margin_gap = | abs(result) - abs_spread |
      How many points the final margin sat away from the closing spread.
      margin_gap == 0  => the game PUSHED on the spread. A scoring correction
                          of even 1 point creates a winner where there was none.
      margin_gap == 1  => a 1-point correction flips the spread result.
      margin_gap == n  => a correction of >= n points flips it.

  total_gap  = | total - total_line |
      Same idea for the game total (over/under).

A game is flagged "correction-sensitive" when margin_gap <= threshold or
total_gap <= threshold for a configurable threshold (default 1 point, i.e.
"any single scoring correction could have flipped this market").

IMPORTANT FRAMING
-----------------
This measures SENSITIVITY, not occurrence. It says "a correction here would have
mattered". It does not claim a correction happened. Combined with the
score-integrity study (data/evidence/score_integrity_study.json), which found
zero post-completion score revisions across 28,323 game snapshots, the correct
reading is:

    This is the set of games where the failure mode COULD have bitten.
    Empirically it did not bite, because NFL final scores are not revised
    after the game. Player-level markets are where corrections do land.

SIGN CONVENTION CAVEAT
----------------------
The sign convention of nflverse's `spread_line` field relative to home/away has
been described inconsistently in secondary sources. This script therefore uses
ONLY the magnitude |spread_line|, which is correct under either convention.
That was a deliberate design choice to avoid asserting something we had not
independently verified.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def to_float(v):
    if v is None:
        return None
    v = str(v).strip()
    if v in ("", "None", "NA", "nan"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def analyse(path: str, seasons: set[int] | None, threshold: float = 1.0) -> tuple[list[dict], dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    out: list[dict] = []
    considered = 0
    for r in rows:
        try:
            season = int(r["season"])
        except (KeyError, ValueError, TypeError):
            continue
        if seasons and season not in seasons:
            continue

        away, home = to_float(r.get("away_score")), to_float(r.get("home_score"))
        spread, tline = to_float(r.get("spread_line")), to_float(r.get("total_line"))
        if away is None or home is None or spread is None or tline is None:
            continue  # not played, or no closing line — cannot assess

        considered += 1
        result = home - away
        total = home + away
        margin_gap = abs(abs(result) - abs(spread))
        total_gap = abs(total - tline)

        spread_sensitive = margin_gap <= threshold
        total_sensitive = total_gap <= threshold
        if not (spread_sensitive or total_sensitive):
            continue

        out.append(
            {
                "game_id": r.get("game_id"),
                "season": season,
                "week": r.get("week"),
                "gameday": r.get("gameday"),
                "away_team": r.get("away_team"),
                "home_team": r.get("home_team"),
                "away_score": int(away),
                "home_score": int(home),
                "final_margin_home": int(result),
                "final_total": int(total),
                "closing_spread": spread,
                "closing_total": tline,
                "margin_gap_points": round(margin_gap, 2),
                "total_gap_points": round(total_gap, 2),
                "pushed_on_spread": margin_gap == 0,
                "pushed_on_total": total_gap == 0,
                "spread_sensitive": spread_sensitive,
                "total_sensitive": total_sensitive,
                "min_correction_points_to_flip_spread": None if not spread_sensitive else round(margin_gap, 2),
                "min_correction_points_to_flip_total": None if not total_sensitive else round(total_gap, 2),
                "note": (
                    "A scoring correction of any size would create a winner where the game pushed."
                    if margin_gap == 0
                    else "Closest market outcome to the final score; listed because a correction "
                    "within the stated gap would have flipped a spread/total market."
                ),
            }
        )

    summary = {
        "games_considered_with_scores_and_lines": considered,
        "correction_sensitive_games": len(out),
        "sensitive_share_pct": round(100.0 * len(out) / considered, 2) if considered else 0.0,
        "threshold_points": threshold,
        "exact_spread_pushes": sum(1 for g in out if g["pushed_on_spread"]),
        "exact_total_pushes": sum(1 for g in out if g["pushed_on_total"]),
        "framing": (
            "Sensitivity only. A row means a scoreboard correction WOULD have changed a market "
            "outcome. It does not mean one occurred — see data/evidence/score_integrity_study.json."
        ),
    }
    return out, summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", required=True, help="path to nfldata games.csv")
    ap.add_argument("--seasons", default="2025,2026")
    ap.add_argument("--threshold", type=float, default=1.0)
    ap.add_argument("--outdir", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
    args = ap.parse_args()

    seasons = {int(s) for s in args.seasons.split(",") if s.strip()}
    rows, summary = analyse(args.games, seasons, args.threshold)

    os.makedirs(args.outdir, exist_ok=True)
    stem = "market_sensitivity_" + "_".join(str(s) for s in sorted(seasons))
    csv_path = os.path.join(args.outdir, stem + ".csv")
    json_path = os.path.join(args.outdir, stem + ".json")

    cols = list(rows[0].keys()) if rows else []
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "games": rows}, f, indent=2)

    print(json.dumps(summary, indent=2))
    print(f"wrote {csv_path}\nwrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
