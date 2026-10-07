# Alert detection & notification feasibility

**Reviewed:** 2026-10-07 (UTC) · **Notification layer rebuilt the same day — see §"What changed in the notification review"**

## Direct answer

**A narrow scoreboard-mirror detector, a public comparison feed, subscribable Atom feeds, receipted webhook delivery and an independent health watchdog are implemented. The full requested system is not yet complete.** The current monitor does not detect player-stat revisions end to end, cannot attribute mirror changes to the NFL/Elias, does not verify historical sportsbook/fantasy settlements, cannot prove a notification was read, and cannot see a schedule that GitHub itself disabled.

**Is an alert-detection notification system possible here?** Split the question, because the halves have different answers:

| Half | Possible? | Evidence |
|---|---|---|
| *Detect* a post-final scoreboard change in a mirror | **Yes — shipped and dry-run on 44 genuine vintage pairs** | §1.1b of the README: 321,009 already-final record comparisons, 0 frozen-field changes, 179 non-frozen changes |
| *Detect* it reliably enough to alert on | **Only because the scope is narrow** | A naive any-field detector would have fired 179 times in 59 days for zero scoreboard changes |
| *Notify* a person with no configuration | **Yes — shipped** | Atom feeds published on Pages; no secret, no account, no endpoint to own |
| *Notify* a person by push | **Yes, opt-in** | Webhook transport with idempotency, bounded retries, receipts and dead letters; never enabled by default |
| *Know the monitor is still alive* | **Yes — shipped** | Independent watchdog workflow; "unknown" is never reported as "ok" |
| *Know a notification was read* | **No** | Slack/Discord webhooks return no read receipt; a 2xx proves acceptance only |
| *Attribute a change to the NFL/Elias* | **No** | The official corrections channel was retired in 2026; a mirror diff cannot tell a correction from a provider repair |
| *Detect player-stat corrections* | **Not yet** | Needs a validated vintage adapter and a backtest against known corrections (P0-3) |
| *Say a correction flipped a settled market* | **No** | Requires offered lines, timing and operator rules this project does not hold |

The distinction matters: an alert is a **candidate mirror change**, not an official correction. The market screens are **review heuristics**, not proof of an offered market, line or result.

## What is implemented

