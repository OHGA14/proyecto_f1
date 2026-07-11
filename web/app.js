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

const PLOTLY_CFG = {
  displayModeBar: true, displaylogo: false, responsive: true,
  modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d", "toggleSpikelines",
                           "hoverClosestCartesian", "hoverCompareCartesian"],
  doubleClick: "reset",
};

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

  // ritmo puro por GP + récords de speed trap (histórico)
  const [hp, tr] = await Promise.all([
    api(`/historic/pace/${state.year}`), api(`/historic/trap/${state.year}`),
  ]);
  if (hp.drivers && hp.drivers.length) {
    $view.appendChild(el(`<div style="height:20px"></div>`));
    const cHp = chartCard({
      title: `Ritmo puro por GP · ${state.year}`,
      sub: "% sobre la mejor vuelta de cada carrera · 0% = hizo LA vuelta del GP",
      summary: hp.summary || "",
      tips: ["<b>¿Una línea toca el 0%?</b> → ese piloto hizo la vuelta más rápida de esa carrera.",
             "<b>¿Plana y baja todo el año?</b> → ritmo de élite constante, sin importar el circuito."],
    });
    $view.appendChild(cHp.card);
    Plotly.newPlot(cHp.plot, hp.drivers.map((x) => ({
      type: "scatter", mode: "lines+markers", name: x.code,
      x: hp.gps, y: x.pct, connectgaps: true,
      line: { color: x.color, width: 2 }, marker: { size: 6 },
      hovertemplate: `<b>${x.code}</b> · %{x}<br>+%{y:.2f}%<extra></extra>`,
    })), baseLayout({
      height: 480, hovermode: "x unified",
      margin: { l: 58, r: 16, t: 14, b: 60 },
      xaxis: { ...baseLayout().xaxis, tickangle: -35, tickfont: { size: 10 } },
      yaxis: { ...baseLayout().yaxis, title: { text: "% SOBRE LA MEJOR", font: { size: 10 } },
               ticksuffix: "%", zeroline: true, zerolinecolor: "rgba(255,45,45,.5)" },
      legend: { orientation: "h", y: -0.22, font: { size: 10.5 } },
    }), PLOTLY_CFG);
  }
  if (tr && tr.length) {
    $view.appendChild(el(`<div style="height:20px"></div>`));
    $view.appendChild(el(`<div class="section-title">Récord de speed trap por GP</div>`));
    const trRows = tr.map((r) => `<tr><td>${r.gp}</td>
      <td>${drvChip(r.code, r.color)}</td>
      <td class="num"><b>${r.vmax.toFixed(0)}</b> km/h</td></tr>`).join("");
    $view.appendChild(el(`<div class="card table-wrap"><table>
      <thead><tr><th>GP</th><th>Piloto</th><th class="num">Vel. punta</th></tr></thead>
      <tbody>${trRows}</tbody></table></div>`));
  }
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
    const cGap = chartCard({
      title: "Gap al líder", sub: "segundos detrás del primero, vuelta a vuelta",
      summary: d.summaries.gaps || "",
      tips: ["<b>¿Línea plana?</b> → mantiene el ritmo del líder; si sube, lo está perdiendo.",
             "<b>¿Todas las líneas se comprimen de golpe?</b> → coche de seguridad: el pelotón se reagrupa.",
             "<b>¿Escalón hacia arriba de ~20s?</b> → pit stop de ese piloto.",
             "Para enfocar la pelea de cabeza: arrastra un recuadro sobre la zona 0-40s; doble clic vuelve a verlo todo."],
    });
    $view.appendChild(cGap.card);
    Plotly.newPlot(cGap.plot, d.gaps.map((x) => ({
      type: "scatter", mode: "lines", name: x.code, x: x.laps, y: x.gap,
      line: { color: x.color, width: 1.8 },
      hovertemplate: `<b>${x.code}</b> · V%{x}<br>+%{y:.1f}s del líder<extra></extra>`,
    })), baseLayout({
      height: 660, shapes: scShapes,
      margin: { l: 52, r: 14, t: 14, b: 44 },
      xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } } },
      yaxis: { ...baseLayout().yaxis, title: { text: "SEGUNDOS TRAS EL LÍDER", font: { size: 10 } },
               autorange: "reversed" },
      legend: { orientation: "h", y: -0.1, font: { size: 10.5 } },
    }), PLOTLY_CFG);
    zoomGapPills(cGap.card, cGap.plot);
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

  state.schedCache = state.schedCache || {};
  const years = [...new Set([2026, 2025, 2024, 2023, ...cat.map((c) => c.year)])]
    .sort((a, b) => b - a);
  if (!state.telYear) {
    const ready = cat.find((c) => c.status === "ready") || cat[cat.length - 1];
    if (ready) { state.telYear = ready.year; state.telGp = ready.gp; state.telSes = ready.session; }
    else state.telYear = years[0];
  }

  const controls = el(`<div class="card analysis-controls" style="margin-bottom:18px">
    <select id="selYear">${years.map((y) =>
      `<option ${y === state.telYear ? "selected" : ""}>${y}</option>`).join("")}</select>
    <select id="selGp" style="min-width:250px"><option>cargando…</option></select>
    <select id="selSes2" style="min-width:160px"></select>
    <button class="btn-red" id="btnLoad">ANALIZAR</button>
    <button class="swap" id="btnRefresh" style="transform:none" title="Recarga el calendario y el catálogo — útil justo después de un GP">⟳ BUSCAR NUEVOS</button>
    <span style="font-size:11.5px;color:var(--ink3)">● = ya descargada (instantánea) · sin ● la baja de internet (~1-2 min)</span>
  </div>`);
  $view.appendChild(controls);
  const zone = el(`<div></div>`);
  $view.appendChild(zone);
  const selYear = controls.querySelector("#selYear");
  const selGp = controls.querySelector("#selGp");
  const selSes = controls.querySelector("#selSes2");

  const fillSes = (evs) => {
    const ev = evs.find((e) => e.gp === state.telGp) || evs[evs.length - 1];
    if (!ev) { selSes.innerHTML = ""; return; }
    state.telGp = ev.gp;
    if (!ev.sessions.some((x) => x.session === state.telSes))
      state.telSes = (ev.sessions.find((x) => x.session === "Race") || ev.sessions[ev.sessions.length - 1]).session;
    selSes.innerHTML = ev.sessions.map((x) =>
      `<option value="${x.session}" ${x.session === state.telSes ? "selected" : ""}>${x.session}${x.cached ? " ●" : ""}</option>`).join("");
  };
  const fillGp = async () => {
    selGp.innerHTML = "<option>cargando…</option>";
    if (!state.schedCache[state.telYear])
      state.schedCache[state.telYear] = await api(`/telemetry/schedule?year=${state.telYear}`);
    const evs = state.schedCache[state.telYear].events || [];
    if (!evs.length) { selGp.innerHTML = "<option>sin calendario</option>"; selSes.innerHTML = ""; return; }
    if (!evs.some((e) => e.gp === state.telGp)) {
      const conCache = [...evs].reverse().find((e) => e.sessions.some((x) => x.cached));
      state.telGp = (conCache || evs[evs.length - 1]).gp;
    }
    selGp.innerHTML = evs.map((e) =>
      `<option value="${e.gp}" ${e.gp === state.telGp ? "selected" : ""}>R${e.round} · ${e.gp.replace(" Grand Prix", "")}${e.sessions.some((x) => x.cached) ? " ●" : ""}</option>`).join("");
    fillSes(evs);
  };
  selYear.onchange = () => { state.telYear = +selYear.value; state.telGp = null; state.telSes = null; fillGp(); };
  selGp.onchange = () => { state.telGp = selGp.value; state.telSes = null; fillSes(state.schedCache[state.telYear].events); };
  selSes.onchange = () => { state.telSes = selSes.value; };
  controls.querySelector("#btnLoad").onclick = () => {
    state.tsid = `${state.telYear}|${state.telGp}|${state.telSes}`;
    state.telSel = null;
    beginAnalysis(zone);
  };
  controls.querySelector("#btnRefresh").onclick = () => { state.schedCache = {}; viewAnalisis(); };
  await fillGp();

  if (state.tsid) {
    const st = await api(`/telemetry/status?sid=${encodeURIComponent(state.tsid)}`);
    if (st.status === "ready") return renderAnalysis(zone);
    if (st.status === "loading") return beginAnalysis(zone);
  }
  zone.appendChild(el(`<div class="empty">Elige año, Gran Premio y sesión, y pulsa <b>ANALIZAR</b>.</div>`));
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
  const q = (state.telSel && state.telSel.length ? `&drivers=${state.telSel.join(",")}` : "")
          + (state.telLap ? `&lap=${state.telLap}` : "");
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
    <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:10px">
      <span style="font-size:10px;letter-spacing:2px;color:var(--ink3);font-weight:700">
        PILOTOS · el primero es la referencia del delta y del mapa</span>
      <span style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
        <button class="pill" data-top="3">TOP 3</button>
        <button class="pill" data-top="5">TOP 5</button>
        <button class="pill" data-top="10">TOP 10</button>
        <select id="lapMode" style="padding:6px 30px 6px 10px;font-size:12px">
          <option value="">VUELTA RÁPIDA</option><option value="n">VUELTA Nº…</option></select>
        <input type="number" id="lapN" min="1" placeholder="nº" style="width:70px;display:${state.telLap ? "" : "none"};background:var(--card2);color:var(--ink);border:1px solid var(--border);border-radius:8px;padding:7px 8px;font:inherit">
      </span></div>
    <div class="drv-chips"></div></div>`);
  chipsCard.querySelectorAll("[data-top]").forEach((b) => {
    b.onclick = () => {
      state.telSel = (d.available || []).slice(0, +b.dataset.top).map((x) => x.code);
      renderPilotos(zone);
    };
  });
  const lapMode = chipsCard.querySelector("#lapMode");
  const lapN = chipsCard.querySelector("#lapN");
  lapMode.value = state.telLap ? "n" : "";
  if (state.telLap) lapN.value = state.telLap;
  lapMode.onchange = () => {
    if (lapMode.value === "n") { lapN.style.display = ""; lapN.focus(); }
    else { state.telLap = null; renderPilotos(zone); }
  };
  lapN.onchange = () => { state.telLap = +lapN.value || null; renderPilotos(zone); };
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
  drawSessionStats(zone, ss, state.telSel);
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
  const sectorAnnots = (d.cuts || []).map((x, i) => ({
    x, yref: "paper", y: 1.045, text: `S${i + 2}`, showarrow: false,
    font: { size: 10, color: "#8a919e" },
  }));
  const winnerAnnots = (d.sectors || []).map((sc) => ({
    x: (sc.d0 + sc.d1) / 2, yref: "paper", y: 1.1, showarrow: false,
    text: `${sc.label}: ${sc.winner} +${sc.margin.toFixed(3)}`,
    font: { size: 10.5, color: sc.color },
  }));
  const zoneAnnots = (d.zones || []).map((z) => ({
    x: (z.d0 + z.d1) / 2, yref: "paper", y: 0.99, showarrow: false,
    text: "ALTA VEL", font: { size: 9, color: "#2ECC71" },
  }));
  const DASHES = ["solid", "dash", "dot", "longdash", "dashdot"];
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
    title: "Velocidad (línea sólida = referencia, guiones = siguientes)",
    sub: lapLabels, summary: d.summaries.speed || "",
    tips: ["<b>¿Una línea llega más alto en recta?</b> → menos ala o mejor tracción a la salida de la curva previa.",
           "<b>¿Valle más estrecho en una curva?</b> → frena más tarde y suelta antes: ahí gana el tiempo.",
           "Las líneas verticales tenues separan los sectores S1/S2/S3."],
  });
  zone.appendChild(cVel.card);
  Plotly.newPlot(cVel.plot, d.drivers.map((x, i) => ({
    type: "scatter", mode: "lines", name: x.code, x: x.d, y: x.speed,
    line: { color: x.color, width: 1.9, dash: DASHES[i % DASHES.length] },
    hovertemplate: `<b>${x.code}</b> · %{y:.0f} km/h<extra></extra>`,
  })), baseLayout({
    height: 600, hovermode: "x unified", shapes: sectorShapes,
    annotations: [...sectorAnnots, ...winnerAnnots, ...zoneAnnots],
    margin: { l: 56, r: 14, t: 42, b: 48 },
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
      height: 500, hovermode: "x unified", shapes: sectorShapes,
      annotations: sectorAnnots,
      margin: { l: 56, r: 14, t: 30, b: 48 },
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
      <canvas id="rpTele" style="width:100%;display:block;border-radius:10px;margin-top:10px"></canvas>
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
  let W = 800, H = 560, k = 1, ox = 0, oy = 0, dpr = window.devicePixelRatio || 1;
  const fit = () => {
    W = canvas.clientWidth || 800;
    const aspecto = (maxY - minY) / (maxX - minX);
    H = Math.round(Math.min(780, Math.max(420, W * aspecto * 0.96)));
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.height = H + "px";
    k = Math.min(W / (maxX - minX), H / (maxY - minY)) * 0.94;
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

  // ── tira de telemetría sincronizada (velocidad / gas / freno / marcha) ──
  const tele = card.querySelector("#rpTele");
  const tctx = tele.getContext("2d");
  const Dmax = Math.max(...cars.map((c) => c.d[c.d.length - 1]));
  const vMax = Math.max(...cars.map((c) => Math.max(...c.speed))) * 1.05;
  const BANDS = [
    { key: "speed", lbl: "VEL",   min: 0,  max: vMax, frac: 0.42 },
    { key: "throttle", lbl: "GAS", min: 0, max: 105,  frac: 0.20 },
    { key: "brake", lbl: "FRENO", min: 0,  max: 105,  frac: 0.20 },
    { key: "gear", lbl: "MARCHA", min: 0.5, max: 8.5, frac: 0.18 },
  ];
  const TH = 330, PADL = 56;
  let TW = 800, teleStatic = null, bandGeo = [];
  const fitTele = () => {
    TW = tele.clientWidth || 800;
    tele.width = TW * dpr; tele.height = TH * dpr;
    tele.style.height = TH + "px";
    let y0 = 6;
    bandGeo = BANDS.map((b) => {
      const h = (TH - 14) * b.frac;
      const g = { ...b, y0, y1: y0 + h - 8 };
      y0 += h;
      return g;
    });
    teleStatic = document.createElement("canvas");
    teleStatic.width = TW * dpr; teleStatic.height = TH * dpr;
    const c = teleStatic.getContext("2d");
    c.scale(dpr, dpr);
    const px = (dd) => PADL + (dd / Dmax) * (TW - PADL - 10);
    const py = (g, v) => g.y1 - ((v - g.min) / (g.max - g.min)) * (g.y1 - g.y0);
    bandGeo.forEach((g) => {
      c.strokeStyle = "rgba(255,255,255,.07)";
      c.beginPath(); c.moveTo(PADL, g.y1); c.lineTo(TW - 10, g.y1); c.stroke();
      c.font = "700 9px Inter, sans-serif";
      c.fillStyle = "#767c88"; c.textAlign = "left";
      c.fillText(g.lbl, 8, (g.y0 + g.y1) / 2 + 3);
      cars.forEach((car) => {
        c.strokeStyle = car.color; c.globalAlpha = 0.85; c.lineWidth = 1.4;
        c.beginPath();
        for (let i = 0; i < car.d.length; i++) {
          const X = px(car.d[i]), Y = py(g, car[g.key][i]);
          (i ? c.lineTo(X, Y) : c.moveTo(X, Y));
        }
        c.stroke(); c.globalAlpha = 1;
      });
    });
    (d.cuts || []).forEach((x) => {
      c.strokeStyle = "rgba(255,255,255,.14)";
      c.beginPath(); c.moveTo(px(x), 4); c.lineTo(px(x), TH - 6); c.stroke();
    });
  };
  const idxAt = (car, dist) => {
    let lo = 0, hi = car.d.length - 1;
    if (dist >= car.d[hi]) return hi;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; (car.d[m] <= dist ? lo = m : hi = m); }
    return lo;
  };
  const drawTele = (estados) => {
    tctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    tctx.clearRect(0, 0, TW, TH);
    tctx.drawImage(teleStatic, 0, 0, TW, TH);
    const px = (dd) => PADL + (dd / Dmax) * (TW - PADL - 10);
    const py = (g, v) => g.y1 - ((v - g.min) / (g.max - g.min)) * (g.y1 - g.y0);
    const xRef = px(estados[0].p.dist);
    tctx.strokeStyle = "rgba(255,255,255,.45)"; tctx.lineWidth = 1;
    tctx.beginPath(); tctx.moveTo(xRef, 4); tctx.lineTo(xRef, TH - 6); tctx.stroke();
    estados.forEach(({ c, p }) => {
      const i = idxAt(c, p.dist), X = px(p.dist);
      bandGeo.forEach((g) => {
        tctx.fillStyle = c.color;
        tctx.beginPath();
        tctx.arc(X, py(g, c[g.key][i]), 3.6, 0, 7);
        tctx.fill();
        tctx.strokeStyle = "#0b0d12"; tctx.lineWidth = 1.4; tctx.stroke();
      });
    });
  };

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
    // CLOSE-UP: cámara con zoom sobre los dos primeros fantasmas
    if (cars.length >= 2) {
      const pw = Math.min(360, W * 0.32), ph = Math.round(pw * 0.62);
      const px0 = W - pw - 14, py0 = 14;
      const a = estados[0].p, b = estados[1].p;
      const cx = (a.x + b.x) / 2, cy = (a.y + b.y) / 2;
      const sep = Math.hypot(a.x - b.x, a.y - b.y);
      const k2 = Math.min(4 * k, (pw * 0.6) / Math.max(sep, 30));
      const S = (x, y) => [px0 + pw / 2 + (x - cx) * k2, py0 + ph / 2 - (y - cy) * k2];
      ctx.save();
      ctx.beginPath(); ctx.roundRect(px0, py0, pw, ph, 10); ctx.clip();
      ctx.fillStyle = "rgba(10,12,17,.96)"; ctx.fillRect(px0, py0, pw, ph);
      ctx.strokeStyle = "rgba(255,255,255,.1)";
      ctx.lineWidth = Math.max(10, (k2 / k) * 5);
      ctx.lineJoin = ctx.lineCap = "round";
      ctx.beginPath();
      for (let i = 0; i < xs.length; i++) {
        const [X2, Y2] = S(xs[i], ys[i]);
        (i ? ctx.lineTo(X2, Y2) : ctx.moveTo(X2, Y2));
      }
      ctx.stroke();
      estados.slice(0, 2).forEach(({ c, p }) => {
        const [X2, Y2] = S(p.x, p.y);
        ctx.shadowColor = c.color; ctx.shadowBlur = 12;
        ctx.fillStyle = c.color;
        ctx.beginPath(); ctx.arc(X2, Y2, 9, 0, 7); ctx.fill();
        ctx.shadowBlur = 0;
        ctx.font = "800 10px Inter, sans-serif"; ctx.textAlign = "center";
        ctx.fillStyle = "#0b0d12"; ctx.fillText(c.code[0], X2, Y2 + 3.5);
      });
      ctx.restore();
      ctx.strokeStyle = "rgba(255,255,255,.18)"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.roundRect(px0, py0, pw, ph, 10); ctx.stroke();
      ctx.font = "700 9px Inter, sans-serif"; ctx.fillStyle = "#8a919e";
      ctx.textAlign = "left";
      ctx.fillText("CLOSE-UP", px0 + 10, py0 + 16);
    }
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
    drawTele(estados);
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
  new ResizeObserver(() => { fit(); buildStatic(); fitTele(); frame(); }).observe(canvas);
  fit(); buildStatic(); fitTele(); frame();
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

function drawSessionStats(zone, ss, sel) {
  const cont = el(`<div></div>`);
  zone.appendChild(cont);
  const render = () => {
    cont.innerHTML = "";
    const usarSel = !state.ritmoAll && sel && sel.length;
    const f = (arr) => (usarSel ? (arr || []).filter((x) => sel.includes(x.code)) : (arr || []));
    const ss2 = { ...ss, box: f(ss.box), cv: f(ss.cv), evo: f(ss.evo),
                  deg: f(ss.deg), grid: f(ss.grid), stints: f(ss.stints),
                  positions: f(ss.positions), gaps: f(ss.gaps) };
    if (ss.trap && usarSel) {
      const idx = ss.trap.drivers.map((c, i) => [c, i]).filter(([c]) => sel.includes(c));
      ss2.trap = idx.length >= 1
        ? { drivers: idx.map(([c]) => c), laps: ss.trap.laps, z: idx.map(([, i]) => ss.trap.z[i]) }
        : null;
    }
    drawSessionStatsInner(cont, ss2, render);
  };
  render();
}

function drawSessionStatsInner(zone, ss, rerender) {
  zone.appendChild(el(`<div class="section-title" id="sec-ritmo">Ritmo de sesión
    <small> · ${ss.session} · toda la sesión, no solo la vuelta rápida</small></div>`));
  const tg = el(`<div class="pills" style="margin-bottom:14px">
    <button class="pill ${!state.ritmoAll ? "active" : ""}">PILOTOS SELECCIONADOS</button>
    <button class="pill ${state.ritmoAll ? "active" : ""}">TODO EL CAMPO</button></div>`);
  const [tgA, tgB] = tg.querySelectorAll("button");
  tgA.onclick = () => { state.ritmoAll = false; rerender(); };
  tgB.onclick = () => { state.ritmoAll = true; rerender(); };
  zone.appendChild(tg);

  let sumRitmo = "";
  if (ss.cv.length) {
    const rap = [...ss.cv].sort((a, b) => a.median - b.median)[0];
    const con = ss.cv[0];
    sumRitmo = `Mejor ritmo mediano: ${rap.code} (${rap.median_label}). Más consistente: ` +
               `${con.code} (CV ${con.cv.toFixed(2)}%). El más rápido no siempre es el más regular.`;
  }

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
      summary: sumRitmo,
      tips: ["<b>¿La línea baja poco a poco?</b> → el coche mejora al quemar combustible; si sube, la goma degrada más de lo que el combustible regala.",
             "<b>¿Escalón hacia abajo tras una ✕?</b> → paró y volvió con goma nueva.",
             "Toca un piloto en la leyenda para aislarlo."],
      legendHtml: `<div class="compound-legend">${Object.entries(COMP_COLORS).map(([k, v]) =>
        `<span class="chip" style="--cc:${v}"><i></i>${k}</span>`).join("")}
        <span class="chip" style="--cc:#5b616d"><i></i>✕ atípica</span>
        <span class="chip" style="--cc:#fff"><i></i>◆ pit</span>
        <button class="pill" id="evoTgl" style="margin-left:auto">${state.evoOut === false ? "MOSTRAR" : "OCULTAR"} ATÍPICAS</button></div>`,
    });
    zone.appendChild(cEvo.card);
    zone.appendChild(el(`<div style="height:20px"></div>`));
    cEvo.card.querySelector("#evoTgl").onclick = () => {
      state.evoOut = state.evoOut === false;
      rerender();
    };
    const traces = [];
    const outX = [], outY = [];
    const pitX = [], pitY = [], pitC = [];
    ss.evo.forEach((e) => {
      const limpio = e.points.filter((p) => !p.out);
      traces.push({ type: "scatter", mode: "lines+markers", name: e.code,
        x: limpio.map((p) => p.lap), y: limpio.map((p) => p.t),
        line: { color: e.color, width: 1.7 },
        marker: { size: 6, color: limpio.map((p) => COMP_COLORS[p.comp] || e.color),
                  line: { color: "#11141b", width: 1 } },
        customdata: limpio.map((p) => [fmtLap(p.t), p.comp]),
        hovertemplate: `<b>${e.code}</b> · V%{x}<br>%{customdata[0]} · %{customdata[1]}<extra></extra>` });
      e.points.filter((p) => p.out).forEach((p) => { outX.push(p.lap); outY.push(p.t); });
      e.points.filter((p) => p.pit).forEach((p) => { pitX.push(p.lap); pitY.push(p.t); pitC.push(e.color); });
    });
    if (state.evoOut !== false && outX.length)
      traces.push({ type: "scatter", mode: "markers", name: "Atípicas",
        x: outX, y: outY, marker: { symbol: "x-thin-open", size: 6, color: "#5b616d" },
        hoverinfo: "skip" });
    if (pitX.length)
      traces.push({ type: "scatter", mode: "markers", name: "Pit",
        x: pitX, y: pitY, marker: { symbol: "diamond", size: 7, color: pitC,
        line: { color: "#fff", width: 1 } },
        hovertemplate: "PIT · V%{x}<extra></extra>" });
    const visibles = traces.flatMap((t) => (t.name === "Atípicas" || t.name === "Pit")
      ? (state.evoOut !== false ? t.y : []) : t.y).filter((v) => v != null);
    const tt = timeTicks(visibles.length ? visibles : [60, 120]);
    const scShapesEvo = (ss.sc_ranges || []).map(([l0, l1]) => ({
      type: "rect", x0: l0 - 0.5, x1: l1 + 0.5, yref: "paper", y0: 0, y1: 1,
      fillcolor: "rgba(255,196,0,.07)", line: { width: 0 }, layer: "below" }));
    Plotly.newPlot(cEvo.plot, traces, baseLayout({
      height: 560, hovermode: "closest", shapes: scShapesEvo,
      annotations: (ss.sc_ranges || []).map(([l0, l1]) => ({
        x: (l0 + l1) / 2, yref: "paper", y: 1.03, text: "SC/VSC", showarrow: false,
        font: { size: 9, color: "#FFC400" } })),
      margin: { l: 64, r: 14, t: 30, b: 44 },
      xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } } },
      yaxis: { ...baseLayout().yaxis, ...tt },
      legend: { orientation: "h", y: -0.12, font: { size: 10.5 } },
    }), PLOTLY_CFG);
  }

  // LAP CHART + GAP AL LÍDER (carrera)
  if (ss.positions && ss.positions.length) {
    const scShapesLap = (ss.sc_ranges || []).map(([l0, l1]) => ({
      type: "rect", x0: l0 - 0.5, x1: l1 + 0.5, yref: "paper", y0: 0, y1: 1,
      fillcolor: "rgba(255,196,0,.07)", line: { width: 0 }, layer: "below" }));
    const cLp = chartCard({
      title: "Lap chart · posición vuelta a vuelta", sub: "bandas amarillas = SC/VSC",
      tips: ["<b>¿Cae varias posiciones de golpe?</b> → pit stop; mira si las recupera.",
             "<b>¿Cruces constantes?</b> → batalla real en pista."],
    });
    zone.appendChild(cLp.card);
    zone.appendChild(el(`<div style="height:20px"></div>`));
    Plotly.newPlot(cLp.plot, ss.positions.map((x) => ({
      type: "scatter", mode: "lines", name: x.code, x: x.laps, y: x.pos,
      line: { color: x.color, width: 2 },
      hovertemplate: `<b>${x.code}</b> · V%{x} · P%{y}<extra></extra>`,
    })), baseLayout({
      height: 560, shapes: scShapesLap,
      margin: { l: 46, r: 14, t: 14, b: 44 },
      xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } } },
      yaxis: { ...baseLayout().yaxis, title: { text: "POSICIÓN", font: { size: 10 } },
               autorange: "reversed", dtick: 1 },
      legend: { orientation: "h", y: -0.1, font: { size: 10.5 } },
    }), PLOTLY_CFG);

    if (ss.gaps && ss.gaps.length) {
      const cGp = chartCard({
        title: "Gap al líder", sub: "segundos detrás del primero",
        tips: ["<b>¿Se comprimen todas las líneas?</b> → coche de seguridad: el pelotón se reagrupa.",
               "<b>¿Escalón de ~20s hacia arriba?</b> → pit stop."],
      });
      zone.appendChild(cGp.card);
      zone.appendChild(el(`<div style="height:20px"></div>`));
      Plotly.newPlot(cGp.plot, ss.gaps.map((x) => ({
        type: "scatter", mode: "lines", name: x.code, x: x.laps, y: x.gap,
        line: { color: x.color, width: 2 },
        hovertemplate: `<b>${x.code}</b> · V%{x}<br>+%{y:.1f}s<extra></extra>`,
      })), baseLayout({
        height: 660, shapes: scShapesLap,
        margin: { l: 52, r: 14, t: 14, b: 44 },
        xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } } },
        yaxis: { ...baseLayout().yaxis, title: { text: "SEGUNDOS TRAS EL LÍDER", font: { size: 10 } },
                 autorange: "reversed" },
        legend: { orientation: "h", y: -0.1, font: { size: 10.5 } },
      }), PLOTLY_CFG);
      zoomGapPills(cGp.card, cGp.plot);
    }
  }

  // DISTRIBUCIÓN DE RITMO: ancho completo, ordenado por mediana
  if (ss.box.length) {
    const med = (arr) => { const a = [...arr].sort((x, y) => x - y);
      return a.length % 2 ? a[(a.length - 1) / 2] : (a[a.length / 2 - 1] + a[a.length / 2]) / 2; };
    const orden = [...ss.box].sort((a, b) => med(a.times) - med(b.times));
    const cBox = chartCard({
      title: "Distribución de ritmo",
      sub: "ordenado por mediana · cada punto = una vuelta limpia · línea punteada = promedio",
      tips: ["<b>¿Caja pequeña?</b> → piloto metrónomo: casi todas sus vueltas son iguales.",
             "<b>¿Caja baja pero larga?</b> → rápido pero irregular; la mediana (línea central) es su ritmo real.",
             "<b>¿Puntos sueltos lejos de la caja?</b> → vueltas raras que sobrevivieron al filtro: tráfico o goma muerta.",
             "Comparar MEDIANAS es más honesto que comparar la mejor vuelta."],
    });
    zone.appendChild(cBox.card);
    zone.appendChild(el(`<div style="height:20px"></div>`));
    const tt = timeTicks(ss.box.flatMap((b) => b.times));
    Plotly.newPlot(cBox.plot, orden.map((b) => ({
      type: "box", y: b.times, name: b.code,
      boxpoints: "all", jitter: 0.55, pointpos: 0, boxmean: true, width: 0.55,
      marker: { color: rgba(b.color, 0.4), size: 3.8 },
      line: { color: b.color, width: 2.2 },
      fillcolor: rgba(b.color, 0.13),
      customdata: b.times.map(fmtLap),
      hovertemplate: `<b>${b.code}</b> · %{customdata}<extra></extra>`,
    })), baseLayout({
      height: 620, showlegend: false,
      annotations: orden.map((b) => ({
        x: b.code, y: med(b.times), yshift: 16, showarrow: false,
        text: fmtLap(med(b.times)),
        font: { size: 10.5, color: b.color, family: "Inter" },
      })),
      margin: { l: 64, r: 14, t: 26, b: 44 },
      xaxis: { ...baseLayout().xaxis, tickfont: { size: 11.5 } },
      yaxis: { ...baseLayout().yaxis, ...tt },
    }), PLOTLY_CFG);
  }

  // CONSISTENCIA (CV): tabla a lo ancho
  if (ss.cv.length) {
    const badge = (v) => v < 0.9 ? ["#2ECC71", "Estable"] : v < 1.3 ? ["#FFC400", "Media"] : ["#FF5252", "Variable"];
    const rows = ss.cv.map((r) => {
      const [c, t] = badge(r.cv);
      return `<tr><td>${drvChip(r.code, r.color)}</td><td class="num">${r.laps}</td>
        <td class="num">${r.median_label}</td><td class="num">${r.sigma.toFixed(3)}</td>
        <td class="num">${r.iqr.toFixed(3)}</td>
        <td class="num"><b style="color:${c}">${r.cv.toFixed(2)}%</b> <small style="color:${c}">${t}</small></td></tr>`;
    }).join("");
    zone.appendChild(el(`<div class="card table-wrap" style="margin-bottom:20px">
      <div class="chart-head" style="padding:0 0 8px">
      <h2>Consistencia (CV)</h2><span class="sub">CV = σ / mediana · menor = más regular</span></div>
      <table><thead><tr><th>Piloto</th><th class="num">Vueltas</th><th class="num">Mediana</th>
      <th class="num">σ</th><th class="num">IQR</th><th class="num">CV</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`));
  }

  // RESUMEN DE RITMO: tarjetas por piloto (vueltas limpias)
  if (ss.cv.length) {
    const mejor = Math.min(...ss.cv.map((r) => r.median));
    zone.appendChild(el(`<div class="section-title">Resumen de ritmo
      <small> · vueltas limpias por piloto (sin pits ni atípicas)</small></div>`));
    const cards = [...ss.cv].sort((a, b) => a.median - b.median).map((r) => `
      <div class="card tile" style="--tc:${r.color}">
        <div class="label">${r.code}</div>
        <div class="value" style="font-size:23px">${r.median_label}</div>
        <div class="hint">${r.median === mejor ? "MEJOR RITMO" : `+${(r.median - mejor).toFixed(3)}s vs mejor`}
          · ${r.laps} vueltas<br>σ ${r.sigma.toFixed(3)} · IQR ${r.iqr.toFixed(3)}</div>
      </div>`).join("");
    zone.appendChild(el(`<div class="tiles" style="margin-bottom:20px">${cards}</div>`));
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

  // GESTIÓN DE NEUMÁTICOS: gantt de stints
  if (ss.stints && ss.stints.length) {
    const orden = [...new Set(ss.stints.map((x) => x.code))];
    const cGt = chartCard({
      title: "Gestión de neumáticos", sub: "stints por piloto · color = compuesto",
      tips: ["<b>¿Un bloque más largo que los vecinos?</b> → estiró el stint: posible overcut.",
             "<b>¿Paró antes que su rival?</b> → intento de undercut."],
      legendHtml: `<div class="compound-legend">${Object.entries(COMP_COLORS).map(([k, v]) =>
        `<span class="chip" style="--cc:${v}"><i></i>${k}</span>`).join("")}</div>`,
    });
    zone.appendChild(cGt.card);
    zone.appendChild(el(`<div style="height:20px"></div>`));
    Plotly.newPlot(cGt.plot, ss.stints.map((st) => ({
      type: "bar", orientation: "h", y: [st.code], base: [st.from - 1],
      x: [st.to - st.from + 1], showlegend: false,
      marker: { color: st.color, line: { color: "#11141b", width: 2 } },
      hovertemplate: `<b>${st.code}</b> · ${st.compound}<br>V${st.from}–V${st.to}<extra></extra>`,
    })), baseLayout({
      height: Math.max(300, orden.length * 34 + 120), barmode: "stack", bargap: 0.35,
      margin: { l: 52, r: 16, t: 14, b: 44 },
      xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } } },
      yaxis: { ...baseLayout().yaxis, categoryorder: "array",
               categoryarray: [...orden].reverse(), gridcolor: "rgba(0,0,0,0)" },
    }), PLOTLY_CFG);
  }

  // degradación por stint: filtro de compuesto + gráfica + tabla
  if (ss.deg && ss.deg.length) {
    const comps = [...new Set(ss.deg.map((r) => r.compound))];
    const degSel = state.compFilter && comps.includes(state.compFilter)
      ? ss.deg.filter((r) => r.compound === state.compFilter) : ss.deg;
    const fpills = `<div class="pills" style="margin-bottom:14px">
      <button class="pill ${!state.compFilter ? "active" : ""}" data-c="">TODAS</button>
      ${comps.map((c) => `<button class="pill ${state.compFilter === c ? "active" : ""}"
        data-c="${c}" style="--cc:${COMP_COLORS[c] || "#6b7280"}">${c}</button>`).join("")}</div>`;
    ss.deg = degSel;
    const peor = [...ss.deg].sort((a, b) => b.slope - a.slope)[0];
    zone.appendChild(el(`<div class="section-title">Análisis de stint y degradación
      <small> · Mayor degradación: ${peor.code} en el stint ${peor.stint} (${peor.compound}): +${(peor.slope * 1000).toFixed(0)} ms/vuelta</small></div>`));
    const pillsEl = el(fpills);
    pillsEl.querySelectorAll("[data-c]").forEach((b) => {
      b.onclick = () => { state.compFilter = b.dataset.c || null; rerender(); };
    });
    zone.appendChild(pillsEl);

    // ritmo mediano por stint (marcador = compuesto, línea = piloto)
    const cSt = chartCard({
      title: "Ritmo mediano por stint", sub: "cada punto = un stint · color del punto = compuesto",
      tips: ["<b>¿El punto siguiente más abajo?</b> → mejoró con la goma nueva o el coche más ligero.",
             "<b>¿Puntos del mismo compuesto a alturas distintas entre pilotos?</b> → gestión, no goma."],
    });
    zone.appendChild(cSt.card);
    zone.appendChild(el(`<div style="height:20px"></div>`));
    const porPiloto = {};
    degSel.forEach((r) => { (porPiloto[r.code] = porPiloto[r.code] || []).push(r); });
    const stTraces = Object.entries(porPiloto).map(([code, rows]) => ({
      type: "scatter", mode: "lines+markers", name: code,
      x: rows.map((r) => r.stint), y: rows.map((r) => r.median),
      line: { color: rows[0].color, width: 1.8 },
      marker: { size: 11, color: rows.map((r) => r.comp_color),
                line: { color: "#11141b", width: 1.5 } },
      customdata: rows.map((r) => [fmtLap(r.median), r.compound, (r.slope * 1000).toFixed(0)]),
      hovertemplate: `<b>${code}</b> · stint %{x} (%{customdata[1]})<br>mediana %{customdata[0]} · deg %{customdata[2]} ms/vuelta<extra></extra>`,
    }));
    const ttSt = timeTicks(degSel.map((r) => r.median));
    Plotly.newPlot(cSt.plot, stTraces, baseLayout({
      height: 440, margin: { l: 64, r: 14, t: 14, b: 44 },
      xaxis: { ...baseLayout().xaxis, title: { text: "STINT", font: { size: 10 } }, dtick: 1 },
      yaxis: { ...baseLayout().yaxis, ...ttSt },
      legend: { orientation: "h", y: -0.14, font: { size: 10.5 } },
    }), PLOTLY_CFG);
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
      summary: (ss.grid[0] && ss.grid[0].delta > 0)
        ? `Mayor remontada del grupo: ${ss.grid[0].code} (P${ss.grid[0].grid} → P${ss.grid[0].pos}, +${ss.grid[0].delta}).` : "",
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
      summary: (() => { let mx = 0, quien = "";
        ss.trap.drivers.forEach((c, i) => { const v = Math.max(...ss.trap.z[i].filter(Boolean));
          if (v > mx) { mx = v; quien = c; } });
        return `Récord del speed trap del grupo: ${mx.toFixed(0)} km/h de ${quien}.`; })(),
      tips: ["<b>¿Una fila que se enfría (azul) al final?</b> → gestionaba o perdió motor/rebufo.",
             "<b>¿Columna entera fría?</b> → vuelta lenta de todos: SC o lluvia.",
             "<b>¿Un punto rojo aislado?</b> → rebufo perfecto o DRS en esa vuelta."],
    });
    zone.appendChild(cTr.card);
    zone.appendChild(el(`<div style="height:18px"></div>`));
    const planos = ss.trap.z.flat().filter((v) => v != null).sort((a, b) => a - b);
    const zmin = planos[Math.floor(planos.length * 0.04)] || 0;
    Plotly.newPlot(cTr.plot, [{
      type: "heatmap", x: ss.trap.laps, y: ss.trap.drivers, z: ss.trap.z,
      colorscale: "Turbo", hoverongaps: false, zmin, zmax: planos[planos.length - 1],
      xgap: 2, ygap: 3,
      texttemplate: "%{z:.0f}", textfont: { color: "#ffffff", size: 10.5,
        family: "Inter Black, Inter, sans-serif" },
      hovertemplate: "<b>%{y}</b> · V%{x}<br>%{z:.0f} km/h<extra></extra>",
      colorbar: { thickness: 12, outlinewidth: 0,
        tickfont: { size: 10, color: "#9aa0aa" } },
    }], baseLayout({
      height: Math.max(420, ss.trap.drivers.length * 46 + 150),
      margin: { l: 56, r: 70, t: 14, b: 44 },
      xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } }, dtick: 2 },
      yaxis: { ...baseLayout().yaxis, autorange: "reversed", gridcolor: "rgba(0,0,0,0)",
               tickfont: { size: 11 } },
    }), PLOTLY_CFG);
  }

  // TIEMPOS POR VUELTA (TABLA) — desplegable
  if (ss.evo.length) {
    const byLap = {};
    ss.evo.forEach((e) => e.points.forEach((p) => {
      (byLap[p.lap] = byLap[p.lap] || {})[e.code] = p;
    }));
    const lapsL = Object.keys(byLap).map(Number).sort((a, b) => a - b);
    const head = `<tr><th class="num">V</th>${ss.evo.map((e) =>
      `<th>${drvChip(e.code, e.color)}</th>`).join("")}</tr>`;
    const rows = lapsL.map((l) => `<tr><td class="num"><b>${l}</b></td>${ss.evo.map((e) => {
      const p = byLap[l][e.code];
      if (!p) return "<td class=num>—</td>";
      const st = p.out ? "text-decoration:line-through;color:var(--ink3)" : "";
      return `<td class="num" style="${st}"><span style="color:${COMP_COLORS[p.comp] || "#6b7280"}">●</span> ${fmtLap(p.t)}${p.pit ? " ◆" : ""}</td>`;
    }).join("")}</tr>`).join("");
    zone.appendChild(el(`<details class="card" style="margin-bottom:20px">
      <summary style="cursor:pointer;font-weight:800;font-size:12.5px;letter-spacing:1.4px">
        TIEMPOS POR VUELTA (TABLA) · ● compuesto · ◆ pit · tachado = atípica</summary>
      <div class="table-wrap" style="margin-top:12px;max-height:560px;overflow:auto">
      <table><thead>${head}</thead><tbody>${rows}</tbody></table></div></details>`));
  }
}

function rgba(hex, a) {
  const r = parseInt(hex.slice(1, 3), 16), g = parseInt(hex.slice(3, 5), 16),
        b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${a})`;
}

