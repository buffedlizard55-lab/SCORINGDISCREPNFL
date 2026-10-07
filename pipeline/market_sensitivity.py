#!/usr/bin/env python3
"""
market_sensitivity.py — Measure distance between final scores and closing lines.

WHY THIS MATTERS
----------------
The brief asks us to distinguish realized outcomes from hypothetical market
sensitivity. This script computes a narrow distance metric for games with a
final score and closing-line values; it does NOT model an actual correction or
settlement.

METHOD
------
For each game:

  home_margin = home_score - away_score
  final_total = home_score + away_score
  margin_line_distance = | |home_margin| - |spread_line| |
  total_line_distance  = | final_total - total_line |

A game is included when either distance is at most the configured threshold
(default: 1 point). This identifies proximity only. The distance is not the
number of points a correction must change, does not specify a direction, and
does not establish a wager outcome.

IMPORTANT FRAMING
-----------------
This measures line proximity, not correction occurrence, probability, or
settlement. No score correction or wager is inferred. The sign convention of
the `spread_line` field is not resolved here, so equal absolute margin/spread
magnitudes are NOT labeled as confirmed pushes. The result is a sensitivity
screen to prioritize review, not a count of affected games or bets.

The score-integrity study compares four selected vintages of a third-party
mirror and found no difference in five frozen fields for rows already final in
the older snapshots. That limited result does not establish that NFL scores
never change or estimate how often corrections affect a market.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def sha256_file(path: str) -> str:
    """Hash the exact --games input without loading it all into memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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

        margin_line_within_threshold = margin_gap <= threshold
        total_line_within_threshold = total_gap <= threshold
        if not (margin_line_within_threshold or total_line_within_threshold):
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
                "zero_margin_line_distance": margin_gap == 0,
                "zero_total_line_distance": total_gap == 0,
                "margin_line_within_threshold": margin_line_within_threshold,
                "total_line_within_threshold": total_line_within_threshold,
                "note": (
                    "Absolute score-margin magnitude equals absolute spread-line magnitude. "
                    "Spread sign/side and operator settlement are not inferred."
                    if margin_gap == 0
                    else "Included because the final margin or total is within the configured "
                    "distance threshold of a closing-line value; no correction or settlement is inferred."
                ),
            }
        )

    summary = {
        "games_considered_with_scores_and_lines": considered,
        "games_within_distance_threshold_of_a_line": len(out),
        "within_threshold_share_pct": round(100.0 * len(out) / considered, 2) if considered else 0.0,
        "distance_threshold_points": threshold,
        "zero_margin_line_distance_matches": sum(1 for g in out if g["zero_margin_line_distance"]),
        "zero_total_line_distance_matches": sum(1 for g in out if g["zero_total_line_distance"]),
        "framing": (
            "Distance-based sensitivity screen only. A row means the final score margin or total "
            "is within the configured distance of a closing-line value. It does not mean a "
            "correction occurred, that a particular side pushed or won, or that a wager settled. "
            "See data/evidence/score_integrity_study.json and LIMITATIONS.md."
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
    summary["game_data_input"] = {
        "source": "nflverse/nfldata data/games.csv (third-party mirror)",
        "source_url": "https://github.com/nflverse/nfldata/blob/master/data/games.csv",
        "input_basename": os.path.basename(args.games),
        "sha256": sha256_file(args.games),
        "bytes": os.path.getsize(args.games),
        "retained_by_builder": False,
        "note": "Hash identifies the exact --games input; retrieval time and Git commit are not inferred.",
    }

    os.makedirs(args.outdir, exist_ok=True)
    stem = "market_sensitivity_" + "_".join(str(s) for s in sorted(seasons))
    csv_path = os.path.join(args.outdir, stem + ".csv")
    json_path = os.path.join(args.outdir, stem + ".json")

    cols = list(rows[0].keys()) if rows else []
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "games": rows}, f, indent=2)

    print(json.dumps(summary, indent=2))
    print(f"wrote {csv_path}\nwrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