| Capability | Current state | Boundary |
|---|---|---|
| Final-game scoreboard diff | `pipeline/detect.py` compares five frozen fields (`away_score`, `home_score`, `result`, `total`, `overtime`) for games already final in the older snapshot. Tests cover unfinished games, volatile lines, missing records and alerts. | Input is the versioned `nflverse/nfldata` third-party mirror. Differences are not official NFL/Elias attribution and only persist if present at a poll. |
| Scheduled collection | `.github/workflows/detect.yml` is configured for daily runs during Sep–Feb plus an additional Wednesday poll. It snapshots the mirror and diffs successive slim snapshots. | GitHub Actions scheduling is best-effort, not a freshness SLA. It does not monitor player stats. A clean run only speaks to the compared snapshot fields. |
| Public comparison feed | `pipeline/feed.py` appends completed comparisons—including clean ones—to `data/alerts/feed.json`; `docs/index.html` renders the published copy. Entries retain input paths/hashes, comparison counts, rules and candidate alerts. | It is not a workflow-health log. Baseline-only, failed or aborted attempts may not create a row; check Actions for the latest attempt. The checked-in feed has two `clean` entries (2026-10-07 16:58:20 and 18:11:31 UTC), each comparing **7,340** final records, but the old/new SHA-256 values are identical in both. They are no-op comparisons, not evidence of a newly changed source payload. |
| Optional webhook push | `pipeline/detect.py` formats Slack-compatible or Discord-compatible payloads; `pipeline/notify.py` orchestrates delivery and `run.py deliver` is the workflow entry point. Unit tests cover payload shape, content and review links. | No live webhook delivery was performed. It is opt-in. There is no email/SMS channel, no user accounts and no read receipt. |
| Delivery receipts, idempotency, dead letters | Every attempt is appended to `data/alerts/deliveries.json` with an idempotency key derived from the compared snapshot hashes and alert ids (never the timestamp), attempt count, HTTP outcome and a dead-letter flag. Retries are bounded with backoff. Exhaustion exits 11 and fails the run so the baseline is not advanced. | At-least-once, not exactly-once: an endpoint can accept a message and lose the response, so a retry can duplicate. The webhook URL is never stored — only its host and a SHA-256. |
| Subscribable Atom feeds | `pipeline/atom.py` publishes `data/alerts/feed.atom` (one entry per completed comparison, clean runs included) and `data/corrections.atom` (one entry per verified correction, each linking its archived source page). Both are linked from the page head and validated as well-formed with unique entry ids by the merge gate. | Pull-based: someone still has to poll. Correction-entry timestamps are the database build time, because the archived pages print a calendar date with no time and none is invented. |
| Independent health watchdog | `pipeline/health.py` + `.github/workflows/health.yml` assess feed freshness, source movement, the snapshot store and its upstream commit watermark, dead letters, Atom consistency and published-copy drift. Each check reports ok/warn/fail/**unknown**, with a plain-language next action. | It cannot see a workflow GitHub disabled or delayed, a runner outage, or whether a delivered message was read. It reads this repository's artefacts, not the league's records. |
| Player-stat prototype and source helpers | `scripts/monitor.py` is a local CSV/SQLite prototype. `pipeline/fetch.py` includes release-metadata and asset-download helpers for potential sources. | Neither is an automated production player-stat detector. There is no validated vintage adapter, stable identity normalization, persisted before/after player-stat dataset or correction backtest. |
| Historical correction evidence | 74 correction rows are parsed from 10 stored archived page artefacts. The page-level evidence can be re-ingested (`ingest_rendered.py --check`), validated against an explicit contract (`pipeline/schema.py`), and re-read against a fresh rendering row by row (`pipeline/verify_artefact.py`). 70 rows join to a game; 4 lack a source-printed team code and remain flagged. | Nine sampled season-weeks are a verified seed, not a comprehensive historical denominator. The archived notices generally give changed values, not the rationale; missing reasons remain unstated. One artefact was independently re-read this session (11/11 rows identical); the other nine were not. |
| Source-movement measurement | `pipeline/vintage_study.py` downloads genuine upstream vintages pinned to commit SHAs and diffs them with the shipped detector: 45 vintages, 44 intervals, 59 days, 321,009 already-final record comparisons, 0 frozen-field changes, 179 other changes across 91 games. | It measures a mirror, and sampling at a stride cannot see a change made and reverted inside one interval. Zero frozen-field changes is a bounded observation, not a law. |
| Market sensitivity | The 2025–26 screen checks 349 mirror records with scores and closing-line values. 82 (23.5%) are within the configured one-point distance threshold; 10 have zero absolute-margin/spread-magnitude distance; 0 have zero total-line distance. The JSON summary records the exact input size and SHA-256. | This is numeric proximity only. It does not show that a book offered the line, that a correction happened, or that a bet pushed, won, lost or settled. The full source file is not retained. |

## Operational feasibility and safeguards

When configured and healthy, the scheduled workflow can collect a mirror snapshot, compare it, publish a Markdown/JSON result to the workflow summary/artifact, append a completed comparison to the feed, and optionally send a webhook. The workflow also persists snapshots and feed state as Git commits, which requires repository write permission and creates commit noise; it is not a production datastore.

The detector distinguishes return code `10` (alerts found) from `0` (clean comparison) and treats other diff errors as failures. Delivery adds `11` (dead-lettered) and the watchdog adds `3` (unhealthy). The workflow does not advance the baseline after a failed comparison or a dead-lettered delivery, so the next run retries the same alert. This is not exactly-once delivery: a webhook can accept a message while its response is lost, so duplicates remain possible. No live webhook or end-to-end scheduled delivery has been verified in this review.

**The out-of-band monitor that this document previously listed as missing now exists.** `health.yml` runs on its own schedule (daily 06:00 UTC) and after every detection run, so a detector that stops writing anything still gets judged: the watchdog reads the artefacts on disk and fails when the newest completed comparison is older than the staleness threshold (40 h for a daily in-season schedule), when a published copy has drifted from its canonical source, when the Atom feed is malformed or out of step with the JSON feed, when the snapshot store has nothing to diff against, or when a notification is dead-lettered. Its residual blind spots are GitHub-side (a disabled or queued workflow, a runner outage, a rejected push) and human-side (whether a delivered message was read).

One conflation was found and fixed while building this: the feed's `identical_inputs` flag describes the *compared projection*, and an earlier revision of both the site and the documentation read it as "the source did not move". The snapshot manifests disprove that — the whole upstream file changed in all three recorded comparisons. Runs now carry `source_file_changed` alongside `identical_inputs`, the site renders both, and a test asserts every recorded run states source movement explicitly.

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
4. ~~**Make system health visible.**~~ — **DONE 2026-10-07.** `pipeline/health.py` publishes `data/alerts/health.json` with per-check statuses, a latest-success timestamp, an upstream commit watermark and a next action; `health.yml` sends failures through a separate operational channel and cannot be silenced by the detector.
5. **Harden delivery.** — **PARTLY DONE 2026-10-07.** Idempotency keys, bounded retries with backoff, HTTP-outcome receipts and dead-letter visibility are shipped in `pipeline/notify.py`, and the merge gate asserts the URL is never stored. Still open: an end-to-end Slack/Discord delivery test against a real (disposable) endpoint. Delivery acknowledgements beyond the HTTP status do not exist — no platform offers a read receipt for an incoming webhook.
6. **Only then evaluate settlements.** Obtain timestamped offered lines and applicable platform/book rules before asserting that a correction changed a wager or fantasy outcome.
7. **Expand the historical database with a reviewable manifest.** Enumerate observed archive captures, retain exact served timestamps and source artefacts, back off on rate limits, and report coverage without treating unobserved weeks as zero corrections.

These steps can reduce repetitive manual checking on the healthy path. Human or authoritative-source escalation remains necessary for conflicting sources, outages, ambiguous rulings and settlement questions. A trustworthy system reports those states instead of converting uncertainty into a clean result.

## Decision principles

- **Maximize P(Win):** prefer fewer, source-verifiable alerts over high volume or unsupported certainty. Provenance, false-positive control and clear confidence are core functionality.
- **Own the Outcome:** account for collection, comparison, publication and delivery failures—not just diff logic. A site that leaves stale data looking current is not a successful monitor.

## What changed in the notification review (2026-10-07)

1. **Delivery became a system, not a POST.** `pipeline/notify.py` adds idempotency, bounded retries, receipts and dead letters; `run.py deliver` is the workflow entry point and exits 11 on exhaustion so the baseline is not advanced.
2. **A zero-configuration channel shipped.** Atom feeds for comparisons and for the verified database, published on Pages, validated for well-formedness and unique ids by the merge gate.
3. **The watchdog gap closed.** `pipeline/health.py` + `health.yml` assess freshness, source movement, watermark, dead letters, Atom consistency and copy drift, and never fold "unknown" into "ok".
4. **Source freshness became a recorded fact.** Every snapshot now carries the upstream commit SHA, date and codeload URL, and every feed run records whether the whole source file changed.
5. **The scoping rule got an evidence base.** The source-movement study measured the noise floor a naive detector would have produced (179 alerts / 59 days) against the signal it would have caught (0 scoreboard changes).
6. **Two data-integrity bugs were fixed.** `record_id` is now content-derived rather than positional (an insertion used to silently re-point external citations), and the fact layer is validated against an explicit contract (`pipeline/schema.py`) in the merge gate.
7. **A verification path was made mechanical.** `pipeline/verify_artefact.py` re-reads a stored artefact against a fresh rendering and reports row-level drift; it was mutation-checked, and the results of this session's checks are in `data/evidence/verification_log.json`. The re-read inputs are committed under `data/evidence/verification/`, so the check repeats from the repository alone (exit 0, 11/11 rows identical; the mutated inputs exit 2).

## Review links

- [Scheduled detection workflow](.github/workflows/detect.yml)
- [Independent health watchdog](.github/workflows/health.yml)
- [Weekly source-movement study](.github/workflows/source-churn.yml)
- [Delivery orchestration and receipts](pipeline/notify.py)
- [Monitor health assessment](pipeline/health.py)
- [Atom feed generation](pipeline/atom.py)
- [Source-movement study](pipeline/vintage_study.py)
- [Artefact re-read verification](pipeline/verify_artefact.py)
- [Fact-layer contract](pipeline/schema.py)
- [Verification log with review URLs](data/evidence/verification_log.json)
- [Diff engine and webhook formatter](pipeline/detect.py)
- [Comparison-feed implementation](pipeline/feed.py)
- [Player-stat prototype](scripts/monitor.py)
- [Source adapter helpers](pipeline/fetch.py)
- [Market-screen rules](pipeline/market_rules.py) and [distance analysis](pipeline/market_sensitivity.py)
- [Archived correction rows and source links](data/discrepancies.json)
- [Rendered archived-page artefacts](data/evidence/pages/)
- [Public site](docs/index.html)
- [Limitations](LIMITATIONS.md) · [Recommendations](RECOMMENDATIONS.md) · [Findings](FINDINGS.md)
