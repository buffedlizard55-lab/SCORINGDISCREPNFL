# Limitations

Ranked by how much each one blocks the brief. Everything here was verified by
hand during the build; where a limitation has a workaround, the workaround is
named. Nothing here is speculative.

---

## 1. BLOCKER — the official NFL correction feed has been retired

**What we found.** The authoritative, machine-readable release of NFL stat
corrections was `https://fantasy.nfl.com/research/statcorrections`, which
carried the header: *"View official stat corrections as released by the NFL
League Office and the official statistician of the NFL, Elias Sports Bureau."*

As of **2026-10-07**, that URL **302-redirects** to
`https://www.nfl.com/news/series/fantasy`, a news hub that now promotes
*"ESPN FANTASY — The Official Fantasy Game of the NFL."*

**Verified how.** Direct fetch of
`https://fantasy.nfl.com/research/statcorrections?position=O&statSeason=2025&statWeek=1`
returns the NFL fantasy news page. An archived snapshot from **2026-05-16**
still shows a working corrections page with season links through **2025**, which
dates the retirement to the 2026 offseason.

**Why it matters.** The single most valuable input — the official
human-curated list of corrections, with old and new values — is no longer
published at a stable, pollable URL. Any automated system must now *infer*
corrections by diffing third-party data, which is strictly worse: it can produce
false positives and it cannot tell an official Elias correction apart from a
data-provider bug.

**Workaround shipped.** Archived snapshots remain and are what the database is
built from. They are excellent for *history* and useless for *live* alerting.

**What would unblock it.** A licensed data feed that republishes Elias
corrections (e.g. a commercial sports-data vendor), or a documented public API
from whichever party now publishes them.

---

## 2. HIGH — the successor channel is a client-side JS app with no documented API

`https://fantasy.espn.com/football/statcorrections` is the current consumer-facing
corrections page. Fetching it returns an application shell and a support-page
listing, not data: the content is rendered client-side.

**Why it matters.** Even if ESPN now carries the official corrections, there is
no documented, stable, terms-friendly endpoint to poll. Scraping it would mean
reverse-engineering a private API — brittle, and likely against terms.

**Workaround shipped.** None for live use. Recorded as a first-class limitation
rather than papered over with a fragile scraper.

---

## 3. HIGH — the highest-resolution correction signal is network-blocked here

`nflverse/nflverse-pbp` publishes **raw play-by-play per game** and, per
nflverse's own internal workflow documentation, runs a job whose stated purpose
is to *"Refresh raw pbp of the last week … to incorporate stat corrections
during the week"* (`.github/workflows/refresh_raw_pbp.yaml`, cron
`0 2 * 1,2,9-12 3` → **Wednesdays 02:00 UTC**).

That is the ideal detector: a play-by-play vintage that is *explicitly refreshed
to fold in corrections*. Diffing two vintages of one game's pbp would pinpoint
the exact play that changed.

**Why it is blocked.** Release assets are served from
`release-assets.githubusercontent.com`, which is **not reachable from the
evaluation sandbox** (`curl` returns `000`). Only `github.com`,
`codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org` and
`files.pythonhosted.org` are on the allowlist. On a GitHub Actions runner this
restriction does not apply.

**Workaround shipped.** The adapter exists (`fetch.nflverse_pbp_asset_index`,
`fetch.download_release_asset`) and the release index is enumerable via
`api.github.com` even here — asset *bytes* are what cannot be fetched. The
`detect.py` engine is source-agnostic, so pointing it at two pbp vintages is a
configuration change, not a rewrite.

---

## 4. PARTLY RESOLVED — the parser is now validated against real page content, but still not byte-exact HTML

**What was true, and what happened when it was tested.** The parser shipped untested
against real input because `web.archive.org` is **not on this sandbox's bash egress
allowlist** (`curl` returns `000`). That gap was not hypothetical. On 2026-10-07 the
archive became reachable through a document-render channel, the parser was run against
real archived page content for the first time, and it produced **zero usable rows from
every page**, for two reasons the hand-written fixtures could not catch:

1. The real page **bolds the numbers** — `Tackle changed from **0** to **1**.` The
   numeric class in `_RE_CHANGED` cannot match `**0**`, so every row fell through to
   `parse_status="unparsed"` with `stat=None`. The old fixture had omitted the
   asterisks, which is why the suite was green while the parser was broken.
