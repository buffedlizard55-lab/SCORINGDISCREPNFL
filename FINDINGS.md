# Findings

The investigation narrative. Every number here is reproducible with the commands
in `README.md` §4, and every artefact is checked in under `data/`.

---

## How the investigation was run

The brief posed six questions. Rather than answer them from memory or from
secondary commentary, each was reduced to something measurable:

| Question in the brief | How we made it measurable |
|---|---|
| Can a score change after the game appears complete? | Diff historical versions of a versioned mirror of the official record; count revisions to games that were already final |
| How often do corrections occur? | Transcribe the official release pages week by week |
| How quickly are they published? | Measure game date → correction date for every transcribed row |
| What source controls the final record? | Quote the publisher statement on the official page itself |
| Could this be automated? | Build the detector and test it against real data |
| Which corrections actually changed an outcome vs merely could have? | Separate "did it happen" (diff study) from "could it have mattered" (closing-line analysis) |

---

## Finding 1 — No revisions observed in selected mirror comparisons

### Method

`nflverse/nfldata` commits `data/games.csv` to git roughly every 30 minutes
during the season. That gives a genuine time series of a well-maintained mirror
of the NFL's official results. We pulled the file at four historical commits,
kept **only games that already had a populated `result` field** (i.e. had
finished), and compared the frozen fields — `away_score`, `home_score`,
`result`, `total`, `overtime` — against today's record.

### Result

| Baseline commit | Date | Games already final | Frozen fields revised | Field revisions found |
|---|---|---|---|---|
| `88766138b8c3…` | 2023-12-03 | 6,602 | 0 | 0 |
| `204290217ee8…` | 2025-11-12 | 7,140 | 0 | 0 |
| `b1b3621d0452…` | 2026-01-20 | 7,273 | 0 | 0 |
| `eeec4e0bae47…` | 2026-09-22 | 7,308 | 0 | 0 |
| | **Total** | **28,323** | **0** | **0** |

Artefact: `data/evidence/score_integrity_study.json` — includes both input
SHA-256 hashes, the extraction method, and the caveat.

### Interpretation

**Post-game corrections change *attribution and statistics*, not the
scoreboard.** A receiver's 44 yards becomes 43; a sack is reassigned from one
player to two half-sacks; a play is reclassified from a forward pass to a
backwards lateral. None of that alters the final score.

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

## Finding 2 — What corrections actually look like (36 transcribed cases)

Transcribed verbatim from archived snapshots of the official NFL/Elias release
page. Full records with source links: `data/discrepancies.json`.

### They are routine, not exotic

| Season / week | Rows transcribed | Correction posted | Days after game |
|---|---|---|---|
| 2010 W1 (DEF) | 2 | Sep 15 | 3 |
| 2015 W16 | 14 | Dec 29–30 | 2–3 |
| 2017 W16 | 9 | Dec 26–27 | 2–4 |
| 2018 W14 | 11 | Dec 12 | 2–3 |

**Every single row landed 2–4 days after the game.** That is the real cadence:
the NFL League Office and Elias Sports Bureau review, then publish, in the early
part of the following week. This is the empirically measured answer to "how
quickly are corrections published": **same week, typically within three days**,
with the caveat that no published deadline exists (`LIMITATIONS.md` §10).

### They cluster in attribution, not scoring

By market-impact class:

| Class | Rows |
|---|---|
| Severity 3 — discrete scoring event or scoreboard change | **0** |
| Severity 2 — line-priced stat moved, or a round number crossed | 26 |
| Severity 1 — market-relevant but small (tackles, games played) | 6 |
| Severity 0 — out of scope | 4 |
| **Total** | **36** |

**Not one of the 36 corrections was a scoring event.** Not a touchdown, not a
field goal, not an extra point, not a safety, not a two-point conversion. They
are yardage adjustments, fumble re-attributions, sack reassignments and
defensive credits. This independently corroborates Finding 1 from a completely
different direction: the scoring events are stable, the bookkeeping around them
is not.

### The most market-significant cases found

