# Feasibility assessment: automatic NFL correction alerts

**Assessment date:** 2026-10-07
**Decision:** feasible as a *candidate-correction monitor* if a stable, public, machine-readable official source is available; not yet verified as a reliable always-on feed. Automatic detection of actual sportsbook market or settlement impact is not feasible from the sources currently confirmed.

## Direct answers

| Question | Current finding | Confidence / caveat |
|---|---|---|
| Can NFL statistics change after a game is over? | Yes. The NFL GSIS “About” page says existing game information is regularly corrected in conjunction with Elias Sports Bureau. AP reports weekly review and later requests. | High that post-game corrections occur; this does not establish the rate. |
| Is there a fixed deadline? | No fixed deadline is described by the AP report; it says October/November box scores were still corrected in January/February. | Reported practice, not a complete current operations specification. |
| How often do changes happen? | Not quantified by this project. The nine cases are curated, not a random sample; the AP article says sacks are the statistic changed most often but supplies no denominator. | No rate estimate. The feed/access gaps prevent a complete census. |
| What record controls the official stat? | NFL GSIS / NFL’s official statistician, Elias, is the relevant official statistical record. Current NFL.com logs and game centers are useful final-state sources. | The official current value is not always accompanied by a public version history. |
| Can a watcher alert on corrections? | Yes, in principle: poll an official correction table/API or compare continuously captured official stat snapshots, then publish a candidate alert with source evidence. | This repo’s legacy-page implementation is unvalidated against a stable live endpoint and deliberately fails closed on redirects/layout changes. |
| Can it determine the actual sportsbook result? | Not with a correction feed alone. It would also need an archived market/price, the correct operator/jurisdiction/product rule in force, and a wager/settlement record. | No actual NFL sportsbook line or settlement change has been verified in the reviewed sample. |
| Can it determine fantasy impact? | Sometimes: compare provider scoring and cutoff rules. | Provider policies differ, and league-specific matchup data may be private or only reported second-hand. Do not conflate this with sportsbook wagering. |

## How detection could work

A robust detector needs a versioned input rather than a single final-state page:

1. **Acquire an authoritative, durable correction list** with season/week, player/team, stat, before/after values, source date, and stable row identity. Check endpoint status, final URL, content type, timestamp, and schema.
2. **Capture snapshots** of each source response with retrieval time and cryptographic hash. Compare new rows and changed rows with the prior snapshots; do not rely only on a current total.
3. **Normalize** player identifiers, team abbreviations, stat names/units, season/week, and correction dates. Preserve the source wording and raw row alongside normalized fields.
4. **Validate** values against the current NFL/GSIS player log, gamebook, and game center. Resolve same-name players, team changes, multiple games, negative yardage, fractional IDP stats, and row-level duplicates. Flag a correction when data conflict; never discard a row silently.
5. **Publish an idempotent candidate notification** with a direct source link and the observed before/after values. Clearly say which checks ran and which did not. Deduplicate by source identity/content and keep a correction history if a source revises its own row.
6. **Separately assess possible market relevance.** A threshold crossing is only a hypothetical signal until an archived sportsbook market/line and applicable settlement terms are found. Record actual outcome only when a reliable final disposition is independently documented.

The current Python watcher implements a conservative subset: expected-table parsing, per-season/per-week page polling, deterministic row IDs, GitHub issue deduplication, and a health warning on source errors. By default it scans the active or most recently completed season plus the immediately preceding season; this lookback is configurable from one to five seasons. The workflow runs up to four times daily September–February and daily March–August, when late corrections may still appear. This bounded lookback is not a complete historical monitor: corrections to older seasons can still be missed. The watcher uses the standard library, has fixture-only tests, and has no sportsbook or fantasy-account integration. It is not yet a production-verified detector.

## Source and reliability limits

### Legacy NFL Fantasy corrections table

The legacy page identifies itself as showing official stat corrections released by the NFL League Office and Elias Sports Bureau, with default NFL-managed fantasy points. Search indexes still expose historical entries—for example, Jared Goff’s Oct. 28, 2020 passing-yard correction and DeMario Douglas’s Nov. 20, 2024 reception correction. During this review, canonical and regional historical URLs redirected to a general NFL Fantasy-news page; a direct request to `tab.fantasy.nfl.com` failed to fetch rather than returning the correction table. Search-result excerpts are useful leads but are not a dependable live endpoint or a substitute for opening the primary correction record.

The watcher uses the legacy table only as a **candidate source**. It checks that the response stays on the expected host and path and that a recognized table or empty-state is present. This prevents one important false negative (misreading an unrelated redirect as zero changes), but source unavailability means no current alerts. If the page simply omits a row, changes its archive, publishes later than the polling window, or silently changes meaning without a detectable schema change, the watcher cannot guarantee detection.

### Alternative feeds and snapshots

- **NFL GSIS/gamebooks/current NFL.com pages:** primary or official sources for current final data, but a final current record is not necessarily a before/after correction log. Polling final stats without storing the earlier snapshot cannot reveal when or how a number changed.
- **Fantasy provider corrections:** may echo NFL/Elias changes, but can have provider-specific scoring, cutoffs, corrections to data feeds, and manual league settings. These are not the official NFL record and not sportsbook settlement records.
- **Commercial sports-data APIs:** could provide contractual feeds, change timestamps, and service-level commitments. They may improve availability but require licensing, cost, vendor due diligence, and independent checks; no such feed is configured here.
- **Direct sportsbook sources:** market pages may be dynamic, personalized, jurisdiction-gated, or removed after a game. Even a public line is not a bet slip or settlement record. Terms and market rules can differ by state and product.

