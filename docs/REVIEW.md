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


---

# Three-pass review — 2026-10-07 (detection, notification and verification session)

Headline question put to this session: **can an alert-detection-notification system
for scoring discrepancies be built, and if so what are its limits?** The answer is
in `ALERT_SYSTEM_FEASIBILITY.md`; the evidence is below.

## Pass 1 — implement

- `pipeline/notify.py` — opt-in Slack/Discord delivery: idempotency key derived from
  the report content, `BACKOFF_SECONDS=(2,8,30)` retries, per-attempt receipts, and a
  dead-letter state. Receipts store the host and a SHA-256 of the URL only; the URL
  itself (which contains the webhook secret) is never written to disk or logs.
- `pipeline/health.py` — seven self-assessment checks (`comparison_feed`, `freshness`,
  `source_movement`, `snapshot_store`, `push_notification`, `atom_feed`,
  `published_copies`). Anything without evidence reports **UNKNOWN**; UNKNOWN is never
  folded into OK. `data/alerts/health.json` is regenerated, not hand-written.
- `pipeline/atom.py` — two subscribable feeds (detection comparisons, corrections
  database) plus the matching `<link rel="alternate">` tags and a `#subscribe` panel,
  so a reader can verify what was published and when without trusting this project.
- `pipeline/schema.py` — a machine contract for the fact layer (~22 violation codes).
  Run as a merge gate: `OK — 74 correction row(s) across 10 source page(s)`.
- `pipeline/verify_artefact.py` — re-reads a stored archived page against a fresh
  rendering of the same capture URL and compares row by row.
- `pipeline/vintage_study.py` + `run.py churn` — downloads SHA-pinned upstream
  vintages and measures how often the mirror actually moves.
- `run.py` gained `evidence`, `health`, `atom`, `churn`, `deliver`; `detect.yml` now
  delivers through `run.py deliver` (exit 11 on dead letter, so a failed alert never
  silently advances the baseline); new `health.yml` watchdog (daily cron + `workflow_run`)
  and weekly `source-churn.yml`; `validate.yml` extended with the schema gate, Atom
  well-formedness/uniqueness and site-sync drift.
- `tests/test_notification.py` — 85 tests covering idempotency, receipts, retries,
  dead-letter, URL-never-logged, transport shapes, health and its mutation guards,
  Atom, schema mutations, record-id stability, churn consistency and workflow wiring.

## Pass 2 — review and fix

Bugs this pass found and fixed, in the order they surfaced:

1. **The suite hung instead of failing.** `deliver(..., poster=detect.notify_webhook)`
   bound the transport at import time, so every `patch.object` was bypassed and unit
   tests issued real HTTPS requests. Fixed to `poster=None` with call-time resolution
   (same for `sleeper`). This was the single most dangerous defect of the session.
2. **`health.snapshot_manifests()` crashed on non-repo roots** (`relative_to` ValueError)
   — the first health test could not even build a fixture. Wrapped in try/except.
3. **Atom staleness ordering bug, found by the new health check:** generating
   `feed.atom` before appending the newest comparison run published 2 entries against
   3 recorded comparisons. The rule is now **atom → sync → health**, and `validate.yml`
   fails on an entry/run mismatch.
4. **Atom `<id>` collisions:** hashing only the input SHA-256 pair is insufficient —
   two clean runs over byte-identical snapshots share both hashes. Entry ids now hash
   `old|new|checked_at`; uniqueness is both a test and a workflow gate.
5. **Schema contract gap:** the hand-written `SOURCE_KEYS` omitted `position_filter`.
   `UNEXPECTED_KEY` caught it, so the key was added rather than the rule weakened —
   the contract earning its keep on day one.
6. **A documentation error that was also a code error.** `identical_inputs` had been
   described as "the source did not move". The manifests say otherwise: all three
   recorded comparisons have `source_file_changed: true`. Fixed in `feed.py`,
   `health.py`, `docs/index.html`, `docs/app.js`, and retracted explicitly in
   `README.md` §6 rather than quietly overwritten.
7. **Two health checks reported the wrong verdicts in draft:** `push_notification`
   claimed `PASS … 0 delivered` when every attempt was `not_configured` (now UNKNOWN +
   an irregularity), and `source_movement` warned on identical slim inputs, which is the
   normal healthy state for a scoreboard-only monitor (now reported as movement of the
   *source file*, with frozen-field projection counted separately).
8. **Test fixtures wrote only `data/alerts/feed.json`**, so the (correct) published-copy
   drift check failed every fixture. Fixtures now write both copies; a never-run checkout
   legitimately assesses as UNKNOWN, not FAIL.
