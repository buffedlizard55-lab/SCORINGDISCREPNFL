#!/usr/bin/env python3
"""Best-effort watcher for the legacy NFL Fantasy stat-corrections archive.

The watcher intentionally fails closed: a redirect, changed page layout, or
unparseable correction row is an error, never a silent "zero corrections".
It creates one idempotent GitHub issue for each source row. It does not infer
sportsbook lines, settlement outcomes, or whether a correction changed a game.
Only the Python standard library is required.
"""

from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from urllib.request import Request, urlopen

DEFAULT_SOURCE = "https://tab.fantasy.nfl.com/research/statcorrections"
DEFAULT_REPOSITORY = "buffedlizard55-lab/SCORINGDISCREPNFL"
CORRECTION_LABEL = "official-stat-correction"
HEALTH_LABEL = "nfl-monitor-health"
USER_AGENT = "SCORINGDISCREPNFL-correction-watch/1.0 (+https://github.com/buffedlizard55-lab/SCORINGDISCREPNFL)"


class SourceError(RuntimeError):
    """The public correction source could not be safely interpreted."""


class GitHubError(RuntimeError):
    """GitHub's public API rejected an alert operation."""


class TableParser(HTMLParser):
    """Collect plain-text cells from HTML table rows, including nested links."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[tuple[int | None, list[str]]] = []
        self._table_stack: list[int] = []
        self._next_table_id = 0
        self._row_table_id: int | None = None
        self._in_row = False
        self._in_cell = False
        self._cell_parts: list[str] = []
        self._row: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "table":
            self._next_table_id += 1
            self._table_stack.append(self._next_table_id)
        elif tag == "tr":
            self._in_row = True
            self._row = []
            self._row_table_id = self._table_stack[-1] if self._table_stack else None
        elif tag in {"td", "th"} and self._in_row:
            self._in_cell = True
            self._cell_parts = []
        elif tag in {"br", "p", "div"} and self._in_cell:
            self._cell_parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self._in_cell:
            text = re.sub(r"\s+", " ", "".join(self._cell_parts)).strip()
            self._row.append(text)
            self._cell_parts = []
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            if self._row:
                self.rows.append((self._row_table_id, self._row))
            self._row = []
            self._row_table_id = None
            self._in_row = False
        elif tag == "table" and self._table_stack:
            self._table_stack.pop()

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_parts.append(data)


STAT_CHANGE = re.compile(
    r"^(?P<stat>.+?)\s+changed\s+from\s+(?P<old>-?\d+(?:\.\d+)?)\s+to\s+(?P<new>-?\d+(?:\.\d+)?)[.]?$",
    re.IGNORECASE,
)
PLAYER = re.compile(
    r"^(?P<name>.+?)\s+(?P<position>QB|RB|WR|TE|K|PK|P|DEF|DL|LB|DB|OL)\s+-\s+(?P<team>[A-Z]{2,3})(?:\s+[A-Z]+)?$",
    re.IGNORECASE,
)


def numeric(value: str) -> int | float:
    """Return integer values as ints and fractional values as floats."""
    number = Decimal(value)
    if number == number.to_integral_value():
        return int(number)
    return float(number)


def correction_id(row: dict[str, Any]) -> str:
    stable = "|".join(
        str(row.get(key, ""))
        for key in ("season", "week", "player", "position", "team", "date", "stat", "old_value", "new_value")
    )
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()[:20]


def parse_player(raw: str) -> tuple[str, str | None, str | None]:
    match = PLAYER.fullmatch(raw.strip())
    if not match:
        return raw.strip(), None, None
    return (
        match.group("name").strip(),
        match.group("position").upper(),
        match.group("team").upper(),
    )


def parse_correction_html(source_html: str, season: int, week: int, source_url: str) -> list[dict[str, Any]]:
    """Parse a correction table or an explicit empty-state message.

    Unknown layouts raise SourceError so upstream page migrations cannot be
    misrepresented as weeks with no changes.
    """
    decoded = html.unescape(source_html)
    parser = TableParser()
    parser.feed(decoded)
    all_text = re.sub(r"\s+", " ", decoded).strip().lower()

    header: list[str] | None = None
    header_table_id: int | None = None
    header_row_index: int | None = None
    for row_index, (table_id, row) in enumerate(parser.rows):
        normalized = [cell.strip().lower() for cell in row]
        if {"player", "date", "stat"}.issubset(set(normalized)):
            header = normalized
            header_table_id = table_id
            header_row_index = row_index
            break

    if header is None:
        if "no stat corrections to display" in all_text or "no corrections to display" in all_text:
            return []
        raise SourceError("Correction page had neither the expected Player/Date/Stat table nor a recognized empty-state message.")

    data_rows: list[list[str]] = []
    assert header_row_index is not None
    for row_index, (table_id, row) in enumerate(parser.rows[header_row_index + 1 :], start=1):
        if table_id != header_table_id:
            continue
        normalized = [cell.strip().lower() for cell in row]
        if normalized == header:
            continue
        if not any(cell.strip() for cell in row):
            continue
        if len(row) != len(header):
            raise SourceError(
                f"Correction table row {row_index} has {len(row)} cells; expected {len(header)}."
            )
        data_rows.append(row)

    if not data_rows:
        if "no stat corrections to display" in all_text or "no corrections to display" in all_text:
            return []
        raise SourceError("Correction table had a header but no correction rows and no recognized empty-state message.")

    indices = {name: header.index(name) for name in ("player", "date", "stat")}
    points_index = header.index("points") if "points" in header else None
    records: list[dict[str, Any]] = []

    for row_number, cells in enumerate(data_rows, start=1):
        try:
            player_raw = cells[indices["player"]]
            date_raw = cells[indices["date"]]
            stat_raw = cells[indices["stat"]]
        except IndexError as exc:
            raise SourceError(f"Correction table row {row_number} is missing required cells.") from exc

        change = STAT_CHANGE.fullmatch(stat_raw.strip())
        if not change:
            raise SourceError(f"Unrecognized correction description in row {row_number}: {stat_raw!r}")

        player_name, position, team = parse_player(player_raw)
        old_value = numeric(change.group("old"))
        new_value = numeric(change.group("new"))
        point_change: float | None = None
        if points_index is not None and points_index < len(cells):
            points_raw = cells[points_index].strip()
            if points_raw:
                try:
                    point_change = float(Decimal(points_raw))
                except InvalidOperation:
                    raise SourceError(f"Unrecognized fantasy-point value in row {row_number}: {points_raw!r}")

        record: dict[str, Any] = {
            "season": season,
            "week": week,
            "player": player_name,
            "position": position,
            "team": team,
            "date": date_raw,
            "stat": change.group("stat").strip(),
            "old_value": old_value,
            "new_value": new_value,
            "delta": new_value - old_value,
            "fantasy_points_delta": point_change,
            "source_url": source_url,
            "source_row": row_number,
        }
        record["id"] = correction_id(record)
        record["market_classification"] = classify_market(record["stat"])
        records.append(record)

    return records


def classify_market(stat: str) -> str:
    """Classify likely market relevance without claiming an actual market exists."""
    text = stat.lower()
    if any(term in text for term in (
        "passing", "completion", "attempt", "rushing", "receiving", "reception",
        "touchdown", "interception", "sack", "fumble", "field goal", "extra point",
        "kickoff return", "punt return", "tackle", "assisted tackle", "pass defended",
        "safety", "blocked kick", "points allowed", "yards allowed", "total yards",
    )):
        return "possible_player_or_team_market"
    if re.search(r"\bgames?\s+played\b", text):
        return "fantasy_or_roster_only_unless_a_market_is_listed"
    return "unclassified_stat_change_review_required"


def fetch_bytes(url: str, timeout: int = 30, token: str | None = None) -> tuple[bytes, str, int]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json, text/html, application/json;q=0.9, */*;q=0.8",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read(), response.geturl(), response.status
    except HTTPError as exc:
        body = exc.read(500).decode("utf-8", errors="replace")
        raise SourceError(f"HTTP {exc.code} while fetching {url}: {body[:300]}") from exc
    except URLError as exc:
        raise SourceError(f"Network error while fetching {url}: {exc.reason}") from exc


def correction_page_url(base_url: str, season: int, week: int) -> str:
    parsed = urlsplit(base_url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params.update({
        "statCategory": "stats",
        "statSeason": str(season),
        "statType": "weekStats",
        "statWeek": str(week),
    })
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(params), ""))


def current_nfl_season(now: datetime | None = None) -> int:
    """Return the active season in fall, otherwise the most recently completed season."""
    now = now or datetime.now(timezone.utc)
    return now.year if now.month >= 9 else now.year - 1


def seasons_to_poll(base_season: int, lookback: int) -> list[int]:
    """Return the base season and the requested number of immediately prior seasons."""
    return [base_season - offset for offset in range(lookback)]


def poll_season(base_url: str, season: int, max_week: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for week in range(1, max_week + 1):
        url = correction_page_url(base_url, season, week)
        body, final_url, status = fetch_bytes(url)
        if status != 200:
            raise SourceError(f"Unexpected HTTP status {status} for {url}.")
        requested = urlsplit(url)
        landed = urlsplit(final_url)
        if landed.hostname != requested.hostname or "/research/statcorrections" not in landed.path:
            raise SourceError(
                f"Correction source redirected away from its expected page: {url} -> {final_url}. "
                "This is treated as a source outage, not an empty correction list."
            )
        try:
            source_html = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SourceError(f"Correction page was not valid UTF-8: {url}") from exc
        records.extend(parse_correction_html(source_html, season, week, final_url))
        # Be polite to the legacy page and reduce the chance of rate limiting.
        time.sleep(0.15)
    return records


class GitHubClient:
    def __init__(self, repository: str, token: str) -> None:
        if "/" not in repository:
            raise GitHubError("GITHUB_REPOSITORY must be owner/repository.")
        self.repository = repository
        self.token = token
        self.api_root = f"https://api.github.com/repos/{repository}"

    def request_json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = path if path.startswith("https://") else f"{self.api_root}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=30) as response:
                content = response.read()
                return json.loads(content.decode("utf-8")) if content else None
        except HTTPError as exc:
            detail = exc.read(1000).decode("utf-8", errors="replace")
            raise GitHubError(f"GitHub API {method} {url} returned HTTP {exc.code}: {detail[:500]}") from exc
        except URLError as exc:
            raise GitHubError(f"GitHub API network error for {url}: {exc.reason}") from exc

    def ensure_label(self, name: str, color: str, description: str) -> None:
        encoded = name.replace(" ", "%20")
        try:
            self.request_json("GET", f"/labels/{encoded}")
            return
        except GitHubError as exc:
            if "HTTP 404" not in str(exc):
                raise
        self.request_json("POST", "/labels", {"name": name, "color": color, "description": description})

    def list_issues(self, label: str, state: str = "all") -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        for page in range(1, 101):
            query = urlencode({"state": state, "labels": label, "per_page": 100, "page": page})
            batch = self.request_json("GET", f"/issues?{query}")
            if not isinstance(batch, list):
                raise GitHubError("GitHub issues endpoint returned an unexpected response.")
            issues.extend(item for item in batch if "pull_request" not in item)
            if len(batch) < 100:
                return issues
        raise GitHubError("GitHub issue pagination exceeded 10,000 records; refusing to risk duplicate alerts.")

    def create_issue(self, title: str, body: str, label: str) -> dict[str, Any]:
        return self.request_json("POST", "/issues", {"title": title[:250], "body": body, "labels": [label]})


def issue_marker(record_id: str) -> str:
    return f"<!-- nfl-correction:{record_id} -->"


def format_number(value: int | float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def correction_issue(record: dict[str, Any]) -> tuple[str, str]:
    delta = record["delta"]
    delta_label = f"{delta:+g}" if isinstance(delta, (int, float)) else str(delta)
    name = record["player"]
    stat = record["stat"]
    title = f"[NFL stat correction] {record['season']} W{record['week']:02d} — {name}: {stat} {format_number(record['old_value'])}→{format_number(record['new_value'])}"
    marker = issue_marker(record["id"])
    body = f"""{marker}

