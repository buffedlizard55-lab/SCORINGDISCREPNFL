# Three-pass review — 2026-10-07

> **PERIOD DOCUMENT — do not read as current.** This file records a three-pass review
> performed on 2026-10-07 against the repository as it stood at that time. It describes
> a 36-row and then 74-row database; the database has since been expanded to **141 rows
> across 13 seasons and 16 season-weeks from 22 evidence artefacts**. Row counts,
> severity splits, test counts and latency ranges quoted below are historical. For
> current numbers see the root [`README.md`](../README.md), [`FINDINGS.md`](../FINDINGS.md)
> and [`LIMITATIONS.md`](../LIMITATIONS.md).

## Pass 1 — repository, evidence, implementation
Repository was a single 19-byte README, no application or tests. Pages already configured for main/root. Built source register, seven-case seed with original/corrected values and per-stat evidence, static responsive site, README charter, agent startup instructions, research/limitations report and a local SQLite snapshot detector. Sources reviewed through web search and page retrieval; article excerpts preserved, not full copyrighted archives.

## Pass 2 — assumptions and edge cases
- Separated play, game, season-to-date and apparent-final scopes; Dawson correction +3 is not the +6 including later overtime play.
- Polamalu acknowledgement is not a restored score; Manning retained values are not a correction.
- Gray defender conflict surfaced rather than guessed. Mendenhall 2010 reason marked unconfirmed by NFL.
- Source metadata migration dates not used as correction timestamps. No sportsbook settlement claimed.
- Reject empty/HTML/malformed/nonfinite feeds; missing values never become zero; additions/removals not scored as changes; fractional sacks preserved; failed parse leaves baseline untouched.
- Changed source plan after finding retired NFL endpoint and legacy nflverse release path. Actual current CSV download blocked by network restrictions; no invented baseline or “live” badge.

## Pass 3 — original-request audit
Eight automated tests pass; deterministic generation and JavaScript syntax check pass. Site contains all seven cards without requiring JavaScript and uses relative assets for repository Pages paths. Search/filter code reviewed; browser visual/interaction automation not run. Source links retrieved for core narratives; no automated full link-crawl or semantic fact-check guarantee is claimed. Tests validate structure/arithmetic, not truth.

Partial requirements remain explicit: exhaustive history, incidence estimates, precision timing, direct official current feed, automatic notifications and all-category coverage are NOT delivered. Autonomous research does not remove access/licensing limits. Next-session plan is in RESEARCH.md. Do not describe this release as fully satisfying those requirements.

## Concurrent-main reconciliation
Main advanced to `30f402c` during implementation, causing three conflicts. Reviewed
its README, dataset, scraper and deployment workflow. Preserved its documents,
case leads and old UI in `docs/archive/`, prominently marked unverified/superseded.
Did not admit Reddit-only cases or the guessed-column scraper. Kept existing
Pages Actions workflow, added tests/build before deploy, and generate identical
root/site copies so either existing deployment mode serves the current release.
No concurrent branch or PR was modified. Re-ran all local checks after resolution.

## Second concurrent-main reconciliation
PR #2 then merged as `be9b359`, adding a much broader dataset, `pipeline/`, a
scheduled detector and docs-based Pages deployment. Preserved that work and its
active README/site/workflows. This PR is now **supplemental**: the seven-case UI
lives in `research-seed/`, the local detector remains separately scoped, and the
source mappings are not silently mixed into the broader database. Earlier status
statements above apply to this contribution, not the newer main implementation.
Root README links both contributions. No claim is made that this session
independently verified PR #2's archived sources or historical mirror study.

Final integrated local verification: all **40 tests** (32 pipeline + 8 seed) pass;
both main and supplemental JavaScript syntax checks pass; supplemental build is
deterministic; diff against current main has no new whitespace errors.

PR #4 subsequently merged (`9a96509`) to restore root Pages and add validation.
Kept its root site, validation workflow and sync script intact. Re-ran all **42
integrated tests** successfully. Supplemental code still never overwrites root.

## Follow-up three-pass review — 2026-10-07