9. `pipeline/build_database.py:199` leaked a file handle
   (`json.load(open(...))`) and emitted a ResourceWarning on every rebuild. Now a
   `with` block; the suite runs warning-free.

Also recorded so nobody re-litigates it: upstream `games.csv` bytes change nearly every
commit while all five slim snapshots share one hash, because churn lives in non-frozen
metadata columns and in not-yet-final rows. The full-file SHA moved
`d3a4878d…` → `460f01c5…` in eleven minutes at identical byte length.

## Pass 3 — re-audit against the original request

The North Star stays verbatim in `README.md` §0 and was re-read before this pass.

- **Frequency:** measured, not asserted — 44/44 sampled upstream intervals changed file
  bytes over 59 days; 15 changed the slim projection, all explained by row-count growth;
  **0 frozen scoreboard changes**; the detector fired 0 alerts in all 44 intervals.
  A naive "any field changed" alert would have produced **179 false positives and 0 true
  positives** in that window.
- **Latency:** correction lag 1–4 days after the game (mode 3, n=70 joined rows).
- **Which source controls the record:** the official NFL/Elias corrections page is
  authoritative and **retired** (302 → a news series page); its ESPN successor is
  client-side JavaScript with no documented API. So the live monitor necessarily runs on
  a third-party mirror, and a mirror diff **cannot distinguish an Elias correction from a
  provider bug**. Stated as a limitation, not papered over.
- **Automated detection without manual checking:** yes for the narrow frozen-scoreboard
  case (scheduled diff + feed + Atom + health watchdog). No for authoritative attribution,
  no for player-stat revisions end to end, no read receipt, no email/SMS channel (none is
  faked), and no claim that any correction flipped a settled market.
- **Verified, line by line, with links:** `data/evidence/verification_log.json` (inputs committed under `data/evidence/verification/`) records
  10 artefacts whose declared, extractable and shipped row counts all agree; all header
  capture URLs match their manifests; one archived official page was independently re-read
  this session — 11/11 rows identical, publisher header verbatim — and the verifier was
  mutation-checked (a changed value and a dropped row both detected). The other nine
  artefacts are **not** re-read; the log says so instead of implying coverage it lacks.
- **Irregularities flagged, not smoothed:** the four `TEAM_NOT_PRINTED` rows for Isaac
  Redman (2013 W1) are retained and flagged; the retired-feed finding, the provider-id
  renumbering ~21 months after games ended, and the delivery≠read gap are all published
  on the site's limits table.

Decisions were still made against **Maximize P(Win)** (prefer a checkable row to a
thousand unverifiable ones; prefer UNKNOWN to a flattering OK) and **Own the Outcome**
(delivery failure is fatal to the run; the watchdog is allowed to fail loudly; no
artefact was hand-written where a generator existed).

## Final local verification (this session)

- `python3 -m unittest discover -s tests`: **159 tests OK** (0.53 s), no warnings.
- `python3 pipeline/schema.py`: **OK — 74 correction row(s) across 10 source page(s)**.
- `python3 pipeline/ingest_rendered.py --check`: payload matches the stored artefacts.
- `python3 pipeline/verify_artefact.py --artefact data/evidence/pages/2018-W14-O.md
  --fetched <fresh rendering>`: **IDENTICAL, 11/11 rows**, exit 0; mutated value → exit 2;
  truncated rendering → 11 only-in-stored. `2013-W01-O.md` self-check → 15/15.
- Third scheduled comparison `2026-10-07T210737Z` → `…T211802Z` at `--min-severity 2`:
  0 alerts, source file changed, frozen projection unchanged.
- `python3 pipeline/run.py health --fail-on none`: overall **WARN** — 6 PASS, 1 UNKNOWN
  (`push_notification`: no webhook configured). Next action recorded as
  "detection works, notification does not".
- `python3 pipeline/run.py churn --commits 2200 --stride 50`: 45 vintages, 44 intervals,
  0 fetch failures, 321,009 final-record comparisons.
- All five workflow YAMLs parse; `node --check` passes on `docs/app.js` and the root
  mirror; `./pipeline/sync_site_data.sh` run twice so `health.json` reflects the
  regenerated Atom feeds; `published_copies` PASSes.
- Local preview on the published root layout returned HTTP 200 for `/`, `/app.js`,
  `/styles.css`, `/data/discrepancies.json`, `/data/alerts/feed.json`,
  `/data/alerts/health.json`, both Atom feeds, `/data/evidence/upstream_churn_study.json`
  and `/research-seed/index.html`.

Hosted GitHub Actions runs and a real webhook delivery remain unverified until the pull
request executes; no success is inferred from local tests. P2-5 (an end-to-end live
webhook proof) is the open item that closes that gap.


---

# Merge reconciliation — 2026-10-07 (two sessions, one repository)

