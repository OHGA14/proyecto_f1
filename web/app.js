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

  // bandas de SC/VSC compartidas por lap chart y gap
  const scShapes = (d.sc_ranges || []).map(([l0, l1]) => ({
    type: "rect", xref: "x", x0: l0 - 0.5, x1: l1 + 0.5, yref: "paper", y0: 0, y1: 1,
    fillcolor: "rgba(255,255,255,.07)", line: { width: 0 }, layer: "below",
  }));

  // LAP CHART: posición vuelta a vuelta
  if (d.laps_chart && d.laps_chart.length) {
    const cLap = chartCard({
      title: "Lap chart · posición vuelta a vuelta", sub: "bandas grises = SC/VSC",
      summary: d.summaries.lapchart || "",
      tips: ["<b>¿Una línea cae de golpe varias posiciones?</b> → pit stop; mira si las recupera (estrategia buena) o no.",
             "<b>¿Cruces constantes entre dos líneas?</b> → batalla en pista real, vuelta a vuelta.",
             "<b>¿Saltos durante una banda gris?</b> → posiciones ganadas/perdidas parando bajo coche de seguridad (parada 'gratis')."],
    });
    $view.appendChild(cLap.card);
    Plotly.newPlot(cLap.plot, d.laps_chart.map((x) => ({
      type: "scatter", mode: "lines", name: x.code, x: x.laps, y: x.pos,
      line: { color: x.color, width: 1.8 },
      hovertemplate: `<b>${x.code}</b> · V%{x} · P%{y}<extra></extra>`,
    })), baseLayout({
      height: 620, shapes: scShapes,
      margin: { l: 46, r: 14, t: 14, b: 44 },
      xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } } },
      yaxis: { ...baseLayout().yaxis, title: { text: "POSICIÓN", font: { size: 10 } },
               autorange: "reversed", dtick: 2 },
      legend: { orientation: "h", y: -0.1, font: { size: 10.5 } },
    }), PLOTLY_CFG);
    $view.appendChild(el(`<div style="height:18px"></div>`));
  }

  // GAP AL LÍDER
  if (d.gaps && d.gaps.length) {
    const flat = d.gaps.flatMap((g) => g.gap).sort((a, b) => a - b);
    const cap = flat[Math.floor(flat.length * 0.93)] || 60;
    const cGap = chartCard({
      title: "Gap al líder", sub: "segundos detrás del primero, vuelta a vuelta",
      summary: d.summaries.gaps || "",
      tips: ["<b>¿Línea plana?</b> → mantiene el ritmo del líder; si sube, lo está perdiendo.",
             "<b>¿Todas las líneas se comprimen de golpe?</b> → coche de seguridad: el pelotón se reagrupa.",
             "<b>¿Escalón hacia arriba de ~20s?</b> → pit stop de ese piloto."],
    });
    $view.appendChild(cGap.card);
    Plotly.newPlot(cGap.plot, d.gaps.map((x) => ({
      type: "scatter", mode: "lines", name: x.code, x: x.laps, y: x.gap,
      line: { color: x.color, width: 1.8 },
      hovertemplate: `<b>${x.code}</b> · V%{x}<br>+%{y:.1f}s del líder<extra></extra>`,
    })), baseLayout({
      height: 560, shapes: scShapes,
      margin: { l: 52, r: 14, t: 14, b: 44 },
      xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } } },
      yaxis: { ...baseLayout().yaxis, title: { text: "SEGUNDOS TRAS EL LÍDER", font: { size: 10 } },
               range: [cap, -2] },
      legend: { orientation: "h", y: -0.1, font: { size: 10.5 } },
    }), PLOTLY_CFG);
    $view.appendChild(el(`<div style="height:18px"></div>`));
  }

  // MEJORES SECTORES + VUELTA IDEAL
  if (d.sectors && d.sectors.rows.length) {
    $view.appendChild(el(`<div class="section-title">Mejores sectores · vuelta ideal
      <small> · ${d.summaries.sectors || ""}</small></div>`));
    const fmtS = (row, k) => `<td class="num ${row.best.includes(k) ? "sector-best" : ""}">${row[k].toFixed(3)}</td>`;
    const secRows = d.sectors.rows.map((r) => `<tr>
      <td>${drvChip(r.code, r.color)}</td>
      ${fmtS(r, "s1")}${fmtS(r, "s2")}${fmtS(r, "s3")}
      <td class="num"><b>${r.ideal}</b></td></tr>`).join("");
    $view.appendChild(el(`<div class="card table-wrap" style="margin-bottom:18px"><table>
      <thead><tr><th>Piloto</th><th class="num">S1</th><th class="num">S2</th>
      <th class="num">S3</th><th class="num">Vuelta ideal</th></tr></thead>
      <tbody>${secRows}</tbody></table>
      <div class="chart-summary" style="margin:10px 0 4px">En <span class="sector-best">morado</span>,
      el mejor sector de todo el campo. La vuelta ideal junta los 3 mejores sectores de cada piloto:
      si es mucho más rápida que su vuelta real, dejó tiempo en la mesa.</div></div>`));
  }

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
  const modes = el(`<div class="pills" style="margin-bottom:14px">
    <button class="pill ${state.telMode !== "vueltas" ? "active" : ""}">COMPARAR PILOTOS</button>
    <button class="pill ${state.telMode === "vueltas" ? "active" : ""}">2 VUELTAS DE UN PILOTO</button>
  </div>`);
  const [bp, bv] = modes.querySelectorAll("button");
  bp.onclick = () => { state.telMode = "pilotos"; renderAnalysis(zone); };
  bv.onclick = () => { state.telMode = "vueltas"; renderAnalysis(zone); };
  zone.appendChild(modes);
  const sub = el(`<div></div>`);
  zone.appendChild(sub);
  if (state.telMode === "vueltas") return renderVsLaps(sub);
  return renderPilotos(sub);
}

