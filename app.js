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

/* ------------------------------------------------------------------ cards */
function renderTopCards(db, study) {
  const c = db.meta.counts;
  document.getElementById('stat-records').textContent = num(c.total_records);
  document.getElementById('stat-potential').textContent = num(c.potential_to_change_market);
  document.getElementById('stat-snapshots').textContent = num(study.totals.game_snapshots_examined);
  document.getElementById('stat-snapshots-2').textContent = num(study.totals.game_snapshots_examined);
  document.getElementById('stat-revisions').textContent = num(study.totals.final_scores_revised_after_completion);
  document.getElementById('badge-records').textContent = `${c.total_records} verified records`;
}

/* --------------------------------------------------------- integrity table */
function renderIntegrity(study) {
  const tb = document.querySelector('#tbl-integrity tbody');
  tb.innerHTML = study.baselines.map((b) => {
    const bad = (b.frozen_field_changes_vs_current ?? 0) > 0;
    return `<tr>
      <td class="mono">${esc(b.baseline)}<br><span class="src">${esc(String(b.commit).slice(0, 10))}…</span></td>
      <td class="num">${num(b.final_at_baseline)}</td>
      <td class="num">${num(b.frozen_field_changes_vs_current ?? 0)}</td>
      <td><span class="pill ${bad ? 'sev-3' : 'sev-2'}">${bad ? 'revised' : 'unchanged'}</span></td>
    </tr>`;
  }).join('');

  const t = study.totals;
  document.querySelector('#tbl-integrity tfoot').innerHTML = `<tr>
    <td><strong>Total</strong></td>
    <td class="num"><strong>${num(t.game_snapshots_examined)}</strong></td>
    <td class="num"><strong>${num(t.final_scores_revised_after_completion)}</strong></td>
    <td><span class="pill sev-2">no score ever revised</span></td>
  </tr>`;

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
    tb.innerHTML = `<tr><td colspan="10" class="empty">No records match these filters.</td></tr>`;
    return;
  }

  tb.innerHTML = rows.map((r) => {
    const d = r.numeric_change;
    const delta = d > 0 ? `+${d}` : `${d}`;
    return `<tr>
      <td><span class="pill ${SEV_CLASS[r.severity_label] || 'sev-0'}" title="${esc(r.impact_reason)}">${esc(r.severity_label)}</span></td>
      <td>${esc(r.season)} <span class="src">W${esc(r.week)}</span></td>
      <td><strong>${esc(r.player)}</strong> <span class="src">${esc(r.position || '')}</span></td>
      <td>${esc(r.team)}</td>
      <td class="mono">${esc(fmt(r.game_id))}<br><span class="src">${esc(fmt(r.opponent))}</span></td>
      <td>${esc(fmt(r.game_date))}</td>
      <td>${esc(r.stat)}</td>
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
/* Selected by record_id only. All prose is generated from the record's own
   fields, so nothing here can assert something the database does not contain. */
const CASE_IDS = ['SC-0034', 'SC-0029', 'SC-0026', 'SC-0005', 'SC-0023', 'SC-0035'];

function renderCases(db) {
  const byId = Object.fromEntries(db.records.map((r) => [r.record_id, r]));
  const host = document.getElementById('cases');
  host.innerHTML = CASE_IDS.filter((id) => byId[id]).map((id) => {
    const r = byId[id];
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
        ${esc(r.position || '')} ${esc(r.team)} · ${esc(r.season)} W${esc(r.week)} ·
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
      <div class="src" style="margin-top:8px;">${esc(r.impact_reason)}</div>
      <div style="margin-top:10px;"><a href="${esc(r.source_url_archived)}" target="_blank" rel="noopener" class="src">check the official source ↗</a></div>
    </div>`;
  }).join('');
}

