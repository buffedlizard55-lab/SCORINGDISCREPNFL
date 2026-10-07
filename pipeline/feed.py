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
