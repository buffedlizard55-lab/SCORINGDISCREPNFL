"""
detect.py — Core differential detection engine for NFL stat/scoring discrepancies.

THE CENTRAL IDEA
----------------
We cannot rely on the retired NFL correction feed as a live source (see
LIMITATIONS.md). This module compares versioned snapshots of nflverse/nfldata,
a third-party mirror of NFL game results.

A difference in a frozen field for a game already final in the older snapshot
is a *candidate mirror revision* for human review. It is not, by itself, proof
that the NFL/Elias changed its official record.

DESIGN RULES THAT CAME OUT OF EMPIRICAL TESTING (see FINDINGS.md)
-----------------------------------------------------------------
RULE 1 — Only diff rows that were already final in the OLD snapshot.
         Otherwise newly completed games and schedule updates look like
         post-game changes.

RULE 2 — Only diff FROZEN fields for final games (scores, result, total, OT).
         Pre-game fields (spread_line, total_line, moneylines) are volatile and
         are excluded from the post-completion scoreboard comparison.

RULE 3 — Record the old AND new value plus hashes, so any third party can
         independently reproduce the finding. Never store a derived claim
         without the raw values that produced it.

These three rules are enforced in code below and covered by tests/.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Iterable, Iterator

from market_rules import classify, market_outcomes, SEVERITY


# ---------------------------------------------------------------------------
# Fields that are FROZEN once a game is final, per source dataset.
# Anything not listed here is treated as pre-game / volatile and ignored.
# ---------------------------------------------------------------------------
FROZEN_FIELDS_GAMES = [
    "away_score",
    "home_score",
    "result",
    "total",
    "overtime",
]

# Pre-game/volatile fields, listed explicitly so the exclusion is auditable.
VOLATILE_FIELDS_GAMES = [
    "spread_line",
    "total_line",
    "away_moneyline",
    "home_moneyline",
    "away_spread_odds",
    "home_spread_odds",
    "gametime",
    "weekday",
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


SLIM_FIELDS = [
    "game_id",
    "season",
    "week",
    "gameday",
    "away_team",
    "home_team",
] + FROZEN_FIELDS_GAMES


def slim_frozen_csv(rows: dict[str, dict]) -> bytes:
    """
    Reduce a full games dataset to only the columns the detector needs, and
    only rows that have concluded.

    WHY: a raw snapshot of games.csv is ~2.1 MB. Committing one per day would
    add roughly 750 MB a year and would make the snapshot store useless. The
    slim form keeps the primary key, the game-identification columns, and the
    five frozen fields, for final games only — about 100 KB, which is small
    enough to version in git indefinitely and still fully sufficient to run
    every rule in diff_final_records().
    """
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=SLIM_FIELDS, extrasaction="ignore")
    w.writeheader()
    for key in sorted(rows):
        r = rows[key]
        if not is_final(r):
            continue
        r = dict(r)
        r.setdefault("game_id", key)
        w.writerow(r)
    return buf.getvalue().encode("utf-8")


def load_csv_rows(data: bytes | str) -> dict[str, dict]:
    """Load a CSV into {primary_key: row}. Key is `game_id` when present."""
    if isinstance(data, bytes):
        data = data.decode("utf-8-sig", errors="replace")
    rdr = csv.DictReader(io.StringIO(data))
    rows = {}
    for r in rdr:
        key = r.get("game_id") or r.get("player_id") or r.get("id")
        if key is None:
            raise ValueError("dataset has no usable primary key column")
        rows[key] = r
    return rows


def is_final(row: dict) -> bool:
    """
    A game row counts as final when the source has published a non-empty result.
    We deliberately use `result` (source-computed margin) because it is only
    populated once the game has concluded.
    """
    return (row.get("result") or "").strip() not in ("", "None", "NA")


@dataclass
class Change:
    """One field-level difference on one record between two snapshots."""

    key: str
    field_name: str
    old_value: str | None
    new_value: str | None
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def diff_final_records(
    old_rows: dict[str, dict],
    new_rows: dict[str, dict],
    frozen_fields: Iterable[str],
    final_predicate=is_final,
) -> list[Change]:
    """
    Compare two snapshots and return only meaningful, post-completion changes.

    Enforces RULE 1 and RULE 2 from the module docstring.
    """
    frozen = list(frozen_fields)
    out: list[Change] = []

    for key, old in old_rows.items():
        # RULE 1: skip anything that was not already final in the old snapshot.
        if not final_predicate(old):
            continue
        new = new_rows.get(key)
        if new is None:
            # Record disappearing entirely is itself a discrepancy worth flagging.
            out.append(
                Change(key, "<record>", "present", "missing", {"note": "record vanished from snapshot"})
            )
            continue
        for f in frozen:
            ov, nv = old.get(f), new.get(f)
            if ov != nv:
                out.append(
                    Change(
                        key,
                        f,
                        ov,
                        nv,
                        context={
                            "season": old.get("season"),
                            "week": old.get("week"),
                            "away_team": old.get("away_team"),
                            "home_team": old.get("home_team"),
                            "gameday": old.get("gameday"),
                        },
                    )
                )
    return out


def change_to_alert(change: Change, source: str, retrieved_at: str) -> dict:
    """Convert a raw Change into a market-classified alert record."""
    stat = change.field_name
    old_v, new_v = change.old_value, change.new_value

    # Scoreboard fields map onto the discrete "scoring event" rules directly.
    scoreboard = {
        "away_score": "points",
        "home_score": "points",
        "result": "margin",
        "total": "game total",
        "overtime": "overtime flag",
    }

    try:
        of = float(old_v)
        nf = float(new_v)
    except (TypeError, ValueError):
        of = nf = None

    if stat in scoreboard:
        cls = {
            "severity": 3,
            "category": "scoreboard",
            "threshold": None,
            "reason": (
                f"final-game {scoreboard[stat]} changed {old_v} -> {new_v} after the game "
                "had already reached a final state"
            ),
        }
        stat_label = scoreboard[stat]
        away = change.context.get("away_team") or "away team"
        home = change.context.get("home_team") or "home team"
        scoreboard_markets = {
            "away_score": [
                f"{away} team total, if offered",
                "game total (over/under), if offered",
                "point spread, if offered",
                "moneyline if the corrected margin changes the winner, if offered",
            ],
            "home_score": [
                f"{home} team total, if offered",
                "game total (over/under), if offered",
                "point spread, if offered",
                "moneyline if the corrected margin changes the winner, if offered",
            ],
            "result": [
                "point spread, if offered",
                "moneyline if the corrected margin changes the winner, if offered",
            ],
            "total": ["game total (over/under), if offered"],
            "overtime": ["final game-state review; no wager result inferred from this field alone"],
        }
        markets = scoreboard_markets[stat]
    else:
        stat_label = stat
        cls = classify(stat, of, nf) if of is not None and nf is not None else {
            "severity": 1,
            "category": "unparsed",
            "threshold": None,
            "reason": "non-numeric change on a frozen field",
        }
        markets = (
            market_outcomes(stat_label, of, nf)
            if of is not None and nf is not None
            else ["unknown — manual review required"]
        )

    return {
        "alert_id": f"{source}:{change.key}:{stat}",
        "source": source,
        "retrieved_at": retrieved_at,
        "game_id": change.key,
        "context": change.context,
        "stat": stat_label,
        "original_value": old_v,
        "corrected_value": new_v,
        "numeric_change": (None if of is None else round(nf - of, 4)),
        "severity": cls["severity"],
        "severity_label": SEVERITY.get(cls["severity"], "INFO"),
        "category": cls["category"],
        "threshold_crossed": cls["threshold"],
        "reason": cls["reason"],
        "markets_potentially_affected": markets,
        "actually_changed_outcome": None,  # requires scorer/manual confirmation; never asserted
        "verification_status": "detected_by_diff_pending_manual_confirmation",
    }


def build_alert_report(
    changes: list[Change],
    source: str,
    min_severity: int = 1,
) -> dict:
    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    alerts = [change_to_alert(c, source, retrieved_at) for c in changes]
    alerts = [a for a in alerts if a["severity"] >= min_severity]
    alerts.sort(key=lambda a: (-a["severity"], a["game_id"]))

    counts: dict[str, int] = {}
    for a in alerts:
        counts[a["severity_label"]] = counts.get(a["severity_label"], 0) + 1

    return {
        "generated_at": retrieved_at,
        "source": source,
        "min_severity": min_severity,
        "total_alerts": len(alerts),
        "counts_by_severity": counts,
        "alerts": alerts,
        "disclaimer": (
            "Alerts are MACHINE-DETECTED differences between two snapshots of a "
            "third-party mirror of the NFL's official record. Each alert is a "
            "candidate discrepancy, not a confirmed official correction. "
            "Cross-check against an authoritative source before treating it as "
            "official. See LIMITATIONS.md."
        ),
    }


def render_markdown(report: dict) -> str:
    lines = [
        f"# Scoring-discrepancy alerts — {report['generated_at']}",
        "",
        f"**Source:** `{report['source']}`  ",
        f"**Total alerts:** {report['total_alerts']}  ",
        f"**By severity:** " + (", ".join(f"{k}={v}" for k, v in sorted(report["counts_by_severity"].items())) or "none"),
        "",
        "> " + report["disclaimer"],
        "",
    ]
    if not report["alerts"]:
        lines.append("_No qualifying discrepancies detected in this run._")
        return "\n".join(lines) + "\n"

    lines += [
        "| Severity | Game | Field | Original | Corrected | Δ | Category |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for a in report["alerts"]:
        lines.append(
            f"| {a['severity_label']} | {a['game_id']} | {a['stat']} | "
            f"{a['original_value']} | {a['corrected_value']} | {a['numeric_change']} | {a['category']} |"
        )
    lines.append("")
    lines.append("## Detail")
    for a in report["alerts"][:50]:
        lines += [
            f"### {a['game_id']} — {a['stat']} ({a['severity_label']})",
            f"- **Original:** {a['original_value']} → **Corrected:** {a['corrected_value']} (Δ {a['numeric_change']})",
            f"- **Why it matters:** {a['reason']}",
            f"- **Markets potentially affected:** {', '.join(a['markets_potentially_affected']) or 'none identified'}",
            f"- **Verification status:** `{a['verification_status']}`",
            "",
        ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Notifiers. All are OFF unless explicitly configured, so a scheduled run in a
# fork of this repo never spams a third party.
# ---------------------------------------------------------------------------
def notify_stdout(report: dict) -> None:
    print(render_markdown(report))


def notify_file(report: dict, path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_markdown(report))
    with open(os.path.splitext(path)[0] + ".json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def notify_webhook(report: dict, url: str, timeout: int = 15) -> tuple[bool, str]:
    """POST a compact summary to Slack or Discord without storing the URL.

    Slack incoming webhooks require a ``text`` field; Discord incoming
    webhooks require ``content``. A generic endpoint defaults to Slack's
    documented ``text`` shape. Callers must read ``url`` from configuration or
    a secret and must treat a failed response as a delivery failure.
    """
    import urllib.request
    from urllib.parse import urlparse

    if report["total_alerts"] == 0:
        return True, "skipped: no alerts"
    alerts = report["alerts"]
    text = (
        f"*Unconfirmed NFL results-mirror change candidate* — {report['total_alerts']} "
        f"frozen-field change(s) detected in `{report['source']}` at {report['generated_at']}.\n"
        "This is a third-party mirror difference, not confirmation of an official correction "
        "or a wager settlement.\n"
    )
    if report.get("review_url"):
        text += f"Review the workflow report and snapshot artefacts: {report['review_url']}\n"
    for a in alerts[:5]:
        context = a.get("context") or {}
        game_context = " ".join(
            part for part in [
                str(context.get("season") or ""),
                f"W{context['week']}" if context.get("week") else "",
                f"{context['away_team']}@{context['home_team']}"
                if context.get("away_team") and context.get("home_team") else "",
            ] if part
        )
        text += (
            f"• `{a['game_id']}` {game_context} — **{a['stat']}**: "
            f"{a['original_value']} → {a['corrected_value']} ({a['severity_label']})\n"
        )
    if len(alerts) > 5:
        text += f"…and {len(alerts) - 5} more; see the report link above.\n"

    host = (urlparse(url).hostname or "").lower()
    if host == "discord.com" or host == "discordapp.com":
        payload = {"content": text}
    else:
        payload = {"text": text}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = getattr(resp, "status", None) or resp.getcode()
        return 200 <= status < 300, f"http {status}"