function linfit(xs, ys) {
  const n = xs.length;
  let Sx = 0, Sy = 0, Sxy = 0, Sxx = 0;
  for (let i = 0; i < n; i++) { Sx += xs[i]; Sy += ys[i]; Sxy += xs[i] * ys[i]; Sxx += xs[i] * xs[i]; }
  const b1 = (n * Sxy - Sx * Sy) / (n * Sxx - Sx * Sx);
  return [b1, (Sy - b1 * Sx) / n];
}

function zoomGapPills(card, plot) {
  const z = el(`<div class="pills" style="padding:0 18px 12px">
    <button class="pill active">TODO</button>
    <button class="pill">CABEZA · 0-60s</button>
    <button class="pill">0-180s</button></div>`);
  card.insertBefore(z, card.querySelector(".chart-summary") || card.querySelector(".chart-guide"));
  const set = (rango, btn) => {
    z.querySelectorAll(".pill").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    Plotly.relayout(plot, rango ? { "yaxis.range": rango }
                                : { "yaxis.autorange": "reversed" });
  };
  const [b1, b2, b3] = z.querySelectorAll("button");
  b1.onclick = () => set(null, b1);
  b2.onclick = () => set([60, -2], b2);
  b3.onclick = () => set([180, -2], b3);
}

/* ───────────────────────────── vista EQUIPOS (evolución de la temporada) */
function filtrarEquipos(raw, selSet) {
  const teams = raw.teams.filter((t) => selSet.has(t.team));
  const completo = teams.length === raw.teams.length;
  let conv = completo ? raw.conv : null;
  if (!completo && teams.length >= 3) {
    // recalcula la convergencia SOLO con los equipos elegidos
    const rs = [], sig = [];
    raw.rounds.forEach((r, i) => {
      const vals = teams.map((t) => t.deficit[i]).filter((v) => v != null);
      if (vals.length >= 3) {
        const m = vals.reduce((a, b) => a + b, 0) / vals.length;
        sig.push(+Math.sqrt(vals.reduce((a, v) => a + (v - m) ** 2, 0) / (vals.length - 1)).toFixed(3));
        rs.push(r);
      }
    });
    if (sig.length >= 3) {
      const [b1, b0] = linfit(rs, sig);
      conv = { rounds: rs, sigma: sig, trend: rs.map((r) => +(b0 + b1 * r).toFixed(3)),
               slope: +b1.toFixed(4) };
    }
  }
  let huella = raw.huella;
  if (huella && !completo) {
    const keep = huella.teams.map((t, i) => [t, i]).filter(([t]) => selSet.has(t));
    huella = { ...huella, teams: keep.map(([t]) => t), z: keep.map(([, i]) => huella.z[i]) };
  }
  return { ...raw, teams, conv, huella, _completo: completo };
}

