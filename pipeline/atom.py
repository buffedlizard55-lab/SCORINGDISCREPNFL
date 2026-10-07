#!/usr/bin/env python3
"""
atom.py — subscribable feeds (RFC 4287 Atom 1.0) published on GitHub Pages.

WHY THIS EXISTS
---------------
The brief asks for "an up to date current feed" that removes the need to check
manually. A webhook can do that, but a webhook needs a secret, needs somebody to
own an endpoint, and cannot be tried out by a reader. An Atom feed needs none of
that: it is a static file, published next to the site, that any feed reader,
browser extension or `curl` can poll. It is the only notification channel this
project can ship that works with **zero configuration and zero secrets**, so it
is the default answer to "how do I get told without checking?".

Two feeds are produced, and they are deliberately separate because they mean
different things:

  data/alerts/feed.atom       one entry per completed snapshot COMPARISON,
                              including clean ones. This is the monitor's pulse.
  data/corrections.atom       one entry per row of the verified corrections
                              database. This changes only when the database is
                              rebuilt from new evidence — it is not a live wire.

HONESTY RULES ENCODED IN THE OUTPUT
-----------------------------------
* Every alert entry carries the disclaimer that it is a machine-detected
  candidate from a third-party mirror, not a confirmed NFL/Elias correction.
* A clean comparison is published as an entry, with the number of records
  compared and both input SHA-256 values, so "nothing happened" is distinguishable
  from "nothing was checked" and from "the inputs were identical".
* Entry ids are derived from content (input hashes / record identity), never from
  a position in a list, so a reader's "already seen" state survives a rebuild.
* Correction entries use the database build time as `<updated>`, because the
  archived pages print a calendar date ("Sep 15") with no time. We do not invent
  a publication timestamp.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import sys
from xml.sax.saxutils import escape
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_URL = "https://buffedlizard55-lab.github.io/SCORINGDISCREPNFL/"
REPO_URL = "https://github.com/buffedlizard55-lab/SCORINGDISCREPNFL"
FEED_TAG_BASE = "tag:github.com,2026:buffedlizard55-lab/SCORINGDISCREPNFL"

DISCLAIMER = (
    "Machine-detected difference between two snapshots of a third-party mirror of the NFL "
    "record. A candidate for review, not a confirmed official NFL/Elias correction, and not "
    "a statement about any wager, line or settlement."
)


def _rfc3339(ts: str | None, fallback: str) -> str:
    """Normalise a timestamp to RFC 3339, or use the fallback. Never guesses a time."""
    if not ts:
        return fallback
    t = ts.strip()
    if t.endswith("Z"):
        return t
    try:
        d = _dt.datetime.fromisoformat(t)
    except ValueError:
        return fallback
    if d.tzinfo is None:
        d = d.replace(tzinfo=_dt.timezone.utc)
    return d.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _entry(entry_id: str, title: str, updated: str, content: str, link: str | None = None) -> str:
    parts = [
        "  <entry>",
        f"    <id>{escape(entry_id)}</id>",
        f"    <title>{escape(title)}</title>",
        f"    <updated>{escape(updated)}</updated>",
    ]
    if link:
        parts.append(f'    <link rel="alternate" href="{escape(link, {chr(34): "&quot;"})}"/>')
    parts += [
        f'    <content type="html">{escape(content)}</content>',
        "  </entry>",
    ]
    return "\n".join(parts)


def _table(rows: list[tuple[str, str]]) -> str:
    """Small HTML table for entry content; escaped by the caller."""
    out = ["<table>"]
    for k, v in rows:
        out.append(f"<tr><th>{k}</th><td>{v}</td></tr>")
    out.append("</table>")
    return "".join(out)


def build_detection_feed(feed: dict, site_url: str = SITE_URL, now: str | None = None) -> str:
    now = now or _now()
    runs = feed.get("runs", []) or []
    entries = []
    for r in runs:
        # Atom requires every <id> in a feed to be unique. Two clean runs that
        # compared byte-identical snapshots share the same input hashes, so a
        # hash-of-hashes id COLLIDES (found while validating the first output).
        # Identity therefore includes which snapshot directories were compared
        # and when — still content-derived, never a list position.
        ident = "|".join(str(r.get(k) or "") for k in
                         ("old_snapshot", "new_snapshot", "checked_at"))
        entry_id = f"{FEED_TAG_BASE}/comparison/{hashlib.sha256(ident.encode('utf-8')).hexdigest()[:16]}"
        total = int(r.get("alerts_total", 0))
        if total:
            title = f"{total} candidate scoreboard change(s) — review required"
        elif r.get("identical_inputs"):
            title = "Clean comparison (inputs byte-identical — no source movement observed)"
        else:
            title = f"Clean comparison — {r.get('records_compared')} finished games, no frozen-field change"

        rows = [
            ("Status", r.get("status") or ""),
            ("Compared at", r.get("checked_at") or ""),
            ("Records compared", str(r.get("records_compared") or "")),
            ("Old snapshot", f"{r.get('old_snapshot') or ''} (sha256 {r.get('old_sha256') or ''})"),
            ("New snapshot", f"{r.get('new_snapshot') or ''} (sha256 {r.get('new_sha256') or ''})"),
            ("Inputs identical", "yes — this comparison observed no source movement"
             if r.get("identical_inputs") else "no"),
            ("Min severity", str(r.get("min_severity") if r.get("min_severity") is not None else "")),
            ("Verification status", r.get("verification_status") or ""),
            ("Outcome changed", "not asserted (null)" if r.get("actually_changed_outcome") is None
             else str(r.get("actually_changed_outcome"))),
        ]
        content = _table(rows)
        for a in (r.get("alerts") or [])[:20]:
            ctx = a.get("context") or {}
            content += (
                "<p><b>" + f"{a.get('game_id')} {ctx.get('away_team', '')}@{ctx.get('home_team', '')}".strip()
                + f"</b> — {a.get('stat')}: {a.get('original_value')} → {a.get('corrected_value')} "
                f"({a.get('severity_label')}, {a.get('category')})<br/>{a.get('reason')}</p>"
            )
        content += f"<p><i>{DISCLAIMER}</i></p>"
        entries.append(_entry(entry_id, title, _rfc3339(r.get("checked_at"), now), content,
                              link=f"{site_url}#feed"))

    updated = _rfc3339(runs[0].get("checked_at") if runs else None, now)
    body = "\n".join(entries) if entries else _entry(
        f"{FEED_TAG_BASE}/comparison/none-recorded",
        "No completed comparison recorded yet",
        updated,
        "<p>This checkout has no recorded snapshot comparison. Absence of entries is not a clean "
        "result; it means the monitor has not produced one.</p>",
    )
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>{escape(FEED_TAG_BASE + "/comparisons")}</id>
  <title>NFL scoring-discrepancy monitor — comparison feed</title>
  <subtitle>Every completed snapshot comparison, including clean ones. {escape(DISCLAIMER)}</subtitle>
  <updated>{escape(updated)}</updated>
  <link rel="self" href="{escape(site_url)}data/alerts/feed.atom"/>
  <link rel="alternate" href="{escape(site_url)}"/>
  <author><name>SCORINGDISCREPNFL monitor</name><uri>{escape(REPO_URL)}</uri></author>
  <rights>Research artefact. Data originates from a third-party mirror of the NFL record and from
archived NFL League Office / Elias Sports Bureau correction pages.</rights>
{body}
</feed>
"""