### Timing and market impact

AP describes NFL/Elias reviews each Wednesday, team requests later, and no fixed deadline. It says some October/November stats were still revised in January/February. In the nine curated game examples, all have a date attached to a cited public record/report, but those dates are not uniformly correction timestamps. Seven cited dates are 2–4 days after the game, Caleb Williams was reported 65 days later, and the AP Rodgers story is marked “FOR RELEASE” 76 days after that game while ESPN metadata says “Updated: Dec. 28” (before the Dec. 31 release); it is retrospective and does not reveal the actual NFL correction date. The Spiller/Kamara legacy-table dates cannot be independently re-opened in this review. These mixed source dates do not form a measured delay distribution.

A one-yard or one-reception difference could cross a hypothetical prop line. To conclude that an actual wager outcome changed, one must show (a) the market was listed and the exact line/price, (b) which operator, jurisdiction, product, and market rules applied, (c) the corrected value fell on the opposite side of that market definition, and (d) the operator’s final wager disposition. This research has not verified those elements for any sample case. No sample correction changed the documented official final score or winner.

Fantasy consequences are separate. AP’s 2011 Bills-defense sack anecdote reports a fantasy matchup reversal from a narrow win to a narrow loss, but does not give the exact game week or old/new sack totals. The Caleb Williams analysis claims fantasy manager outcomes changed, but its aggregate counts are not audited from league records. These reports are visible in the site and data only with their attribution and limits.

## Alert delivery and operational reliability

- The scheduled workflow runs every six hours from September through February (four runs/day in theory) and once daily March–August. It polls up to 18 regular-season pages for each of two seasons by default (configurable to one through five). GitHub may delay scheduled runs, and scheduled workflows generally need to exist on the default branch and be enabled.
- The live source has not yet passed the workflow’s manual dry-run. Until it does, the website accurately labels the monitor experimental and must not describe a blank feed as “no corrections.”
- Candidate issues use public GitHub Issues as the notification surface. Repository watchers can receive GitHub notifications, but users must configure their own watch/notification preferences. There is no email, SMS, mobile push, sportsbook integration, or guaranteed delivery SLA.
- A successful parser run would confirm only that the configured page was retrieved and parsed. It would not prove the source is complete, that the row is correct, or that a sportsbook market was affected.
- On source errors, non-dry-run workflow execution attempts to create one open health issue rather than silently reporting zero. A human still has to investigate endpoint changes and review correction candidates.

## Recommendations and blockers

### Before relying on the current watcher

1. Identify a stable official NFL correction endpoint or obtain written confirmation of a supported export/API. A search cache or redirecting URL is not enough.
2. Manually dispatch the workflow on the default branch with `dry_run=true`; record the final URL, response status, raw HTML shape, parsed rows, and empty-state. Repeat across at least one correction week and one no-correction week.
3. Add source snapshots and parser regression fixtures for real pages, including defense/IDP stats, fractional values, abbreviations, multiple corrections per player, no-correction pages, and redirects.
4. Run the first non-dry workflow only after source/parse checks pass and repository Actions/Issues permissions are confirmed. Review resulting candidate issues before relying on notifications.
5. Audit the nine historical rows and their original-value sources. In particular, older correction-table links currently redirect and should not be presented as currently accessible primary artifacts.
6. Expand the historical dataset season-by-season with a defined search protocol, source snapshots, completeness notes, and explicit exclusions. Publish counts by season only after reconciliation.
7. For betting impact, obtain lawfully archived market data and applicable operator/state rules. Actual wager/settlement claims additionally require primary settlement evidence; public media claims should remain attributed and secondary.

### Bottom line

A public correction *alert* is an achievable engineering task only if its upstream correction record remains public, stable, and sufficiently complete. This repository provides a fail-closed prototype and a source-linked research site, not a proven comprehensive surveillance system. An alert can establish “this source listed a change”; it cannot, by itself, establish “this sportsbook’s bet changed.”

## Primary reference links

- [NFL GSIS — About the statistical system and corrections](https://www.nflgsis.com/Help/About.html)
- [Legacy NFL Fantasy Stat Corrections page](https://fantasy.nfl.com/research/statcorrections) — current accessibility caveat applies
- [AP via ESPN — “Stats-taking at NFL games more art than science” (Dec. 31, 2011 release; updated Dec. 28)](https://www.espn.com/espn/wire?id=7399087)
- [Fanatics Sportsbook Tennessee house rules](https://sportsbook.fanatics.com/legal/tn/house-rules/) — one jurisdiction/operator; not a universal policy
- [ESPN fantasy scoring/stat correction policy](https://support.espn.com/hc/en-us/articles/360000099732-Scoring-Stat-Corrections) — fantasy product, not sportsbook rules
- [DraftKings Pick6 NFL season-long contest rules](https://pick6.draftkings.com/pick6-rules-and-scoring-nfl-season-long) — fantasy contest product, not sportsbook rules
