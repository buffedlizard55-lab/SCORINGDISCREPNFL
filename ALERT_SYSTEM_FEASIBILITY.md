# Alert detection & notification feasibility

**Reviewed:** 2026-10-07 (UTC) · **Notification layer rebuilt the same day — see §"What changed in the notification review"**

**Question asked:** can we build an alert-detection notification system that detects
NFL scoring discrepancies? What are the limitations, and is it even possible?

**Reviewed:** 2026-10-07 (UTC). Every "verified" row below is the outcome of an actual
request made during this review, not an assumption carried over from a previous session.

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

---

## 1. Direct answer

**Three different questions hide inside that one question, and they have three
different answers.**

| Question | Answer |
|---|---|
| Can a machine detect that a *final score* changed after a game looked finished? | **Yes. Shipped, and demonstrated.** |
| Can a machine detect that a *player statistic* changed after a game looked finished? | **Yes in principle, but not demonstrated — and it can never be backtested against history using any channel available to this project.** |
| Can a machine tell you the change was an *official NFL/Elias correction*? | **No.** The official channel that said so was retired in 2026. |

The gap between rows 1 and 3 is the whole problem. A detector that fires is easy. A
detector whose output you are entitled to *believe* is the hard part, and it depends on
a source this project does not have.

---

## 2. What was actually tested this session

These are measurements, not recollections. Re-run them with the commands in §9.

