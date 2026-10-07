"""
feed.py — The comparison feed: an append-only log of completed diff runs.

WHY THIS EXISTS
---------------
The brief's everyday-use requirement is explicit:

    "It should solve the problem of having to manually check everything
     ourselves and having an up to date current feed."

A detector that only speaks when it finds something is not a feed. This log
records each completed snapshot comparison passed to `append_run`, INCLUDING
clean comparisons, with the input hashes and result. It is not a workflow-health
log: baseline-only, failed or aborted runs may not create an entry. Check the
Actions history to see whether the latest scheduled attempt succeeded.

HONESTY RULES
-------------
* A recorded run is a statement about the MIRROR we diff, not about the NFL's
  internal records (LIMITATIONS.md #5).
* Alerts are machine-detected candidates. Every alert keeps
  verification_status="detected_by_diff_pending_manual_confirmation" and
  actually_changed_outcome=null. The machine detects; a human confirms.
* A clean run is NOT evidence that the NFL made no corrections that week. It
  means: in these two snapshots of this mirror, no frozen field on any
  already-final game differed.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import pathlib

MAX_RUNS = 200

META = {
    "what_this_is": (
        "Log of completed differential comparisons against a versioned "
        "third-party mirror of the NFL record. Clean comparisons are recorded "
        "too; baseline-only, failed and aborted workflow attempts may not appear. "
        "This is not a workflow-health log."
    ),
    "what_a_recorded_alert_is": (
        "A machine-detected difference between two snapshots. It is a CANDIDATE "
        "discrepancy, not a confirmed official NFL/Elias correction. Cross-check "
        "against an authoritative source before treating it as official."
    ),
    "what_a_clean_run_means": (
        "No frozen field on any already-final game differed between the two "
        "snapshots compared. It is NOT evidence that the NFL issued no "
        "corrections in that window."
    ),
    "source": "nflverse/nfldata data/games.csv (third-party mirror, not the NFL)",
    "see": ["LIMITATIONS.md", "RECOMMENDATIONS.md"],
}


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_entry(report: dict, old_path: str, new_path: str) -> dict:
    """Flatten one detection report into a compact, self-describing feed entry."""
    inputs = report.get("inputs", {})
    old_meta, new_meta = inputs.get("old", {}), inputs.get("new", {})
    total = int(report.get("total_alerts", 0))
    return {
        "checked_at": report.get("generated_at") or _now(),
        "status": "ALERTS" if total else "clean",
        "alerts_total": total,
        "counts_by_severity": report.get("counts_by_severity", {}),
        "records_compared": inputs.get("old_final_records"),
        "old_snapshot": old_path,
        "new_snapshot": new_path,
        "old_sha256": old_meta.get("sha256"),
        "new_sha256": new_meta.get("sha256"),
        "identical_inputs": old_meta.get("sha256") == new_meta.get("sha256"),
        "min_severity": report.get("min_severity"),
        "rules_applied": report.get("rules_applied", []),
        "alerts": report.get("alerts", []),
        "verification_status": (
            "detected_by_diff_pending_manual_confirmation" if total else "no_change_detected"
        ),
        "actually_changed_outcome": None,
    }


def load(feed_path: str | os.PathLike) -> dict:
    p = pathlib.Path(feed_path)
    if not p.exists():
        return {"meta": META, "last_checked_at": None, "runs": []}
    return json.loads(p.read_text(encoding="utf-8"))


def append_run(report: dict, old_path: str, new_path: str, feed_path: str | os.PathLike) -> dict:
    """Append one run (newest first), cap the history, and return the new feed."""
    feed = load(feed_path)
    feed["meta"] = META
    entry = run_entry(report, old_path, new_path)

    runs = feed.get("runs", [])
    # Re-running the same snapshot pair must not duplicate the entry.
    runs = [
        r for r in runs
        if not (r.get("old_snapshot") == entry["old_snapshot"]
                and r.get("new_snapshot") == entry["new_snapshot"])
    ]
    runs.insert(0, entry)
    feed["runs"] = runs[:MAX_RUNS]

    alert_runs = [r for r in feed["runs"] if r["status"] == "ALERTS"]
    feed["last_checked_at"] = feed["runs"][0]["checked_at"] if feed["runs"] else None
    feed["summary"] = {
        "runs_recorded": len(feed["runs"]),
        "runs_with_alerts": len(alert_runs),
        "runs_clean": len(feed["runs"]) - len(alert_runs),
        "total_alerts": sum(r["alerts_total"] for r in feed["runs"]),
        "first_run": feed["runs"][-1]["checked_at"] if feed["runs"] else None,
        "last_run": feed["last_checked_at"],
    }
    feed["latest"] = feed["runs"][0] if feed["runs"] else None

    pathlib.Path(feed_path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(feed_path).write_text(
        json.dumps(feed, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return feed


# ---------------------------------------------------------------------------
# Monitor health — the failure mode where "nothing to report" means "we never
# looked".
#
# WHY THIS EXISTS
# ---------------
# The feed above records COMPLETED comparisons. If the scheduled workflow is
# disabled, delayed, lacks write permission, cannot fetch the source, or fails
# to publish, no entry appears and the page keeps showing the last successful
# run as though it were current. A monitoring system whose failure mode is
# "looks fine" is the worst kind, so attempt outcomes are recorded separately
# and the site renders them.
# ---------------------------------------------------------------------------

HEALTH_META = {
    "what_this_is": (
        "Outcome of the most recent scheduled detection ATTEMPT, whether it "
        "succeeded or failed. The comparison feed records completed comparisons "
        "only; this file records attempts, so a broken schedule is visible "
        "instead of silently showing a stale result as current."
    ),
    "how_to_read_status": {
        "ok": "the last attempt collected, compared and published successfully",
        "baseline": "the last attempt collected a first snapshot; nothing to compare yet",
        "failed": "the last attempt did not complete; the displayed result may be stale",
        "unknown": "no attempt has been recorded yet",
    },
    "see": ["LIMITATIONS.md", "RECOMMENDATIONS.md"],
}

VALID_STATUSES = ("ok", "baseline", "failed", "unknown")


def load_health(health_path: str | os.PathLike) -> dict:
    p = pathlib.Path(health_path)
    if not p.exists():
        return {"meta": HEALTH_META, "status": "unknown", "last_attempt": None,
                "last_success": None, "last_failure": None, "consecutive_failures": 0}
    return json.loads(p.read_text(encoding="utf-8"))


def record_attempt(
    health_path: str | os.PathLike,
    status: str,
    detail: str = "",
    attempted_at: str | None = None,
) -> dict:
    """
    Record the outcome of one scheduled attempt.

    `status` must be one of VALID_STATUSES; anything else is a programming
    error and is rejected rather than written, because a misspelled status
    would silently read as "nothing wrong" on the page.
    """
    if status not in VALID_STATUSES:
        raise ValueError(f"status must be one of {VALID_STATUSES}, got {status!r}")

    h = load_health(health_path)
    h["meta"] = HEALTH_META
    h["status"] = status
    h["last_attempt"] = attempted_at or _now()
    h["detail"] = detail

    if status == "ok":
        h["last_success"] = h["last_attempt"]
        h["consecutive_failures"] = 0
    elif status == "failed":
        h["last_failure"] = h["last_attempt"]
        h["consecutive_failures"] = int(h.get("consecutive_failures", 0)) + 1

    pathlib.Path(health_path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(health_path).write_text(
        json.dumps(h, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return h


def health_age_hours(health: dict, now: _dt.datetime | None = None) -> float | None:
    """Hours since the last recorded attempt, or None if there has never been one."""
    stamp = health.get("last_attempt") or health.get("last_success")
    if not stamp:
        return None
    try:
        then = _dt.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None
    now = now or _dt.datetime.now(_dt.timezone.utc)
    return round((now - then).total_seconds() / 3600.0, 2)
