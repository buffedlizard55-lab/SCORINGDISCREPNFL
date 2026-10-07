# Alert detection & notification feasibility

**Reviewed:** 2026-10-07 (UTC)

## Direct answer

**A narrow scoreboard-mirror detector, a public comparison feed and optional webhook delivery are implemented. The full requested system is not yet complete.** The current monitor does not detect player-stat revisions end to end, cannot attribute mirror changes to the NFL/Elias, does not verify historical sportsbook/fantasy settlements, and cannot guarantee that a scheduled run happened or that a notification reached a person.

The distinction matters: an alert is a **candidate mirror change**, not an official correction. The market screens are **review heuristics**, not proof of an offered market, line or result.

## What is implemented

| Capability | Current state | Boundary |
|---|---|---|
| Final-game scoreboard diff | `pipeline/detect.py` compares five frozen fields (`away_score`, `home_score`, `result`, `total`, `overtime`) for games already final in the older snapshot. Tests cover unfinished games, volatile lines, missing records and alerts. | Input is the versioned `nflverse/nfldata` third-party mirror. Differences are not official NFL/Elias attribution and only persist if present at a poll. |
| Scheduled collection | `.github/workflows/detect.yml` is configured for daily runs during Sep–Feb plus an additional Wednesday poll. It snapshots the mirror and diffs successive slim snapshots. | GitHub Actions scheduling is best-effort, not a freshness SLA. It does not monitor player stats. A clean run only speaks to the compared snapshot fields. |
| Public comparison feed | `pipeline/feed.py` appends completed comparisons—including clean ones—to `data/alerts/feed.json`; `docs/index.html` renders the published copy. Entries retain input paths/hashes, comparison counts, rules and candidate alerts. | It is not a workflow-health log. Baseline-only, failed or aborted attempts may not create a row; check Actions for the latest attempt. The checked-in feed has two `clean` entries (2026-10-07 16:58:20 and 18:11:31 UTC), each comparing **7,340** final records, but the old/new SHA-256 values are identical in both. They are no-op comparisons, not evidence of a newly changed source payload. |
| Optional webhook | `pipeline/detect.py` formats Slack-compatible or Discord-compatible payloads; the workflow can use `ALERT_WEBHOOK_URL`. Unit tests cover payload shape, content and review links. | No live webhook delivery was performed. It is opt-in; no email/SMS, user subscriptions, delivery receipts or idempotent outbox are shipped. |
| Player-stat prototype and source helpers | `scripts/monitor.py` is a local CSV/SQLite prototype. `pipeline/fetch.py` includes release-metadata and asset-download helpers for potential sources. | Neither is an automated production player-stat detector. There is no validated vintage adapter, stable identity normalization, persisted before/after player-stat dataset or correction backtest. |
| Historical correction evidence | 74 correction rows are parsed from 10 stored archived page artefacts. The page-level evidence can be re-ingested; 70 rows join to a game and 4 lack a source-printed team code and remain flagged. | Nine sampled season-weeks are a verified seed, not a comprehensive historical denominator. The archived notices generally give changed values, not the rationale; missing reasons remain unstated. |
| Market sensitivity | The 2025–26 screen checks 349 mirror records with scores and closing-line values. 82 (23.5%) are within the configured one-point distance threshold; 10 have zero absolute-margin/spread-magnitude distance; 0 have zero total-line distance. The JSON summary records the exact input size and SHA-256. | This is numeric proximity only. It does not show that a book offered the line, that a correction happened, or that a bet pushed, won, lost or settled. The full source file is not retained. |

## Operational feasibility and safeguards

When configured and healthy, the scheduled workflow can collect a mirror snapshot, compare it, publish a Markdown/JSON result to the workflow summary/artifact, append a completed comparison to the feed, and optionally send a webhook. The workflow also persists snapshots and feed state as Git commits, which requires repository write permission and creates commit noise; it is not a production datastore.

The detector distinguishes return code `10` (alerts found) from `0` (clean comparison) and treats other diff errors as failures. The updated workflow should not advance the baseline after a failed comparison or failed configured webhook delivery, allowing a later retry. This is not exactly-once delivery: a webhook can accept a message while its response is lost, so duplicates remain possible. No live webhook or end-to-end scheduled delivery has been verified in this review.

