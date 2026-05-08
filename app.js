let DATA, FETCHLOG, leafletMap;
const icons = {blue:"🧾", teal:"🔬", red:"💔", orange:"🏥", purple:"🤒", green:"👥"};

async function loadData(){
  const [incident, log] = await Promise.all([
    fetch("data/incident.json?ts=" + Date.now()).then(r => r.json()),
    fetch("data/fetch_log.json?ts=" + Date.now()).then(r => r.json()).catch(()=>({latest_items:[], academic_items:[]}))
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
  renderKpis(); renderOfficial(); renderTimeline("all"); renderRisk(); renderHypotheses();
  renderLineList(); renderMap(); renderOps(); renderSummary(); renderSignals("all"); renderAcademic();
  bindControls();
}

function renderKpis(){
  $("kpiGrid").innerHTML = DATA.kpis.map(k => `
    <div class="kpi-card ${esc(k.class)}"><div class="kpi-icon">${icons[k.class] || "●"}</div><div>
      <div class="kpi-label">${esc(k.label)}</div><div class="kpi-value">${esc(k.value)}</div><div class="kpi-src">${esc(k.source)}</div>
    </div></div>`).join("");
}

function renderOfficial(){
  $("officialAssessments").innerHTML = DATA.official_assessments.map(a => `
    <section class="assessment"><div class="assessment-head"><span>${esc(a.agency)} (${esc(a.date)})</span>
      <a href="${esc(a.url)}" target="_blank" rel="noopener" class="pill ${esc(a.badgeClass)}">${esc(a.badge)}</a></div>
      <ul>${a.bullets.map(b=>`<li>${esc(b)}</li>`).join("")}</ul></section>`).join("");
}

function renderTimeline(filter){
  const rows = DATA.timeline.filter(t => filter==="all" || t.confidence === filter || (filter==="reported" && t.confidence!=="official"));
  $("timeline").innerHTML = rows.map(t => `
    <div class="t-item ${esc(t.type)}" data-confidence="${esc(t.confidence)}"><div class="t-date">${esc(t.short)}</div><div class="t-dot"></div>
      <div class="t-card"><div class="t-title">${esc(t.title)}</div><div class="t-detail">${esc(t.detail)}</div>
      <div class="confidence">${esc(t.date)} / ${esc(t.source)} / ${esc(t.confidence)}</div></div></div>`).join("");
}

function renderRisk(){
  $("riskMatrix").innerHTML = DATA.risk_matrix.map(r => `
    <div class="risk-row ${esc(r.class)}"><div class="risk-target">${esc(r.target)}</div><div class="risk-level">${esc(r.level)}</div>
    <div class="risk-rationale">${esc(r.rationale)}</div></div>`).join("");
  $("uncertainties").innerHTML = DATA.uncertainties.map(u=>`<li>${esc(u)}</li>`).join("");
}

function renderHypotheses(){
  const badgeClass = {best:"green", possible:"blue", unknown:"gray", low:"gray"};
  $("hypotheses").innerHTML = DATA.hypotheses.map(h => `
    <div class="hypo-card"><div class="hypo-head"><span class="hypo-title">${esc(h.name)}　${esc(h.title)}</span>
    <span class="pill ${badgeClass[h.class] || "gray"}">${esc(h.status)}</span></div>
    <div class="hypo-meta"><b>支持:</b> ${esc((h.support||[]).join(" / "))}</div>
    <div class="hypo-meta"><b>未確定・反証:</b> ${esc((h.against||[]).join(" / "))}</div></div>`).join("");
}

function renderLineList(){
  const q = ($("lineSearch")?.value || "").toLowerCase();
  const rows = DATA.line_list.filter(c => JSON.stringify(c).toLowerCase().includes(q));
  const badge = (c)=> c==="official" ? "green" : c==="mixed" ? "blue" : c==="reported" ? "gray" : "gray";
  $("lineList").querySelector("tbody").innerHTML = rows.map(c => `
    <tr><td><b>${esc(c.case_id)}</b><br><small>${esc(c.role)}</small></td><td>${esc(c.status)}</td>
    <td>${esc(c.sex_age)}<br><small>${esc(c.nationality)}</small></td><td>${esc(c.onset)}</td><td>${esc(c.outcome)}</td>
    <td>${esc(c.location)}</td><td>${esc(c.lab)}</td><td><span class="pill ${badge(c.confidence)}">${esc(c.confidence)}</span><br><small>${esc(c.source)}</small></td></tr>`).join("");
}

function renderMap(){
  const route = DATA.route;
  $("shipPositionLabel").textContent = route.position.label;
  $("mapNote").textContent = `現在位置: ${route.position.label} / ${route.position.timestamp} / Source: ${route.position.source} / Confidence: ${route.position.confidence}`;

  if (leafletMap) { leafletMap.remove(); leafletMap = null; }
  const mapEl = $("map");
  mapEl.innerHTML = "";

  leafletMap = L.map("map", {
    scrollWheelZoom:false,
    worldCopyJump:true,
    preferCanvas:true
  });

  const tileLayer = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 7,
    minZoom: 2,
    attribution: "&copy; OpenStreetMap contributors",
    crossOrigin: true
  });
  tileLayer.addTo(leafletMap);

  const pts = route.waypoints.map(w => [Number(w.lat), Number(w.lng)]).filter(p => Number.isFinite(p[0]) && Number.isFinite(p[1]));
  const path = L.polyline(pts, {color:"#0b66b2", weight:3, opacity:.85}).addTo(leafletMap);

  route.waypoints.forEach(w => {
    const color = w.type==="departure" ? "#0b7f8e" : w.type==="disembarkation" ? "#ea7a1a" : w.type==="evacuation" ? "#d94b4b" : w.type==="current-area" ? "#21a366" : "#1266b0";
    const marker = L.circleMarker([w.lat,w.lng], {radius: w.type==="current-area" ? 8 : 5, color, fillColor: color, fillOpacity:.9, weight:2}).addTo(leafletMap);
    marker.bindPopup(`<b>${esc(w.name)}</b><br>${esc(w.type)}`);
  });

  const shipIcon = L.divIcon({className:"ship-marker", html:"🚢", iconSize:[28,28], iconAnchor:[14,14]});
  L.marker([route.position.lat, route.position.lng], {icon: shipIcon}).addTo(leafletMap)
    .bindPopup(`<b>${esc(route.ship_name)}</b><br>${esc(route.position.label)}<br>${esc(route.position.timestamp)}`);

  const bounds = L.latLngBounds(pts.concat([[route.position.lat, route.position.lng]]));
  leafletMap.fitBounds(bounds.pad(0.18), {maxZoom: 4});

  // Fix common GitHub Pages/Leaflet rendering issue where tiles load into only one corner.
  const invalidate = () => leafletMap && leafletMap.invalidateSize(true);
  setTimeout(invalidate, 100);
  setTimeout(invalidate, 500);
  setTimeout(() => { invalidate(); leafletMap.fitBounds(bounds.pad(0.18), {maxZoom: 4}); }, 1000);

  if (window.ResizeObserver) {
    const ro = new ResizeObserver(() => invalidate());
    ro.observe(mapEl);
  }
}