The fixed Arena branch was initially 16 commits behind the current `origin/main`.
Fast-forwarded **the same required branch** to current main before integrating
new research. Preserved the existing root Pages deployment, 36-row correction
database, mirror study, pipeline, validation workflow and README charter; did
not apply the stale parallel `docs/` draft over those files.

### Pass 1 — implement and verify
Added five source-linked case studies to the supplemental `data/events.json`
seed and `data/sources.json` evidence register: Cutler (2008), Fitzpatrick and
Parrish (2010), Manning and Nicks (2011), Brees and Snead (2015), and Elliott
(2018). Regenerated the supplemental static case library; updated the root site
link and README. These are separate from the 36-row archived-official-correction
database. No sportsbook line or settlement is claimed.

### Pass 2 — review and fix
Compared each new case against the available official NFL gamebook, contemporaneous
team reporting and/or independent contemporaneous reports. Retained explicit
conflicts: Cutler's accessible NFL PDF says 299 while the Denver Post footnote
and MyFantasyLeague report 300; the Denver Post page also shows a 2016 update,
so the footnote's original publication time is not established. Bills reporting
says 373 then 374 before 382; NJ.com says Brees 504 while
the final NFL book says 505. Recorded the Nicks play at 6:37 Q1 and the FleaFlicker
report time without treating it as an NFL timestamp. For Elliott, the final NFL
book confirms one fumble, zero lost and one own recovery; corrected the stale
candidate wording that could imply the fumble itself disappeared. Kept the
initial Sheard attribution and correction rationale labeled secondary, and the
legacy NFL Fantasy correction route labeled inaccessible. Changed the seed UI
to say “reported correction / decision date” rather than imply exact system time.

### Pass 3 — complete requirements audit
Kept the original full governing brief and Core Values in README; linked the
supplemental case library; recorded timing, reasons, possible markets, score
outcomes and settlement caveats for all five added events. Rechecked that the
sample is not used as a frequency estimate, the market impacts are hypothetical,
source conflicts are visible, and the project still clearly states its retired
official-feed, licensing, odds, persistent-storage and notification blockers.
The existing Pages root-build setting remains unchanged; no competing Pages
workflow was added. Final local test/build results are recorded after the final
run below, before PR creation.

### Final verification

- `python3 -m unittest discover -s tests -v`: **44 passed** (35 pipeline tests,
  9 supplemental tests).
- `python3 scripts/build.py`: deterministic supplemental page with **12 cards**;
  source IDs, HTTPS links, numeric deltas, and the five re-review caveats validate.
- `./pipeline/sync_site_data.sh`: root Pages copies synchronized with canonical
  `docs/` copies; the site-contract tests confirm no drift.
- `node --check app.js`, `node --check docs/app.js`, and
  `node --check research-seed/site.js`: passed.
- JSON parsing for the case seed, source register, correction database, score
  study and market-sensitivity data passed; `git diff --check` passed.
- The local root preview returned HTTP 200 for `/`, the root CSS and JS, the
  supplemental case page, and `/data/events.json` (12 events).

No automated browser interaction/screenshot test or exhaustive public-link crawl
was available. This review is not a guarantee against later source changes or
publisher corrections; the case cards preserve their source and evidence caveats.

### Post-deployment copy review

After PR #7's Pages deployment, the live supplemental card text exposed a
double-period where a fully punctuated timing note met the builder's sentence
suffix. The generator now appends punctuation only when needed, and the
rebuild regression test rejects `..</p>`. Rebuilt the 12-card page and reran
all 44 tests, Node syntax checks, JSON parsing and whitespace validation.

## Alert-feasibility and evidence-integrity review — 2026-10-07

### Pass 1 — implement and verify
Added `ALERT_SYSTEM_FEASIBILITY.md` as an end-to-end feasibility assessment.
Documented the scoreboard-mirror workflow as implemented but narrow, the player
CSV/SQLite tool as a local prototype, optional webhook delivery, static-site
limits, operational risks and prioritized next steps. Improved webhook content
to identify an **unconfirmed mirror candidate**, include before/after values and
context, and link to the run report when invoked from Actions. Added fail-closed
workflow handling, kept failed comparisons/webhook deliveries from advancing the
baseline, and removed an unused workflow permission.

