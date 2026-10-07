# Limitations

Ranked by how much each one blocks the brief. Everything here was verified by
hand during the build; where a limitation has a workaround, the workaround is
named. Nothing here is speculative.

---

## 1. BLOCKER — the official NFL correction feed has been retired

**What we found.** The authoritative, machine-readable release of NFL stat
corrections was `https://fantasy.nfl.com/research/statcorrections`, which
carried the header: *"View official stat corrections as released by the NFL
League Office and the official statistician of the NFL, Elias Sports Bureau."*

As of **2026-10-07**, that URL **302-redirects** to
`https://www.nfl.com/news/series/fantasy`, a news hub that now promotes
*"ESPN FANTASY — The Official Fantasy Game of the NFL."*

**Verified how.** Direct fetch of
`https://fantasy.nfl.com/research/statcorrections?position=O&statSeason=2025&statWeek=1`
returns the NFL fantasy news page. An archived snapshot from **2026-05-16**
still shows a working corrections page with season links through **2025**, which
dates the retirement to the 2026 offseason.

**Why it matters.** The single most valuable input — the official
human-curated list of corrections, with old and new values — is no longer
published at a stable, pollable URL. Any automated system must now *infer*
corrections by diffing third-party data, which is strictly worse: it can produce
false positives and it cannot tell an official Elias correction apart from a
data-provider bug.

**Workaround shipped.** Archived snapshots remain and are what the database is
built from. They are excellent for *history* and useless for *live* alerting.

**What would unblock it.** A licensed data feed that republishes Elias
corrections (e.g. a commercial sports-data vendor), or a documented public API
from whichever party now publishes them.

---

## 2. HIGH — the successor channel is a client-side JS app with no documented API

`https://fantasy.espn.com/football/statcorrections` is the current consumer-facing
corrections page. Fetching it returns an application shell and a support-page
listing, not data: the content is rendered client-side.

**Why it matters.** Even if ESPN now carries the official corrections, there is
no documented, stable, terms-friendly endpoint to poll. Scraping it would mean
reverse-engineering a private API — brittle, and likely against terms.

**Workaround shipped.** None for live use. Recorded as a first-class limitation
rather than papered over with a fragile scraper.

---

## 3. HIGH — the highest-resolution correction signal is network-blocked here

`nflverse/nflverse-pbp` publishes **raw play-by-play per game** and, per
nflverse's own internal workflow documentation, runs a job whose stated purpose
is to *"Refresh raw pbp of the last week … to incorporate stat corrections
during the week"* (`.github/workflows/refresh_raw_pbp.yaml`, cron
`0 2 * 1,2,9-12 3` → **Wednesdays 02:00 UTC**).

That is the ideal detector: a play-by-play vintage that is *explicitly refreshed
to fold in corrections*. Diffing two vintages of one game's pbp would pinpoint
the exact play that changed.

**Why it is blocked.** Release assets are served from
`release-assets.githubusercontent.com`, which is **not reachable from the
evaluation sandbox** (`curl` returns `000`). Only `github.com`,
`codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org` and
`files.pythonhosted.org` are on the allowlist. On a GitHub Actions runner this
restriction does not apply.

**Workaround shipped.** The adapter exists (`fetch.nflverse_pbp_asset_index`,
`fetch.download_release_asset`) and the release index is enumerable via
`api.github.com` even here — asset *bytes* are what cannot be fetched. The
`detect.py` engine is source-agnostic, so pointing it at two pbp vintages is a
configuration change, not a rewrite.

---

## 4. MEDIUM — the first build could not validate its parser against byte-exact HTML

The Internet Archive (`web.archive.org`) is **not on the sandbox egress
allowlist**, so the corrections parser could not be run against real archived
HTML during the build. It is therefore unit-tested against fixtures that
reproduce the structure observed through the document-rendering channel, not
against raw bytes.

**Why it matters.** A parser that has never seen real input is unproven input.
This is exactly the kind of gap that normally gets quietly ignored.

**Workaround shipped.** `python3 pipeline/run.py selfcheck` fetches a known-good
archived page and asserts the parser recovers ≥10 fully-parsed rows. **Run this
before trusting any parsed output.** If it fails, reconcile the parser — do not
trust the rows.

---

## 5. MEDIUM — the mirror is not the NFL

All differential detection runs against `nflverse/nfldata`, a well-maintained
third-party mirror of the NFL's official game statistics. It is not the NFL.

**Consequences, stated plainly:**

