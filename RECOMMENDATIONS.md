# Recommendations — what still needs to be done

Ordered by expected value against the brief. Each item states the work, the
reason, and how we would know it succeeded.

---

## P0 — Unblock the two things that actually gate live alerting

### P0-1. ~~Validate the corrections parser against real archived HTML~~ — **DONE 2026-10-07 (rendered form); HTML path still open**

**What was done.** The archive became reachable through a document-render channel, so
the parser was run against **real archived page content** for the first time. It
produced **zero usable rows from every page**, for two reasons the fixtures could not
catch: the real page bolds the numbers (`from **0** to **1**`), and a player with a
highlight reel renders a second link in the same cell (`Case Keenum    View Videos`).
Both are fixed, both are covered by `TestRealArchivedPageContent`, and both were
**mutation-checked** (re-introducing either bug fails 6 and 2 tests).

`pipeline/ingest_rendered.py` now regenerates `data/verified_corrections_raw.json` from
stored artefacts in `data/evidence/pages/`, and `--check` fails if the shipped copy is
not byte-reproducible from them. The raw layer is no longer hand-typed.

**Still open.** The HTML extraction path has never seen byte-exact HTML. Run
`python3 pipeline/run.py selfcheck` on Actions; reconcile if it reports < 10 rows.

**Done when.** `selfcheck` prints `SELFCHECK PASS` in CI on every run.

### P0-2. Expand the database from 74 rows to the full archived corpus — **now mechanical**

**Work.** Add a scheduled job that walks the archived corpus
(2010–2025 × positions `O,1,2,3,4,7,8,11,12,13` × weeks 1–22), one request at a
time with exponential backoff, and appends to
`data/verified_corrections_raw.json`. The archive rate-limits (HTTP 429 was hit
during the build), so this must be a patient background job, not a burst.

**Why.** The brief asks for a *comprehensive* historical database. 74 rows is a
verified seed, not the deliverable. The parse path is now **proven against real pages**
and the ingest path is regenerable, so the remaining work is fetching, not research.

**Progress 2026-10-07.** 36 → 74 rows, 4 → 6 seasons, 4 → 9 season-weeks. Use the CDX
API (`web.archive.org/cdx/search/cdx?url=fantasy.nfl.com/research/statcorrections&matchType=prefix&output=json`)
to enumerate exact capture timestamps before fetching: requesting a timestamp that has
no capture silently returns the *nearest* one (LIMITATIONS §11).

**Done when.** Coverage spans every season with archived snapshots, every row
retains a resolvable archived URL, and row counts per week are non-zero for
weeks known to have corrections.

### P0-3. Wire the pbp differential detector on Actions

**Work.** Diff two vintages of `nflverse-pbp` raw play-by-play for one game
(fetch at game end, re-fetch after the Wednesday 02:00 UTC refresh) and emit the
changed plays. The engine is already source-agnostic; this is an adapter, not a
rewrite.

**Why.** Raw play-by-play is the highest-resolution correction signal available,
and nflverse explicitly refreshes it to fold in corrections (LIMITATIONS §3).
This is what turns "a stat changed" into "**this specific play** was re-scored",
which is the difference between an alert and an explanation.

**Done when.** A known historical correction is recovered by the diff, and the
changed play is reported with both vintages' values.

---

## P1 — Make alerts trustworthy

### P1-1. Add a second independent mirror and require cross-source agreement

**Work.** Add a second free schedule/results source. Only emit a high-severity
alert when both sources disagree with the snapshot in the same direction, or
label single-source alerts `LOW_CONFIDENCE` / `NEEDS_CROSS_CHECK`.

**Why.** A mirror bug is currently indistinguishable from an official
correction (LIMITATIONS §5). This is the single biggest false-positive risk in
the design, and the cheapest way to cut it.

**Done when.** Every alert carries a `corroboration` field naming the sources
that agree, and single-source alerts are visibly marked.

### P1-2. Add per-player identity resolution

**Work.** Join correction rows to the `nflverse/players` ID crosswalk
(`gsis_id` / `pfr_id` / `espn_id`) instead of matching on name + team.

**Why.** Name matching will mis-join on duplicate names and on mid-season
trades. Player prop markets are player-scoped, so a bad join is a wrong alert.

**Done when.** Every row carries a stable `gsis_id`, and a test asserts no row
joins on name alone.

### P1-3. Backtest the detector against known corrections

**Work.** For each of the 74 transcribed corrections, replay the detector using
snapshots bracketing that week and confirm it would have fired, with correct
severity, and with no false positives in the same window.

**Why.** A detector that has never been backtested against known ground truth is
an assertion, not a capability. This is the highest-value correctness work
available, because ground truth already exists in-repo.

**Done when.** A report shows detection rate and false-positive rate across all
74 historical cases.

> **Scope caveat worth stating before this is attempted.** The 74 rows are *player
> statistics* corrections. The detector as built diffs **scoreboard** fields, so it will
> correctly fire on **none** of them. A meaningful backtest first requires the
> play-by-play / weekly-stat differential from P0-3; backtesting the scoreboard diff
> against stat corrections would measure nothing.

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

`pipeline/feed.py` appends **every** detection run — including clean ones — to
`data/alerts/feed.json`, which the site renders as a "Live detection feed" section with
per-run SHA-256 hashes of both inputs. Recording clean runs is the point: without them,
"nothing changed" is indistinguishable from "it never ran". `detect.yml` now passes
`--feed` and re-syncs the published copy.

**Still open.** History is capped at 200 runs and there is no retention/export strategy
yet, and the feed records *runs*, not a human-readable "this week's corrections" digest.

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

- **P3-1.** Replace the unit-test harness with `pytest` + coverage, and add the
  suite to CI on every push (currently runnable but not gated in CI).
- **P3-2.** Add schema validation (e.g. JSON Schema) for
  `verified_corrections_raw.json`, so a malformed contribution fails loudly
  rather than producing a plausible-looking wrong row.
- **P3-3.** Add an integrity check that the shipped `discrepancies.json` is
  reproducible byte-for-byte from `verified_corrections_raw.json` + the pinned
  `games.csv`, so the derived layer can always be regenerated and audited.
- **P3-4.** Terminate the `fantasy.nfl.com` retirement watch: a small scheduled
  probe that alerts us if the official corrections endpoint comes back, or if a
  documented successor appears.

---

## Explicitly not recommended

- **Do not scrape ESPN's JS app by reverse-engineering its private API.** It is
  brittle and likely against terms. Prefer a licensed feed.
- **Do not guess per-game prop lines.** Model the pricing convention instead; a
  fabricated line makes the whole database untrustworthy.
- **Do not assert that a correction changed a game's final score** without a
  primary source. Our own evidence says this essentially never happens
  (28,323 snapshots, 0 revisions), so any such claim should be treated as
  extraordinary and demanded to be proven.
- **Do not grow the database by relaxing verification.** Row count is not the
  goal; checkable rows are.
