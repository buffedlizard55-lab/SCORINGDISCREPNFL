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

Exit codes: 0 = clean, 10 = alerts at/above --min-severity found, 1 = error.
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

    # The full file is recorded by hash only; the slim frozen-field form is what
    # gets committed, so the snapshot store stays small enough to version daily.
    path = fetch.write_snapshot(
        REPO_ROOT,
        "nfldata_games",
        "games.slim.csv",
        detect.slim_frozen_csv(detect.load_csv_rows(data)),
        {"repo": fetch.NFLDATA_REPO, "ref": args.ref, "source_file_sha256": raw_sha,
         "source_bytes": len(data), "note": "slim = final games only, frozen fields only"},
    )
    print(f"full source: {len(data)} bytes, sha256 {raw_sha}")
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


def cmd_health(args: argparse.Namespace) -> int:
    """
    Record the outcome of one scheduled detection ATTEMPT.

    This exists because the comparison feed records completed comparisons only.
    If the schedule breaks, no new entry appears and the site keeps showing the
    last successful run as though it were current. Recording attempts separately
    makes a dead monitor visible instead of silently reassuring.
    """
    h = feed.record_attempt(args.health, args.status, args.detail)
    age = feed.health_age_hours(h)
    print(json.dumps({
        "status": h["status"],
        "last_attempt": h.get("last_attempt"),
        "last_success": h.get("last_success"),
        "last_failure": h.get("last_failure"),
        "consecutive_failures": h.get("consecutive_failures", 0),
        "age_hours": age,
    }, indent=2))
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

    h = sub.add_parser("health", help="record the outcome of one scheduled attempt")
    h.add_argument("--status", required=True,
                   choices=list(feed.VALID_STATUSES),
                   help="ok | baseline | failed | unknown")
    h.add_argument("--detail", default="", help="free-text context for the run log")
    h.add_argument("--health", default=os.path.join(REPO_ROOT, "data", "alerts", "health.json"))
    h.set_defaults(fn=cmd_health)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
