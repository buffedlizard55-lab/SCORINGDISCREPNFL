const REPOSITORY = 'buffedlizard55-lab/SCORINGDISCREPNFL';
const LABEL = 'official-stat-correction';
const API = 'https://api.github.com';

const caseList = document.querySelector('#case-list');
const searchInput = document.querySelector('#case-search');
const seasonFilter = document.querySelector('#season-filter');
const gradeFilter = document.querySelector('#grade-filter');
const resultCount = document.querySelector('#case-results');
let historicalCases = [];

function text(tag, value, className) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  node.textContent = value == null ? '' : String(value);
  return node;
}

function safeLink(url, label, className = 'source-link') {
  const link = document.createElement('a');
  link.className = className;
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== 'https:') throw new Error('Only HTTPS sources are allowed');
    link.href = parsed.href;
  } catch {
    link.removeAttribute('href');
    link.setAttribute('aria-disabled', 'true');
  }
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  link.append(text('span', '↗'));
  link.append(text('span', label));
  return link;
}

function formatNumber(value) {
  if (typeof value === 'number' && Number.isInteger(value)) return String(value);
  return value == null ? 'not recorded' : String(value);
}

function signed(value) {
  if (typeof value !== 'number') return 'not recorded';
  return `${value > 0 ? '+' : ''}${formatNumber(value)}`;
}

function countChanges(caseRecord) {
  return (caseRecord.players || []).reduce((total, player) => total + (player.changes || []).length, 0);
}

function renderTable(caseRecord) {
  const table = document.createElement('table');
  table.className = 'case-stat-table';
  const caption = text('caption', 'Recorded player-stat changes');
  table.append(caption);
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  ['Player', 'Statistic', 'Original', 'Corrected', 'Δ'].forEach(label => headRow.append(text('th', label)));
  thead.append(headRow);
  table.append(thead);
  const tbody = document.createElement('tbody');
  (caseRecord.players || []).forEach(player => {
    (player.changes || []).forEach(change => {
      const row = document.createElement('tr');
      row.append(text('td', `${player.name} (${player.position || 'position n/a'})`));
      row.append(text('td', change.stat));
      row.append(text('td', formatNumber(change.initial)));
      row.append(text('td', formatNumber(change.corrected)));
      row.append(text('td', signed(change.delta)));
      tbody.append(row);
    });
  });
  table.append(tbody);
  return table;
}

function renderList(items, emptyMessage) {
  const list = document.createElement('ul');
  if (!Array.isArray(items) || !items.length) {
    list.append(text('li', emptyMessage));
    return list;
  }
  items.forEach(item => list.append(text('li', item)));
  return list;
}