Reframed the market-distance output as a **line-proximity metric**, not a list
of hypothetical corrections or settled wagers. Removed unsupported “minimum
correction” and spread-push labels because the line-distance method does not
establish correction direction, spread side, or operator settlement. The exact
absolute-margin matches remain recorded as distance observations only. Updated
the generator, CSV/JSON artifacts, site, README and tests together.

### Pass 2 — assumptions and edge cases
- Replaced broad scoreboard-immutability language with the bounded result: no
  frozen-field differences observed in four selected versions of a third-party
  mirror, not proof about NFL records generally.
- Made the evidence command fail visibly when a selected baseline cannot be
  fetched; tested that incomplete baseline results cannot be summarized as
  zero changes.
- Qualified the 82/349 figure as a distance-threshold screen, not “0 actual / 82
  potential” market outcomes. Removed the claim that ten absolute margin/line
  magnitude matches necessarily mean a push.
- Labeled the line-market category table as a project screening heuristic, not a
  verified book/line inventory. Regenerated the 36-row database from the raw
  correction seed and current versioned `games.csv`; its counts remain 36 total,
  26 severity-2, 6 severity-1, 4 severity-0, and 0 documented realized outcomes.
- Kept correction-row date labels distinct from publication timestamps; kept
  player scoring-stat attribution distinct from game-score changes; retained
  unknown correction reasons rather than inferring them.
- Updated the static UI so an incomplete evidence study would show an unknown/
  partial state rather than a zero-result claim.

### Pass 3 — complete-request audit
Confirmed README §0 still contains the full governing brief and both Arena Core
Values. The current deliverable answers feasibility directly and points to
reviewable source links, names what is automated, what is not, and which external
feed/licensing/coverage gaps remain. No new historical claims or candidate rows
were added. The requested everyday, no-manual-checking live feed is **not yet
complete**; the report states that directly and ranks the remaining work.

### Final verification for this review

- `python3 -m unittest discover -s tests -v`: **54 passed** (45 pipeline/site
  tests and 9 supplemental seed tests).
- `python3 pipeline/run.py evidence`: completed all four selected baseline
  downloads; reports 28,323 overlapping game-snapshot comparisons and zero
  frozen-field differences, with the mirror/selection caveat preserved.
- Rebuilt database and market-sensitivity artifacts from the current fetched
  `games.csv`; result counts remain 36 / 26 / 6 / 4 and 349 assessed / 82 within
  the configured distance / 10 zero absolute-margin-distance matches.
- `./pipeline/sync_site_data.sh`: synchronized four JSON artifacts and four
  published site assets; repository tests confirmed byte identity.
- Final JavaScript syntax, Python compilation, JSON parsing and `git diff
  --check` are recorded after the complete run. No automated browser
  interaction test or exhaustive URL crawl is claimed.

At the time of that historical review, the remaining limitations included a
36-row sample and an unpublished comparison feed. Those counts/status are
superseded by the integrated review below; the retired official correction
channel, missing player-stat adapter/backtest, unverified settlement data and
lack of independent service-health alert remain open. See `LIMITATIONS.md`,
`RECOMMENDATIONS.md`, and `ALERT_SYSTEM_FEASIBILITY.md`.

## Integrated three-pass review — 2026-10-07

**This section is the current status and supersedes earlier historical test and
row counts above.** The fixed Arena branch was behind `main` at `c1aee73`; Git
history confirmed that `origin/main` descends from that commit. The same branch
was fast-forwarded to `7b5c883` before the integrated review.

### Pass 1 — implement and verify

- Re-ingested the 10 stored archived-page artefacts; `ingest_rendered.py
  --check` parsed 74 correction rows and confirmed the stored raw payload matches
  the artefacts (the generated timestamp is excluded from the comparison).
- Rebuilt the historical database from the current fetched `nflverse/nfldata`
  `games.csv`. It contains 74 rows, with counts 0 / 48 / 14 / 12 by severity;
  70 rows join to a game and four 2013 rows without a printed team code remain
  unjoined and visibly flagged. The generated metadata records the exact input
  byte count and SHA-256; the builder does not retain the full source file or
  claim a retrieval time or Git commit.
