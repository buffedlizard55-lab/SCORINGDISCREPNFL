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
import fetch  # noqa: E402
from parse_corrections import parse_official_page  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
    return 10 if report["total_alerts"] else 0


def cmd_evidence(args: argparse.Namespace) -> int:
    """
    Score-integrity study.

    Pulls nfldata games.csv at a set of historical commits, keeps only games
    that were ALREADY FINAL at that commit, and checks whether any frozen score
    field differs from the current record. Any difference would be direct
    evidence that a completed NFL game's official score was revised after the
    fact and then propagated into a mirror.
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

    total_final = sum(r.get("final_at_baseline", 0) for r in results)
    total_changed = sum(r.get("frozen_field_changes_vs_current", 0) for r in results)
    out = {
        "study": "final-score integrity of the NFL record as mirrored by nflverse/nfldata",
        "method": (
            "For each historical commit of nflverse/nfldata data/games.csv, retain games whose "
            "`result` field was already populated (i.e. the game had concluded), then compare the "
            "frozen fields (away_score, home_score, result, total, overtime) against the current "
            "record and count any difference."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "baselines": results,
        "totals": {
            "game_snapshots_examined": total_final,
            "final_scores_revised_after_completion": total_changed,
        },
        "conclusion": (
            "Across every baseline examined, zero completed games had any frozen score field "
            "revised afterwards. Within the retention window of this mirror, an NFL game's final "
            "score is effectively immutable once posted; what changes post-game is ATTRIBUTION "
            "and STATISTICS, not the scoreboard."
            if total_changed == 0
            else "One or more completed games had a frozen score field revised after completion. "
                 "See `baselines[].changes` for the specific games and values."
        ),
        "caveat": (
            "This tests a third-party MIRROR of the NFL's record, not the NFL's own database. "
            "It cannot detect a correction that the NFL made and then re-corrected back within a "
            "single mirror update interval, nor any correction made before this mirror existed."
        ),
    }

    outdir = os.path.join(REPO_ROOT, "data", "evidence")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "score_integrity_study.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out["totals"], indent=2))
    print(f"wrote {path}")
    return 0


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
        rows = parse_official_page(
            raw.decode("utf-8", "replace"), source_url=url, snapshot_timestamp=ts
        )
        print(f"  {ts} -> {len(rows)} rows  ({url[:80]})")
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
    Fetch one known-good archived page and report whether the parser recovered
    the expected four-column structure. Run this FIRST on Actions before
    trusting any parsed output.
    """
    ts, url = "20200930215056", fetch.official_corrections_url(2015, 16, "O")
    raw = fetch.official_corrections_page(ts, url)
    text = raw.decode("utf-8", "replace")
    rows = parse_official_page(text, 2015, 16, source_url=url, snapshot_timestamp=ts)
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
    d.set_defaults(fn=cmd_diff)

    e = sub.add_parser("evidence"); e.set_defaults(fn=cmd_evidence)

    c = sub.add_parser("corrections")
    c.add_argument("--season", type=int, default=None)
    c.add_argument("--limit", type=int, default=50)
    c.set_defaults(fn=cmd_corrections)

    sc = sub.add_parser("selfcheck"); sc.set_defaults(fn=cmd_selfcheck)

    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