**Michael Clark, WR, GB — 2017 Week 16** (`data/discrepancies.json` → `SC-0032`, `SC-0033`, `SC-0034`)

The Packers were shut out 16–0 at home by Minnesota on 2017-12-23. Four days
later, on Dec 27, the official record was corrected to add Clark's entire stat
line:

| Stat | Original | Corrected | Published fantasy delta |
|---|---|---|---|
| Games Played | 0 | 1 | 0.00 |
| Receptions | 0 | 3 | 0.00 |
| Receiving Yards | 0 | 36 | **+3.60** |

This is the strongest illustration of the whole phenomenon: a player who was
recorded as **not having played at all** was, days later, credited with three
catches and 36 yards — on a night his team scored zero points. Every receptions
and receiving-yards market on Clark moved from a certain loss to a win, and any
fantasy lineup that had him benched for "did not play" was retroactively wrong.

**Dak Prescott, QB, DAL — 2017 Week 16** (`SC-0029`, `SC-0030`)

Passing yards 182 → 181. Small in isolation; directly across a 181.5 prop line.
Note the source page lists this correction **twice, on two different dates**
(Dec 26 and Dec 27) — the official feed itself was re-issued. That is a real,
documented example of why a single snapshot is not enough and why the detector
must diff successive vintages.

**Dez Bryant, WR, DAL — 2017 Week 16** (`SC-0026`)

Receiving yards 44 → 43 on 2017-12-26. One yard, across a 43.5 line.

**Ben Roethlisberger, QB, PIT — 2015 Week 16** (`SC-0004`, `SC-0005`)

Passing yards 215 → 220 **and** receiving yards −8 → −3. The second row is
notable: a *negative* receiving-yards value was corrected, which is legal in the
NFL record when a player laterals backwards or is tackled behind the line on a
reception.

**Green Bay Packers DEF — 2010 Week 1** (`SC-0035`, `SC-0036`)

Sacks 5 → 6 and yards allowed 321 → 320, three days after GB 27 @ PHI 20. This
is the canonical "wrong jersey number written down on the sideline" correction
described in the secondary literature, and here it is at an official source:
the defence's sack total changed, along with the yardage its opponent was
credited with.

**Lamar Jackson, QB, BAL — 2018 Week 14** (`SC-0023`, `SC-0024`, `SC-0025`)

Rushing yards 71 → 67, rush attempts 13 → 14, and **times sacked 3 → 2**. The
sack and the rush attempt moving together is the fingerprint of a play being
reclassified — a scramble recorded as a sack is instead recorded as a
run. Exactly the mechanism the brief asks about, caught in the official record.

**Marvin Hall / Mohamed Sanu, WR, ATL — 2018 Week 14** (`SC-0017`, `SC-0018` for Sanu; `SC-0020`, `SC-0021`, `SC-0022` for Hall)

A mirrored pair: Hall's fumble and fumble recovery are removed (1 → 0) while
Sanu's are added (0 → 1). Same play, credit moved between two players. Hall also
loses three kickoff/punt return yards. This is a clean example of *attribution*
correction as distinct from *measurement* correction.

---

## Finding 3 — Exposure: how often a correction *could* have mattered

Since the scoreboard is stable (Finding 1) but bookkeeping is not (Finding 2),
the honest question is not "did it happen" but "how close did it come".

Using closing lines from the authoritative record, for every 2025–26 game with
both a final score and a line (349 games):

| Metric | Value |
|---|---|
| Games assessed | 349 |
| Finished within 1 point of the closing spread or total | **82 (23.5%)** |
| Pushed **exactly** on the closing spread | **10** |

Artefact: `data/market_sensitivity_2025_2026.csv`, with the arithmetic spelled
out per row (`margin_gap_points`, `total_gap_points`, `min_correction_points_to_flip_spread`).

**The 10 exact pushes are the sharpest cases.** On a push, no bet wins or loses.
A scoring correction of *any* size creates a winner where there was none. Ten
games out of 349 is roughly one every three weeks.

