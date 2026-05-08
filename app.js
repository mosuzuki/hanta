let DATA, FETCHLOG;
const icons = {blue:"🧾", teal:"🔬", red:"💔", orange:"🏥", purple:"🤒", green:"👥"};

async function loadData(){
  const [incident, log] = await Promise.all([
    fetch("data/incident.json?ts=" + Date.now()).then(r => r.json()),
    fetch("data/fetch_log.json?ts=" + Date.now()).then(r => r.json()).catch(()=>({latest_items:[]}))
  ]);
  DATA = incident; FETCHLOG = log;
  renderAll();
}

function $(id){return document.getElementById(id);}
function esc(s){return String(s ?? "").replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));}

function renderAll(){
  $("title").textContent = DATA.meta.title;
  $("subtitle").textContent = DATA.meta.subtitle;
  $("lastUpdated").textContent = "最終更新 " + DATA.meta.last_updated_jst;
  $("updatePolicy").textContent = DATA.meta.update_policy;
  renderKpis();
  renderOfficial();
  renderTimeline("all");
  renderRisk();
  renderHypotheses();
  renderLineList();
  renderMap();
  renderOps();
  renderSummary();
  renderSignals("all");
  bindControls();
}

function renderKpis(){
  $("kpiGrid").innerHTML = DATA.kpis.map(k => `
    <div class="kpi-card ${esc(k.class)}">
      <div class="kpi-icon">${icons[k.class] || "●"}</div>
      <div>
        <div class="kpi-label">${esc(k.label)}</div>
        <div class="kpi-value">${esc(k.value)}</div>
        <div class="kpi-src">${esc(k.source)}</div>
      </div>
    </div>`).join("");
}

function renderOfficial(){
  $("officialAssessments").innerHTML = DATA.official_assessments.map(a => `
    <section class="assessment">
      <div class="assessment-head">
        <span>${esc(a.agency)} (${esc(a.date)})</span>
        <a href="${esc(a.url)}" target="_blank" rel="noopener" class="pill ${esc(a.badgeClass)}">${esc(a.badge)}</a>
      </div>
      <ul>${a.bullets.map(b=>`<li>${esc(b)}</li>`).join("")}</ul>
    </section>`).join("");
}

function renderTimeline(filter){
  const rows = DATA.timeline.filter(t => filter==="all" || t.confidence === filter || (filter==="reported" && t.confidence!=="official"));
  $("timeline").innerHTML = rows.map(t => `
    <div class="t-item ${esc(t.type)}" data-confidence="${esc(t.confidence)}">
      <div class="t-date">${esc(t.short)}</div>
      <div class="t-dot"></div>
      <div class="t-card">
        <div class="t-title">${esc(t.title)}</div>
        <div class="t-detail">${esc(t.detail)}</div>
        <div class="confidence">${esc(t.date)} / ${esc(t.source)} / ${esc(t.confidence)}</div>
      </div>
    </div>`).join("");
}

function renderRisk(){
  $("riskMatrix").innerHTML = DATA.risk_matrix.map(r => `
    <div class="risk-row ${esc(r.class)}">
      <div class="risk-target">${esc(r.target)}</div>
      <div class="risk-level">${esc(r.level)}</div>
      <div class="risk-rationale">${esc(r.rationale)}</div>
    </div>`).join("");
  $("uncertainties").innerHTML = DATA.uncertainties.map(u=>`<li>${esc(u)}</li>`).join("");
}

function renderHypotheses(){
  const badgeClass = {best:"green", possible:"blue", unknown:"gray", low:"gray"};
  $("hypotheses").innerHTML = DATA.hypotheses.map(h => `
    <div class="hypo-card">
      <div class="hypo-head">
        <span class="hypo-title">${esc(h.name)}　${esc(h.title)}</span>
        <span class="pill ${badgeClass[h.class] || "gray"}">${esc(h.status)}</span>
      </div>
      <div class="hypo-meta"><b>支持:</b> ${esc((h.support||[]).join(" / "))}</div>
      <div class="hypo-meta"><b>未確定・反証:</b> ${esc((h.against||[]).join(" / "))}</div>
    </div>`).join("");
}

