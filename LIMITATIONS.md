# Limitations

Ranked by how much each one blocks the brief. Each entry distinguishes what
was observed or tested from what remains unverified; a workaround is called out
only where one has actually been implemented.

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

**What could help.** A licensed or documented feed may provide corroboration, but it would only address attribution if its NFL/Elias provenance, correction history, timestamps, access terms and field coverage are established for the specific product. No vendor product has been evaluated or licensed here; a feed is not assumed to be authoritative merely because it is commercial.

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

## 3. HIGH — player-stat monitoring is not implemented end-to-end

The repository contains release-metadata/download helpers for nflverse play-by-
play assets, and the upstream repository documents a weekly refresh intended to
incorporate stat corrections. That makes the source worth evaluating; it does
not demonstrate that a usable, stable vintage is available to this project's
workflow or that the data can be replayed historically.

**What is missing.** No validated adapter currently downloads two genuine
player-stat vintages, verifies and retains their bytes/hashes, normalizes game
and player identities, separates additions/removals/nulls, diffs the changed
plays/stat fields, and reconciles candidates against a known official correction.
No player-stat detector has been backtested, and access from a GitHub Actions
run has not been demonstrated as part of this review.

**Environment note.** The release assets were not reachable from this sandbox;
that limits local experimentation but does not prove they will work on Actions.
Conversely, Actions availability alone would not solve version retention,
schema, identity, provenance, licensing or false-positive issues.

**Status.** Helpers and source documentation are leads, not a shipped
player-stat monitoring capability. The player-stat adapter and historical
backtest remain P0 work in `RECOMMENDATIONS.md`.

---

## 4. PARTLY RESOLVED — the parser is now validated against real page content, but still not byte-exact HTML

**What was true, and what happened when it was tested.** The parser shipped untested
against real input because `web.archive.org` is **not on this sandbox's bash egress
allowlist** (`curl` returns `000`). That gap was not hypothetical. On 2026-10-07 the
archive became reachable through a document-render channel, the parser was run against
real archived page content for the first time, and it produced **zero usable rows from
the nine non-empty pages** (the tenth archived page explicitly reports no corrections),
for two reasons the hand-written fixtures could not catch:

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
`python3 pipeline/ingest_rendered.py --check` fails if the shipped raw database's
parsed payload differs from the stored artefacts (the generated timestamp is ignored),
so substantive row drift is surfaced.

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
Cross-checking against a genuinely independent second source could improve
confidence, but no such source is integrated or validated in this project.
Provider lineage would need review because two services may share upstream data.

---

## 6. MEDIUM — no verified per-game prop-line or settlement record

To say "this 1-yard correction flipped a prop", the project would need the
actual offered line, book, time, applicable settlement rules and (for a claim
about a wager) the relevant wager/settlement record. None is present in this
repository. This review did not establish that no free source exists. Any
candidate source must be evaluated separately for coverage, timestamps, terms
and rights before being used.

**Workaround shipped.** `market_rules.py` and `market_sensitivity.py` use
project-defined screening heuristics only:

- **Scoring-related stats** are flagged as high-priority candidates but do not
  prove points were added to the scoreboard.
- **Candidate line-market categories** and **round-number review markers**
  prioritize human review; they are not a verified inventory of markets,
  offers, specific lines, prices or settlement rules.
- The 2025–26 screen uses mirror-supplied closing-line values and numeric
  distance only; it does not determine wager flips or settlements.

Per-game lines, bets and outcomes are **never guessed**.

---

## 7. MEDIUM — the database is a seed, not the comprehensive corpus

**74 verified rows across 9 sampled season-weeks in 6 seasons** (2010 W1, 2012 W1,
2013 W1, 2015 W1, 2015 W16, 2017 W1, 2017 W16, 2018 W1, 2018 W14), parsed from 10
stored archived pages. An observed archive search surface includes candidate
captures across 2010–2025, multiple position filters and weeks, but that surface
has not been validated as a complete denominator or a guaranteed collection.

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