The current feed records completed comparisons, not every workflow attempt. If the workflow is disabled, delayed, lacks write permission, cannot fetch the source, fails comparison, or fails to publish, the site may continue showing an older successful comparison. The feed UI notes identical input hashes, but operational freshness still requires checking the Actions run status. There is no separate out-of-band monitor to alert on a stale or failed schedule.

## What is not established

1. **Official attribution:** the legacy NFL Fantasy corrections page identified the NFL League Office and Elias Sports Bureau as publishers but is now retired. A third-party mirror diff cannot distinguish an official correction from a provider repair or bug. The current consumer-facing page is not used as an undocumented API.
2. **Player-stat automation:** no production before/after adapter is wired to the scheduled workflow. An upstream refresh note or downloadable asset is not enough; source access, vintage retention, schema, stable game/player IDs, rights and a known-correction backtest still need verification.
3. **Correction timing/frequency:** the 70 joined rows in this selected seed are dated 1–4 calendar days after their games (mode 3). Those are dates printed on archived pages, not exact publication timestamps or a population-wide rate/deadline.
4. **Real market outcomes:** no verified per-game player-prop line, wager or settlement dataset is included. The project’s category and distance rules rank cases for review only.
5. **Complete history:** the 74 rows span 9 sampled weeks in 6 seasons. Observed archive-search results are a candidate collection surface, not a proven complete denominator.

## Feasible path to a useful, trustworthy service

1. **Secure a permitted, versioned source.** Prefer an official corrections feed or a vendor/source whose specific product documents NFL/Elias provenance, revisions, timestamps, retention, field coverage and redistribution rights. Do not assume a paid product is official or independent without evidence.
2. **Build a player-stat adapter.** Preserve each genuine vintage’s raw bytes and SHA-256, validate schema, normalize stable game/player IDs, separate additions/removals/nulls from value changes, and produce reviewable source links.
3. **Backtest before alerting.** Recover known archived corrections from genuine before/after vintages. Report tested, detected, missed, false-positive and unavailable cases separately.
4. **Make system health visible.** Log success, failure, baseline, stale source and comparison status distinctly. Publish a latest-success timestamp and source watermark; send failures through a separate operational channel.
5. **Harden delivery.** Add idempotency keys, bounded retries/backoff, delivery acknowledgements and dead-letter visibility. Test Slack/Discord end to end without exposing webhook secrets.
6. **Only then evaluate settlements.** Obtain timestamped offered lines and applicable platform/book rules before asserting that a correction changed a wager or fantasy outcome.
7. **Expand the historical database with a reviewable manifest.** Enumerate observed archive captures, retain exact served timestamps and source artefacts, back off on rate limits, and report coverage without treating unobserved weeks as zero corrections.

These steps can reduce repetitive manual checking on the healthy path. Human or authoritative-source escalation remains necessary for conflicting sources, outages, ambiguous rulings and settlement questions. A trustworthy system reports those states instead of converting uncertainty into a clean result.

## Decision principles

- **Maximize P(Win):** prefer fewer, source-verifiable alerts over high volume or unsupported certainty. Provenance, false-positive control and clear confidence are core functionality.
- **Own the Outcome:** account for collection, comparison, publication and delivery failures—not just diff logic. A site that leaves stale data looking current is not a successful monitor.

## Review links

- [Scheduled detection workflow](.github/workflows/detect.yml)
- [Diff engine and webhook formatter](pipeline/detect.py)
- [Comparison-feed implementation](pipeline/feed.py)
- [Player-stat prototype](scripts/monitor.py)
- [Source adapter helpers](pipeline/fetch.py)
- [Market-screen rules](pipeline/market_rules.py) and [distance analysis](pipeline/market_sensitivity.py)
- [Archived correction rows and source links](data/discrepancies.json)
- [Rendered archived-page artefacts](data/evidence/pages/)
- [Public site](docs/index.html)
- [Limitations](LIMITATIONS.md) · [Recommendations](RECOMMENDATIONS.md) · [Findings](FINDINGS.md)