async function renderPilotos(zone) {
  zone.innerHTML = "";
  zone.appendChild(el(`<div class="skeleton-block" style="height:380px"></div>`));
  const q = state.telSel && state.telSel.length ? `&drivers=${state.telSel.join(",")}` : "";
  const [d, ss] = await Promise.all([
    api(`/telemetry/analysis?sid=${encodeURIComponent(state.tsid)}${q}`),
    api(`/telemetry/sessionstats?sid=${encodeURIComponent(state.tsid)}`),
  ]);
  state.telSel = d.drivers.map((x) => x.code);
  zone.innerHTML = "";

  const secNav = el(`<div class="pills" style="margin-bottom:14px">
    <button class="pill">↓ RITMO DE SESIÓN</button>
    <button class="pill">↓ TELEMETRÍA</button>
    <button class="pill">↓ FÍSICA</button>
    <button class="pill">↓ REPLAY</button></div>`);
  const [b1, b2, b3, b4] = secNav.querySelectorAll("button");
  b1.onclick = () => document.getElementById("sec-ritmo")?.scrollIntoView({ behavior: "smooth" });
  b2.onclick = () => document.getElementById("sec-tel")?.scrollIntoView({ behavior: "smooth" });
  b3.onclick = () => document.getElementById("sec-fis")?.scrollIntoView({ behavior: "smooth" });
  b4.onclick = () => document.getElementById("sec-replay")?.scrollIntoView({ behavior: "smooth" });
  zone.appendChild(secNav);

  const chipsCard = el(`<div class="card" style="margin-bottom:18px">
    <div style="font-size:10px;letter-spacing:2px;color:var(--ink3);font-weight:700;margin-bottom:10px">
      PILOTOS · el primero es la referencia del delta y del mapa</div>
    <div class="drv-chips"></div></div>`);
  const chipsWrap = chipsCard.querySelector(".drv-chips");
  (d.available || []).forEach((a) => {
    const on = state.telSel.includes(a.code);
    const isRef = a.code === d.ref;
    const chip = el(`<span class="drv-chip ${on ? "on" : ""}" style="--cc:${a.color}"
      title="${a.name} · ${a.team}"><i></i>${a.code}${isRef ? ' <span class="ref-tag">REF</span>' : ""}</span>`);
    chip.onclick = () => {
      let sel = [...state.telSel];
      if (sel.includes(a.code)) { if (sel.length > 1) sel = sel.filter((c) => c !== a.code); }
      else if (sel.length < 5) sel.push(a.code);
      state.telSel = sel;
      renderPilotos(zone);
    };
    chipsWrap.appendChild(chip);
  });
  zone.appendChild(chipsCard);
  drawSessionStats(zone, ss);
  drawTelCharts(zone, d);
}

async function renderVsLaps(zone) {
  zone.innerHTML = "";
  zone.appendChild(el(`<div class="skeleton-block" style="height:110px"></div>`));
  const drivers = await api(`/telemetry/drivers?sid=${encodeURIComponent(state.tsid)}`);
  if (!state.vsDriver || !drivers.some((x) => x.code === state.vsDriver))
    state.vsDriver = drivers[0].code;
  const lapsList = await api(`/telemetry/laps?sid=${encodeURIComponent(state.tsid)}&driver=${state.vsDriver}`);
  if (lapsList.length < 2) {
    zone.innerHTML = "";
    zone.appendChild(el(`<div class="empty">${state.vsDriver} no tiene suficientes vueltas válidas.</div>`));
    return;
  }
  const rapida = lapsList.find((l) => l.fastest) || lapsList[0];
  if (!state.vsA || !lapsList.some((l) => l.lap === state.vsA)) state.vsA = rapida.lap;
  if (!state.vsB || !lapsList.some((l) => l.lap === state.vsB) || state.vsB === state.vsA) {
    const otras = lapsList.filter((l) => l.lap !== state.vsA)
                          .sort((a, b) => a.time_s - b.time_s);
    state.vsB = otras[0].lap;
  }
  zone.innerHTML = "";
  const opts = (sel) => lapsList.map((l) =>
    `<option value="${l.lap}" ${l.lap === sel ? "selected" : ""}>${l.label}${l.fastest ? " ★" : ""}</option>`).join("");
  const controls = el(`<div class="card h2h-controls" style="margin-bottom:18px">
    <select id="vsDrv">${drivers.map((x) =>
      `<option value="${x.code}" ${x.code === state.vsDriver ? "selected" : ""}>${x.code} · ${x.name}</option>`).join("")}</select>
    <select id="vsA">${opts(state.vsA)}</select>
    <span class="vs">VS</span>
    <select id="vsB">${opts(state.vsB)}</select>
    <span style="font-size:11.5px;color:var(--ink3)">ideal para qualy: primer intento vs
      definitivo · vuelta A = color del piloto, B = blanco · ★ = su vuelta rápida</span>
  </div>`);
  zone.appendChild(controls);
  controls.querySelector("#vsDrv").onchange = (e) => {
    state.vsDriver = e.target.value; state.vsA = null; state.vsB = null; renderVsLaps(zone);
  };
  controls.querySelector("#vsA").onchange = (e) => { state.vsA = +e.target.value; renderVsLaps(zone); };
  controls.querySelector("#vsB").onchange = (e) => { state.vsB = +e.target.value; renderVsLaps(zone); };
  if (state.vsA === state.vsB) {
    zone.appendChild(el(`<div class="empty">Elige dos vueltas distintas.</div>`));
    return;
  }
  const chartsZone = el(`<div></div>`);
  zone.appendChild(chartsZone);
  chartsZone.appendChild(el(`<div class="skeleton-block" style="height:380px"></div>`));
  const d = await api(`/telemetry/vslaps?sid=${encodeURIComponent(state.tsid)}` +
                      `&driver=${state.vsDriver}&lap_a=${state.vsA}&lap_b=${state.vsB}`);
  chartsZone.innerHTML = "";
  drawTelCharts(chartsZone, d);
}

