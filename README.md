# NFL Scoring Discrepancy Observatory

[Public site](https://buffedlizard55-lab.github.io/SCORINGDISCREPNFL/) · [Research & limitations](docs/RESEARCH.md) · [Review log](docs/REVIEW.md)

**Start every session by reading this entire README.** `AGENTS.md` repeats this requirement for coding agents; documentation cannot guarantee a future agent obeys it.

## Status
Evidence-backed historical seed, **not a full historical database**. Seven cases, four post-game statistical corrections, two apparent-final/officiating cases, one reviewed non-change. No season exhaustively audited. No live official feed or sportsbook settlement integration. The site must never imply otherwise.

Run `python -m unittest discover -s tests -v` and `python scripts/build.py`.
Preview with `python -m http.server 8000 --bind 0.0.0.0`.
The committed root `index.html` works on the repository's existing main/root GitHub Pages configuration, with no dependencies or build service needed.

## Core Values (user-provided)
### Maximize P(Win)
“Maximize the Probability of Winning”: our decision making framework. In every decision, we weigh tradeoffs, assess risk, and choose the path that maximizes the probability that Arena succeeds. We set aside our emotions and make tough decisions in order to maximize P(Win). “Maximize P(Win)” frees us from constraints and clarifies that we must put Arena first.

### Own the Outcome
We own results end to end — not just our individual slice of the work. When problems arise and we have the means to act, we do so without waiting for permission or assignment. We treat failure and success as signals and use them to improve. At Arena, we stay accountable to the final outcome.

Project application: favor verifiable evidence over impressive counts, surface failed feeds, own deployment and tests, and never equate provider changes with confirmed NFL corrections.

## Original investigation brief — project north star
### NFL Scoring Discrepancy Investigation

Investigate documented NFL scoring discrepancies, scoring corrections, and post-game statistical corrections that can materially change a market-relevant outcome. Focus only on events that could affect the final score, team totals, game totals, spreads, or player statistical outcomes such as passing yards, rushing yards, receiving yards, receptions, passing touchdowns, rushing touchdowns, receiving touchdowns, field goals, extra points, safeties, interceptions, sacks, or other statistics that can determine a player or game market result. Do not include ordinary statistical corrections that cannot affect a relevant market outcome unless they help establish how the NFL correction process works.

Build a comprehensive historical database of qualifying discrepancies using official NFL sources and other authoritative, independently verifiable sources. For every event, identify the game, date, teams, player(s), original ruling/statistic, corrected ruling/statistic, exact numerical change, when the correction occurred, why the correction occurred, and which market-relevant outcomes could have changed. Distinguish between corrections that actually changed the official outcome and corrections that merely had the potential to change a market. Include the original and corrected values so the impact can be independently reproduced and verified.

Specifically investigate whether NFL scoring discrepancies can occur after the apparent completion of a game and whether official records can subsequently change in a way that crosses a relevant statistical threshold or changes a scoring outcome. Look for corrections involving touchdowns, field goals, extra points, two-point conversions, safeties, defensive scores, scoring attribution, passing/rushing/receiving statistics, and other events where the official record can change after the initial result. Determine how frequently these events occur, how quickly corrections are published, what official source controls the final record, and whether a reliable automated system could detect them without manual checking.

Put this prompt into the repo readme and read it everytime we work on the project as a starting point to make sure we are building what we are aiming for and have a strong base to continue building and improving on making something useful for everyday use. It should solve the problem of having to manually check everything ourselves and having an up to date current feed.

## Delivery and verification requirements
Build a clean, organized, user-friendly GitHub Pages site with official verified links for manual review. Work autonomously; no routine manual input. Flag irregularities for review. No hallucinations; verify line by line. The goal is a full list meeting the brief, not an unsupported claim of completeness.

Run multiple passes: (1) implement and verify; (2) find and fix bugs, missing requirements, assumptions and edge cases; (3) re-check against the original request, improve accuracy, reliability, completeness and code quality. Open a pull request and merge to main when safe. Document remaining work and limitations for the next session.
