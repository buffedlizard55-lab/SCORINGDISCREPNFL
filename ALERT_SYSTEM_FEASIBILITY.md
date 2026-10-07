# Alert detection & notification feasibility

**Question asked:** can we build an alert-detection notification system that detects
NFL scoring discrepancies? What are the limitations, and is it even possible?

**Reviewed:** 2026-10-07 (UTC). Every "verified" row below is the outcome of an actual
request made during this review, not an assumption carried over from a previous session.

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

**Mitigation shipped.** `data/alerts/health.json` records the outcome of the most
recent *attempt* (`ok` / `baseline` / `failed` / `unknown`), written by an
`if: always()` workflow step and rendered as a banner at the top of the feed. A
failure does not erase `last_success`, and the banner states the age of the last
attempt with an explicit warning past 48 hours.

**Still open.** No out-of-band alert on silence, and the live scheduled path has not
been observed completing end to end on GitHub Actions.

### L9 — LOW: `record_id` is positional
`record_id` is assigned `SC-{i:04d}` in build order. Adding rows re-points every ID
below the insertion point. The site's case cards now select by natural key, so the page
is safe, but any external citation of an ID (issue, email, bookmark) breaks on the next
insert. Fix is in `RECOMMENDATIONS.md` P1-4.

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
- [Diff engine and webhook formatter](pipeline/detect.py)
- [Comparison feed](pipeline/feed.py)
- [Source adapters](pipeline/fetch.py)
- [Archived correction rows and per-row source links](data/discrepancies.json)
- [Rendered archived-page artefacts](data/evidence/pages/)
- [Score-integrity study](data/evidence/score_integrity_study.json)
- [Market screen](pipeline/market_sensitivity.py) · [rule table](pipeline/market_rules.py)
- [Public site](docs/index.html)
- [Limitations](LIMITATIONS.md) · [Recommendations](RECOMMENDATIONS.md) · [Findings](FINDINGS.md)