- Re-ran the 2025–26 distance screen against that fetched CSV and compared its
  outputs byte-for-byte with the checked-in JSON and CSV: 349 games considered,
  82 within one point (23.5%), 10 zero absolute-margin/spread-magnitude
  distances and 0 zero total-line distances. No market occurrence or settlement
  is inferred.
- Updated the database UI to expose row-level review flags and the reason as
  stated (or not stated) in the archived correction notice. Kept all team and
  source irregularities visible rather than inferring missing values.
- Kept the scheduled comparator fail-closed: snapshot/diff failures are
  `UNKNOWN`, baseline-only runs are distinct, and a failed configured webhook
  does not advance the snapshot baseline.

### Pass 2 — audit and correct

- Removed the prototype's 61-candidate/18-line-movement figures from headline
  findings because the exact full-file vintage pair was not retained for
  reproduction. `FINDINGS.md` now explicitly marks that exploratory count as
  non-reproducible; detector behavior is supported by code and regression tests.
- Corrected stale documentation/test counts to the current 74-test suite and
  synchronized root Pages copies from canonical `docs/` assets.
- Qualified all scoreboard claims as third-party mirror observations, not
  official NFL/Elias changes. Rechecked the feed: its two recorded clean runs
  (16:58:20 and 18:11:31 UTC) compare identical input hashes, so each is a
  no-op—not evidence of a newly changed source payload. No live webhook delivery
  was tested.
- Added the game-data source URL, input size and SHA-256 to the generated
  database and market-sensitivity JSON metadata. The lack of a retained full
  source vintage remains an explicit P3 limitation, not hidden reproducibility.

### Pass 3 — full-request and feasibility audit

The governing prompt remains verbatim in `README.md` §0. The direct answer is
still bounded: a scheduled scoreboard-field diff and comparison feed exist;
there is no production player-stat revision adapter/backtest, no authoritative
live corrections feed, no verified wager/settlement dataset, and no guarantee
of source or Actions freshness. Webhook alerts are opt-in and human-confirmed.
The 74-row, nine-week seed is not a comprehensive denominator. The remaining
work and limits are listed in `RECOMMENDATIONS.md`, `LIMITATIONS.md`, and
`ALERT_SYSTEM_FEASIBILITY.md`. Decisions remain guided by **Maximize P(Win)**
and **Own the Outcome**.

### Final local verification

- `python3 -m unittest discover -s tests -v`: **74 passed** (65 pipeline/site
  tests and 9 supplemental tests).
- `python3 pipeline/ingest_rendered.py --check`: 10 artefacts, 74 rows; payload
  matches the checked-in raw corrections.
- Rebuilt `data/discrepancies.json` / `.csv`; the JSON matched the checked-in
  file after excluding its generated timestamp, and the CSV matched byte-for-byte.
  Counts match the source-linked records and the four missing-team cases are flagged.
- Re-ran `market_sensitivity.py` on the fetched source file; generated outputs
  match the checked-in distance screen byte-for-byte.
- `python3 pipeline/run.py evidence`: all four selected baselines fetched;
  28,323 overlapping game-snapshot comparisons, zero frozen-field differences.
  This remains a third-party mirror result, not a claim about NFL internal records.
- `pipeline/run.py diff` on the two stored daily snapshots returned zero alerts;
  both source hashes were identical, so the comparison is explicitly a no-op.
- `python3 scripts/build.py`: supplemental page rebuilt with 12 cards.
- `node --check` on root/docs/research-seed JavaScript, `python3 -m py_compile`
  on pipeline and scripts, workflow YAML parsing, and `git diff --check`: passed.
- `./pipeline/sync_site_data.sh`: published `docs/` and root copies synchronized;
  the site-contract tests verify those copies and data fields. Local preview
  returned HTTP 200 for `/`, CSS, JS, the database JSON, the feed JSON and the
  supplemental page.

The hosted GitHub Actions checks and actual webhook delivery remain unverified
until the pull request is run; no success is inferred from local tests.
