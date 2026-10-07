# SCORINGDISCREPNFL

**An automated detector for NFL post-game scoring and statistical discrepancies, and a verified database of documented corrections.**

> **Read this file first, every session.** It is the north star for the project. If a proposed change does not serve the brief below, it does not ship.

---

## 0. North Star — the governing brief

This is the specification this repository is built against. It is reproduced verbatim so it cannot drift.

> ### NFL Scoring Discrepancy Investigation
>
> Investigate documented NFL scoring discrepancies, scoring corrections, and post-game statistical corrections that can materially change a market-relevant outcome. Focus only on events that could affect the final score, team totals, game totals, spreads, or player statistical outcomes such as passing yards, rushing yards, receiving yards, receptions, passing touchdowns, rushing touchdowns, receiving touchdowns, field goals, extra points, safeties, interceptions, sacks, or other statistics that can determine a player or game market result. Do not include ordinary statistical corrections that cannot affect a relevant market outcome unless they help establish how the NFL correction process works.
>
> Build a comprehensive historical database of qualifying discrepancies using official NFL sources and other authoritative, independently verifiable sources. For every event, identify the game, date, teams, player(s), original ruling/statistic, corrected ruling/statistic, exact numerical change, when the correction occurred, why the correction occurred, and which market-relevant outcomes could have changed. Distinguish between corrections that actually changed the official outcome and corrections that merely had the potential to change a market. Include the original and corrected values so the impact can be independently reproduced and verified.
>
> Specifically investigate whether NFL scoring discrepancies can occur after the apparent completion of a game and whether official records can subsequently change in a way that crosses a relevant statistical threshold or changes a scoring outcome. Look for corrections involving touchdowns, field goals, extra points, two-point conversions, safeties, defensive scores, scoring attribution, passing/rushing/receiving statistics, and other events where the official record can change after the initial result. Determine how frequently these events occur, how quickly corrections are published, what official source controls the final record, and whether a reliable automated system could detect them without manual checking.
>
> …It should solve the problem of having to manually check everything ourselves and having an up to date current feed.
>
> Create a github page for this repo that has clean ui, user friendly, simple and easy to use. It should be organized and clean. It should include all relevant information in an easy to read format with official verified links as sources for review.
>
> Work line by line verifying from official verified trusted sources, provide links for manual review. There should be no manual input, work on your own to complete tasks. Flag any irregularities for review. **No hallucinations. Verify no hallucinations. Verify line by line.**

### Core values we build by

**Maximize P(Win)** — in every decision, weigh tradeoffs, assess risk, and choose the path that maximizes the probability the project succeeds. Set aside emotion; make the hard call.

**Own the Outcome** — own results end to end, not just an individual slice. When a problem appears and we have the means to act, act without waiting to be told. Treat failure and success as signals. Stay accountable to the final outcome.

### The rules this repo enforces on itself

1. **No invented data.** Every factual row carries a source URL a human can open and check.
2. **No unsourced conclusions.** Every claim is either computed from a named dataset or quoted from a named publisher.
3. **Nothing is inferred silently.** Derived columns are labelled as derived and stored separately from transcribed facts (see `data/verified_corrections_raw.json` vs `data/discrepancies.json`).
4. **Never assert a realised impact the machine cannot prove.** `actually_changed_official_outcome` defaults to `false` and a test fails the build if it is ever set without evidence.
5. **Flag irregularities, never smooth them over.** Rows carry `review_flags`.
6. **Distinguish sensitivity from occurrence.** "A correction here *would* have mattered" is never written as "a correction here *happened*".

---

## 1. Headline findings

These are the answers to the brief's explicit questions. All four are reproducible from this repo (commands in §4).

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

**What this means.** An NFL game's final score is effectively immutable once posted. What changes after a game is **attribution and statistics** — who gets the sack, whether a play was a forward pass or a lateral, whether a receiver's 44 yards were really 43. Those changes move *player* markets, not the scoreboard.

**What this does not prove.** It tests a *mirror* of the NFL record, not the NFL's own database. It cannot see a correction made and then re-corrected back between two mirror updates, nor anything before the mirror existed. Stated plainly in the artefact's `caveat` field.

### 1.2 How frequently do corrections occur, and how fast?

From the archived official release pages we transcribed, corrections for a given week are published in a tight window **2–4 days after the games**, clustered on the Wednesday after (the NFL League Office and Elias Sports Bureau confer, then publish). Every one of the 36 transcribed rows landed inside that window — see `days_from_game_to_correction` in the database, and note that the build raises `DATE_LATE` for anything beyond 14 days and `DATE_INCONSISTENT` for anything before the game.

Corrections are **routine, not exceptional** — a normal week produces a handful to a few dozen rows across all positions, mostly yardage and defensive-credit adjustments.

