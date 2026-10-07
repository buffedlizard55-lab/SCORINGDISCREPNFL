/* SCORINGDISCREPNFL — site logic.
   Everything rendered is read from the shipped JSON artefacts. No numbers are
   hard-coded in this file, so the page can never drift from the data. */

const SEV_CLASS = { HIGH: 'sev-3', MEDIUM: 'sev-2', LOW: 'sev-1', INFO: 'sev-0' };
const SEV_LABEL = { HIGH: 'HIGH', MEDIUM: 'MEDIUM', LOW: 'LOW', INFO: 'INFO' };

const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const fmt = (v) => (v === null || v === undefined || v === '' ? '—' : v);
const num = (v) => (v === null || v === undefined ? '—' : Number(v).toLocaleString());

async function loadJSON(path) {
  const r = await fetch(path, { cache: 'no-store' });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json();
}

/* This code is published from BOTH the repository root and docs/ (GitHub Pages
   is configured to serve the repo root, while docs/ remains the canonical copy).
   The same three files therefore sit at two different relative paths:

     root : data/discrepancies.json, data/evidence/score_integrity_study.json, data/market_sensitivity_*.json
     docs : data/discrepancies.json, data/score_integrity_study.json,        data/market_sensitivity_*.json

   Rather than rewrite paths during the copy — which silently breaks when
   someone edits one copy — each loader takes candidate paths and uses the
   first one that resolves. One app.js, correct in both locations. */