## Automated candidate — manual review required

The legacy NFL Fantasy stat-corrections page listed this row. The monitor has **not** checked sportsbook lines, prices, bet rules, settlements, or whether the game result changed.

- **Season / week:** {record['season']} / {record['week']}
- **Correction date as printed by source:** {record['date']}
- **Player / team / position:** {name} / {record.get('team') or 'not parsed'} / {record.get('position') or 'not parsed'}
- **Stat:** {stat}
- **Reported change:** {format_number(record['old_value'])} → {format_number(record['new_value'])} ({delta_label})
- **Market relevance:** {record['market_classification']}
- **NFL Fantasy default-score change:** {record.get('fantasy_points_delta') if record.get('fantasy_points_delta') is not None else 'not shown'}

[Open the source correction page]({record['source_url']})

### Verification checklist
1. Confirm the correction row and date at the source link.
2. Match player, game, team, and final official statistics against NFL GSIS / NFL.com logs and the gamebook.
3. Preserve the original value's source and determine whether it is a contemporaneous snapshot or a reconstruction.
4. Search archived sportsbook lines and the applicable settlement rules before describing any actual market effect.
5. Keep score/winner changes distinct from player-stat-only changes.

**This issue is a detection alert, not a verified historical database entry or a claim of market impact.**
"""
    return title, body


def health_issue(error: str, checked_at: str) -> tuple[str, str]:
    marker = "<!-- nfl-monitor-health:source-unavailable -->"
    title = "[NFL monitor health] Official correction source unavailable or changed"
    body = f"""{marker}

