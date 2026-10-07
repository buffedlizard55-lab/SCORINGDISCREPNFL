// Database entries (embedded for GitHub Pages compatibility)
const entries = [
  {
    id: "SEA-LAR-2025-W16-2PT",
    category: "scoring_change",
    title: "Seahawks 2-Point Conversion Reversal",
    date: "December 18, 2025",
    teams: "SEA vs LAR",
    week: "Week 16, 2025",
    players: ["Sam Darnold", "Zach Charbonnet", "Jared Verse"],
    original: "Failed 2-point conversion (incomplete forward pass)",
    corrected: "Successful 2-point conversion (backward pass/lateral recovered in end zone)",
    change: "+2 points for Seattle (30-28 → 30-30 tie). Seahawks won 38-37 in OT.",
    when: "During game, 100-second replay review",
    why: "Replay determined Darnold's pass traveled backward, making it a lateral. Verse's deflection made it a live ball. Charbonnet recovered in the end zone.",
    changedOutcome: true,
    sources: [
      { name: "ESPN", url: "https://www.espn.com/nfl/story/_/id/47354685/sean-mcvay-rams-question-overturned-call-2-point-attempt" },
      { name: "CBS Sports", url: "https://www.cbssports.com/nfl/news/rams-propose-nfl-rule-change-seahawks-2-point-conversion/" },
      { name: "NBC Sports", url: "https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/report-rams-will-propose-change-to-rule-that-led-to-wacky-seahawks-two-point-play" }
    ]
  },
  {
    id: "PIT-PHI-2012-W05-ROETHLISBERGER",
    category: "scoring_attribution",
    title: "Roethlisberger / Mendenhall Lateral Ruling",
    date: "October 7, 2012",
    teams: "PIT @ PHI",
    week: "Week 5, 2012",
    players: ["Ben Roethlisberger", "Rashard Mendenhall"],
    original: "13-yard rushing touchdown for Mendenhall (pass ruled as lateral)",
    corrected: "13-yard passing touchdown from Roethlisberger to Mendenhall (forward pass)",
    change: "Roethlisberger: +13 passing yards, +1 passing TD. Mendenhall: -13 rushing yards, +13 receiving yards.",
    when: "October 10, 2012 (3 days after game)",
    why: "Elias Sports Bureau reviewed tape and determined the pass traveled forward, not backward.",
    changedOutcome: false,
    sources: [
      { name: "ESPN", url: "https://www.espn.com/nfl/story/_/id/8487929/ben-roethlisberger-awarded-touchdown-pass-stats-change" },
      { name: "Steelers Depot", url: "https://steelersdepot.com/2012/10/roethlisberger-credited-with-touchdown-pass-to-mendenhall-by-elias/" },
      { name: "SB Nation", url: "https://www.sbnation.com/nfl/2012/10/11/3489324/ben-roethlisberger-stat-correction-nfl-fantasy-football-steelers" }
    ]
  },
  {
    id: "DAL-IND-2018-W15-ELLIOTT",
    category: "fumble_attribution",
    title: "Ezekiel Elliott Fumble Reversal",
    date: "December 16, 2018",
    teams: "DAL @ IND",
    week: "Week 15, 2018",
    players: ["Ezekiel Elliott", "Jabaal Sheard", "Pierre Desir"],
    original: "Fumble lost (recovered by Jabaal Sheard)",
    corrected: "Own fumble recovery (no fumble lost, turnover on downs)",
    change: "Elliott: fumble lost removed. Colts D/ST: fumble recovery removed. +2 fantasy points for Elliott.",
    when: "December 20, 2018 (4 days after game)",
    why: "Referee did not signal fumble on field. NFL rule requires video review for turnover by fumble. No clear visual evidence of recovery. Correction initiated after fantasy player contacted Elias Sports Bureau.",
    changedOutcome: false,
    sources: [
      { name: "Action Network", url: "https://www.actionnetwork.com/nfl/ezekiel-elliott-stat-correction-fantasy-football-fumble" },
      { name: "Fantasy Index", url: "https://fantasyindex.com/2018/12/20/around-the-nfl/ezekiel-elliott-turnover-by-fumble-overturned-by-nfl" },
      { name: "USA Today", url: "https://ftw.usatoday.com/story/sports/sports-betting/2019/12/27/fantasy-football-ravens-stat-correction-championships-bad-beat/81570051007/" }
    ]
  },
  {
    id: "CHI-JAX-2024-W06-WILLIAMS",
    category: "play_classification",
    title: "Caleb Williams Aborted Snap (10-Week Delay)",
    date: "October 13, 2024",
    teams: "CHI @ JAX (Bears won)",
    week: "Week 6, 2024 (corrected Week 16)",
    players: ["Caleb Williams"],
    original: "Rush for -5 yards",
    corrected: "Aborted play: fumble, own fumble recovery, rush for 0 yards",
    change: "Rushing yards: -5 → 0. Added fumble and fumble recovery stats. +0.5 fantasy points.",
    when: "December 17, 2025 — 10 WEEKS after the original game",
    why: "NFL determined shotgun snap went above QB's head, making it an aborted play per NFL Guide for Statisticians.",
    changedOutcome: false,
    note: "Demonstrates corrections can arrive months later. Fantasy platforms do not retroactively adjust.",
    sources: [
      { name: "NFL Network", url: "https://x.com/TomPelissero/status/2001410427968684212" },
      { name: "Yahoo Sports", url: "https://sports.yahoo.com/articles/bizarre-caleb-williams-stat-correction-044009234.html" }
    ]
  },
  {
    id: "BAL-2019-W16-RAVENS-SACK",
    category: "defensive_stat",
    title: "Ravens D/ST Sack Stat Correction",
    date: "December 2019",
    teams: "Baltimore Ravens",
    week: "Week 16, 2019",
    players: ["Ravens D/ST"],
    original: "Sack negated due to penalty",
    corrected: "Sack credited to Ravens D/ST",
    change: "+1 sack for Ravens D/ST (+1 fantasy point). Multiple championship games reversed.",
    when: "Thursday after game (Christmas week 2019)",
    why: "Post-game review determined sack should be credited despite penalty.",
    changedOutcome: false,
    sources: [
      { name: "USA Today", url: "https://ftw.usatoday.com/story/sports/sports-betting/2019/12/27/fantasy-football-ravens-stat-correction-championships-bad-beat/81570051007/" }
    ]
  },
  {
    id: "CAR-ATL-2020-W05-BRIDGEWATER",
    category: "pass_stat",
    title: "Bridgewater Completion Percentage",
    date: "October 11, 2020",
    teams: "CAR @ ATL",
    week: "Week 5, 2020",
    players: ["Teddy Bridgewater"],
    original: "Incompletion counted (73.0% completion rate)",
    corrected: "Incompletion removed — play nullified by penalty (73.4%)",
    change: "Bridgewater became NFL completion percentage leader, surpassing Derek Carr (73.1%).",
    when: "Thursday after game",
    why: "Elias Sports Bureau determined play should have been nullified by penalty.",
    changedOutcome: false,
    sources: [
      { name: "CBS Sports", url: "https://www.cbssports.com/nfl/news/a-stat-correction-doesnt-just-impact-fantasy-football-as-teddy-bridgewater-is-now-league-leader-in-key-stat/" }
    ]
  },
  {
    id: "DET-MIN-2025-W17-LIONS-SACK",
    category: "defensive_stat",
    title: "Lions D/ST Sack Count Dispute",
    date: "December 2025",
    teams: "DET @ MIN",
    week: "Week 17, 2025",
    players: ["Detroit Lions D/ST"],
    original: "7 sacks credited to Lions defense",
    corrected: "6 sacks (one play ruled not a sack)",
    change: "-1 sack for Lions D/ST. Significant cross-platform confusion.",
    when: "~1 week after game",
    why: "Post-game review determined 4th quarter play was not a sack.",
    changedOutcome: false,
    note: "NFL Gamebook showed 7 sacks while NFL.com stats page showed 6. ESPN, Sleeper showed different values at different times.",
    sources: [
      { name: "Reddit r/fantasyfootball", url: "https://www.reddit.com/r/fantasyfootball/comments/1q22n68/stat_correction_lions_dst_week_17_stat_correction/" }
    ]
  },
  {
    id: "NE-2020-W07-BLOCKED-KICK",
    category: "special_teams_stat",
    title: "Patriots D/ST Blocked Kick",
    date: "October 2020",
    teams: "New England Patriots",
    week: "Week 7, 2020",
    players: ["New England D/ST"],
    original: "Blocked extra point not credited",
    corrected: "Blocked extra point credited to NE D/ST",
    change: "+1 blocked kick (+2 fantasy points). Multiple matchup outcomes reversed.",
    when: "Thursday after game",
    why: "Post-game review confirmed blocked kick should be credited.",
    changedOutcome: false,
    sources: [
      { name: "Reddit r/fantasyfootball", url: "https://www.reddit.com/r/fantasyfootball/comments/jk9r3b/yes_youre_waking_up_to_some_stat_corrections/" }
    ]
  },
  {
    id: "DEN-2008-W01-CUTLER",
    category: "passing_yardage",
    title: "Jay Cutler 300-Yard Threshold",
    date: "September 2008",
    teams: "Denver Broncos",
    week: "Week 1, 2008",
    players: ["Jay Cutler"],
    original: "299 passing yards",
    corrected: "300 passing yards",
    change: "+1 passing yard. Crossed 300-yard fantasy bonus threshold.",
    when: "Thursday after game",
    why: "Elias Sports Bureau review of game tape.",
    changedOutcome: false,
    sources: [
      { name: "MyFantasyLeague", url: "https://myfantasyleague.wordpress.com/2008/09/11/official-nfl-stat-corrections/" }
    ]
  },
  {
    id: "NO-DET-2026-W02-SAINTS-TD",
    category: "scoring_change",
    title: "Saints Strip-Sack TD Overturned",
    date: "September 14, 2026",
    teams: "NO @ DET",
    week: "Week 2, 2026",
    players: ["Jared Goff", "Chase Young", "Jonas Sanker"],
    original: "Strip-sack, fumble recovery touchdown by Saints (Sanker scoop-and-score)",
    corrected: "Incomplete forward pass (Goff throwing motion began before contact)",
    change: "7 points removed from Saints potential score. Lions won 31-30 in OT.",
    when: "During game via replay review",
    why: "NFL VP of Instant Replay: Goff had begun throwing motion before contact, making backward trajectory still a forward pass.",
    changedOutcome: true,
    sources: [
      { name: "NBC Sports", url: "https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/saints-lions-included-controversial-reversal-of-strip-sack-score" },
      { name: "ESPN", url: "https://www.espn.com/nfl/story/_/id/49934999/saints-irked-overturned-defensive-td-ot-loss-lions" },
      { name: "Yahoo Sports", url: "https://sports.yahoo.com/articles/saints-had-scoop-score-td-191222727.html" }
    ]
  },
  {
    id: "MIN-DET-2016-TGIVING-FELLS",
    category: "scoring_change",
    title: "Darren Fells TD Confirmed Then Overturned",
    date: "November 23, 2016",
    teams: "MIN @ DET",
    week: "Week 12, 2016 (Thanksgiving)",
    players: ["Darren Fells"],
    original: "Touchdown catch confirmed by replay official",
    corrected: "Touchdown overturned to incomplete pass (did not maintain control)",
    change: "TD → FG: Lions settled for 3 points instead of 7 on the drive. Lions won 16-13.",
    when: "During game, after replay official initially confirmed then reversed",
    why: "Replay official initially confirmed TD, then realized Fells did not maintain control. Corrected before extra point snap.",
    changedOutcome: true,
    note: "If Lions had snapped the extra point quickly, the play could not have been reviewed under NFL rules.",
    sources: [
      { name: "NBC Sports", url: "https://www.nbcsports.com/nfl/profootballtalk/rumor-mill/news/replay-at-first-confirmed-lions-touchdown-that-was-later-overturned" }
    ]
  }
];