function renderCase(caseRecord) {
  const details = document.createElement('details');
  details.className = 'case-card';

  const summary = document.createElement('summary');
  summary.className = 'case-summary';
  const left = document.createElement('div');
  left.className = 'case-summary-left';
  left.append(text('span', '+', 'case-toggle'));
  const titleBlock = document.createElement('div');
  titleBlock.className = 'case-title-block';
  const game = caseRecord.game || {};
  const title = (caseRecord.players || []).map(player => player.name).join(' · ') || 'Unnamed player';
  titleBlock.append(text('h3', `${title} — ${game.away_team || '?'} at ${game.home_team || '?'}`));
  const meta = document.createElement('div');
  meta.className = 'case-meta';
  meta.append(text('span', `${game.season || 'Season n/a'} · Week ${game.week ?? 'n/a'}`));
  meta.append(text('span', game.date || 'Game date not recorded'));
  meta.append(text('span', game.final_score || 'Final score not recorded'));
  titleBlock.append(meta);
  left.append(titleBlock);
  summary.append(left);

  const right = document.createElement('div');
  right.className = 'case-summary-right';
  const grade = text('span', caseRecord.evidence_grade || '?', `grade grade-${String(caseRecord.evidence_grade || 'c').toLowerCase()}`);
  grade.setAttribute('aria-label', `Evidence grade ${caseRecord.evidence_grade || 'unknown'}`);
  right.append(text('span', `${countChanges(caseRecord)} stat change${countChanges(caseRecord) === 1 ? '' : 's'}`, 'case-change-count'));
  right.append(grade);
  summary.append(right);
  details.append(summary);

  const content = document.createElement('div');
  content.className = 'case-content';
  content.append(renderTable(caseRecord));

  const overview = document.createElement('div');
  overview.className = 'case-overview';
  const timing = document.createElement('div');
  timing.append(text('h4', 'Correction timing & reason'));
  const timingText = caseRecord.reported_on
    ? `${caseRecord.reported_on} · ${caseRecord.reported_on_basis || 'Date basis not recorded'}${Number.isInteger(caseRecord.elapsed_days_to_report) ? ` · ${caseRecord.elapsed_days_to_report} days after the game to the cited report` : ''}`
    : (caseRecord.reported_on_basis || 'Correction timestamp not found in reviewed sources.');
  timing.append(text('p', timingText));
  timing.append(text('p', caseRecord.reason || 'Reason not established.'));
  const evidence = document.createElement('div');
  evidence.append(text('h4', 'Evidence assessment'));
  evidence.append(text('p', caseRecord.evidence_grade_note || 'No grade note supplied.'));
  overview.append(timing, evidence);
  content.append(overview);

  const tableLink = document.createElement('p');
  tableLink.className = 'case-game-link';
  tableLink.append(safeLink(game.url || '', `Open official NFL game center${game.final_score ? ` · ${game.final_score}` : ''}`, 'text-link'));
  content.append(tableLink);

  const bottom = document.createElement('div');
  bottom.className = 'case-bottom-grid';
  const potential = document.createElement('div');
  potential.append(text('h4', 'Possible impact only'));
  potential.append(renderList(caseRecord.possible_market_impact, 'No possible market impact recorded.'));
  const actual = document.createElement('div');
  actual.append(text('h4', 'What is actually verified'));
  const verifiedFacts = [
    `Sportsbook line: ${caseRecord.actual_market_impact?.sportsbook_line_verified ? 'verified' : 'not verified'}`,
    `Sportsbook settlement: ${caseRecord.actual_market_impact?.sportsbook_settlement_change || 'not verified'}`,
    `Score / winner: ${caseRecord.score_effect?.official_score_changed ? 'score change recorded' : 'no score change recorded'}; ${caseRecord.score_effect?.winner_changed ? 'winner change recorded' : 'no winner change recorded'}`,
    caseRecord.actual_market_impact?.fantasy_or_other_platform_note || 'No fantasy/platform outcome note recorded.'
  ];
  actual.append(renderList(verifiedFacts));
  bottom.append(potential, actual);
  content.append(bottom);

  const sourceHeading = text('h4', 'Sources for manual review');
  sourceHeading.style.marginTop = '20px';
  content.append(sourceHeading);
  const sourceList = document.createElement('div');
  sourceList.className = 'source-list';
  (caseRecord.sources || []).forEach(source => {
    const link = safeLink(source.url, source.label);
    link.title = [source.supports, source.availability_note, source.source_type].filter(Boolean).join(' · ');
    sourceList.append(link);
  });
  content.append(sourceList);
  details.append(content);
  return details;
}

function visibleCases() {
  const query = (searchInput?.value || '').trim().toLowerCase();
  const selectedSeason = seasonFilter?.value || 'all';
  const selectedGrade = gradeFilter?.value || 'all';
  return historicalCases.filter(caseRecord => {
    if (selectedSeason !== 'all' && String(caseRecord.game?.season) !== selectedSeason) return false;
    if (selectedGrade !== 'all' && caseRecord.evidence_grade !== selectedGrade) return false;
    if (!query) return true;
    const searchable = [
      caseRecord.id,
      caseRecord.game?.season,
      caseRecord.game?.week,
      caseRecord.game?.date,
      caseRecord.game?.away_team,
      caseRecord.game?.home_team,
      caseRecord.game?.final_score,
      caseRecord.reason,
      caseRecord.evidence_grade_note,
      ...(caseRecord.players || []).flatMap(player => [player.name, player.position, ...(player.changes || []).flatMap(change => [change.stat, change.initial, change.corrected])]),
      ...(caseRecord.possible_market_impact || []),
      ...(caseRecord.sources || []).flatMap(source => [source.label, source.supports, source.availability_note])
    ].join(' ').toLowerCase();
    return searchable.includes(query);
  });
}