function renderOps(){
  $("contactOps").innerHTML = DATA.contact_ops.map(o => `<div class="ops-item"><b>${esc(o.item)}</b><span>${esc(o.status)}</span><small>${esc(o.evidence)}</small></div>`).join("");
}

function renderSummary(){
  $("aiSummary").innerHTML = DATA.ai_summary.map(s => `<div class="summary-item"><div>▸</div><div><b>${esc(s.heading)}:</b> ${esc(s.text)}</div></div>`).join("");
}

function renderSignals(filter){
  const items = (FETCHLOG.latest_items || []).filter(it => filter==="all" || it.kind===filter);
  $("signals").innerHTML = items.length ? items.map(it => `
    <div class="signal-item"><div class="signal-kind kind-${esc(it.kind)}">${esc(it.kind)}<br><small>tier ${esc(it.tier ?? "")}</small></div>
      <div><div class="signal-title"><a href="${esc(it.url || "#")}" target="_blank" rel="noopener">${esc(it.title || "(untitled)")}</a></div>
      <div class="signal-snippet">${esc(it.snippet || "")}</div><div class="confidence">${esc(it.source || "")} / ${esc(it.confidence || "low")}</div></div>
      <div class="signal-time">${esc(it.published || "")}</div></div>`).join("") :
    `<p class="note">まだ取得ログがありません。GitHub Actions実行後に表示されます。Actions画面で workflow_dispatch を押すとすぐ更新できます。</p>`;
}

function renderAcademic(){
  const items = FETCHLOG.academic_items || [];
  $("academicList").innerHTML = items.length ? items.map(it => `
    <div class="academic-item"><div class="signal-kind kind-academic">academic<br><small>${esc(it.year || "")}</small></div>
      <div>
        <div class="academic-title"><a href="${esc(it.url || "#")}" target="_blank" rel="noopener">${esc(it.title_ja || it.title || "(untitled)")}</a></div>
        <div class="academic-en">${esc(it.title || "")}</div>
        <div class="academic-summary">${esc(it.summary_ja || it.abstract || "要約未生成。OPENAI_API_KEYを設定すると日本語要約を生成します。")}</div>
        <div class="confidence">${esc(it.journal || "")} / ${esc(it.source || "PubMed")} / ${esc(it.doi || "")}</div>
      </div>
      <div class="academic-meta">${esc(it.published || "")}<br><span class="pill ${it.priority ? "orange" : "gray"}">${it.priority ? "主要誌" : "関連"}</span></div>
    </div>`).join("") :
    `<p class="note">学術文献ログがありません。GitHub Actions実行後にPubMed/Journal RSSから取得されます。</p>`;
}

function bindControls(){
  document.querySelectorAll("#timelineFilters button").forEach(btn => {
    btn.onclick = () => { document.querySelectorAll("#timelineFilters button").forEach(b=>b.classList.remove("active")); btn.classList.add("active"); renderTimeline(btn.dataset.filter); };
  });
  document.querySelectorAll(".signal-tabs button").forEach(btn => {
    btn.onclick = () => { document.querySelectorAll(".signal-tabs button").forEach(b=>b.classList.remove("active")); btn.classList.add("active"); renderSignals(btn.dataset.signal); };
  });
  $("lineSearch").oninput = renderLineList;
}

loadData().catch(err => {
  console.error(err);
  document.body.insertAdjacentHTML("afterbegin", `<div style="padding:12px;background:#fff0f0;color:#8a1f1f">データ読み込みに失敗しました: ${esc(err.message)}</div>`);
});
