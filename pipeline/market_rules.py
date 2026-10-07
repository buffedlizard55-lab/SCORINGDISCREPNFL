"""
market_rules.py — Market-impact rule table for NFL stat corrections.

WHY THIS FILE EXISTS
--------------------
A stat correction only *matters* for a market if it crosses a line that somebody
could have bet, or flips a discrete scoring event. A 1-yard rushing change from
42 -> 43 is noise. A change from 299 -> 301 passing yards crosses the very common
300-yard bonus threshold. This module encodes those thresholds as data so the
detector can label each correction by market relevance instead of a human
eyeballing every row.

SOURCING DISCIPLINE
-------------------
Every rule below is either:
  (a) a DISCRETE SCORING EVENT (touchdown, field goal, extra point, two-point
      conversion, safety, defensive score). These are binary: they either
      happened or they did not. Changing one changes points on the scoreboard
      and therefore team totals / game totals / player TD markets. No threshold
      judgement is required.
  (b) a ROUND-NUMBER STATISTICAL THRESHOLD that is widely offered as a betting
      line or a DFS/fantasy bonus. These are the conventional round numbers.

This file deliberately does NOT invent sportsbook lines. It encodes only
(a) discrete events and (b) conventional round-number bonuses. Actual per-game
player-prop lines are NOT available from any free, verifiable, redistributable
feed, which is called out explicitly in LIMITATIONS.md rather than guessed at.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. Discrete scoring events.
#    Any correction to one of these can change the scoreboard, the game total,
#    the team total, the spread, or a player's TD/points market.
#    `severity` = 3 (highest).
# ---------------------------------------------------------------------------
SCORING_EVENT_STATS = {
    # Offensive scoring
    "touchdowns": "touchdown",
    "passing touchdowns": "touchdown",
    "rushing touchdowns": "touchdown",
    "receiving touchdowns": "touchdown",
    "return touchdowns": "touchdown",
    "fumble recovery touchdowns": "touchdown",
    "interception return touchdowns": "touchdown",
    "kickoff return touchdowns": "touchdown",
    "punt return touchdowns": "touchdown",
    "two point conversions": "two_point",
    "two-point conversions": "two_point",
    "extra points made": "extra_point",
    "extra points attempted": "extra_point",
    # Kicking
    "field goals made": "field_goal",
    "field goals attempted": "field_goal",
    # Defensive scoring
    "safeties": "safety",
    "defensive touchdowns": "touchdown",
}

# ---------------------------------------------------------------------------
# 1b. LINE-PRICED STATS.
#     These are stats that sportsbooks price as over/under lines at essentially
#     every integer value, with the line almost always quoted at X.5.
#     Consequence (and the reason this category exists): for these stats ANY
#     integer change of >=1 can flip an over/under. A move of 182 -> 181 passing
#     yards is NOT harmless simply because 182 is not a round number — it can
#     flip a 181.5 line. Treating only round numbers as sensitive was a real bug
#     found during review, so these are floored at severity 2.
#
#     This deliberately does NOT claim that a prop line existed at any specific
#     value. It claims only that the stat is line-priced, therefore a one-unit
#     change is capable of crossing a line. Per-game lines are not freely
#     redistributable, which is stated in LIMITATIONS.md rather than guessed.
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

# ---------------------------------------------------------------------------
# 4. Stats that are explicitly NOT market-relevant under our scope.
#    These are recorded so the pipeline can drop them without a human deciding.
# ---------------------------------------------------------------------------
NON_MARKET_STATS = {
    "kickoff and punt return touchdowns",  # duplicate guard; see SCORING_EVENT_STATS
    "yardage",
}

SEVERITY = {3: "HIGH", 2: "MEDIUM", 1: "LOW", 0: "INFO"}


def _norm(stat: str) -> str:
    return " ".join(stat.strip().lower().replace("_", " ").split())


def crosses_threshold(stat: str, old_value: float, new_value: float) -> tuple[bool, float | None]:
    """
    Return (crossed, threshold). `crossed` is True when old and new sit on
    opposite sides of some round-number threshold for this stat.

    Exactness rule: if a value lands exactly ON a threshold we require the
    other value to be beyond it, because sportsbook lines are typically
    X.5 and only a strict crossing changes the outcome. A move from 100 -> 99
    does cross the 100 line, so it is reported.
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

    if s in SCORING_EVENT_STATS:
        return {
            "severity": 3,
            "category": SCORING_EVENT_STATS[s],
            "threshold": None,
            "reason": (
                f"discrete scoring event changed ({old_value:g} -> {new_value:g}); "
                "can change scoreboard, game total, team total, spread or a TD market"
            ),
        }

    crossed, t = crosses_threshold(s, old_value, new_value)
    if crossed:
        return {
            "severity": 2,
            "category": "threshold_crossing",
            "threshold": t,
            "reason": (
                f"{stat} moved {old_value:g} -> {new_value:g}, crossing the "
                f"round-number market threshold of {t:g}"
            ),
        }

    if s in LINE_PRICED_STATS:
        return {
            "severity": 2,
            "category": "line_priced_change",
            "threshold": None,
            "reason": (
                f"{stat} moved {old_value:g} -> {new_value:g}; this is a line-priced stat, so a "
                "change of this size is capable of crossing an over/under quoted at a half point"
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
    """Human-readable list of markets that could be affected."""
    c = classify(stat, old_value, new_value)
    s = _norm(stat)
    out: list[str] = []
    if c["severity"] == 3:
        out.append("game total (over/under)")
        out.append("team total")
        out.append("point spread")
        out.append("moneyline (when the change flips the margin)")
        if "passing" in s:
            out.append("player passing touchdown market")
        if "rushing" in s:
            out.append("player rushing touchdown market / anytime TD")
        if "receiving" in s:
            out.append("player receiving touchdown market / anytime TD")
        if "field goal" in s:
            out.append("player field goals made market")
        if "extra point" in s:
            out.append("player extra points market")
        if "safety" in s:
            out.append("team total / game total precision markets")
    elif c["severity"] == 2:
        if c.get("category") == "threshold_crossing" and c.get("threshold") is not None:
            out.append(f"{s} over/under (line near {c['threshold']:g})")
            out.append(f"{s} statistical milestone / yardage bonus")
        else:
            out.append(f"{s} over/under (any half-point line between {min(old_value, new_value):g} and {max(old_value, new_value):g})")
            out.append(f"{s} statistical milestone / yardage bonus if a round number sits inside that range")
        out.append("same-game parlay / same-game combo legs containing this stat")
    elif c["severity"] == 1:
        out.append(f"{s} over/under")
    return out