While this branch was being written, `main` advanced by two pull requests from a parallel
session: **#12** (database expanded 74 → **141 rows** across **22** stored archived pages,
plus its own answer to the alert-system question) and **#13** (a site placeholder fix and a
two-way element-contract test). Merging them was not a formality: the two sessions had
built **the same name for two different things**.

## The collision, and how it was resolved

| Thing | This branch | `main` | Resolution |
|---|---|---|---|
| `data/alerts/health.json` | monitor **self-assessment**: eight checks, overall status, next action | **attempt ledger**: did a scheduled run happen (`ok`/`baseline`/`failed`/`unknown`) | Both kept, names separated. The ledger moved to `data/alerts/attempts.json`; `health.json` stays the assessment. |
| `run.py health` | `--fail-on none\|warn\|fail`, exits 3 on failure | `--status ok --detail "…"`, records an attempt | `run.py health` = assessment; the ledger writer became `run.py attempt`. |
| `feed.load_health` / `health_age_hours` | — | attempt-ledger helpers | Renamed `load_attempts` / `attempt_age_hours`; `record_attempt` unchanged. |
| `renderHealth()` in `app.js` | renders the assessment table into `#health` | renders the banner into `#health-banner` | Two functions with one name would have silently shadowed each other in JS. `main`'s became `renderAttempts()` → `#attempts-banner`. |
| Comparison feed | 3 same-day runs, each carrying `source_file_changed` | 3 runs incl. a genuine **15-day** vintage comparison | **Union: 4 runs.** The 15-day entry was back-filled from its own manifests, so it now also states source movement explicitly. |
| `ALERT_SYSTEM_FEASIBILITY.md` §L9 | `record_id` is content-derived (P1-4 DONE) | "`record_id` is positional" | `main`'s text was written before this branch's fix. L9 is now marked **RESOLVED**, with the reason: ids survived the 74 → 141 growth precisely because they are content-derived. |
| README §6 feed bullet | retracts the "no-op comparisons" claim with manifest evidence | repeats the retracted claim verbatim | The retraction stands; the stale bullet was deleted rather than left beside its own correction. |
| Test suite | 159 tests | 88 tests | **173 tests**, all passing after the merge. |

Nothing was dropped to make the merge compile. The one deliberate rename (`health` →
`attempts` for the ledger) is documented in `AGENTS.md`, `LIMITATIONS.md` §15,
`ALERT_SYSTEM_FEASIBILITY.md` L8 and the site's own code comments, so the next session does
not "fix" it back.

## Improvements the merge made possible

- **The ledger is no longer banner-only.** `pipeline/health.py` gained an eighth check,
  `attempt_ledger`, which reads `data/alerts/attempts.json`: a `failed` attempt makes the
  whole assessment FAIL, a `baseline`-only attempt WARNs, and an ageing ledger WARNs even
  when it says `ok`. `validate.yml` now rejects a ledger with an unusable status string.
  Two sessions each built half of a dead-monitor alarm; joined, they close the loop.
- **The null result got stronger.** `main`'s 15-day comparison (2026-09-22 → 2026-10-07,
  two different input hashes, 7,308 already-final games, zero frozen-field differences) is
  the first recorded run whose *compared bytes* genuinely differ, so "0 alerts" no longer
  rests on same-day snapshots alone. All four runs now record that the upstream file moved.
- **The 141-row database passed this branch's gates untouched.** `pipeline/schema.py`
  → `OK — 141 correction row(s) across 22 source page(s)` and
  `ingest_rendered.py --check` → exit 0 on the first try after the merge: the contract
  written for 74 rows validated 12 pages it had never seen, including three deliberate
  "no corrections" negative observations.

## Numbers restated after the merge

141 records · 22 stored archived pages (19 with rows, 3 explicit empty observations) ·
severity 3/2/1/0 = **0 / 70 / 50 / 21** · market-relevant **120** · potential-to-change **70** ·
**confirmed changed official outcome 0** · 4 rows flagged `TEAM_NOT_PRINTED` ·
82 distinct players · 13 seasons · 16 season-weeks · correction lag **1–6 days**
(mode 3, n = 137 joined rows) · 4 recorded comparisons, 0 alerts · Atom feeds:
**141** correction entries and **4** comparison entries · 8 health checks (7 PASS, 1 UNKNOWN) ·
173 tests.

`data/evidence/verification_log.json` was regenerated from the merged tree: row counts agree
on all 22 artefacts (declared = extractable = shipped, totalling 141), every artefact's
header URL matches its manifest, and the log now states plainly that **21 of the 22 pages
were not independently re-read** — the 12 that arrived from `main` were validated
mechanically, not re-observed against the archive.
