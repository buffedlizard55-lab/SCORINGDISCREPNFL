#!/usr/bin/env python3
"""
vintage_study.py — measure how a versioned third-party mirror actually revises.

WHY THIS EXISTS
---------------
The brief asks two questions that a single before/after snapshot pair cannot
answer:

  * "how quickly corrections are published"
  * "whether a reliable automated system could detect them without manual
     checking"

Both depend on the *revision behaviour of the source we poll*. If the mirror
rewrites already-final games every ten minutes, a daily poll is blind to most
of it; if it never touches them, a daily poll is enough. That is an empirical
question, and this module answers it from genuine, immutable, re-downloadable
upstream vintages rather than from assumption.

WHAT IT DOES
------------
1. Enumerates upstream commits that touched the mirrored file
   (`nflverse/nfldata` -> `data/games.csv`) via the GitHub commits API.
2. Samples a stride through them and downloads each vintage as a codeload
   tarball **at the exact commit SHA**. A tarball at a SHA is immutable, so any
   reviewer can re-download the identical bytes years later and reproduce the
   hashes recorded here. That URL is stored for every vintage.
3. For each consecutive pair, runs the *shipped* detector
   (`detect.diff_final_records`) — this is a genuine dry run of the alerting
   path on real before/after vintages — and additionally records EVERY
   field-level change on games already final in the older vintage, including
   fields the detector deliberately ignores.

WHAT THE RESULT IS *NOT*
------------------------
* It is not a measure of NFL/Elias corrections. It measures a mirror.
* It is not exhaustive. Sampling with a stride means changes that happened and
  were reverted inside one interval are invisible (LIMITATIONS §9). The stride
  and the exact commit list are recorded so the blind spot is quantified, not
  hidden.
* Zero observed frozen-field changes is not proof that official scores cannot
  change. It is a bounded observation over a stated window.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import detect  # noqa: E402
import fetch  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "data", "evidence", "upstream_churn_study.json")

META = {
    "what_this_is": (
        "A measurement of how often a versioned third-party mirror of NFL game "
        "results revises records for games that were ALREADY FINAL, using genuine "
        "immutable upstream Git vintages. Every vintage is re-downloadable from the "
        "recorded codeload URL and identified by SHA-256."
    ),
    "what_it_is_not": (
        "Not a count of NFL/Elias corrections, not an official-record statement, and "
        "not exhaustive: vintages are sampled at a stride, so a change made and "
        "reverted inside one interval is invisible. The mirror is not the NFL."
    ),
    "detector_under_test": (
        "pipeline/detect.py diff_final_records() over FROZEN_FIELDS_GAMES, the same "
        "code path the scheduled alerting workflow runs."
    ),
    "see": ["FINDINGS.md", "LIMITATIONS.md", "ALERT_SYSTEM_FEASIBILITY.md"],
}


def _parse_ts(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def collect_commits(path: str = fetch.NFLDATA_CSV, total: int = 100, until: str | None = None) -> list[dict]:
    """Page backwards through commits touching `path`, newest first."""
    out: list[dict] = []
    cursor = until
    while len(out) < total:
        batch = fetch.nfldata_commits(path=path, limit=min(100, total - len(out)), until=cursor)
        if not batch:
            break
        for c in batch:
            out.append({
                "sha": c["sha"],
                "date": c["commit"]["committer"]["date"].replace("+00:00", "Z"),
                "message": (c["commit"]["message"] or "").splitlines()[0][:120],
                "url": c.get("html_url"),
            })
        cursor = out[-1]["date"]
        if len(batch) < 2:
            break
    # de-duplicate while preserving order (the API can repeat a boundary commit)
    seen, uniq = set(), []
    for c in out:
        if c["sha"] in seen:
            continue
        seen.add(c["sha"])
        uniq.append(c)
    return uniq[:total]


def download_vintage(sha: str, member: str = fetch.NFLDATA_CSV, cache: str | None = None) -> bytes:
    """Bytes of `member` at an exact commit SHA, optionally cached on disk."""
    if cache:
        os.makedirs(cache, exist_ok=True)
        p = os.path.join(cache, sha[:12] + ".csv")
        if os.path.exists(p):
            with open(p, "rb") as f:
                return f.read()
        data = fetch.nfldata_snapshot_from_commit(sha, member=member)
        with open(p, "wb") as f:
            f.write(data)
        return data
    return fetch.nfldata_snapshot_from_commit(sha, member=member)


def run_study(commits: list[dict], stride: int = 10, cache: str | None = None,
              member: str = fetch.NFLDATA_CSV) -> dict:
    """Sample vintages oldest->newest and diff each consecutive pair."""
    ordered = sorted(commits, key=lambda c: c["date"])
    sampled = ordered[::max(1, stride)]
    if sampled and sampled[-1] is not ordered[-1]:
        sampled.append(ordered[-1])  # always include the newest vintage

    vintages: list[dict] = []
    pairs: list[dict] = []
    prev_rows = None

    for c in sampled:
        try:
            data = download_vintage(c["sha"], member=member, cache=cache)
        except Exception as e:  # a failed download is recorded, never skipped silently
            vintages.append({**c, "error": f"{type(e).__name__}: {e}"})
            prev_rows = None
            continue
        rows = detect.load_csv_rows(data)
        slim = detect.slim_frozen_csv(rows)
        v = {
            **c,
            "codeload_url": f"https://codeload.github.com/{fetch.NFLDATA_REPO}/tar.gz/{c['sha']}",
            "member": member,
            "bytes": len(data),
            "sha256": detect.sha256_bytes(data),
            "slim_sha256": detect.sha256_bytes(slim),
            "records": len(rows),
            "final_records": sum(1 for r in rows.values() if detect.is_final(r)),
        }
        vintages.append(v)

        if prev_rows is not None:
            old_meta, new_meta = vintages[-2], v
            frozen_changes = detect.diff_final_records(prev_rows, rows, detect.FROZEN_FIELDS_GAMES)
            report = detect.build_alert_report(
                frozen_changes, source=f"nflverse/nfldata@{c['sha'][:10]}", min_severity=0)
            # Every field that moved on an already-final game, including the
            # volatile/metadata fields the detector ignores on purpose. Recording
            # them is what lets us say the frozen-field result is not an artefact
            # of a silent file.
            other: list[dict] = []
            for key, old in prev_rows.items():
                if not detect.is_final(old):
                    continue
                new = rows.get(key)
                if new is None:
                    other.append({"game_id": key, "field": "<record>", "old": "present",
                                  "new": "missing", "kind": "record_removed"})
                    continue
                for field_name, ov in old.items():
                    nv = new.get(field_name)
                    if ov != nv and field_name not in detect.FROZEN_FIELDS_GAMES:
                        # A blank -> value edit is a LATE BACKFILL. A value -> different
                        # value edit is a REVISION of data the mirror had already
                        # published for a finished game. Only the second kind can be a
                        # correction in the sense the brief means, so they are counted
                        # separately instead of being lumped together.
                        blank = (ov or "").strip() in ("", "None", "NA")
                        other.append({
                            "game_id": key, "field": field_name, "old": ov, "new": nv,
                            "kind": "backfill_of_blank" if blank else "revision_of_published_value",
                            "season": old.get("season"), "week": old.get("week"),
                            "away_team": old.get("away_team"), "home_team": old.get("home_team"),
                            "gameday": old.get("gameday"),
                        })
            hours = ( _parse_ts(v["date"]) - _parse_ts(old_meta["date"]) ).total_seconds() / 3600.0
            pairs.append({
                "old_commit": old_meta["sha"], "new_commit": v["sha"],
                "old_date": old_meta["date"], "new_date": v["date"],
                "interval_hours": round(hours, 2),
                "final_records_in_old": old_meta["final_records"],
                "final_records_in_new": v["final_records"],
                "final_records_delta": v["final_records"] - old_meta["final_records"],
                "full_file_changed": old_meta["sha256"] != v["sha256"],
                "slim_changed": old_meta["slim_sha256"] != v["slim_sha256"],
                "detector_alerts": report["total_alerts"],
                "detector_alert_detail": report["alerts"],
                "non_frozen_changes_on_final_games": other,
                "non_frozen_change_count": len(other),
            })
        prev_rows = rows

    ok = [v for v in vintages if "error" not in v]
    frozen_total = sum(p["detector_alerts"] for p in pairs)
    nonfrozen_total = sum(p["non_frozen_change_count"] for p in pairs)
    fields_seen: dict[str, int] = {}
    kinds: dict[str, int] = {}
    games_touched: set[str] = set()
    revisions: list[dict] = []
    for p in pairs:
        for ch in p["non_frozen_changes_on_final_games"]:
            fields_seen[ch["field"]] = fields_seen.get(ch["field"], 0) + 1
            kinds[ch.get("kind", "unknown")] = kinds.get(ch.get("kind", "unknown"), 0) + 1
            games_touched.add(ch["game_id"])
            if ch.get("kind") == "revision_of_published_value":
                revisions.append({"observed_at": p["new_date"], **ch})

    # INTERNAL CONSISTENCY: if the slim frozen projection changed but no frozen
    # value changed and the number of final records did not change either, then
    # something happened we cannot explain. That must be surfaced, not smoothed.
    unexplained = [
        {"old_commit": p["old_commit"], "new_commit": p["new_commit"], "new_date": p["new_date"]}
        for p in pairs
        if p["slim_changed"] and p["detector_alerts"] == 0 and p["final_records_delta"] == 0
    ]

    span_hours = None
    if len(ok) >= 2:
        span_hours = round((_parse_ts(ok[-1]["date"]) - _parse_ts(ok[0]["date"])).total_seconds() / 3600.0, 2)

    return {
        "meta": META,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "repo": fetch.NFLDATA_REPO,
            "member": member,
            "commit_listing_api": f"https://api.github.com/repos/{fetch.NFLDATA_REPO}/commits?path={member}",
            "provenance": "third-party mirror of NFL schedule/results/lines; not an NFL publication",
        },
        "sampling": {
            "commits_enumerated": len(commits),
            "stride": stride,
            "vintages_downloaded": len(ok),
            "vintages_failed": len(vintages) - len(ok),
            "window_start": ok[0]["date"] if ok else None,
            "window_end": ok[-1]["date"] if ok else None,
            "window_hours": span_hours,
            "intervals_compared": len(pairs),
            "note": (
                "Sampled intervals are a blind spot by construction: a change made and "
                "reverted inside one interval cannot be observed. Reduce --stride to shrink it."
            ),
        },
        "totals": {
            "final_records_compared": sum(p["final_records_in_old"] for p in pairs),
            "frozen_field_changes_on_final_games": frozen_total,
            "non_frozen_field_changes_on_final_games": nonfrozen_total,
            "intervals_where_full_file_bytes_changed": sum(1 for p in pairs if p["full_file_changed"]),
            "intervals_where_slim_frozen_projection_changed": sum(1 for p in pairs if p["slim_changed"]),
            "non_frozen_fields_observed": dict(sorted(fields_seen.items(), key=lambda kv: -kv[1])),
            "change_kinds_on_final_games": dict(sorted(kinds.items(), key=lambda kv: -kv[1])),
            "distinct_final_games_touched": len(games_touched),
            "revisions_of_already_published_values": revisions,
            "slim_changes_not_explained_by_frozen_or_row_count": unexplained,
        },
        "vintages": vintages,
        "pairs": pairs,
        "interpretation": (
            f"Across {len(pairs)} sampled intervals spanning {span_hours} hours of upstream "
            f"history, {sum(1 for p in pairs if p['full_file_changed'])} intervals changed the "
            f"mirrored file's bytes. On games that were ALREADY FINAL, {nonfrozen_total} "
            f"non-scoreboard field change(s) were observed across {len(games_touched)} games "
            f"({kinds.get('backfill_of_blank', 0)} late backfills of a blank cell, "
            f"{kinds.get('revision_of_published_value', 0)} revisions of an already-published "
            f"value), and {frozen_total} frozen scoreboard-field change(s). The mirror therefore "
            "does edit finished games after the fact; in this window none of those edits touched "
            "a score, margin, total or overtime flag. Bounded observation about a third-party "
            "mirror, not a statement about NFL records."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commits", type=int, default=100, help="how many upstream commits to enumerate")
    ap.add_argument("--stride", type=int, default=10, help="download every Nth commit")
    ap.add_argument("--until", default=None, help="ISO-8601 UTC upper bound for commit listing")
    ap.add_argument("--cache", default=None, help="directory to cache downloaded vintages")
    ap.add_argument("--out", default=OUT_PATH)
    args = ap.parse_args()

    cache = args.cache or os.path.join(tempfile.gettempdir(), "scoringdiscrepnfl_vintages")
    commits = collect_commits(total=args.commits, until=args.until)
    if len(commits) < 2:
        print("::error::fewer than two upstream commits were enumerable; no comparison is possible.")
        return 1
    study = run_study(commits, stride=args.stride, cache=cache)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(study, f, indent=1)
        f.write("\n")
    t = study["totals"]
    print(json.dumps({
        "window": f"{study['sampling']['window_start']} -> {study['sampling']['window_end']}",
        "window_hours": study["sampling"]["window_hours"],
        "vintages": study["sampling"]["vintages_downloaded"],
        "intervals": study["sampling"]["intervals_compared"],
        "intervals_with_byte_changes": t["intervals_where_full_file_bytes_changed"],
        "frozen_field_changes_on_final_games": t["frozen_field_changes_on_final_games"],
        "non_frozen_changes_on_final_games": t["non_frozen_field_changes_on_final_games"],
        "non_frozen_fields_observed": t["non_frozen_fields_observed"],
    }, indent=2))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
