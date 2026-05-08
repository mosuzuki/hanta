const iconForKpi = {
  casesTotal: '👥',
  pcrPositive: '🔬',
  deaths: '❤',
  severeIcu: '🏥',
  symptomaticOnBoard: '🗣️',
  peopleOnBoard: '👥'
};

const timelineIcons = {
  ship: '🚢', case: '♙', death: '✚', port: '⚓', evac: '🚑', lab: '📋', notice: '📣', document: '📄'
};

const summaryIcons = ['📋', '📈', '👁️', '📣'];

function fmtDate(iso) {
  try {
    return new Intl.DateTimeFormat('ja-JP', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Tokyo', hour12: false
    }).format(new Date(iso)).replaceAll('/', '-');
  } catch (_) {
    return iso;
  }
}

async function loadIncident() {
  const response = await fetch('data/incident.json', { cache: 'no-store' });
  if (!response.ok) throw new Error('data/incident.json を読み込めませんでした');
  return response.json();
}

function renderHeader(data) {
  document.getElementById('title').textContent = data.meta.title;
  document.getElementById('subtitle').textContent = data.meta.subtitle;
  document.getElementById('last-updated').textContent = `最終更新 ${fmtDate(data.meta.lastUpdated)} JST`;
  document.getElementById('update-note').textContent = data.meta.updateNote;
}

function renderKpis(data) {
  const grid = document.getElementById('kpi-grid');
  grid.innerHTML = Object.entries(data.kpis).map(([key, item]) => `
    <article class="kpi-card ${key}" title="${item.note || ''}">
      <div class="kpi-icon">${iconForKpi[key] || '•'}</div>
      <div>
        <div class="kpi-label">${item.label}</div>
        <div class="kpi-value">${item.value}</div>
      </div>
    </article>
  `).join('');
  const people = data.kpis.peopleOnBoard?.note || '';
  document.getElementById('kpi-note').textContent = `ⓘ ${people}`;
}

function renderAssessments(data) {
  const target = document.getElementById('official-assessments');
  target.innerHTML = data.officialAssessments.map(block => `
    <article class="assessment-block">
      <div class="assessment-head">
        <strong>${block.source} (${block.date})</strong>
        <a class="pill ${block.badgeClass}" href="${block.url}" target="_blank" rel="noopener">${block.badge}</a>
      </div>
      <ul class="clean">${block.bullets.map(b => `<li>${b}</li>`).join('')}</ul>
    </article>
  `).join('');
}

function renderTimeline(data) {
  const target = document.getElementById('timeline');
  const n = data.timeline.length;
  const nodes = data.timeline.map((ev, i) => {
    const x = 6 + (i * (88 / (n - 1)));
    return `<div class="tl-node ${ev.type}" style="left:${x}%">
      <div class="tl-date">${ev.date}</div>
      <div class="tl-label"><strong>${ev.label}</strong><br>${ev.detail}</div>
      <div class="tl-dot"></div>
      <div class="tl-icon">${timelineIcons[ev.type] || '•'}</div>
    </div>`;
  }).join('');
  target.innerHTML = `<div class="timeline-track"><div class="timeline-line"></div>${nodes}</div>`;
}

function renderRisk(data) {
  document.getElementById('risk-matrix').innerHTML = data.riskMatrix.map(row => `
    <div class="risk-row">
      <span>${row.target}</span>
      <span class="risk-level ${row.class}"><i class="dot ${row.class}"></i>${row.level}</span>
    </div>
  `).join('');
}

function renderHypotheses(data) {
  document.getElementById('hypotheses').innerHTML = data.hypotheses.map(h => `
    <div class="hyp-row">
      <span class="hyp-id">仮説${h.id}</span>
      <span class="hyp-title">${h.title}</span>
      <span class="hyp-badge ${h.class}">${h.status}</span>
    </div>
  `).join('');
}

function renderOperations(data) {
  document.getElementById('operations-table').innerHTML = data.operations.map(row => `
    <tr><td>${row.item}</td><td>${row.status}</td></tr>
  `).join('');
}

function renderRoute(data) {
  const labels = data.route;
  const points = [
    [56, 202], [112, 170], [178, 155], [270, 132], [352, 104], [432, 70], [520, 28]
  ];
  const line = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p[0]} ${p[1]}`).join(' ');
  const circles = points.map((p, i) => `
    <circle cx="${p[0]}" cy="${p[1]}" r="5" fill="#fff" stroke="#0d7587" stroke-width="3" />
    <text x="${p[0] + (i < 3 ? -42 : 12)}" y="${p[1] + (i < 3 ? 23 : 5)}" font-size="12" font-weight="700" fill="#173b60">${labels[i]}</text>
  `).join('');
  document.getElementById('route-map').innerHTML = `
    <svg viewBox="0 0 560 240" role="img" aria-label="MV Hondius route diagram">
      <defs>
        <linearGradient id="sea" x1="0" x2="1"><stop offset="0" stop-color="#eaf6ff"/><stop offset="1" stop-color="#ffffff"/></linearGradient>
      </defs>
      <rect width="560" height="240" fill="url(#sea)"/>
      <path d="M40 120 C120 60 195 78 265 110 S440 130 535 58" fill="none" stroke="#c4d9e8" stroke-width="18" opacity="0.45"/>
      <path d="M48 214 C125 200 172 186 226 150 C290 106 398 67 536 20" fill="none" stroke="#bdd6ea" stroke-width="1.2" stroke-dasharray="4 5"/>
      <path d="${line}" fill="none" stroke="#1d64b8" stroke-width="3"/>
      ${circles}
    </svg>`;
}

function renderSummary(data) {
  document.getElementById('ai-summary').innerHTML = data.aiSummary.map((s, i) => `
    <div class="summary-item">
      <div class="summary-icon">${summaryIcons[i] || '•'}</div>
      <p><strong>${s.label}:</strong> ${s.text}</p>
    </div>
  `).join('');
}

function renderSignals(data) {
  const target = document.getElementById('media-signals');
  target.innerHTML = `<div class="signals-list">${data.mediaSignals.map(s => `
    <article class="signal">
      <div class="meta">${s.date} / ${s.source} / ${s.evidence}</div>
      <p>${s.summary}</p>
      <a href="${s.url}" target="_blank" rel="noopener">ソースを開く</a>
    </article>
  `).join('')}</div>`;
}

function renderFooter(data) {
  document.getElementById('source-footer').textContent = data.sourceFooter;
}

loadIncident()
  .then(data => {
    renderHeader(data);
    renderKpis(data);
    renderAssessments(data);
    renderTimeline(data);
    renderRisk(data);
    renderHypotheses(data);
    renderOperations(data);
    renderRoute(data);
    renderSummary(data);
    renderSignals(data);
    renderFooter(data);
  })
  .catch(error => {
    document.body.innerHTML = `<main class="app-shell"><div class="card"><h1>読み込みエラー</h1><p>${error.message}</p></div></main>`;
  });