async function viewEquipos() {
  skeleton([46, 120, 500]);
  if (!state.teamSource) state.teamSource = "quali";
  state._tcache = state._tcache || {};
  const key = `${state.year}|${state.teamSource}`;
  const raw = state._tcache[key] || (state._tcache[key] =
    await api(`/teams/${state.year}?source=${state.teamSource}`));
  $view.innerHTML = "";
  $view.appendChild(seasonPills(state.year, (y) => { state.year = y; state.teamSel = null; viewEquipos(); }));

  const src = el(`<div class="pills" style="margin-bottom:14px">
    <button class="pill ${state.teamSource === "quali" ? "active" : ""}">QUALY (potencial a 1 vuelta)</button>
    <button class="pill ${state.teamSource === "race" ? "active" : ""}">CARRERA (mejor vuelta)</button></div>`);
  const [bq, br] = src.querySelectorAll("button");
  bq.onclick = () => { state.teamSource = "quali"; viewEquipos(); };
  br.onclick = () => { state.teamSource = "race"; viewEquipos(); };
  $view.appendChild(src);

  // chips de equipos: elige uno o varios para el análisis
  const todos = raw.teams.map((t) => t.team);
  const selArr = (state.teamSel && state.teamSel.length)
    ? state.teamSel.filter((t) => todos.includes(t)) : [...todos];
  const selSet = new Set(selArr);
  if (raw.teams.length) {
    const chipsCard = el(`<div class="card" style="margin-bottom:18px">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:10px">
        <span style="font-size:10px;letter-spacing:2px;color:var(--ink3);font-weight:700">
          EQUIPOS · elige uno o varios para el análisis</span>
        <button class="pill" id="teamTodos">TODOS</button></div>
      <div class="drv-chips"></div></div>`);
    const wrap = chipsCard.querySelector(".drv-chips");
    raw.teams.forEach((t) => {
      const on = selSet.has(t.team);
      const chip = el(`<span class="drv-chip ${on ? "on" : ""}" style="--cc:${t.color}">
        <i></i>${t.team}</span>`);
      chip.onclick = () => {
        let sel = [...selArr];
        if (sel.includes(t.team)) { if (sel.length > 1) sel = sel.filter((x) => x !== t.team); }
        else sel.push(t.team);
        state.teamSel = sel.length === todos.length ? null : sel;
        viewEquipos();
      };
      wrap.appendChild(chip);
    });
    chipsCard.querySelector("#teamTodos").onclick = () => { state.teamSel = null; viewEquipos(); };
    $view.appendChild(chipsCard);
  }

  const d = filtrarEquipos(raw, selSet);

  if (!d.teams.length) {
    $view.appendChild(el(`<div class="empty">No hay ${state.teamSource === "quali" ? "clasificaciones" : "carreras"}
      de ${state.year} en la base.</div>`));
    return;
  }

  // resumen ejecutivo automático
  if (d.summary) {
    $view.appendChild(el(`<div class="card" style="margin-bottom:20px">
      <div class="chart-head" style="padding:0 0 6px"><h2>Resumen ejecutivo · ${state.year}</h2>
      <span class="sub">tras ${d.n_rounds} rondas · se redacta solo con los datos${d._completo ? "" : " · calculado sobre TODO el campo"}</span></div>
      ${d.summary.map((p) => `<div class="chart-summary" style="margin:8px 0 0">${p}</div>`).join("")}
    </div>`));
  }

  const conSlope = d.teams.filter((t) => t.slope != null);

  // 1) evolución del déficit al pole
  const c1 = chartCard({
    title: "Déficit % al pole por equipo",
    sub: "0% = hizo la pole · comparable entre circuitos",
    tips: ["<b>¿Línea que baja?</b> → el equipo se acerca a la referencia: sus mejoras funcionan.",
           "<b>¿Pico aislado?</b> → suele ser efecto circuito o una qualy con lluvia; busca la tendencia, no el punto.",
           "Clic en la leyenda para ocultar equipos; doble clic para aislar uno."],
  });
  $view.appendChild(c1.card);
  $view.appendChild(el(`<div style="height:20px"></div>`));
  Plotly.newPlot(c1.plot, d.teams.map((t) => ({
    type: "scatter", mode: "lines+markers", name: t.team,
    x: d.labels, y: t.deficit, connectgaps: false,
    line: { color: t.color, width: 2.2 }, marker: { size: 7 },
    hovertemplate: `<b>${t.team}</b> · %{x}<br>+%{y:.2f}% al pole<extra></extra>`,
  })), baseLayout({
    height: 560, hovermode: "x unified",
    margin: { l: 58, r: 16, t: 14, b: 60 },
    xaxis: { ...baseLayout().xaxis, tickangle: -32, tickfont: { size: 10 } },
    yaxis: { ...baseLayout().yaxis, title: { text: "DÉFICIT VS POLE (%)", font: { size: 10 } },
             ticksuffix: "%" },
    legend: { orientation: "h", y: -0.24, font: { size: 10.5 } },
  }), PLOTLY_CFG);

  // 2) déficit vs la mediana del campo (des-ancla al líder)
  const c2 = chartCard({
    title: "Déficit % contra la MEDIANA del campo",
    sub: "negativo = más rápido que el equipo típico · aquí el líder por fin tiene forma",
    tips: ["<b>¿El líder baja aquí?</b> → se está escapando del pelotón aunque siempre haga la pole (eso era invisible en la gráfica anterior).",
           "<b>¿Un equipo 'mejoraba' al pole pero no a la mediana?</b> → en realidad el líder aflojó; no fue mérito propio."],
  });
  $view.appendChild(c2.card);
  $view.appendChild(el(`<div style="height:20px"></div>`));
  Plotly.newPlot(c2.plot, d.teams.map((t) => ({
    type: "scatter", mode: "lines+markers", name: t.team,
    x: d.labels, y: t.deficit_med, connectgaps: false,
    line: { color: t.color, width: 2.2 }, marker: { size: 7 },
    hovertemplate: `<b>${t.team}</b> · %{x}<br>%{y:+.2f}% vs mediana<extra></extra>`,
  })), baseLayout({
    height: 540, hovermode: "x unified",
    margin: { l: 58, r: 16, t: 14, b: 60 },
    xaxis: { ...baseLayout().xaxis, tickangle: -32, tickfont: { size: 10 } },
    yaxis: { ...baseLayout().yaxis, title: { text: "VS MEDIANA (%)", font: { size: 10 } },
             ticksuffix: "%", zeroline: true, zerolinecolor: "rgba(255,255,255,.35)" },
    legend: { orientation: "h", y: -0.24, font: { size: 10.5 } },
  }), PLOTLY_CFG);

  // 3) pendiente de desarrollo + 4) mapa de credibilidad
  if (conSlope.length >= 2) {
    const row = el(`<div class="grid cols-2" style="margin-bottom:20px"></div>`);
    $view.appendChild(row);

    const c3 = chartCard({
      title: "Pendiente de desarrollo (β₁)",
      sub: "cambio del déficit por carrera · negativo = mejora",
      tips: ["<b>Barra verde hacia la izquierda</b> → recorta % al pole cada carrera.",
             "Con pocas rondas una barra puede estar dominada por 1-2 fines de semana atípicos: crúzala con el mapa de credibilidad."],
    });
    row.appendChild(c3.card);
    const ordSlope = [...conSlope].sort((a, b) => b.slope - a.slope);
    Plotly.newPlot(c3.plot, [{
      type: "bar", orientation: "h",
      y: ordSlope.map((t) => t.team), x: ordSlope.map((t) => t.slope),
      marker: { color: ordSlope.map((t) => t.slope < 0 ? "#2ECC71" : "#FF5252"),
                line: { color: "#11141b", width: 2 } },
      text: ordSlope.map((t) => ` ${t.slope > 0 ? "+" : ""}${t.slope.toFixed(3)} `),
      textposition: "outside", textfont: { size: 10, color: "#9aa0aa" },
      hovertemplate: "<b>%{y}</b> · %{x:+.4f} %/carrera<extra></extra>",
    }], baseLayout({
      height: Math.max(420, ordSlope.length * 34 + 130),
      margin: { l: 110, r: 60, t: 14, b: 44 },
      xaxis: { ...baseLayout().xaxis, title: { text: "Δ DÉFICIT % POR CARRERA", font: { size: 10 } },
               zeroline: true, zerolinecolor: "rgba(255,255,255,.35)" },
      yaxis: { ...baseLayout().yaxis, gridcolor: "rgba(0,0,0,0)", tickfont: { size: 11 } },
    }), PLOTLY_CFG);

    const c4 = chartCard({
      title: "Mapa de credibilidad · pendiente vs R²",
      sub: "arriba-izquierda = desarrollo real y sostenido",
      tips: ["<b>Izquierda + arriba (R² alto)</b> → mejora creíble y sostenida.",
             "<b>Izquierda + abajo</b> → mejora, pero errática: espera más datos.",
             "<b>Derecha + arriba</b> → declive consistente: foco rojo confirmado.",
             "<b>Derecha + abajo</b> → probablemente ruido o efecto circuito."],
    });
    row.appendChild(c4.card);
    Plotly.newPlot(c4.plot, [{
      type: "scatter", mode: "markers+text",
      x: conSlope.map((t) => t.slope), y: conSlope.map((t) => t.r2),
      text: conSlope.map((t) => t.team), textposition: "top center",
      textfont: { size: 10.5, color: conSlope.map((t) => t.color) },
      marker: { size: 13, color: conSlope.map((t) => t.color),
                line: { color: "#11141b", width: 1.5 } },
      hovertemplate: "<b>%{text}</b><br>β₁ %{x:+.4f} · R² %{y:.2f}<extra></extra>",
    }], baseLayout({
      height: Math.max(420, ordSlope.length * 34 + 130), showlegend: false,
      shapes: [
        { type: "line", x0: 0, x1: 0, yref: "paper", y0: 0, y1: 1,
          line: { color: "rgba(255,255,255,.25)", dash: "dash", width: 1 } },
        { type: "line", xref: "paper", x0: 0, x1: 1, y0: 0.5, y1: 0.5,
          line: { color: "rgba(255,255,255,.18)", dash: "dot", width: 1 } },
      ],
      annotations: [{ xref: "paper", x: 0.99, y: 0.52, text: "umbral de credibilidad",
                      showarrow: false, font: { size: 9, color: "#6b7280" }, xanchor: "right" }],
      margin: { l: 56, r: 16, t: 14, b: 46 },
      xaxis: { ...baseLayout().xaxis, title: { text: "PENDIENTE β₁ (− = MEJORA)", font: { size: 10 } },
               showgrid: true, gridcolor: "rgba(255,255,255,.05)", griddash: "dot" },
      yaxis: { ...baseLayout().yaxis, title: { text: "R² DEL AJUSTE", font: { size: 10 } },
               range: [-0.05, 1.08] },
    }), PLOTLY_CFG);
  }

  // 5) huella de circuito
  if (d.huella && d.huella.teams.length) {
    const cH = chartCard({
      title: "Huella de circuito",
      sub: "residuo vs el promedio propio · azul = mejor que su normal, rojo = peor",
      tips: ["<b>Celda azul intensa aislada</b> → esa pista le sienta al coche (carga, tracción, bumps).",
             "<b>Columna entera teñida</b> → qualy atípica para todos (lluvia/banderas): ruido de sesión, no efecto circuito.",
             "Cruza esto con la pendiente: si el 'empeoramiento' de un equipo cae en pistas de un mismo tipo, es efecto circuito, no declive."],
    });
    $view.appendChild(cH.card);
    $view.appendChild(el(`<div style="height:20px"></div>`));
    Plotly.newPlot(cH.plot, [{
      type: "heatmap", x: d.huella.labels, y: d.huella.teams, z: d.huella.z,
      colorscale: "RdBu", reversescale: true, zmid: 0, xgap: 2, ygap: 3,
      texttemplate: "%{z:.2f}", textfont: { color: "#ffffff", size: 10 },
      hovertemplate: "<b>%{y}</b> · %{x}<br>%{z:+.2f}% vs su promedio<extra></extra>",
      colorbar: { thickness: 12, outlinewidth: 0, tickfont: { size: 10, color: "#9aa0aa" } },
    }], baseLayout({
      height: Math.max(420, d.huella.teams.length * 44 + 160),
      margin: { l: 110, r: 70, t: 14, b: 70 },
      xaxis: { ...baseLayout().xaxis, tickangle: -32, tickfont: { size: 10 } },
      yaxis: { ...baseLayout().yaxis, autorange: "reversed", gridcolor: "rgba(0,0,0,0)",
               tickfont: { size: 11 } },
    }), PLOTLY_CFG);
  }

  // 6) convergencia + 7) proyección
  const row2 = el(`<div class="grid cols-2"></div>`);
  $view.appendChild(row2);
  if (d.conv) {
    const c6 = chartCard({
      title: "Convergencia de la parrilla (σ por ronda)",
      sub: "σ bajando = el campo se aprieta · σ subiendo = alguien se escapa",
      summary: `Velocidad de convergencia: ${d.conv.slope > 0 ? "+" : ""}${d.conv.slope} puntos de σ por carrera → la parrilla ${d.conv.slope < 0 ? "se APRIETA" : "se ABRE"}.`,
      tips: ["La línea punteada es la tendencia: su pendiente resume la era reglamentaria en un número.",
             "<b>¿σ cae?</b> → cada décima de desarrollo mueve más posiciones: la qualy se vuelve lotería de centésimas."],
    });
    row2.appendChild(c6.card);
    Plotly.newPlot(c6.plot, [
      { type: "scatter", mode: "lines+markers", name: "σ del déficit",
        x: d.conv.rounds, y: d.conv.sigma, line: { color: "#5B8FD9", width: 2.2 },
        marker: { size: 7 },
        hovertemplate: "Ronda %{x}<br>σ = %{y:.3f}%<extra></extra>" },
      { type: "scatter", mode: "lines", name: "tendencia",
        x: d.conv.rounds, y: d.conv.trend,
        line: { color: "#FFC400", width: 2, dash: "dash" }, hoverinfo: "skip" },
    ], baseLayout({
      height: 460, margin: { l: 56, r: 16, t: 14, b: 44 },
      xaxis: { ...baseLayout().xaxis, title: { text: "RONDA", font: { size: 10 } }, dtick: 1 },
      yaxis: { ...baseLayout().yaxis, title: { text: "σ DEL DÉFICIT (%)", font: { size: 10 } } },
      legend: { orientation: "h", y: 1.1, x: 1, xanchor: "right" },
    }), PLOTLY_CFG);
  }
  const conProy = conSlope.filter((t) => t.proy != null)
    .sort((a, b) => a.proy - b.proy);
  if (conProy.length) {
    const c7 = chartCard({
      title: `Proyección ingenua · Ronda ${d.next_round}`,
      sub: "extrapolación de la tendencia pura, sin efecto circuito",
      tips: ["Es el <b>baseline</b>: cuando pase la carrera real, compara — si un modelo sofisticado no le gana a esta recta, no vale su complejidad.",
             "El déficit proyectado se acota en 0 (nadie puede ser 'más rápido que la pole' por definición)."],
    });
    row2.appendChild(c7.card);
    const rev = [...conProy].reverse();
    Plotly.newPlot(c7.plot, [{
      type: "bar", orientation: "h",
      y: rev.map((t) => t.team), x: rev.map((t) => t.proy),
      marker: { color: rev.map((t) => t.color), line: { color: "#11141b", width: 2 } },
      text: rev.map((t) => ` ${t.proy.toFixed(2)}% `), textposition: "outside",
      textfont: { size: 10, color: "#9aa0aa" },
      hovertemplate: "<b>%{y}</b> · déficit proyectado %{x:.3f}%<extra></extra>",
    }], baseLayout({
      height: 460, margin: { l: 110, r: 62, t: 14, b: 44 },
      xaxis: { ...baseLayout().xaxis, title: { text: "DÉFICIT PROYECTADO (%)", font: { size: 10 } } },
      yaxis: { ...baseLayout().yaxis, gridcolor: "rgba(0,0,0,0)", tickfont: { size: 11 } },
    }), PLOTLY_CFG);
  }
}