**Consequence.** The current workflow polls on a configured seasonal schedule,
not continuously. A change-and-revert between snapshots is therefore invisible;
the cadence is best-effort and is not a feed or Actions SLA. No verified example
of this exact failure mode is included in the evidence database.

**Now quantified rather than assumed.** The source-movement study
(`data/evidence/upstream_churn_study.json`) sampled 45 genuine upstream vintages
across 59 days. The mirrored file's bytes changed in **44 of 44** sampled
intervals, so the blind spot is real and frequently exercised: between any two
polls the source moves many times. What it did *not* do in that window is change
a frozen scoreboard field on an already-final game (0 of 321,009 comparisons),
while changing 179 other fields on 91 finished games. Reducing the polling
interval shrinks the blind spot; it cannot close it. Upstream Git history is the
only way to look inside an interval, and that is what the study does.

---

## 10. LOW — exact publication latency and any general deadline remain unknown

The archived pages expose correction calendar dates, not the exact publication
time. In the selected 74-row seed, the 70 joined rows are 1–4 calendar days from
game date to displayed correction date (mode 3). This sample does not establish
a general deadline or that all later corrections are captured. We did not verify
a primary-source rule setting a universal correction deadline.

**Workaround shipped.** The build flags `DATE_LATE` beyond its project-defined
14-day review threshold and `DATE_INCONSISTENT` for a date before the game; the
threshold is a heuristic, not an NFL policy.

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
`TEAM_NAME_TO_CODE` table (a test asserts every mapped code occurs in the
versioned third-party schedule snapshot, so a typo fails the build). Rows where no code can be
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

## 14. MEDIUM — a notification can be delivered and never read

`pipeline/notify.py` records an HTTP outcome per attempt. A 2xx from a Slack or
Discord incoming webhook means the endpoint **accepted a payload**. Neither
platform returns a read receipt, a delivery guarantee to a device, or any signal
that a human saw the message. There is no email or SMS channel, no user account
model and no subscription database in this repository.

**Consequence.** "The alert was sent" is the strongest claim the system can make.
Anything stronger would be invented.

**Workaround shipped.** The pull-based Atom feeds (`data/alerts/feed.atom`,
`data/corrections.atom`) need no secret and no endpoint, so a reader can verify
independently what was published and when. Delivery receipts, idempotency keys
and dead letters make the push path auditable after the fact, and a dead letter
fails the run instead of passing silently.

---

## 15. MEDIUM — the watchdog cannot see GitHub-side or human-side failure

`health.yml` exists because a detector cannot report its own death, and it reads
artefacts that the detector writes. It therefore cannot distinguish:

* a workflow **disabled, queued, throttled or cancelled by GitHub** from one that
  ran and found nothing — the artefacts simply stop advancing, which the watchdog
  reports as stale, but the cause is invisible to it;
* a **runner outage** or a rejected `git push` from a source that went quiet;
* a delivered notification that nobody read (see §14).

**Consequence.** Health statuses are statements about this repository's
artefacts, not about GitHub's scheduler or about people. The Actions history
remains the authority on whether an attempt happened.

**Workaround shipped.** Every check reports `unknown` rather than `ok` when the
evidence needed to decide is absent, and the report carries a plain-language next
action pointing at the Actions history. Staleness is a hard failure (exit 3).

---

## 16. MEDIUM — archive verification uses one channel on both sides

`web.archive.org` is not reachable from this project's sandbox over plain HTTP
(TLS handshake fails; `curl` returns 000). Archived pages are obtained through a
document-render channel, so `pipeline/verify_artefact.py` compares a stored
artefact against a fresh rendering **obtained the same way**.

**Consequence.** The re-read catches transcription drift, dropped rows, changed
values and a wrong capture timestamp — it was mutation-checked to prove that —
but it is not two independent observations of the archive. A systematic
rendering error would appear on both sides and pass.

