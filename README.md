# SCORINGDISCREPNFL

**An automated detector for NFL post-game scoring and statistical discrepancies, and a verified database of documented corrections.**

> **Read this file first, every session.** It is the north star for the project. If a proposed change does not serve the brief in §0, it does not ship.

---

## 0. North Star — the governing brief

Reproduced in full so it cannot drift.

> ### NFL Scoring Discrepancy Investigation
>
> Investigate documented NFL scoring discrepancies, scoring corrections, and post-game statistical corrections that can materially change a market-relevant outcome. Focus only on events that could affect the final score, team totals, game totals, spreads, or player statistical outcomes such as passing yards, rushing yards, receiving yards, receptions, passing touchdowns, rushing touchdowns, receiving touchdowns, field goals, extra points, safeties, interceptions, sacks, or other statistics that can determine a player or game market result. Do not include ordinary statistical corrections that cannot affect a relevant market outcome unless they help establish how the NFL correction process works.
>
> Build a comprehensive historical database of qualifying discrepancies using official NFL sources and other authoritative, independently verifiable sources. For every event, identify the game, date, teams, player(s), original ruling/statistic, corrected ruling/statistic, exact numerical change, when the correction occurred, why the correction occurred, and which market-relevant outcomes could have changed. Distinguish between corrections that actually changed the official outcome and corrections that merely had the potential to change a market. Include the original and corrected values so the impact can be independently reproduced and verified.
>
> Specifically investigate whether NFL scoring discrepancies can occur after the apparent completion of a game and whether official records can subsequently change in a way that crosses a relevant statistical threshold or changes a scoring outcome. Look for corrections involving touchdowns, field goals, extra points, two-point conversions, safeties, defensive scores, scoring attribution, passing/rushing/receiving statistics, and other events where the official record can change after the initial result. Determine how frequently these events occur, how quickly corrections are published, what official source controls the final record, and whether a reliable automated system could detect them without manual checking.
>
> Put this prompt into the repo readme and read it everytime we work on the project as a starting point to make sure we are building what we are aiming for and have a strong base to continue building and improving on making something useful for everyday use. It should solve the problem of having to manually check everything ourselves and having an up to date current feed.
>
> Create a github page for this repo that has clean ui, user friendly, simple and easy to use. It should be organized and clean. It should include all relevant information in an easy to read format with official verified links as sources for review.
>
> Work line by line verifying from official verified trusted sources, provide links for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for review. **No hallucinations. Verify no hallucinations. Verify line by line.**

### Core values we build by

**Maximize P(Win)** — "Maximize the Probability of Winning": our decision-making framework. In every decision, weigh tradeoffs, assess risk, and choose the path that maximizes the probability the project succeeds. Set aside emotion and make the tough calls.

**Own the Outcome** — own results end to end, not just an individual slice. When a problem arises and we have the means to act, act without waiting for permission or assignment. Treat failure and success as signals and use them to improve. Stay accountable to the final outcome.

### The rules this repo enforces on itself

1. **No invented data.** Every factual row carries a source URL a human can open and check.
2. **No unsourced conclusions.** Every claim is either computed from a named dataset or quoted from a named publisher.
3. **Nothing is inferred silently.** Derived columns are labelled and stored separately from transcribed facts (`data/verified_corrections_raw.json` vs `data/discrepancies.json`).
4. **Never assert a realised impact the machine cannot prove.** `actually_changed_official_outcome` defaults to `false`, and a test fails the build if it is ever set without evidence.
5. **Flag irregularities, never smooth them over.** Rows carry `review_flags`.
6. **Distinguish sensitivity from occurrence.** "A correction here *would* have mattered" is never written as "a correction here *happened*".
7. **Never mix verified and unverified material.** Unverified candidates live in `data/prior_session/`, walled off from the verified database.

---

## 1. Headline findings

All four are reproducible from this repo (commands in §5).

### 1.1 Can an NFL score change after the game appears complete?

**In the selected historical snapshots of the third-party mirror: no frozen score-field changes were observed.** This is a bounded result, not a claim that official score changes never occur.

We diffed historical versions of `nflverse/nfldata`'s `data/games.csv` against the current record, examining only games that had **already reached a final state** at the older timestamp:

