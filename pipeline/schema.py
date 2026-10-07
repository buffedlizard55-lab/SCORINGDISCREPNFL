#!/usr/bin/env python3
"""
schema.py — validation for the generated raw-corrections layer.

WHY THIS EXISTS
---------------
`data/verified_corrections_raw.json` is the fact layer the whole project rests
on. It is generated, but a generator can be wrong, and a malformed row does not
crash anything: it flows through `build_database.py` into a plausible-looking
record on the public site. That is the worst failure mode available to this
project — a wrong number presented as verified.

So the fact layer is validated against an explicit contract, with no third-party
JSON Schema library, because the repo's rule is stdlib-only.

WHAT IS CHECKED
---------------
Structure   every required key is present, with the right type, and nothing
            extra has appeared that nobody has thought about.
Cross-file  every correction's `source_id` exists in `sources`; every source's
            declared `rows_parsed` equals the number of corrections actually
            carrying that id; every `evidence_artefact` exists on disk.
Provenance  every archived URL is a web.archive.org capture whose 14-digit
            timestamp matches the recorded `snapshot_timestamp` — the thing a
            reviewer clicks to verify a row.
Plausibility season/week are in NFL-shaped ranges; values are numeric; original
            and corrected differ (an unchanged value is not a correction);
            correction dates look like the "Sep 12" the page prints.

Every failure is returned as a structured problem with the exact JSON path, so a
build fails with "corrections[31].season is 2112" rather than with a bad page.

WHAT THIS CANNOT CHECK
----------------------
It cannot check truth. A row can be perfectly well-formed and still be a
mis-transcription of the archived page; only re-reading the artefact catches
that (`ingest_rendered.py --check` regenerates the layer from the artefacts, and
`data/evidence/pages/` holds the pages themselves).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_PATH = os.path.join(REPO_ROOT, "data", "verified_corrections_raw.json")

SOURCE_KEYS = {
    "source_id": str, "publisher": str, "page_title": str, "snapshot_timestamp": str,
    "url": str, "live_url_now_retired": str, "season": int, "week": int,
    "position_filter": str,
    "evidence_artefact": str, "retrieval_channel": str, "expected_empty": bool,
    "rows_parsed": int,
}
# The position filter values the official page's own UI defines. A capture taken
# under a filter nobody recognises would silently describe a different page.
POSITION_FILTERS = {"O", "1", "2", "3", "4", "7", "8", "11", "12", "13"}
CORRECTION_KEYS = {
    "source_id": str, "season": int, "week": int, "player": str, "position": str,
    "team": (str, type(None)), "correction_date": str, "stat": str,
    "original_value": (float, int, type(None)), "corrected_value": (float, int, type(None)),
    "published_points_delta": (float, int, type(None)), "raw_stat_text": str,
    "parse_status": str,
}
POSITIONS = {"QB", "RB", "WR", "TE", "K", "DEF", "DL", "LB", "DB", "P", "LS", ""}
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
DATE_RE = re.compile(rf"^({'|'.join(MONTHS)})\s+\d{{1,2}}$")
TS_RE = re.compile(r"^\d{14}$")
ARCHIVE_RE = re.compile(r"^https://web\.archive\.org/web/(\d{14})")
CURRENT_YEAR = _dt.datetime.now(_dt.timezone.utc).year
# The NFL's first season was 1920; a week beyond 22 does not exist in any era.
SEASON_RANGE = (1920, CURRENT_YEAR + 1)
WEEK_RANGE = (1, 22)


def problem(path: str, code: str, message: str) -> dict:
    return {"path": path, "code": code, "message": message}


def _check_keys(obj: dict, contract: dict, path: str, out: list[dict]) -> None:
    for key, typ in contract.items():
        if key not in obj:
            out.append(problem(f"{path}.{key}", "MISSING_KEY", f"required key '{key}' is absent"))
            continue
        if not isinstance(obj[key], typ) or (isinstance(obj[key], bool) and bool not in _as_tuple(typ)):
            out.append(problem(
                f"{path}.{key}", "BAD_TYPE",
                f"expected {_type_names(typ)}, got {type(obj[key]).__name__}: {obj[key]!r}"))
    extra = sorted(set(obj) - set(contract))
    if extra:
        out.append(problem(path, "UNEXPECTED_KEY",
                           f"key(s) not in the contract: {', '.join(extra)}"))


def _as_tuple(typ) -> tuple:
    return typ if isinstance(typ, tuple) else (typ,)


def _type_names(typ) -> str:
    return "/".join(t.__name__ for t in _as_tuple(typ))


def _in_range(value, lo: int, hi: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and lo <= value <= hi


def validate(raw: dict, root: str = REPO_ROOT) -> list[dict]:
    """Return a list of structured problems. Empty list means the layer is valid."""
    out: list[dict] = []

    for key in ("sources", "corrections"):
        if key not in raw:
            out.append(problem(key, "MISSING_KEY", "top-level section is absent"))
    if out:
        return out
    if not isinstance(raw["sources"], list) or not isinstance(raw["corrections"], list):
        out.append(problem("sources/corrections", "BAD_TYPE", "both sections must be JSON arrays"))
        return out

    # ---- sources ---------------------------------------------------------
    sources_by_id: dict[str, dict] = {}
    for i, s in enumerate(raw["sources"]):
        path = f"sources[{i}]"
        if not isinstance(s, dict):
            out.append(problem(path, "BAD_TYPE", "source entry must be an object"))
            continue
        _check_keys(s, SOURCE_KEYS, path, out)
        sid = s.get("source_id")
        if isinstance(sid, str):
            if sid in sources_by_id:
                out.append(problem(f"{path}.source_id", "DUPLICATE_ID", f"'{sid}' is defined twice"))
            sources_by_id[sid] = s

        ts = s.get("snapshot_timestamp")
        if isinstance(ts, str) and not TS_RE.match(ts):
            out.append(problem(f"{path}.snapshot_timestamp", "BAD_TIMESTAMP",
                               f"'{ts}' is not a 14-digit Wayback timestamp"))
        url = s.get("url")
        if isinstance(url, str):
            m = ARCHIVE_RE.match(url)
            if not m:
                out.append(problem(f"{path}.url", "NOT_AN_ARCHIVE_CAPTURE",
                                   f"'{url}' is not a https://web.archive.org/web/<14-digit>/ URL"))
            elif isinstance(ts, str) and m.group(1) != ts:
                out.append(problem(f"{path}.url", "TIMESTAMP_MISMATCH",
                                   f"URL capture {m.group(1)} != recorded snapshot_timestamp {ts}"))
        live = s.get("live_url_now_retired")
        if isinstance(live, str) and not live.startswith("https://fantasy.nfl.com/"):
            out.append(problem(f"{path}.live_url_now_retired", "UNEXPECTED_ORIGIN",
                               f"'{live}' is not the retired official corrections origin"))
        artefact = s.get("evidence_artefact")
        if isinstance(artefact, str):
            if not os.path.exists(os.path.join(root, artefact)):
                out.append(problem(f"{path}.evidence_artefact", "ARTEFACT_MISSING",
                                   f"'{artefact}' does not exist, so this source cannot be re-checked"))
        if not _in_range(s.get("season"), *SEASON_RANGE):
            out.append(problem(f"{path}.season", "OUT_OF_RANGE", f"{s.get('season')!r} outside {SEASON_RANGE}"))
        if not _in_range(s.get("week"), *WEEK_RANGE):
            out.append(problem(f"{path}.week", "OUT_OF_RANGE", f"{s.get('week')!r} outside {WEEK_RANGE}"))
        pf = s.get("position_filter")
        if isinstance(pf, str) and pf not in POSITION_FILTERS:
            out.append(problem(f"{path}.position_filter", "UNKNOWN_FILTER",
                               f"'{pf}' is not one of the page's own position filters "
                               f"({', '.join(sorted(POSITION_FILTERS))})"))

    # ---- corrections -----------------------------------------------------
    per_source: dict[str, int] = {}
    ids_seen: dict[str, str] = {}
    for i, c in enumerate(raw["corrections"]):
        path = f"corrections[{i}]"
        if not isinstance(c, dict):
            out.append(problem(path, "BAD_TYPE", "correction entry must be an object"))
            continue
        _check_keys(c, CORRECTION_KEYS, path, out)
        sid = c.get("source_id")
        if isinstance(sid, str):
            per_source[sid] = per_source.get(sid, 0) + 1
            src = sources_by_id.get(sid)
            if src is None:
                out.append(problem(f"{path}.source_id", "UNKNOWN_SOURCE",
                                   f"'{sid}' has no entry in sources[], so the row has no citable origin"))
            else:
                if c.get("season") != src.get("season") or c.get("week") != src.get("week"):
                    out.append(problem(
                        f"{path}.season/week", "SCOPE_MISMATCH",
                        f"row says {c.get('season')} W{c.get('week')} but its source page is "
                        f"{src.get('season')} W{src.get('week')}"))
        if not _in_range(c.get("season"), *SEASON_RANGE):
            out.append(problem(f"{path}.season", "OUT_OF_RANGE", f"{c.get('season')!r} outside {SEASON_RANGE}"))
        if not _in_range(c.get("week"), *WEEK_RANGE):
            out.append(problem(f"{path}.week", "OUT_OF_RANGE", f"{c.get('week')!r} outside {WEEK_RANGE}"))
        pos = c.get("position")
        if isinstance(pos, str) and pos.upper() not in POSITIONS:
            out.append(problem(f"{path}.position", "UNKNOWN_POSITION",
                               f"'{pos}' is not a position the official page's filters define"))
        date = c.get("correction_date")
        if isinstance(date, str) and not DATE_RE.match(date):
            out.append(problem(f"{path}.correction_date", "BAD_DATE",
                               f"'{date}' does not look like the 'Sep 12' form the page prints"))
        player = c.get("player")
        if isinstance(player, str) and not player.strip():
            out.append(problem(f"{path}.player", "EMPTY_VALUE", "player/unit name is blank"))
        if isinstance(player, str) and "View Videos" in player:
            # Regression guard for a real parser bug: the highlight-reel link used
            # to leak into the player cell.
            out.append(problem(f"{path}.player", "PARSER_LEAK",
                               "'View Videos' link text leaked into the player name"))
        ov, cv = c.get("original_value"), c.get("corrected_value")
        if ov is None or cv is None:
            out.append(problem(f"{path}.values", "MISSING_VALUE",
                               "a correction needs both the original and the corrected value"))
        elif ov == cv:
            out.append(problem(f"{path}.values", "NO_CHANGE",
                               f"original and corrected are both {ov}; that is not a correction"))
        if c.get("parse_status") != "parsed":
            out.append(problem(f"{path}.parse_status", "UNPARSED_ROW",
                               f"parse_status is {c.get('parse_status')!r}; the fact layer ships parsed rows only"))

        ident = json.dumps({k: c.get(k) for k in sorted(CORRECTION_KEYS)}, sort_keys=True, default=str)
        if ident in ids_seen:
            out.append(problem(path, "DUPLICATE_ROW",
                               f"identical to {ids_seen[ident]}; the same correction is recorded twice"))
        else:
            ids_seen[ident] = path

    # ---- declared vs actual row counts -----------------------------------
    for sid, s in sources_by_id.items():
        declared, actual = s.get("rows_parsed"), per_source.get(sid, 0)
        if declared != actual:
            out.append(problem(f"sources[{sid}].rows_parsed", "COUNT_MISMATCH",
                               f"declares {declared} row(s) but {actual} correction(s) carry this source_id"))
        if s.get("expected_empty") and actual:
            out.append(problem(f"sources[{sid}].expected_empty", "EXPECTED_EMPTY_BUT_HAS_ROWS",
                               f"page is recorded as empty but {actual} row(s) were parsed from it"))

    return out


def report(problems: list[dict], raw: dict) -> str:
    n_sources = len(raw.get("sources", []))
    n_rows = len(raw.get("corrections", []))
    if not problems:
        return f"OK — {n_rows} correction row(s) across {n_sources} source page(s) satisfy the contract."
    lines = [f"FAILED — {len(problems)} problem(s) in {n_rows} row(s) / {n_sources} source(s):"]
    for p in problems[:50]:
        lines.append(f"  [{p['code']}] {p['path']}: {p['message']}")
    if len(problems) > 50:
        lines.append(f"  ... and {len(problems) - 50} more")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=RAW_PATH)
    ap.add_argument("--root", default=REPO_ROOT)
    ap.add_argument("--json", action="store_true", help="emit machine-readable problems")
    args = ap.parse_args()

    raw = json.loads(pathlib.Path(args.raw).read_text(encoding="utf-8"))
    problems = validate(raw, root=args.root)
    if args.json:
        print(json.dumps({"valid": not problems, "problems": problems}, indent=1))
    else:
        print(report(problems, raw))
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