The scheduled correction watcher could not safely read the configured NFL Fantasy correction page at **{checked_at}**.

**Error:** `{error[:1200]}`

The monitor fails closed and did not interpret this as zero corrections. No correction alerts were emitted by this run. Review the source and update the parser/endpoint before relying on current-feed coverage.

This issue is a source-health warning, not a claim that the NFL issued or did not issue a correction.
"""
    return title, body


def emit_health_issue(client: GitHubClient, error: str) -> None:
    client.ensure_label(HEALTH_LABEL, "d93f0b", "Alerts when the automatic NFL stat-correction source is unavailable or changes format.")
    existing_open = client.list_issues(HEALTH_LABEL, state="open")
    marker = "<!-- nfl-monitor-health:source-unavailable -->"
    if any(marker in (issue.get("body") or "") for issue in existing_open):
        print("An open monitor-health issue already exists; not creating a duplicate.")
        return
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    title, body = health_issue(error, now)
    result = client.create_issue(title, body, HEALTH_LABEL)
    print(f"Created source-health issue: {result.get('html_url', result.get('number'))}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, help="Base NFL season year (defaults to active/most recently completed season).")
    parser.add_argument("--lookback-seasons", type=int, default=2, help="Number of most recent seasons to poll, including --season (default: 2).")
    parser.add_argument("--max-week", type=int, default=18, help="Last regular-season week to poll (default: 18).")
    parser.add_argument("--dry-run", action="store_true", help="Poll and print candidate rows without creating GitHub issues.")
    parser.add_argument("--source-base-url", default=os.getenv("NFL_CORRECTIONS_BASE_URL", DEFAULT_SOURCE))
    args = parser.parse_args(argv)

    if not 1 <= args.max_week <= 18:
        parser.error("--max-week must be between 1 and 18.")
    if not 1 <= args.lookback_seasons <= 5:
        parser.error("--lookback-seasons must be between 1 and 5.")
    season = args.season or current_nfl_season()
    if season < 2000 or season > datetime.now(timezone.utc).year + 1:
        parser.error("--season must be a plausible NFL season year.")
    seasons = seasons_to_poll(season, args.lookback_seasons)
    if seasons[-1] < 2000:
        parser.error("The requested season lookback extends before 2000.")

    token = os.getenv("GITHUB_TOKEN")
    repository = os.getenv("GITHUB_REPOSITORY", DEFAULT_REPOSITORY)
    client: GitHubClient | None = None
    if not args.dry_run:
        if not token:
            print("GITHUB_TOKEN is required outside --dry-run mode.", file=sys.stderr)
            return 2
        client = GitHubClient(repository, token)

    try:
        season_labels = ", ".join(str(year) for year in seasons)
        page_count = len(seasons) * args.max_week
        print(f"Polling official-correction candidate source for seasons {season_labels}, weeks 1-{args.max_week}.")
        print(f"Configured source: {args.source_base_url}")
        records: list[dict[str, Any]] = []
        for monitored_season in seasons:
            records.extend(poll_season(args.source_base_url, monitored_season, args.max_week))
    except SourceError as exc:
        message = str(exc)
        print(f"SOURCE ERROR: {message}", file=sys.stderr)
        if client is not None:
            try:
                emit_health_issue(client, message)
            except GitHubError as github_exc:
                print(f"Could not publish source-health issue: {github_exc}", file=sys.stderr)
        return 1

    print(f"Parsed {len(records)} source row(s) across up to {page_count} week page(s) in {len(seasons)} season(s).")
    if args.dry_run:
        for record in records:
            print(json.dumps(record, sort_keys=True))
        print("DRY RUN: no GitHub issues were created.")
        return 0

    assert client is not None
    client.ensure_label(
        CORRECTION_LABEL,
        "1d76db",
        "Unreviewed candidate row from the NFL Fantasy stat-corrections source.",
    )
    existing = client.list_issues(CORRECTION_LABEL, state="all")
    markers = {
        match.group(1)
        for issue in existing
        for match in [re.search(r"<!-- nfl-correction:([a-f0-9]{20}) -->", issue.get("body") or "")]
        if match
    }

    created = 0
    skipped = 0
    for record in records:
        if record["id"] in markers:
            skipped += 1
            continue
        title, body = correction_issue(record)
        result = client.create_issue(title, body, CORRECTION_LABEL)
        print(f"Created candidate alert: {result.get('html_url', result.get('number'))}")
        created += 1
        # Update local markers too in case duplicate rows occur in source pages.
        markers.add(record["id"])

    print(f"Alert run complete: {created} created, {skipped} already present, {len(records)} row(s) parsed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