| Snapshot baseline | Games already final | Frozen score fields revised later |
|---|---|---|
| 2023-12-03 | 6,602 | **0** |
| 2025-11-12 | 7,140 | **0** |
| 2026-01-20 | 7,273 | **0** |
| 2026-09-22 | 7,308 | **0** |
| **Total** | **28,323** | **0** |

Artefact: [`data/evidence/score_integrity_study.json`](data/evidence/score_integrity_study.json)

**What this means.** No revisions were observed in these selected mirror comparisons; this does not establish that official scores cannot change. The 28,323 total is overlapping game-snapshot comparisons, not unique games. Post-game corrections can change **attribution and player statistics** — who gets a sack, whether a play is classified as a pass or lateral, or whether a receiver's credited yards change. Such changes can affect player markets without changing the scoreboard; the selected rows are not a complete history.

**What this does not prove.** It tests a *mirror* of the NFL record, not the NFL's own database. It cannot see a correction made and then reverted between two mirror updates, nor anything before the mirror existed. It also cannot see an **in-game replay reversal**, which is a different phenomenon entirely (see §1.6).

### 1.2 How frequently do corrections occur, and how fast?

Measured only in the **74 transcribed rows from 9 archived week-pages**: 70 join to a real game, and their displayed correction calendar dates are 1–4 days after the game date (mode 3). This is not an exact time-to-publication measure or a universal NFL correction window.

| Days from game to correction | Rows |
|---|---|
| 1 | 3 |
| 2 | 7 |
| 3 | **44** |
| 4 | 16 |

(The other 4 rows carry no gap because the official page printed no team code for them, so no game join was attempted — see `review_flags`.)

> **Correction to an earlier claim in this file.** A previous revision stated the window was "2–4 days". That was true of the 36-row sample it was measured on, and **false** of the current 74-row database: three rows were corrected just 1 day after the game. The claim is now stated as a measured distribution rather than a range.

Secondary sources describe the league and Elias conferring midweek before publishing; that is consistent with the 3-day mode but is **not** independently verified to primary standard, so it is not stated as fact here. The build raises `DATE_LATE` beyond 14 days and `DATE_INCONSISTENT` for anything dated before the game.

The 9 sampled week-pages contain 2–15 rows each (mean 8.2), mostly yardage and defensive-credit adjustments. This selected archive sample does not establish a population-wide weekly frequency.

**Not one of the 74 rows records a scoring-event change.** No touchdown, field goal, extra point, two-point conversion or safety was added or removed in this selected database. Under the project-defined severity heuristic, counts are severity 3/2/1/0 = **0 / 48 / 14 / 12**; these are review-priority labels, not verified market outcomes.

### 1.3 Which source publishes the official corrections used here?

**The Elias Sports Bureau is the official statistician of the NFL**, and official corrections are released jointly by the **NFL League Office and Elias Sports Bureau**. Quoted directly from the source page header:

> "View official stat corrections as released by the NFL League Office and the official statistician of the NFL, Elias Sports Bureau."

**Critical finding: that release channel is now retired.** As of 2026-10-07, `https://fantasy.nfl.com/research/statcorrections` **302-redirects to `https://www.nfl.com/news/series/fantasy`**, which now advertises *"ESPN FANTASY — The Official Fantasy Game of the NFL."* The machine-readable official corrections page is gone. Archived snapshots (2010–2025) survive on the Internet Archive and are what this database is built from. See [`LIMITATIONS.md`](LIMITATIONS.md) §1.

### 1.4 Could an automated system detect these without manual checking?

**Partly — and honestly, not the part that matters most.**

| Capability | Status | Why |
|---|---|---|
| Detect a **scoreboard** field change post-game | ✅ Implemented, narrow scope | Tested diff of two snapshots from a third-party mirror; only persistent differences present at poll time are visible |
| Detect a **player stat** change post-game | ❌ Not implemented end-to-end | Download/release-metadata helpers are not a validated player-stat snapshot adapter; schema, vintage retention, identity joins and a historical-correction backtest remain open (see LIMITATIONS §3) |
| Read the **official** corrections list automatically | ❌ Not today | The official feed was retired; the replacement is client-side JS with no documented public API |
| Distinguish official corrections from mirror-feed bugs | ❌ Not reliably | No independent corroboration source is integrated or validated; even two mirrors may share upstream data |

