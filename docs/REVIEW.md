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