/* ───────────────────────────── router */
const VIEWS = { temporada: viewTemporada, carrera: viewCarrera, h2h: viewH2H,
                analisis: viewAnalisis, equipos: viewEquipos };

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

function toast(msg, ms = 6000) {
  document.querySelectorAll(".toast").forEach((t) => t.remove());
  const t = el(`<div class="toast">${msg}</div>`);
  document.body.appendChild(t);
  setTimeout(() => t.remove(), ms);
}

async function actualizarTodo() {
  const b = document.getElementById("btnUpdate");
  b.classList.add("busy");
  b.textContent = "⏳ Buscando sesiones nuevas…";
  await fetch("/api/update", { method: "POST" });
  const poll = async () => {
    const st = await api("/update/status");
    if (st.running) {
      const ultimo = st.log[st.log.length - 1] || "…";
      b.textContent = `⏳ ${ultimo}`.slice(0, 42);
      return setTimeout(poll, 2500);
    }
    b.classList.remove("busy");
    b.textContent = "⟳ ACTUALIZAR";
    if (st.found === 0) toast("La base ya está al día: no hay sesiones nuevas.");
    else toast(`Actualización lista: ${st.ok} sesión(es) nueva(s) en la base`
               + (st.fail ? ` · ${st.fail} fallaron` : "") + ". Refrescando…");
    state.schedCache = {};
    state._tcache = {};
    route();
  };
  setTimeout(poll, 1500);
}

(async function init() {
  const bu = document.getElementById("btnUpdate");
  if (bu) bu.onclick = (e) => { e.preventDefault(); actualizarTodo(); };
  try {
    const meta = await api("/meta");
    state.seasons = meta.seasons;
    state.year = meta.seasons.length ? meta.seasons[0].year : null;
  } catch (e) { /* la ruta mostrará el error */ }
  window.addEventListener("hashchange", route);
  route();
})();