**Workaround shipped.** Every artefact records its retrieval channel, both the
requested and served Wayback timestamps, and a SHA-256; the verification log
(`data/evidence/verification_log.json`) states which artefacts were re-read and
which were not, and the re-read inputs themselves are committed under
`data/evidence/verification/` (fresh rendering, verifier result, and the two
mutation-check inputs), so the check is repeatable from the repository alone:
`python3 pipeline/verify_artefact.py --artefact data/evidence/pages/2018-W14-O.md
--fetched data/evidence/verification/2018-W14-O-fresh-rendering.md` → exit 0,
11/11 identical. `run.py selfcheck` remains the path for reconciling byte-exact
HTML on a runner that can reach the archive directly.

---

## 17. LOW — provider identifier columns are renumbered long after a game ends

The source-movement study observed 34 revisions of already-published values on
finished games. Most were wholesale renumbering of the `ftn` and `pff` columns —
which sit in the mirrored file's block of provider game-identifier columns
alongside `gsis`, `nfl_detail`, `nflverse`, `espn` and `pfr` — on 2024 games,
observed in September 2026, roughly 21 months after those games were played.

**Consequence.** Anything keyed on a provider identifier rather than on the
mirror's own `game_id` can silently re-point at a different game. This is a
concrete instance of the general identity-join risk in `RECOMMENDATIONS.md` P1-2.

**Workaround shipped.** This project keys on `game_id` (`season_week_away_home`)
and never on `ftn`/`pff`/`espn`. Both columns are outside the frozen set, so they
cannot generate an alert.

---

## Summary — what is genuinely blocked vs merely unfinished

| Limitation | Blocked, or unfinished? |
|---|---|
| 1. Official feed retired | **Blocked by an external party's decision.** Needs a licensed feed. |
| 2. ESPN channel is JS-only | **Blocked** absent a documented API or permission. |
| 3. Player-stat adapter/backtest | **Unfinished.** Local asset access is restricted; Actions access and a production adapter remain unproven. |
| 4. Parser vs byte-exact HTML | **Partly resolved.** Validated against real rendered content; the HTML path still needs `selfcheck` on an appropriate runner. |
| 5. Mirror ≠ NFL | **Inherent.** Requires independent provenance/corroboration; no second source is integrated. |
| 6. Per-game lines/settlements | **Unverified source gap.** Do not assume they are unavailable everywhere or infer them. |
| 7. Seed database (74 rows) | **Unfinished.** Now mechanical; needs a scheduled bulk job. |
| 11. Archive serves another timestamp | **Inherent.** Both timestamps recorded per artefact. |
| 12. No team code printed | **Inherent to the source.** Flagged, never inferred. |
| 13. Duplicate published rows | **Inherent to the source.** Date is part of every key. |
| 8–10. Convention/edge cases | **Unfinished or inherent.** Mitigations shipped. §9 is now quantified by the source-movement study. |
| 14. Delivery ≠ read | **Inherent to the platforms.** No webhook offers a read receipt; receipts and dead letters are the ceiling. |
| 15. Watchdog blind spots | **Inherent.** It reads artefacts, not GitHub's scheduler or people. Reports unknown, never ok-by-default. |
| 16. One-channel archive verification | **Environmental.** Strong consistency check, not independent observation; both timestamps and hashes recorded. |
| 17. Provider id renumbering | **Inherent to the mirror.** Avoided by keying on `game_id` only. |

**Bottom line.** A narrow scoreboard-mirror diff, a published run feed,
subscribable Atom feeds, receipted webhook delivery and an independent health
watchdog are implemented and tested; they do not solve the broader player-stat
correction problem. The player-stat adapter/backtest is unfinished, and
mirror-only alerts cannot establish official NFL/Elias attribution. Delivery can
be proven accepted but never proven read. The retired correction channel is an
external blocker; alternatives require product-specific evidence, rights and
provenance review. The source-movement study now supplies a measured noise floor
— 179 non-scoreboard edits on finished games in 59 days against 0 scoreboard
edits — which is why the detector's scope is narrow on purpose.
