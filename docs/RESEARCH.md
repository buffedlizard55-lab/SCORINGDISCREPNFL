# Supplemental case-seed findings and feasibility — 2026-10-07

> **Scope note after concurrent integration:** This report describes the seven-case seed and `scripts/monitor.py`, not the broader pipeline/site merged in PR #2. Main now also contains an archived-corrections database, historical mirror comparison, market-sensitivity study and scheduled `pipeline/` workflow. See the root README, FINDINGS.md and LIMITATIONS.md for that work. Those additions have not been independently source-audited by this supplemental implementation; the tests below exercise their code, not prove their evidence. The statements about no schedule/no notifications below apply to the local seed prototype only.

## What is established
Yes, automatic **change detection** is feasible. Automatic determination that every change is an official correction, crosses an actually offered market line, and changes settlement is not feasible from an unversioned public box score alone.

The source-linked case database separates:
- **Post-game official statistic changes:** Mendenhall 100→99, Gray 199→201, Roethlisberger/Mendenhall run→pass touchdown, Watt sack removed.
- **Apparent-final reversal:** Dawson's field goal added 3 points at the end of regulation; overtime then added another 3. Not a days-later reversal of a certified result.
- **Error acknowledged without final-score amendment:** Polamalu, 2008.
- **Review with no change:** Manning, 2013. Never count this as a correction.

These findings are backed by the event-level links and excerpts in [sources.json](../data/sources.json) and [events.json](../data/events.json). Exact clock time of correction is unknown unless explicitly supplied. Dates derived from contemporaneous reports are not precise publication-latency measurements.

## Authority and timing
The [NFL Guide for Statisticians (2025), p.4](https://www.nflgsis.com/gsis/documentation/stadiumguides/guide_for_statisticians.pdf) subjects stadium statistical judgments to review by the NFL and its official statistician. The [Manning statement](https://www.espn.com/nfl/playoffs/2013/story/_/id/10224344/peyton-manning-passing-yardage-record-stand) identifies Elias as that statistician. Use NFL/Elias correction notices and versioned official statistical records for confirmation. A stadium gamebook is useful evidence of an initial record, not proof it incorporated all later corrections. A publisher's label “final” is not a universal settlement guarantee.

[MyFantasyLeague's historical explanation](https://myfantasyleague.wordpress.com/2008/09/11/official-nfl-stat-corrections/) describes typical Wednesday/Thursday distribution, not a universal deadline. [ESPN](https://support.espn.com/hc/en-us/articles/360000099732-Scoring-Stat-Corrections) distinguishes official changes from feed errors and has its own cutoff. [CBS](https://help.football.cbssports.com/s/article/How-do-Stat-Corrections-work) describes Thursday 6 a.m. ET finality for its product. These are platform rules, not league-wide finality. Watt's September 9 correction reported October 10 demonstrates why a seven-day-only archive is inadequate.

## Frequency: not yet measurable
Four selected post-game cases are not a representative sample. Their game-to-reported-correction calendar gaps are 2, 3, 4 and 31 days; these are NOT exact publication delays or a population distribution. We have no complete season denominator, all-games audit, or validated count of qualifying corrections. No annual rate, recall percentage, or claim that score amendments never occur is justified.

## Coverage gaps / review queue
No complete era or season is covered. Extra points, two-point conversions, safeties and interceptions lack an admitted verified correction case in this seed. Absence here is not evidence of absence historically.

Leads deliberately not promoted:
- [Elliott fumble recovery, 2018 reporting](https://www.actionnetwork.com/nfl/ezekiel-elliott-stat-correction-fantasy-football-fumble): exact before/after play text found; obtain official record and game-date corroboration.
- [Caleb Williams late correction, 2025](https://www.sportingnews.com/us/fantasy/chicago-bears/news/bizarre-caleb-williams-stat-correction-bears-qb-confusing-fantasy-football-scores/cc286bb9d3e34e955b4b6a20): authoritative reporting lead, not yet matched to official before/after records.
- [Alex Smith interception/fumble, 2013](https://www.arrowheadpride.com/2014/1/1/5263428/kansas-city-chiefs-alex-smith-lost-an-interception): secondary lead requires official verification.

Irregularities: Patriots and ESPN disagree on Gray's penalized defender; leave unresolved. Search metadata sometimes shows migration dates rather than original article dates. A current ESPN scoring summary still showed Mendenhall's original run while its rushing total was corrected: do not treat heterogeneous page components as one synchronized record.

## Automation built / not built
`scripts/monitor.py` is a dependency-free, snapshot-diff prototype for the current nflverse weekly player-stat CSV schema. It compares only existing game/player keys, handles fractional sacks, rejects malformed/missing schemas, preserves nulls, logs row additions/deletions separately, records hashes and observation times in SQLite, and emits candidate changes. No change is auto-promoted to the historical database. It does not discover an original value that was already overwritten before the first snapshot.

The nflverse release API confirms `stats_player/stats_player_week_2026.csv` exists. The older `player_stats` path has no 2026 asset. Repository release downloads redirect to a host blocked in this sandbox; no real CSV baseline was acquired. Legacy NFL fantasy correction URL redirected to NFL news during this review, despite search results still exposing old table snippets. Neither can be silently counted as a successful poll.

The prototype is **not scheduled**, has **no external notification delivery**, and has **not been tested against a downloaded production CSV**. GitHub Pages is static, not a background collector. CI cannot supply a missing feed. Automatic official verification, source comparison, scores/spreads, sportsbook lines and settlement remain unimplemented. A local diff JSON is not a delivered notification.

## Next session, in order
1. Obtain permitted versioned official data access and inspect terms, retention and redistribution rights. Add live schema contract tests. No credential should be put in the site or Git.
2. Run collector on persistent infrastructure with an object store and database; poll recent games frequently plus a season-long slow sweep. Archive every changed snapshot and maintain per-game coverage/watermarks.
3. Add official confirmation adapter; distinguish provider disagreement, official correction, pending adjudication and resolved non-change. A single shared upstream is not independent corroboration.
4. Add durable outbox, retry/backoff, idempotency keys, dead-letter queue and an authorized notification channel. Track attempted/succeeded polling, stale data, delivery acknowledgments and outages separately. Never alert “no discrepancies” when collection failed.
5. Capture market line, book/jurisdiction, timestamp and versioned settlement policy; compute win/loss/push from original/corrected values. Until then only report hypothetical sensitivity, never “winning bet.”
6. Backfill seasons systematically with correction bulletins AND original snapshots. Publish audited game/season counts and unresolved rows. Then estimate incidence and latency, with denominator and bias disclosure.
7. Add scheduled Pages publication only after persistent collector and safe review gate exist. No unattended commits to main; use reviewed PRs. Expand tests to source drift and delivery outages.

“No manual checking” is a reasonable happy-path goal, not a defensible guarantee: retired feeds, ambiguous rulings, conflicting sources and access rights require exception handling. Make those exceptions visible instead of guessing.