Full system feasibility assessment: [`ALERT_SYSTEM_FEASIBILITY.md`](ALERT_SYSTEM_FEASIBILITY.md). Detailed limitations: [`LIMITATIONS.md`](LIMITATIONS.md). Next work: [`RECOMMENDATIONS.md`](RECOMMENDATIONS.md). The older [`docs/archive/ALERT_SYSTEM_ANALYSIS.md`](docs/archive/ALERT_SYSTEM_ANALYSIS.md) is preserved as historical material.

### 1.4a Can we build an alert-detection notification system? Direct answer

**Yes for detection. No, not yet, for authoritative attribution.** Both halves matter, so here they are separately.

**What is built and working today:**

- A differential detector that compares two versioned snapshots of a third-party mirror and emits differences in *frozen scoreboard* fields (score, result, total, overtime) for games already final in the older snapshot. Pre-game lines are excluded. Alerts carry before/after values and input SHA-256 hashes; they are candidates that still need source confirmation.
- A published **detection feed** at [`data/alerts/feed.json`](data/alerts/feed.json), rendered on the site. It records completed snapshot comparisons, including clean comparisons. A baseline run or failed/aborted workflow is not a completed comparison and may not add an entry; check the linked Actions history for the latest attempt/status.
- A scheduled GitHub Actions job (`detect.yml`) that snapshots, diffs, appends to the feed, publishes it, and optionally posts to a Slack/Discord webhook (`ALERT_WEBHOOK_URL`, off by default so a fork never spams anyone).

**What is genuinely not possible today, and why:**

| Goal | Possible? | Blocker |
|---|---|---|
| Alert when the **mirror's final-score field** changes after the game | **Yes — shipped** | — |
| Alert when a **player stat** changes after the game | **Not yet** | There is no end-to-end player-stat vintage adapter or validated backtest. A source's refresh documentation alone does not prove that usable historical vintages are available to this workflow. |
| Know that a detected change **is** an official Elias correction | **No** | The official corrections feed was retired in 2026 (LIMITATIONS §1). A mirror diff cannot tell an official correction from a data-provider bug fix. |
| Read the official corrections list **automatically** | **No** | The successor ESPN page is a client-side JS app with no documented public API. Scraping it means reverse-engineering a private API — brittle and likely against terms. We decline to do that. |
| Say "this correction **flipped** a settled market" | **No** | Requires the actual offered line, timing, wager and applicable operator/league rules. No such settlement record is in this project; market categories are only screening heuristics. |

**The honest one-line answer:** the current workflow can compare frozen scoreboard fields in two snapshots of a third-party mirror and report a difference for manual review; it does not monitor the full player-stat correction problem. A mirror diff cannot establish whether the NFL/Elias made a change or whether a provider corrected a data error. Alerts remain candidates with `actually_changed_outcome: null`; market outcomes are not confirmed. **The machine detects within a narrow scope; a human verifies.**

### 1.5 Exposure — which games *could* have been flipped?

In the 349-game 2025–26 sample with scores and mirror-supplied closing-line values, the configured one-point distance screen reports:

- **82 games (23.5%)** within one point of at least one screened line value.
- **10** where the absolute final margin equals the spread magnitude, and **0** with exact total-line distance.

Artefact: [`data/market_sensitivity_2025_2026.csv`](data/market_sensitivity_2025_2026.csv).

This is a **distance-based screening heuristic**, not proof that a particular book offered that line, that any correction occurred, or that a push, wager flip, or settlement would result. Direction, book-specific rules, prices and actual historical wagers are not modeled. The correction database contains **0 verified realized outcome changes**; the 82 are sensitivity candidates only.

### 1.6 An important distinction: in-game reversals vs post-game corrections

These are different phenomena and must never be conflated:

- **In-game replay reversal** — the play is re-scored *before the game ends*. Markets settle on the corrected result. No settled bet is retrospectively flipped.
- **Post-game correction** — the record changes *days later*. Bets may already have settled. This is what the brief targets, and what §1.1 measures.

An earlier parallel effort on this brief catalogued candidate cases that appear to mix the two; those are preserved and walled off in [`data/prior_session/`](data/prior_session/README.md) pending primary-source re-verification, with the specific promotion steps documented. Two of them, if they verify, would be the highest-value cases in the project — they are named there.

---

## 2. What is in this repository

