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

### 0.1 Standing session instructions added later (also part of the brief)

Reproduced so later sessions inherit them rather than rediscovering them.

> Review the repo.

> We should also look into if we can build a alert detection notification system that can detect scoring discrepancies. Tell me the limitations and if it's even possible to do that.

> Site creation — Create a github page for this repo that has clean ui, user friendly, simple and easy to use. It should be organized and clean. It should include all relevant information in an easy to read format with official verified links as sources for review. Work line by line verify everything no hallucinations.

> The goal of this project is to get a full list that follow our requirements. No hallucinations. Verify line by line.

> Work line by line verifying from official verified trusted sources, provide links for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for review. No hallucinations.

**How each is answered in this repo:** §0 (brief) · §1.4a + [`ALERT_SYSTEM_FEASIBILITY.md`](ALERT_SYSTEM_FEASIBILITY.md) (alert system + limitations) · §5 (site) · §6 (honesty statement) · [`RECOMMENDATIONS.md`](RECOMMENDATIONS.md) (remaining work) · [`LIMITATIONS.md`](LIMITATIONS.md) (what is blocked vs unfinished).

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

**The null result is not vacuous.** A "zero changes" finding only means something if the underlying data was moving. It was: across four polls on 2026-10-07 the mirror's full `games.csv` hash changed every time (`1da074c8…` → `e5986b32…` → `51550c2e…` → `d3a4878d…`) while the hash of the frozen fields of already-final games stayed byte-identical (`341417de…`) in all four. Line movement, broadcast times and in-progress games churn constantly; already-final scores, results, totals and overtime flags did not. The filter is suppressing real churn, not reporting on a static file.

**What this does not prove.** It tests a *mirror* of the NFL record, not the NFL's own database. It cannot see a correction made and then reverted between two mirror updates, nor anything before the mirror existed. It also cannot see an **in-game replay reversal**, which is a different phenomenon entirely (see §1.6).

### 1.1b Does the mirror revise games that are already final? (new this session)

**Yes — but not the scoreboard fields, and the difference is the whole design of the detector.**

We downloaded **45 genuine upstream vintages** of `nflverse/nfldata`'s `data/games.csv`, each pinned
to an exact commit SHA (so any reviewer can re-fetch byte-identical files), spanning
**2026-08-09 → 2026-10-07 (1,420.7 hours / 59 days)** and **44 consecutive intervals**, and diffed
them with the shipped detector.

| Measured over 44 intervals | Result |
|---|---|
| Intervals where the mirrored file's bytes changed | **44 of 44** |
| Already-final record comparisons performed | **321,009** |
| Frozen scoreboard changes on already-final games | **0** |
| Other field changes on already-final games | **179** across **91** games |
| — late backfill of a blank cell | 145 |
| — revision of an already-published value | 34 |
| Columns observed changing | `ftn` 55, `referee` 38, `temp` 28, `wind` 28, `surface` 28, `pff` 2 |
| Slim-projection changes not explained by a frozen change or a row-count change | **0** |

Artefact: [`data/evidence/upstream_churn_study.json`](data/evidence/upstream_churn_study.json),
regenerable with `python3 pipeline/run.py churn`.

**What this establishes.** The source is genuinely live: it rewrites the mirrored file in every
sampled interval, and it *does* edit games that were already final — mostly weather and officials
metadata backfilled 1–2 days after the game, plus a wholesale renumbering of provider game-id
columns (`ftn`, `pff`) on 2024 games observed ~21 months later. One true post-final value revision
was observed in a non-scoreboard column: `2026_01_SF_LA` `surface` `matrixturf` → `grass`.

**Why it matters for alerting.** A naive "any field changed on a finished game" detector would have
fired **179 times in 59 days** and caught **zero** scoreboard changes. The frozen-field scoping rule
is not a convenience; it is what keeps the alert channel credible. That measured noise floor is now
part of the evidence base rather than an assertion.

**What it does not prove.** It measures a mirror, over a sampled window. Sampling at a stride is a
blind spot by construction: a value changed and changed back inside one interval cannot be observed.
The stride, the commit list and every SHA-256 are recorded so the size of that blind spot is known.