function updateSummary() {
  const changeCount = historicalCases.reduce((total, item) => total + countChanges(item), 0);
  const scoreCount = historicalCases.filter(item => item.score_effect?.official_score_changed || item.score_effect?.winner_changed || item.score_effect?.point_total_or_margin_changed).length;
  const bookCount = historicalCases.filter(item => item.actual_market_impact?.sportsbook_line_verified && item.actual_market_impact?.sportsbook_settlement_change === 'verified').length;
  document.querySelector('#case-count').textContent = String(historicalCases.length);
  document.querySelector('#change-count').textContent = String(changeCount);
  document.querySelector('#score-count').textContent = String(scoreCount);
  document.querySelector('#book-count').textContent = String(bookCount);
}

function renderCases() {
  if (!caseList) return;
  const results = visibleCases();
  caseList.replaceChildren();
  resultCount.textContent = `Showing ${results.length} of ${historicalCases.length} curated game cases. This dataset is not a complete census.`;
  if (!results.length) {
    caseList.append(text('p', 'No cases match those filters. Try a different season, grade, or search term.', 'no-results'));
    return;
  }
  results.forEach(item => caseList.append(renderCase(item)));
}

function populateSeasonFilter() {
  const seasons = [...new Set(historicalCases.map(item => item.game?.season).filter(Boolean))].sort((a, b) => b - a);
  seasons.forEach(season => {
    const option = document.createElement('option');
    option.value = String(season);
    option.textContent = String(season);
    seasonFilter.append(option);
  });
}

function updateGradeFilterLabels() {
  if (!gradeFilter) return;
  const names = { A: 'direct record', B: 'corroborated sources', C: 'incomplete / provisional' };
  [...gradeFilter.options].forEach(option => {
    if (option.value === 'all') return;
    const count = historicalCases.filter(item => item.evidence_grade === option.value).length;
    option.textContent = `${option.value} · ${names[option.value] || 'unknown'} (${count})`;
  });
}

async function loadHistoricalCases() {
  try {
    const response = await fetch('./data/historical-cases.json', { cache: 'no-cache' });
    if (!response.ok) throw new Error(`Dataset request returned HTTP ${response.status}`);
    const data = await response.json();
    if (!Array.isArray(data.cases)) throw new Error('Historical case file is missing its cases list.');
    historicalCases = [...data.cases].sort((a, b) => String(b.game?.date || '').localeCompare(String(a.game?.date || '')));
    populateSeasonFilter();
    updateGradeFilterLabels();
    updateSummary();
    renderCases();
  } catch (error) {
    resultCount.textContent = 'Historical dataset could not be loaded.';
    caseList.replaceChildren(text('p', `${error.message} Try opening the site from its GitHub Pages URL or a local web server.`, 'no-results'));
  }
}

function compactDate(value) {
  if (!value) return 'time not provided';
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' }) + ' UTC';
}

