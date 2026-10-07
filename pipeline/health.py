#!/usr/bin/env python3
"""
health.py — answers "is the monitor actually running?", separately from
"did the monitor find anything?".

WHY THIS EXISTS
---------------
A detection feed that only records successful comparisons has a failure mode
worse than a false positive: it goes quiet. If the schedule is disabled, the
runner cannot reach the source, the comparison throws, or the commit that
persists the feed is rejected, the site keeps showing the last good run and
looks current. Nobody is notified, and nobody knows they were not notified.

So health is computed from artefacts that exist *independently of the detector's
own opinion*: the feed, the snapshot store, the delivery log and the published
copies. Every check reports one of:

    ok        — the check passed
    warn      — degraded; the monitor is working but something needs a look
    fail      — the monitor cannot be trusted right now
    unknown   — the evidence needed to decide is absent (never reported as ok)

"unknown" is never folded into "ok". That is the single most important rule here.

WHAT THIS IS NOT
----------------
Not a probe of the NFL, not a statement about corrections, and not a substitute
for the Actions run history. It reports the state of *this repository's*
monitoring artefacts at the moment it runs.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import notify as notify_mod  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED_PATH = os.path.join(REPO_ROOT, "data", "alerts", "feed.json")
DELIVERY_PATH = os.path.join(REPO_ROOT, "data", "alerts", "deliveries.json")
SNAPSHOT_ROOT = os.path.join(REPO_ROOT, "snapshots", "nfldata_games")
OUT_PATH = os.path.join(REPO_ROOT, "data", "alerts", "health.json")

# The scheduled workflow polls daily in season. 40h gives one missed run of
# slack before we call the monitor stale; a project choice, not a source SLA.
DEFAULT_STALE_AFTER_HOURS = 40.0
# Three consecutive comparisons of byte-identical inputs means the detector has
# not actually observed the source move. That is worth a look, not an alarm.
DEFAULT_IDENTICAL_INPUT_STREAK_WARN = 3

META = {
    "what_this_is": (
        "Self-assessment of the monitoring artefacts in this repository: the "
        "comparison feed, the snapshot store, the delivery log and the published "
        "site copies. It answers 'is the monitor running?', not 'did the NFL "
        "change anything?'."
    ),
    "status_values": {
        "ok": "every check passed",
        "warn": "the monitor is working but at least one check is degraded",
        "fail": "the monitor cannot currently be trusted; see checks[]",
        "unknown": "the evidence needed to decide is absent; never reported as ok",
    },
    "what_it_cannot_see": (
        "A workflow that is disabled, queued or cancelled by GitHub, a runner "
        "outage, or a notification that was accepted by an endpoint and never "
        "read. Check the Actions history for attempt-level truth."
    ),
    "see": ["ALERT_SYSTEM_FEASIBILITY.md", "LIMITATIONS.md", ".github/workflows/health.yml"],
}


def _parse(ts: str | None) -> _dt.datetime | None:
    if not ts:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            d = _dt.datetime.strptime(ts, fmt)
            return d if d.tzinfo else d.replace(tzinfo=_dt.timezone.utc)
        except ValueError:
            continue
    try:  # fromisoformat handles "+00:00" and "Z" on 3.11+
        d = _dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


def _age_hours(ts: str | None, now: _dt.datetime | None = None) -> float | None:
    d = _parse(ts)
    if d is None:
        return None
    now = now or _dt.datetime.now(_dt.timezone.utc)
    return round((now - d).total_seconds() / 3600.0, 2)


def check(name: str, status: str, detail: str, **extra) -> dict:
    return {"check": name, "status": status, "detail": detail, **extra}


def snapshot_manifests(root: str = SNAPSHOT_ROOT) -> list[dict]:
    """Newest-first manifests from the snapshot store."""
    out = []
    p = pathlib.Path(root)
    if not p.exists():
        return out
    for d in sorted((x for x in p.iterdir() if x.is_dir()), key=lambda x: x.name, reverse=True):
        for m in d.glob("*.manifest.json"):
            try:
                data = json.loads(m.read_text(encoding="utf-8"))
            except Exception as e:
                out.append({"dir": d.name, "manifest": m.name, "error": f"{type(e).__name__}: {e}"})
                continue
            data["dir"] = d.name
            try:
                data["manifest_path"] = str(m.relative_to(REPO_ROOT))
            except ValueError:
                # assess() can be pointed at any root (the tests do exactly that),
                # so a path outside the checkout is normal, not an error.
                data["manifest_path"] = str(m)
            out.append(data)
    return out


def identical_input_streak(feed: dict) -> int:
    n = 0
    for r in feed.get("runs", []):
        if r.get("identical_inputs"):
            n += 1
        else:
            break
    return n


def assess(root: str = REPO_ROOT, now: _dt.datetime | None = None,
           stale_after_hours: float = DEFAULT_STALE_AFTER_HOURS,
           streak_warn: int = DEFAULT_IDENTICAL_INPUT_STREAK_WARN) -> dict:
    now = now or _dt.datetime.now(_dt.timezone.utc)
    checks: list[dict] = []
    irregularities: list[str] = []
    watermark: dict | None = None

    feed_path = os.path.join(root, "data", "alerts", "feed.json")
    delivery_path = os.path.join(root, "data", "alerts", "deliveries.json")
    snapshot_root = os.path.join(root, "snapshots", "nfldata_games")

    # ---- 1. is there a feed at all? -------------------------------------
    if not os.path.exists(feed_path):
        checks.append(check("comparison_feed", "unknown",
                            "no feed artefact exists; no comparison has been recorded from this checkout"))
        feed = {"runs": []}
    else:
        try:
            feed = json.loads(pathlib.Path(feed_path).read_text(encoding="utf-8"))
        except Exception as e:
            checks.append(check("comparison_feed", "fail", f"feed exists but is not valid JSON: {e}"))
            irregularities.append(f"feed JSON unreadable: {e}")
            feed = {"runs": []}
        else:
            runs = feed.get("runs", [])
            checks.append(check("comparison_feed", "ok" if runs else "unknown",
                                f"{len(runs)} completed comparison(s) recorded",
                                runs_recorded=len(runs)))
            if not runs:
                irregularities.append("feed exists but records no completed comparison")

    # ---- 2. how old is the newest completed comparison? ------------------
    last_run = (feed.get("runs") or [None])[0]
    last_at = last_run.get("checked_at") if last_run else None
    age = _age_hours(last_at, now)
    if age is None:
        checks.append(check("freshness", "unknown",
                            "no timestamped comparison exists, so staleness cannot be assessed"))
        status_freshness = "unknown"
    elif age > stale_after_hours:
        status_freshness = "fail"
        checks.append(check(
            "freshness", "fail",
            f"newest completed comparison is {age}h old, beyond the {stale_after_hours}h "
            "project threshold for the daily in-season schedule",
            last_comparison_at=last_at, age_hours=age, threshold_hours=stale_after_hours))
        irregularities.append(f"monitor is stale: no completed comparison in {age}h")
    else:
        status_freshness = "ok"
        checks.append(check(
            "freshness", "ok",
            f"newest completed comparison is {age}h old (threshold {stale_after_hours}h)",
            last_comparison_at=last_at, age_hours=age, threshold_hours=stale_after_hours))

    # ---- 3. did the SOURCE actually move between comparisons? ------------
    # Two different facts, and conflating them is the mistake this replaces:
    #   * the compared projection (final games, frozen fields) was identical
    #   * the upstream source file was identical
    # The churn study measured 44/44 upstream intervals changing the source
    # bytes while zero changed a frozen scoreboard field, so "identical inputs"
    # is the NORMAL healthy state for this detector, not a sign of a stuck
    # fetch. What would be alarming is the source file itself never moving.
    streak = identical_input_streak(feed)
    runs = feed.get("runs") or []
    if not runs:
        checks.append(check("source_movement", "unknown", "no runs to assess"))
    else:
        known = [r for r in runs[:streak_warn] if r.get("source_file_changed") is not None]
        if not known:
            checks.append(check(
                "source_movement", "unknown",
                "the recorded comparisons do not carry upstream source-file hashes, so it cannot "
                "be established whether the source moved; run the snapshot step with a current "
                "pipeline (manifests now record the upstream commit)",
                identical_input_streak=streak))
            irregularities.append("comparisons lack upstream source-file hashes")
        elif all(r.get("source_file_changed") is False for r in known):
            checks.append(check(
                "source_movement", "warn",
                f"the upstream source file did not change across the last {len(known)} "
                "comparisons; either the source is idle or the snapshot step is serving "
                "cached bytes",
                identical_input_streak=streak, comparisons_inspected=len(known)))
            irregularities.append(f"source file unchanged across {len(known)} comparisons")
        else:
            moved = sum(1 for r in known if r.get("source_file_changed"))
            checks.append(check(
                "source_movement", "ok",
                f"the upstream source file changed in {moved} of the last {len(known)} "
                f"comparisons; the frozen-field projection changed in none of them "
                f"(identical-input streak {streak}), which is the expected state for a "
                "scoreboard-only monitor",
                identical_input_streak=streak, comparisons_inspected=len(known),
                source_file_changed_in=moved))

    # ---- 4. snapshot store + upstream watermark --------------------------
    manifests = snapshot_manifests(snapshot_root)
    if not manifests:
        checks.append(check("snapshot_store", "fail",
                            "no snapshot manifests found; there is nothing to diff against on the next run"))
        irregularities.append("snapshot store is empty")
    else:
        newest = manifests[0]
        watermark = {
            "upstream_commit_sha": newest.get("upstream_commit_sha"),
            "upstream_commit_date": newest.get("upstream_commit_date"),
            "upstream_commit_url": newest.get("upstream_commit_url"),
            "source_file_sha256": newest.get("source_file_sha256"),
            "snapshot_dir": newest.get("dir"),
        }
        wm_age = _age_hours(watermark["upstream_commit_date"], now)
        if watermark["upstream_commit_sha"] is None:
            checks.append(check(
                "snapshot_store", "warn",
                f"{len(manifests)} snapshot(s) present, but the newest does not record which "
                "upstream commit it came from, so source freshness cannot be established from it",
                snapshots=len(manifests), watermark=watermark))
            irregularities.append("newest snapshot has no upstream commit watermark")
        elif wm_age is not None and wm_age > stale_after_hours:
            checks.append(check(
                "snapshot_store", "warn",
                f"newest snapshot is pinned to an upstream commit {wm_age}h old",
                snapshots=len(manifests), watermark=watermark, watermark_age_hours=wm_age))
        else:
            checks.append(check(
                "snapshot_store", "ok",
                f"{len(manifests)} snapshot(s); newest is pinned to upstream commit "
                f"{str(watermark['upstream_commit_sha'])[:10]} ({wm_age}h old)",
                snapshots=len(manifests), watermark=watermark, watermark_age_hours=wm_age))

    # ---- 5. delivery receipts --------------------------------------------
    if os.path.exists(delivery_path):
        try:
            log = notify_mod.load_log(delivery_path)
        except Exception as e:
            checks.append(check("push_notification", "fail", f"delivery log unreadable: {e}"))
            irregularities.append(f"delivery log unreadable: {e}")
        else:
            s = log.get("summary", {})
            dead = s.get("dead_letter", 0)
            if dead:
                checks.append(check("push_notification", "fail",
                                    f"{dead} delivery attempt(s) exhausted retries and are dead-lettered; "
                                    "alerts may not have reached anyone",
                                    summary=s))
                irregularities.append(f"{dead} dead-lettered notification(s)")
            elif s.get("attempts_recorded", 0) == 0:
                checks.append(check("push_notification", "unknown",
                                    "delivery log exists but records no attempt", summary=s))
            elif s.get("by_outcome", {}).get("not_configured", 0) == s.get("attempts_recorded", 0):
                checks.append(check(
                    "push_notification", "unknown",
                    f"all {s.get('attempts_recorded')} recorded attempt(s) found no webhook "
                    "configured, so no alert would currently reach a person; delivery is opt-in "
                    "via the ALERT_WEBHOOK_URL secret, and the Atom feed is the "
                    "zero-configuration alternative", summary=s))
                irregularities.append("notification is not configured; alerts reach nobody")
            else:
                checks.append(check("push_notification", "ok",
                                    f"{s.get('attempts_recorded')} attempt(s) recorded; "
                                    f"{s.get('delivered', 0)} delivered", summary=s))
    else:
        checks.append(check("push_notification", "unknown",
                            "no delivery log; push notification has never been attempted from this "
                            "checkout (webhook delivery is opt-in via ALERT_WEBHOOK_URL). The "
                            "pull-based Atom feed is the default channel and is checked separately."))

    # ---- 5b. the pull-based channel: is the Atom feed real and current? ----
    atom_path = os.path.join(root, "data", "alerts", "feed.atom")
    if not os.path.exists(atom_path):
        checks.append(check("atom_feed", "warn",
                            "no Atom feed is published, so there is no zero-configuration way to be "
                            "told about a comparison; run `python3 pipeline/run.py atom`"))
        irregularities.append("Atom feed not published")
    else:
        try:
            import xml.etree.ElementTree as ET
            ns = {"a": "http://www.w3.org/2005/Atom"}
            tree = ET.parse(atom_path)
            root_el = tree.getroot()
            entries = root_el.findall("a:entry", ns)
            ids = [e.findtext("a:id", default="", namespaces=ns) for e in entries]
            updated = root_el.findtext("a:updated", default=None, namespaces=ns)
            problems = []
            if len(set(ids)) != len(ids):
                problems.append("duplicate entry ids (Atom requires unique ids)")
            runs = feed.get("runs") or []
            if runs and len(entries) != len(runs):
                problems.append(f"{len(entries)} entries for {len(runs)} recorded comparisons")
            if updated and last_at and updated[:10] != str(last_at)[:10]:
                problems.append(f"feed <updated> {updated} does not match the newest comparison {last_at}")
            if problems:
                checks.append(check("atom_feed", "fail",
                                    "the published Atom feed is inconsistent: " + "; ".join(problems),
                                    entries=len(entries)))
                irregularities.extend(problems)
            else:
                checks.append(check("atom_feed", "ok",
                                    f"{len(entries)} subscribable entr(ies), unique ids, "
                                    f"<updated> {updated}", entries=len(entries)))
        except Exception as e:
            checks.append(check("atom_feed", "fail",
                                f"the Atom feed is not well-formed XML and would break every "
                                f"subscriber silently: {e}"))
            irregularities.append(f"Atom feed not well-formed: {e}")

    # ---- 6. published copies in step -------------------------------------
    # health.json itself is deliberately NOT in this list: it is written after
    # this assessment runs, so comparing its published copy would always report
    # drift one step behind reality.
    drift = []
    for src, dst in (
        ("data/alerts/feed.json", "docs/data/alerts/feed.json"),
        ("data/alerts/feed.atom", "docs/data/alerts/feed.atom"),
        ("data/discrepancies.json", "docs/data/discrepancies.json"),
        ("data/corrections.atom", "docs/data/corrections.atom"),
        ("data/evidence/upstream_churn_study.json", "docs/data/upstream_churn_study.json"),
    ):
        a, b = os.path.join(root, src), os.path.join(root, dst)
        if os.path.exists(a) and not os.path.exists(b):
            drift.append(f"{dst} missing")
        elif os.path.exists(a) and os.path.exists(b):
            if pathlib.Path(a).read_bytes() != pathlib.Path(b).read_bytes():
                drift.append(f"{dst} differs from {src}")
    if drift:
        checks.append(check("published_copies", "fail",
                            "the site would render stale data: " + "; ".join(drift), drift=drift))
        irregularities.extend(drift)
    else:
        checks.append(check("published_copies", "ok",
                            "every published copy of the feed matches its canonical source"))

    # ---- overall ----------------------------------------------------------
    statuses = [c["status"] for c in checks]
    if "fail" in statuses:
        overall = "fail"
    elif "unknown" in statuses and "ok" not in statuses:
        overall = "unknown"
    elif "warn" in statuses or "unknown" in statuses:
        overall = "warn" if status_freshness == "ok" else "unknown"
    else:
        overall = "ok"

    report = {
        "meta": META,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": overall,
        "headline": _headline(overall, checks),
        "last_successful_comparison_at": last_at,
        "hours_since_last_comparison": age,
        "stale_after_hours": stale_after_hours,
        "identical_input_streak": streak,
        "source_watermark": watermark,
        "checks": checks,
        "irregularities": irregularities,
        "next_action": _next_action(overall, checks),
    }
    return report


def _headline(status: str, checks: list[dict]) -> str:
    failed = [c["check"] for c in checks if c["status"] == "fail"]
    unknown = [c["check"] for c in checks if c["status"] == "unknown"]
    if status == "ok":
        return "Monitor healthy: a completed comparison exists within the freshness threshold."
    if status == "fail":
        return "Monitor NOT healthy: " + ", ".join(failed) + ". A clean-looking site may be stale."
    if status == "warn":
        return "Monitor degraded: it is running, but at least one check needs attention."
    return "Monitor state unknown: " + (", ".join(unknown) or "insufficient evidence") + \
        ". Unknown is not clean."


def _next_action(status: str, checks: list[dict]) -> str:
    if status == "ok":
        return "None. Keep the schedule enabled and re-check after the next run."
    by_name = {c["check"]: c for c in checks}
    if by_name.get("freshness", {}).get("status") == "fail":
        return ("Open the Actions history for detect.yml. If runs are missing, the schedule is "
                "disabled or GitHub delayed it; if runs failed, read the job log. Do not treat the "
                "site's last timestamp as current.")
    if by_name.get("atom_feed", {}).get("status") == "fail":
        return ("The published Atom feed is inconsistent or malformed. Regenerate it with "
                "`python3 pipeline/run.py atom` and re-run ./pipeline/sync_site_data.sh.")
    if by_name.get("push_notification", {}).get("status") == "fail":
        return ("A webhook exhausted its retries. Verify ALERT_WEBHOOK_URL still exists and accepts "
                "POSTs, then re-run the workflow; the dead-letter receipt identifies the alert.")
    if by_name.get("published_copies", {}).get("status") == "fail":
        return "Run ./pipeline/sync_site_data.sh and commit; the site is serving a stale feed copy."
    if by_name.get("push_notification", {}).get("status") == "unknown":
        return ("Push notification is not configured, so a detected candidate would reach nobody "
                "unless they poll. Either set the ALERT_WEBHOOK_URL repository secret (Slack or "
                "Discord compatible) or subscribe to the Atom feed at data/alerts/feed.atom. Until "
                "then the honest state is: detection works, notification does not.")
    if by_name.get("source_movement", {}).get("status") == "warn":
        return ("Successive comparisons had identical input bytes. Confirm the snapshot step is "
                "actually re-downloading, and check the upstream commit watermark.")
    return "Inspect checks[] and the Actions history; do not assume the monitor is working."


def render_markdown(report: dict) -> str:
    icon = {"ok": "PASS", "warn": "WARN", "fail": "FAIL", "unknown": "UNKNOWN"}
    lines = [f"# Monitor health — {report['generated_at']}", "",
             f"**Status: {report['status'].upper()}** — {report['headline']}", "",
             f"Last completed comparison: `{report['last_successful_comparison_at'] or 'none'}` "
             f"({report['hours_since_last_comparison']} h ago; threshold "
             f"{report['stale_after_hours']} h)", ""]
    wm = report.get("source_watermark") or {}
    if wm.get("upstream_commit_sha"):
        lines += [f"Upstream watermark: commit `{str(wm['upstream_commit_sha'])[:10]}` at "
                  f"`{wm.get('upstream_commit_date')}`", ""]
    lines += ["| Check | Status | Detail |", "| --- | --- | --- |"]
    for c in report["checks"]:
        lines.append(f"| {c['check']} | {icon.get(c['status'], c['status'])} | {c['detail']} |")
    if report["irregularities"]:
        lines += ["", "## Irregularities flagged for review"]
        lines += [f"- {i}" for i in report["irregularities"]]
    lines += ["", f"**Next action:** {report['next_action']}", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=REPO_ROOT)
    ap.add_argument("--stale-after-hours", type=float, default=DEFAULT_STALE_AFTER_HOURS)
    ap.add_argument("--out", default=None, help="write the health report here (default: data/alerts/health.json)")
    ap.add_argument("--markdown", default=None, help="also write a Markdown rendering here")
    ap.add_argument("--fail-on", choices=("none", "fail", "warn"), default="fail",
                    help="exit 3 when the overall status is at least this bad")
    args = ap.parse_args()

    report = assess(root=args.root, stale_after_hours=args.stale_after_hours)
    out = args.out or os.path.join(args.root, "data", "alerts", "health.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    pathlib.Path(out).write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                                 encoding="utf-8")
    print(render_markdown(report))
    if args.markdown:
        os.makedirs(os.path.dirname(args.markdown) or ".", exist_ok=True)
        pathlib.Path(args.markdown).write_text(render_markdown(report), encoding="utf-8")
        print(f"wrote {args.markdown}")
    print(f"wrote {out}")

    bad = {"none": None, "warn": ("warn", "fail"), "fail": ("fail",)}[args.fail_on]
    if bad and report["status"] in bad:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
