/* HABIB CONTROL · F1 Data Center — SPA sin build: fetch a /api + Plotly vendorizado. */

const $view = document.getElementById("view");
const state = { year: null, seasons: [], sid: null };

/* ───────────────────────────── helpers */
const api = async (path) => {
  const r = await fetch(`/api${path}`);
  if (!r.ok) throw new Error(`${r.status} en ${path}`);
  return r.json();
};

const el = (html) => {
  const t = document.createElement("template");
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
};

const fmtLap = (s) => {
  if (s == null) return "—";
  const m = Math.floor(s / 60);
  return `${m}:${(s - m * 60).toFixed(3).padStart(6, "0")}`;
};

const PLOTLY_CFG = { displayModeBar: false, responsive: true };

const baseLayout = (extra = {}) => ({
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: "Inter, sans-serif", color: "#c8cdd6", size: 12 },
  margin: { l: 58, r: 70, t: 16, b: 44 },
  xaxis: { showgrid: false, zeroline: false, color: "#9aa0aa" },
  yaxis: { gridcolor: "rgba(255,255,255,.06)", griddash: "dot", zeroline: false, color: "#9aa0aa" },
  hoverlabel: { bgcolor: "#1a1e27", bordercolor: "#3a3d47", font: { color: "#f3f4f6", size: 12 } },
  ...extra,
});

/* Tarjeta de gráfica con la firma de la casa: resumen calculado + guía tip. */
function chartCard({ title, sub = "", summary = "", tips = [], legendHtml = "" }) {
  const card = el(`<div class="card chart-card">
    <div class="chart-head"><h2>${title}</h2><span class="sub">${sub}</span></div>
    <div class="chart-body"><div class="plot"></div></div>
    ${legendHtml}
    ${summary ? `<div class="chart-summary">${summary}</div>` : ""}
    ${tips.length ? `<details class="chart-guide"><summary>¿Cómo leer esta gráfica?</summary>
      <ul>${tips.map((t) => `<li>${t}</li>`).join("")}</ul></details>` : ""}
  </div>`);
  return { card, plot: card.querySelector(".plot") };
}

const skeleton = (hs) => {
  $view.innerHTML = "";
  hs.forEach((h) => $view.appendChild(el(`<div class="skeleton-block" style="height:${h}px"></div>`)));
};

const drvChip = (code, color, name = "") =>
  `<span class="drv" style="--cc:${color}"><i></i>${code}${name ? ` <small>${name}</small>` : ""}</span>`;

function seasonPills(active, onPick) {
  const wrap = el(`<div class="pills" style="margin-bottom:18px"></div>`);
  state.seasons.forEach((s) => {
    const p = el(`<button class="pill ${s.year === active ? "active" : ""}">${s.year}</button>`);
    p.onclick = () => onPick(s.year);
    wrap.appendChild(p);
  });
  return wrap;
}

