# NFL Scoring Discrepancy Investigation

## Project Mission

Investigate documented NFL scoring discrepancies, scoring corrections, and post-game statistical corrections that can materially change a market-relevant outcome. Focus only on events that could affect the final score, team totals, game totals, spreads, or player statistical outcomes such as passing yards, rushing yards, receiving yards, receptions, passing touchdowns, rushing touchdowns, receiving touchdowns, field goals, extra points, safeties, interceptions, sacks, or other statistics that can determine a player or game market result.

Build a comprehensive historical database of qualifying discrepancies using official NFL sources and other authoritative, independently verifiable sources. For every event, identify the game, date, teams, player(s), original ruling/statistic, corrected ruling/statistic, exact numerical change, when the correction occurred, why the correction occurred, and which market-relevant outcomes could have changed. Distinguish between corrections that actually changed the official outcome and corrections that merely had the potential to change a market.

Specifically investigate whether NFL scoring discrepancies can occur after the apparent completion of a game and whether official records can subsequently change in a way that crosses a relevant statistical threshold or changes a scoring outcome. Determine how frequently these events occur, how quickly corrections are published, what official source controls the final record, and whether a reliable automated system could detect them without manual checking.

## How the NFL Stat Correction Process Works

The **Elias Sports Bureau** is the official statistician of the NFL. After each week's games, Elias reviews all plays on tape and issues official stat corrections. Key facts:

- **Corrections are issued every week** — typically by Thursday morning ET after the previous week's games
- **Elias meets with the NFL on Wednesdays** to confer and make official statistic changes
- **Corrections can arrive at any time** — there is no set deadline; corrections have been issued weeks or even months after the original game
- **Fantasy platforms apply corrections at different times**: ESPN (up to 7 days), CBS Sports (Thursday 6AM ET cutoff), Sleeper (through Thursday), Fleaflicker (Thursday 4AM/4PM ET)
- **The NFL official Gamebook** is the authoritative source — not box scores on third-party sites
- **Coaches can appeal** specific statistical rulings to Elias for review

### Data Sources for Corrections

| Source | URL | Type |
|--------|-----|------|
| NFL Fantasy Stat Corrections | https://fantasy.nfl.com/research/statcorrections | Official NFL corrections list |
| ESPN Stat Corrections | https://fantasy.espn.com/football/statcorrections | ESPN's correction page |
| Sportradar NFL API | https://developer.sportradar.com/ | Official NFL data partner |
| Sportradar Daily Change Log | Via Sportradar API | Tracks post-game stat revisions |
| FantasyData (SportsDataIO) | https://sportsdata.io/developers/api-documentation/nfl | NFL API with stat correction notes |
| NFL Guide for Statisticians | https://www.nflgsis.com/gsis/documentation/stadiumguides/guide_for_statisticians.pdf | Official scoring rules |
| Elias Sports Bureau | https://www.esb.com/ | Official NFL statistician |

## Historical Database

The complete database of verified scoring discrepancies is in [`data/discrepancies.json`](data/discrepancies.json) with a human-readable version at [`data/DATABASE.md`](data/DATABASE.md).

## Alert Detection System — Feasibility Analysis

See [`docs/ALERT_SYSTEM_ANALYSIS.md`](docs/ALERT_SYSTEM_ANALYSIS.md) for a detailed analysis of what's possible, what's not, and the limitations.

## GitHub Pages Site

The project site is available at [https://buffedlizard55-lab.github.io/SCORINGDISCREPNFL/](https://buffedlizard55-lab.github.io/SCORINGDISCREPNFL/)

## Core Values

### Maximize P(Win)
Maximize the Probability of Winning: our decision making framework. In every decision, we weigh tradeoffs, assess risk, and choose the path that maximizes the probability of success. We set aside emotions and make tough decisions to maximize P(Win).

### Own the Outcome
We own results end to end — not just our individual slice of the work. When problems arise and we have the means to act, we do so without waiting for permission or assignment. We treat failure and success as signals and use them to improve.

## Project Structure

```
SCORINGDISCREPNFL/
├── README.md                          # This file — project prompt & overview
├── data/
│   ├── DATABASE.md                    # Human-readable database of discrepancies
│   └── discrepancies.json             # Machine-readable database
├── docs/
│   └── ALERT_SYSTEM_ANALYSIS.md       # Alert detection system feasibility
├── site/
│   ├── index.html                     # GitHub Pages site
│   ├── style.css                      # Site styles
│   └── app.js                         # Site JavaScript
├── scripts/
│   └── fetch_corrections.py           # Automated correction fetcher
└── .github/
    └── workflows/
        └── deploy.yml                 # GitHub Pages deployment workflow
```

## Suggestions for Future Work

See the [Suggestions](#suggestions-for-future-work-1) section at the bottom of this README.

---

## Suggestions for Future Work

### Immediate Priorities (Next Session)
1. **Automated Correction Fetcher**: Build a script that polls the NFL.com stat corrections page and Sportradar Daily Change Log daily during the NFL season
2. **Webhook/Email Alerts**: Set up notifications when new corrections are detected that cross market-relevant thresholds
3. **Expand Historical Database**: Research corrections from 2010-2023 seasons using NFL Gamebooks
4. **Sportsbook Settlement Analysis**: Document which sportsbooks honor post-game corrections vs. settle on game-night results

### Medium-Term (1-2 Months)
5. **Real-Time Scoring Monitor**: Build a live monitor that flags suspicious plays during games for potential correction
6. **Threshold Alert System**: Alert when a player's stats are within a configurable distance of a market-relevant threshold (e.g., 99 rushing yards, 299 passing yards)
7. **Historical Frequency Analysis**: Quantify how often corrections affect market-relevant outcomes by season

### Long-Term
8. **API Integration**: Connect to Sportradar or SportsDataIO for real-time correction data
9. **Multi-Sport Extension**: Extend the system to NBA, MLB, NHL which also have stat correction processes
10. **Betting Market Impact Analysis**: Quantify the dollar impact of scoring discrepancies on betting markets