function renderLineList(){
  const q = ($("lineSearch")?.value || "").toLowerCase();
  const rows = DATA.line_list.filter(c => JSON.stringify(c).toLowerCase().includes(q));
  const badge = (c)=> c==="official" ? "green" : c==="mixed" ? "blue" : c==="reported" ? "gray" : "gray";
  $("lineList").querySelector("tbody").innerHTML = rows.map(c => `
    <tr>
      <td><b>${esc(c.case_id)}</b><br><small>${esc(c.role)}</small></td>
      <td>${esc(c.status)}</td>
      <td>${esc(c.sex_age)}<br><small>${esc(c.nationality)}</small></td>
      <td>${esc(c.onset)}</td>
      <td>${esc(c.outcome)}</td>
      <td>${esc(c.location)}</td>
      <td>${esc(c.lab)}</td>
      <td><span class="pill ${badge(c.confidence)}">${esc(c.confidence)}</span><br><small>${esc(c.source)}</small></td>
    </tr>`).join("");
}

function renderMap(){
  const route = DATA.route;
  $("shipPositionLabel").textContent = route.position.label;
  $("mapNote").textContent = `現在位置: ${route.position.label} / ${route.position.timestamp} / Source: ${route.position.source} / Confidence: ${route.position.confidence}`;

  const map = L.map("map", {scrollWheelZoom:false}).setView([0,-28], 3);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 7,
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(map);

  const pts = route.waypoints.map(w => [w.lat, w.lng]);
  L.polyline(pts, {weight:3, opacity:.8}).addTo(map);
  route.waypoints.forEach(w => {
    const marker = L.circleMarker([w.lat,w.lng], {
      radius: w.type==="current-area" ? 8 : 5,
      weight:2,
      fillOpacity:.9
    }).addTo(map);
    marker.bindPopup(`<b>${esc(w.name)}</b><br>${esc(w.type)}`);
  });
  const ship = L.marker([route.position.lat, route.position.lng]).addTo(map);
  ship.bindPopup(`<b>${esc(route.ship_name)}</b><br>${esc(route.position.label)}<br>${esc(route.position.timestamp)}`).openPopup();
  const bounds = L.latLngBounds(pts.concat([[route.position.lat, route.position.lng]]));
  map.fitBounds(bounds.pad(.12));
}

function renderOps(){
  $("contactOps").innerHTML = DATA.contact_ops.map(o => `
    <div class="ops-item"><b>${esc(o.item)}</b><span>${esc(o.status)}</span><small>${esc(o.evidence)}</small></div>`).join("");
}

function renderSummary(){
  $("aiSummary").innerHTML = DATA.ai_summary.map(s => `
    <div class="summary-item"><div>▸</div><div><b>${esc(s.heading)}:</b> ${esc(s.text)}</div></div>`).join("");
}

function renderSignals(filter){
  const items = (FETCHLOG.latest_items || []).filter(it => filter==="all" || it.kind===filter);
  $("signals").innerHTML = items.length ? items.map(it => `
    <div class="signal-item">
      <div class="signal-kind kind-${esc(it.kind)}">${esc(it.kind)}<br><small>tier ${esc(it.tier ?? "")}</small></div>
      <div>
        <div class="signal-title"><a href="${esc(it.url || "#")}" target="_blank" rel="noopener">${esc(it.title || "(untitled)")}</a></div>
        <div class="signal-snippet">${esc(it.snippet || "")}</div>
        <div class="confidence">${esc(it.source || "")} / ${esc(it.confidence || "low")}</div>
      </div>
      <div class="signal-time">${esc(it.published || "")}</div>
    </div>`).join("") : `<p class="note">まだ取得ログがありません。GitHub Actions実行後に表示されます。</p>`;
}

function bindControls(){
  document.querySelectorAll("#timelineFilters button").forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll("#timelineFilters button").forEach(b=>b.classList.remove("active"));
      btn.classList.add("active"); renderTimeline(btn.dataset.filter);
    };
  });
  document.querySelectorAll(".signal-tabs button").forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll(".signal-tabs button").forEach(b=>b.classList.remove("active"));
      btn.classList.add("active"); renderSignals(btn.dataset.signal);
    };
  });
  $("lineSearch").oninput = renderLineList;
}

loadData().catch(err => {
  console.error(err);
  document.body.insertAdjacentHTML("afterbegin", `<div style="padding:12px;background:#fff0f0;color:#8a1f1f">データ読み込みに失敗しました: ${esc(err.message)}</div>`);
});