/* ───────────────────────────── vista TEMPORADA */
async function viewTemporada() {
  skeleton([46, 110, 460, 320]);
  const data = await api(`/championship/${state.year}`);
  $view.innerHTML = "";
  $view.appendChild(seasonPills(state.year, (y) => { state.year = y; viewTemporada(); }));

  if (!data.drivers.length) {
    $view.appendChild(el(`<div class="empty">No hay carreras de ${state.year} en la base.
      Carga sesiones en el dashboard o corre <code>python ingest.py --cached</code>.</div>`));
    return;
  }

  const lid = data.drivers[0];
  const reyW = [...data.drivers].sort((a, b) => b.wins - a.wins)[0];
  const tiles = el(`<div class="tiles" style="margin-bottom:18px">
    <div class="card tile" style="--tc:${lid.color}"><div class="label">Líder</div>
      <div class="value">${lid.code}</div><div class="hint">${lid.total} pts · ${lid.team}</div></div>
    <div class="card tile" style="--tc:${reyW.color}"><div class="label">Más victorias</div>
      <div class="value">${reyW.wins}</div><div class="hint">${reyW.code} · ${reyW.podiums} podios</div></div>
    <div class="card tile"><div class="label">GPs en la base</div>
      <div class="value">${data.gps.length}</div><div class="hint">temporada ${state.year}</div></div>
  </div>`);
  $view.appendChild(tiles);

  const { card, plot } = chartCard({
    title: `Campeonato ${state.year} · puntos acumulados`,
    sub: "Carrera + Sprint del mismo fin de semana",
    summary: data.summary,
    tips: [
      "<b>¿Dos líneas se separan?</b> → uno suma mucho más por fin de semana; busca el GP donde empezó la brecha.",
      "<b>¿Una línea se aplana?</b> → racha mala: abandonos o fuera de puntos.",
      "<b>¿Se cruzan?</b> → cambio de liderato real del campeonato.",
      "Toca un piloto en la leyenda para aislarlo; doble toque lo deja solo.",
    ],
  });
  $view.appendChild(card);

  const top = data.drivers.slice(0, 10);
  const annotations = top.slice(0, 5).map((d) => ({
    x: data.gps.length - 1, y: d.points[d.points.length - 1],
    text: ` ${d.code}`, showarrow: false, xanchor: "left",
    font: { color: d.color, size: 11.5, family: "Inter" },
  }));
  Plotly.newPlot(plot, top.map((d) => ({
    type: "scatter", mode: "lines+markers", name: d.code,
    x: data.gps, y: d.points,
    line: { color: d.color, width: 2 }, marker: { size: 5.5, color: d.color },
    hovertemplate: `<b>${d.code}</b> · %{x}<br>%{y:.0f} pts<extra></extra>`,
  })), baseLayout({
    height: 440, annotations, hovermode: "x unified",
    yaxis: { ...baseLayout().yaxis, title: { text: "PUNTOS", font: { size: 10.5 } } },
    legend: { orientation: "h", y: -0.14, font: { size: 11 } },
  }), PLOTLY_CFG);

  // clasificación
  const maxPts = lid.total || 1;
  const rows = data.drivers.map((d, i) => `<tr>
    <td class="num">${i + 1}</td>
    <td>${drvChip(d.code, d.color, d.name)}</td>
    <td>${d.team}</td>
    <td class="num"><b>${d.total}</b></td>
    <td><div class="ptsbar" style="--cc:${d.color}"><i style="width:${(d.total / maxPts) * 100}%"></i></div></td>
    <td class="num">${d.wins}</td><td class="num">${d.podiums}</td>
  </tr>`).join("");
  $view.appendChild(el(`<div class="section-title">Clasificación del campeonato</div>`));
  $view.appendChild(el(`<div class="card table-wrap"><table>
    <thead><tr><th class="num">#</th><th>Piloto</th><th>Equipo</th>
    <th class="num">Pts</th><th></th><th class="num">Vict.</th><th class="num">Podios</th></tr></thead>
    <tbody>${rows}</tbody></table></div>`));
}

