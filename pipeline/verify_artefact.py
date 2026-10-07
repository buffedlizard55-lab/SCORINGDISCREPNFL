#!/usr/bin/env python3
"""
verify_artefact.py — re-read a stored evidence artefact against a fresh
rendering of the same archived official page, row by row.

WHY THIS EXISTS
---------------
The brief's hardest requirement is "no hallucinations, verify line by line". The
fact layer is generated from stored artefacts in `data/evidence/pages/`, and
`ingest_rendered.py --check` proves the *generator* still reads those artefacts
the same way. It cannot prove the artefacts still match the archive: a page could
have been mis-transcribed when it was stored, or the archive could serve a
different capture than the one recorded.

This tool closes that gap by comparing a stored artefact against a freshly
obtained rendering of the same URL and reporting every row-level difference.

THE HONEST LIMIT, STATED IN THE OUTPUT
--------------------------------------
`web.archive.org` is not reachable from this project's sandbox over plain HTTP
(curl fails at TLS; only a document-render channel resolves it). So the "fresh"
side is supplied by the operator as a file, and both sides pass through the same
render channel. That makes this a *strong consistency check* — it catches typos,
dropped rows, changed values, a wrong capture timestamp and a stale artefact —
but it is not two independent observations of the archive. The report records
which channel produced each side so nobody mistakes it for one.

EXIT CODES
----------
0  every row matches
2  a difference was found (printed with the exact field, stored value and fresh value)
1  the inputs could not be compared at all — never reported as a pass
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import pathlib
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
HEADER_TOKENS = {"player", "date", "stat", "points"}


def artefact_header(text: str) -> dict:
    """Read the `# key: value` header block an artefact carries."""
    head: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("#"):
            if head:
                break
            continue
        m = re.match(r"^#\s*([a-z_]+):\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            # continuation lines of a wrapped header value
            if key in head:
                head[key] = (head[key] + " " + value).strip()
            else:
                head[key] = value
    return head


def correction_rows(text: str) -> list[dict]:
    """Extract correction rows from rendered Markdown of the official page.

    A row qualifies when its Stat cell contains the page's own phrasing
    ("changed from X to Y"). Header rows, navigation tables and the week/season
    link lists are therefore excluded without needing to know the page layout.
    """
    rows: list[dict] = []
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if len(cells) < 4:
            continue
        if {c.lower() for c in cells[:4]} & HEADER_TOKENS and "changed from" not in line:
            continue
        if set("".join(cells)) <= {"-", " ", ":"}:
            continue
        stat = cells[2]
        if "changed from" not in stat:
            continue
        player_cell = cells[0]
        meta = re.search(r"_([^_]+)_", player_cell)
        # Strip the link markup, the highlight-reel link text (a real parser bug
        # this project already hit once) and the trailing _POS - TEAM_ emphasis,
        # so the printed name is what a human reads on the page.
        name = re.sub(r"\[([^\]]*)\]\([^)]*\)", r" \1 ", player_cell)
        name = re.sub(r"_([^_]*)_", " ", name)
        name = re.sub(r"View Videos", " ", name)
        name = re.sub(r"https?://\S+", " ", name)
        name = re.sub(r"\s+", " ", name).strip()
        rows.append({
            "player": re.sub(r"\s+", " ", name).strip(),
            "position_team": (meta.group(1).strip() if meta else ""),
            "date": cells[1].strip(),
            "stat_text": re.sub(r"\s*\*\*\s*", " ", stat).strip(),
            "points": cells[3].strip(),
            "player_cell_raw": player_cell,
        })
    return rows


def row_identity(r: dict) -> tuple:
    return (r["player"], r["date"], r["stat_text"], r["points"])


def compare(stored_text: str, fresh_text: str) -> dict:
    """Row-level comparison. Order-insensitive; duplicates are counted."""
    stored = correction_rows(stored_text)
    fresh = correction_rows(fresh_text)

    def bag(rows):
        out: dict[tuple, int] = {}
        for r in rows:
            out[row_identity(r)] = out.get(row_identity(r), 0) + 1
        return out

    bs, bf = bag(stored), bag(fresh)
    missing = sorted(k for k in bs if bs[k] > bf.get(k, 0))
    extra = sorted(k for k in bf if bf[k] > bs.get(k, 0))

    sh = artefact_header(stored_text)
    fh = artefact_header(fresh_text)
    header_diffs = []
    for key in ("url", "snapshot_timestamp", "season", "week", "page_title"):
        if fh.get(key) and sh.get(key) and fh[key].split("#")[0] != sh[key].split("#")[0]:
            header_diffs.append({"field": key, "stored": sh[key], "fresh": fh[key]})

    matches = sum(min(bs[k], bf.get(k, 0)) for k in bs)
    identical = not missing and not extra and not header_diffs
    return {
        "identical": identical,
        "stored_rows": len(stored),
        "fresh_rows": len(fresh),
        "rows_matching": matches,
        "rows_only_in_stored": [{"player": k[0], "date": k[1], "stat": k[2], "points": k[3]} for k in missing],
        "rows_only_in_fresh": [{"player": k[0], "date": k[1], "stat": k[2], "points": k[3]} for k in extra],
        "header_differences": header_diffs,
        "stored_sha256": hashlib.sha256(stored_text.encode("utf-8")).hexdigest(),
        "fresh_sha256": hashlib.sha256(fresh_text.encode("utf-8")).hexdigest(),
    }


def render(result: dict, artefact: str, url: str | None) -> str:
    lines = [f"# Artefact verification — {artefact}"]
    if url:
        lines.append(f"Source URL: {url}")
    lines += [
        f"Stored rows: {result['stored_rows']} · Fresh rows: {result['fresh_rows']} · "
        f"Matching: {result['rows_matching']}",
        f"Result: {'IDENTICAL' if result['identical'] else 'DIFFERENCES FOUND'}",
    ]
    for r in result["rows_only_in_stored"]:
        lines.append(f"  ONLY IN STORED ARTEFACT: {r['player']} | {r['date']} | {r['stat']} | {r['points']}")
    for r in result["rows_only_in_fresh"]:
        lines.append(f"  ONLY IN FRESH RENDERING: {r['player']} | {r['date']} | {r['stat']} | {r['points']}")
    for h in result["header_differences"]:
        lines.append(f"  HEADER {h['field']}: stored={h['stored']!r} fresh={h['fresh']!r}")
    lines.append("")
    lines.append(
        "Residual risk: both sides were obtained through the same document-render channel, "
        "because web.archive.org is not reachable from this project's sandbox over plain HTTP. "
        "This check catches transcription drift, dropped rows and a wrong capture; it is not two "
        "independent observations of the archive.")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artefact", required=True, help="stored artefact in data/evidence/pages/")
    ap.add_argument("--fetched", required=True,
                    help="file containing a fresh rendering of the same archived URL")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    a = pathlib.Path(args.artefact)
    b = pathlib.Path(args.fetched)
    if not a.exists() or not b.exists():
        print(f"::error::cannot compare: {a} exists={a.exists()}, {b} exists={b.exists()}")
        return 1

    stored = a.read_text(encoding="utf-8")
    fresh = b.read_text(encoding="utf-8")
    head = artefact_header(stored)
    result = compare(stored, fresh)
    result.update({
        "artefact": str(a.relative_to(REPO_ROOT)) if str(a).startswith(REPO_ROOT) else str(a),
        "source_url": head.get("url"),
        "snapshot_timestamp": head.get("snapshot_timestamp"),
        "verified_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "channel": "document-render (HTML-to-markdown) on both sides",
    })
    print(render(result, result["artefact"], head.get("url")))
    if args.json_out:
        os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
        pathlib.Path(args.json_out).write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {args.json_out}")
    return 0 if result["identical"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