### 1.2 How frequently do corrections occur, and how fast?

Measured only in the **141 transcribed rows from 22 archived week-pages**: 137 join to a real game, and their displayed correction calendar dates are 1–6 days after the game date (mode 3). This is not an exact time-to-publication measure or a universal NFL correction window.

| Days from game to correction | Rows |
|---|---|
| 1 | 3 |
| 2 | 32 |
| 3 | **71** |
| 4 | 29 |
| 6 | 2 |

(The other 4 rows carry no gap because the official page printed no team code for them, so no game join was attempted — see `review_flags`.)

> **Correction to an earlier claim in this file.** A previous revision stated the window was "2–4 days". That was true of the 36-row sample it was measured on, and **false** of the 74-row database that followed: three rows were corrected just 1 day after the game. The claim is now stated as a measured distribution rather than a range, and the current database has widened it again to 1–6 days: the two 6-day rows are 2023 Week 16 corrections dated Dec 27 against a **Thursday-night** game played Dec 21. A correction dated a fixed number of days after "the week" therefore does *not* mean a fixed number of days after every game in that week.

Secondary sources describe the league and Elias conferring midweek before publishing; that is consistent with the 3-day mode but is **not** independently verified to primary standard, so it is not stated as fact here. The build raises `DATE_LATE` beyond 14 days and `DATE_INCONSISTENT` for anything dated before the game.

The 16 sampled season-weeks contain 1–25 rows each (mean 8.8), mostly yardage and defensive-credit adjustments. This selected archive sample does not establish a population-wide weekly frequency.

**Not one of the 141 rows records a scoring-event change.** No touchdown, field goal, extra point, two-point conversion or safety was added or removed in this selected database. Under the project-defined severity heuristic, counts are severity 3/2/1/0 = **0 / 70 / 50 / 21**; these are review-priority labels, not verified market outcomes.

### 1.2a Coverage of the current database

| Season / week | Rows | Games in the join | Game-to-correction gap |
|---|---:|---|---|
| 2010 W1 (DEF) | 2 | 2010-09-12 | 3 days |
| 2012 W1 | 7 | 2012-09-09 | 3 days |
| 2013 W1 | 15 | 2013-09-08 | 3–4 days |
| 2014 W16 | 3 | 2014-12-21 | 3 days |
| 2015 W1 | 6 | 2015-09-13 – 09-14 | 1–3 days |
| 2015 W16 | 14 | 2015-12-27 | 2–3 days |
| 2016 W16 (O + DEF) | 12 | 2016-12-24 | 4 days |
| 2017 W1 | 7 | 2017-09-10 | 4 days |
| 2017 W16 | 9 | 2017-12-23 – 12-25 | 1–4 days |
| 2018 W1 | 3 | 2018-09-09 | 3 days |
| 2018 W14 | 11 | 2018-12-09 | 3 days |
| 2019 W16 (O + DB) | 25 | 2019-12-21 – 12-22 | 2–3 days |
| 2020 W16 | 8 | 2020-12-27 | 3 days |
| 2021 W16 | 3 | 2021-12-26 | 3 days |
| 2022 W16 | 1 | 2022-12-24 | 4 days |
| 2023 W16 (O + LB) | 15 | 2023-12-21 – 12-25 | 2–6 days |
| **Total** | **141** |  | **137 rows join to a game** |

Two further artefacts are deliberate **negative observations**: 2024 W16 and 2025 W1 both render "No stat corrections to display" under the All-Offense filter. They are recorded so that "seasons 2010–2025 are represented in the evidence set" is never read as "every season and week has corrections".

Two database gaps are stated rather than hidden: **2011 is absent** (no qualifying capture retrieved yet), and **weeks 2–15 and 17 are almost entirely absent** — the sample is deliberately weighted to weeks 1 and 16.

### 1.3 Which source publishes the official corrections used here?

**The Elias Sports Bureau is the official statistician of the NFL**, and official corrections are released jointly by the **NFL League Office and Elias Sports Bureau**. Quoted directly from the source page header:

> "View official stat corrections as released by the NFL League Office and the official statistician of the NFL, Elias Sports Bureau."

**Critical finding: that release channel is now retired.** As of 2026-10-07, `https://fantasy.nfl.com/research/statcorrections` **302-redirects to `https://www.nfl.com/news/series/fantasy`**, which now advertises *"ESPN FANTASY — The Official Fantasy Game of the NFL."* The machine-readable official corrections page is gone. Archived snapshots (2010–2025) survive on the Internet Archive and are what this database is built from. See [`LIMITATIONS.md`](LIMITATIONS.md) §1.

### 1.4 Could an automated system detect these without manual checking?

**Partly — and honestly, not the part that matters most.**

| Capability | Status | Why |
|---|---|---|
| Detect a **scoreboard** field change post-game | ✅ Implemented, narrow scope | Tested diff of two snapshots from a third-party mirror; only persistent differences present at poll time are visible. Dry-run against 44 genuine before/after vintages this session: 0 frozen-field changes, 179 non-frozen (§1.1b) |
| **Notify** a human when a candidate is detected | ✅ Implemented (pull) / ⚠️ opt-in (push) | Atom feeds need no configuration; webhook push needs the `ALERT_WEBHOOK_URL` secret and is off by default. Every attempt is receipted, idempotent and retried; exhaustion becomes a dead letter that fails the run |
| Know whether the **monitor itself** is still working | ✅ Implemented | `pipeline/health.py` + `.github/workflows/health.yml`, an independent watchdog that reads the artefacts the detector leaves behind and fails on staleness, drift, malformed feeds or dead letters. "Unknown" is never folded into "OK" |
| Detect a **player stat** change post-game | ❌ Not implemented end-to-end | Download/release-metadata helpers are not a validated player-stat snapshot adapter; schema, vintage retention, identity joins and a historical-correction backtest remain open (see LIMITATIONS §3) |
| Read the **official** corrections list automatically | ❌ Not today | The official feed was retired; the replacement is client-side JS with no documented public API |
| Distinguish official corrections from mirror-feed bugs | ❌ Not reliably | No independent corroboration source is integrated or validated; even two mirrors may share upstream data |
| Confirm a notification was **read** | ❌ Not possible | Slack/Discord webhooks return no read receipt. A 2xx proves the endpoint accepted a payload, nothing more |

Full system feasibility assessment: [`ALERT_SYSTEM_FEASIBILITY.md`](ALERT_SYSTEM_FEASIBILITY.md). Detailed limitations: [`LIMITATIONS.md`](LIMITATIONS.md). Next work: [`RECOMMENDATIONS.md`](RECOMMENDATIONS.md). The older [`docs/archive/ALERT_SYSTEM_ANALYSIS.md`](docs/archive/ALERT_SYSTEM_ANALYSIS.md) is preserved as historical material.

### 1.4a Can we build an alert-detection notification system? Direct answer

**Yes for scoreboard detection. Yes in principle, but not yet demonstrated, for player-stat detection. No for authoritative attribution.** All three halves matter, so they are answered separately.

#### What was verified this session (2026-10-07), by direct test