/* ───────────────────────────── vista CARRERA */
async function viewCarrera() {
  skeleton([46, 200]);
  const races = await api(`/races/${state.year}`);
  $view.innerHTML = "";
  $view.appendChild(seasonPills(state.year, (y) => { state.year = y; state.sid = null; viewCarrera(); }));

  if (!races.length) {
    $view.appendChild(el(`<div class="empty">No hay carreras de ${state.year} en la base.</div>`));
    return;
  }
  if (!state.sid || !races.some((r) => r.sid === state.sid)) state.sid = races[races.length - 1].sid;

  const grid = el(`<div class="race-grid" style="margin-bottom:22px"></div>`);
  races.forEach((r) => {
    const c = el(`<div class="card race-card" style="${r.sid === state.sid ? "border-color:rgba(255,60,60,.55)" : ""}">
      <div class="round">RONDA ${r.round}</div><h3>${r.label}</h3>
      <div class="date">${r.date} · ${r.n_laps} vueltas</div>
      <div class="podium">${r.podium.map((p, i) =>
        `<span class="chip" style="--cc:${p.color}"><i></i>P${i + 1} ${p.code}</span>`).join("")}</div>
    </div>`);
    c.onclick = () => { state.sid = r.sid; viewCarrera(); };
    grid.appendChild(c);
  });
  $view.appendChild(grid);

  const d = await api(`/session/detail?sid=${encodeURIComponent(state.sid)}`);

  // podio hero
  $view.appendChild(el(`<div class="section-title">${d.info.gp} ${d.info.year}
    <small> · ${d.info.date} · ${d.info.n_laps} vueltas · ${d.info.circuit}</small></div>`));
  const podium = d.results.slice(0, 3);
  $view.appendChild(el(`<div class="podium-hero" style="margin-bottom:18px">${podium.map((p) => `
    <div class="pod" style="--tc:${p.color}"><span class="pos">P${p.pos}</span>
      <div class="code">${p.code}</div><div class="name">${p.name}</div>
      <div class="team">${p.team} · mejor vuelta ${p.best_lap}</div></div>`).join("")}</div>`));

  const two = el(`<div class="grid cols-2" style="margin-bottom:18px"></div>`);
  $view.appendChild(two);

  // ritmo (top 10 de la clasificación final)
  const top10 = new Set(d.results.slice(0, 10).map((r) => r.code));
  const pace = d.pace.filter((p) => top10.has(p.code));
  const allT = pace.flatMap((p) => p.times);
  const c1 = chartCard({
    title: "Ritmo vuelta a vuelta", sub: "top 10 final · sin vueltas de pits",
    summary: d.summaries.pace || "",
    tips: [
      "<b>¿Una línea consistentemente abajo?</b> → ese piloto tenía el mejor ritmo de carrera.",
      "<b>¿Escalones hacia abajo?</b> → goma nueva tras parar; compáralo con la estrategia.",
      "<b>¿Todos suben a la vez?</b> → coche de seguridad o lluvia.",
    ],
  });
  two.appendChild(c1.card);
  const tmin = Math.min(...allT), tmax = Math.max(...allT);
  const ticks = [];
  for (let t = Math.ceil(tmin); t <= tmax; t += Math.max(1, Math.round((tmax - tmin) / 5))) ticks.push(t);
  Plotly.newPlot(c1.plot, pace.map((p) => ({
    type: "scatter", mode: "lines", name: p.code,
    x: p.laps, y: p.times, line: { color: p.color, width: 1.7 },
    hovertemplate: `<b>${p.code}</b> · V%{x}<br>%{customdata}<extra></extra>`,
    customdata: p.times.map(fmtLap),
  })), baseLayout({
    height: 380, margin: { l: 64, r: 16, t: 16, b: 40 },
    xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } } },
    yaxis: { ...baseLayout().yaxis, tickvals: ticks, ticktext: ticks.map(fmtLap) },
    legend: { orientation: "h", y: -0.18, font: { size: 10.5 } },
  }), PLOTLY_CFG);

  // estrategia
  const compounds = [...new Set(d.strategy.flatMap((s) => s.stints.map((x) => x.compound)))];
  const c2 = chartCard({
    title: "Estrategia de neumáticos", sub: "orden = clasificación final",
    summary: d.summaries.strategy || "",
    tips: [
      "<b>¿Un bloque más largo que los vecinos?</b> → estiró el stint: posible overcut.",
      "<b>¿Paró antes que su rival directo?</b> → intento de undercut.",
      "<b>¿Verde o azul?</b> → intermedios/lluvia: carrera mojada.",
    ],
    legendHtml: `<div class="compound-legend">${compounds.map((c) =>
      `<span class="chip" style="--cc:${(d.strategy.flatMap((s) => s.stints).find((x) => x.compound === c) || {}).color}"><i></i>${c}</span>`).join("")}</div>`,
  });
  two.appendChild(c2.card);
  const order = d.strategy.map((s) => s.code);
  const bars = d.strategy.flatMap((s) => s.stints.map((st) => ({
    y: [s.code], base: [st.from - 1], x: [st.to - st.from + 1],
    type: "bar", orientation: "h", marker: { color: st.color, line: { color: "#11141b", width: 2 } },
    hovertemplate: `<b>${s.code}</b> · ${st.compound}<br>V${st.from}–V${st.to} (${st.laps} vueltas)<extra></extra>`,
    showlegend: false,
  })));
  Plotly.newPlot(c2.plot, bars, baseLayout({
    height: Math.max(340, order.length * 17 + 90), barmode: "stack", bargap: 0.35,
    margin: { l: 52, r: 16, t: 16, b: 40 },
    xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } } },
    yaxis: { ...baseLayout().yaxis, categoryorder: "array",
             categoryarray: [...order].reverse(), gridcolor: "rgba(0,0,0,0)", tickfont: { size: 10 } },
  }), PLOTLY_CFG);

  // tabla de resultados
  $view.appendChild(el(`<div class="section-title">Resultados
    ${d.summaries.results ? `<small> · ${d.summaries.results}</small>` : ""}</div>`));
  const rows = d.results.map((r) => {
    const dp = r.delta_pos;
    const cls = dp == null || dp === 0 ? "flat" : dp > 0 ? "up" : "down";
    const txt = dp == null ? "—" : dp > 0 ? `▲ ${dp}` : dp < 0 ? `▼ ${-dp}` : "=";
    return `<tr><td class="num">${r.pos}</td>
      <td>${drvChip(r.code, r.color, r.name)}</td><td>${r.team}</td>
      <td class="num">${r.grid ?? "—"}</td>
      <td class="num"><span class="delta-pos ${cls}">${txt}</span></td>
      <td class="num">${r.best_lap}</td><td class="num"><b>${r.points || ""}</b></td></tr>`;
  }).join("");
  $view.appendChild(el(`<div class="card table-wrap"><table>
    <thead><tr><th class="num">Pos</th><th>Piloto</th><th>Equipo</th>
    <th class="num">Salida</th><th class="num">±</th><th class="num">Mejor vuelta</th>
    <th class="num">Pts</th></tr></thead><tbody>${rows}</tbody></table></div>`));

  // speed trap
  const c3 = chartCard({
    title: "Speed trap", sub: "velocidad punta máxima de la carrera (km/h)",
    tips: ["<b>¿Alto aquí pero lento en la tabla?</b> → coche con poca carga: vuela en recta, sufre en curva."],
  });
  $view.appendChild(el(`<div style="height:18px"></div>`));
  $view.appendChild(c3.card);
  const st = [...d.speedtrap].reverse();
  Plotly.newPlot(c3.plot, [{
    type: "bar", orientation: "h",
    y: st.map((s) => s.code), x: st.map((s) => s.vmax),
    marker: { color: st.map((s) => s.color), line: { color: "#11141b", width: 2 } },
    text: st.map((s) => `${s.vmax.toFixed(0)} `), textposition: "outside",
    textfont: { color: "#c8cdd6", size: 11 },
    hovertemplate: "<b>%{y}</b> · %{x:.0f} km/h<extra></extra>",
  }], baseLayout({
    height: 320, margin: { l: 52, r: 46, t: 10, b: 36 },
    xaxis: { ...baseLayout().xaxis, range: [Math.min(...st.map((s) => s.vmax)) - 8,
             Math.max(...st.map((s) => s.vmax)) + 6] },
    yaxis: { ...baseLayout().yaxis, gridcolor: "rgba(0,0,0,0)" },
  }), PLOTLY_CFG);
}

