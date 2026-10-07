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
_MD_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_EMPHASIS = re.compile(r"[*_]{1,3}")

# Position token with no team, e.g. "_DEF_" on a defensive-unit row. The dashed
# form (_QB - BAL_) is tried first; this is the fallback, anchored to the end of
# the cell so it cannot fire on a letter inside a player's name.
_RE_POS_BARE = re.compile(r"\b(?P<pos>QB|RB|WR|TE|K|DEF|DL|LB|DB)\b\s*$")


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


def normalize_cell(s: str) -> str:
    """
    Reduce one rendered table cell to the plain wording the official page
    displayed, so that _RE_CHANGED can match it.

    TWO BUGS FOUND HERE ON 2026-10-07, by running this parser against real
    archived page content (data/evidence/pages/) rather than hand-written
    fixtures. Both would have silently produced zero usable rows:

    1. The real page wraps the numbers in bold: "Tackle changed from **0** to
       **1**."  _RE_CHANGED's numeric class [-\\d,.]+ cannot match "**0**", so
       every row fell through to parse_status="unparsed" with stat=None and
       original_value=None. The old fixture omitted the asterisks, which is why
       the test suite was green while the parser was broken.
    2. A player who has a highlight reel renders a second link in the same cell
       ("Case Keenum ... View Videos"). Stripping link syntax but keeping the
       text produced the player name "Case Keenum    View Videos".

    Both are fixed by (a) dropping emphasis markers, and (b) taking only the
    text before the position marker.
    """
    # Keep the link TEXT: on this page the player name IS the link text, so
    # collapsing "[Darrius Heyward-Bey](...)" to a space destroys the name.
    # The *trailing* "View Videos" link is dropped later by the prefix split in
    # parse_rows, not here.
    s = _MD_LINK.sub(r"\1", s)
    s = _MD_EMPHASIS.sub(" ", s)
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
        cells = [normalize_cell(c) for c in line.strip("|").split("|")]
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

        # Position/team sit at the END of the player cell; everything before the
        # marker is the name. Taking only the prefix (rather than deleting the
        # matched marker) is what keeps a trailing "View Videos" out of the name.
        pos = team = None
        player = player_cell
        pm = _RE_POS_TEAM.search(player_cell)
        if pm:
            pos, team = pm.group("pos"), pm.group("team")
            player = player_cell[: pm.start()]
        else:
            bm = _RE_POS_BARE.search(player_cell)
            if bm:
                pos = bm.group("pos")
                player = player_cell[: bm.start()]
        player = player.strip(" -") or None
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
