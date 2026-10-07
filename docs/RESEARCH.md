# Supplemental case-seed findings and feasibility — 2026-10-07

> **PERIOD DOCUMENT — do not read as current.** This file records supplemental
> case-seed research performed on 2026-10-07. It describes the database as a 36-row
> seed; the database has since been expanded to **141 rows across 13 seasons from 22
> archived evidence artefacts**. The twelve supplemental case studies remain valid as
> individually sourced narratives, but counts quoted below are historical. For current
> numbers see the root [`README.md`](../README.md).

> **Scope note after concurrent integration:** This report describes the twelve-case supplemental seed and `scripts/monitor.py`, not the broader pipeline/site merged in PR #2. Main now also contains an archived-corrections database, historical mirror comparison, market-sensitivity study and scheduled `pipeline/` workflow. See the root README, FINDINGS.md and LIMITATIONS.md for that work. Those additions have not been independently source-audited by this supplemental implementation; the tests below exercise their code, not prove their evidence. The statements about no schedule/no notifications below apply to the local seed prototype only.

## What is established
Yes, automatic **change detection** is feasible. Automatic determination that every change is an official correction, crosses an actually offered market line, and changes settlement is not feasible from an unversioned public box score alone.

The source-linked case seed separates:
- **Post-game official statistic changes:** Mendenhall 100→99, Gray 199→201, Roethlisberger/Mendenhall run→pass touchdown, Watt sack removed.
- **Apparent-final reversal:** Dawson's field goal added 3 points at the end of regulation; overtime then added another 3. Not a days-later reversal of a certified result.
- **Error acknowledged without final-score amendment:** Polamalu, 2008.
- **Review with no change:** Manning, 2013. Never count this as a correction.

These findings are backed by the event-level links and excerpts in [sources.json](../data/sources.json) and [events.json](../data/events.json). Exact clock time of correction is unknown unless explicitly supplied. Dates derived from contemporaneous reports are not precise publication-latency measurements.

## Five re-reviewed market-relevant case studies

