#!/usr/bin/env python3
"""
run.py — CLI entry point for the scoring-discrepancy detection system.

Commands
--------
  snapshot            Fetch the current nfldata games.csv and store a hashed
                      snapshot under snapshots/nfldata_games/<utc-stamp>/.
  diff OLD NEW        Diff two games.csv files and print/write the alert report.
  evidence            Re-run the score-integrity study across historical
                      snapshots of nfldata/games.csv (this is the check that
                      produced the 0-changes result in FINDINGS.md).
  corrections         Pull archived official NFL stat-correction pages from the
                      Wayback Machine and parse them into structured rows.
  selfcheck           Validate the corrections parser against archived pages.
  deliver             Send the last alert report via webhook, with receipts.
  health              Assess whether the monitor itself is working.
  atom                Regenerate the subscribable Atom feeds for the site.
  churn               Measure how the mirrored source revises finished games.

Exit codes: 0 = clean, 10 = alerts at/above --min-severity found,
            3 = monitor unhealthy (health), 11 = notification dead-lettered
            (deliver), 1 = error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import detect  # noqa: E402
import feed  # noqa: E402
import fetch  # noqa: E402
import notify  # noqa: E402
from parse_corrections import parse_official_page  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def correction_scope_from_url(url: str, fallback_season: int | None = None) -> tuple[int | None, int | None]:
    """Extract source season/week parameters, retaining a CLI season fallback."""
    from urllib.parse import parse_qs, urlsplit

    query = parse_qs(urlsplit(url).query)

    def integer_param(name: str) -> int | None:
        value = query.get(name, [None])[0]
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    return integer_param("statSeason") or fallback_season, integer_param("statWeek")


def cmd_snapshot(args: argparse.Namespace) -> int:
    data = fetch.nfldata_snapshot_head(ref=args.ref)
    raw_sha = detect.sha256_bytes(data)

    # SOURCE WATERMARK: which upstream commit this snapshot came from, and when
    # that commit landed. Without it a snapshot is bytes of unknown age, and
    # pipeline/health.py has to report source freshness as "unknown".
    head = fetch.nfldata_head_commit(ref=args.ref) or {}

    # The full file is recorded by hash only; the slim frozen-field form is what
    # gets committed, so the snapshot store stays small enough to version daily.
    path = fetch.write_snapshot(
        REPO_ROOT,
        "nfldata_games",
        "games.slim.csv",
        detect.slim_frozen_csv(detect.load_csv_rows(data)),
        {"repo": fetch.NFLDATA_REPO, "ref": args.ref, "source_file_sha256": raw_sha,
         "source_bytes": len(data), "note": "slim = final games only, frozen fields only",
         "upstream_commit_sha": head.get("sha"),
         "upstream_commit_date": head.get("date"),
         "upstream_commit_message": head.get("message"),
         "upstream_commit_url": head.get("url"),
         "codeload_url": f"https://codeload.github.com/{fetch.NFLDATA_REPO}/tar.gz/{head.get('sha')}"
         if head.get("sha") else None},
    )
    print(f"full source: {len(data)} bytes, sha256 {raw_sha}")
    if head.get("sha"):
        print(f"upstream watermark: {head['sha'][:10]} committed {head.get('date')}")
    else:
        print("upstream watermark: UNKNOWN (commit listing unavailable; freshness cannot be asserted)")
    print(f"stored slim snapshot -> {path} ({os.path.getsize(path)} bytes)")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    old = detect.load_csv_rows(open(args.old, "rb").read())
    new = detect.load_csv_rows(open(args.new, "rb").read())
    changes = detect.diff_final_records(old, new, detect.FROZEN_FIELDS_GAMES)
    report = detect.build_alert_report(changes, source=args.source, min_severity=args.min_severity)
    report["inputs"] = {
        "old": {"path": args.old, "sha256": detect.sha256_file(args.old)},
        "new": {"path": args.new, "sha256": detect.sha256_file(args.new)},
        "old_records": len(old),
        "new_records": len(new),
        "old_final_records": sum(1 for r in old.values() if detect.is_final(r)),
    }
    report["rules_applied"] = [
        "only rows final in OLD snapshot are compared",
        f"only frozen fields compared: {detect.FROZEN_FIELDS_GAMES}",
        f"volatile fields excluded: {detect.VOLATILE_FIELDS_GAMES}",
    ]
    detect.notify_stdout(report)
    if args.out:
        detect.notify_file(report, args.out)
        print(f"wrote report -> {args.out}")
    if getattr(args, "feed", None):
        # Record EVERY run, including clean ones: that is what turns a detector
        # into a feed. See pipeline/feed.py.
        f = feed.append_run(report, args.old, args.new, args.feed)
        print(f"appended run to feed -> {args.feed} "
              f"({f['summary']['runs_recorded']} runs, "
              f"{f['summary']['runs_with_alerts']} with alerts)")
    return 10 if report["total_alerts"] else 0


def cmd_deliver(args: argparse.Namespace) -> int:
    """Send the last alert report through the notification layer, with receipts.

    Exit codes are deliberately distinct so CI can tell *why* a run failed:
      0  delivered, or nothing to deliver / no webhook configured
      11 the webhook exhausted its retries and is dead-lettered

    A dead-letter is a failure of the notification system, not of the detector,
    and it must not be allowed to look like a quiet week.
    """
    import os as _os

    report_path = args.report or os.path.join(REPO_ROOT, "alerts", "latest.json")
    if not _os.path.exists(report_path):
        print(f"no alert report at {report_path}; nothing to deliver")
        return 0
    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)

    url = _os.environ.get(args.webhook_env) or None
    deliveries = args.deliveries or os.path.join(REPO_ROOT, "data", "alerts", "deliveries.json")
    receipt = notify.deliver(report, url, deliveries, max_attempts=args.max_attempts, force=args.force)
    print(json.dumps({k: v for k, v in receipt.items() if k != "url"}, indent=2))
    print(f"delivery receipt appended -> {deliveries}")
    if receipt["outcome"] == "failed":
        print("::error::notification dead-lettered after "
              f"{receipt['attempts']} attempt(s): {receipt['detail']}")
        return 11
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    """Assess whether the monitor itself is working (see pipeline/health.py)."""
    import health

    report = health.assess(root=args.root, stale_after_hours=args.stale_after_hours)
    out = args.out or os.path.join(args.root, "data", "alerts", "health.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(health.render_markdown(report))
    print(f"wrote {out}")
    bad = {"none": (), "warn": ("warn", "fail"), "fail": ("fail",)}[args.fail_on]
    return 3 if report["status"] in bad else 0


def cmd_atom(args: argparse.Namespace) -> int:
    """Regenerate the subscribable Atom feeds published alongside the site."""
    import atom

    written = []
    feed_path = args.feed or os.path.join(REPO_ROOT, "data", "alerts", "feed.json")
    db_path = args.database or os.path.join(REPO_ROOT, "data", "discrepancies.json")
    site = args.site_url if args.site_url.endswith("/") else args.site_url + "/"

    data = {"runs": []}
    if os.path.exists(feed_path):
        with open(feed_path, encoding="utf-8") as f:
            data = json.load(f)
    else:
        print(f"note: no feed at {feed_path}; publishing an explicit 'no comparison recorded' feed")
    p = os.path.join(args.outdir, "alerts", "feed.atom")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(atom.build_detection_feed(data, site))
    written.append(p)

    if os.path.exists(db_path):
        with open(db_path, encoding="utf-8") as f:
            db = json.load(f)
        p = os.path.join(args.outdir, "corrections.atom")
        with open(p, "w", encoding="utf-8") as f:
            f.write(atom.build_corrections_feed(db, site))
        written.append(p)

    import xml.etree.ElementTree as ET
    for path in written:
        ET.parse(path)  # a malformed feed breaks every subscriber silently
        print(f"wrote {path} ({os.path.getsize(path)} bytes, well-formed)")
    return 0


def cmd_churn(args: argparse.Namespace) -> int:
    """Measure how the mirrored source revises already-final games (vintage study)."""
    import vintage_study

    commits = vintage_study.collect_commits(total=args.commits, until=args.until)
    if len(commits) < 2:
        print("::error::fewer than two upstream commits were enumerable; no comparison is possible.")
        return 1
    study = vintage_study.run_study(commits, stride=args.stride, cache=args.cache)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(study, f, indent=1)
        f.write("\n")
    print(json.dumps({"sampling": study["sampling"], "totals": {
        k: v for k, v in study["totals"].items()
        if k not in ("revisions_of_already_published_values",
                     "slim_changes_not_explained_by_frozen_or_row_count")},
        "unexplained": study["totals"]["slim_changes_not_explained_by_frozen_or_row_count"],
    }, indent=2))
    print(f"wrote {args.out}")
def cmd_attempt(args: argparse.Namespace) -> int:
    """
    Record the outcome of one scheduled detection ATTEMPT.

    This exists because the comparison feed records completed comparisons only.
    If the schedule breaks, no new entry appears and the site keeps showing the
    last successful run as though it were current. Recording attempts separately
    makes a dead monitor visible instead of silently reassuring.

    It is called `attempt` and writes `data/alerts/attempts.json` because
    `health` / `health.json` means the wider self-assessment produced by
    pipeline/health.py — which reads this ledger as one of its checks, so a
    failed attempt is escalated by the watchdog instead of living only in a
    banner. Both features are kept; only the ambiguous name was removed.
    """
    h = feed.record_attempt(args.attempts, args.status, args.detail)
    age = feed.attempt_age_hours(h)
    print(json.dumps({
        "status": h["status"],
        "last_attempt": h.get("last_attempt"),
        "last_success": h.get("last_success"),
        "last_failure": h.get("last_failure"),
        "consecutive_failures": h.get("consecutive_failures", 0),
        "age_hours": age,
    }, indent=2))
    return 0


    return 0


def summarize_evidence_baselines(results: list[dict]) -> dict:
    """Summarize selected baseline diffs without treating failed fetches as zeroes."""
    failed = [r for r in results if "error" in r]
    fetched = len(results) - len(failed)
    total_final = sum(r.get("final_at_baseline", 0) for r in results)
    total_changed = sum(r.get("frozen_field_changes_vs_current", 0) for r in results)

    if failed or not results:
        if not results:
            conclusion = "INCOMPLETE: no baseline results were available; no zero-change conclusion is possible."
        else:
            conclusion = (
                f"INCOMPLETE: {len(failed)} of {len(results)} selected baseline fetches failed. "
                f"Among the {fetched} fetched baselines, {total_changed} frozen-field differences "
                "were observed among games already final at baseline. No conclusion about the "
                "unfetched baselines or NFL score immutability follows."
            )
        status = "incomplete"
    elif total_changed == 0:
        conclusion = (
            f"Across the {len(results)} selected historical baselines, no differences were observed "
            "in the five frozen game fields for rows already final in each older mirror snapshot, "
            "when compared with the current mirror. This limited third-party mirror comparison does "
            "not establish that official NFL scores never change or estimate how often they change."
        )
        status = "complete"
    else:
        conclusion = (
            "One or more frozen game fields differed between a selected older mirror snapshot and "
            "the current mirror for a row already final at baseline. This is a mirror-change "
            "candidate, not proof of an official NFL correction. See `baselines[].changes`."
        )
        status = "complete"

    return {
        "status": status,
        "totals": {
            "game_snapshots_examined": total_final,
            "frozen_field_changes_vs_current": total_changed,
            "selected_baselines": len(results),
            "baselines_fetched": fetched,
            "baselines_failed": len(failed),
        },
        "conclusion": conclusion,
    }


def cmd_evidence(args: argparse.Namespace) -> int:
    """
    Compare selected historical game-results mirror vintages.

    Pulls nfldata games.csv at a set of historical commits, keeps only games
    that were already final at each commit, and checks whether any of five
    frozen fields differs from the current mirror. A difference is a mirror
    change candidate, not direct proof of an official NFL correction. Failed
    baseline downloads make the study incomplete and are reported as such.
    """
    baselines = [
        ("2023-12-03", "88766138b8c3e78a669cca7116e79369749c3049"),
        ("2025-11-12", "204290217ee8c5689eb2fb189f93883361925607"),
        ("2026-01-20", "b1b3621d04525558261a8c888bba367004723bd4"),
        ("2026-09-22", "eeec4e0bae4728f619806dc3fa8fc67a1757ca1e"),
    ]
    print("Fetching current record ...")
    current_raw = fetch.nfldata_snapshot_head()
    current = detect.load_csv_rows(current_raw)

    results = []
    for label, sha in baselines:
        print(f"Fetching baseline {label} ({sha[:10]}) ...")
        try:
            raw = fetch.nfldata_snapshot_from_commit(sha)
        except Exception as e:  # network/permission issues must not be silent
            results.append({"baseline": label, "commit": sha, "error": repr(e)})
            continue
        old = detect.load_csv_rows(raw)
        final_rows = {k: v for k, v in old.items() if detect.is_final(v)}
        changes = detect.diff_final_records(final_rows, current, detect.FROZEN_FIELDS_GAMES)
        results.append(
            {
                "baseline": label,
                "commit": sha,
                "old_records": len(old),
                "final_at_baseline": len(final_rows),
                "frozen_field_changes_vs_current": len(changes),
                "changes": [c.to_dict() for c in changes[:20]],
                "old_sha256": detect.sha256_bytes(raw),
                "current_sha256": detect.sha256_bytes(current_raw),
            }
        )

    summary = summarize_evidence_baselines(results)
    out = {
        "study": "selected frozen-game-field comparisons in the nflverse/nfldata mirror",
        "method": (
            "For each historical commit of nflverse/nfldata data/games.csv, retain games whose "
            "`result` field was already populated (i.e. the game had concluded), then compare the "
            "frozen fields (away_score, home_score, result, total, overtime) against the current "
            "record and count any difference."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "baselines": results,
        **summary,
        "caveat": (
            "This compares selected vintages of a third-party mirror, not the NFL's own database. "
            "It cannot detect a correction that was made and reverted between sampled vintages, "
            "nor any correction made before this mirror existed. The total counts overlapping "
            "game-snapshot comparisons, not unique games."
        ),
    }

    outdir = os.path.join(REPO_ROOT, "data", "evidence")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "score_integrity_study.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out["totals"], indent=2))
    print(f"wrote {path}")
    return 1 if summary["status"] != "complete" else 0


def cmd_corrections(args: argparse.Namespace) -> int:
    snaps = fetch.official_corrections_snapshots(season=args.season, limit=args.limit)
    print(f"found {len(snaps)} archived official corrections snapshots")
    rows_out = []
    for ts, url in snaps:
        try:
            raw = fetch.official_corrections_page(ts, url)
        except Exception as e:
            print(f"  {ts} FETCH FAILED {e!r}")
            continue
        season, week = correction_scope_from_url(url, args.season)
        review_url = fetch.official_corrections_snapshot_url(ts, url)
        rows = parse_official_page(
            raw.decode("utf-8", "replace"),
            season=season,
            week=week,
            source_url=review_url,
            snapshot_timestamp=ts,
        )
        print(f"  {ts} -> {len(rows)} rows  ({review_url[:100]})")
        rows_out.extend(r.to_dict() for r in rows)

    outdir = os.path.join(REPO_ROOT, "data")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "official_corrections_parsed.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows_out, f, indent=2)
    print(f"wrote {path} ({len(rows_out)} rows)")
    return 0


def cmd_selfcheck(args: argparse.Namespace) -> int:
    """
    Fetch one known archived page and report whether the parser recovered at
    least ten fully parsed rows. This is a manual/backfill diagnostic, not a
    validation of every field or a gate in the scoreboard-only workflow.
    """
    ts, url = "20200930215056", fetch.official_corrections_url(2015, 16, "O")
    raw = fetch.official_corrections_page(ts, url)
    text = raw.decode("utf-8", "replace")
    rows = parse_official_page(
        text,
        2015,
        16,
        source_url=fetch.official_corrections_snapshot_url(ts, url),
        snapshot_timestamp=ts,
    )
    parsed = [r for r in rows if r.parse_status == "parsed"]
    print(f"bytes={len(raw)} table_rows_parsed={len(rows)} fully_parsed={len(parsed)}")
    for r in parsed[:5]:
        print(f"  {r.player} | {r.correction_date} | {r.stat}: {r.original_value} -> {r.corrected_value}")
    ok = len(parsed) >= 10
    print("SELFCHECK", "PASS" if ok else "FAIL — reconcile parser against real HTML")
    return 0 if ok else 1


def main() -> int:
    p = argparse.ArgumentParser(prog="run.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("snapshot"); s.add_argument("--ref", default="master"); s.set_defaults(fn=cmd_snapshot)

    d = sub.add_parser("diff")
    d.add_argument("old"); d.add_argument("new")
    d.add_argument("--source", default="nfldata_games")
    d.add_argument("--min-severity", type=int, default=1)
    d.add_argument("--out", default=None)
    d.add_argument("--feed", default=None,
                   help="append this run to the persistent feed JSON (records clean runs too)")
    d.set_defaults(fn=cmd_diff)

    e = sub.add_parser("evidence"); e.set_defaults(fn=cmd_evidence)

    c = sub.add_parser("corrections")
    c.add_argument("--season", type=int, default=None)
    c.add_argument("--limit", type=int, default=50)
    c.set_defaults(fn=cmd_corrections)

    sc = sub.add_parser("selfcheck"); sc.set_defaults(fn=cmd_selfcheck)

    dl = sub.add_parser("deliver", help="send the last alert report, with receipts")
    dl.add_argument("--report", default=None)
    dl.add_argument("--deliveries", default=None)
    dl.add_argument("--webhook-env", default="ALERT_WEBHOOK_URL")
    dl.add_argument("--max-attempts", type=int, default=3)
    dl.add_argument("--force", action="store_true",
                    help="re-deliver even if this comparison was already delivered")
    dl.set_defaults(fn=cmd_deliver)

    h = sub.add_parser("health", help="is the monitor itself working?")
    h.add_argument("--root", default=REPO_ROOT)
    h.add_argument("--stale-after-hours", type=float, default=40.0)
    h.add_argument("--out", default=None)
    h.add_argument("--fail-on", choices=("none", "fail", "warn"), default="fail")
    h.set_defaults(fn=cmd_health)

    at = sub.add_parser("atom", help="regenerate the subscribable Atom feeds")
    at.add_argument("--feed", default=None)
    at.add_argument("--database", default=None)
    at.add_argument("--outdir", default=os.path.join(REPO_ROOT, "data"))
    at.add_argument("--site-url", default="https://buffedlizard55-lab.github.io/SCORINGDISCREPNFL/")
    at.set_defaults(fn=cmd_atom)

    ch = sub.add_parser("churn", help="measure upstream revision behaviour of the mirror")
    ch.add_argument("--commits", type=int, default=2200)
    ch.add_argument("--stride", type=int, default=50)
    ch.add_argument("--until", default=None)
    ch.add_argument("--cache", default=None)
    ch.add_argument("--out", default=os.path.join(REPO_ROOT, "data", "evidence", "upstream_churn_study.json"))
    ch.set_defaults(fn=cmd_churn)

    am = sub.add_parser("attempt", help="record the outcome of one scheduled attempt")
    am.add_argument("--status", required=True,
                    choices=list(feed.VALID_STATUSES),
                    help="ok | baseline | failed | unknown")
    am.add_argument("--detail", default="", help="free-text context for the run log")
    am.add_argument("--attempts",
                    default=os.path.join(REPO_ROOT, "data", "alerts", "attempts.json"))
    am.set_defaults(fn=cmd_attempt)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