// Render entries
function renderEntries(filter = 'all') {
  const container = document.getElementById('entries-container');
  container.innerHTML = '';

  const filtered = filter === 'all'
    ? entries
    : filter === 'outcome_changed'
    ? entries.filter(e => e.changedOutcome)
    : entries.filter(e => e.category.includes(filter));

  filtered.forEach(entry => {
    const card = document.createElement('div');
    card.className = 'entry-card';
    card.innerHTML = `
      <div class="entry-header">
        <div class="entry-title">${entry.title}</div>
        <div class="entry-meta">
          <span class="badge ${entry.changedOutcome ? 'badge-outcome-yes' : 'badge-outcome-no'}">
            ${entry.changedOutcome ? '✅ Changed Outcome' : '⚠️ Stat Change Only'}
          </span>
          <span class="badge badge-category">${entry.category.replace(/_/g, ' ')}</span>
        </div>
      </div>

      <div class="entry-details">
        <div class="detail-item">
          <div class="detail-label">Date</div>
          <div class="detail-value">${entry.date}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">Game</div>
          <div class="detail-value">${entry.teams} — ${entry.week}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">Player(s)</div>
          <div class="detail-value">${entry.players.join(', ')}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">When Corrected</div>
          <div class="detail-value">${entry.when}</div>
        </div>
      </div>

      <div class="entry-details">
        <div class="detail-item">
          <div class="detail-label">Original Ruling</div>
          <div class="detail-value">${entry.original}</div>
        </div>
        <div class="detail-item">
          <div class="detail-label">Corrected Ruling</div>
          <div class="detail-value">${entry.corrected}</div>
        </div>
      </div>

      <div class="change-box">
        <strong>Impact:</strong> ${entry.change}
        ${entry.note ? '<br><em>Note: ' + entry.note + '</em>' : ''}
      </div>

      <div class="detail-item">
        <div class="detail-label">Why It Changed</div>
        <div class="detail-value">${entry.why}</div>
      </div>

      <div class="sources-list">
        ${entry.sources.map(s => `<a href="${s.url}" target="_blank" class="source-link">${s.name} ↗</a>`).join('')}
      </div>
    `;
    container.appendChild(card);
  });
}

// Filter functionality
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderEntries(btn.dataset.filter);
  });
});

// Smooth scroll for nav links
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    const target = document.querySelector(link.getAttribute('href'));
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    link.classList.add('active');
  });
});

// Update active nav on scroll
window.addEventListener('scroll', () => {
  const sections = document.querySelectorAll('section');
  let current = '';
  sections.forEach(section => {
    const sectionTop = section.offsetTop;
    if (window.pageYOffset >= sectionTop - 100) {
      current = section.getAttribute('id');
    }
  });
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.remove('active');
    if (link.getAttribute('href') === '#' + current) {
      link.classList.add('active');
    }
  });
});

// Initial render
renderEntries();