def build_corrections_feed(db: dict, site_url: str = SITE_URL, now: str | None = None) -> str:
    now = now or _now()
    meta = db.get("meta", {})
    built = _rfc3339(meta.get("generated_at"), now)
    records = db.get("records", []) or []
    entries = []
    for r in records:
        key = "|".join(str(r.get(k) or "") for k in
                       ("season", "week", "player", "stat", "correction_date_text",
                        "original_value", "corrected_value", "source_url_archived"))
        entry_id = f"{FEED_TAG_BASE}/correction/{hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]}"
        title = (f"{r.get('season')} W{r.get('week')} — {r.get('player')}: {r.get('stat')} "
                 f"{r.get('original_value')} → {r.get('corrected_value')}")
        rows = [
            ("Game", r.get("final_score") or r.get("game_id") or "not joined"),
            ("Game date", r.get("game_date") or ""),
            ("Correction date (as printed)", r.get("correction_date_text") or ""),
            ("Days game → correction", str(r.get("days_from_game_to_correction")
                                           if r.get("days_from_game_to_correction") is not None else "")),
            ("Numeric change", str(r.get("numeric_change") if r.get("numeric_change") is not None else "")),
            ("Why (per source)", r.get("correction_reason") or
             "not stated in the archived official notice"),
            ("Review priority", f"{r.get('severity_label')} (severity {r.get('severity')}) — project heuristic"),
            ("Markets potentially affected", ", ".join(r.get("markets_potentially_affected") or []) or "none identified"),
            ("Changed the official outcome?", "not established for this row"),
            ("Review flags", ", ".join(r.get("review_flags") or []) or "none"),
            ("Source", f"{r.get('source_publisher') or ''} — {r.get('source_url_archived') or ''}"),
        ]
        content = _table(rows) + (
            "<p><i>Transcribed from an archived page published by the NFL League Office and Elias "
            "Sports Bureau. Values are as printed by that page. Market categories are screening "
            "heuristics, not evidence that a market was offered or that a wager settled.</i></p>")
        link = r.get("source_url_archived") or f"{site_url}#database"
        entries.append(_entry(entry_id, title, built, content, link=link))

    body = "\n".join(entries) if entries else _entry(
        f"{FEED_TAG_BASE}/correction/none", "No verified corrections in this build", built,
        "<p>The database is empty. That is a coverage statement, not evidence that no corrections exist.</p>")
    counts = meta.get("counts", {})
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <id>{escape(FEED_TAG_BASE + "/corrections")}</id>
  <title>Verified NFL stat corrections — database feed</title>
  <subtitle>{escape(str(counts.get('total_records', len(records))))} rows transcribed from archived