```
README.md                       <-- you are here; the north star
FINDINGS.md                     narrative of the investigation, with evidence
LIMITATIONS.md                  engineering + data limitations, ranked by severity
RECOMMENDATIONS.md              prioritised next work
ALERT_SYSTEM_FEASIBILITY.md     integrated automation, notification and source limits
IMPLEMENTATION_SUMMARY.md       summary from the earlier parallel session
data/
  verified_corrections_raw.json    74 official corrections, regenerated from evidence (FACTS ONLY)
  evidence/pages/*.md              10 stored archived official pages — the primary evidence
  alerts/feed.json                 published log of completed snapshot comparisons (including clean runs)
  discrepancies.json|.csv          same rows + game join + market classification (derived); JSON meta records input hash
  market_sensitivity_2025_2026.*   82 distance-screen candidates; JSON records input hash
  evidence/score_integrity_study.json   the 28,323-snapshot result
  monitor.json                      legacy local-prototype status; not current workflow health
  prior_session/                   prior-session candidates — PRESERVED, NOT VERIFIED
pipeline/
  market_rules.py               which stats matter, and why
  detect.py                     diff engine, severity classifier, alert renderers
  fetch.py                      source adapters and download helpers (capability varies by source)
  parse_corrections.py          parser for archived official pages
  ingest_rendered.py            stored archived pages -> raw corrections (regenerable)
  feed.py                       append-only detection-run log (the live feed)
  build_database.py             raw facts -> shipping database, with flagging
  market_sensitivity.py         computes exposure to a scoring correction
  run.py                        CLI: snapshot | diff | evidence | corrections | selfcheck
                                diff --feed records a completed comparison, including clean results
  sync_site_data.sh             keeps docs/data/ byte-identical to data/
tests/test_pipeline.py          65 pipeline/site tests; 74 total via unittest discovery
                                incl. guards for evidence, parser and UI regressions
docs/                           the GitHub Pages site (canonical, single source)
scripts/fetch_corrections.py    prior-session scraper, retained for reference
.github/workflows/              scheduled detection + validation (Pages is branch-published)
```

> **One canonical site, two published copies.** The site is authored in
> **`docs/`** and mirrored to the **repository root**, because GitHub Pages for
> this repo is configured to publish from the root and that setting cannot be
> changed with the available token. The root copies are *generated* by
> `pipeline/sync_site_data.sh`, never hand-edited, and
> `tests/test_pipeline.py` fails if they drift by a single byte. `app.js`
> resolves its data files in either layout, so the same file works in both
> places. Earlier duplicate copies in `site/` were removed.
>
> ```bash
> ./pipeline/sync_site_data.sh   # re-sync docs/data + root site files
> ```

---

## 3. How the NFL correction process works

Established from the official release pages themselves and corroborated by secondary reporting. **Claim-by-claim sourcing is given, because the brief requires it.**

| Fact | Status | Basis |
|---|---|---|
| Elias Sports Bureau is the official statistician of the NFL | **Primary** | Publisher statement on the official corrections page |
| Corrections are released by the NFL League Office **and** Elias | **Primary** | Same page header |
| Displayed correction calendar dates are **1–4 days after the game**, mode 3 | **Measured in this sample** | `days_from_game_to_correction` on the 70 of 74 joined rows; not an exact publication timestamp or population estimate |
| The league and Elias confer on Wednesdays before publishing | **Secondary** | Consistent across multiple independent fantasy-platform operator statements |
| No generally applicable correction deadline is stated on the archived release page | **Not established** | We did not identify a deadline in the cited page; this does not prove no separate rule exists |
| The archived correction page identifies releases by the NFL League Office and Elias | **Primary** | The page header states this; it is the publication source for the transcribed rows, not an independent ruling on settlement authority |
| Coaches may appeal statistical rulings to Elias | **Secondary** | Reported practice; not independently verified to primary standard |

### Source register for corrections

| Source | Role | Verified status |
|---|---|---|
| NFL League Office + Elias Sports Bureau, via NFL.com Fantasy "Stat Corrections" | **The authoritative release** — every row in the database comes from here | **RETIRED 2026**; archived snapshots used |
| Internet Archive Wayback Machine | Primary-source archive of the above | Live; every row links to its exact snapshot |
| nflverse / nfldata `data/games.csv` | Third-party schedule/results/line mirror; scoreboard-diff input | Versioned upstream; no official NFL provenance or freshness SLA established |
| nflverse-pbp raw play-by-play | Candidate high-resolution signal; upstream workflow documentation describes weekly refreshes | No end-to-end adapter or historical correction backtest is shipped; workflow-run access has not been demonstrated here |
| NFL Guide for Statisticians (GSIS) | Official scoring rules used to decide rulings | Referenced; not fetched during this build |
| ESPN Fantasy stat corrections | Consumer successor channel | JS-rendered; no documented public API; not relied upon |
| Commercial NFL data vendors | Potential stat/results feeds | Not evaluated or licensed here; any product would need documented NFL/Elias provenance, revisions, timestamps, rights and field coverage before it could improve attribution |