function drawTelCharts(zone, d) {
  const cornerAxis = {
    tickvals: d.corners.map((c) => c.d), ticktext: d.corners.map((c) => String(c.n)),
    tickfont: { size: 9.5, color: "#6b7280" }, title: { text: "CURVA", font: { size: 10 } },
  };
  const sectorShapes = (d.cuts || []).map((x) => ({
    type: "line", x0: x, x1: x, yref: "paper", y0: 0, y1: 1,
    line: { color: "rgba(255,255,255,.22)", width: 1 },
  }));
  const lapLabels = d.drivers.map((x) => `${x.code} ${x.lap_label} (V${x.lap_number})`).join(" · ");

  zone.appendChild(el(`<div class="section-title" id="sec-tel">Telemetría de vuelta</div>`));
  if (d.dtw && d.dtw.length) {
    zone.appendChild(el(`<div class="card" style="margin-bottom:18px">
      <div class="chart-head" style="padding:0 0 4px"><h2>Similitud DTW · ¿qué tan parecidas son las vueltas?</h2>
        <span class="sub">vs ${d.ref} · menor = más parecida</span></div>
      ${d.dtw.map((x) => `<div class="chart-summary" style="margin:8px 0 0">
        <b>${x.code}</b>: difiere <b>${x.mean_kmh} km/h</b> de media → vueltas ${x.label}.
        Máxima diferencia en la curva ${x.corner} (~${x.at_m} m).</div>`).join("")}
      <details class="chart-guide" style="margin:8px 0 0"><summary>¿Cómo leer esto?</summary><ul>
        <li>El DTW alinea las dos curvas de velocidad permitiendo pequeños desfases (frenar unos metros antes o después) y mide cuánto difieren DE VERDAD.</li>
        <li><b>¿"casi idénticas" pero el delta final es grande?</b> → mismo estilo, distinta ejecución: la diferencia está en UNA curva concreta — la que te señala aquí.</li>
      </ul></details></div>`));
  }

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
    height: 560, margin: { l: 10, r: 10, t: 10, b: 10 },
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
    height: 560, margin: { l: 52, r: 14, t: 12, b: 46 },
    xaxis: { ...baseLayout().xaxis, title: { text: "G LATERAL", font: { size: 10 } },
             showgrid: true, gridcolor: "rgba(255,255,255,.06)", griddash: "dot" },
    yaxis: { ...baseLayout().yaxis, title: { text: "G LONGITUDINAL", font: { size: 10 } } },
    legend: { orientation: "h", y: -0.14, x: 0.5, xanchor: "center" },
  }), PLOTLY_CFG);

  if (d.micro) {
    const m = d.micro;
    const colorDe = (k) => (d.drivers.find((x) => x.code === k) || {}).color || "#ddd";
    const lbls = `<div class="ms-col-lbl"><div class="ms-head">&nbsp;</div>${m.keys.map((k) =>
      `<div class="ms-lbl" style="color:${colorDe(k)}">${k}</div>`).join("")}</div>`;
    const secs = m.sectors.map((sc) => {
      const rows = m.keys.map((k) => `<div class="ms-row">${sc.cells.map((c) =>
        `<span class="ms-cell ms-${c.colors[k]}" title="${k}: +${c.gaps[k].toFixed(3)}s vs el mejor del tramo"></span>`).join("")}</div>`).join("");
      return `<div class="ms-sector"><div class="ms-head"><b>${sc.label}</b>
        <span>gana ${sc.winner} +${sc.margin.toFixed(3)}s</span></div>${rows}</div>`;
    }).join("");
    zone.appendChild(el(`<div class="card chart-card" style="margin-bottom:18px">
      <div class="chart-head"><h2>Micro-sectores</h2>
        <span class="sub">morado = más rápido · verde = empate (&lt;0.02s) · amarillo = más lento</span></div>
      <div style="padding:8px 18px 2px"><div class="ms-wrap">${lbls}${secs}</div></div>
      ${d.summaries.micro ? `<div class="chart-summary">${d.summaries.micro}</div>` : ""}
      <details class="chart-guide"><summary>¿Cómo leer esta gráfica?</summary><ul>
        <li><b>¿Una fila casi toda morada en un sector?</b> → ahí vive su ventaja; ve a ese tramo en la gráfica de velocidad.</li>
        <li><b>¿Mucho verde?</b> → van empatados; la vuelta se decide en los pocos tramos con color.</li>
        <li>Pasa el cursor sobre una celda para ver el tiempo exacto perdido en ese tramo.</li>
      </ul></details></div>`));
  }

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
    height: 580, hovermode: "x unified", shapes: sectorShapes,
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
      height: 480, hovermode: "x unified", shapes: sectorShapes,
      margin: { l: 56, r: 14, t: 14, b: 48 },
      xaxis: { ...baseLayout().xaxis, ...cornerAxis },
      yaxis: { ...baseLayout().yaxis, title: { text: `SEGUNDOS VS ${d.ref}`, font: { size: 10 } },
               zeroline: true, zerolinecolor: "rgba(255,45,45,.5)", zerolinewidth: 1.5 },
      legend: { orientation: "h", y: 1.1, x: 1, xanchor: "right" },
    }), PLOTLY_CFG);
    zone.appendChild(el(`<div style="height:18px"></div>`));
  }

  // canales a ANCHO COMPLETO (aquí se ven las diferencias finas)
  const mkChannel = (title, key, ytitle, tips, summary) => {
    const c = chartCard({ title, sub: "vs distancia · " + lapLabels, tips, summary });
    zone.appendChild(c.card);
    zone.appendChild(el(`<div style="height:18px"></div>`));
    Plotly.newPlot(c.plot, d.drivers.map((x) => ({
      type: "scatter", mode: "lines", name: x.code, x: x.d, y: x[key],
      line: { color: x.color, width: 1.6 },
      hovertemplate: `<b>${x.code}</b> · %{y:.0f}${key === "gear" ? "ª" : "%"}<extra></extra>`,
    })), baseLayout({
      height: 420, hovermode: "x unified", shapes: sectorShapes,
      margin: { l: 50, r: 12, t: 12, b: 44 },
      xaxis: { ...baseLayout().xaxis, ...cornerAxis },
      yaxis: { ...baseLayout().yaxis, title: { text: ytitle, font: { size: 10 } } },
      legend: { orientation: "h", y: 1.08, x: 1, xanchor: "right" },
    }), PLOTLY_CFG);
  };
  mkChannel("Acelerador", "throttle", "% GAS",
    ["<b>¿Pisa a fondo antes que el otro a la salida de una curva?</b> → mejor tracción o más confianza; ahí nace la ventaja de la recta siguiente."],
    d.summaries.throttle || "");
  mkChannel("Freno", "brake", "% FRENO",
    ["<b>¿Su frenada empieza más tarde (más a la derecha)?</b> → frena más profundo: típico punto de adelantamiento.",
     "<b>¿Dos picos seguidos?</b> → soltó y volvió a frenar (corrección o chicane)."],
    d.summaries.brake || "");

  // marchas y fases a ancho completo
  const cGear = chartCard({
    title: "Marchas", sub: "vs distancia",
    tips: ["<b>¿Cambia una marcha menos en la misma curva?</b> → relación más larga o toma la curva con más velocidad."],
  });
  zone.appendChild(cGear.card);
  zone.appendChild(el(`<div style="height:18px"></div>`));
  Plotly.newPlot(cGear.plot, d.drivers.map((x) => ({
    type: "scatter", mode: "lines", name: x.code, x: x.d, y: x.gear,
    line: { color: x.color, width: 1.6, shape: "hv" },
    hovertemplate: `<b>${x.code}</b> · %{y}ª<extra></extra>`,
  })), baseLayout({
    height: 400, hovermode: "x unified", shapes: sectorShapes,
    margin: { l: 50, r: 12, t: 12, b: 44 },
    xaxis: { ...baseLayout().xaxis, ...cornerAxis },
    yaxis: { ...baseLayout().yaxis, title: { text: "MARCHA", font: { size: 10 } }, dtick: 1 },
    legend: { orientation: "h", y: 1.08, x: 1, xanchor: "right" },
  }), PLOTLY_CFG);

  zone.appendChild(el(`<div class="section-title" id="sec-fis">Física del coche</div>`));

  // FUERZA G LONGITUDINAL vs distancia
  const cGl = chartCard({
    title: "Fuerza G longitudinal", sub: "negativo = frenada · " + lapLabels,
    tips: ["<b>¿Picos hacia abajo de -4/-5G?</b> → las grandes frenadas del circuito; compara qué tan tarde y fuerte frena cada uno.",
           "<b>¿Meseta positiva suave?</b> → tracción a la salida: ahí se nota el motor y el agarre trasero."],
  });
  zone.appendChild(cGl.card);
  zone.appendChild(el(`<div style="height:18px"></div>`));
  Plotly.newPlot(cGl.plot, d.drivers.map((x) => ({
    type: "scatter", mode: "lines", name: x.code, x: x.d, y: x.glong,
    line: { color: x.color, width: 1.6 },
    hovertemplate: `<b>${x.code}</b> · %{y:.2f} G<extra></extra>`,
  })), baseLayout({
    height: 400, hovermode: "x unified", shapes: sectorShapes,
    margin: { l: 50, r: 12, t: 12, b: 44 },
    xaxis: { ...baseLayout().xaxis, ...cornerAxis },
    yaxis: { ...baseLayout().yaxis, title: { text: "G LONGITUDINAL", font: { size: 10 } },
             zeroline: true, zerolinecolor: "rgba(255,255,255,.25)" },
    legend: { orientation: "h", y: 1.08, x: 1, xanchor: "right" },
  }), PLOTLY_CFG);

  // DESPLIEGUE DE ENERGÍA (ERS / clipping): aceleración a fondo vs velocidad
  const cErs = chartCard({
    title: "Despliegue de energía (ERS)", sub: "solo puntos a fondo, en recta y sin freno",
    tips: ["<b>¿La nube cae a cero antes de la velocidad punta?</b> → clipping: la batería dejó de empujar al final de la recta.",
           "<b>¿Una curva de tendencia más alta a media velocidad?</b> → ese coche despliega más energía saliendo de curvas.",
           "Cada punto = una muestra con gas ≥95%, sin freno y sin carga lateral."],
  });
  zone.appendChild(cErs.card);
  zone.appendChild(el(`<div style="height:18px"></div>`));
  const ersTraces = [];
  d.drivers.forEach((x) => {
    const xs = [], ys = [];
    for (let i = 0; i < x.d.length; i++) {
      if (x.throttle[i] >= 95 && x.brake[i] < 5 && Math.abs(x.glat[i]) < 0.5) {
        xs.push(x.speed[i]); ys.push(x.glong[i] * 9.81);
      }
    }
    ersTraces.push({ type: "scatter", mode: "markers", name: x.code,
      x: xs, y: ys, marker: { color: x.color, size: 4, opacity: 0.35 },
      hovertemplate: `<b>${x.code}</b> · %{x:.0f} km/h · %{y:.1f} m/s²<extra></extra>` });
    const fit = poly2fit(xs, ys);
    if (fit) {
      const fx = [...xs].sort((a, b) => a - b).filter((v, i, a2) => !i || v > a2[i - 1] + 2);
      ersTraces.push({ type: "scatter", mode: "lines", showlegend: false,
        x: fx, y: fx.map((v) => fit[0] * v * v + fit[1] * v + fit[2]),
        line: { color: x.color, width: 2.5 }, hoverinfo: "skip" });
    }
  });
  Plotly.newPlot(cErs.plot, ersTraces, baseLayout({
    height: 460, margin: { l: 56, r: 14, t: 12, b: 46 },
    xaxis: { ...baseLayout().xaxis, title: { text: "VELOCIDAD (KM/H)", font: { size: 10 } },
             showgrid: true, gridcolor: "rgba(255,255,255,.05)", griddash: "dot" },
    yaxis: { ...baseLayout().yaxis, title: { text: "ACELERACIÓN (M/S²)", font: { size: 10 } },
             zeroline: true, zerolinecolor: "rgba(255,255,255,.25)" },
    legend: { orientation: "h", y: 1.08, x: 1, xanchor: "right" },
  }), PLOTLY_CFG);

  const cPh = chartCard({
    title: "Fases de conducción", sub: "% del tiempo de la vuelta",
    summary: d.summaries.phases || "",
    tips: ["<b>¿Más % a fondo?</b> → o el coche permite pisar antes, o el circuito se lo pide y el motor manda.",
           "<b>¿Más % en curva que el rival?</b> → pasa más tiempo gestionando el paso por curva: ahí se decide su vuelta."],
  });
  zone.appendChild(cPh.card);
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

  zone.appendChild(el(`<div style="height:18px"></div>`));
  drawReplay(zone, d);
}


