# Research and data methodology

This page documents what the ledger means, where its values come from, and what must be checked before a candidate alert can become a historical case. Read the [project charter](../README.md#persistent-project-charter--read-this-first-at-the-start-of-every-work-session) first.

## Scope and inclusion

A case is included when a source documents a post-game change to a statistic that could be relevant to an NFL scoring record, player market, team/game total, spread, or fantasy score. This first release is a **curated example set**, not an exhaustive list, probability sample, or estimate of correction frequency. A row in the NFL Fantasy correction table is not by itself evidence that a sportsbook listed the statistic or changed a wager.

The main dataset is `data/historical-cases.json`. One game can have multiple players and multiple stat deltas. Each game case is counted once; each `{player, change}` pair is counted as one stat delta. Reports of downstream effects that do not identify enough game/stat data for a correction record are stored separately in `data/reported-downstream-effects.json`.

## Source hierarchy

For a qualifying record, collect and preserve evidence in this order where available:

1. **Correction artifact:** an official NFL/Elias/GSIS correction record that gives the original and corrected values and correction date. The legacy NFL Fantasy corrections page attributes its table to NFL League Office/Elias. Its present-day URLs have redirected to a general fantasy-news page in this review, so historical rows need independent archival or cached confirmation and live availability must not be assumed.
2. **Initial value:** a contemporaneous official team report, official box score/gamebook, provider snapshot, or reputable report published before the correction. Do not substitute a current final stat page for an original snapshot.
3. **Corrected value and result:** current NFL.com/GSIS player logs, game center, and gamebook. These establish the current official record and game result, but generally do not expose prior versions.
4. **Play explanation:** official gamebook/play-by-play/team report, then contemporaneous media/reporting. Separate the statistical reclassification from its explanation; a source describing a play does not by itself establish that the NFL later changed it.
5. **Market consequence:** an archived sportsbook line/price captured before the correction, the applicable operator/state/market rule, and a documented settlement record. Without all required elements, label the consequence *possible* or *not verified*. Fantasy scores, analyst simulations, public comments, and operator settlement clauses are not sportsbook settlement evidence.

Every `sources[]` entry includes a human-readable label, URL, source type, and a short statement of what that source supports. A source is not treated as supporting every field in the case. Links can move or disappear; link availability must be checked during each review. The ledger preserves unresolved uncertainty rather than silently filling blanks.

## Timing semantics

- `reported_on` is the date of the cited public correction record/report, **not necessarily the NFL’s exact correction timestamp**.
- `reported_on_basis` names the date source and its limitation.
- `elapsed_days_to_report` is the calendar-day difference between `game.date` and `reported_on`; it measures the cited report lag, not necessarily the correction’s true time-to-publication. It is `null` when the report date is not known.
- Date-known examples can mix an official correction-table date, a platform discussion date, and a media publication date. Do not pool them into a correction-frequency statistic without a new primary-source audit.

## Dataset fields

Each case records:

- `id`: stable descriptive slug; do not reuse it for a different game.
- `game`: season, regular-season week, game date, away/home team abbreviations, official final score, and NFL game-center URL.
- `reported_on`, `reported_on_basis`, `elapsed_days_to_report`: source date and date provenance.
- `players[]`: affected player(s), position, and `changes[]`.
- Each change records the stat, `initial`, `corrected`, arithmetic `delta` (`corrected - initial`), and separate `initial_basis`/`final_basis` descriptions.
- `reason`: play/reclassification account and what the source does or does not establish.
- `possible_market_impact[]`: an explicitly hypothetical market/threshold statement; no listed line should be implied unless a source is cited.
- `actual_market_impact`: separate sportsbook-line and settlement fields plus a note for fantasy or other platforms. A fantasy outcome does not populate a sportsbook outcome.
- `score_effect`: official score, winner, and point-total/margin outcomes are recorded separately from player-stat totals.
- `evidence_grade`, `evidence_grade_note`: the evidence category and the specific weakness/strength.
- `sources[]`: claim-scoped links for manual review.

The site renders values as text and constructs source links only from HTTPS URLs. It does not execute HTML from the dataset or from GitHub issue bodies.

## Evidence grades

- **A — direct correction record:** a correction entry itself gives the before/after values; final official player log/game center confirms the final value/result. This grade reflects the historical evidence captured for the row, not whether the original URL remains online today. If the correction artifact cannot be independently retrieved, note that limitation and reconsider the grade during review.
- **B — corroborated contemporary reporting:** contemporaneous source(s) establish the initial value/correction, and current official records support the final value/result, but a primary before/after correction artifact is absent or inaccessible.
- **C — incomplete/reconstructed:** a value, date, or link in the causal chain is inferred, reconstructed, or unavailable; the limitation is described in the case. A C-grade case is a lead, not a fully verified record.

Grades are not a substitute for reviewing each specific field. A case may have an official corrected total but a secondary-only original value or a separate unaudited fantasy impact.

## Market classification and guardrails

- Player props can include passing/rushing/receiving yardage, completions, attempts, receptions, touchdowns, interceptions, sacks, tackles, and other listed statistics. A market is only relevant if an operator actually offered it under rules covering that stat.
- Team/game total and spread outcomes depend on official points and market-specific grading rules. A non-scoring statistical correction cannot be assumed to change these outcomes; check whether scoring/play classification or the official final score actually changed.
- Fantasy-provider outcomes have different scoring formulas and finalization windows. Record the provider and policy where known. Never relabel a fantasy matchup as a sportsbook wager.
- “Not verified” is not “did not happen.” It records a research gap.
- A hypothetical threshold example illustrates possibility only and must not be counted as actual market impact.

## Watcher and alert lifecycle

The watcher polls the legacy correction table, parses an expected HTML table, and emits a GitHub issue per unique source row. A candidate issue is not automatically promoted to the historical dataset. Human review should verify the correction and official game/player record; preserve the initial value’s source; check the score/winner; and research applicable archived market evidence independently.

The parser raises a source error for redirects away from the expected host/path, unrecognized table layout, malformed stat-change text, or an unknown empty-state page. This is intentionally safer than reporting an empty week, but it cannot guarantee detection if the upstream source is unavailable, late, incomplete, or changes without triggering an error. GitHub schedule delay, API throttling, and repository notification settings create further delivery limits. The workflow does not scrape sportsbook websites, send direct mobile/email messages, or access private wagering records.

## Review checklist for future entries

1. Is this the correct game, week, date, player, team, and position?
2. Does a source show the *original* value before correction, or is it a reconstruction?
3. Does the correction source show both values, the correction date, and the rationale? If not, is each gap explicit?
4. Does a current official NFL/GSIS record confirm the corrected value, score, and winner?
5. Is the delta arithmetically correct? Is the stat name/unit unambiguous?
6. Is score/point-total/spread effect separate from player-market possibility?
7. Is any claimed actual market result tied to an archived line, the operator/jurisdiction/market rules in force, and settlement evidence?
8. Are fantasy-platform outcomes separately sourced and labeled?
9. Are all external links still accessible and correctly described?
10. Are caveats visible in both JSON and the site, not just in developer notes?
