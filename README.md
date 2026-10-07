# SCORINGDISCREPNFL

> **Project north stars:** “Maximize P(Win)” and “Own the Outcome.”

## Persistent project charter — read this first at the start of every work session

Review this repository and investigate whether an alert/notification system can automatically detect NFL scoring and statistical discrepancies that may have market impact. Report feasibility, reliability, limitations, and what cannot be verified.

The project aims to build a comprehensive, independently verifiable historical database of qualifying NFL scoring/statistical corrections. For each record, document the game, game date, teams, player or team unit, original and corrected values, numerical change, correction date/timing, reason or play-level explanation when available, source quality, and possible or actual market impact. Cover potential changes to official score, team/game point totals, spreads, and listed player markets. Separate a verified actual effect from a hypothetical or merely possible effect; do not infer a sportsbook line or settlement from an NFL or fantasy score change.

Determine whether post-game corrections can occur, how often and how late they occur, what official record controls, and whether a fully automated current alert feed can be reliable. Use official, trusted, independently reviewable sources wherever possible, provide direct links for manual review, verify claims line by line, flag inconsistencies and missing evidence, and do not invent facts.

Create a clean, simple, user-friendly GitHub Pages site that presents the findings and source-linked dataset. Work independently. Complete and document three passes rather than stopping at the first implementation:

1. Implement and verify the requested site, research, data, and automation.
2. Re-review the implementation for bugs, missed requirements, unsupported assumptions, source/data problems, and edge cases; fix them.
3. Re-check the whole result against this charter, improve it, and state the remaining work and blockers.

The expected outcome is a useful, current feed that avoids requiring people to manually check for corrections. Be candid if this cannot be achieved safely with the sources available. Create a pull request from the session branch and merge it to `main` if the repository permits.

### Working rule

This README is the persistent project charter. Read it before project edits every session. Preserve the distinction between **official NFL statistics**, **fantasy-provider scores/finalization**, and **sportsbook wager settlement** throughout the code, database, and site.

## Current answer in brief

**Feasibility verdict:** Detecting that a public source has listed an NFL stat correction and publishing a candidate alert is technically feasible. Reliably detecting *every* correction from a durable, currently accessible official feed—and deciding whether a sportsbook market actually changed—is not established. The legacy NFL Fantasy Stat Corrections table describes itself as showing changes released by the NFL League Office and Elias Sports Bureau, but current canonical/region URLs have been observed redirecting to a general fantasy-news page in this research session; legacy `tab.fantasy.nfl.com` pages were inconsistently reachable. The watcher therefore fails closed, labels rows as candidates, and has not yet passed a live source test. A successful parse would still not establish a sportsbook line, settlement, or market outcome.

The initial ledger contains **nine curated game cases, eleven players, and fifteen player-stat deltas**. This is a starting sample, not a complete historical census. Three cases are grade C: Rodgers’ original total is reconstructed, and the old Spiller/Kamara correction-page links now redirect so their original rows are not independently retrievable in this review. In the sample, **no actual sportsbook line or settlement change has been independently verified**, and none of the nine documented stat changes altered the official final score or winner. Those zeroes describe the reviewed sample only—not the NFL as a whole. A separate AP report and one later fantasy-data analysis describe possible/actual fantasy consequences, but neither is sportsbook evidence; the latter is not independently audited here.

## Evidence and findings

### Official statistical authority and change process