These additions are **supplemental, source-linked case studies**, not new rows in the 36-row archived official-correction database. Official NFL gamebooks provide the primary record for the final statistical line and play; for Cutler, the accessible PDF conflicts with reporting and does not resolve the final version. In several cases, the original line or correction date is preserved only in contemporaneous reporting. The source trail, per-stat values and uncertainty flags are visible in the [supplemental case library](https://buffedlizard55-lab.github.io/SCORINGDISCREPNFL/research-seed/index.html) and its [structured records](../data/events.json). A changed player stat is not proof that a particular sportsbook line or settlement changed.

| Game / date | Reported before → final record | Timing / rationale | Market relevance and result | Evidence caveat |
|---|---|---|---|---|
| Broncos–Raiders, Sep. 8, 2008 — [Cutler case](https://buffedlizard55-lab.github.io/SCORINGDISCREPNFL/research-seed/index.html#2008-09-08-den-oak) | Cutler 299→300 passing yards reported; fourth-quarter completion to Nate Jackson. | The Denver Post page is dated Sep. 10, 2008, but also shows a 2016 update; MyFantasyLeague reported 299→300 Sep. 11, 2008. | Cutler passing-yard/300-yard-threshold props and potentially Jackson receiving-yard props could be affected; Jackson’s exact line is unresolved. Denver won 41–14, unchanged. | Accessible NFL gamebook still lists 299 and has no visible version date. The Denver Post page carries a 2016 update, so the footnote's original version time is not independently established. Preserve the conflict; do not call the final NFL line settled. |
| Bills–Ravens, Oct. 24, 2010 — [Fitzpatrick/Parrish case](https://buffedlizard55-lab.github.io/SCORINGDISCREPNFL/research-seed/index.html#2010-10-24-buf-bal) | Fitzpatrick: Bills reports 373 (Oct. 24) and 374 (Oct. 25), later 382; Parrish 49→57 receiving yards. | A secondary correction thread discusses the change around Oct. 27–28; the Bills use 382 Oct. 29. Specific play, reason and NFL timestamp not located. | Passing/receiving-yard props could be affected; Ravens won 37–34 in OT, unchanged. | The original QB baseline conflicts by one yard. The reported Fitzpatrick delta is +8 from 374 or +9 from 373. |
| Rams–Giants, Sep. 19, 2011 — [Manning/Nicks case](https://buffedlizard55-lab.github.io/SCORINGDISCREPNFL/research-seed/index.html#2011-09-19-ram-nyg) | Manning 18/29, 200→19/30, 223; Nicks 3/15→4/38. | Fleaflicker reported the NFL credit at 8:11 p.m. Sep. 21. Final NFL play-by-play has Nicks' 23-yard catch at 6:37 Q1 on fourth-and-four, PI declined. | Completions and passing/receiving yards could be affected; the drive still ended in the Giants' TD and the final score remained 28–16. Fleaflicker did not retroactively rescore that week. | Forum timestamp is a provider report, not an NFL system timestamp or sportsbook result. |
| Giants–Saints, Nov. 1, 2015 — [Brees/Snead case](https://buffedlizard55-lab.github.io/SCORINGDISCREPNFL/research-seed/index.html#2015-11-01-nyg-no) | Brees 40/50, 511, 1 INT→39/50, 505, 2 INT; Snead 7/76→6/70. Catch/fumble became an interception; the 63-yard return TD remained. | ESPN reported the Elias change Nov. 2; exact NFL database timestamp not located. Reported rationale: Snead never had full control. | Completion, passing/receiving-yard, reception, interception, fumble and defensive-return props could be affected; final score remained Saints 52–49. ESPN noted a fantasy-point effect, not a sportsbook settlement. | NJ.com reported 504 yards; the final NFL gamebook and ESPN list 505. The study retains the conflicting report. |
| Cowboys–Colts, Dec. 16, 2018 — [Elliott case](https://buffedlizard55-lab.github.io/SCORINGDISCREPNFL/research-seed/index.html#2018-12-16-dal-ind) | Elliott remained at 1 fumble; lost fumbles 1→0 and own recovery 0→1. | NFL Fantasy correction entry is indexed with Dec. 19; contemporary reports appeared Dec. 20. Final NFL play-by-play gives Q2 14:15, fourth-and-1 at IND 3: Elliott loses 2 yards and recovers at IND 5. | Fumbles-lost/recovery and fantasy markets could be affected; the failed fourth down and Colts' 23–0 win were unchanged. | The legacy NFL correction URL redirects. Initial Sheard attribution and rationale rely on secondary coverage; the final NFL book confirms the fumble was not removed. |

## Authority and timing
The [NFL Guide for Statisticians (2025), p.4](https://www.nflgsis.com/gsis/documentation/stadiumguides/guide_for_statisticians.pdf) subjects stadium statistical judgments to review by the NFL and its official statistician. The [Manning statement](https://www.espn.com/nfl/playoffs/2013/story/_/id/10224344/peyton-manning-passing-yardage-record-stand) identifies Elias as that statistician. Use NFL/Elias correction notices and versioned official statistical records for confirmation. A stadium gamebook is useful evidence of an initial record, not proof it incorporated all later corrections. A publisher's label “final” is not a universal settlement guarantee.

[MyFantasyLeague's historical explanation](https://myfantasyleague.wordpress.com/2008/09/11/official-nfl-stat-corrections/) describes typical Wednesday/Thursday distribution, not a universal deadline. [ESPN](https://support.espn.com/hc/en-us/articles/360000099732-Scoring-Stat-Corrections) distinguishes official changes from feed errors and has its own cutoff. [CBS](https://help.football.cbssports.com/s/article/How-do-Stat-Corrections-work) describes Thursday 6 a.m. ET finality for its product. These are platform rules, not league-wide finality. Watt's September 9 correction reported October 10 demonstrates why a seven-day-only archive is inadequate.

## Frequency: not yet measurable
The original seed's four selected post-game cases have game-to-reported-correction calendar gaps of 2, 3, 4 and 31 days. The five additional case studies have reported windows of roughly 1–5 days, with unresolved bounds in some cases. These are not exact publication delays and cannot be combined into a population distribution: the sample is purposive, and the accessible official correction timestamps are incomplete. We have no complete season denominator, all-games audit, or validated count of qualifying corrections. No annual rate, recall percentage, or claim that score amendments never occur is justified.

## Coverage gaps / review queue
No complete era or season is covered. Extra points, two-point conversions and safeties still lack an admitted **post-game** correction case in this supplemental seed; the Brees/Snead case adds an interception reclassification. In-game reversals remain a separate event type. Absence here is not evidence of absence historically.

Two re-reviewed studies remain outside the archived-official-correction database for explicit reasons:
- [Cutler, 2008](https://buffedlizard55-lab.github.io/SCORINGDISCREPNFL/research-seed/index.html#2008-09-08-den-oak): contemporaneous official-review reporting supports 299→300, but the accessible NFL gamebook still says 299 and the correction notice/version history is unresolved.
- [Elliott, 2018](https://buffedlizard55-lab.github.io/SCORINGDISCREPNFL/research-seed/index.html#2018-12-16-dal-ind): final NFL gamebook confirms 1 fumble, 0 lost and 1 own recovery; the legacy NFL Fantasy correction route redirects, and the initial attribution/reason relies on secondary reports. Do not repeat claims that the fumble itself was removed.

Leads still awaiting case-level verification:
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