NFL League Office / Elias Sports Bureau correction pages, one entry per row with its archived source
link. Entry timestamps are the database build time: the archived pages print a calendar date with no
time, so no publication timestamp is invented.</subtitle>
  <updated>{escape(built)}</updated>
  <link rel="self" href="{escape(site_url)}data/corrections.atom"/>
  <link rel="alternate" href="{escape(site_url)}"/>
  <author><name>SCORINGDISCREPNFL</name><uri>{escape(REPO_URL)}</uri></author>
{body}
</feed>
"""


def write(path: str, content: str) -> str:
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text(content, encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--feed", default=os.path.join(REPO_ROOT, "data", "alerts", "feed.json"))
    ap.add_argument("--database", default=os.path.join(REPO_ROOT, "data", "discrepancies.json"))
    ap.add_argument("--outdir", default=os.path.join(REPO_ROOT, "data"))
    ap.add_argument("--site-url", default=SITE_URL)
    args = ap.parse_args()

    site = args.site_url if args.site_url.endswith("/") else args.site_url + "/"
    written = []

    if os.path.exists(args.feed):
        feed_json = json.loads(pathlib.Path(args.feed).read_text(encoding="utf-8"))
        written.append(write(os.path.join(args.outdir, "alerts", "feed.atom"),
                             build_detection_feed(feed_json, site)))
    else:
        # No feed yet is a real state; publish it rather than shipping nothing,
        # so a subscriber sees "no comparison recorded" instead of a 404.
        written.append(write(os.path.join(args.outdir, "alerts", "feed.atom"),
                             build_detection_feed({"runs": []}, site)))

    if os.path.exists(args.database):
        db = json.loads(pathlib.Path(args.database).read_text(encoding="utf-8"))
        written.append(write(os.path.join(args.outdir, "corrections.atom"),
                             build_corrections_feed(db, site)))

    # XML well-formedness is a contract, not a hope: a malformed feed breaks
    # every subscriber silently.
    import xml.etree.ElementTree as ET
    for p in written:
        ET.parse(p)
        print(f"wrote {p} ({os.path.getsize(p)} bytes, well-formed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