/* ───────────────────────────── REPLAY fantasma (Canvas 2D + rAF, 60 fps) */

function drawReplay(zone, d) {
  const cars = d.drivers.filter((x) => x.x && x.x.length && x.lap_time);
  if (cars.length < 1) return;

  zone.appendChild(el(`<div class="section-title" id="sec-replay">Replay de vuelta
    <small> · fantasmas sincronizados por tiempo real</small></div>`));
  const card = el(`<div class="card chart-card">
    <div class="chart-head"><h2>Replay fantasma</h2>
      <span class="sub">todos arrancan a la vez; el que va delante en pista, va delante en tiempo</span></div>
    <div style="padding:10px 18px 6px">
      <div class="replay-controls">
        <button class="btn-red" id="rpPlay">▶ PLAY</button>
        <select id="rpSpeed" style="padding:8px 34px 8px 12px">
          <option value="0.5">0.5×</option><option value="1" selected>1×</option>
          <option value="2">2×</option><option value="4">4×</option></select>
        <input type="range" id="rpScrub" min="0" max="1000" value="0" style="flex:1">
        <b id="rpTime" style="font-variant-numeric:tabular-nums;min-width:64px;text-align:right">0.0s</b>
      </div>
      <canvas id="rpCanvas" style="width:100%;display:block;border-radius:10px"></canvas>
      <div id="rpHud" class="replay-hud"></div>
    </div>
    <div class="chart-summary" style="margin-top:8px">Animación nativa en canvas (60 fps).
      El gap de cada tarjeta es tiempo real contra ${d.ref} en ese punto de la pista.</div>
    <details class="chart-guide"><summary>¿Cómo leer esta gráfica?</summary><ul>
      <li><b>¿Un fantasma se acerca en las curvas y se aleja en las rectas?</b> → coche con más carga aerodinámica: gana en curva, paga en recta.</li>
      <li><b>¿El gap crece de golpe en una zona?</b> → ahí está el error o la diferencia real; búscala en el delta y los micro-sectores.</li>
      <li>Usa 0.5× para estudiar una frenada concreta y el deslizador para volver a verla.</li>
    </ul></details></div>`);
  zone.appendChild(card);

  const canvas = card.querySelector("#rpCanvas");
  const hud = card.querySelector("#rpHud");
  const btn = card.querySelector("#rpPlay");
  const selV = card.querySelector("#rpSpeed");
  const scrub = card.querySelector("#rpScrub");
  const lblT = card.querySelector("#rpTime");

  const ref = cars[0];
  const Tmax = Math.max(...cars.map((c) => c.t[c.t.length - 1]));

  // mundo → pantalla
  const xs = ref.x, ys = ref.y;
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const H = 560;
  let W = 800, k = 1, ox = 0, oy = 0, dpr = window.devicePixelRatio || 1;
  const fit = () => {
    W = canvas.clientWidth || 800;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.height = H + "px";
    k = Math.min(W / (maxX - minX), H / (maxY - minY)) * 0.86;
    ox = (W - (maxX - minX) * k) / 2 - minX * k;
    oy = (H - (maxY - minY) * k) / 2 - minY * k;
  };
  const sx = (x) => x * k + ox;
  const sy = (y) => H - (y * k + oy);   // eje Y invertido (pantalla)

  // capa estática pre-renderizada: trazado + curvas + meta
  let staticLayer = null;
  const buildStatic = () => {
    staticLayer = document.createElement("canvas");
    staticLayer.width = W * dpr; staticLayer.height = H * dpr;
    const c = staticLayer.getContext("2d");
    c.scale(dpr, dpr);
    c.lineJoin = c.lineCap = "round";
    const path = () => {
      c.beginPath();
      c.moveTo(sx(xs[0]), sy(ys[0]));
      for (let i = 1; i < xs.length; i++) c.lineTo(sx(xs[i]), sy(ys[i]));
    };
    path(); c.strokeStyle = "rgba(255,255,255,.07)"; c.lineWidth = 16; c.stroke();
    path(); c.strokeStyle = "#2f333d"; c.lineWidth = 3.5; c.stroke();
    c.font = "700 10px Inter, sans-serif"; c.fillStyle = "#767c88"; c.textAlign = "center";
    (d.corners || []).forEach((cn) => c.fillText(cn.n, sx(cn.x), sy(cn.y) - 10));
    c.fillStyle = "#e8eaed";
    c.fillRect(sx(xs[0]) - 4, sy(ys[0]) - 4, 8, 8);
  };

  // interpolación de posición por TIEMPO (búsqueda binaria)
  const at = (car, tau) => {
    const t = car.t;
    if (tau >= t[t.length - 1]) {
      const i = t.length - 1;
      return { x: car.x[i], y: car.y[i], v: car.speed[i], dist: car.d[i], fin: true };
    }
    let lo = 0, hi = t.length - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; (t[m] <= tau ? lo = m : hi = m); }
    const f = (tau - t[lo]) / Math.max(t[hi] - t[lo], 1e-6);
    const L = (a) => a[lo] + (a[hi] - a[lo]) * f;
    return { x: L(car.x), y: L(car.y), v: L(car.speed), dist: L(car.d), fin: false };
  };
  // gap real vs referencia: mi tiempo aquí menos el tiempo de la ref en esta distancia
  const gapVsRef = (car, tau, dist) => {
    if (car === ref) return 0;
    let lo = 0, hi = ref.d.length - 1;
    if (dist >= ref.d[hi]) return tau - ref.t[hi];
    while (hi - lo > 1) { const m = (lo + hi) >> 1; (ref.d[m] <= dist ? lo = m : hi = m); }
    const f = (dist - ref.d[lo]) / Math.max(ref.d[hi] - ref.d[lo], 1e-6);
    return tau - (ref.t[lo] + (ref.t[hi] - ref.t[lo]) * f);
  };

  const ctx = canvas.getContext("2d");
  const trails = new Map(cars.map((c) => [c.code, []]));
  let tau = 0, playing = false, last = null, raf = null, arrastrando = false;

  const frame = () => {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    ctx.drawImage(staticLayer, 0, 0, W, H);
    const estados = cars.map((c) => ({ c, p: at(c, tau) }));
    estados.forEach(({ c, p }) => {
      const tr = trails.get(c.code);
      tr.push([p.x, p.y]);
      if (tr.length > 46) tr.shift();
      for (let i = 0; i < tr.length; i++) {
        ctx.globalAlpha = (i / tr.length) * 0.35;
        ctx.fillStyle = c.color;
        ctx.beginPath();
        ctx.arc(sx(tr[i][0]), sy(tr[i][1]), 2.4, 0, 7);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    });
    estados.forEach(({ c, p }) => {
      const X = sx(p.x), Y = sy(p.y);
      ctx.shadowColor = c.color; ctx.shadowBlur = 14;
      ctx.fillStyle = c.color;
      ctx.beginPath(); ctx.arc(X, Y, 8, 0, 7); ctx.fill();
      ctx.shadowBlur = 0;
      ctx.font = "800 10px Inter, sans-serif"; ctx.textAlign = "center";
      ctx.fillStyle = "#0b0d12";
      ctx.fillText(c.code[0], X, Y + 3.5);
      ctx.fillStyle = c.color;
      ctx.fillText(c.code, X, Y - 13);
    });
    // HUD
    hud.innerHTML = estados.map(({ c, p }) => {
      const g = gapVsRef(c, tau, p.dist);
      const gtxt = c === ref ? "REF" : (g >= 0 ? `+${g.toFixed(2)}s` : `${g.toFixed(2)}s`);
      return `<span class="chip" style="--cc:${c.color}"><i></i><b>${c.code}</b>
        &nbsp;${p.fin ? c.lap_label : p.v.toFixed(0) + " km/h"}
        &nbsp;<span style="color:${c === ref ? "var(--ink3)" : g > 0 ? "#ff8181" : "#7dffb0"}">${p.fin ? "" : gtxt}</span></span>`;
    }).join("");
    lblT.textContent = `${tau.toFixed(1)}s`;
    if (!arrastrando) scrub.value = Math.round((tau / Tmax) * 1000);
  };

  const loop = (ts) => {
    if (!playing) return;
    if (last != null) tau = Math.min(Tmax, tau + ((ts - last) / 1000) * (+selV.value));
    last = ts;
    frame();
    if (tau >= Tmax) { playing = false; btn.textContent = "↻ REPETIR"; return; }
    raf = requestAnimationFrame(loop);
  };
  btn.onclick = () => {
    if (playing) { playing = false; btn.textContent = "▶ PLAY"; cancelAnimationFrame(raf); return; }
    if (tau >= Tmax) { tau = 0; trails.forEach((t) => t.length = 0); }
    playing = true; last = null; btn.textContent = "❚❚ PAUSA";
    raf = requestAnimationFrame(loop);
  };
  scrub.oninput = (e) => {
    arrastrando = true;
    tau = (+e.target.value / 1000) * Tmax;
    trails.forEach((t) => t.length = 0);
    frame();
    arrastrando = false;
  };
  new ResizeObserver(() => { fit(); buildStatic(); frame(); }).observe(canvas);
  fit(); buildStatic(); frame();
}