- A differential detector that compares two versioned snapshots of a third-party mirror and emits differences in *frozen scoreboard* fields (score, result, total, overtime) for games already final in the older snapshot. Pre-game lines are excluded. Alerts carry before/after values and input SHA-256 hashes; they are candidates that still need source confirmation.
- A published **detection feed** at [`data/alerts/feed.json`](data/alerts/feed.json), rendered on the site. It records completed snapshot comparisons, including clean comparisons, and — since this session — the **upstream source-file hash and commit** behind each side, so "the compared projection was identical" can never again be misread as "the source did not move". A baseline run or failed/aborted workflow is not a completed comparison and may not add an entry; check the linked Actions history for the latest attempt/status.
- **Subscribable Atom feeds** ([`data/alerts/feed.atom`](data/alerts/feed.atom) for comparisons, [`data/corrections.atom`](data/corrections.atom) for the verified database), published on Pages and linked from the page head. This is the only notification channel that needs **no secret and no configuration**, which makes it the default answer to "tell me without me checking". Entry ids are content-derived and unique; a malformed or out-of-step feed fails the merge gate.
- **Delivery receipts, idempotency and dead letters** ([`pipeline/notify.py`](pipeline/notify.py) → `data/alerts/deliveries.json`). The idempotency key is derived from the compared snapshot hashes and alert ids — deliberately *not* the timestamp — so re-running the same comparison cannot notify anyone twice. Retries are bounded with backoff; exhaustion is recorded as a dead letter and exits 11, which fails the run so the baseline is not advanced. The webhook URL is never stored: only its host and a SHA-256.
- An **independent health watchdog** ([`pipeline/health.py`](pipeline/health.py), [`.github/workflows/health.yml`](.github/workflows/health.yml)) that answers "is the monitor running?" separately from "did it find anything?". It checks feed freshness, source movement, the snapshot store and its upstream watermark, dead letters, Atom consistency and published-copy drift, and it publishes a plain-language next action. It cannot be silenced by the workflow it watches.
- A scheduled GitHub Actions job (`detect.yml`) that snapshots (recording the upstream commit watermark), diffs, appends to the feed, regenerates the Atom feeds, assesses health, publishes everything, and optionally posts to a Slack/Discord webhook (`ALERT_WEBHOOK_URL`, off by default so a fork never spams anyone).
- A weekly **source-movement study** ([`.github/workflows/source-churn.yml`](.github/workflows/source-churn.yml)) that refreshes the §1.1b evidence from genuine upstream vintages.
- A **contract for the fact layer** ([`pipeline/schema.py`](pipeline/schema.py)) that fails the build on a malformed correction row, an unknown source id, a row count that disagrees with its page, a URL that is not an archive capture, or a value pair with no change — the failure modes that would otherwise ship as a plausible-looking wrong number.

#### What the review environment could actually reach, by direct request

Not assumed — each row below is the result of an actual request made during this review.

| Source / route | Result | Consequence |
|---|---|---|
| `api.github.com` — nfldata commit history, nflverse release metadata | **Reachable** (HTTP 200) | Snapshot scheduling and vintage discovery work |
| `codeload.github.com` — full repo tarballs | **Reachable** (2.6 MB in 0.65 s) | Historical `games.csv` vintages can be pulled and diffed |
| `raw.githubusercontent.com` | **Not reachable** (curl exit 000) | Tarball route is required, not optional |
| `github.com/.../releases/download/...` — release asset bytes | **Not reachable** (302 → 0 bytes) | Player-stat asset bytes cannot be downloaded here |
| `api.github.com/.../releases/assets/{id}` with `Accept: application/octet-stream` | **Not reachable** (302 → 0 bytes) | Second route tested; same result |
| `web.archive.org` from bash | **Not reachable** (curl exit 000) | Archived pages come in through a document-render channel only |
| `web.archive.org` CDX API via render channel | **Reachable** | This is how the 22 evidence artefacts were retrieved |

#### What is built and working today

- A differential detector that compares two dated snapshots of a third-party mirror and emits differences in *frozen scoreboard* fields (score, result, total, overtime) for games already final in the older snapshot. Pre-game lines are excluded. Alerts carry before/after values and input SHA-256 hashes; they are candidates that still need source confirmation.
- A published **detection feed** at [`data/alerts/feed.json`](data/alerts/feed.json), rendered on the site. It records completed snapshot comparisons, including clean comparisons.
- An **attempt ledger** at [`data/alerts/attempts.json`](data/alerts/attempts.json), rendered as a banner above the feed. The feed records *completed comparisons*; the ledger records *attempts*, so a broken schedule shows a red "last attempt FAILED" banner instead of silently presenting a stale result as current. A failure never erases the last-success timestamp, and the monitor self-assessment reads the ledger as one of its checks — a failed attempt escalates to FAIL rather than living only in a banner.
- A scheduled GitHub Actions job (`detect.yml`) that snapshots, diffs, appends to the feed, records the attempt outcome, delivers notifications with receipts, regenerates the Atom feeds, assesses health, publishes everything, and optionally posts to a Slack/Discord webhook (`ALERT_WEBHOOK_URL`, off by default so a fork never spams anyone). **The scheduled path itself has not been observed completing on Actions** — the logic is unit-tested, the wiring is not.