---

## 4. The detection system in one paragraph

The retired corrections channel is not available as a live source here. The scoreboard workflow keeps **its own versioned snapshots** of a third-party game-results mirror and diffs them. The engine applies three rules, each backed by tests:

1. **Only compare records that were already final** at the older snapshot — a game that is not final there cannot be called a post-final revision.
2. **Only compare frozen fields** — scores, result, total, overtime. Pre-game lines are volatile and excluded from this scoreboard comparison.
3. **Carry the old *and* new value plus SHA-256 hashes of both inputs**, so a third party can reproduce and verify any alert. Nothing is asserted without the raw values that produced it.

Market severity is a **project prioritization heuristic**, not a verified market inventory: **severity 3** = scoreboard change or a player/team stat categorized as scoring-related; **severity 2** = a stat category or project-defined round-number marker selected for market review; **severity 1** = other potentially relevant categories; **severity 0** = out of scope. Actual offerings, lines, prices and settlement rules are not inferred.

Critically, every alert is emitted as `verification_status: detected_by_diff_pending_manual_confirmation` with `actually_changed_outcome: null`. **The machine detects; a human confirms.**

---

## 5. Reproduce everything

Stdlib only — no dependencies. Python 3.10+.

```bash
# verify the whole pipeline (74 tests at this review; rerun after changes)
python3 -m unittest discover -s tests -v

# 0. Regenerate the raw corrections from stored archived pages; --check compares
#    the parsed payload (excluding the generated timestamp)
python3 pipeline/ingest_rendered.py --write
python3 pipeline/ingest_rendered.py --check

# 1. Get a current snapshot from the third-party game-results mirror
python3 pipeline/run.py snapshot

# 2. Re-run the 28,323-record score-integrity study  -> data/evidence/
python3 pipeline/run.py evidence

# 3. Rebuild the verified database (joins corrections to real games, flags irregularities)
#    NOTE: pipeline/sync_site_data.sh afterwards keeps the site in step.
python3 pipeline/build_database.py --games /path/to/games.csv

# 4. Recompute market exposure
python3 pipeline/market_sensitivity.py --games /path/to/games.csv --seasons 2025,2026

# 5. Detect a change between any two snapshots
python3 pipeline/run.py diff OLD.slim.csv NEW.slim.csv --min-severity 2 --out alerts/report.md

# 6. Pull + parse archived official correction pages (run on Actions; Wayback is
#    not on the sandbox allowlist — see LIMITATIONS #4)
python3 pipeline/run.py corrections --season 2018 --limit 50
python3 pipeline/run.py selfcheck     # reconciles the parser against real HTML FIRST
```

`run.py diff` exits **10** when alerts at or above `--min-severity` are found, so it drops straight into CI as a gate.

---

## 6. Status and honesty statement

**Verified and shipped:** the score-integrity study; the market-sensitivity analysis; the market-impact rule table; the diff engine and alerting; the corrections parser, now validated against rendered archived-page content; the comparison feed; **74 passing tests as of this review**; and 74 official correction records parsed from 10 stored archived pages, each with a per-row archived source link. The consolidated site is synchronized in both Pages layouts.

**Known incomplete, stated rather than hidden:**