/* ───────────────────────────── RITMO DE SESIÓN (estadística de toda la sesión) */

function poly2fit(xs, ys) {
  // ajuste y = ax² + bx + c por mínimos cuadrados (para la tendencia del ERS)
  const n = xs.length;
  if (n < 8) return null;
  let Sx = 0, Sx2 = 0, Sx3 = 0, Sx4 = 0, Sy = 0, Sxy = 0, Sx2y = 0;
  for (let i = 0; i < n; i++) {
    const x = xs[i], y = ys[i], x2 = x * x;
    Sx += x; Sx2 += x2; Sx3 += x2 * x; Sx4 += x2 * x2;
    Sy += y; Sxy += x * y; Sx2y += x2 * y;
  }
  const A = [[Sx4, Sx3, Sx2], [Sx3, Sx2, Sx], [Sx2, Sx, n]], B = [Sx2y, Sxy, Sy];
  const det = (m) => m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
    - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
    + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
  const D = det(A);
  if (!D) return null;
  const rep = (m, c, v) => m.map((r, i) => r.map((x, j) => (j === c ? v[i] : x)));
  return [det(rep(A, 0, B)) / D, det(rep(A, 1, B)) / D, det(rep(A, 2, B)) / D];
}

const COMP_COLORS = { SOFT: "#E0243F", MEDIUM: "#FFC400", HARD: "#E8EAED",
                      INTERMEDIATE: "#2ECC71", WET: "#3F7BF0" };