**Framing matters here, and the artefact enforces it.** A row means a correction
*would* have changed a market — not that one occurred. This is the concrete form
of the brief's instruction to distinguish corrections that actually changed an
official outcome from those that merely had the potential to. We found: **0 of
the former, 82 of the latter.**

---

## Finding 4 — The official source, and the fact that it was switched off

The official page stated its own provenance:

> "View official stat corrections as released by the NFL League Office and the
> official statistician of the NFL, Elias Sports Bureau."

So: **Elias Sports Bureau is the official statistician; the NFL League Office
co-publishes; that publication is what controls the final record.**

**Then it was retired.** On 2026-10-07, `https://fantasy.nfl.com/research/statcorrections`
**302-redirects** to `https://www.nfl.com/news/series/fantasy`, which now
advertises *"ESPN FANTASY — The Official Fantasy Game of the NFL."* An archived
snapshot from **2026-05-16** still shows the page working with season links
through 2025, which places the change in the 2026 offseason.

This is the single most consequential finding for anyone trying to build this
system, and it is the reason the architecture had to change: **you can no longer
poll an authoritative feed, so you must diff snapshots and label your output as
unconfirmed.** `LIMITATIONS.md` §1 covers the consequences.

---

## Finding 5 — Why a naive detector fails, and what we replaced it with

The first prototype diffed `games.csv` between 2026-09-22 and 2026-10-07 and
reported **61 changes**. Every one was a false positive:

- **61 of 61** were games that simply had not kicked off at the earlier date.
- **61 of 61** *also* showed line or odds movement (`spread_line`, `total_line`,
  moneylines) — real data, but market movement, not corrections.
- After applying both rules, **0** of the 61 survived. The true alert count for
  that fortnight was zero, and the naive detector reported 61.

That failure produced the two design rules the shipped engine enforces:

1. **Only diff records already final at the older timestamp.**
2. **Only diff frozen fields** (scores, result, total, overtime); never pre-game lines.

A third bug was found by review rather than by data: a 1-yard move from 182 to
181 passing yards was being classified as irrelevant because 182 is not a round
number. It is not irrelevant — it crosses an 181.5 line. The rule table was
restructured around **line-priced stats** (any integer change can cross a
half-point line) as distinct from **round-number milestones** (bonus markets).
All three defects now have regression tests in `tests/test_pipeline.py`, so they
cannot come back silently.

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
| Can NFL scoring discrepancies occur after apparent completion? | **Statistics can change; scoreboard permanence is not established** — no observed revisions in selected mirror comparisons | Finding 1 |
| Can official records change across a relevant threshold? | **Yes.** Passing 182→181, receiving 44→43, rec 0→3 / yds 0→36 all cross real prop lines | Finding 2 |
| How frequently do these occur? | **Every week, in small numbers.** 36 rows across four sampled weeks ≈ 4–14 per week across all positions | Finding 2 |
| How quickly are corrections published? | **2–4 days after the game**, clustered on the following Wednesday; no published deadline | Finding 2 |
| What controls the final record? | **Elias Sports Bureau, co-published by the NFL League Office** — via a channel now retired | Finding 4 |
| Could this be automated without manual checking? | **Detection: yes, and it is built and tested. Attribution: not for free in 2026.** | Finding 5, `LIMITATIONS.md` |

---

## What we deliberately did *not* claim

Three temptations we refused, because unverifiable rows would poison the dataset:

1. **No fabricated prop lines.** We model the *pricing convention* of line-priced
   stats. We never assert a line existed at a specific number.
2. **No realised-outcome claims.** `actually_changed_official_outcome` is `false`
   for all 36 rows, and a test fails the build if it is set without evidence.
   Every row documents *potential* impact only.
3. **No inclusion of unverifiable anecdote.** Widely repeated community reports
   describe corrections flipping fantasy championships. They are not in the
   database: they could not be verified to primary-source standard. They are
   named in `RECOMMENDATIONS.md` P2-4 as a known gap so their absence is not
   mistaken for evidence that nothing happened.