- The database is a **74-row verified seed across 6 seasons and 9 sampled weeks, not the "comprehensive historical database"** the brief asks for. An observed archive-search surface contains candidate captures across 2010–2025, position filters and weeks, but is not a validated complete denominator. Parsing a preserved page is mechanical; establishing coverage still requires careful retrieval, timestamp verification and review. **We would rather ship 74 rows that regenerate from stored evidence than thousands nobody can check.** See `RECOMMENDATIONS.md` P0-2.
- The parser **is now validated against real archived page content** (2026-10-07): running it on the nine non-empty pages found two bugs that produced **zero usable rows**; the tenth page explicitly reports no corrections. Both bugs are fixed and regression-tested. What is still *not* validated is **byte-exact HTML** — the archive is reachable only through a document-render channel from this sandbox, so the stored evidence is the rendered table, not raw bytes. `run.py selfcheck` is still needed to reconcile the HTML path on an appropriate runner.
- **No row in the verified database claims a realised game-outcome change**, because no verifiable case was established in this seed, and a test fails the build if such a claim is made without evidence. Candidate cases that might qualify are walled off in `data/prior_session/` pending primary-source verification.
- The checked-in comparison feed has two clean entries (16:58 and 18:11 UTC on 2026-10-07). Both pairs of snapshot hashes are identical, so these are no-op comparisons—not evidence of changed source bytes. No live webhook delivery was performed in this review. The feed records completed comparisons, not every failed or baseline-only workflow attempt; inspect Actions for current workflow health.
- The prior session's 11 candidate entries are **preserved but not endorsed**; §1.6 and `data/prior_session/README.md` explain exactly what would be required to promote them.

**What we are explicitly *not* doing:** guessing prop lines, inferring opponents, or filling gaps with plausible-looking data.

---

## 7. Deploying

- **Site:** GitHub Pages is already configured with **legacy branch deploy from
  `main` / (repository root)**, so merging to `main` publishes the site
  directly — there is no deploy workflow to enable. Because a bad commit goes
  live immediately, `.github/workflows/validate.yml` is the gate: it runs the
  test suite, asserts every published copy is byte-identical to its canonical
  source, and checks that the data the page renders is present and well-formed.
  **That workflow must pass before merge.**

  > *If you have repo-admin rights*, the cleaner long-term setup is
  > *Settings → Pages → Source: GitHub Actions* with a `deploy-pages` workflow
  > publishing `docs/`. That would let `docs/` be the single published copy and
  > remove the root mirror entirely. It could not be applied here because the
  > available token returns 403 on the Pages settings API.

- **Detection:** `.github/workflows/detect.yml` is configured for daily runs in
  season plus an extra Wednesday poll after the upstream refresh time described
  in nflverse workflow documentation. This is a schedule, not a source/Actions
  freshness SLA. Set `ALERT_WEBHOOK_URL` (Slack/Discord-compatible) as a repo
  secret to attempt webhook delivery; without it, results go to the job summary
  and artifact. Delivery was not live-tested here. Webhook notification is
  **off by default** so a fork never spams anyone.


## Supplemental evidence seed and review (PR #3)

A supplemental research pass expands the narrative seed to **12 case studies** in `data/events.json`, with per-stat source mappings and excerpts in `data/sources.json`. They supplement, and do not replace or automatically merge into, the broader official-corrections database. The seed includes the original seven cases (Dawson's apparent-final reversal, Polamalu's unchanged final result, the Manning non-change, and Mendenhall/Gray/Watt post-game changes) plus five re-reviewed reports: Cutler (2008), Fitzpatrick/Parrish (2010), Manning/Nicks (2011), Brees/Snead (2015), and Elliott (2018). See the [supplemental case library](https://buffedlizard55-lab.github.io/SCORINGDISCREPNFL/research-seed/index.html), where each card links to its source trail. Source conflicts, inaccessible correction history, and imprecise timestamps remain explicit; no sportsbook settlement is claimed. The Elliott final NFL gamebook confirms one fumble, zero lost, and one own recovery—the fumble itself was not removed.

- [Supplemental findings & next steps](docs/RESEARCH.md)
- [Three-pass review](docs/REVIEW.md)
- `scripts/monitor.py`: local SQLite weekly-stat snapshot prototype, separate from `pipeline/`.
- `research-seed/`: standalone supplemental UI; does not control the main Pages deployment.
- `docs/archive/`: preserved earlier draft, explicitly unverified/superseded.

Run all tests with `python -m unittest discover -s tests -v`.
Run `python scripts/build.py` to regenerate only the supplemental preview.
A provider mirror's final flag is not proof of league finality; observed gaps
are not exact publication latency, and sensitivity is not observed settlement.

User's full everyday-use instruction, preserved without ellipsis:
“Put this prompt into the repo readme and read it everytime we work on the project as a starting point to make sure we are building what we are aiming for and have a strong base to continue building and improving on making something useful for everyday use. It should solve the problem of having to manually check everything ourselves and having an up to date current feed.”
