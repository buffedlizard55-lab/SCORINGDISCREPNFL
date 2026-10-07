"""
market_rules.py — Market-impact rule table for NFL stat corrections.

WHY THIS FILE EXISTS
--------------------
Whether a stat correction matters to a wager depends on the actual market,
line, timing, and operator rules. This module provides a screening heuristic,
not a verified market inventory: a move from 42 -> 43 may be worth checking
against a line if one was offered, and 299 -> 301 crosses the project's 300-yard
review marker without asserting that a bonus market existed. The rules help
prioritize human review; they do not settle bets.

SOURCING DISCIPLINE
-------------------
This rule table flags candidate relevance for player/team scoring stats,
project-defined candidate line-market categories, and round-number review
thresholds. The line-market categories are a heuristic, not verified proof of
what books offered. A player-level stat correction can change attribution
without changing points on the board; direct scoreboard fields are detected
separately in detect.py. Round numbers are markers, not a claim that a
particular book offered a market at that value.

This file deliberately does NOT invent sportsbook lines. Actual per-game
player-prop lines are not available from a free, verified, redistributable feed
in this project, which is called out explicitly in LIMITATIONS.md.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. Player/team scoring-stat corrections.
#    These can be decisive for a player scoring market, but a stat-line change
#    alone does NOT prove that the scoreboard changed: the correction might
#    re-attribute an unchanged play. Direct scoreboard fields are classified in
#    detect.py, independently from player-stat categories.
#    `severity` = 3 (highest candidate priority), with score impact unasserted.
# ---------------------------------------------------------------------------
PLAYER_SCORING_STATS = {
    "touchdowns": "player_touchdown",
    "passing touchdowns": "player_passing_touchdown",
    "rushing touchdowns": "player_rushing_touchdown",
    "receiving touchdowns": "player_receiving_touchdown",
    "return touchdowns": "player_return_touchdown",
    "fumble recovery touchdowns": "player_fumble_recovery_touchdown",
    "interception return touchdowns": "player_interception_return_touchdown",
    "kickoff return touchdowns": "player_kickoff_return_touchdown",
    "punt return touchdowns": "player_punt_return_touchdown",
    "kickoff and punt return touchdowns": "player_return_touchdown",
    "two point conversions": "player_two_point_conversion",
    "two-point conversions": "player_two_point_conversion",
    "extra points made": "player_extra_point_made",
    "field goals made": "player_field_goal_made",
    "safeties": "team_safety",
    "defensive touchdowns": "team_defensive_touchdown",
}

# ---------------------------------------------------------------------------
# 1b. CANDIDATE LINE-MARKET STATS.
#     This project provisionally treats these stat categories as candidates for
#     over/under review. It does NOT assert that every sportsbook offers each
#     category, that a particular game had a line, or that all lines are X.5.
#     Under a hypothetical half-point line between adjacent integer values, a
#     one-unit change could cross it. Thus a move of 182 -> 181 passing yards is
#     not dismissed solely because it misses a round-number marker. This is a
#     screening heuristic, not a verified market inventory.
#
#     Per-game lines are not available here. Every generated market label is
#     explicitly conditional (`if offered`); do not infer a specific book,
#     line, price, wager, or settlement from this rule table.
# ---------------------------------------------------------------------------
LINE_PRICED_STATS = {
    "passing yards",
    "rushing yards",
    "receiving yards",
    "receptions",
    "targets",
    "rushing attempts",
    "passing attempts",
    "passing completions",
    "kickoff and punt return yards",
    "sacks",
    "every time sacked",
    "interceptions",
    "interceptions thrown",
    "fumbles lost",
    "fumbles recovery",
    "fumbles recovered",
    "forced fumbles",
    "yards allowed",
    "points allowed",
    "field goals made",
    "field goals attempted",
    "extra points made",
    "extra points attempted",
    "touchdowns",
}

# ---------------------------------------------------------------------------
# 2. Round-number statistical thresholds.
#    A correction is "threshold-crossing" if the original and corrected values
#    sit on opposite sides of a value in this list for that stat.
#    Also feeds the milestone/yardage-bonus market (300-yd bonus etc.).
#    `severity` = 2.
# ---------------------------------------------------------------------------
ROUND_NUMBER_THRESHOLDS = {
    "passing yards": [100, 150, 200, 250, 300, 350, 400, 425, 450, 500],
    "rushing yards": [25, 50, 75, 100, 125, 150, 175, 200, 250],
    "receiving yards": [25, 50, 75, 100, 125, 150, 175, 200, 250],
    "receptions": [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15],
    "rushing attempts": [5, 10, 15, 20, 25, 30],
    "kickoff and punt return yards": [50, 100, 150, 200],
    "sacks": [1, 2, 3, 4, 5, 6],
    "yards allowed": [200, 250, 300, 350, 400, 450, 500],
    "points allowed": [0, 6, 10, 14, 17, 21, 24, 28, 35],
}

# ---------------------------------------------------------------------------
# 3. Stats that are market-relevant but have no clean round-number rule.
#    Kept at severity 1 so they still appear in the feed, flagged as
#    "relevant but not threshold-crossing".
# ---------------------------------------------------------------------------
OTHER_RELEVANT_STATS = {
    "interceptions": "turnover",
    "interceptions thrown": "turnover",
    "fumbles lost": "turnover",
    "fumble recovery touchdowns": "touchdown",
    "forced fumbles": "turnover",
    "fumbles recovery": "turnover",
    "fumbles recovered": "turnover",
    "targets": "volume",
    "every time sacked": "sack",
    "tackle": "idp",
    "tackles": "idp",
    "assisted tackles": "idp",
    "games played": "eligibility",
    "field goals made 0-19": "field_goal",
    "field goals made 20-29": "field_goal",
    "field goals made 30-39": "field_goal",
    "field goals made 40-49": "field_goal",
    "field goals made 50+": "field_goal",
    "passing attempts": "volume",
    "passing completions": "volume",
}

SEVERITY = {3: "HIGH", 2: "MEDIUM", 1: "LOW", 0: "INFO"}


def _norm(stat: str) -> str:
    return " ".join(stat.strip().lower().replace("_", " ").split())


def crosses_threshold(stat: str, old_value: float, new_value: float) -> tuple[bool, float | None]:
    """
    Return (crossed, threshold). `crossed` is True when old and new sit on
    opposite sides of some round-number threshold for this stat.

    Project rule: flag when one value is strictly below the marker and the
    other is at or above it (`lo < threshold <= hi`). This is a consistent
    review boundary, not a claim about any book's line or settlement rule.
    For example, 99 -> 100 and 100 -> 99 are flagged; 100 -> 101 is not.
    """
    ths = ROUND_NUMBER_THRESHOLDS.get(_norm(stat))
    if not ths:
        return False, None
    lo, hi = (old_value, new_value) if old_value <= new_value else (new_value, old_value)
    for t in ths:
        if lo < t <= hi and lo != hi:
            return True, float(t)
    return False, None


def classify(stat: str, old_value: float, new_value: float) -> dict:
    """
    Classify a single correction row.

    Returns a dict with severity, category, threshold info and a short reason.
    Pure function: no I/O, no globals mutated. Trivially unit-testable.
    """
    s = _norm(stat)
    if old_value == new_value:
        return {
            "severity": 0,
            "category": "no_change",
            "threshold": None,
            "reason": "original and corrected value are identical",
        }

    if s in PLAYER_SCORING_STATS:
        return {
            "severity": 3,
            "category": PLAYER_SCORING_STATS[s],
            "threshold": None,
            "reason": (
                f"scoring-related statistic changed ({old_value:g} -> {new_value:g}); "
                "may affect a player/team scoring market, but this row alone does not "
                "establish a scoreboard change or prove that points were added or removed"
            ),
        }

    crossed, t = crosses_threshold(s, old_value, new_value)
    if crossed:
        return {
            "severity": 2,
            "category": "threshold_crossing",
            "threshold": t,
            "reason": (
                f"{stat} moved {old_value:g} -> {new_value:g}, crossing the project's "
                f"round-number review threshold of {t:g}; no specific market is asserted"
            ),
        }

    if s in LINE_PRICED_STATS:
        return {
            "severity": 2,
            "category": "line_priced_change",
            "threshold": None,
            "reason": (
                f"{stat} moved {old_value:g} -> {new_value:g}; this project flags the category "
                "for line-market review. A hypothetical half-point line between these values "
                "could be crossed if such a market was actually offered"
            ),
        }

    if s in OTHER_RELEVANT_STATS:
        return {
            "severity": 1,
            "category": OTHER_RELEVANT_STATS[s],
            "threshold": None,
            "reason": f"{stat} moved {old_value:g} -> {new_value:g}; market-relevant but not threshold-crossing",
        }

    return {
        "severity": 0,
        "category": "out_of_scope",
        "threshold": None,
        "reason": f"{stat} moved {old_value:g} -> {new_value:g}; not a defined market-relevant stat",
    }


def market_outcomes(stat: str, old_value: float, new_value: float) -> list[str]:
    """List possible markets without inferring an unobserved scoreboard change."""
    c = classify(stat, old_value, new_value)
    s = _norm(stat)
    out: list[str] = []

    if c["category"] in PLAYER_SCORING_STATS.values():
        if "passing" in s:
            out.append("player passing-touchdown markets, if offered")
        elif "rushing" in s:
            out.append("player rushing-touchdown / anytime-touchdown markets, if offered")
        elif "receiving" in s:
            out.append("player receiving-touchdown / anytime-touchdown markets, if offered")
        elif "return" in s or "recovery" in s or "defensive touchdown" in s:
            out.append("player/defense touchdown markets, if offered")
        elif "field goal" in s:
            out.append("kicker field-goals-made markets, if offered")
        elif "extra point" in s:
            out.append("kicker extra-points-made markets, if offered")
        elif "two" in s:
            out.append("player two-point-conversion markets, if offered")
        elif "safety" in s:
            out.append("team safety/scoring markets, if offered")
        else:
            out.append("player touchdown / anytime-touchdown markets, if offered")
        out.append("Scoreboard, team-total, game-total and spread impact is unproven unless the game-level score record also changes.")
        return out

    if c["severity"] == 2:
        if c.get("category") == "threshold_crossing" and c.get("threshold") is not None:
            out.append(f"{s} over/under around the {c['threshold']:g} threshold, if offered")
            if "yard" in s:
                out.append(f"{s} milestone/yardage-bonus markets, if offered")
            else:
                out.append(f"{s} threshold-based market or bonus, if offered")
        else:
            out.append(f"{s} over/under (a half-point line between {min(old_value, new_value):g} and {max(old_value, new_value):g}, if offered)")
            if "yard" in s:
                out.append(f"{s} milestone/yardage-bonus markets, if offered")
        out.append("same-game parlay / combo legs containing this stat, if offered")
    elif c["severity"] == 1:
        out.append(f"{s} over/under or fantasy/IDP scoring, if offered")
    return out
