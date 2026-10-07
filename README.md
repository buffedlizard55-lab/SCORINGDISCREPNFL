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

**Within the retention window of the authoritative mirror we can test: no — not once.**

We diffed historical versions of `nflverse/nfldata`'s `data/games.csv` against the current record, examining only games that had **already reached a final state** at the older timestamp:

| Snapshot baseline | Games already final | Frozen score fields revised later |
|---|---|---|
| 2023-12-03 | 6,602 | **0** |
| 2025-11-12 | 7,140 | **0** |
| 2026-01-20 | 7,273 | **0** |
| 2026-09-22 | 7,308 | **0** |
| **Total** | **28,323** | **0** |

Artefact: [`data/evidence/score_integrity_study.json`](data/evidence/score_integrity_study.json)

**What this means.** An NFL game's final score is effectively immutable once posted. What changes after a game is **attribution and statistics** — who gets the sack, whether a play was a forward pass or a lateral, whether a receiver's 44 yards were really 43. Those move *player* markets, not the scoreboard.

**What this does not prove.** It tests a *mirror* of the NFL record, not the NFL's own database. It cannot see a correction made and then reverted between two mirror updates, nor anything before the mirror existed. It also cannot see an **in-game replay reversal**, which is a different phenomenon entirely (see §1.6).

### 1.2 How frequently do corrections occur, and how fast?

From the archived official release pages we transcribed, corrections for a given week are published **2–4 days after the games**, clustered on the Wednesday after (the NFL League Office and Elias Sports Bureau confer, then publish). Every one of the 36 transcribed rows landed inside that window — see `days_from_game_to_correction` in the database. The build raises `DATE_LATE` beyond 14 days and `DATE_INCONSISTENT` for anything before the game.

Corrections are **routine, not exceptional** — a normal week produces a handful to a few dozen rows across all positions, mostly yardage and defensive-credit adjustments.

### 1.3 What official source controls the final record?

**The Elias Sports Bureau is the official statistician of the NFL**, and official corrections are released jointly by the **NFL League Office and Elias Sports Bureau**. Quoted directly from the source page header:

> "View official stat corrections as released by the NFL League Office and the official statistician of the NFL, Elias Sports Bureau."

**Critical finding: that release channel is now retired.** As of 2026-10-07, `https://fantasy.nfl.com/research/statcorrections` **302-redirects to `https://www.nfl.com/news/series/fantasy`**, which now advertises *"ESPN FANTASY — The Official Fantasy Game of the NFL."* The machine-readable official corrections page is gone. Archived snapshots (2010–2025) survive on the Internet Archive and are what this database is built from. See [`LIMITATIONS.md`](LIMITATIONS.md) §1.

### 1.4 Could an automated system detect these without manual checking?

**Partly — and honestly, not the part that matters most.**

| Capability | Status | Why |
|---|---|---|
| Detect a **scoreboard** change post-game | ✅ Works | Differential snapshots of a versioned mirror; engine implemented and tested |
| Detect a **player stat** change post-game | ✅ Works *in principle* | Same method on play-by-play / weekly stat vintages — but those release assets are **network-blocked in the evaluation sandbox** (see LIMITATIONS §3) |
| Read the **official** corrections list automatically | ❌ Not today | The official feed was retired; the replacement is client-side JS with no documented public API |
| Distinguish official corrections from mirror-feed bugs | ❌ Not reliably | No independent second feed available for free |

Full engineering assessment: [`LIMITATIONS.md`](LIMITATIONS.md). Next work: [`RECOMMENDATIONS.md`](RECOMMENDATIONS.md). Also see [`docs/ALERT_SYSTEM_ANALYSIS.md`](docs/ALERT_SYSTEM_ANALYSIS.md) for the earlier feasibility write-up.

### 1.5 Exposure — which games *could* have been flipped?

Across the 349 games in 2025–26 with both a final score and a closing line:

- **82 games (23.5%) finished within 1 point of a market line** — any single-point scoring correction would have flipped a spread or total.
- **10 games pushed exactly on the closing spread.** A correction of *any* size would have created a winner where there was none.

Artefact: [`data/market_sensitivity_2025_2026.csv`](data/market_sensitivity_2025_2026.csv)

Read this as **sensitivity, not occurrence** — the concrete form of the brief's requirement to separate corrections that *actually* changed an outcome from those that merely *could* have. We found **0 of the former, 82 of the latter**.

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
IMPLEMENTATION_SUMMARY.md       summary from the earlier parallel session
data/
  verified_corrections_raw.json    36 transcribed official corrections (FACTS ONLY)
  discrepancies.json|.csv          same rows + game join + market classification (derived)
  market_sensitivity_2025_2026.*   82 correction-sensitive games, with arithmetic
  evidence/score_integrity_study.json   the 28,323-snapshot result
  prior_session/                   prior-session candidates — PRESERVED, NOT VERIFIED
pipeline/
  market_rules.py               which stats matter, and why
  detect.py                     diff engine, severity classifier, alert renderers
  fetch.py                      source adapters (all verified reachable)
  parse_corrections.py          parser for archived official pages
  build_database.py             raw facts -> shipping database, with flagging
  market_sensitivity.py         computes exposure to a scoring correction
  run.py                        CLI: snapshot | diff | evidence | corrections | selfcheck
  sync_site_data.sh             keeps docs/data/ byte-identical to data/
