# Recommendations — what still needs to be done

Ordered by expected value against the brief. Each item states the work, the
reason, and how we would know it succeeded.

---

## P0 — Close the main evidence and implementation gaps

### P0-1. ~~Validate the corrections parser against real archived HTML~~ — **DONE 2026-10-07 (rendered form); HTML path still open**

**What was done.** The archive became reachable through a document-render channel, so
the parser was run against **real archived page content** for the first time. It
produced **zero usable rows from the nine non-empty pages** (the tenth page explicitly
reported no corrections), for two reasons the fixtures could not catch: the real page
bolds the numbers (`from **0** to **1**`), and a player with a
highlight reel renders a second link in the same cell (`Case Keenum    View Videos`).
Both are fixed, both are covered by `TestRealArchivedPageContent`, and both were
**mutation-checked** (re-introducing either bug fails 6 and 2 tests).

`pipeline/ingest_rendered.py` now regenerates `data/verified_corrections_raw.json` from
stored artefacts in `data/evidence/pages/`, and `--check` fails if the parsed data
payload differs (the generated timestamp is intentionally ignored). The raw layer
is no longer hand-typed.

**Still open.** The HTML extraction path has never seen byte-exact HTML. Run
`python3 pipeline/run.py selfcheck` on Actions; reconcile if it reports < 10 rows.

**Done when.** `selfcheck` has a repeatable runner and CI records a successful
real-HTML check; unavailable archive access is reported as unknown, never as a
parser pass or an empty corrections page.

### P0-2. Expand the database from 74 rows to the full archived corpus — **now mechanical**

**Work.** First enumerate exact, observed Internet Archive CDX captures and make
a reviewable manifest. The search space includes 2010–2025, position filters
`O,1,2,3,4,7,8,11,12,13`, and weeks 1–22, but do not assume every combination
exists or that the observed CDX surface is a complete denominator. Fetch only
listed captures, one request at a time with backoff, verify the served timestamp
and rights/provenance, then ingest the stored page artefacts. The archive has
rate-limited requests (HTTP 429 was hit during the build).

**Why.** The brief asks for a *comprehensive* historical database. 74 rows are
a verified seed, not the deliverable. The rendered-page ingest path is
reproducible, but establishing completeness and preserving the source evidence
still requires research and careful retrieval.

**Progress 2026-10-07.** 36 → 74 rows, 4 → 6 seasons, 4 → 9 season-weeks. Use the CDX
API (`web.archive.org/cdx/search/cdx?url=fantasy.nfl.com/research/statcorrections&matchType=prefix&output=json`)
to enumerate exact capture timestamps before fetching: requesting a timestamp that has
no capture silently returns the *nearest* one (LIMITATIONS §11).

**Done when.** Coverage spans every season with archived snapshots, every row
retains a resolvable archived URL, and row counts per week are non-zero for
weeks known to have corrections.

### P0-3. Build and backtest a player-stat/PBP adapter

**Work.** On a permitted runner, first demonstrate access to genuine,
versioned player-stat or play-by-play vintages. Validate schemas; preserve raw
bytes, hashes and timestamps; normalize stable game/player IDs; diff additions,
removals, nulls and changed fields; then reconcile candidates against archived
official notices. Do not assume a weekly refresh means historical vintages are
retained or accessible.

**Why.** The current workflow compares scoreboard fields only. Download helpers
and upstream refresh documentation are leads, not a demonstrated player-stat
detector. A known-correction backtest is required before scheduling alerts.

**Done when.** At least one known correction is recovered from genuine before/
after vintages, with the exact old/new values, play/player/game identifiers,
capture times, hashes and reviewable source links; failure cases have tests.

---

## P1 — Make alerts trustworthy

### P1-1. Add a second independent mirror and require cross-source agreement

**Work.** Evaluate a second genuinely independent source, including its
upstream lineage, access terms, field coverage and revision history. Keep
one-source candidates explicitly `LOW_CONFIDENCE` / `NEEDS_CROSS_CHECK`; do not
label cross-source agreement as official NFL/Elias confirmation.

**Why.** A mirror bug is currently indistinguishable from an official
correction (LIMITATIONS §5). A second source may reduce false positives, but
correlated providers do not prove official attribution.

**Done when.** Every alert carries a `corroboration` field naming the sources,
lineage and agreement status; no mirror-only alert is labeled an official
correction.

### P1-2. Add per-player identity resolution

**Work.** Evaluate a documented, stable player-ID crosswalk (provider IDs such
as GSIS/PFR/ESPN only where licensed and supported) instead of relying on name
+ team. Record the crosswalk source and version.

**Why.** Name matching will mis-join on duplicate names and on mid-season
trades. Player prop markets are player-scoped, so a bad join is a wrong alert.

**Done when.** Every row carries a stable `gsis_id`, and a test asserts no row
joins on name alone.

### P1-3. Backtest the detector against known corrections

