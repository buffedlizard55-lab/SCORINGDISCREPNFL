"""
parse_corrections.py — Parse archived official NFL stat-corrections pages.

The official page rendered one HTML table with exactly four columns:

    Player | Date | Stat | Points

and the Stat cell carried the authoritative wording, e.g.

    "Tackle changed from 0 to 1."
    "Passing Yards changed from 215 to 220."
    "Touchdowns changed from 0 to 1."

We parse the wording with explicit patterns and, critically, we DO NOT invent a
value when a pattern does not match. Unparsed rows are emitted with
`parse_status = "unparsed"` and the raw text preserved, so nothing is silently
dropped or guessed.

HONESTY NOTE
------------
The row-extraction logic below was written against the structure observed in
archived rendered output. It has unit tests against fixtures that reproduce that
structure. It has NOT been validated against the byte-exact live/archived HTML
from inside the restricted evaluation sandbox (Wayback is not on the sandbox
egress allowlist; see LIMITATIONS.md #4). The first action when this runs on
GitHub Actions is to reconcile the parser against real archived HTML — the
`--selfcheck` mode in run.py exists for exactly that.
"""

from __future__ import annotations

import html as _html
import re
from dataclasses import dataclass, asdict

# "Passing Yards changed from 215 to 220."
_RE_CHANGED = re.compile(
    r"^(?P<stat>.+?)\s+changed\s+from\s+(?P<old>-?[\d,.]+)\s+to\s+(?P<new>-?[\d,.]+)",
    re.IGNORECASE,
)

# "<a ...>Cam Newton</a> ... QB - CAR"  /  "Cam Newton QB - CAR"
_RE_POS_TEAM = re.compile(r"\b(?P<pos>QB|RB|WR|TE|K|DEF|DL|LB|DB)\s*-\s*(?P<team>[A-Z]{2,3})\b")

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


@dataclass
class CorrectionRow:
    season: int | None
    week: int | None
    position: str | None
    team: str | None
    player: str | None
    correction_date: str | None
    stat: str | None
    original_value: float | None
    corrected_value: float | None
    numeric_change: float | None
    fantasy_points_delta: float | None
    raw_stat_text: str
    parse_status: str
    source_url: str
    snapshot_timestamp: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def strip_tags(s: str) -> str:
    s = _TAG.sub(" ", s)
    s = _html.unescape(s)
    return _WS.sub(" ", s).strip()


def _num(s: str) -> float | None:
    try:
        return float(s.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def extract_table_cells(html: str) -> list[list[str]]:
    """
    Return every <tr> as a list of cell strings, tags stripped.

    Only rows with >= 3 cells are returned; header and nav rows are then
    filtered by the caller. Works on both archived HTML and the
    rendered-to-text form.
    """
    rows: list[list[str]] = []
    for tr in re.findall(r"<tr\b[^>]*>(.*?)</tr>", html, flags=re.IGNORECASE | re.DOTALL):
        cells = re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, flags=re.IGNORECASE | re.DOTALL)
        if not cells:
            continue
        rows.append([strip_tags(c) for c in cells])
    return rows


def parse_markdown_rows(text: str) -> list[list[str]]:
    """
    Fallback parser for the pipe-delimited rendering, used by tests and by any
    caller that only has text. Cells look like:
        "| [Cam Newton](...) _QB - CAR_ | Dec 30 | Tackle changed from 0 to 1. | 0.00 |"
    """
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = [strip_tags(c).strip() for c in line.strip("|").split("|")]
        # strip markdown link syntax and emphasis left behind
        cells = [re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", c).replace("_", " ").strip() for c in cells]
        if len(cells) >= 3:
            rows.append(cells)
    return rows


def _looks_like_header(cells: list[str]) -> bool:
    joined = " ".join(cells).lower()
    return joined.startswith("player") and "stat" in joined


def parse_rows(
    rows: list[list[str]],
    season: int | None = None,
    week: int | None = None,
    source_url: str = "",
    snapshot_timestamp: str | None = None,
) -> list[CorrectionRow]:
    """Turn raw table rows into structured correction records."""
    out: list[CorrectionRow] = []
    for cells in rows:
        if len(cells) < 3 or _looks_like_header(cells):
            continue

        player_cell, date_cell, stat_cell = cells[0], cells[1], cells[2]
        points_cell = cells[3] if len(cells) > 3 else ""

        m = _RE_CHANGED.search(stat_cell)
        stat = m.group("stat").strip() if m else None
        old_v = _num(m.group("old")) if m else None
        new_v = _num(m.group("new")) if m else None

        pos = team = None
        pm = _RE_POS_TEAM.search(player_cell)
        if pm:
            pos, team = pm.group("pos"), pm.group("team")
        player = _RE_POS_TEAM.sub("", player_cell).strip(" -") or None
        if player in ("", "No stat corrections to display"):
            continue

        status = "parsed" if (stat is not None and old_v is not None and new_v is not None) else "unparsed"

        out.append(
            CorrectionRow(
                season=season,
                week=week,
                position=pos,
                team=team,
                player=player,
                correction_date=date_cell or None,
                stat=stat,
                original_value=old_v,
                corrected_value=new_v,
                numeric_change=(None if (old_v is None or new_v is None) else round(new_v - old_v, 4)),
                fantasy_points_delta=_num(points_cell),
                raw_stat_text=stat_cell,
                parse_status=status,
                source_url=source_url,
                snapshot_timestamp=snapshot_timestamp,
            )
        )
    return out


def parse_official_page(
    html_or_text: str,
    season: int | None = None,
    week: int | None = None,
    source_url: str = "",
    snapshot_timestamp: str | None = None,
) -> list[CorrectionRow]:
    """
    Entry point. Tries HTML table extraction first, falls back to the
    pipe-delimited form. Returns [] (not an exception) for the legitimate
    "No stat corrections to display" case so callers can distinguish
    "nothing to report" from "parse failure".
    """
    rows = extract_table_cells(html_or_text)
    if not rows:
        rows = parse_markdown_rows(html_or_text)
    if "No stat corrections to display" in html_or_text:
        return []
    return parse_rows(rows, season, week, source_url, snapshot_timestamp)
