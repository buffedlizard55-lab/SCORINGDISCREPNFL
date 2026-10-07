# Three-pass review — 2026-10-07

## Pass 1 — repository, evidence, implementation
Repository was a single 19-byte README, no application or tests. Pages already configured for main/root. Built source register, seven-case seed with original/corrected values and per-stat evidence, static responsive site, README charter, agent startup instructions, research/limitations report and a local SQLite snapshot detector. Sources reviewed through web search and page retrieval; article excerpts preserved, not full copyrighted archives.

## Pass 2 — assumptions and edge cases
- Separated play, game, season-to-date and apparent-final scopes; Dawson correction +3 is not the +6 including later overtime play.
- Polamalu acknowledgement is not a restored score; Manning retained values are not a correction.
- Gray defender conflict surfaced rather than guessed. Mendenhall 2010 reason marked unconfirmed by NFL.
- Source metadata migration dates not used as correction timestamps. No sportsbook settlement claimed.
- Reject empty/HTML/malformed/nonfinite feeds; missing values never become zero; additions/removals not scored as changes; fractional sacks preserved; failed parse leaves baseline untouched.
- Changed source plan after finding retired NFL endpoint and legacy nflverse release path. Actual current CSV download blocked by network restrictions; no invented baseline or “live” badge.

## Pass 3 — original-request audit
Eight automated tests pass; deterministic generation and JavaScript syntax check pass. Site contains all seven cards without requiring JavaScript and uses relative assets for repository Pages paths. Search/filter code reviewed; browser visual/interaction automation not run. Source links retrieved for core narratives; no automated full link-crawl or semantic fact-check guarantee is claimed. Tests validate structure/arithmetic, not truth.

Partial requirements remain explicit: exhaustive history, incidence estimates, precision timing, direct official current feed, automatic notifications and all-category coverage are NOT delivered. Autonomous research does not remove access/licensing limits. Next-session plan is in RESEARCH.md. Do not describe this release as fully satisfying those requirements.

## Concurrent-main reconciliation
Main advanced to `30f402c` during implementation, causing three conflicts. Reviewed
its README, dataset, scraper and deployment workflow. Preserved its documents,
case leads and old UI in `docs/archive/`, prominently marked unverified/superseded.
Did not admit Reddit-only cases or the guessed-column scraper. Kept existing
Pages Actions workflow, added tests/build before deploy, and generate identical
root/site copies so either existing deployment mode serves the current release.
No concurrent branch or PR was modified. Re-ran all local checks after resolution.

## Second concurrent-main reconciliation
PR #2 then merged as `be9b359`, adding a much broader dataset, `pipeline/`, a
scheduled detector and docs-based Pages deployment. Preserved that work and its
active README/site/workflows. This PR is now **supplemental**: the seven-case UI
lives in `research-seed/`, the local detector remains separately scoped, and the
source mappings are not silently mixed into the broader database. Earlier status
statements above apply to this contribution, not the newer main implementation.
Root README links both contributions. No claim is made that this session
independently verified PR #2's archived sources or historical mirror study.

Final integrated local verification: all **40 tests** (32 pipeline + 8 seed) pass;
both main and supplemental JavaScript syntax checks pass; supplemental build is
deterministic; diff against current main has no new whitespace errors.

PR #4 subsequently merged (`9a96509`) to restore root Pages and add validation.
Kept its root site, validation workflow and sync script intact. Re-ran all **42
integrated tests** successfully. Supplemental code still never overwrites root.

## Follow-up three-pass review — 2026-10-07

The fixed Arena branch was initially 16 commits behind the current `origin/main`.
Fast-forwarded **the same required branch** to current main before integrating
new research. Preserved the existing root Pages deployment, 36-row correction
database, mirror study, pipeline, validation workflow and README charter; did
not apply the stale parallel `docs/` draft over those files.

### Pass 1 — implement and verify
Added five source-linked case studies to the supplemental `data/events.json`
seed and `data/sources.json` evidence register: Cutler (2008), Fitzpatrick and
Parrish (2010), Manning and Nicks (2011), Brees and Snead (2015), and Elliott
(2018). Regenerated the supplemental static case library; updated the root site
link and README. These are separate from the 36-row archived-official-correction
database. No sportsbook line or settlement is claimed.

### Pass 2 — review and fix
Compared each new case against the available official NFL gamebook, contemporaneous
team reporting and/or independent contemporaneous reports. Retained explicit
conflicts: Cutler's accessible NFL PDF says 299 while the Denver Post footnote
and MyFantasyLeague report 300; the Denver Post page also shows a 2016 update,
so the footnote's original publication time is not established. Bills reporting
says 373 then 374 before 382; NJ.com says Brees 504 while
the final NFL book says 505. Recorded the Nicks play at 6:37 Q1 and the FleaFlicker
report time without treating it as an NFL timestamp. For Elliott, the final NFL
book confirms one fumble, zero lost and one own recovery; corrected the stale
candidate wording that could imply the fumble itself disappeared. Kept the
initial Sheard attribution and correction rationale labeled secondary, and the
legacy NFL Fantasy correction route labeled inaccessible. Changed the seed UI
to say “reported correction / decision date” rather than imply exact system time.

### Pass 3 — complete requirements audit
Kept the original full governing brief and Core Values in README; linked the
supplemental case library; recorded timing, reasons, possible markets, score
outcomes and settlement caveats for all five added events. Rechecked that the
sample is not used as a frequency estimate, the market impacts are hypothetical,
source conflicts are visible, and the project still clearly states its retired
official-feed, licensing, odds, persistent-storage and notification blockers.
The existing Pages root-build setting remains unchanged; no competing Pages
workflow was added. Final local test/build results are recorded after the final
run below, before PR creation.

### Final verification

- `python3 -m unittest discover -s tests -v`: **44 passed** (35 pipeline tests,
  9 supplemental tests).
- `python3 scripts/build.py`: deterministic supplemental page with **12 cards**;
  source IDs, HTTPS links, numeric deltas, and the five re-review caveats validate.
- `./pipeline/sync_site_data.sh`: root Pages copies synchronized with canonical
  `docs/` copies; the site-contract tests confirm no drift.
- `node --check app.js`, `node --check docs/app.js`, and
  `node --check research-seed/site.js`: passed.
- JSON parsing for the case seed, source register, correction database, score
  study and market-sensitivity data passed; `git diff --check` passed.
- The local root preview returned HTTP 200 for `/`, the root CSS and JS, the
  supplemental case page, and `/data/events.json` (12 events).

No automated browser interaction/screenshot test or exhaustive public-link crawl
was available. This review is not a guarantee against later source changes or
publisher corrections; the case cards preserve their source and evidence caveats.
