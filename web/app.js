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

/* ───────────────────────────── router */
const VIEWS = { temporada: viewTemporada, carrera: viewCarrera, h2h: viewH2H };

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