tests/test_pipeline.py          32 tests, incl. regressions for 5 real bugs found
docs/                           the GitHub Pages site (canonical, single source)
scripts/fetch_corrections.py    prior-session scraper, retained for reference
.github/workflows/              scheduled detection + Pages deploy
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
| Corrections for a week arrive **2–4 days after the games**, typically the following Wednesday | **Measured** | `days_from_game_to_correction` on all 36 transcribed rows — the strongest primary evidence we hold |
| The league and Elias confer on Wednesdays before publishing | **Secondary** | Consistent across multiple independent fantasy-platform operator statements |
| There is **no published deadline**; corrections can arrive days or weeks later | **Secondary** | Platform operator statements; no contrary primary source found |
| The **official gamebook / league statistics** control the final record — not third-party box scores | **Primary** | Consistent with the publisher statement; the archive pages are the league's published view |
| Coaches may appeal statistical rulings to Elias | **Secondary** | Reported practice; not independently verified to primary standard |

### Source register for corrections

| Source | Role | Verified status |
|---|---|---|
| NFL League Office + Elias Sports Bureau, via NFL.com Fantasy "Stat Corrections" | **The authoritative release** — every row in the database comes from here | **RETIRED 2026**; archived snapshots used |
| Internet Archive Wayback Machine | Primary-source archive of the above | Live; every row links to its exact snapshot |
| nflverse / nfldata `data/games.csv` | Schedule, final scores, closing lines; diff-engine input | Live; auto-committed ~every 30 min in season |
| nflverse-pbp raw play-by-play | Highest-resolution correction signal (nflverse refreshes it weekly *to incorporate stat corrections*) | Reachable on Actions; **blocked** in the evaluation sandbox |
| NFL Guide for Statisticians (GSIS) | Official scoring rules used to decide rulings | Referenced; not fetched during this build |
| ESPN Fantasy stat corrections | Consumer successor channel | JS-rendered; no documented public API; not relied upon |
| Sportradar / SportsDataIO | Commercial NFL data with revision change-logs | Would resolve the attribution problem; licensed, not used |

---

## 4. The detection system in one paragraph

We cannot poll a single authoritative correction feed any more. So instead we keep **our own versioned snapshots** of an authoritative mirror and diff them. The engine applies three rules, each derived from a bug found by testing against real data:

1. **Only compare records that were already final** at the older snapshot — otherwise every newly played game looks like a "change" (a naive diff produced 61 candidates; **61 of 61** were games that had not yet kicked off).
2. **Only compare frozen fields** — scores, result, total, overtime. Pre-game lines move constantly and must be excluded (all 61 of those candidates also carried line or odds movement). After both rules, **0** of the 61 survived: the true alert count for that fortnight was zero.
3. **Carry the old *and* new value plus SHA-256 hashes of both inputs**, so a third party can reproduce and verify any alert. Nothing is asserted without the raw values that produced it.

Each difference is classified by market impact: **severity 3** = discrete scoring event or scoreboard change; **severity 2** = a line-priced stat moved, or a round-number threshold was crossed; **severity 1** = market-relevant but small; **severity 0** = out of scope.

Critically, every alert is emitted as `verification_status: detected_by_diff_pending_manual_confirmation` with `actually_changed_outcome: null`. **The machine detects; a human confirms.**

---

## 5. Reproduce everything

Stdlib only — no dependencies. Python 3.10+.

```bash
# verify the whole pipeline (32 tests)
python3 tests/test_pipeline.py

# 1. Get a current authoritative snapshot of games + closing lines
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

**Verified and shipped:** the score-integrity study; the market-sensitivity analysis; the market-impact rule table; the diff engine and alerting; the corrections parser; 32 tests; 36 transcribed official correction records with per-row archived source links; the consolidated site.

**Known incomplete, stated rather than hidden:**

- The database is a **36-row verified seed, not the "comprehensive historical database"** the brief asks for. The archived corpus covers 2010–2025 × 10 position filters × 18+ weeks. **We would rather ship 36 verified rows than 5,000 unverified ones.** Expansion is the top item in `RECOMMENDATIONS.md`.
- The parser is unit-tested against fixtures reproducing the observed page structure but has **not** been validated against byte-exact archived HTML, because the Internet Archive is not on the sandbox egress allowlist. `run.py selfcheck` reconciles it on the first Actions run.
- **No row in the verified database claims a realised game-outcome change**, because we found no verifiable case, and a test fails the build if such a claim is made without evidence. Candidate cases that might qualify are walled off in `data/prior_session/` pending primary-source verification.
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

- **Detection:** `.github/workflows/detect.yml` runs on a schedule (daily in
  season, plus a Wednesday run after nflverse's 02:00 UTC correction refresh).
  Set `ALERT_WEBHOOK_URL` (Slack/Discord-compatible) as a repo secret to receive
  alerts; without it, alerts go to the job summary and an artefact. Webhook
  notification is **off by default** so a fork never spams anyone.


## Supplemental evidence seed and review (PR #3)

A concurrent contribution adds seven narrative cases in `data/events.json` with
per-stat source mappings in `data/sources.json`. These supplement, and do not
replace or automatically merge into, the broader main database. The seed includes
Dawson's apparent-final reversal, Polamalu's unchanged final result, the Manning
non-change, and Mendenhall/Gray/Watt post-game changes. It highlights a 31-day
Watt reporting gap and the conflicting identity of Gray's penalized defender.

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