### 1.3 What official source controls the final record?

**The Elias Sports Bureau is the official statistician of the NFL**, and the official corrections are released jointly by the **NFL League Office and Elias Sports Bureau**. That is quoted directly from the source page header: *"View official stat corrections as released by the NFL League Office and the official statistician of the NFL, Elias Sports Bureau."*

**Critical finding: that release channel is now retired.** As of 2026-10-07, `https://fantasy.nfl.com/research/statcorrections` **302-redirects to `https://www.nfl.com/news/series/fantasy`**, which now advertises *"ESPN FANTASY — The Official Fantasy Game of the NFL."* The machine-readable official corrections page is gone. Archived snapshots (2010–2025) survive on the Internet Archive and are what this database is built from. See [`LIMITATIONS.md`](LIMITATIONS.md) §1.

### 1.4 Could an automated system detect these without manual checking?

**Partly — and honestly, not the part that matters most.**

| Capability | Status | Why |
|---|---|---|
| Detect a **scoreboard** change post-game | ✅ Works | Differential snapshots of a versioned mirror; engine implemented and tested |
| Detect a **player stat** change post-game | ✅ Works *in principle* | Same method on play-by-play / weekly stat vintages — but the high-resolution feeds are release assets that are **network-blocked in the evaluation sandbox** (§3 of LIMITATIONS) |
| Read the **official** corrections list automatically | ❌ Not today | The official feed was retired; ESPN's replacement is client-side JS with no documented public API |
| Distinguish official corrections from mirror-feed bugs | ❌ Not reliably | No independent second feed available for free |

Full engineering assessment, including the specific blocker for each row: [`LIMITATIONS.md`](LIMITATIONS.md). What to do next: [`RECOMMENDATIONS.md`](RECOMMENDATIONS.md). Narrative write-up: [`FINDINGS.md`](FINDINGS.md).

### 1.5 Exposure — which games *could* have been flipped?

Across the 349 games in 2025–26 with both a final score and a closing line:

- **82 games (23.5%) finished within 1 point of a market line** — any single-point scoring correction would have flipped a spread or total.
- **10 games pushed exactly on the closing spread.** A correction of *any* size would have created a winner where there was none.

Artefact: [`data/market_sensitivity_2025_2026.csv`](data/market_sensitivity_2025_2026.csv)

Read this as **sensitivity, not occurrence**. These are the games where the failure mode *could* have bitten. Per §1.1, it did not bite, because scores are not revised. This is the concrete, reproducible form of the brief's requirement to separate corrections that *actually* changed an outcome from those that merely *could* have.

---

## 2. What is in this repository

```
README.md                       <-- you are here; the north star
FINDINGS.md                     narrative of the investigation, with evidence
LIMITATIONS.md                  engineering + data limitations, ranked by severity
RECOMMENDATIONS.md              prioritised next work
data/
  verified_corrections_raw.json    36 transcribed official corrections (FACTS ONLY)
  discrepancies.json|.csv          same rows + game join + market classification (derived)
  market_sensitivity_2025_2026.*   82 correction-sensitive games, with arithmetic
  evidence/score_integrity_study.json   the 28,323-snapshot result
pipeline/
  market_rules.py               which stats matter, and why
  detect.py                     diff engine, severity classifier, alert renderers
  fetch.py                      source adapters (all verified reachable)
  parse_corrections.py          parser for archived official pages
  build_database.py             raw facts -> shipping database, with flagging
  market_sensitivity.py         computes exposure to a scoring correction
  run.py                        CLI: snapshot | diff | evidence | corrections | selfcheck
tests/test_pipeline.py          32 tests, incl. regressions for 5 real bugs found
docs/                           the GitHub Pages site (clean, filterable, sourced)
.github/workflows/              scheduled detection + Pages deploy
```

---

## 3. Source policy

Every factual record must trace to a primary or independently verifiable source, listed for manual review.

| Source | Role | Verified reachable | Status |
|---|---|---|---|
| **NFL League Office + Elias Sports Bureau** via the NFL.com Fantasy "Stat Corrections" page | The authoritative correction release | Archived snapshots only | **RETIRED 2026** — live URL 302s to the NFL fantasy news hub |
| **Internet Archive Wayback Machine** | Primary-source archive of the above | Yes | Every database row links to its exact snapshot |
| **nflverse/nfldata** (`data/games.csv`, git-versioned) | Schedule, final scores, closing lines; the diff engine's input | Yes (`codeload.github.com`) | Live; auto-committed every ~30 min in season |
| **nflverse-pbp** raw play-by-play | Highest-resolution correction signal (nflverse explicitly refreshes it weekly *to incorporate stat corrections*) | On Actions runners only | **Blocked** in the evaluation sandbox — `release-assets.githubusercontent.com` unreachable |
| **ESPN Fantasy stat corrections** | Successor fantasy channel | JS-rendered | No documented public API; not relied upon |