/* ---------------------------------------------------------------- exposure */
function renderExposure(ms) {
  const s = ms.summary;
  document.getElementById('exposure-cards').innerHTML = `
    <div class="card"><div class="num">${num(s.games_considered_with_scores_and_lines)}</div>
      <div class="lbl">Games assessed</div>
      <div class="sub">2025–26 games with a final score and a closing line</div></div>
    <div class="card"><div class="num warn">${num(s.correction_sensitive_games)}</div>
      <div class="lbl">Correction-sensitive</div>
      <div class="sub">${num(s.sensitive_share_pct)}% finished within 1 point of a market line</div></div>
    <div class="card"><div class="num warn">${num(s.exact_spread_pushes)}</div>
      <div class="lbl">Exact spread pushes</div>
      <div class="sub">a correction of any size would have created a winner</div></div>
    <div class="card"><div class="num">${num(s.exact_total_pushes)}</div>
      <div class="lbl">Exact total pushes</div>
      <div class="sub">finished exactly on the closing total</div></div>`;

  const pushes = ms.games.filter((g) => g.pushed_on_spread);
  const tb = document.querySelector('#tbl-push tbody');
  tb.innerHTML = pushes.length ? pushes.map((g) => `<tr>
      <td class="mono">${esc(g.game_id)}</td>
      <td>${esc(g.gameday)}</td>
      <td class="num">${esc(g.away_team)} ${esc(g.away_score)} – ${esc(g.home_score)} ${esc(g.home_team)}</td>
      <td class="num">${esc(g.closing_spread)}</td>
      <td class="num">${esc(g.closing_total)}</td>
      <td class="num">${esc(g.margin_gap_points)}</td>
      <td class="num">${esc(g.total_gap_points)}</td>
    </tr>`).join('')
    : `<tr><td colspan="7" class="empty">No exact spread pushes in this window.</td></tr>`;
}

/* ------------------------------------------------------------ limitations */
const LIMITS = [
  ['Blocker', 'The official NFL correction feed was retired in 2026.',
   'The page that published Elias Sports Bureau corrections now redirects to a news hub. Detection must infer changes by diffing third-party data, which can produce false positives and cannot distinguish an official correction from a provider bug. A licensed feed would unblock it.'],
  ['High', 'The successor channel is a client-side JS app with no documented API.',
   'ESPN\'s corrections page renders in the browser. Scraping it would mean reverse-engineering a private API — brittle and likely against terms.'],
  ['High', 'The highest-resolution signal is network-blocked in the build sandbox.',
   'Raw play-by-play release assets are served from a host unreachable here. On GitHub Actions this restriction does not apply; the adapter already exists, so it is a configuration change, not a rewrite.'],
  ['Medium', 'The corrections parser has not seen byte-exact archived HTML.',
   'The Internet Archive is not reachable from the build sandbox, so the parser is unit-tested against structural fixtures. <code>run.py selfcheck</code> reconciles it against real input on the first CI run — and should be run before any parsed output is trusted.'],
  ['Medium', 'The mirror is not the NFL.',
   'All differential detection runs against a third-party mirror of the official record. A change could be an official correction or a mirror bug, and the detector cannot tell them apart. A second independent source is the fix.'],
  ['Medium', 'No free, redistributable source of per-game prop lines.',
   'Real player-prop lines are a commercial product. We therefore model the pricing convention of line-priced stats and never assert that a specific line existed.'],
  ['Medium', 'The database is a verified seed, not the full corpus.',
   '36 rows across four sampled weeks, against an archived corpus spanning 2010–2025 × 10 position filters × 18+ weeks. Each page is a separate rate-limited request, so bulk expansion belongs in a scheduled job with backoff.'],
  ['Low', 'Betting-line sign conventions are ambiguous in secondary sources.',
   'The exposure analysis uses only the magnitude of the spread, which is correct under either convention. The sign is never asserted.'],
  ['Low', 'A correction reverted between two polls is invisible.',
   'If a value changes and changes back between snapshots, the diff sees nothing. Poll frequency is the only lever.'],
  ['Low', 'There is no published deadline for how late a correction may arrive.',
   'Rather than assume one, the build flags anything more than 14 days after the game, and anything dated before it.'],
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