| Route | Result | What it means |
|---|---|---|
| Final-game scoreboard diff | `pipeline/detect.py` compares five frozen fields (`away_score`, `home_score`, `result`, `total`, `overtime`) for games already final in the older snapshot. Tests cover unfinished games, volatile lines, missing records and alerts. | Input is the versioned `nflverse/nfldata` third-party mirror. Differences are not official NFL/Elias attribution and only persist if present at a poll. |
| Scheduled collection | `.github/workflows/detect.yml` is configured for daily runs during Sep–Feb plus an additional Wednesday poll. It snapshots the mirror and diffs successive slim snapshots. | GitHub Actions scheduling is best-effort, not a freshness SLA. It does not monitor player stats. A clean run only speaks to the compared snapshot fields. |
| Public comparison feed | `pipeline/feed.py` appends completed comparisons—including clean ones—to `data/alerts/feed.json`; `docs/index.html` renders the published copy. Entries retain input paths/hashes, comparison counts, rules and candidate alerts. | It is not a workflow-health log. Baseline-only, failed or aborted attempts may not create a row; check Actions for the latest attempt. The checked-in feed has two `clean` entries (2026-10-07 16:58:20 and 18:11:31 UTC), each comparing **7,340** final records, but the old/new SHA-256 values are identical in both. They are no-op comparisons, not evidence of a newly changed source payload. |
| Optional webhook push | `pipeline/detect.py` formats Slack-compatible or Discord-compatible payloads; `pipeline/notify.py` orchestrates delivery and `run.py deliver` is the workflow entry point. Unit tests cover payload shape, content and review links. | No live webhook delivery was performed. It is opt-in. There is no email/SMS channel, no user accounts and no read receipt. |
| Delivery receipts, idempotency, dead letters | Every attempt is appended to `data/alerts/deliveries.json` with an idempotency key derived from the compared snapshot hashes and alert ids (never the timestamp), attempt count, HTTP outcome and a dead-letter flag. Retries are bounded with backoff. Exhaustion exits 11 and fails the run so the baseline is not advanced. | At-least-once, not exactly-once: an endpoint can accept a message and lose the response, so a retry can duplicate. The webhook URL is never stored — only its host and a SHA-256. |
| Subscribable Atom feeds | `pipeline/atom.py` publishes `data/alerts/feed.atom` (one entry per completed comparison, clean runs included) and `data/corrections.atom` (one entry per verified correction, each linking its archived source page). Both are linked from the page head and validated as well-formed with unique entry ids by the merge gate. | Pull-based: someone still has to poll. Correction-entry timestamps are the database build time, because the archived pages print a calendar date with no time and none is invented. |
| Independent health watchdog | `pipeline/health.py` + `.github/workflows/health.yml` assess feed freshness, source movement, the snapshot store and its upstream commit watermark, dead letters, Atom consistency and published-copy drift. Each check reports ok/warn/fail/**unknown**, with a plain-language next action. | It cannot see a workflow GitHub disabled or delayed, a runner outage, or whether a delivered message was read. It reads this repository's artefacts, not the league's records. |
| Player-stat prototype and source helpers | `scripts/monitor.py` is a local CSV/SQLite prototype. `pipeline/fetch.py` includes release-metadata and asset-download helpers for potential sources. | Neither is an automated production player-stat detector. There is no validated vintage adapter, stable identity normalization, persisted before/after player-stat dataset or correction backtest. |
| Historical correction evidence | 141 correction rows are parsed from 22 stored archived page artefacts. The page-level evidence can be re-ingested (`ingest_rendered.py --check`), validated against an explicit contract (`pipeline/schema.py`), and re-read against a fresh rendering row by row (`pipeline/verify_artefact.py`). 137 rows join to a game; 4 lack a source-printed team code and remain flagged. | Sixteen sampled season-weeks across 13 seasons are a verified seed, not a comprehensive historical denominator. The archived notices generally give changed values, not the rationale; missing reasons remain unstated. One artefact was independently re-read this session (11/11 rows identical); the other 21 were not. |
| Source-movement measurement | `pipeline/vintage_study.py` downloads genuine upstream vintages pinned to commit SHAs and diffs them with the shipped detector: 45 vintages, 44 intervals, 59 days, 321,009 already-final record comparisons, 0 frozen-field changes, 179 other changes across 91 games. | It measures a mirror, and sampling at a stride cannot see a change made and reverted inside one interval. Zero frozen-field changes is a bounded observation, not a law. |
| Market sensitivity | The 2025–26 screen checks 349 mirror records with scores and closing-line values. 82 (23.5%) are within the configured one-point distance threshold; 10 have zero absolute-margin/spread-magnitude distance; 0 have zero total-line distance. The JSON summary records the exact input size and SHA-256. | This is numeric proximity only. It does not show that a book offered the line, that a correction happened, or that a bet pushed, won, lost or settled. The full source file is not retained. |

| `api.github.com` — nfldata commit list, nflverse release metadata | **200 OK** | Vintage discovery and scheduling work |
| `codeload.github.com` — full repo tarball (2.6 MB) | **200 OK in 0.65 s** | Historical `games.csv` vintages are retrievable |
| `raw.githubusercontent.com` | **fails** (curl exit 35/000) | The tarball route is mandatory, not a preference |
| `github.com/.../releases/download/<asset>` | **302 → 0 bytes** | Player-stat asset bytes are not downloadable from this environment |
| `api.github.com/.../releases/assets/<id>` with `Accept: application/octet-stream` | **302 → 0 bytes** | A second route was tried specifically to rule out an API proxy; same result |
| `web.archive.org` from `bash` | **fails** (curl exit 000) | Archived pages arrive only through a document-render channel |
| `web.archive.org` CDX API via the render channel | **works** | This is how all 22 evidence artefacts were retrieved |
| Asset re-upload: `stats_player` release published **2025-07-31**, its `stats_player_post_2023.csv` asset created **2026-08-13** | **confirmed** | Release assets are overwritten in place; prior bytes are not retained |
| Git-committed player-stat file in `nflverse/nfldata`, `nflverse-data`, `nflverse-pbp`, `guga31bb/nflfastR-data` | **none found** | No versioned player-stat history exists in the nflverse family |

---

## 3. The structural blocker

The detector distinguishes return code `10` (alerts found) from `0` (clean comparison) and treats other diff errors as failures. Delivery adds `11` (dead-lettered) and the watchdog adds `3` (unhealthy). The workflow does not advance the baseline after a failed comparison or a dead-lettered delivery, so the next run retries the same alert. This is not exactly-once delivery: a webhook can accept a message while its response is lost, so duplicates remain possible. No live webhook or end-to-end scheduled delivery has been verified in this review.

**The out-of-band monitor that this document previously listed as missing now exists.** `health.yml` runs on its own schedule (daily 06:00 UTC) and after every detection run, so a detector that stops writing anything still gets judged: the watchdog reads the artefacts on disk and fails when the newest completed comparison is older than the staleness threshold (40 h for a daily in-season schedule), when a published copy has drifted from its canonical source, when the Atom feed is malformed or out of step with the JSON feed, when the snapshot store has nothing to diff against, or when a notification is dead-lettered. Its residual blind spots are GitHub-side (a disabled or queued workflow, a runner outage, a rejected push) and human-side (whether a delivered message was read).

One conflation was found and fixed while building this: the feed's `identical_inputs` flag describes the *compared projection*, and an earlier revision of both the site and the documentation read it as "the source did not move". The snapshot manifests disprove that — the whole upstream file changed in all three recorded comparisons. Runs now carry `source_file_changed` alongside `identical_inputs`, the site renders both, and a test asserts every recorded run states source movement explicitly.

A differential detector needs two genuine vintages: the "before" bytes and the "after"
bytes. What exists:

- **`nflverse/nfldata` `data/games.csv` is committed to Git.** Thousands of dated
  versions exist and can be pulled and diffed. This is why scoreboard detection works.
  That file is **scoreboard-only — it contains no player statistics.**
- **Player statistics are published as release assets that get overwritten.** The
  evidence is in §2: a release published 2025-07-31 carries an asset created
  2026-08-13. Overwrite destroys the prior vintage.
- **No Git-committed player-stat file was found anywhere in the nflverse family.**

**The consequence, stated plainly:** a player-stat detector can be written and can begin
accumulating vintages the day it is switched on, but **it can never be validated against
the 141 known historical corrections**, because the "before" bytes for those weeks no
longer exist on any channel this project can reach.

That is not a code problem and not a budget problem. It is a property of how the
upstream data is published. Any plan that promises a validated player-stat alerting
system without first solving source retention is not a plan.

---

1. **Secure a permitted, versioned source.** Prefer an official corrections feed or a vendor/source whose specific product documents NFL/Elias provenance, revisions, timestamps, retention, field coverage and redistribution rights. Do not assume a paid product is official or independent without evidence.
2. **Build a player-stat adapter.** Preserve each genuine vintage’s raw bytes and SHA-256, validate schema, normalize stable game/player IDs, separate additions/removals/nulls from value changes, and produce reviewable source links.
3. **Backtest before alerting.** Recover known archived corrections from genuine before/after vintages. Report tested, detected, missed, false-positive and unavailable cases separately.
4. ~~**Make system health visible.**~~ — **DONE 2026-10-07.** `pipeline/health.py` publishes `data/alerts/health.json` with per-check statuses, a latest-success timestamp, an upstream commit watermark and a next action; `health.yml` sends failures through a separate operational channel and cannot be silenced by the detector.
5. **Harden delivery.** — **PARTLY DONE 2026-10-07.** Idempotency keys, bounded retries with backoff, HTTP-outcome receipts and dead-letter visibility are shipped in `pipeline/notify.py`, and the merge gate asserts the URL is never stored. Still open: an end-to-end Slack/Discord delivery test against a real (disposable) endpoint. Delivery acknowledgements beyond the HTTP status do not exist — no platform offers a read receipt for an incoming webhook.
6. **Only then evaluate settlements.** Obtain timestamped offered lines and applicable platform/book rules before asserting that a correction changed a wager or fantasy outcome.
7. **Expand the historical database with a reviewable manifest.** Enumerate observed archive captures, retain exact served timestamps and source artefacts, back off on rate limits, and report coverage without treating unobserved weeks as zero corrections.

## 4. What is implemented today

| Capability | State | Boundary |
|---|---|---|
| Final-game scoreboard diff | `pipeline/detect.py` compares five frozen fields (`away_score`, `home_score`, `result`, `total`, `overtime`) for games already final in the older snapshot | Input is the versioned `nflverse/nfldata` third-party mirror. A difference is a candidate, not official attribution, and is only visible if present at a poll |
| Scheduled collection | `.github/workflows/detect.yml`: daily in season (Sep–Feb) plus an extra Wednesday poll | Best-effort cron, not a freshness SLA. Monitors scoreboard fields only |
| Public comparison feed | `pipeline/feed.py` appends each completed comparison — including clean ones — to `data/alerts/feed.json`; the site renders it | Not a health monitor. Baseline-only, failed or aborted attempts may create no row |
| Optional webhook | Slack- and Discord-compatible payloads; `ALERT_WEBHOOK_URL` secret | Opt-in, so a fork never spams anyone. **No live delivery has been exercised.** No email/SMS, subscriptions, delivery receipts or idempotent outbox |
| Historical evidence | 141 rows from 22 stored archived-page artefacts; 137 join to a game; 4 flagged `TEAM_NOT_PRINTED` | A verified seed, not a comprehensive historical denominator |
| Market sensitivity | 2025–26 screen: 349 games, 82 (23.5%) within the configured one-point distance | Numeric proximity only. Not an offered line, a wager, a push or a settlement |

### The one real end-to-end run

The two feed entries inherited from earlier in the day were **no-op comparisons**: both
pairs of input hashes were identical, so they prove nothing about source bytes.

## What changed in the notification review (2026-10-07)

1. **Delivery became a system, not a POST.** `pipeline/notify.py` adds idempotency, bounded retries, receipts and dead letters; `run.py deliver` is the workflow entry point and exits 11 on exhaustion so the baseline is not advanced.
2. **A zero-configuration channel shipped.** Atom feeds for comparisons and for the verified database, published on Pages, validated for well-formedness and unique ids by the merge gate.
3. **The watchdog gap closed.** `pipeline/health.py` + `health.yml` assess freshness, source movement, watermark, dead letters, Atom consistency and copy drift, and never fold "unknown" into "ok".
4. **Source freshness became a recorded fact.** Every snapshot now carries the upstream commit SHA, date and codeload URL, and every feed run records whether the whole source file changed.
5. **The scoping rule got an evidence base.** The source-movement study measured the noise floor a naive detector would have produced (179 alerts / 59 days) against the signal it would have caught (0 scoreboard changes).
6. **Two data-integrity bugs were fixed.** `record_id` is now content-derived rather than positional (an insertion used to silently re-point external citations), and the fact layer is validated against an explicit contract (`pipeline/schema.py`) in the merge gate.
7. **A verification path was made mechanical.** `pipeline/verify_artefact.py` re-reads a stored artefact against a fresh rendering and reports row-level drift; it was mutation-checked, and the results of this session's checks are in `data/evidence/verification_log.json`. The re-read inputs are committed under `data/evidence/verification/`, so the check repeats from the repository alone (exit 0, 11/11 rows identical; the mutated inputs exit 2).

## Review links added by the notification pass

This session ran a genuine 15-day comparison:

| | |
|---|---|
| Window | 2026-09-22 → 2026-10-07 |
| Old input | `games.csv` at commit `eeec4e0b…`, SHA-256 `92e5890f…` |
| New input | `games.csv` at `master`, SHA-256 `d3a4878d…` |
| Records | 7,548 in each (7,308 already final at the older date) |
| Frozen-field differences among already-final games | **0** |
| Notes | The mirror genuinely changed in the window — 32 more games reached final — so this is not a no-op. Those 32 are excluded by rule 1, correctly, because a game that was not final at the baseline cannot be called a post-final revision |

That is the honest ceiling of what the current system demonstrates: **it works, on a
narrow field set, on a third-party mirror.**

### The null result is not vacuous

A "we found nothing" result only means something if the data was moving. Across four
polls on 2026-10-07 it was:

| Snapshot (UTC) | Full `games.csv` SHA-256 | Slim (final games, frozen fields) SHA-256 |
|---|---|---|
| 04:51 | `1da074c8…` | `341417de…` |
| 16:56 | `e5986b32…` | `341417de…` |
| 18:11 | `51550c2e…` | `341417de…` |
| 21:09 | `d3a4878d…` | `341417de…` |

The upstream file changed on **every poll**; the frozen-field projection never did.
The two design rules — compare only already-final games, and only frozen fields —
are therefore demonstrably suppressing real churn rather than reporting on a file
that simply never moves. This is the strongest available evidence that the detector
would notice a change if one occurred in the fields it watches.

---

## 5. Limitations, ranked by how much each one blocks the goal

### L1 — BLOCKER (external): the official corrections feed is retired
`https://fantasy.nfl.com/research/statcorrections` — the page carrying *"official stat
corrections as released by the NFL League Office and the official statistician of the
NFL, Elias Sports Bureau"* — 302-redirects to `https://www.nfl.com/news/series/fantasy`.
No replacement polling endpoint exists with documented access terms.

**Effect:** every alert is unattributable by construction. Nothing in this repository can
promote a mirror diff to "the NFL changed this".

### L2 — BLOCKER (external): player-stat vintages are not retained upstream
See §2 and §3. This removes the possibility of backtesting, which removes the usual way
of measuring false-positive and false-negative rates.

**Effect:** a player-stat detector would ship unmeasured. You would find out it was noisy
in production, which is the most expensive place to find out.

### L3 — HIGH: release asset bytes are not reachable from this environment
Both routes tested (§2). Likely reachable from GitHub Actions, which is where the
scheduled job runs — but "likely" is not "verified", and it cannot be verified here.

**Effect:** the download path cannot be tested before it is scheduled. It must be written
defensively, treated as unproven on first run, and fail loudly rather than silently
recording a clean result.

### L4 — HIGH: the successor channel is a JS app with no documented API
`fantasy.espn.com/football/statcorrections` renders client-side. Reading it means
reverse-engineering a private API — brittle, and likely against terms. **Declined.**

### L5 — MEDIUM: a mirror is not the NFL
`nflverse/nfldata` is a well-maintained third-party mirror. A change in it could be an
NFL correction, a provider repair, or a bug. The detector cannot distinguish them, and no
independent corroboration source is integrated. Two providers may also share upstream
data, so a second mirror is not automatically independent.

### L6 — MEDIUM: no per-game line or settlement record
Saying "this 1-yard change flipped a prop" needs the actual offered line, book, time,
applicable rules and the wager. None is in this repository. The market screens are
project-defined heuristics and are labelled as such everywhere.

### L7 — MEDIUM: a change-and-revert between two polls is invisible
The schedule is best-effort cron, not continuous monitoring. Anything corrected and
reverted inside one polling interval leaves no trace.

### L8 — RESOLVED (2026-10-07): silent-staleness risk
The feed records completed comparisons, not attempts, so a broken schedule used to
leave the page showing the last successful run as though it were current.

**Mitigation shipped.** `data/alerts/attempts.json` records the outcome of the most
recent *attempt* (`ok` / `baseline` / `failed` / `unknown`), written by an
`if: always()` workflow step (`python3 pipeline/run.py attempt --status …`) and rendered
as a banner at the top of the feed. A failure does not erase `last_success`, and the
banner states the age of the last attempt with an explicit warning past 48 hours. The
ledger is no longer banner-only: `pipeline/health.py` reads it as its `attempt_ledger`
check, so a failed attempt turns the monitor assessment FAIL, `health.yml` fails loudly
and posts its own webhook notice, and `validate.yml` rejects a ledger with an unusable
status string.

> Naming note: this ledger was originally published as `data/alerts/health.json`. That
> filename now belongs to the wider monitor self-assessment, which *consumes* the ledger.
> Both features are shipped; only the ambiguous name changed.

**Still open.** A workflow that GitHub never starts writes nothing at all, so it is
visible only as an ageing ledger and an ageing feed (WARN), never as an explicit failure.
And the live scheduled path has not been observed completing end to end on GitHub
Actions with a real webhook configured (P2-5).

### L9 — RESOLVED (2026-10-07): `record_id` was positional
`record_id` used to be assigned `SC-{i:04d}` in build order, so adding rows re-pointed
every ID below the insertion point — exactly what happened when the database grew from
74 to 141 rows. It is now derived from the row's own content (`pipeline/build_database.py`:
`stable_record_id()` over the identity fields), which means an external citation of an ID
survives insertions, reordering and rebuilds. A test asserts the IDs are stable across a
rebuild and unique within one. `RECOMMENDATIONS.md` P1-4 is DONE.

### L10 — LOW: `spread_line` sign convention is ambiguous
`market_sensitivity.py` uses only `|spread_line|`, which is correct under either
convention. The sign is never asserted.

---

## 6. Is it even possible? — the decision

**Yes, with a scoped definition of success:**

> A system that watches a dated, hash-recorded mirror of NFL game results, reports
> differences in frozen fields for games already final, publishes every run including
> clean ones, and routes candidates to a human for confirmation.

That system exists in this repository today.

**No, with the definition the brief implies:**

> A system that tells you, automatically and without manual checking, that an official
> NFL scoring or statistical record changed and that a market outcome moved.

Two independent reasons: the official attribution channel was switched off by a third
party (L1), and the data needed to prove a player-stat detector works was never retained
by anyone (L2). Neither is fixable by writing better code.

**The recommendation:** ship the narrow, honest system. Do not widen its claims to match
the ambition of the brief, because an alert that overstates its own certainty is worse
than no alert — it converts a monitoring system into a source of false confidence, and
the first time it is wrong in a way that costs money it will be switched off entirely.

---

## 7. Path to a genuinely trustworthy service

In dependency order. Each step is only worth taking once the one above it holds.

1. ~~**Make system health visible (L8).**~~ **DONE.** Attempt outcomes are recorded and
   rendered, so a failure no longer looks like a clean run. Remaining piece: alert on
   *silence* out of band, so a dead monitor reaches a human who did not open the page.
2. **Prove the scheduled run actually works end to end.** Confirm on GitHub Actions that
   a snapshot is fetched, a comparison completes, a feed row is written and a health
   record is committed — with differing input hashes, so a no-op cannot masquerade as a
   pass. **This is now the highest-value open item:** health reporting only pays off once
   the schedule it reports on is demonstrably running.
3. **Add asset download defensively (L3).** Bounded retries, explicit failure, and a
   manifest that distinguishes "no change" from "could not look". Never record a clean
   result when the source was unreachable.
4. **Start accumulating player-stat vintages now (L2).** The first vintage is captured
   on day one; every day of delay is a day of history permanently lost. Store bytes,
   SHA-256, retrieval time and upstream `updated_at`.
5. **Build the player-stat diff.** Validate schema, normalise stable game and player IDs,
   separate additions, removals and nulls from value changes, and emit reviewable
   source links. Test the diff logic against synthetic before/after fixtures — the logic
   can be tested even though the network path cannot.
6. **Backtest whatever can be backtested.** Historical player-stat vintages do not
   exist, so report tested / detected / missed / false-positive / unavailable counts
   honestly rather than treating "unavailable" as a pass.
7. **Only then evaluate settlement (L6).** Obtain timestamped offered lines and the
   applicable operator rules before asserting that a correction changed a wager.
8. **Harden delivery.** Idempotency keys, bounded retry with backoff, delivery
   acknowledgements, dead-letter visibility. Test Slack/Discord end to end without
   exposing the webhook secret.
9. **Add a second, genuinely independent source (L5)** — after checking upstream
   lineage, because correlated providers do not constitute corroboration.
10. **Expand the historical database with a reviewable manifest** (CDX enumeration,
    exact served timestamps, rate-limit backoff), and report unobserved weeks as unknown
    rather than as zero.

---

## 8. Decision principles applied

- **Maximize P(Win)** — fewer, source-verifiable alerts beat high volume and unsupported
  certainty. Provenance, false-positive control and explicit confidence are core
  functionality, not polish. The realistic path to a useful product is a narrow system
  people trust, not a broad one that gets switched off after its first confident mistake.
- **Own the Outcome** — account for collection, comparison, publication, delivery and
  *silence*. A site that leaves stale data looking current, or a job that fails quietly,
  is a failed monitor regardless of how good the diff logic is.

---

## 9. Review links

Reproduce the network findings:

```bash
# reachable: commit history + release metadata
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://api.github.com/repos/nflverse/nfldata/commits?path=data/games.csv&per_page=3"

# reachable: full repo tarball -> historical games.csv vintages
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://codeload.github.com/nflverse/nfldata/tar.gz/refs/heads/master"

# NOT reachable: release asset bytes (both routes 302 -> 0 bytes)
curl -sL -o /dev/null -w "%{http_code} %{size_download}\n" \
  "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_post_2018.csv"

# asset re-upload in place: compare published_at with asset created_at
curl -s "https://api.github.com/repos/nflverse/nflverse-data/releases/tags/stats_player" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['published_at']); \
    [print(a['name'], a['created_at']) for a in d['assets'] if 'post_2023' in a['name']]"
```

Code and evidence:

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
- [Comparison feed](pipeline/feed.py)
- [Source adapters](pipeline/fetch.py)
- [Archived correction rows and per-row source links](data/discrepancies.json)
- [Rendered archived-page artefacts](data/evidence/pages/)
- [Score-integrity study](data/evidence/score_integrity_study.json)
- [Market screen](pipeline/market_sensitivity.py) · [rule table](pipeline/market_rules.py)
- [Public site](docs/index.html)
- [Limitations](LIMITATIONS.md) · [Recommendations](RECOMMENDATIONS.md) · [Findings](FINDINGS.md)