/* ───────────────────────────── vista H2H */
async function viewH2H() {
  skeleton([70, 110, 420]);
  const drivers = await api("/drivers");
  $view.innerHTML = "";

  const codes = drivers.map((d) => d.code);
  if (!window._h2hA || !codes.includes(window._h2hA)) window._h2hA = codes[0];
  if (!window._h2hB || !codes.includes(window._h2hB) || window._h2hB === window._h2hA)
    window._h2hB = codes.find((c) => c !== window._h2hA);

  const opts = (sel) => drivers.map((d) =>
    `<option value="${d.code}" ${d.code === sel ? "selected" : ""}>${d.code} · ${d.name} (${d.gps} GPs)</option>`).join("");
  const controls = el(`<div class="card h2h-controls" style="margin-bottom:18px">
    <select id="selA">${opts(window._h2hA)}</select>
    <span class="vs">VS</span>
    <select id="selB">${opts(window._h2hB)}</select>
    <button class="swap" title="Intercambiar">⇄</button>
  </div>`);
  $view.appendChild(controls);
  controls.querySelector("#selA").onchange = (e) => { window._h2hA = e.target.value; viewH2H(); };
  controls.querySelector("#selB").onchange = (e) => { window._h2hB = e.target.value; viewH2H(); };
  controls.querySelector(".swap").onclick = () => {
    [window._h2hA, window._h2hB] = [window._h2hB, window._h2hA]; viewH2H();
  };

  if (window._h2hA === window._h2hB) {
    $view.appendChild(el(`<div class="empty">Elige dos pilotos distintos.</div>`));
    return;
  }
  const d = await api(`/h2h?a=${window._h2hA}&b=${window._h2hB}`);
  if (!d.deltas.length) {
    $view.appendChild(el(`<div class="empty">${d.summary}</div>`));
    return;
  }

  const mas = d.media < 0 ? d.a : d.b;
  $view.appendChild(el(`<div class="tiles" style="margin-bottom:18px">
    <div class="card tile" style="--tc:${d.a.color}"><div class="label">${d.a.code} más rápido en</div>
      <div class="value">${d.a.wins}</div><div class="hint">de ${d.deltas.length} GPs comunes</div></div>
    <div class="card tile" style="--tc:${mas.color}"><div class="label">Ventaja media</div>
      <div class="value">${Math.abs(d.media).toFixed(3)}s</div><div class="hint">a favor de ${mas.code}</div></div>
    <div class="card tile" style="--tc:${d.b.color}"><div class="label">${d.b.code} más rápido en</div>
      <div class="value">${d.b.wins}</div><div class="hint">de ${d.deltas.length} GPs comunes</div></div>
  </div>`));

  const { card, plot } = chartCard({
    title: `${d.a.code} vs ${d.b.code} · Δ mejor vuelta por GP`,
    sub: `abajo = ${d.a.code} más rápido (convención delta)`,
    summary: d.summary,
    tips: [
      `<b>¿Barra hacia abajo?</b> → ${d.a.code} hizo mejor vuelta ese GP (abajo = más rápido, como el delta del dashboard).`,
      "<b>¿Barras gigantes (&gt;1s)?</b> → lluvia, abandono temprano o safety car; no siempre es ritmo puro.",
      "<b>¿Patrón por tipo de circuito?</b> → mira si uno domina en urbanos y el otro en circuitos rápidos.",
    ],
  });
  $view.appendChild(card);
  Plotly.newPlot(plot, [{
    type: "bar", x: d.gps, y: d.deltas,
    marker: { color: d.deltas.map((v) => (v < 0 ? d.a.color : d.b.color)),
              line: { color: "#11141b", width: 2 } },
    text: d.deltas.map((v) => `${Math.abs(v).toFixed(2)}`), textposition: "outside",
    textfont: { size: 10, color: "#9aa0aa" },
    hovertemplate: "%{x}<br>Δ = %{y:+.3f}s (A − B)<extra></extra>",
  }], baseLayout({
    height: 430, margin: { l: 58, r: 16, t: 16, b: 86 },
    xaxis: { ...baseLayout().xaxis, tickangle: -38, tickfont: { size: 10 } },
    yaxis: { ...baseLayout().yaxis, title: { text: "SEGUNDOS (A − B)", font: { size: 10 } },
             zeroline: true, zerolinecolor: "rgba(255,255,255,.35)", zerolinewidth: 1 },
  }), PLOTLY_CFG);
}