#### The structural blocker nobody can engineer around

Historical **vintages** — a genuine "before" and "after" — are the raw material of any differential detector. Two facts, both verified:

1. **`nflverse/nfldata` keeps `data/games.csv` in Git**, so historical vintages exist and can be diffed. That file is **scoreboard-only**; it contains no player statistics.
2. **Player statistics live in release assets that are re-uploaded in place.** The `stats_player` release was published 2025-07-31; its `stats_player_post_2023.csv` asset was created **2026-08-13**. When an asset is overwritten, the prior bytes are gone. No Git-committed player-stat file was found in `nflverse/nfldata`, `nflverse/nflverse-data`, `nflverse/nflverse-pbp` or `guga31bb/nflfastR-data`.

**Therefore: a player-stat detector can be built and can start accumulating vintages from the day it is switched on, but it can never be backtested against the 141 known historical corrections using any channel available to this project.** That is the single most important limitation, and it is a property of how the upstream data is published, not of our code.

#### What is possible, and what is not

| Goal | Possible? | Blocker |
|---|---|---|
| Alert when the **mirror's final-score field** changes after the game | **Yes — shipped and demonstrated** | — |
| Alert when a **player stat** changes after the game | **Yes in principle; not demonstrated** | Code can be written and scheduled, but (a) asset bytes are not downloadable from this sandbox, only plausibly on GitHub Actions, and (b) no historical vintages exist, so it cannot be backtested before it is trusted |
| Know that a detected change **is** an official Elias correction | **No** | The official feed was retired in 2026 (LIMITATIONS §1). A mirror diff cannot tell an official correction from a provider data fix |
| Read the official corrections list **automatically** | **No** | The successor ESPN page is a client-side JS app with no documented public API. Reverse-engineering a private API is brittle and likely against terms — we decline |
| Say "this correction **flipped** a settled market" | **No** | Requires the actual offered line, timing, wager and applicable operator/league rules. No settlement record exists in this project; market categories are screening heuristics only |

**The honest one-line answer:** the workflow can compare frozen scoreboard fields between two dated snapshots of a third-party mirror — and it has now done so across a real 15-day window with genuinely different input hashes — report a difference for manual review, publish it as a subscribable feed, push it to a configured webhook with receipts, and fail loudly if any part of that chain stops working. It does *not* monitor the full player-stat correction problem, cannot attribute a mirror change to the NFL/Elias rather than to a provider data fix, and cannot confirm any market outcome. Alerts stay candidates with `actually_changed_outcome: null`. **The machine detects within a narrow scope; a human verifies.**

**Is it even possible? The one-paragraph verdict.** Detection: yes, and it is shipped for scoreboard
fields, with a measured noise floor (§1.1b) that shows why the scope is narrow. Notification: yes —
pull-based Atom works with zero configuration today, and push works the moment a webhook secret is
set; what is *not* possible is proving a human read it. Attribution: no. As long as the official
NFL/Elias corrections channel stays retired, no automated system can distinguish an official
correction from a data-provider repair, and any product that claims otherwise is claiming more than
its source supports. Coverage: no, not yet — player-stat corrections are the majority of what the
archived pages actually contain, and monitoring them needs a validated vintage adapter plus a
backtest against known corrections (§RECOMMENDATIONS P0-3). Reliability: partially — the watchdog
makes silent failure visible, but it cannot see a schedule GitHub itself disabled or delayed, and it
cannot recover a change that was made and reverted between two polls.

The complete assessment, including the operational failure modes that a demo hides, is in [`ALERT_SYSTEM_FEASIBILITY.md`](ALERT_SYSTEM_FEASIBILITY.md).

### 1.5 Exposure — which games *could* have been flipped?

In the 349-game 2025–26 sample with scores and mirror-supplied closing-line values, the configured one-point distance screen reports:

- **82 games (23.5%)** within one point of at least one screened line value.
- **10** where the absolute final margin equals the spread magnitude, and **0** with exact total-line distance.

Artefact: [`data/market_sensitivity_2025_2026.csv`](data/market_sensitivity_2025_2026.csv).

This is a **distance-based screening heuristic**, not proof that a particular book offered that line, that any correction occurred, or that a push, wager flip, or settlement would result. Direction, book-specific rules, prices and actual historical wagers are not modeled. The correction database contains **0 verified realized outcome changes**; the 82 are sensitivity candidates only.

### 1.5b What was independently verified this session, and what was not

Artefact: [`data/evidence/verification_log.json`](data/evidence/verification_log.json). Every check
below carries the URL a human can open to repeat it.

| Check | Result | Manual review link |
|---|---|---|
| Row counts agree across all 22 stored archived pages (declared = extractable = shipped) | **22/22 agree** | each row's `source_url_archived` |
| Every artefact's recorded URL matches its manifest | **22/22 match** | [`data/evidence/pages/`](data/evidence/pages/) |
| Independent re-read of one archived official page against its stored artefact | **11/11 rows identical** | [2018 W14 capture](https://web.archive.org/web/20181219090041/https://fantasy.nfl.com/research/statcorrections?leagueId=0&statWeek=14) |
| Publisher header quoted in §1.3 re-read verbatim on that capture | **confirmed verbatim** | same URL |
| The re-read tool catches drift (mutation-checked: one value altered, rows removed) | **both detected, exit 2** | [`pipeline/verify_artefact.py`](pipeline/verify_artefact.py) |
| The re-read inputs are committed, so the check repeats without re-fetching the archive | **exit 0 / 2 / 2 reproduced from the repo alone** | [`data/evidence/verification/`](data/evidence/verification/) |
| The database's exact `games.csv` input hash is a re-downloadable upstream vintage | **matches** | [commit listing](https://github.com/nflverse/nfldata/commits/master/data/games.csv) |
| All 45 churn-study vintages re-downloadable and hash-identified | **45/45** | each `codeload_url` in the artefact |

**Not verified, stated plainly:** the other 9 stored artefacts were not independently re-read this
session (they were validated when first stored and remain self-consistent); no sportsbook or fantasy
settlement was verified anywhere in this project; and the archive re-read used the same
document-render channel on both sides, because `web.archive.org` is unreachable from this sandbox
over plain HTTP. That makes it a strong consistency check, not two independent observations.

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

docs/archive/IMPLEMENTATION_SUMMARY.md  summary from the earlier parallel session (archived)
data/
  verified_corrections_raw.json    141 official corrections, regenerated from evidence (FACTS ONLY)
  evidence/pages/*.md              22 stored archived official pages — the primary evidence
                                   (includes 2 deliberate "no corrections" negative observations)
  alerts/feed.json                 published log of completed snapshot comparisons (including clean runs)
  alerts/attempts.json             outcome of the most recent scheduled ATTEMPT (ok/baseline/failed/unknown)
  discrepancies.json|.csv          same rows + game join + market classification (derived); JSON meta records input hash
  market_sensitivity_2025_2026.*   82 distance-screen candidates; JSON records input hash
  evidence/score_integrity_study.json   the 28,323-snapshot result
  evidence/upstream_churn_study.json    45 genuine upstream vintages: how the mirror revises final games
  evidence/verification_log.json        what was independently verified, with review URLs
  evidence/verification/                committed re-read inputs: fresh rendering, verifier result, two mutation checks
  alerts/feed.atom                  subscribable Atom feed of comparisons (zero-config notification)
  alerts/deliveries.json            delivery receipts: idempotency keys, retries, dead letters
  alerts/health.json                monitor self-assessment ("is it running?", not "did it find anything?")
  corrections.atom                  subscribable Atom feed of the verified corrections database
  monitor.json                      legacy local-prototype status; not current workflow health
  prior_session/                   prior-session candidates — PRESERVED, NOT VERIFIED
pipeline/
  market_rules.py               which stats matter, and why
  detect.py                     diff engine, severity classifier, alert renderers, webhook transport
  notify.py                     delivery orchestration: idempotency, retries, receipts, dead letters
  health.py                     monitor self-assessment and watchdog exit codes
  atom.py                       RFC 4287 feeds so anyone can subscribe with no secret
  vintage_study.py              measures how the mirror revises already-final games
  verify_artefact.py            re-reads a stored artefact against a fresh rendering, row by row
  schema.py                     contract for the fact layer; a malformed row fails the build
  fetch.py                      source adapters, download helpers, upstream commit watermark
  parse_corrections.py          parser for archived official pages
  ingest_rendered.py            stored archived pages -> raw corrections (regenerable)
  feed.py                       append-only detection-run log (the live feed) + source-file hashes
  build_database.py             raw facts -> shipping database, with flagging and stable record ids
  market_sensitivity.py         computes exposure to a scoring correction
  run.py                        CLI: snapshot | diff | evidence | corrections | selfcheck |
                                deliver | health | atom | churn
                                diff --feed records a completed comparison, including clean results
  sync_site_data.sh             keeps docs/data/ byte-identical to data/
tests/test_pipeline.py          detection, parser, database and site contracts, incl. guards for
                                evidence, docs/data drift and UI regressions
tests/test_notification.py      notification, health, attempt ledger, Atom, schema, stable-id and
                                churn guards
                                173 tests total via unittest discovery
docs/                           the GitHub Pages site (canonical, single source)
scripts/fetch_corrections.py    prior-session scraper, retained for reference
.github/workflows/              detect (daily) · health (independent watchdog) · source-churn
                                (weekly evidence refresh) · validate (merge gate) · verify
                                Pages is branch-published from main/(root); there is no deploy job
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
| Displayed correction calendar dates are **1–6 days after the game**, mode 3 | **Measured in this sample** | `days_from_game_to_correction` on the 137 of 141 joined rows (mode 3, counts 3/32/71/29/2); measured per game, not per week; not an exact publication timestamp or population estimate |
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
# verify the whole pipeline (173 tests at this review; rerun after changes)
python3 -m unittest discover -s tests -v

# 0a. Validate the fact layer against its contract, and re-read one artefact
python3 pipeline/schema.py
python3 pipeline/verify_artefact.py --artefact data/evidence/pages/2018-W14-O.md \
        --fetched /path/to/a-fresh-rendering-of-the-same-url.md   # exit 2 = drift

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

# 5a. Measure how the mirror revises already-final games (the §1.1b evidence)
python3 pipeline/run.py churn --commits 2200 --stride 50

# 5b. Notification and monitor health
python3 pipeline/run.py atom                       # regenerate the subscribable feeds
python3 pipeline/run.py deliver                    # send with receipts (needs ALERT_WEBHOOK_URL)
python3 pipeline/run.py health --fail-on fail      # exit 3 = the monitor cannot be trusted

# 6. Pull + parse archived official correction pages (run on Actions; Wayback is
#    not on the sandbox allowlist — see LIMITATIONS #4)
python3 pipeline/run.py corrections --season 2018 --limit 50
python3 pipeline/run.py selfcheck     # reconciles the parser against real HTML FIRST
```

`run.py diff` exits **10** when alerts at or above `--min-severity` are found, so it drops straight into CI as a gate.

---

## 6. Status and honesty statement

**Verified and shipped:** the score-integrity study; the source-movement study over 45 genuine
upstream vintages; the market-sensitivity analysis; the market-impact rule table; the diff engine and
alerting; delivery receipts with idempotency and dead letters; subscribable Atom feeds; an attempt
ledger that records failed runs as well as clean ones; an independent health watchdog that reads it;
a validated contract for the fact layer; content-stable record ids; the corrections parser, validated
against rendered archived-page content and hardened against five distinct real cell shapes; the
comparison feed; **173 passing tests as of this review**; and **141 official correction records parsed
from 22 stored archived pages**, each with a per-row archived source link. A real 15-day mirror
comparison (2026-09-22 → 2026-10-07, two different input hashes, 7,308 already-final games) is
recorded in the feed alongside three same-day comparisons. The consolidated site is synchronized in
both Pages layouts.

**Known incomplete, stated rather than hidden:**

- The database is a **141-row verified seed across 13 seasons and 16 sampled season-weeks, not the "comprehensive historical database"** the brief asks for. Coverage is deliberately weighted to weeks 1 and 16; **2011 is absent entirely** and weeks 2–15 and 17 are almost entirely absent. An observed archive-search surface contains candidate captures across 2010–2025, position filters and weeks, but is not a validated complete denominator. Parsing a preserved page is mechanical; establishing coverage still requires careful retrieval, timestamp verification and review. **We would rather ship 141 rows that regenerate from stored evidence than thousands nobody can check.** See `RECOMMENDATIONS.md` P0-2.
- The parser **is validated against real archived page content** (22 artefacts, 141 rows, zero unparsed). Running it against real pages has now caught five cell shapes that hand-written fixtures missed: bolded numbers, a trailing "View Videos" link, a half-sack (`0 → 0.5`), and two bold injury designations (`**Q**`, `**IA**`). All five are regression-tested. What is still *not* validated is **byte-exact HTML** — the archive is reachable only through a document-render channel from this sandbox, so the stored evidence is the rendered table, not raw bytes. `run.py selfcheck` is still needed to reconcile the HTML path on an appropriate runner.
- **No row in the verified database claims a realised game-outcome change**, because no verifiable case was established in this seed, and a test fails the build if such a claim is made without evidence. Candidate cases that might qualify are walled off in `data/prior_session/` pending primary-source verification.
- The checked-in comparison feed has **four entries**: three same-day comparisons (16:58, 18:11 and
  21:22 UTC on 2026-10-07) and one genuine 15-day vintage comparison (2026-09-22 → 2026-10-07) over
  7,308 already-final games. All four report zero frozen-field differences; all four record that the
  upstream source file itself changed.

  > **Correction to an earlier claim in this file.** A previous revision called the first two
  > entries "no-op comparisons — not evidence of changed source bytes", because the two snapshot
  > hashes in each pair were identical. That was wrong, and the manifests beside the snapshots prove
  > it: those hashes are of the *slim frozen-field projection*, while the recorded
  > `source_file_sha256` of the whole upstream file differs in **all four** pairs. The upstream
  > mirror changed every time; the frozen scoreboard fields did not. The feed now carries both facts
  > per run (`identical_inputs` vs `source_file_changed`) so the two can never be conflated again,
  > and a test asserts every recorded run states source movement explicitly.

  No live webhook delivery was performed in this review — push notification remains opt-in and
  unexercised end to end, and the delivery log records exactly that (`not_configured`). The feed
  records completed comparisons only; failed and baseline-only workflow attempts are recorded
  separately in `data/alerts/attempts.json`, and `data/alerts/health.json` is the self-assessment that
  reads both.
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
  secret to attempt webhook delivery; without it, results go to the job summary,
  the artifact, the comparison feed and the Atom feed. Delivery was not
  live-tested here. Webhook notification is **off by default** so a fork never
  spams anyone.

- **Watchdog:** `.github/workflows/health.yml` runs daily at 06:00 UTC and after
  every detection run. It fails (exit 3) when the monitor is stale, the published
  copies have drifted, the Atom feed is malformed or out of step, the snapshot
  store is empty, or a notification is dead-lettered. It deliberately does not
  depend on `detect.yml` succeeding, because a detector cannot report its own
  death. A missing webhook is reported as UNKNOWN, not as a failure.

- **Evidence refresh:** `.github/workflows/source-churn.yml` re-runs the
  source-movement study weekly, so the noise floor behind the detector's scoping
  rule is a current measurement rather than a one-off.

- **Subscribing:** no setup is required. Point any feed reader at
  `https://buffedlizard55-lab.github.io/SCORINGDISCREPNFL/data/alerts/feed.atom`
  (comparisons) or `.../data/corrections.atom` (the verified database).


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