async function loadAlerts() {
  const status = document.querySelector('#feed-status');
  const list = document.querySelector('#live-alert-list');
  const count = document.querySelector('#feed-count');
  const url = `${API}/repos/${REPOSITORY}/issues?state=all&labels=${encodeURIComponent(LABEL)}&per_page=30`;
  try {
    const response = await fetch(url, { headers: { Accept: 'application/vnd.github+json' } });
    if (!response.ok) throw new Error(response.status === 403 ? 'GitHub API rate limit or permission issue.' : `GitHub API returned HTTP ${response.status}.`);
    const issues = await response.json();
    if (!Array.isArray(issues)) throw new Error('Unexpected response from GitHub Issues API.');
    const alerts = issues.filter(issue => !issue.pull_request && (issue.body || '').includes('<!-- nfl-correction:'));
    count.textContent = String(alerts.length);
    list.replaceChildren();
    status.textContent = alerts.length
      ? `${alerts.length} candidate alert${alerts.length === 1 ? '' : 's'} currently available from the GitHub issue feed.`
      : 'No correction issues have been published yet. Check the monitor-run status above; an empty list is not proof that no corrections occurred.';
    alerts.forEach(issue => {
      const card = document.createElement('article');
      card.className = 'live-alert';
      const top = document.createElement('div');
      top.className = 'live-alert-top';
      const heading = document.createElement('h4');
      heading.append(safeLink(issue.html_url, issue.title, ''));
      top.append(heading);
      top.append(text('span', issue.state === 'closed' ? 'Reviewed / closed' : 'Open candidate', `issue-status${issue.state === 'closed' ? ' closed' : ''}`));
      card.append(top);
      card.append(text('p', `Alert #${issue.number} · opened ${compactDate(issue.created_at)}`));
      const lines = (issue.body || '').split('\n').map(line => line.replace(/^#+\s*/, '').trim()).filter(line => line && !line.startsWith('<!--') && !line.startsWith('['));
      const preview = lines.find(line => /Reported change|Season \/ week|Player \/ team|Stat:/i.test(line)) || 'Automated candidate; review the source and verification checklist in the issue.';
      card.append(text('p', preview.replaceAll('**', ''), 'issue-body-preview'));
      list.append(card);
    });
  } catch (error) {
    count.textContent = '—';
    status.textContent = `Live alert feed could not be loaded: ${error.message} The linked GitHub Issues page remains available.`;
    list.replaceChildren();
  }
}

async function loadReportedEffects() {
  const list = document.querySelector('#reported-effects');
  if (!list) return;
  try {
    const response = await fetch('./data/reported-downstream-effects.json', { cache: 'no-cache' });
    if (!response.ok) throw new Error(`Reported-effects request returned HTTP ${response.status}`);
    const data = await response.json();
    if (!Array.isArray(data.effects)) throw new Error('Reported-effects file is missing its effects list.');
    list.replaceChildren();
    data.effects.forEach(effect => {
      const card = document.createElement('article');
      card.className = 'reported-effect-card';
      const meta = document.createElement('div');
      meta.append(text('h4', effect.game || 'Game details not recorded'));
      meta.append(text('p', `Reported ${effect.reported_on || 'date not recorded'}`, 'effect-date'));
      const details = document.createElement('div');
      details.append(text('p', effect.reported_effect || 'No outcome details recorded.', 'effect-description'));
      details.append(text('p', effect.verification_limit || effect.sportsbook_impact || 'Secondary report; not independently audited.', 'effect-limit'));
      card.append(meta, details, safeLink(effect.source?.url || '', effect.source?.label || 'Open source'));
      list.append(card);
    });
  } catch (error) {
    list.replaceChildren(text('p', `Reported fantasy-effect notes could not be loaded: ${error.message}`, 'no-results'));
  }
}

async function loadMonitorStatus() {
  const status = document.querySelector('#monitor-status');
  const runLink = document.querySelector('#monitor-run-link');
  const workflow = 'stat-correction-watch.yml';
  const endpoint = `${API}/repos/${REPOSITORY}/actions/workflows/${workflow}/runs?branch=main&per_page=1`;
  try {
    const response = await fetch(endpoint, { headers: { Accept: 'application/vnd.github+json' } });
    if (!response.ok) throw new Error(response.status === 403 ? 'GitHub API rate limit or permission issue.' : `GitHub API returned HTTP ${response.status}.`);
    const payload = await response.json();
    const run = payload.workflow_runs?.[0];
    if (!run) {
      status.textContent = 'No run is visible on the default branch yet. The scheduled feed is not confirmed active.';
      return;
    }
    const isSuccess = run.conclusion === 'success';
    const label = run.status === 'in_progress' || run.status === 'queued'
      ? `Last monitor run is ${run.status}.`
      : `Last monitor run ${isSuccess ? 'succeeded' : `ended ${run.conclusion || run.status}`}: ${compactDate(run.updated_at)}.`;
    status.textContent = `${label} A successful run only verifies that the configured source could be parsed; it does not verify market outcomes.`;
    runLink.append(safeLink(run.html_url, 'View latest GitHub Actions run', 'text-link'));
  } catch (error) {
    status.textContent = `Monitor run status could not be loaded: ${error.message} Use GitHub Actions to review the workflow directly.`;
  }
}

searchInput?.addEventListener('input', renderCases);
seasonFilter?.addEventListener('change', renderCases);
gradeFilter?.addEventListener('change', renderCases);
document.querySelector('#clear-filters')?.addEventListener('click', () => {
  searchInput.value = '';
  seasonFilter.value = 'all';
  gradeFilter.value = 'all';
  renderCases();
  searchInput.focus();
});

loadHistoricalCases();
loadReportedEffects();
loadAlerts();
loadMonitorStatus();