/* ───────────────────────────── vista ANÁLISIS (telemetría bajo demanda) */
let _pollToken = 0;

async function viewAnalisis() {
  skeleton([70, 380]);
  const cat = await api("/telemetry/catalog");
  $view.innerHTML = "";

  if (!cat.length) {
    $view.appendChild(el(`<div class="empty">No hay sesiones con telemetría en la caché de FastF1.
      Carga una sesión en el laboratorio primero.</div>`));
    return;
  }
  const ready = cat.find((c) => c.status === "ready");
  if (!state.tsid || !cat.some((c) => c.sid === state.tsid))
    state.tsid = (ready || cat[cat.length - 1]).sid;

  const opts = cat.map((c) => `<option value="${c.sid}" ${c.sid === state.tsid ? "selected" : ""}>
      ${c.year} · ${c.gp} · ${c.session}${c.status === "ready" ? " ●" : ""}</option>`).join("");
  const controls = el(`<div class="card analysis-controls" style="margin-bottom:18px">
    <select id="selSes" style="max-width:430px">${opts}</select>
    <button class="btn-red" id="btnLoad">ANALIZAR</button>
    <span style="font-size:11.5px;color:var(--ink3)">Vuelta rápida por piloto ·
      la 1ª carga de una sesión tarda ~1 min, luego es instantáneo (●&nbsp;=&nbsp;ya en memoria)</span>
  </div>`);
  $view.appendChild(controls);
  const zone = el(`<div></div>`);
  $view.appendChild(zone);

  controls.querySelector("#selSes").onchange = (e) => { state.tsid = e.target.value; state.telSel = null; };
  controls.querySelector("#btnLoad").onclick = () => beginAnalysis(zone);

  const st = await api(`/telemetry/status?sid=${encodeURIComponent(state.tsid)}`);
  if (st.status === "ready") renderAnalysis(zone);
  else if (st.status === "loading") beginAnalysis(zone);
  else zone.appendChild(el(`<div class="empty">Elige una sesión y pulsa <b>ANALIZAR</b>.</div>`));
}

async function beginAnalysis(zone) {
  const sid = state.tsid;
  const [year, gp, ses] = sid.split("|");
  zone.innerHTML = "";
  zone.appendChild(el(`<div class="card loader-card"><div class="spinner"></div>
    <div><div class="t1">Cargando ${gp} ${year} · ${ses} desde FastF1…</div>
    <div class="t2">~1 minuto la primera vez; después queda en memoria y cambiar de piloto es instantáneo.</div></div></div>`));
  await fetch(`/api/telemetry/load?year=${year}&gp=${encodeURIComponent(gp)}&session=${encodeURIComponent(ses)}`,
              { method: "POST" });
  const token = ++_pollToken;
  const poll = async () => {
    if (token !== _pollToken || !location.hash.includes("analisis")) return;
    const st = await api(`/telemetry/status?sid=${encodeURIComponent(sid)}`);
    if (st.status === "ready") return renderAnalysis(zone);
    if (st.status === "error") {
      zone.innerHTML = "";
      zone.appendChild(el(`<div class="empty">No se pudo cargar la sesión: ${st.error}</div>`));
      return;
    }
    setTimeout(poll, 2500);
  };
  setTimeout(poll, 2500);
}

