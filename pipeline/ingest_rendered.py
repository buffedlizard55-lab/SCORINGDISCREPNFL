"""
ingest_rendered.py — Turn stored archived-page artefacts into raw correction rows.

WHY THIS EXISTS
---------------
`parse_corrections.py` was written against the *structure* of the official NFL
stat-corrections page but, until 2026-10-07, had never been run against real
archived content, because web.archive.org is not on this sandbox's bash egress
allowlist. That gap (LIMITATIONS.md #4) was not hypothetical: running the parser
against real archived page text on 2026-10-07 found TWO bugs that would have
produced zero usable rows from every real page (see normalize_cell's docstring).

This script closes the loop. Each artefact in data/evidence/pages/ is a stored
copy of the table portion of one archived official page, together with the URL
and snapshot timestamp it came from. Feeding those through the real parser is
what makes the database reproducible rather than hand-typed.

WHAT IS AND IS NOT CLAIMED
--------------------------
The artefacts are the *rendered* form of the page (HTML-to-markdown), not
byte-exact HTML, because only the render channel reaches the archive from this
sandbox. Every artefact says so in its own header. Nothing here is inferred:
the player, position, team, date, stat wording, original value, corrected value
and published points delta are exactly what the archived page displayed.

USAGE
-----
    python3 pipeline/ingest_rendered.py                 # report only
    python3 pipeline/ingest_rendered.py --write         # rebuild raw JSON
    python3 pipeline/ingest_rendered.py --check         # exit 1 on any drift
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from parse_corrections import parse_official_page  # noqa: E402

PAGES_DIR = ROOT / "data" / "evidence" / "pages"
RAW_PATH = ROOT / "data" / "verified_corrections_raw.json"

PUBLISHER = (
    "NFL League Office / Elias Sports Bureau (NFL.com Fantasy), "
    "archived by the Internet Archive"
)

_HEADER = re.compile(r"^#\s?(?P<key>[a-z_]+):\s?(?P<val>.*)$")
_WAYBACK_PREFIX = re.compile(r"^https?://web\.archive\.org/web/[^/]+/")


def live_url_from(archived_url: str, explicit: str = "") -> str:
    """
    Recover the original (now-retired) NFL.com URL from its Wayback wrapper.

    The archive URL is "https://web.archive.org/web/<timestamp>/<original>", so
    stripping the prefix yields the exact URL the official corrections page was
    published at. Every record must carry it so a reader can see both where the
    evidence lives today and where the league originally published it.
    """
    if explicit:
        return explicit
    return _WAYBACK_PREFIX.sub("", archived_url or "")


def read_artefact(path: pathlib.Path) -> tuple[dict, str]:
    """Split an artefact into its metadata header and its table body."""
    meta: dict[str, str] = {}
    body: list[str] = []
    last_key = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            m = _HEADER.match(line)
            if m:
                last_key = m.group("key")
                meta[last_key] = m.group("val").strip()
            elif last_key:  # continuation of a wrapped header value
                meta[last_key] = (meta[last_key] + " " + line.lstrip("# ").strip()).strip()
            continue
        body.append(line)
    return meta, "\n".join(body)


def source_id_from(meta: dict, path: pathlib.Path) -> str:
    if meta.get("source_id"):
        return meta["source_id"]
    season = meta.get("season")
    week = meta.get("week")
    pf = meta.get("position_filter_label") or meta.get("position_filter") or "O"
    if season and week:
        return f"WAYBACK-{season}W{int(week):02d}-{pf}"
    return "WAYBACK-" + path.stem.upper()


def ingest(pages_dir: pathlib.Path = PAGES_DIR) -> dict:
    """Parse every artefact and return a raw-source document."""
    sources: list[dict] = []
    corrections: list[dict] = []
    problems: list[str] = []

    for path in sorted(pages_dir.glob("*.md")):
        meta, body = read_artefact(path)
        url = meta.get("url")
        if not url:
            problems.append(f"{path.name}: no `url` header — cannot verify provenance")
            continue

        season = int(meta["season"]) if meta.get("season") else None
        week = int(meta["week"]) if meta.get("week") else None
        sid = source_id_from(meta, path)

        rows = parse_official_page(
            body,
            season=season,
            week=week,
            source_url=url,
            snapshot_timestamp=meta.get("snapshot_timestamp"),
        )
        # A week with no corrections renders the literal string
        # "No stat corrections to display". That is a legitimate empty result, not
        # a parse failure, so it is only a problem if the artefact did not say so.
        expect_empty = str(meta.get("expect_empty", "")).lower() == "true"
        if not rows and not expect_empty:
            problems.append(f"{path.name}: parser returned 0 rows")

        unparsed = [r for r in rows if r.parse_status != "parsed"]
        if unparsed:
            problems.append(
                f"{path.name}: {len(unparsed)} row(s) did not parse, e.g. "
                f"{unparsed[0].raw_stat_text!r}"
            )
        missing = [r for r in rows if not r.player]
        if missing:
            problems.append(f"{path.name}: {len(missing)} row(s) with no player name")

        sources.append(
            {
                "source_id": sid,
                "publisher": PUBLISHER,
                "page_title": meta.get("page_title", "Stat Corrections - NFL.com Fantasy"),
                "snapshot_timestamp": meta.get("snapshot_timestamp"),
                "url": url,
                "live_url_now_retired": live_url_from(url, meta.get("live_url", "")),
                "season": season,
                "week": week,
                "position_filter": meta.get("position_filter", "O"),
                "evidence_artefact": str(path.relative_to(ROOT)),
                "retrieval_channel": meta.get("retrieval_channel", ""),
                "expected_empty": expect_empty,
                "rows_parsed": len(rows),
            }
        )

        for r in rows:
            corrections.append(
                {
                    "source_id": sid,
                    "season": season,
                    "week": week,
                    "player": r.player,
                    "position": r.position,
                    "team": r.team,
                    "correction_date": r.correction_date,
                    "stat": r.stat,
                    "original_value": r.original_value,
                    "corrected_value": r.corrected_value,
                    "published_points_delta": r.fantasy_points_delta,
                    "raw_stat_text": r.raw_stat_text,
                    "parse_status": r.parse_status,
                }
            )

    return {
        "_README": [
            "GENERATED FILE — do not edit by hand.",
            "",
            "Regenerate with: python3 pipeline/ingest_rendered.py --write",
            "",
            "Every row below is parsed by pipeline/parse_corrections.py from a stored",
            "artefact in data/evidence/pages/. Each artefact is the table portion of one",
            "archived snapshot of the official NFL stat-corrections page, published by the",
            "NFL League Office and the official statistician of the NFL, Elias Sports",
            "Bureau, and carries the exact snapshot URL so a human can open it and check",
            "every line by hand.",
            "",
            "NOTHING HERE IS INFERRED. Player, position, team, correction date, stat",
            "wording, original value, corrected value and the published fantasy-points",
            "delta are exactly what the archived page displayed. Derived fields (numeric",
            "change, market severity, market relevance) are computed downstream by",
            "pipeline/build_database.py and are labelled as derived there.",
        ],
        "generated_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": "pipeline/ingest_rendered.py",
        "sources": sources,
        "corrections": corrections,
        "_problems": problems,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="write data/verified_corrections_raw.json")
    ap.add_argument("--check", action="store_true", help="exit 1 if the stored file would change")
    args = ap.parse_args()

    doc = ingest()
    problems = doc.pop("_problems")
    n_src, n_row = len(doc["sources"]), len(doc["corrections"])
    print(f"artefacts parsed : {n_src}")
    print(f"correction rows  : {n_row}")
    for s in doc["sources"]:
        cnt = sum(1 for c in doc["corrections"] if c["source_id"] == s["source_id"])
        print(f"  {s['source_id']:26s} {cnt:4d} rows  {s['url']}")

    if problems:
        print("\nPROBLEMS (irregularities flagged for review):")
        for p in problems:
            print("  -", p)

    blob = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"

    if args.check:
        # Compare the PAYLOAD, not the bytes: `generated_at` legitimately differs
        # on every run and must not be reported as drift.
        def strip_ts(d):
            d.pop("generated_at", None)
            return d

        same = (
            RAW_PATH.exists()
            and strip_ts(json.loads(RAW_PATH.read_text(encoding="utf-8")))
            == strip_ts(json.loads(blob))
        )
        if not same:
            print("\nDRIFT: data/verified_corrections_raw.json is not reproducible from the artefacts.")
            print("Fix: python3 pipeline/ingest_rendered.py --write")
            return 1
        print("\nOK: raw database is reproducible from data/evidence/pages/.")
        return 1 if problems else 0

    if args.write:
        RAW_PATH.write_text(blob, encoding="utf-8")
        print(f"\nwrote {RAW_PATH.relative_to(ROOT)}")

    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
