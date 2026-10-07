# Prior-session candidate cases — PRESERVED, NOT YET RE-VERIFIED

These files came from an earlier, parallel effort on the same brief
(branch `arena/838ce80a-scoringdiscrepnfl`, merged to `main` as PR #1). They are
**preserved here rather than deleted**, because several entries point at exactly
the kind of event the brief cares about most: a scoring play whose official
recording changed.

**They are NOT part of the verified database.** The canonical, per-row
primary-source-linked database is `../discrepancies.json`. These are kept
separate on purpose so that verified and unverified material never mix — which
is the entire value proposition of this repository.

| File | Contents |
|---|---|
| `discrepancies.json` | 11 candidate entries: `{metadata, entries}` — preserved verbatim from the prior session |
| `DATABASE.md` | The prior session's human-readable rendering of the same 11 entries |

---

## Why these are held back from the verified database

Reviewing the 11 entries surfaced two distinct problems.

### 1. In-game replay reversals are mixed in with post-game corrections

Several entries describe a ruling that was reversed **on the field, by replay,
during the game** — which is not the same thing as the NFL revising the official
record after the game. Those are fundamentally different phenomena with
completely different market implications:

- **In-game reversal** — the play is re-scored before the game ends. Markets
  settle on the corrected result. No bet is retrospectively flipped.
- **Post-game correction** — the record changes days later. Bets may already
  have settled. This is the phenomenon the brief targets.

Examples from these files that read as in-game replay reversals:

- `MIN-DET-2016-TGIVING-FELLS` — "Touchdown catch confirmed by replay official →
  overturned to incomplete pass (did not maintain control)". Its own
  `final_score` field records `DET 16, MIN 13`, i.e. the correction is already
  reflected in the final score, which is the signature of an in-game reversal.
- `NO-DET-2026-W02-SAINTS-TD` — a strip-sack recovery touchdown changed to an
  incomplete forward pass. Same ambiguity: if the 7 points were removed from the
  record described, the listed final score needs to be reconciled explicitly.

Before any of these can enter the verified database, each needs a primary source
that states **when** the change was made (during the game, or days after).

### 2. Incomplete provenance on several entries

Several entries carry `"final_score": "Not specified in source"` or
`"away_team_full": null`, and the `metadata.methodology` field asserts
"All entries verified from official NFL sources … with direct links provided"
without a per-entry primary link of the strength used in `../discrepancies.json`.

That is not a criticism of the prior work — it is a description of what would be
needed to promote these rows. Under this repository's rules
(see `README.md` §0 and §3), a row does not enter the verified database until it
carries a resolvable primary source a human can open and check line by line.

---

## How to promote a case into the verified database

1. Find a primary source (an archived NFL.com stat-corrections page, an official
   gamebook, or a league/team statement) that states the change and its date.
2. Add a row to `../verified_corrections_raw.json` with the corrected values and
   the source URL.
3. Run `python3 pipeline/build_database.py --games <games.csv>`. The builder will
   join it to the real game, classify its market impact, and raise
   `review_flags` automatically if anything does not reconcile.
4. Run `python3 tests/test_pipeline.py`.

The entries most worth chasing first, because they are the highest-value cases
in the whole project if they verify:

| Entry | Why it matters |
|---|---|
| `SEA-LAR-2025-W16-2PT` | A failed 2-point conversion changed to successful — this changes the scoreboard, i.e. it is the rare case the score-integrity study found zero of |
| `NO-DET-2026-W02-SAINTS-TD` | A defensive touchdown removed — 7 points, in an overtime game decided by 1 point |
| `PIT-PHI-2012-W05-ROETHLISBERGER` | A rushing touchdown re-attributed as a passing touchdown — changes two players' TD markets without changing the score |
| `DEN-2008-W01-CUTLER` | 299 → 300 passing yards — a textbook round-number threshold crossing |

> **Important context.** These cases do not contradict the score-integrity study
> in `../evidence/score_integrity_study.json`. That study found zero revisions to
> games that had already reached a final state in the source record. An in-game
> replay reversal is not a post-final revision, and a scoring change corrected
> *before* the record was finalised would never appear as a diff either. The two
> bodies of evidence are consistent; they are measuring different things.