2. A player with a highlight reel renders a **second link in the same cell**, producing
   player names like `Case Keenum    View Videos`.

Both are fixed in `parse_corrections.normalize_cell` / `parse_rows`, and both are covered
by `TestRealArchivedPageContent`. Those tests were mutation-checked: re-introducing
either bug fails 6 and 2 tests respectively.

**What is still true.** The stored evidence is the **rendered** table
(HTML-to-markdown), not byte-exact HTML, because only the render channel reaches the
archive from here. Each artefact in `data/evidence/pages/` says so in its own header.
The HTML extraction path (`extract_table_cells`) therefore remains unproven against
real bytes.

**Workaround shipped.** `python3 pipeline/run.py selfcheck` fetches a known-good
archived page and asserts the parser recovers ≥10 fully-parsed rows — **run it on
Actions before trusting the HTML path.** Separately,
`python3 pipeline/ingest_rendered.py --check` fails if the shipped raw database is not
byte-reproducible from the stored artefacts, so the rows can never silently drift from
their evidence.

---

## 5. MEDIUM — the mirror is not the NFL

All differential detection runs against `nflverse/nfldata`, a well-maintained
third-party mirror of the NFL's official game statistics. It is not the NFL.

**Consequences, stated plainly:**

- A change in the mirror could be a **correction by the NFL** or a **bug fix in
  the mirror**. The detector cannot tell them apart.
- Mirror update latency means the observed *timestamp* of a change is not the
  timestamp the NFL published it.
- If the mirror is wrong and stays wrong, the detector sees nothing.
- The score-integrity result in §1.1 of the README is a statement about the
  mirror's retention window, **not** a claim about the NFL's internal records.

**Workaround.** Every alert is labelled
`detected_by_diff_pending_manual_confirmation` and carries `actually_changed_outcome: null`.
Cross-checking against a *second* independent mirror would materially improve
confidence; no suitable free second mirror was found.

---

## 6. MEDIUM — no free, redistributable source of per-game prop lines

To say "this 1-yard correction flipped a prop", you need the prop line. Real
per-game player-prop lines are a commercial product.

**Workaround shipped.** `market_rules.py` encodes only what is defensible:

- **Discrete scoring events** (touchdowns, field goals, extra points, two-point
  conversions, safeties, defensive scores) — binary, no threshold judgement needed.
- **Line-priced stats** — stats that books price at essentially every integer,
  almost always at `X.5`. For these, *any* integer change can cross a line. This
  is a statement about the stat's pricing convention, **not** an assertion that a
  line existed at a specific value.
- **Round-number milestones** (300 passing yards, 100 receiving yards, …) for
  bonus markets.

Per-game prop lines are **never guessed**.

---

## 7. MEDIUM — the database is a seed, not the comprehensive corpus

**74 verified rows across 9 season-weeks in 6 seasons** (2010 W1, 2012 W1, 2013 W1,
2015 W1, 2015 W16, 2017 W1, 2017 W16, 2018 W1, 2018 W14), parsed from 10 stored
archived pages. The archived corpus spans 2010–2025 × 10 position filters × 18+ weeks,
so the achievable ceiling is orders of magnitude larger.

**Rows per sampled week:** 2, 3, 6, 7, 7, 9, 11, 14, 15 (mean 8.2).

**What changed.** Expansion is no longer research work — it is mechanical. Each
archived page is stored in `data/evidence/pages/`; `pipeline/ingest_rendered.py`
parses them into the raw layer, and `--check` fails if the shipped copy drifts from
the artefacts. Adding a week is: store the page, re-run, rebuild.

**Why it is still not comprehensive.** Every page is a separate request against a
rate-limited archive, and the archive itself rate-limits (an HTTP 429 was hit during
the build). Bulk expansion belongs in a scheduled job with backoff, not in an
interactive session.

**Deliberate choice.** 74 rows that each regenerate from a stored archived page a
human can open beat thousands of rows nobody can check. Bulk expansion is the top
item in `RECOMMENDATIONS.md`.

---

## 11. MEDIUM — the archive serves a different timestamp than the one requested

Requesting `web.archive.org/web/<ts>/<url>` returns the **nearest** capture, which is
frequently *not* `<ts>`. Of the six pages newly fetched on 2026-10-07, **five** were
served from a different timestamp than requested (e.g. requested `20191016215648`,
served `20191019093854`).