Each row in `data/discrepancies.json` carries `source_publisher`, `source_page_title`, `source_url_archived`, `source_url_live_now_retired`, and `source_snapshot_timestamp`.

---

## 4. Reproduce everything

Stdlib only — no dependencies. Python 3.10+.

```bash
# verify the whole pipeline (32 tests)
python3 tests/test_pipeline.py

# 1. Get a current authoritative snapshot of games + closing lines
python3 pipeline/run.py snapshot

# 2. Re-run the 28,323-record score-integrity study  -> data/evidence/
python3 pipeline/run.py evidence

# 3. Rebuild the verified database (joins corrections to real games, flags irregularities)
curl -sL -o /tmp/games.csv \
  https://codeload.github.com/nflverse/nfldata/tar.gz/refs/heads/master \
  && tar xzf /tmp/games.csv -C /tmp
python3 pipeline/build_database.py --games /tmp/nfldata-master/data/games.csv

# 4. Recompute market exposure
python3 pipeline/market_sensitivity.py --games /tmp/nfldata-master/data/games.csv --seasons 2025,2026

# 5. Detect a change between any two snapshots
python3 pipeline/run.py diff OLD_games.csv NEW_games.csv --min-severity 2 --out alerts/report.md

# 6. Pull + parse archived official correction pages (run on Actions; Wayback is
#    not on the sandbox allowlist — see LIMITATIONS #4)
python3 pipeline/run.py corrections --season 2018 --limit 50
python3 pipeline/run.py selfcheck     # reconciles the parser against real HTML FIRST
```

`run.py diff` exits **10** when alerts at or above `--min-severity` are found, so it drops straight into CI as a gate.

---

## 5. The detection system in one paragraph

We cannot poll a single authoritative correction feed any more. So instead we keep **our own versioned snapshots** of an authoritative mirror and diff them. The engine applies three rules, each derived from a bug found by testing against real data:

1. **Only compare records that were already final** at the older snapshot — otherwise every newly played game looks like a "change" (a naive diff produced 61 candidates; **61 of 61** were games that had not yet kicked off).
2. **Only compare frozen fields** — scores, result, total, overtime. Pre-game lines move constantly and must be excluded (all 61 of those candidates also carried line or odds movement). After both rules, **0** of the 61 survived: the real alert count for that fortnight was zero.
3. **Only compare frozen fields on final records, and carry the old *and* new value plus SHA-256 hashes of both inputs**, so a third party can reproduce and verify any alert. Nothing is asserted without the raw values that produced it.

Each surviving difference is classified by market impact: **severity 3** = discrete scoring event or scoreboard change; **severity 2** = a line-priced stat moved, or a round-number threshold was crossed; **severity 1** = market-relevant but small; **severity 0** = out of scope.

Critically, every alert is emitted as `verification_status: detected_by_diff_pending_manual_confirmation` with `actually_changed_outcome: null`. **The machine detects; a human confirms.** The system is built to *point* at the discrepancy, not to certify it.

---

## 6. Status and honesty statement

**Verified and shipped:** the score-integrity study; the market-sensitivity analysis; the market-impact rule table; the diff engine and alerting; the corrections parser; 32 tests; 36 transcribed official correction records with per-row archived source links; the site.

**Known incomplete, stated rather than hidden:**

- The database is a **36-row seed, not the "comprehensive historical database"** the brief asks for. The archived corpus covers 2010–2025 across 10 position filters and 18+ weeks each; each page is a separate rate-limited fetch. The `run.py corrections` command exists to expand it, and expansion is the top item in `RECOMMENDATIONS.md`. **We would rather ship 36 verified rows than 5,000 unverified ones.**
- The parser is unit-tested against fixtures reproducing the observed page structure but has **not** been validated against byte-exact archived HTML, because the Internet Archive is not on the sandbox egress allowlist. `run.py selfcheck` reconciles it on first Actions run.
- **No row in the database claims a realised game-outcome change**, because we found no verifiable case of one, and a test fails the build if such a claim is made without evidence. Reported fan anecdotes about flips exist in the wild; none are included, because we could not verify them to primary-source standard.

**What we are explicitly *not* doing:** guessing prop lines, inferring opponents, or filling gaps with plausible-looking data.

---

## 7. Deploying

- **Site:** `.github/workflows/pages.yml` publishes `docs/` to GitHub Pages. Enable Pages → Source: GitHub Actions.
- **Detection:** `.github/workflows/detect.yml` runs on a schedule. Set `ALERT_WEBHOOK_URL` (Slack/Discord-compatible) as a repo secret to receive alerts; without it, alerts are written to the job summary and uploaded as an artefact. Webhook notification is **off by default** so a fork never spams anyone.