function timeTicks(vals) {
  const mn = Math.min(...vals), mx = Math.max(...vals);
  const paso = Math.max(0.5, Math.round((mx - mn) / 6 * 2) / 2);
  const ticks = [];
  for (let t = Math.ceil(mn * 2) / 2; t <= mx; t += paso) ticks.push(Math.round(t * 2) / 2);
  return { tickvals: ticks, ticktext: ticks.map(fmtLap) };
}

function drawSessionStats(zone, ss) {
  zone.appendChild(el(`<div class="section-title" id="sec-ritmo">Ritmo de sesión
    <small> · ${ss.session} · toda la sesión, no solo la vuelta rápida</small></div>`));

  // tiles: veredicto
  if (ss.cv.length) {
    const rapido = [...ss.cv].sort((a, b) => a.median - b.median)[0];
    const consistente = ss.cv[0];
    zone.appendChild(el(`<div class="tiles" style="margin-bottom:18px">
      <div class="card tile" style="--tc:${rapido.color}"><div class="label">Mejor ritmo (mediana)</div>
        <div class="value">${rapido.code}</div><div class="hint">${rapido.median_label} · ${rapido.laps} vueltas limpias</div></div>
      <div class="card tile" style="--tc:${consistente.color}"><div class="label">Más consistente</div>
        <div class="value">${consistente.code}</div><div class="hint">CV ${consistente.cv.toFixed(2)}% · σ ${consistente.sigma.toFixed(3)}s</div></div>
      <div class="card tile"><div class="label">Vueltas de la sesión</div>
        <div class="value">${ss.n_laps}</div><div class="hint">${ss.type === "race" ? "carrera" : ss.type === "quali" ? "clasificación" : "práctica"}</div></div>
    </div>`));
  }

  // tablero de qualy
  if (ss.quali && ss.quali.length) {
    zone.appendChild(el(`<div class="section-title">Clasificación Q1 · Q2 · Q3
      <small> · ${ss.summaries.quali || ""}</small></div>`));
    const rows = ss.quali.map((r) => `<tr><td class="num">${r.pos ?? "—"}</td>
      <td>${drvChip(r.code, r.color)}</td>
      <td class="num">${r.q1}</td><td class="num">${r.q2}</td><td class="num">${r.q3}</td>
      <td class="num"><b>${r.gap}</b></td><td>${r.corte}</td></tr>`).join("");
    zone.appendChild(el(`<div class="card table-wrap" style="margin-bottom:18px"><table>
      <thead><tr><th class="num">Pos</th><th>Piloto</th><th class="num">Q1</th>
      <th class="num">Q2</th><th class="num">Q3</th><th class="num">Gap</th><th>Corte</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`));
  }

  // evolución de tiempos con compuestos y atípicas
  if (ss.evo.length) {
    const cEvo = chartCard({
      title: "Evolución de tiempos por vuelta", sub: "color del punto = compuesto · ✕ gris = pit/SC/atípica",
      summary: ss.summaries.ritmo || "",
      tips: ["<b>¿La línea baja poco a poco?</b> → el coche mejora al quemar combustible; si sube, la goma degrada más de lo que el combustible regala.",
             "<b>¿Escalón hacia abajo tras una ✕?</b> → paró y volvió con goma nueva.",
             "Toca un piloto en la leyenda para aislarlo."],
      legendHtml: `<div class="compound-legend">${Object.entries(COMP_COLORS).map(([k, v]) =>
        `<span class="chip" style="--cc:${v}"><i></i>${k}</span>`).join("")}</div>`,
    });
    zone.appendChild(cEvo.card);
    zone.appendChild(el(`<div style="height:18px"></div>`));
    const traces = [];
    const outX = [], outY = [];
    ss.evo.forEach((e) => {
      const limpio = e.points.filter((p) => !p.out);
      traces.push({ type: "scatter", mode: "lines+markers", name: e.code,
        x: limpio.map((p) => p.lap), y: limpio.map((p) => p.t),
        line: { color: e.color, width: 1.7 },
        marker: { size: 5.5, color: limpio.map((p) => COMP_COLORS[p.comp] || e.color),
                  line: { color: "#11141b", width: 1 } },
        customdata: limpio.map((p) => [fmtLap(p.t), p.comp]),
        hovertemplate: `<b>${e.code}</b> · V%{x}<br>%{customdata[0]} · %{customdata[1]}<extra></extra>` });
      e.points.filter((p) => p.out).forEach((p) => { outX.push(p.lap); outY.push(p.t); });
    });
    if (outX.length) traces.push({ type: "scatter", mode: "markers", name: "Atípicas",
      x: outX, y: outY, marker: { symbol: "x-thin-open", size: 6, color: "#5b616d" },
      hoverinfo: "skip" });
    const tt = timeTicks(traces.flatMap((t) => t.y).filter((v) => v != null));
    Plotly.newPlot(cEvo.plot, traces, baseLayout({
      height: 520, hovermode: "closest",
      margin: { l: 64, r: 14, t: 14, b: 44 },
      xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } } },
      yaxis: { ...baseLayout().yaxis, ...tt },
      legend: { orientation: "h", y: -0.12, font: { size: 10.5 } },
    }), PLOTLY_CFG);
  }

  // fila: boxplot + tabla de consistencia
  const rowB = el(`<div class="grid cols-2" style="margin-bottom:18px"></div>`);
  zone.appendChild(rowB);
  if (ss.box.length) {
    const cBox = chartCard({
      title: "Distribución de ritmo", sub: "filtrado robusto IQR · sin pits ni atípicas",
      tips: ["<b>¿Caja pequeña?</b> → piloto metrónomo: casi todas sus vueltas son iguales.",
             "<b>¿Caja baja pero larga?</b> → rápido pero irregular; la mediana (línea central) es su ritmo real.",
             "Comparar MEDIANAS es más honesto que comparar la mejor vuelta."],
    });
    rowB.appendChild(cBox.card);
    const tt = timeTicks(ss.box.flatMap((b) => b.times));
    Plotly.newPlot(cBox.plot, ss.box.map((b) => ({
      type: "box", y: b.times, name: b.code, boxpoints: false,
      marker: { color: b.color }, line: { color: b.color, width: 1.8 },
      fillcolor: "rgba(0,0,0,0)",
    })), baseLayout({
      height: 460, showlegend: false,
      margin: { l: 64, r: 14, t: 14, b: 44 },
      yaxis: { ...baseLayout().yaxis, ...tt },
    }), PLOTLY_CFG);
  }
  if (ss.cv.length) {
    const badge = (v) => v < 0.9 ? ["#2ECC71", "Estable"] : v < 1.3 ? ["#FFC400", "Media"] : ["#FF5252", "Variable"];
    const rows = ss.cv.map((r) => {
      const [c, t] = badge(r.cv);
      return `<tr><td>${drvChip(r.code, r.color)}</td><td class="num">${r.laps}</td>
        <td class="num">${r.median_label}</td><td class="num">${r.sigma.toFixed(3)}</td>
        <td class="num">${r.iqr.toFixed(3)}</td>
        <td class="num"><b style="color:${c}">${r.cv.toFixed(2)}%</b> <small style="color:${c}">${t}</small></td></tr>`;
    }).join("");
    rowB.appendChild(el(`<div class="card table-wrap"><div class="chart-head" style="padding:0 0 8px">
      <h2>Consistencia (CV)</h2><span class="sub">CV = σ / mediana · menor = más regular</span></div>
      <table><thead><tr><th>Piloto</th><th class="num">Vueltas</th><th class="num">Mediana</th>
      <th class="num">σ</th><th class="num">IQR</th><th class="num">CV</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`));
  }

  // ritmo corregido por combustible (solo carrera) con slider
  if (ss.type === "race" && ss.evo.length) {
    const cFuel = chartCard({
      title: "Ritmo corregido por combustible", sub: "quita el efecto del peso para ver la degradación pura",
      tips: ["<b>¿Línea plana tras corregir?</b> → la goma aguantó: lo que ganaba era solo combustible.",
             "<b>¿Sigue subiendo?</b> → degradación real del neumático.",
             "Mueve el deslizador: ~0.035 s/vuelta es lo típico por quema de combustible."],
    });
    zone.appendChild(cFuel.card);
    const ctl = el(`<div style="padding:0 18px 10px;display:flex;gap:12px;align-items:center">
      <span style="font-size:11px;color:var(--ink3)">CORRECCIÓN</span>
      <input type="range" min="0" max="0.08" step="0.005" value="0.035" style="flex:1;max-width:340px">
      <b id="fuelval" style="font-size:12.5px">0.035 s/vuelta</b></div>`);
    cFuel.card.insertBefore(ctl, cFuel.card.querySelector(".chart-guide"));
    const drawFuel = (k) => {
      const traces = ss.evo.map((e) => {
        const limpio = e.points.filter((p) => !p.out);
        return { type: "scatter", mode: "lines", name: e.code,
          x: limpio.map((p) => p.lap), y: limpio.map((p) => p.t + k * (p.lap - 1)),
          line: { color: e.color, width: 1.7 },
          hovertemplate: `<b>${e.code}</b> · V%{x}<br>%{y:.3f}s corregido<extra></extra>` };
      });
      Plotly.react(cFuel.plot, traces, baseLayout({
        height: 440, hovermode: "x unified",
        margin: { l: 64, r: 14, t: 14, b: 44 },
        xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } } },
        yaxis: { ...baseLayout().yaxis, title: { text: "SEGUNDOS (CORREGIDO)", font: { size: 10 } } },
        legend: { orientation: "h", y: -0.12, font: { size: 10.5 } },
      }), PLOTLY_CFG);
    };
    ctl.querySelector("input").oninput = (e2) => {
      ctl.querySelector("#fuelval").textContent = `${(+e2.target.value).toFixed(3)} s/vuelta`;
      drawFuel(+e2.target.value);
    };
    drawFuel(0.035);
    zone.appendChild(el(`<div style="height:18px"></div>`));
  }

  // degradación por stint (tabla con badge)
  if (ss.deg && ss.deg.length) {
    zone.appendChild(el(`<div class="section-title">Degradación por stint
      <small> · ${ss.summaries.deg || ""}</small></div>`));
    const badge = (sl) => sl < 0 ? ["#3F7BF0", "Mejora"] : sl < 0.05 ? ["#2ECC71", "Excelente"]
      : sl < 0.10 ? ["#FFC400", "Normal"] : ["#FF5252", "Alta"];
    const rows = ss.deg.map((r) => {
      const [c, t] = badge(r.slope);
      return `<tr><td>${drvChip(r.code, r.color)}</td><td class="num">${r.stint}</td>
        <td><span class="chip" style="--cc:${r.comp_color}"><i></i>${r.compound}</span></td>
        <td class="num">${r.laps}</td><td class="num">${fmtLap(r.median)}</td>
        <td class="num"><b style="color:${c}">${(r.slope * 1000).toFixed(0)} ms/vuelta</b>
        <small style="color:${c}">${t}</small></td></tr>`;
    }).join("");
    zone.appendChild(el(`<div class="card table-wrap" style="margin-bottom:18px"><table>
      <thead><tr><th>Piloto</th><th class="num">Stint</th><th>Goma</th><th class="num">Vueltas</th>
      <th class="num">Mediana</th><th class="num">Degradación</th></tr></thead>
      <tbody>${rows}</tbody></table>
      <div class="chart-summary" style="margin:10px 0 4px">La degradación es la pendiente del stint:
      cuántos ms pierde por vuelta. "Mejora" = iba más rápido cada vuelta (goma entrando o quemando combustible).</div></div>`));
  }

  // parrilla → meta (solo carrera)
  if (ss.grid && ss.grid.length) {
    const cGr = chartCard({
      title: "Parrilla → meta", sub: "posiciones ganadas (verde) o perdidas (rojo) respecto a la salida",
      summary: ss.summaries.grid || "",
      tips: ["<b>¿Barra verde larga?</b> → gran remontada: salió atrás y acabó delante.",
             "<b>¿Roja larga?</b> → mal día: problema mecánico, sanción o mala estrategia."],
    });
    zone.appendChild(cGr.card);
    zone.appendChild(el(`<div style="height:18px"></div>`));
    const g = [...ss.grid].reverse();
    Plotly.newPlot(cGr.plot, [{
      type: "bar", orientation: "h",
      y: g.map((x) => x.code), x: g.map((x) => x.delta),
      marker: { color: g.map((x) => x.delta > 0 ? "#2ECC71" : x.delta < 0 ? "#FF5252" : "#5b616d"),
                line: { color: "#11141b", width: 2 } },
      text: g.map((x) => ` P${x.grid}→P${x.pos} `), textposition: "outside",
      textfont: { size: 10, color: "#9aa0aa" },
      hovertemplate: "<b>%{y}</b> · %{x:+d} posiciones<extra></extra>",
    }], baseLayout({
      height: Math.max(360, g.length * 22 + 110),
      margin: { l: 52, r: 60, t: 12, b: 40 },
      xaxis: { ...baseLayout().xaxis, title: { text: "± POSICIONES", font: { size: 10 } },
               zeroline: true, zerolinecolor: "rgba(255,255,255,.3)" },
      yaxis: { ...baseLayout().yaxis, gridcolor: "rgba(0,0,0,0)", tickfont: { size: 10 } },
    }), PLOTLY_CFG);
  }

  // heatmap de speed trap por vuelta
  if (ss.trap) {
    const cTr = chartCard({
      title: "Speed trap por vuelta", sub: "velocidad punta de cada piloto en cada vuelta (km/h)",
      summary: ss.summaries.trap || "",
      tips: ["<b>¿Una fila que se enfría (azul) al final?</b> → gestionaba o perdió motor/rebufo.",
             "<b>¿Columna entera fría?</b> → vuelta lenta de todos: SC o lluvia.",
             "<b>¿Un punto rojo aislado?</b> → rebufo perfecto o DRS en esa vuelta."],
    });
    zone.appendChild(cTr.card);
    zone.appendChild(el(`<div style="height:18px"></div>`));
    Plotly.newPlot(cTr.plot, [{
      type: "heatmap", x: ss.trap.laps, y: ss.trap.drivers, z: ss.trap.z,
      colorscale: "Turbo", hoverongaps: false,
      hovertemplate: "<b>%{y}</b> · V%{x}<br>%{z:.0f} km/h<extra></extra>",
      colorbar: { thickness: 10, tickfont: { size: 10, color: "#9aa0aa" } },
    }], baseLayout({
      height: Math.max(380, ss.trap.drivers.length * 21 + 130),
      margin: { l: 52, r: 60, t: 12, b: 40 },
      xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } } },
      yaxis: { ...baseLayout().yaxis, autorange: "reversed", gridcolor: "rgba(0,0,0,0)",
               tickfont: { size: 10 } },
    }), PLOTLY_CFG);
  }
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