**Work.** After the player-stat adapter exists, acquire genuine source
vintages bracketing as many of the 74 transcribed correction rows as possible.
Replay each comparison and manually reconcile candidates to the archived
correction notice; record unavailable vintages rather than treating them as
misses or successes.

**Why.** The archived notices provide corrected values, but the repository does
not currently contain the before/after player-stat vintages needed for a
backtest. A detector not evaluated against genuine vintages is not a
demonstrated capability.

**Done when.** A report states the number of cases with valid before/after
vintages, detected cases, missed cases, false positives in the same windows,
and cases that could not be tested. Each classification remains reviewable.

---

### P1-4. Make `record_id` content-stable instead of positional

**The bug.** `record_id` is assigned as `SC-{i:04d}` in build order. On 2026-10-07,
adding 38 rows silently re-pointed **all six** of the site's case cards at different
records — `SC-0034` went from Michael Clark's 0 → 36 receiving yards to an unrelated
Roethlisberger row. Nothing failed; the page simply showed the wrong evidence under a
plausible-looking heading.

**Shipped mitigation.** The case cards now select by natural key
(`season|week|player|stat|correction_date`), and a test asserts every key resolves to
exactly one record. Note the date is required: the official page sometimes lists the
same correction on two consecutive days (LIMITATIONS §13).

**Still open.** `record_id` itself is still positional, so anything *external* that
cites one (an issue, an email, a bookmarked row) breaks on the next insert.

**Work.** Derive `record_id` from a hash of the row's identity
(`source_id|player|stat|original|corrected|correction_date`) so IDs are stable under
insertion.

**Done when.** Adding a row never changes an existing `record_id`, asserted by a test
that builds the database twice with an extra artefact present.

## P2 — Coverage and product

### P2-1. ~~Publish a public alert archive~~ — **DONE 2026-10-07**

`pipeline/feed.py` records each completed snapshot comparison passed to it,
including clean comparisons, in `data/alerts/feed.json`; the site renders the
feed with per-run SHA-256 hashes. The scheduled workflow publishes the updated
feed after a successful comparison.

**Still open.** Baseline-only, failed and aborted workflow attempts do not
necessarily create a feed row; users must check Actions for latest attempt
status. History is capped at 200 runs with no retention/export strategy, and
the feed records comparisons, not a human-readable "this week's corrections"
digest. No webhook delivery was exercised in this review.

### P2-2. Fantasy-platform re-scoring impact

Given a confirmed correction and a league's scoring rules, compute which
matchups would flip. This is the direct answer to "solve the problem of having
to manually check everything ourselves" for a league commissioner: the alert
should say *"and this flips Team A vs Team B"*, not just *"a sack moved"*.

### P2-3. Milestone and bonus threshold watch

Track season-to-date totals against round-number milestones, so a 1-yard change
that moves a player from 999 to 1,000 career/season receiving yards is surfaced
as a milestone event rather than a routine correction.

### P2-4. Historic reported flips, verified or excluded

Several widely repeated fan reports describe stat corrections flipping fantasy
playoff matchups. **None are in this database, because none could be verified to
primary-source standard.** Either find primary sources and add them, or document
explicitly that they are unverifiable so the gap is not mistaken for absence of
evidence.

---

## P3 — Engineering hygiene

- **P3-1.** Keep full `unittest` discovery as the no-dependency CI gate. Add
  coverage reporting only if it improves diagnostics without weakening that path.
- **P3-2.** Add schema validation (e.g. JSON Schema) for
  `verified_corrections_raw.json`, so a malformed contribution fails loudly
  rather than producing a plausible-looking wrong row.
- **P3-3.** The database and market-sensitivity JSON now record the byte count
  and SHA-256 of their exact `--games` input, but neither builder retains the
  full source file or a retrieval timestamp/Git commit. Preserve an immutable
  full snapshot or commit reference and test that the shipped outputs can be
  rebuilt from it. Do not call a moving upstream file pinned.
- **P3-4.** Terminate the `fantasy.nfl.com` retirement watch: a small scheduled
  probe that alerts us if the official corrections endpoint comes back, or if a
  documented successor appears.

---

## Explicitly not recommended

- **Do not scrape ESPN's JS app by reverse-engineering its private API.** It is
  brittle and may violate terms. Prefer a documented, permitted source with
  verified provenance; licensing alone does not prove official status.
- **Do not guess per-game prop lines.** Keep the project-defined screen labelled
  as a heuristic; a fabricated market, line or settlement makes the analysis
  untrustworthy.
- **Do not assert that a correction changed a game's final score** without
  primary-source evidence. The selected mirror study observed zero frozen-field
  changes across 28,323 overlapping comparisons; it does not establish that
  official score amendments never happen. Any asserted amendment needs direct,
  reviewable proof.
- **Do not grow the database by relaxing verification.** Row count is not the
  goal; checkable rows are.