async function renderAnalysis(zone) {
  zone.innerHTML = "";
  zone.appendChild(el(`<div class="skeleton-block" style="height:380px"></div>`));
  const q = state.telSel && state.telSel.length ? `&drivers=${state.telSel.join(",")}` : "";
  const d = await api(`/telemetry/analysis?sid=${encodeURIComponent(state.tsid)}${q}`);
  state.telSel = d.drivers.map((x) => x.code);
  zone.innerHTML = "";

  // chips de pilotos (el 1º seleccionado es la referencia del delta)
  const chipsCard = el(`<div class="card" style="margin-bottom:18px">
    <div style="font-size:10px;letter-spacing:2px;color:var(--ink3);font-weight:700;margin-bottom:10px">
      PILOTOS · el primero es la referencia del delta y del mapa</div>
    <div class="drv-chips"></div></div>`);
  const chipsWrap = chipsCard.querySelector(".drv-chips");
  d.available.forEach((a) => {
    const on = state.telSel.includes(a.code);
    const isRef = a.code === d.ref;
    const chip = el(`<span class="drv-chip ${on ? "on" : ""}" style="--cc:${a.color}"
      title="${a.name} · ${a.team}"><i></i>${a.code}${isRef ? ' <span class="ref-tag">REF</span>' : ""}</span>`);
    chip.onclick = () => {
      let sel = [...state.telSel];
      if (sel.includes(a.code)) { if (sel.length > 1) sel = sel.filter((c) => c !== a.code); }
      else if (sel.length < 5) sel.push(a.code);
      state.telSel = sel;
      renderAnalysis(zone);
    };
    chipsWrap.appendChild(chip);
  });
  zone.appendChild(chipsCard);

  const cornerAxis = {
    tickvals: d.corners.map((c) => c.d), ticktext: d.corners.map((c) => String(c.n)),
    tickfont: { size: 9.5, color: "#6b7280" }, title: { text: "CURVA", font: { size: 10 } },
  };
  const sectorShapes = (d.cuts || []).map((x) => ({
    type: "line", x0: x, x1: x, yref: "paper", y0: 0, y1: 1,
    line: { color: "rgba(255,255,255,.22)", width: 1 },
  }));
  const lapLabels = d.drivers.map((x) => `${x.code} ${x.lap_label} (V${x.lap_number})`).join(" · ");

  // fila 1: mapa de dominancia + G-G
  const row1 = el(`<div class="grid cols-2" style="margin-bottom:18px"></div>`);
  zone.appendChild(row1);

  const cMap = chartCard({
    title: "Mapa de dominancia", sub: "color = quién gana cada mini-sector",
    summary: d.summaries.map || "",
    tips: ["<b>¿Un color domina las rectas y otro las curvas?</b> → configuraciones distintas: menos ala vs más carga.",
           "Los números son las curvas oficiales del circuito."],
  });
  row1.appendChild(cMap.card);
  const segTraces = d.segments.map((s) => ({
    type: "scatter", mode: "lines", x: s.x, y: s.y, showlegend: false,
    line: { color: s.color, width: 5 }, hoverinfo: "skip",
  }));
  const legendTraces = d.drivers.map((x) => ({
    type: "scatter", mode: "lines", x: [null], y: [null], name: x.code,
    line: { color: x.color, width: 5 },
  }));
  Plotly.newPlot(cMap.plot, [...segTraces, ...legendTraces], baseLayout({
    height: 430, margin: { l: 10, r: 10, t: 10, b: 10 },
    xaxis: { visible: false }, yaxis: { visible: false, scaleanchor: "x" },
    legend: { orientation: "h", y: -0.02, x: 0.5, xanchor: "center" },
    annotations: d.corners.map((c) => ({
      x: c.x, y: c.y, text: String(c.n), showarrow: false,
      font: { size: 10, color: "#8a919e" },
    })),
  }), PLOTLY_CFG);

  const cGG = chartCard({
    title: "G-G · envolvente de agarre", sub: "cada punto = una muestra de la vuelta",
    tips: ["<b>¿Nube ancha a los lados?</b> → mucho paso por curva (G lateral).",
           "<b>¿Puntos muy abajo?</b> → frenadas fuertes (G longitudinal negativa).",
           "El borde de la nube es el límite de agarre que ese coche alcanzó."],
  });
  row1.appendChild(cGG.card);
  Plotly.newPlot(cGG.plot, d.drivers.map((x) => ({
    type: "scatter", mode: "markers", name: x.code, x: x.glat, y: x.glong,
    marker: { color: x.color, size: 3.5, opacity: 0.45 },
    hovertemplate: `<b>${x.code}</b><br>G lat: %{x:.2f} · G long: %{y:.2f}<extra></extra>`,
  })), baseLayout({
    height: 430, margin: { l: 52, r: 14, t: 12, b: 46 },
    xaxis: { ...baseLayout().xaxis, title: { text: "G LATERAL", font: { size: 10 } },
             showgrid: true, gridcolor: "rgba(255,255,255,.06)", griddash: "dot" },
    yaxis: { ...baseLayout().yaxis, title: { text: "G LONGITUDINAL", font: { size: 10 } } },
    legend: { orientation: "h", y: -0.14, x: 0.5, xanchor: "center" },
  }), PLOTLY_CFG);

  // VELOCIDAD
  const cVel = chartCard({
    title: "Velocidad", sub: lapLabels, summary: d.summaries.speed || "",
    tips: ["<b>¿Una línea llega más alto en recta?</b> → menos ala o mejor tracción a la salida de la curva previa.",
           "<b>¿Valle más estrecho en una curva?</b> → frena más tarde y suelta antes: ahí gana el tiempo.",
           "Las líneas verticales tenues separan los sectores S1/S2/S3."],
  });
  zone.appendChild(cVel.card);
  Plotly.newPlot(cVel.plot, d.drivers.map((x) => ({
    type: "scatter", mode: "lines", name: x.code, x: x.d, y: x.speed,
    line: { color: x.color, width: 1.9 },
    hovertemplate: `<b>${x.code}</b> · %{y:.0f} km/h<extra></extra>`,
  })), baseLayout({
    height: 400, hovermode: "x unified", shapes: sectorShapes,
    margin: { l: 56, r: 14, t: 14, b: 48 },
    xaxis: { ...baseLayout().xaxis, ...cornerAxis },
    yaxis: { ...baseLayout().yaxis, title: { text: "KM/H", font: { size: 10 } } },
    legend: { orientation: "h", y: 1.08, x: 1, xanchor: "right" },
  }), PLOTLY_CFG);
  zone.appendChild(el(`<div style="height:18px"></div>`));

  // DELTA (si hay 2+ pilotos)
  const conDelta = d.drivers.filter((x) => x.delta);
  if (conDelta.length) {
    const cDelta = chartCard({
      title: `Delta vs ${d.ref}`, sub: "abajo = más rápido que la referencia",
      summary: d.summaries.delta || "",
      tips: [`<b>¿La línea baja?</b> → ese piloto le está GANANDO tiempo a ${d.ref} en ese tramo.`,
             "<b>¿Sube de golpe en una curva?</b> → ahí lo pierde: compara la frenada en esa zona.",
             "El valor al final de la vuelta es la diferencia total de la vuelta rápida."],
    });
    zone.appendChild(cDelta.card);
    Plotly.newPlot(cDelta.plot, conDelta.map((x) => ({
      type: "scatter", mode: "lines", name: `Δ ${x.code}`, x: x.delta_d, y: x.delta,
      line: { color: x.color, width: 2 },
      hovertemplate: `<b>${x.code}</b> · Δ %{y:+.3f}s<extra></extra>`,
    })), baseLayout({
      height: 340, hovermode: "x unified", shapes: sectorShapes,
      margin: { l: 56, r: 14, t: 14, b: 48 },
      xaxis: { ...baseLayout().xaxis, ...cornerAxis },
      yaxis: { ...baseLayout().yaxis, title: { text: `SEGUNDOS VS ${d.ref}`, font: { size: 10 } },
               zeroline: true, zerolinecolor: "rgba(255,45,45,.5)", zerolinewidth: 1.5 },
      legend: { orientation: "h", y: 1.1, x: 1, xanchor: "right" },
    }), PLOTLY_CFG);
    zone.appendChild(el(`<div style="height:18px"></div>`));
  }

  // fila: acelerador + freno
  const row2 = el(`<div class="grid cols-2" style="margin-bottom:18px"></div>`);
  zone.appendChild(row2);
  const mkChannel = (title, key, ytitle, tips) => {
    const c = chartCard({ title, sub: "vs distancia", tips });
    row2.appendChild(c.card);
    Plotly.newPlot(c.plot, d.drivers.map((x) => ({
      type: "scatter", mode: "lines", name: x.code, x: x.d, y: x[key],
      line: { color: x.color, width: 1.6 },
      hovertemplate: `<b>${x.code}</b> · %{y:.0f}${key === "gear" ? "ª" : "%"}<extra></extra>`,
    })), baseLayout({
      height: 300, hovermode: "x unified",
      margin: { l: 46, r: 12, t: 12, b: 44 },
      xaxis: { ...baseLayout().xaxis, ...cornerAxis },
      yaxis: { ...baseLayout().yaxis, title: { text: ytitle, font: { size: 10 } } },
      legend: { orientation: "h", y: 1.12, x: 1, xanchor: "right" },
    }), PLOTLY_CFG);
  };
  mkChannel("Acelerador", "throttle", "% GAS",
    ["<b>¿Pisa a fondo antes que el otro a la salida de una curva?</b> → mejor tracción o más confianza; ahí nace la ventaja de la recta siguiente."]);
  mkChannel("Freno", "brake", "% FRENO",
    ["<b>¿Su frenada empieza más tarde (más a la derecha)?</b> → frena más profundo: típico punto de adelantamiento.",
     "<b>¿Dos picos seguidos?</b> → soltó y volvió a frenar (corrección o chicane)."]);

  // fila: marchas + fases
  const row3 = el(`<div class="grid cols-2"></div>`);
  zone.appendChild(row3);
  const cGear = chartCard({
    title: "Marchas", sub: "vs distancia",
    tips: ["<b>¿Cambia una marcha menos en la misma curva?</b> → relación más larga o toma la curva con más velocidad."],
  });
  row3.appendChild(cGear.card);
  Plotly.newPlot(cGear.plot, d.drivers.map((x) => ({
    type: "scatter", mode: "lines", name: x.code, x: x.d, y: x.gear,
    line: { color: x.color, width: 1.6, shape: "hv" },
    hovertemplate: `<b>${x.code}</b> · %{y}ª<extra></extra>`,
  })), baseLayout({
    height: 300, hovermode: "x unified",
    margin: { l: 46, r: 12, t: 12, b: 44 },
    xaxis: { ...baseLayout().xaxis, ...cornerAxis },
    yaxis: { ...baseLayout().yaxis, title: { text: "MARCHA", font: { size: 10 } }, dtick: 1 },
    legend: { orientation: "h", y: 1.12, x: 1, xanchor: "right" },
  }), PLOTLY_CFG);

  const cPh = chartCard({
    title: "Fases de conducción", sub: "% del tiempo de la vuelta",
    summary: d.summaries.phases || "",
    tips: ["<b>¿Más % a fondo?</b> → o el coche permite pisar antes, o el circuito se lo pide y el motor manda.",
           "<b>¿Más % en curva que el rival?</b> → pasa más tiempo gestionando el paso por curva: ahí se decide su vuelta."],
  });
  row3.appendChild(cPh.card);
  const phSeries = [
    { key: "fondo", name: "A fondo", color: "#2ECC71" },
    { key: "frenada", name: "Frenada", color: "#FF5252" },
    { key: "curva", name: "En curva", color: "#FFC400" },
  ];
  Plotly.newPlot(cPh.plot, phSeries.map((s) => ({
    type: "bar", orientation: "h", name: s.name,
    y: d.drivers.map((x) => x.code).reverse(),
    x: d.drivers.map((x) => x.phases[s.key]).reverse(),
    marker: { color: s.color, line: { color: "#11141b", width: 2 } },
    text: d.drivers.map((x) => `${x.phases[s.key].toFixed(0)}%`).reverse(),
    textposition: "inside", textfont: { size: 10.5, color: "#0b0d12" },
    hovertemplate: `%{y} · ${s.name}: %{x:.1f}%<extra></extra>`,
  })), baseLayout({
    height: 300, barmode: "stack",
    margin: { l: 46, r: 12, t: 12, b: 36 },
    xaxis: { ...baseLayout().xaxis, ticksuffix: "%" },
    yaxis: { ...baseLayout().yaxis, gridcolor: "rgba(0,0,0,0)" },
    legend: { orientation: "h", y: 1.14, x: 0.5, xanchor: "center" },
  }), PLOTLY_CFG);
}

/* ───────────────────────────── router */
const VIEWS = { temporada: viewTemporada, carrera: viewCarrera, h2h: viewH2H,
                analisis: viewAnalisis };

async function route() {
  const name = (location.hash.replace("#/", "") || "temporada").split("?")[0];
  const fn = VIEWS[name] || viewTemporada;
  document.querySelectorAll(".nav a").forEach((a) =>
    a.classList.toggle("active", a.dataset.view === name));
  try {
    await fn();
  } catch (e) {
    $view.innerHTML = "";
    $view.appendChild(el(`<div class="empty">No se pudo cargar: ${e.message}.<br>
      ¿Existe la base? Corre <code>python ingest.py --cached</code> y recarga.</div>`));
  }
}

(async function init() {
  try {
    const meta = await api("/meta");
    state.seasons = meta.seasons;
    state.year = meta.seasons.length ? meta.seasons[0].year : null;
  } catch (e) { /* la ruta mostrará el error */ }
  window.addEventListener("hashchange", route);
  route();
})();