async function loadFirst(candidates) {
  let lastErr;
  for (const p of candidates) {
    try {
      return await loadJSON(p);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr;
}

/* ------------------------------------------------------------- live feed */
/* One cell, two facts: did the whole upstream file change, and which commit did
   the newer snapshot come from. Unknown is rendered as unknown. */
function srcCell(r) {
  const changed = r.source_file_changed;
  const pill = changed === true
    ? '<span class="pill sev-1">changed</span>'
    : changed === false
      ? '<span class="pill sev-2">unchanged</span>'
      : '<span class="pill sev-0">unknown</span>';
  const commit = (r.new_source || {}).upstream_commit_sha;
  const when = (r.new_source || {}).upstream_commit_date;
  const link = commit
    ? ` <a class="src" href="https://github.com/nflverse/nfldata/commit/${esc(commit)}">${esc(String(commit).slice(0, 10))}</a>`
    : '';
  const backfilled = (r.new_source || {}).backfilled_from_manifest ? ' <span class="src">(hash read from the snapshot manifest)</span>' : '';
  return `${pill}${link}${when ? `<br><span class="src">upstream ${esc(String(when))}</span>` : ''}${backfilled}`;
}

/* ------------------------------------------------------- monitor health */
const HEALTH_CLASS = { ok: 'sev-1', warn: 'sev-2', fail: 'sev-3', unknown: 'sev-0' };
const HEALTH_WORD = { ok: 'PASS', warn: 'WARN', fail: 'FAIL', unknown: 'UNKNOWN' };

function renderHealth(h) {
  const box = document.getElementById('health-headline');
  const tbody = document.querySelector('#tbl-health tbody');
  const flags = document.getElementById('health-irregularities');
  const foot = document.getElementById('health-footnote');
  if (!box || !tbody) return;

  if (!h) {
    box.className = 'callout warn';
    box.innerHTML = '<p><strong>Monitor health is unknown.</strong> No health artefact was '
      + 'published with this page. Unknown is not clean — check the '
      + '<a href="https://github.com/buffedlizard55-lab/SCORINGDISCREPNFL/actions">Actions history</a>.</p>';
    tbody.innerHTML = '<tr><td class="empty" colspan="3">No health report published.</td></tr>';
    return;
  }

  box.className = `callout ${h.status === 'ok' ? 'ok' : h.status === 'warn' ? 'warn' : 'bad'}`;
  const wm = h.source_watermark || {};
  box.innerHTML = `<p><span class="pill ${HEALTH_CLASS[h.status] || 'sev-0'}" style="margin-right:8px;">`
    + `${esc((h.status || 'unknown').toUpperCase())}</span><strong>${esc(h.headline || '')}</strong></p>`
    + `<p class="footnote">Assessed ${esc(h.generated_at || '—')} · last completed comparison `
    + `<strong>${esc(h.last_successful_comparison_at || 'none')}</strong> `
    + `(${fmt(h.hours_since_last_comparison)} h ago; stale after ${fmt(h.stale_after_hours)} h)`
    + (wm.upstream_commit_sha
      ? ` · newest snapshot pinned to upstream commit <a href="${esc(wm.upstream_commit_url || '#')}">${esc(String(wm.upstream_commit_sha).slice(0, 10))}</a> at ${esc(wm.upstream_commit_date || '—')}`
      : ' · upstream commit watermark not recorded')
    + `</p>`;

  tbody.innerHTML = (h.checks || []).map((c) => `<tr>
      <td><strong>${esc(c.check)}</strong></td>
      <td><span class="pill ${HEALTH_CLASS[c.status] || 'sev-0'}">${esc(HEALTH_WORD[c.status] || c.status)}</span></td>
      <td>${esc(c.detail)}</td>
    </tr>`).join('') || '<tr><td class="empty" colspan="3">No checks reported.</td></tr>';

  const irr = h.irregularities || [];
  flags.innerHTML = irr.length
    ? `<div class="callout warn"><p><strong>Irregularities flagged for review</strong></p><ul>`
      + irr.map((i) => `<li>${esc(i)}</li>`).join('') + `</ul></div>`
    : '';
  foot.textContent = `Next action: ${h.next_action || '—'}`;
}

/* -------------------------------------------------------- source churn */
function renderChurn(study) {
  const cards = document.getElementById('churn-cards');
  const callout = document.getElementById('churn-callout');
  const fields = document.querySelector('#tbl-churn-fields tbody');
  const revs = document.querySelector('#tbl-churn-revisions tbody');
  if (!cards || !fields) return;

  if (!study) {
    callout.className = 'callout warn';
    callout.innerHTML = '<p><strong>No churn study published.</strong> Run '
      + '<code>python3 pipeline/run.py churn</code> to regenerate it.</p>';
    fields.innerHTML = '<tr><td class="empty" colspan="3">No study available.</td></tr>';
    revs.innerHTML = '<tr><td class="empty" colspan="5">No study available.</td></tr>';
    return;
  }

  const t = study.totals || {}, sp = study.sampling || {};
  cards.innerHTML = `
    <div class="card"><div class="num accent">${num(sp.vintages_downloaded)}</div>
      <div class="lbl">genuine upstream vintages</div>
      <div class="sub">${num(sp.intervals_compared)} consecutive pairs compared</div></div>
    <div class="card"><div class="num">${fmt(sp.window_hours)}</div>
      <div class="lbl">hours of upstream history</div>
      <div class="sub">${esc(String(sp.window_start || '').slice(0, 10))} → ${esc(String(sp.window_end || '').slice(0, 10))}</div></div>
    <div class="card"><div class="num warn">${num(t.intervals_where_full_file_bytes_changed)}</div>
      <div class="lbl">intervals where the source bytes changed</div>
      <div class="sub">the mirror is actively rewritten</div></div>
    <div class="card"><div class="num ${Number(t.frozen_field_changes_on_final_games) === 0 ? 'ok' : 'warn'}">${num(t.frozen_field_changes_on_final_games)}</div>
      <div class="lbl">frozen scoreboard changes on finished games</div>
      <div class="sub">score, margin, total, overtime</div></div>
    <div class="card"><div class="num">${num(t.non_frozen_field_changes_on_final_games)}</div>
      <div class="lbl">other changes on finished games</div>
      <div class="sub">across ${num(t.distinct_final_games_touched)} games — the noise a naive detector would have sent</div></div>`;

  callout.className = 'callout ok';
  callout.innerHTML = `<p>${esc(study.interpretation || '')}</p>
    <p class="footnote">${num(t.final_records_compared)} already-final record comparisons. `
    + `Every vintage is re-downloadable from its recorded codeload URL and identified by SHA-256, `
    + `so this table can be checked without trusting this page.</p>`;

  const frozen = new Set(['away_score', 'home_score', 'result', 'total', 'overtime']);
  const rows = Object.entries(t.non_frozen_fields_observed || {});
  fields.innerHTML = (rows.length ? rows : [['(none observed)', 0]]).map(([k, n]) => `<tr>
      <td class="mono">${esc(k)}</td>
      <td class="num">${num(n)}</td>
      <td>${frozen.has(k) ? '<span class="pill sev-3">yes — would alert</span>' : '<span class="pill sev-0">no — excluded by design</span>'}</td>
    </tr>`).join('');

  const revList = t.revisions_of_already_published_values || [];
  revs.innerHTML = (revList.length ? revList.slice(0, 40) : []).map((r) => `<tr>
      <td class="mono">${esc(r.observed_at)}</td>
      <td class="mono">${esc(r.game_id)}</td>
      <td class="mono">${esc(r.field)}</td>
      <td>${esc(r.old)}</td>
      <td>${esc(r.new)}</td>
    </tr>`).join('')
    || '<tr><td class="empty" colspan="5">No already-published value was revised in this window.</td></tr>';
  if (revList.length > 40) {
    revs.innerHTML += `<tr><td class="empty" colspan="5">…and ${revList.length - 40} more in `
      + `<code>data/evidence/upstream_churn_study.json</code>.</td></tr>`;
  }
}
/* Renders data/alerts/feed.json. Loaded separately and non-fatally: the feed is
   operational state, and its absence must never blank the historical database. */
function renderFeed(feed) {
  const cards = document.getElementById('feed-cards');
  const note = document.getElementById('feed-note');
  const tbody = document.querySelector('#tbl-feed tbody');
  if (!cards || !tbody) return;

  const latest = feed.latest;
  const s = feed.summary || {};

  if (!latest) {
    cards.innerHTML = '';
    note.innerHTML = '<p class="footnote">No detection run has been recorded yet.</p>';
    tbody.innerHTML = '<tr><td class="empty" colspan="6">No runs recorded.</td></tr>';
    return;
  }

  const clean = latest.status === 'clean';
  cards.innerHTML = `
    <div class="card">
      <div class="num ${clean ? 'ok' : 'warn'}">${num(latest.alerts_total)}</div>
      <div class="lbl">alerts in the latest run</div>
      <div class="sub">${clean ? 'no scoreboard change detected' : 'pending manual confirmation'}</div>
    </div>
    <div class="card">
      <div class="num accent">${num(s.runs_recorded)}</div>
      <div class="lbl">runs recorded</div>
      <div class="sub">${num(s.runs_clean)} clean · ${num(s.runs_with_alerts)} with alerts</div>
    </div>
    <div class="card">
      <div class="num">${num(latest.records_compared)}</div>
      <div class="lbl">already-final games compared</div>
      <div class="sub">in the latest run</div>
    </div>
    <div class="card">
      <div class="num">${num(s.total_alerts)}</div>
      <div class="lbl">alerts across all recorded runs</div>
      <div class="sub">since ${esc(s.first_run || '—')}</div>
    </div>`;

  /* "Identical inputs" describes the COMPARED PROJECTION, not the source. The
     manifests record the whole upstream file's SHA-256, so both facts are shown.
     An earlier revision of this page called an identical projection a "no-op
     rather than a fresh check", which the manifests disproved: the upstream file
     had changed in every one of those comparisons. */
  const srcMoved = latest.source_file_changed;
  const srcNote = srcMoved === true
    ? 'The upstream source file DID change between the two snapshots; the frozen-field projection did not.'
    : srcMoved === false
      ? 'The upstream source file did not change between the two snapshots either.'
      : 'The upstream source-file hash is not recorded for this run, so source movement is unknown.';
  const projNote = latest.identical_inputs
    ? 'The compared projection (finished games, five frozen scoreboard fields) was byte-identical.'
    : 'The compared projection changed.';
  note.innerHTML = `<p class="footnote">Last checked <strong>${esc(latest.checked_at)}</strong>.
    Status: <strong>${esc(latest.status)}</strong>. ${esc(projNote)} ${esc(srcNote)}</p>`;

  tbody.innerHTML = (feed.runs || []).slice(0, 25).map((r) => {
    const cls = r.status === 'clean' ? 'sev-0' : 'sev-3';
    const hash = (h) => (h ? esc(String(h).slice(0, 10)) + '…' : '—');
    return `<tr>
      <td>${esc(r.checked_at)}</td>
      <td><span class="pill ${cls}">${esc(r.status === 'clean' ? 'clean' : 'ALERTS')}</span></td>
      <td class="num">${num(r.alerts_total)}</td>
      <td class="num">${num(r.records_compared)}</td>
      <td>${srcCell(r)}</td>
      <td class="mono">${hash(r.old_sha256)} → ${hash(r.new_sha256)}</td>
    </tr>`;
  }).join('') || '<tr><td class="empty" colspan="6">No runs recorded.</td></tr>';
}

/* ------------------------------------------------------------------ cards */
function renderTopCards(db, study) {
  const c = db.meta.counts;
  document.getElementById('stat-records').textContent = num(c.total_records);
  const sampleEl = document.getElementById('stat-sample-rows');
  if (sampleEl) sampleEl.textContent = num(c.total_records);
  document.getElementById('stat-potential').textContent = num(c.potential_to_change_market);
  const studyComplete = study.status === 'complete';
  const observedFieldChanges = Number(study.totals.frozen_field_changes_vs_current || 0);
  document.getElementById('stat-snapshots').textContent = num(study.totals.game_snapshots_examined);
  document.getElementById('stat-snapshots-status').textContent = studyComplete
    ? `across ${num(study.totals.selected_baselines)} selected baselines; not unique games`
    : `from ${num(study.totals.baselines_fetched)} fetched baselines only; study incomplete`;
  document.getElementById('stat-revisions').textContent = studyComplete
    ? num(observedFieldChanges)
    : (observedFieldChanges > 0 ? `≥${num(observedFieldChanges)}` : 'Unknown');
  document.getElementById('stat-revisions').className = studyComplete ? 'num ok' : 'num warn';
  const datedRows = db.records
    .map((r) => Number(r.days_from_game_to_correction))
    .filter((v) => Number.isFinite(v));
  document.getElementById('stat-cadence').textContent = datedRows.length
    ? `${Math.min(...datedRows)}–${Math.max(...datedRows)}`
    : '—';
  document.getElementById('badge-records').textContent = `${c.total_records} archived rows`;
}

/* --------------------------------------------------------- integrity table */
function renderIntegrity(study) {
  const complete = study.status === 'complete';
  const tb = document.querySelector('#tbl-integrity tbody');
  tb.innerHTML = study.baselines.map((b) => {
    const failed = Boolean(b.error);
    const changed = Number(b.frozen_field_changes_vs_current || 0);
    const result = failed ? 'fetch failed' : changed > 0 ? 'mirror change observed' : 'no difference observed';
    const severity = failed ? 'sev-3' : changed > 0 ? 'sev-2' : 'sev-1';
    return `<tr>
      <td class="mono">${esc(b.baseline)}<br><span class="src">${esc(String(b.commit).slice(0, 10))}…</span></td>
      <td class="num">${num(b.final_at_baseline)}</td>
      <td class="num">${num(b.frozen_field_changes_vs_current)}</td>
      <td><span class="pill ${severity}" title="${esc(b.error || '')}">${result}</span></td>
    </tr>`;
  }).join('');

  const t = study.totals;
  const totalChanges = Number(t.frozen_field_changes_vs_current || 0);
  const overall = !complete
    ? 'incomplete — failed baselines are not counted as zero'
    : totalChanges > 0
      ? 'mirror change(s) observed; official status unconfirmed'
      : 'no difference observed in selected mirror comparisons';
  document.querySelector('#tbl-integrity tfoot').innerHTML = `<tr>
    <td><strong>${complete ? 'Complete study' : 'Partial study'}</strong></td>
    <td class="num"><strong>${num(t.game_snapshots_examined)}</strong></td>
    <td class="num"><strong>${complete ? num(totalChanges) : (totalChanges > 0 ? `≥${num(totalChanges)}` : 'Unknown')}</strong></td>
    <td><span class="pill ${complete && totalChanges === 0 ? 'sev-1' : 'sev-3'}">${overall}</span></td>
  </tr>`;

  const callout = document.getElementById('integrity-callout');
  if (!complete) {
    callout.className = 'callout warn';
    callout.textContent = 'The mirror comparison is incomplete. A failed baseline is not counted as zero; the available count cannot support a no-change conclusion.';
  } else if (totalChanges > 0) {
    callout.className = 'callout warn';
    callout.textContent = `${num(totalChanges)} frozen-field difference(s) were observed in selected mirror comparisons. This is a third-party mirror change, not confirmation of an official NFL correction.`;
  } else {
    callout.className = 'callout ok';
    callout.textContent = `No frozen-field differences were observed in the ${num(t.selected_baselines)} selected mirror comparisons (${num(t.game_snapshots_examined)} overlapping game-snapshot comparisons, not unique games). This does not establish that official scores never change.`;
  }

  document.getElementById('integrity-caveat').textContent = study.caveat;
  document.getElementById('integrity-caveat-full').textContent = study.caveat;
}

/* ---------------------------------------------------------- database table */
let DB = [];
let sortKey = 'severity_label';
let sortDir = 1;

function renderDB() {
  const q = document.getElementById('q').value.trim().toLowerCase();
  const sev = document.getElementById('f-sev').value;
  const season = document.getElementById('f-season').value;

  let rows = DB.filter((r) => {
    if (sev !== '' && String(r.severity) !== sev) return false;
    if (season !== '' && String(r.season) !== season) return false;
    if (!q) return true;
    return ['player', 'team', 'stat', 'game_id', 'position', 'category', 'opponent']
      .some((k) => String(r[k] ?? '').toLowerCase().includes(q));
  });

  const sevRank = { HIGH: 0, MEDIUM: 1, LOW: 2, INFO: 3 };
  rows.sort((a, b) => {
    let x = a[sortKey], y = b[sortKey];
    if (sortKey === 'severity_label') { x = sevRank[x]; y = sevRank[y]; }
    if (typeof x === 'number' && typeof y === 'number') return (x - y) * sortDir;
    return String(x).localeCompare(String(y)) * sortDir;
  });

  document.getElementById('count').textContent =
    `${rows.length} of ${DB.length} records`;

  const tb = document.querySelector('#tbl-db tbody');
  if (!rows.length) {
    tb.innerHTML = `<tr><td colspan="12" class="empty">No records match these filters.</td></tr>`;
    return;
  }

  tb.innerHTML = rows.map((r) => {
    const d = r.numeric_change;
    const delta = d > 0 ? `+${d}` : `${d}`;
    return `<tr>
      <td><span class="pill ${SEV_CLASS[r.severity_label] || 'sev-0'}" title="${esc(r.impact_reason)}">${esc(r.severity_label)}</span></td>
      <td>${esc(r.season)} <span class="src">W${esc(r.week)}</span></td>
      <td><strong>${esc(r.player)}</strong> <span class="src">${esc(r.position || '')}</span></td>
      <td title="${esc(r.team_source || '')}">${esc(fmt(r.team))}</td>
      <td>${(r.review_flags || []).length
        ? `<details><summary>⚠ ${num(r.review_flags.length)} flag(s)</summary><ul class="tight">${r.review_flags.map((flag) => `<li>${esc(flag)}</li>`).join('')}</ul></details>`
        : '—'}</td>
      <td class="mono">${esc(fmt(r.game_id))}<br><span class="src">${esc(fmt(r.opponent))}</span></td>
      <td>${esc(fmt(r.game_date))}</td>
      <td>${esc(r.stat)}</td>
      <td class="src" title="${esc(r.correction_reason || 'The archived official correction notice does not state a reason.')}">${esc(r.correction_reason || 'Not stated in source')}</td>
      <td class="chg"><span class="from">${esc(r.original_value)}</span> → <span class="to">${esc(r.corrected_value)}</span> <span class="delta">(${esc(delta)})</span></td>
      <td class="num">${esc(fmt(r.days_from_game_to_correction))}</td>
      <td class="src"><a href="${esc(r.source_url_archived)}" target="_blank" rel="noopener">archived official page ↗</a></td>
    </tr>`;
  }).join('');
}

function wireSorting() {
  document.querySelectorAll('#tbl-db th[data-k]').forEach((th) => {
    th.addEventListener('click', () => {
      const k = th.dataset.k;
      sortDir = (sortKey === k) ? -sortDir : 1;
      sortKey = k;
      renderDB();
    });
  });
}

/* -------------------------------------------------------------- case cards */
/* Selected by NATURAL KEY, not by record_id.
   BUG FIXED 2026-10-07: this list used to hold record_ids ('SC-0034', ...), but
   record_id is a positional ordinal assigned in build order. Adding 38 new rows
   silently re-pointed all six cards at different records — SC-0034 went from
   Michael Clark's 0 -> 36 receiving yards to an unrelated Roethlisberger row.
   A natural key cannot shift when rows are added. All prose is still generated
   from the matched record's own fields, so nothing here can assert something the
   database does not contain. */
/* The key MUST include the correction date: the official page sometimes lists the
   same correction twice on consecutive days (Dak Prescott, 2017 W16, Passing Yards
   182 -> 181 appears on both Dec 26 and Dec 27), so (season, week, player, stat)
   is not unique. */
const CASE_KEYS = [
  { season: 2017, week: 16, player: 'Michael Clark',      stat: 'Receiving Yards',   date: 'Dec 27' },
  { season: 2017, week: 16, player: 'Dak Prescott',       stat: 'Passing Yards',     date: 'Dec 26' },
  { season: 2017, week: 16, player: 'Dez Bryant',         stat: 'Receiving Yards',   date: 'Dec 26' },
  { season: 2015, week: 16, player: 'Ben Roethlisberger', stat: 'Receiving Yards',   date: 'Dec 30' },
  { season: 2018, week: 14, player: 'Lamar Jackson',      stat: 'Every Time Sacked', date: 'Dec 12' },
  { season: 2010, week: 1,  player: 'Green Bay Packers',  stat: 'Sacks',             date: 'Sep 15' },
];

const naturalKey = (r) =>
  `${r.season}|${r.week}|${r.player}|${r.stat}|${r.correction_date_text || ''}`;
const caseKey = (k) => `${k.season}|${k.week}|${k.player}|${k.stat}|${k.date}`;

function renderCases(db) {
  const byKey = Object.fromEntries(db.records.map((r) => [naturalKey(r), r]));
  const host = document.getElementById('cases');
  host.innerHTML = CASE_KEYS.map(caseKey).filter((k) => byKey[k]).map((k) => {
    const r = byKey[k];
    const d = r.numeric_change;
    const delta = d > 0 ? `+${d}` : `${d}`;
    const markets = (r.markets_potentially_affected || []).slice(0, 3)
      .map((m) => `<li>${esc(m)}</li>`).join('');
    return `<div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">
        <strong>${esc(r.player)}</strong>
        <span class="pill ${SEV_CLASS[r.severity_label]}">${esc(r.severity_label)}</span>
      </div>
      <div class="src" style="margin:4px 0 10px;">
        ${esc(r.position || '')} ${esc(fmt(r.team))} · ${esc(r.season)} W${esc(r.week)} ·
        <span class="mono">${esc(fmt(r.game_id))}</span>
      </div>
      <div class="chg" style="font-size:1.05rem;margin-bottom:8px;">
        ${esc(r.stat)}: <span class="from">${esc(r.original_value)}</span> →
        <span class="to">${esc(r.corrected_value)}</span>
        <span class="delta">(${esc(delta)})</span>
      </div>
      <div class="src">
        Final score ${esc(fmt(r.final_score))} ·
        corrected ${esc(fmt(r.days_from_game_to_correction))} days after the game
      </div>
      ${markets ? `<div class="src" style="margin-top:8px;"><strong>Markets potentially affected:</strong><ul class="tight" style="margin:4px 0 0 16px;">${markets}</ul></div>` : ''}
      <div class="src" style="margin-top:8px;"><strong>Rationale stated in notice:</strong> ${esc(r.correction_reason || 'Not stated in the archived correction notice.')}</div>
      <div class="src" style="margin-top:6px;"><strong>Market relevance:</strong> ${esc(r.impact_reason)}</div>
      <div style="margin-top:10px;"><a href="${esc(r.source_url_archived)}" target="_blank" rel="noopener" class="src">check the official source ↗</a></div>
    </div>`;
  }).join('');
}

/* ---------------------------------------------------------------- exposure */
function renderExposure(ms) {
  const s = ms.summary;
  const exactMarginCount = document.getElementById('zero-margin-count');
  if (exactMarginCount) exactMarginCount.textContent = num(s.zero_margin_line_distance_matches);
  document.getElementById('exposure-cards').innerHTML = `
    <div class="card"><div class="num">${num(s.games_considered_with_scores_and_lines)}</div>
      <div class="lbl">Games assessed</div>
      <div class="sub">2025–26 games with a final score and a closing line</div></div>
    <div class="card"><div class="num warn">${num(s.games_within_distance_threshold_of_a_line)}</div>
      <div class="lbl">Within the distance threshold</div>
      <div class="sub">${num(s.within_threshold_share_pct)}% had a final margin or total within ${num(s.distance_threshold_points)} point(s) of a line</div></div>
    <div class="card"><div class="num warn">${num(s.zero_margin_line_distance_matches)}</div>
      <div class="lbl">Zero margin-line distance</div>
      <div class="sub">absolute final margin matched absolute spread size; not necessarily a push</div></div>
    <div class="card"><div class="num">${num(s.zero_total_line_distance_matches)}</div>
      <div class="lbl">Zero total-line distance</div>
      <div class="sub">final total equaled the line value; settlement rules are not evaluated</div></div>`;

  const zeroDistanceGames = ms.games.filter((g) => g.zero_margin_line_distance);
  const tb = document.querySelector('#tbl-push tbody');
  tb.innerHTML = zeroDistanceGames.length ? zeroDistanceGames.map((g) => `<tr>
      <td class="mono">${esc(g.game_id)}</td>
      <td>${esc(g.gameday)}</td>
      <td class="num">${esc(g.away_team)} ${esc(g.away_score)} – ${esc(g.home_score)} ${esc(g.home_team)}</td>
      <td class="num">${esc(g.closing_spread)}</td>
      <td class="num">${esc(g.closing_total)}</td>
      <td class="num">${esc(g.margin_gap_points)}</td>
      <td class="num">${esc(g.total_gap_points)}</td>
    </tr>`).join('')
    : `<tr><td colspan="7" class="empty">No zero-distance margin-to-spread matches in this window.</td></tr>`;
}

/* ------------------------------------------------------------ limitations */
const LIMITS = [
  ['Blocker', 'The official NFL correction feed was retired in 2026.',
   'The page that published Elias Sports Bureau corrections now redirects to a news hub. A third-party diff cannot distinguish an official correction from a provider bug. A vendor feed could help only if the actual product documents NFL/Elias provenance, revision history, access and rights.'],
  ['High', 'The successor channel is a client-side JS app with no documented API.',
   'ESPN\'s corrections page renders in the browser. Scraping it would mean reverse-engineering a private API — brittle and likely against terms.'],
  ['High', 'Player-stat polling is not wired into the scheduled detector.',
   'The play-by-play adapter only exposes metadata/download helpers. Fetching, schema validation, normalization, revision diffing, durable persistence and player-stat alerting still need implementation and a production-data backtest.'],
  ['Medium', 'The corrections parser has not seen byte-exact archived HTML.',
   'The parser was validated against stored rendered page content; byte-exact HTML extraction remains untested here. <code>run.py selfcheck</code> is a manual/backfill diagnostic and is not a gate in the score-only scheduled workflow.'],
  ['Medium', 'The mirror is not the NFL.',
   'The scheduled differential detector uses a third-party mirror of NFL results. A change could be an official correction or a mirror bug; this detector cannot tell them apart. No independent corroboration source is integrated or validated here, and cross-source agreement is not official confirmation.'],
  ['Medium', 'No verified per-game prop-line or settlement archive.',
   'No per-game player-prop line archive was verified. The project flags candidate stat categories for review under a heuristic; it does not prove a particular market or line was offered.'],
  ['Medium', 'The database is a verified seed, not the full corpus.',
   'A verified seed was parsed from 10 stored archived pages. An observed archive-search surface includes candidate captures across 2010–2025, multiple position filters and weeks, but has not been validated as a complete denominator. Adding a sourced page is mechanically ingestible; establishing coverage still requires review and rate-limited retrieval.'],
  ['Low', 'Betting-line sign conventions are ambiguous in secondary sources.',
   'The exposure analysis uses only the magnitude of the spread, which is correct under either convention. The sign is never asserted.'],
  ['Low', 'A correction reverted between two snapshots is invisible.',
   'If a value changes and changes back between snapshots, the diff sees nothing. This is now measured, not assumed: the source-movement study found the mirrored file changed in 44 of 44 sampled intervals across 59 days, so the blind spot is exercised constantly. Upstream Git history is the only way to look inside an interval.'],
  ['Medium', 'A notification can be delivered and never read.',
   'A 2xx from a Slack or Discord webhook proves the endpoint accepted a payload. Neither platform returns a read receipt, and this project has no email or SMS channel and no user accounts. "The alert was sent" is the strongest honest claim; the Atom feeds let a reader verify independently what was published and when.'],
  ['Medium', 'The watchdog cannot see GitHub-side or human-side failure.',
   'health.yml reads the artefacts the detector leaves behind, so it cannot tell a workflow GitHub disabled or delayed from one that ran and found nothing, nor a runner outage, nor whether a delivered message was read. Every check reports UNKNOWN rather than OK when the evidence is absent, and staleness is a hard failure.'],
  ['Medium', 'Archive verification uses one render channel on both sides.',
   'web.archive.org is unreachable from this project\'s sandbox over plain HTTP, so a re-read compares a stored artefact against a fresh rendering obtained the same way. It catches transcription drift, dropped rows and a wrong capture (mutation-checked), but a systematic rendering error would appear on both sides.'],
  ['Low', 'Provider id columns are renumbered long after a game ends.',
   'The mirror renumbered its <code>ftn</code> and <code>pff</code> provider game-id columns on 2024 games in September 2026, about 21 months later. This project keys on <code>game_id</code> only, so a renumbering cannot re-point a record at a different game.'],
  ['Low', 'Exact correction publication latency and any general deadline are unknown.',
   'The selected joined sample spans 1–4 calendar days to the correction date printed on the archived page; this is not an exact timestamp or a universal deadline. The 14-day review flag is a project heuristic, not an NFL policy.'],
];

function renderLimits() {
  document.getElementById('limits-list').innerHTML = LIMITS.map(([sev, title, body]) => `
    <details>
      <summary><span class="pill sev-${sev === 'Blocker' ? 3 : sev === 'High' ? 3 : sev === 'Medium' ? 2 : 0}" style="margin-right:8px;">${esc(sev.toUpperCase())}</span>${esc(title)}</summary>
      <p>${body}</p>
    </details>`).join('');
}

/* -------------------------------------------------------------------- init */
(async function init() {
  try {
    const [db, study, ms] = await Promise.all([
      loadFirst(['data/discrepancies.json']),
      loadFirst(['data/score_integrity_study.json', 'data/evidence/score_integrity_study.json']),
      loadFirst(['data/market_sensitivity_2025_2026.json']),
    ]);

    DB = db.records;

    // The feed is operational state: load it, but never let a missing feed file
    // take the historical database down with it.
    loadFirst(['data/alerts/feed.json', 'data/feed.json'])
      .then(renderFeed)
      .catch(() => renderFeed({ latest: null, runs: [], summary: {} }));

    /* Operational state: loaded separately and non-fatally, and rendered with an
       explicit "unknown" state rather than being silently omitted. */
    loadFirst(['data/alerts/health.json'])
      .then(renderHealth)
      .catch(() => renderHealth(null));

    loadFirst(['data/upstream_churn_study.json', 'data/evidence/upstream_churn_study.json'])
      .then(renderChurn)
      .catch(() => renderChurn(null));

    renderTopCards(db, study);
    renderIntegrity(study);
    renderCases(db);
    renderExposure(ms);
    renderLimits();

    const seasons = [...new Set(DB.map((r) => r.season))].sort();
    document.getElementById('f-season').insertAdjacentHTML('beforeend',
      seasons.map((s) => `<option value="${s}">${s}</option>`).join(''));

    wireSorting();
    ['q', 'f-sev', 'f-season'].forEach((id) =>
      document.getElementById(id).addEventListener('input', renderDB));
    renderDB();

    document.getElementById('generated').textContent =
      `Database generated ${db.meta.generated_at} · integrity study ${study.generated_at} · ` +
      `official statistician: ${db.meta.official_statistician}`;
  } catch (e) {
    document.querySelectorAll('tbody').forEach((tb) => {
      tb.innerHTML = `<tr><td class="empty">Could not load data: ${esc(e.message)}</td></tr>`;
    });
    console.error(e);
  }
})();