**Why it matters.** Recording the requested timestamp would produce a provenance record
that does not match the bytes actually transcribed.

**Workaround shipped.** Each artefact records **both**: `snapshot_timestamp` (what was
actually served, and what is embedded in every link on the page) and
`requested_timestamp`. The CDX API
(`web.archive.org/cdx/search/cdx?url=…&matchType=prefix&output=json`) enumerates exact
capture timestamps up front and is the right way to target them.

## 12. LOW — the official page does not always print a team code

Two shapes were observed in real pages:

- **Defensive-unit rows** print the franchise nickname and no code (`_DEF_`).
- **Some player rows** print a position and no code at all — all four 2013 W1
  `Isaac Redman` rows render as `_RB_` with no team.

**Workaround shipped.** Nicknames resolve through an explicit, tested
`TEAM_NAME_TO_CODE` table (a test asserts every code it maps to actually occurs in the
authoritative schedule, so a typo fails the build). Rows where no code can be
established are left `team: null`, labelled `team_source: "not_printed_on_source"`,
flagged `TEAM_NOT_PRINTED`, and **no game join is attempted** — inferring a team would
put unsourced data in the database. 4 of 74 rows are in this state.

## 13. LOW — the official page sometimes lists the same correction twice

Dak Prescott, 2017 W16, `Passing Yards changed from 182 to 181` appears **twice** on the
same archived page, dated Dec 26 and Dec 27. Both rows are transcribed because both
were published; they are not duplicates to be deduplicated.

**Why it matters.** Any natural key that omits the correction date is ambiguous. This
is why the site's case cards are keyed on `season|week|player|stat|correction_date`.

---

## 8. LOW — `spread_line` sign convention is ambiguous in secondary sources

nflverse's `spread_line` field has been described inconsistently as to whether a
negative value means the home team is favoured. We could not resolve this to a
primary definition during the build.

**Workaround shipped.** `market_sensitivity.py` uses **only the magnitude**,
`|spread_line|`. That is correct under either convention, so the analysis cannot
be wrong because of it. The sign is never asserted.

---

## 9. LOW — a correction reverted between two snapshots is invisible

If a value changes and changes back between poll N and poll N+1, the diff sees
nothing.

**Workaround.** Poll frequency is the only lever. In season, `nfldata` commits
every ~30 minutes, so a 30-minute poll cadence reduces (but does not eliminate)
the window. A real-world example of exactly this failure mode was observed in
the wild during 2025: a team sack was removed and then restored across the
fantasy playoffs.

---

## 10. LOW — no SLA, and no published deadline, for how long corrections may arrive

The source pages do not state a deadline. Multiple secondary sources agree there
is no fixed schedule, and that corrections can arrive days or weeks later.

**Workaround shipped.** The build does not assume a deadline. It flags
`DATE_LATE` beyond 14 days and `DATE_INCONSISTENT` for anything before the game,
rather than silently rejecting or accepting late rows.

---

## Summary — what is genuinely blocked vs merely unfinished

| Limitation | Blocked, or unfinished? |
|---|---|
| 1. Official feed retired | **Blocked by an external party's decision.** Needs a licensed feed. |
| 2. ESPN channel is JS-only | **Blocked** absent a documented API or permission. |
| 3. pbp assets unreachable | **Environment-only.** Works on Actions. Not a design problem. |
| 4. Parser vs byte-exact HTML | **Partly resolved.** Validated against real rendered content; the HTML path still needs `selfcheck` on Actions. |
| 5. Mirror ≠ NFL | **Inherent.** Mitigate with a second source; cannot eliminate. |
| 6. No prop lines | **Commercial.** Model the convention, never guess values. |
| 7. Seed database (74 rows) | **Unfinished.** Now mechanical; needs a scheduled bulk job. |
| 11. Archive serves another timestamp | **Inherent.** Both timestamps recorded per artefact. |
| 12. No team code printed | **Inherent to the source.** Flagged, never inferred. |
| 13. Duplicate published rows | **Inherent to the source.** Date is part of every key. |
| 8–10. Convention/edge cases | **Unfinished or inherent.** Mitigations shipped. |

**Bottom line.** The *detection* problem is solvable and largely solved here. The
*authoritative-attribution* problem — knowing that a detected change is an
official Elias correction rather than a data glitch — is not solvable for free
as of 2026, because the channel that used to answer it was switched off.