- The [NFL Game Statistic and Information System (GSIS) “About” page](https://www.nflgsis.com/Help/About.html) says game/statistical information comes directly from GSIS, explains that gamebooks are produced shortly after games, and says corrections to existing game information are made regularly in conjunction with Elias Sports Bureau, the NFL’s official statistician. This supports treating current official NFL/GSIS statistics as the record of the corrected statistic. It does **not** provide a durable public before/after version history or a fixed correction deadline.
- The legacy [NFL Fantasy Stat Corrections page](https://fantasy.nfl.com/research/statcorrections) describes its entries as official stat corrections released by the NFL League Office and Elias Sports Bureau. Historical rows and week/season filters are surfaced in search indexes, but current direct accessibility is inconsistent. Its archive is a useful correction source when available, not a proven complete database across all NFL history or market types.
- A contemporaneous [Associated Press report carried by ESPN](https://www.espn.com/espn/wire?id=7399087) says NFL/Elias review the prior weekend’s games each Wednesday, teams may request later reviews, and there is no fixed deadline. It reports that October/November box scores were still being corrected in January/February and calls sacks the most frequently changed statistic. This is qualitative reporting, not a season-by-season rate study.
- In the curated sample, seven cited report/table dates fall 2–4 days after their games. The 2025 Caleb Williams Week 6 correction was reported on Dec. 17, **65 days** after the Oct. 13 game. The AP Rodgers story is marked “FOR RELEASE” Dec. 31, 76 days after the game; ESPN’s page metadata says “Updated: Dec. 28” (pre-release). It is retrospective and does not identify the NFL correction date. Several other rows use report/publication dates or legacy-table dates that cannot now be re-opened, rather than an authoritative NFL issuance timestamp. Do not treat these mixed dates or this small selected sample as a frequency distribution.

### Consequences and settlement limits

- The AP story marked “FOR RELEASE” Dec. 31 (with ESPN metadata “Updated: Dec. 28” before release) also reports an earlier fantasy matchup that flipped after an extra sack was credited to the Bills defense against Washington: the participant went from a narrow win to a narrow loss and said the two-point change cost money. The article does not identify the exact game week, original/corrected sack totals, correction timestamp, or a sportsbook. That source-limited anecdote is recorded separately in [`data/reported-downstream-effects.json`](data/reported-downstream-effects.json), not as a complete verified correction row.
- In the 2025 Caleb Williams case, a contemporaneous NFL reporter reported that a five-yard play was reclassified after the game, moving the rushing line from minus two to plus three total yards. Secondary fantasy analysis claims the change affected fantasy matchup/playoff outcomes and says fantasy platforms did not reopen the old week. Those league-level counts have not been independently audited. The official game center still shows Chicago’s 25–24 result; no book line or settlement was located.
- In the Hakeem Nicks case, Fleaflicker documented that it would not automatically rescore a fantasy matchup after its own Tuesday cutoff, despite the NFL statistical change. This is evidence that fantasy-provider finalization can diverge from the official NFL stat record; it is not a sportsbook outcome.
- Settlement is operator-, jurisdiction-, market-, and timing-specific. For example, [Fanatics Sportsbook’s Tennessee rules](https://sportsbook.fanatics.com/legal/tn/house-rules/) distinguish settlement from later amendments in specified cases; [ESPN’s fantasy policy](https://support.espn.com/hc/en-us/articles/360000099732-Scoring-Stat-Corrections) has its own Saturday scoring cutoff. These examples cannot be generalized to other operators or markets. The operator’s applicable rules and the original bet/settlement records are needed to establish actual sportsbook impact.
- A changed player total can hypothetically cross a prop threshold (yards, receptions, completions, sacks, tackles, etc.). That does not prove a market was offered at that number or that an operator changed a graded wager. A non-scoring correction ordinarily does not itself alter the game’s official score, spread result, or game total; the dataset checks and records score/winner separately rather than assuming.

### Automation status and blocker

A scheduled GitHub Actions workflow and a standard-library Python parser are included. The workflow is intended to poll all 18 regular-season week pages for the active or most recently completed season and the immediately preceding season (two seasons by default, configurable from one to five). It runs up to four times daily from September through February and daily in the offseason, to reduce the gap for late corrections. It opens one idempotent GitHub issue per newly observed correction row and does not write to or push a branch. The public site reads these alerts and the latest workflow run from the GitHub API. The workflow attempts to create a health issue if the source is unavailable or its HTML no longer matches the expected table; this also depends on Actions permissions.

**Important:** this design is best-effort and has not been confirmed against a live, stable current-season official correction endpoint. The source’s redirect/access behavior is the immediate blocker. Until a `workflow_dispatch` dry run succeeds against the actual source, do not describe the feed as active or complete. GitHub scheduled runs themselves may be delayed or disabled by GitHub; users must also opt into repository notifications (for example, by watching the repository). No email/SMS/push destination is configured automatically.

## Repository map

- [`index.html`](index.html), [`styles.css`](styles.css), [`app.js`](app.js) — responsive, static GitHub Pages research site; no framework or build step.
- [`data/historical-cases.json`](data/historical-cases.json) — curated cases with stat deltas, evidence grades, timing/reason notes, score effects, possible versus reported impact, and manual-review links.
- [`data/reported-downstream-effects.json`](data/reported-downstream-effects.json) — secondary fantasy consequence reports that lack enough detail for a complete correction record.
- [`scripts/poll_official_corrections.py`](scripts/poll_official_corrections.py) — fail-closed parser, candidate-alert formatter, and GitHub Issues publisher.
- [`.github/workflows/stat-correction-watch.yml`](.github/workflows/stat-correction-watch.yml) — scheduled/manual watcher workflow; manual dispatch defaults to dry-run.
- [`.github/workflows/quality-checks.yml`](.github/workflows/quality-checks.yml) — JSON validation, data/parser tests, and JavaScript syntax check for pushes/PRs to `main`.
- [`tests/`](tests) — parser, data-integrity, and issue-format fixtures/tests; tests never contact a live source.
- [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) — schema, evidence grades, timing rules, and quality controls.
- [`docs/CASE-AUDIT.md`](docs/CASE-AUDIT.md) — first-pass, case-by-case verification notes and unresolved evidence gaps.
- [`docs/FEASIBILITY.md`](docs/FEASIBILITY.md) — detailed feasibility assessment and open blockers.

GitHub Pages is already configured to publish the repository root from `main` (`build_type: legacy`); the site is static and needs no separate build/deploy workflow.

## Run locally

Serve this directory over HTTP (the site uses `fetch`, so opening `index.html` directly as a `file://` URL is not sufficient):

```bash
python3 -m http.server 8000 --bind 0.0.0.0
```

Run fixture-only checks:

```bash
python3 -m unittest discover -s tests -v
python3 -m json.tool data/historical-cases.json >/dev/null
python3 -m json.tool data/reported-downstream-effects.json >/dev/null
```

A live monitor dry run requires network access to the legacy source and should only be attempted from the workflow’s `workflow_dispatch` interface after inspecting the target source. It creates no issues by default. A non-dry run needs GitHub Actions issue-write permission; it still cannot inspect sportsbook accounts or private market archives.

## Review-pass record

1. **Pass 1 — implement and verify (complete):** added the responsive static site, nine-case curated ledger, separate reported fantasy-effects file, fail-closed candidate watcher, research documentation, and fixture/data tests. Verified GitHub Pages is configured for root-of-`main` publishing. Local tests and static checks pass; the legacy live endpoint has not passed a workflow dry-run.
2. **Pass 2 — independent review and fixes (complete):** corrected Cutler’s report date from Sep. 12 to Sep. 11; recorded the AP Rodgers article publication lag separately from the unknown NFL correction date; checked numerical deltas and date arithmetic; downgraded provisional cases where historical correction links now redirect; added per-case audit notes; fixed `Games Played` classification, malformed-table rows being silently skipped, and issue pagination; added regression tests. Extended polling to two recent seasons with a daily offseason schedule because there is no fixed correction deadline. Removed the empty `CNAME` and avoided adding a Pages workflow because the repository already publishes `main` from the root.
3. **Pass 3 — whole-charter re-check (complete):** confirmed the charter, source links, evidence grades, score/winner checks, possible-vs-actual distinctions, public feed UI, notification caveats, and remaining blockers are represented in README/site/docs. A local HTTP preview served the page and both JSON files successfully. The historical sample is explicitly non-comprehensive, and no sportsbook outcome or live-feed reliability claim is made without evidence.

## Delivery status

- Working branch required by this Arena session: `arena/6dd7b301-scoringdiscrepnfl`.
- GitHub Pages configuration: repository root on `main`; publishing occurs through the existing branch-based Pages setting.
- Remaining blockers: stable live official correction endpoint; complete historical census and original snapshots; operator/jurisdiction-specific archived sportsbook lines, rules, and settlements; and production live-monitor validation.