- A change in the mirror could be a **correction by the NFL** or a **bug fix in
  the mirror**. The detector cannot tell them apart.
- Mirror update latency means the observed *timestamp* of a change is not the
  timestamp the NFL published it.
- If the mirror is wrong and stays wrong, the detector sees nothing.
- The score-integrity result in §1.1 of the README is a statement about the
  mirror's retention window, **not** a claim about the NFL's internal records.

**Workaround.** Every alert is labelled
`detected_by_diff_pending_manual_confirmation` and carries `actually_changed_outcome: null`.
Cross-checking against a *second* independent mirror would materially improve
confidence; no suitable free second mirror was found.

---

## 6. MEDIUM — no free, redistributable source of per-game prop lines

To say "this 1-yard correction flipped a prop", you need the prop line. Real
per-game player-prop lines are a commercial product.

**Workaround shipped.** `market_rules.py` encodes only what is defensible:

- **Discrete scoring events** (touchdowns, field goals, extra points, two-point
  conversions, safeties, defensive scores) — binary, no threshold judgement needed.
- **Line-priced stats** — stats that books price at essentially every integer,
  almost always at `X.5`. For these, *any* integer change can cross a line. This
  is a statement about the stat's pricing convention, **not** an assertion that a
  line existed at a specific value.
- **Round-number milestones** (300 passing yards, 100 receiving yards, …) for
  bonus markets.

Per-game prop lines are **never guessed**.

---

## 7. MEDIUM — the database is a seed, not the comprehensive corpus

36 verified rows across four weeks (2010 W1, 2015 W16, 2017 W16, 2018 W14).
The archived corpus spans 2010–2025 × 10 position filters × 18+ weeks, so the
achievable ceiling is orders of magnitude larger.

**Why it is not done yet.** Every page is a separate request against a
rate-limited archive, and the archive itself rate-limits (an HTTP 429 was hit
during the build). Bulk expansion belongs in a scheduled job with backoff, not
in an interactive session.

**Deliberate choice.** 36 rows that each link to an archived official page a
human can open beat thousands of rows nobody can check. Expansion is the top
item in `RECOMMENDATIONS.md`.

---

## 8. LOW — `spread_line` sign convention is ambiguous in secondary sources

nflverse's `spread_line` field has been described inconsistently as to whether a
negative value means the home team is favoured. We could not resolve this to a
primary definition during the build.

**Workaround shipped.** `market_sensitivity.py` uses **only the magnitude**,
`|spread_line|`. That is correct under either convention, so the analysis cannot
be wrong because of it. The sign is never asserted.

---

## 9. LOW — a correction reverted between two snapshots is invisible

If a value changes and changes back between poll N and poll N+1, the diff sees
nothing.

**Workaround.** Poll frequency is the only lever. In season, `nfldata` commits
every ~30 minutes, so a 30-minute poll cadence reduces (but does not eliminate)
the window. A real-world example of exactly this failure mode was observed in
the wild during 2025: a team sack was removed and then restored across the
fantasy playoffs.

---

## 10. LOW — no SLA, and no published deadline, for how long corrections may arrive

The source pages do not state a deadline. Multiple secondary sources agree there
is no fixed schedule, and that corrections can arrive days or weeks later.

**Workaround shipped.** The build does not assume a deadline. It flags
`DATE_LATE` beyond 14 days and `DATE_INCONSISTENT` for anything before the game,
rather than silently rejecting or accepting late rows.

---

## Summary — what is genuinely blocked vs merely unfinished

| Limitation | Blocked, or unfinished? |
|---|---|
| 1. Official feed retired | **Blocked by an external party's decision.** Needs a licensed feed. |
| 2. ESPN channel is JS-only | **Blocked** absent a documented API or permission. |
| 3. pbp assets unreachable | **Environment-only.** Works on Actions. Not a design problem. |
| 4. Parser unvalidated | **Unfinished.** `selfcheck` resolves it in one run. |
| 5. Mirror ≠ NFL | **Inherent.** Mitigate with a second source; cannot eliminate. |
| 6. No prop lines | **Commercial.** Model the convention, never guess values. |
| 7. Seed database | **Unfinished.** Scheduled bulk expansion. |
| 8–10. Convention/edge cases | **Unfinished or inherent.** Mitigations shipped. |

**Bottom line.** The *detection* problem is solvable and largely solved here. The
*authoritative-attribution* problem — knowing that a detected change is an
official Elias correction rather than a data glitch — is not solvable for free
as of 2026, because the channel that used to answer it was switched off.
