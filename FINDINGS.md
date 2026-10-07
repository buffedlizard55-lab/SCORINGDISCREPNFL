# Findings

The investigation narrative. Reproduction commands are in `README.md` §5; each
claim below is tied to a checked-in artefact or a named source. Scope limits are
stated alongside the result.

---

## How the investigation was run

The brief posed six questions. Rather than answer them from memory or from
secondary commentary, each was reduced to something measurable:

| Question in the brief | How we made it measurable |
|---|---|
| Can a score change after the game appears complete? | Diff historical versions of a versioned mirror of the official record; count revisions to games that were already final |
| How often do corrections occur? | Describe 74 rows from nine selected archived week-pages; no population rate is inferred |
| How quickly are they dated? | Compute game date → date printed on each correction row; distinguish this from exact server publication time |
| Which source publishes the correction notices used here? | Quote the provenance statement on the archived official page; do not infer settlement authority |
| Could this be automated? | Build the detector and test it against real data |
| Which corrections actually changed an outcome vs merely could have? | Keep the mirror diff, the source correction rows and the line-distance screen separate; none independently proves a wager's realized settlement |

---

## Finding 1 — No revisions observed in selected mirror comparisons

### Method

`nflverse/nfldata` versions `data/games.csv` in Git. A small commit-history
sample inspected on 2026-10-07 had recent intervals of roughly 15–30 minutes
([history](https://github.com/nflverse/nfldata/commits/master/data/games.csv));
that is an observed repository cadence, not an NFL freshness SLA. We pulled the
file at four historical commits, kept **only games that already had a populated
`result` field** (i.e. had finished), and compared the frozen fields —
`away_score`, `home_score`, `result`, `total`, `overtime` — against the current
mirror record.

### Result

| Baseline commit | Date | Games already final | Frozen-field differences vs current | Field changes found |
|---|---|---|---|---|
| `88766138b8c3…` | 2023-12-03 | 6,602 | 0 | 0 |
| `204290217ee8…` | 2025-11-12 | 7,140 | 0 | 0 |
| `b1b3621d0452…` | 2026-01-20 | 7,273 | 0 | 0 |
| `eeec4e0bae47…` | 2026-09-22 | 7,308 | 0 | 0 |
| | **Total** | **28,323** | **0** | **0** |

Artefact: `data/evidence/score_integrity_study.json` — includes both input
SHA-256 hashes, the extraction method, and the caveat.

### Interpretation

The **74 rows parsed from 10 stored archived-page artefacts** change player
statistics or attribution; none documents a final-score amendment. Separately,
the four selected historical mirror comparisons show zero changes to the frozen
score fields. Neither the 74-row seed nor the mirror comparisons are
comprehensive, so they do not establish that scoreboard changes never occur.
Some play-level explanations are inference from paired stat changes, not reasons
stated by the correction notice, and are labelled accordingly below.

These selected comparisons do not prove scores are immutable or establish zero scoring-market exposure. The 28,323 total counts overlapping game-snapshot comparisons, not unique games. Mirror changes require official confirmation; missed within-interval changes remain possible.

### Why this is a *finding* and not a *proof*

The study tests a mirror, not the NFL's database. It cannot observe a correction
that was made and then reverted between two mirror updates, nor anything before
the mirror existed. That limitation is recorded in the artefact itself and in
`LIMITATIONS.md` §5, so the claim is never inflated beyond what the evidence
supports.

We specifically hunted for the opposite result — a real instance of a final
score being revised — and did not find one in 28,323 overlapping game-snapshot comparisons. That
negative result is the deliverable.

---

## Finding 2 — What the selected archived corrections document (74 rows)

The 74 row-level corrections are regenerated from 10 stored archived-page
artefacts and carry per-row review URLs in `data/discrepancies.json`. Nine
season-week groups contain corrections; the tenth artefact is an archived
2022 W17 page that explicitly reports no corrections.

### Observed rows and printed dates in the selected archive sample

| Season / week | Rows transcribed | Dates printed on source rows | Game-to-row-date gap among joined rows |
|---|---:|---|---|
| 2010 W1 (DEF) | 2 | Sep 15 | 3 days |
| 2012 W1 | 7 | Sep 12 | 3 days |
| 2013 W1 | 15 | Sep 11–12 | 3–4 days; four rows lack a printed team code and are not joined |
| 2015 W1 | 6 | Sep 15–16 | 1–3 days |
| 2015 W16 | 14 | Dec 29–30 | 2–3 days |
| 2017 W1 | 7 | Sep 14 | 4 days |
| 2017 W16 | 9 | Dec 26–27 | 1–4 days |
| 2018 W1 | 3 | Sep 12 | 3 days |
| 2018 W14 | 11 | Dec 12 | 3 days |
| **Total** | **74** |  | **70 rows join to a game** |

For the **70 joined rows**, the displayed correction calendar date is 1–4 days
after the game date (mode: 3 days; counts: 3 at day 1, 7 at day 2, 44 at day 3,
16 at day 4). These are date differences, not exact publication times. The four
2013 W1 rows without a source-printed team code have no game-date join and are
flagged rather than inferred. This purposive sample establishes neither a
population-wide weekly frequency nor a general deadline. A separate 2012
NFL.com report describes a sack correction 31 calendar days after the game
([source](https://www.nfl.com/news/j-j-watt-loses-nfl-s-sack-lead-on-statistical-correction-0ap1000000079268));
its article date is a reported date, not the exact moment the underlying record
changed.

### Project-defined market-review severity (not an offered-market inventory)

| Project severity | Rows | Interpretation |
|---|---:|---|
| 3 — scoring-related stat or scoreboard candidate | **0** | No selected row is a scoring-event correction or scoreboard-field change |
| 2 — candidate category / review-threshold heuristic | 48 | Prioritize for human market review; no specific market or line is asserted |
| 1 — other potentially relevant category under project rules | 14 | Review candidates, not confirmed market effects |
| 0 — out of scope under the current rule table | 12 | Project classification only |
| **Total** | **74** |  |

**None of the 74 selected rows records a changed touchdown, field goal, extra
point, safety, two-point conversion or final-score field.** They include
yardage, fumble attribution, sack/defensive credits, receptions and games
played. Severity is a project heuristic, not an independently verified market
inventory. This selected sample does not prove scoring corrections never occur
or that all score records are stable.

### The most market-significant cases found

**Michael Clark, WR, GB — 2017 Week 16** (natural keys in `data/discrepancies.json`: season 2017, week 16, player Michael Clark, each statistic, date Dec 27)

The Packers were shut out 16–0 at home by Minnesota on 2017-12-23. The three
archived correction rows carry a Dec 27 date label, four calendar days after
the game, and add Clark's line to the table:

| Stat | Original | Corrected | Published fantasy delta |
|---|---|---|---|
| Games Played | 0 | 1 | 0.00 |
| Receptions | 0 | 3 | 0.00 |
| Receiving Yards | 0 | 36 | **+3.60** |

This is a clear example of a recorded player line changing after the game:
Clark's games-played, receptions and yardage values changed in the archived
correction table even though his team scored zero points. That could affect a
reception/yardage prop or fantasy lineup if the applicable line and scoring
rules made the before/after values decisive. No specific sportsbook line,
league rule or settlement was verified, so we do not claim that every market
or lineup outcome changed.

**Dak Prescott, QB, DAL — 2017 Week 16** (natural keys in `data/discrepancies.json`: Passing Yards, dated Dec 26 and Dec 27)

Passing yards 182 → 181. A one-yard change could flip an over/under if the
relevant offered line were 181.5; no game-specific sportsbook line is part of
this record. The archived page lists this stat on two dates (Dec 26 and Dec 27),
which makes successive snapshots important, but it does not by itself establish
when each underlying NFL-system update was made.

**Dez Bryant, WR, DAL — 2017 Week 16** (natural key in `data/discrepancies.json`: Receiving Yards, dated Dec 26)

Receiving yards 44 → 43 on 2017-12-26. A one-yard change could cross a 43.5 over/under if that line was offered; no actual line was verified.

**Ben Roethlisberger, QB, PIT — 2015 Week 16** (natural keys in `data/discrepancies.json`: Passing Yards and Receiving Yards, dated Dec 30)

Passing yards 215 → 220 **and** receiving yards −8 → −3. The second row is
notable because the official correction table preserves negative receiving-yard
values. The notice does not identify the play-level reason for this correction;
we do not infer one from the numbers alone.

**Green Bay Packers DEF — 2010 Week 1** (natural keys in `data/discrepancies.json`: Sacks and Yards Allowed, dated Sep 15)

Sacks 5 → 6 and yards allowed 321 → 320, three days after GB 27 @ PHI 20.
The archived official rows establish these before/after statistics, but do not
state why they changed. The commonly cited wrong-player/jersey-number
explanation is secondary context and is not established by this correction row.

**Lamar Jackson, QB, BAL — 2018 Week 14** (natural keys in `data/discrepancies.json`: Rushing Yards, Rushing Attempts and Every Time Sacked, dated Dec 12)

Rushing yards 71 → 67, rush attempts 13 → 14, and **times sacked 3 → 2**.
Those paired changes are consistent with a play-classification change, but the
archived correction rows do not state the reason or identify a play. Treat
"sack reclassified as a run" as an unverified explanation, not a documented
cause.

**Marvin Hall / Mohamed Sanu, WR, ATL — 2018 Week 14** (natural keys in `data/discrepancies.json`: each player/stat pair, dated Dec 12)

The rows show Hall's fumble/recovery credits removed (1 → 0) and Sanu's added
(0 → 1); Hall also loses three kickoff/punt return yards. This pattern is
consistent with an attribution change, but the release rows do not explicitly
identify the play or state that Hall and Sanu's entries refer to the same play.
That pairing is an inference and remains flagged for review.

---

## Finding 3 — Market-line proximity, not a count of affected outcomes

The selected mirror comparisons observed no post-final frozen-field change,
while the separate archived-correction sample documents player-stat changes.
That does not establish global scoreboard stability. The separate distance
calculation measures how close final scores were to selected closing-line
values; it does not replay hypothetical corrections or sportsbook settlement.

Using closing-line fields in the third-party nflverse/nfldata record, for each
2025–26 game with both a final score and a line (349 games):

| Metric | Value |
|---|---|
| Games assessed | 349 |
| Either absolute-margin-to-spread-magnitude distance or total-to-line distance ≤ 1 point | **82 (23.5%)** |
| Absolute final-margin magnitude equal to absolute spread-line magnitude | **10** |

Artefact: `data/market_sensitivity_2025_2026.csv`, with the arithmetic spelled
out per row (`margin_gap_points` and `total_gap_points`).

**The 10 exact magnitude matches are not asserted to be pushes.** The spread
sign/side convention was not used to determine which team was favored, and the
metric does not apply an operator's settlement rules. No correction, wager, or
settlement is asserted.

**Framing matters here.** Each row is a line-distance sensitivity observation,
not an observed correction. The study found **zero frozen-field differences in
four selected mirror comparisons** and **82 games within the chosen one-point
distance threshold**. Those results must not be combined into a population
claim about realized betting outcomes.

---

## Finding 4 — The official source, and the fact that it was switched off

The official page stated its own provenance:

> "View official stat corrections as released by the NFL League Office and the
> official statistician of the NFL, Elias Sports Bureau."

So: the archived release identifies **Elias Sports Bureau as the NFL's
official statistician** and says the **NFL League Office** releases corrections
with Elias. This establishes the NFL correction source represented in the
archive; it does not determine sportsbook/fantasy settlement policy.

**Then it was retired.** On 2026-10-07, `https://fantasy.nfl.com/research/statcorrections`
**302-redirects** to `https://www.nfl.com/news/series/fantasy`, which now
advertises *"ESPN FANTASY — The Official Fantasy Game of the NFL."* An archived
snapshot from **2026-05-16** still shows the page working with season links
through 2025, which places the change in the 2026 offseason.

This is the single most consequential finding for anyone trying to build this
system, and it is the reason the architecture had to change: **you can no longer
poll the retired official corrections feed, so scoreboard diffs must use mirror
snapshots and label their output as
unconfirmed.** `LIMITATIONS.md` §1 covers the consequences.

---

## Finding 5 — The detector's scope and safeguards

The shipped scoreboard diff applies two rules, covered by regression tests:

1. **Only diff records already final in the older snapshot.** A newly completed
game is not a post-final revision.
2. **Only diff frozen fields** (scores, result, total and overtime); volatile
pre-game lines are excluded from the scoreboard comparison.

A previous exploratory diff used input vintages that are not retained together
as full source files in this repository. Its candidate-count breakdown is
therefore not used here as a reproducible headline result. The tests, source
code and retained snapshots specify the current detector behavior directly.

A separate market-rule review found that a one-yard move such as 182 to 181
passing yards should not be dismissed solely because it misses a round-number
marker. It could cross a hypothetical 181.5 line **if that market and line were
offered**; no specific book line for the game was verified. The rule table now
labels candidate line-market categories separately from project-defined
round-number review thresholds. Neither is proof of an actual market or line.

The evidence helper, parser, market rules and feed each have tests for their
failure modes; tests verify implementation behavior, not the truth of an
unprovided source.

**And a third independent bug** was caught when the evidence job first ran and
crashed: the HTTP helper transparently gunzipped any body starting with the
gzip magic bytes, which broke every `*.tar.gz` consumer before `tarfile` saw it
(the error was `not a gzip file (b'pa')`, the `pa` being the start of the
`pax_global_header` tar member). Decompression is now explicit and opt-in, with
the reasoning recorded in the code.

That is the argument for building the thing rather than describing it: three
real defects surfaced that no amount of specification writing would have found.

---

## Finding 6 — Answers to the brief's specific asks

| Brief question | Answer | Evidence |
|---|---|---|
| Can NFL scoring discrepancies occur after apparent completion? | **Documented player-stat changes exist; zero score-field revisions were observed across four selected mirror baselines. Official score immutability is not established.** | Findings 1–2 |
| Can official records change across a relevant threshold? | **Player values changed; they could cross a line if an applicable line was offered. Specific market lines were not verified.** | Finding 2 |
| How frequently do these occur? | **Not measurable from this purposive 9-week sample; no population denominator.** | Finding 2 |
| How quickly are corrections dated? | **The 70 joined source-row date labels are 1–4 calendar days after their games; not server timestamps or a deadline. A separate 2012 report is dated 31 days after its game.** | Finding 2 |
| What controls the NFL correction record? | **The archived page identifies the NFL League Office and Elias Sports Bureau as correction publishers; sportsbook settlement is platform-specific.** | Finding 4 |
| Could this be automated without manual checking? | **Candidate diffing and optional notification are feasible; the current implementation covers only game-score mirror fields, not an authoritative, comprehensive player-stat feed.** | Feasibility report and `LIMITATIONS.md` |

---

## What we deliberately did *not* claim

Three temptations we refused, because unverifiable rows would poison the dataset:

1. **No fabricated prop lines.** We use a project-defined candidate-stat
   heuristic for screening. We never assert a sportsbook offered a specific
   market or line.
2. **No realised-outcome claims.** `actually_changed_official_outcome` is `false`
   for all 74 rows; the current test rejects every `true` claim until a separate
   evidence review and test update. These rows document potential impact only.
3. **No inclusion of unverifiable anecdote.** Widely repeated community reports
   describe corrections flipping fantasy championships. They are not in the
   database: they could not be verified to primary-source standard. They are
   named in `RECOMMENDATIONS.md` P2-4 as a known gap so their absence is not
   mistaken for evidence that nothing happened.
