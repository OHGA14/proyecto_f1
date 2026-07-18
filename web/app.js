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
  // modebar solo al pasar el cursor: menos ruido visual permanente
  displayModeBar: "hover", displaylogo: false, responsive: true,
  modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d", "toggleSpikelines",
                           "hoverClosestCartesian", "hoverCompareCartesian"],
  doubleClick: "reset",
};

const cssVar = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const accLine = (a = 0.5) => `rgba(${cssVar("--red-rgb") || "255,45,45"},${a})`;

const baseLayout = (extra = {}) => ({
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: cssVar("--font-chart") || "Inter, sans-serif", color: "#ced3dc", size: 12.5 },
  margin: { l: 58, r: 70, t: 16, b: 44 },
  xaxis: { showgrid: false, zeroline: false, color: "#aeb5c0" },
  yaxis: { gridcolor: "rgba(255,255,255,.06)", griddash: "dot", zeroline: false, color: "#aeb5c0" },
  hoverlabel: { bgcolor: "#1a1e27", bordercolor: "#3a3d47", font: { color: "#f3f4f6", size: 12.5 } },
  ...extra,
});

/* Tarjeta de gráfica con la firma de la casa: resumen calculado + guía tip. */
function chartCard({ title, sub = "", summary = "", tips = [], legendHtml = "" }) {
  const card = el(`<div class="card chart-card">
    <div class="chart-head">
      <div class="chart-head-row"><h2>${title}</h2>
        ${tips.length ? `<button class="guide-btn" title="Abrir la guía de lectura">ⓘ CÓMO LEERLA</button>` : ""}</div>
      ${sub ? `<span class="sub">${sub}</span>` : ""}
    </div>
    <div class="chart-body"><div class="plot"></div></div>
    ${legendHtml}
    ${summary ? `<div class="chart-summary">${summary}</div>` : ""}
    ${tips.length ? `<div class="chart-guide" hidden>
      <ul>${tips.map((t) => `<li>${t}</li>`).join("")}</ul></div>` : ""}
  </div>`);
  if (tips.length) {
    const btn = card.querySelector(".guide-btn");
    const guia = card.querySelector(".chart-guide");
    btn.onclick = () => { guia.hidden = !guia.hidden; btn.classList.toggle("on", !guia.hidden); };
  }
  return { card, plot: card.querySelector(".plot") };
}

/* altura proporcional a la cantidad de datos: pocas filas, gráfica compacta */
function chartHeight({ items = 0, min = 260, max = 520, per = 36 }) {
  return Math.min(max, Math.max(min, items * per + 140));
}

/* panel sincronizado: las gráficas vs distancia comparten zoom y cursor.
   La bandera `lock` evita el bucle infinito (mi relayout dispara el tuyo). */
function sincronizaX(plots) {
  const gds = plots.filter(Boolean);
  if (gds.length < 2) return;
  let lock = false;
  gds.forEach((gd) => {
    gd.on("plotly_relayout", (ev) => {
      if (lock) return;
      const a = ev["xaxis.range[0]"], b = ev["xaxis.range[1]"];
      const auto = ev["xaxis.autorange"];
      if (a === undefined && auto === undefined) return;
      lock = true;
      Promise.all(gds.filter((o) => o !== gd).map((o) =>
        Plotly.relayout(o, auto ? { "xaxis.autorange": true }
                                : { "xaxis.range[0]": a, "xaxis.range[1]": b })))
        .finally(() => { lock = false; });
    });
    gd.on("plotly_hover", (ev) => {
      if (lock || !ev.points || !ev.points.length) return;
      const x = ev.points[0].x;
      gds.forEach((o) => {
        if (o !== gd) try { Plotly.Fx.hover(o, { xval: x }); } catch (e) { /* pestaña oculta */ }
      });
    });
    gd.on("plotly_unhover", () => {
      gds.forEach((o) => {
        if (o !== gd) try { Plotly.Fx.unhover(o); } catch (e) { /* pestaña oculta */ }
      });
    });
  });
}

const skeleton = (hs) => {
  $view.innerHTML = "";
  hs.forEach((h) => $view.appendChild(el(`<div class="skeleton-block" style="height:${h}px"></div>`)));
};

const heroTitle = (t, sub) =>
  el(`<div class="hero"><h1>${t}</h1>${sub ? `<div class="sub">${sub}</div>` : ""}</div>`);

const drvChip = (code, color, name = "") =>
  `<span class="drv" style="--cc:${color}"><i></i>${code}${name ? ` <small>${name}</small>` : ""}</span>`;

/* bandera del gran premio, por nombre del GP (cubre calendarios 2018-2026) */
const BANDERAS = [
  [/bahrain|sakhir/i, "🇧🇭"], [/saudi/i, "🇸🇦"], [/australia/i, "🇦🇺"],
  [/japan/i, "🇯🇵"], [/chin/i, "🇨🇳"], [/miami|united states|vegas/i, "🇺🇸"],
  [/emilia|italian|tuscan/i, "🇮🇹"], [/monaco/i, "🇲🇨"], [/canad/i, "🇨🇦"],
  [/spanish|spain|madrid|barcelona/i, "🇪🇸"], [/austria|styria/i, "🇦🇹"],
  [/british|great britain|70th/i, "🇬🇧"], [/hungar/i, "🇭🇺"], [/belgia/i, "🇧🇪"],
  [/dutch|netherlands/i, "🇳🇱"], [/azerbaijan|baku/i, "🇦🇿"], [/singapore/i, "🇸🇬"],
  [/mexic/i, "🇲🇽"], [/paulo|brazil/i, "🇧🇷"], [/qatar/i, "🇶🇦"],
  [/abu dhabi/i, "🇦🇪"], [/french|france/i, "🇫🇷"], [/german|eifel/i, "🇩🇪"],
  [/portug/i, "🇵🇹"], [/turk/i, "🇹🇷"], [/russia/i, "🇷🇺"], [/europe/i, "🇪🇺"],
];
const banderaGP = (gp) => (BANDERAS.find(([re]) => re.test(gp || "")) || [0, "🏁"])[1];

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
  $view.appendChild(heroTitle("Temporada", `campeonato ${state.year} · clasificación · ritmo puro · récords`));
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
               ticksuffix: "%", zeroline: true, zerolinecolor: accLine(0.5) },
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
  $view.appendChild(heroTitle("Carrera", "elige un gran premio · arranca con su podio y suma los pilotos que quieras"));
  $view.appendChild(seasonPills(state.year, (y) => { state.year = y; state.sid = null; state.carSel = null; viewCarrera(); }));

  if (!races.length) {
    $view.appendChild(el(`<div class="empty">No hay carreras de ${state.year} en la base.</div>`));
    return;
  }
  if (!state.sid || !races.some((r) => r.sid === state.sid)) state.sid = races[races.length - 1].sid;

  const grid = el(`<div class="race-grid" style="margin-bottom:22px"></div>`);
  races.forEach((r) => {
    const c = el(`<div class="card race-card" style="${r.sid === state.sid ? "border-color:rgba(255,60,60,.55)" : ""}">
      <div class="round">RONDA ${r.round}</div><h3>${banderaGP(r.label)} ${r.label}</h3>
      <div class="date">${r.date} · ${r.n_laps} vueltas</div>
      <div class="podium">${r.podium.map((p, i) =>
        `<span class="chip" style="--cc:${p.color}"><i></i>P${i + 1} ${p.code}</span>`).join("")}</div>
    </div>`);
    c.onclick = () => { state.sid = r.sid; state.carSel = null; viewCarrera(); };
    grid.appendChild(c);
  });
  $view.appendChild(grid);

  const d = await api(`/session/detail?sid=${encodeURIComponent(state.sid)}`);

  // podio hero
  $view.appendChild(el(`<div class="section-title">${banderaGP(d.info.gp)} ${d.info.gp} ${d.info.year}
    <small> · ${d.info.date} · ${d.info.n_laps} vueltas · ${d.info.circuit}</small></div>`));
  const podium = d.results.slice(0, 3);
  const estratDe = (code) => {
    const s = (d.strategy || []).find((x) => x.code === code);
    return s ? s.stints.map((st) => st.compound[0]).join(" → ") : null;
  };
  $view.appendChild(el(`<div class="podium-hero" style="margin-bottom:18px">${podium.map((p) => {
    const dp = p.grid ? p.grid - p.pos : null;
    const avance = dp == null ? "" : dp > 0 ? ` · +${dp}` : dp < 0 ? ` · ${dp}` : " · =";
    const estr = estratDe(p.code);
    return `
    <div class="pod" style="--tc:${p.color}"><span class="pos">P${p.pos}</span>
      <div class="code">${p.code}</div><div class="name">${p.name}</div>
      <div class="team">${p.team}${p.pos === 1 ? " · GANADOR" : ""}</div>
      <div class="name" style="margin-top:6px;color:var(--ink2)">${p.grid ? `Salida P${p.grid}${avance}` : ""}${estr ? ` · ${estr}` : ""}</div>
      <div class="team" style="margin-top:4px">mejor vuelta ${p.best_lap}</div></div>`;
  }).join("")}</div>`));

  // chips de pilotos: despejan TODAS las gráficas de la carrera
  const codesR = d.results.map((r) => r.code);
  if (!state.carSel || !state.carSel.some((c) => codesR.includes(c)))
    state.carSel = codesR.slice(0, 3);          // al elegir GP: su podio P1-P2-P3
  const selC = new Set(state.carSel.filter((c) => codesR.includes(c)));
  const F = (arr) => (arr || []).filter((x) => selC.has(x.code));
  const chipsR = el(`<div class="card" style="margin-bottom:18px">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:10px">
      <span style="font-size:10px;letter-spacing:2px;color:var(--ink3);font-weight:700">
        PILOTOS EN LAS GRÁFICAS · arrancas con el podio · la tabla siempre muestra a todos</span>
      <span class="pills">
        <button class="pill" data-n="3">TOP 3</button>
        <button class="pill" data-n="5">TOP 5</button>
        <button class="pill" data-n="10">TOP 10</button>
        <button class="pill" data-n="99">TODOS</button></span></div>
    <div class="drv-chips"></div></div>`);
  chipsR.querySelectorAll("[data-n]").forEach((b) => {
    b.onclick = () => { state.carSel = codesR.slice(0, +b.dataset.n); viewCarrera(); };
  });
  const wrapR = chipsR.querySelector(".drv-chips");
  d.results.forEach((r) => {
    const on = selC.has(r.code);
    const chip = el(`<span class="drv-chip ${on ? "on" : ""}" style="--cc:${r.color}"
      title="${r.name} · P${r.pos}"><i></i>${r.code}</span>`);
    chip.onclick = () => {
      let sel = state.carSel.filter((c) => codesR.includes(c));
      if (sel.includes(r.code)) { if (sel.length > 1) sel = sel.filter((c) => c !== r.code); }
      else sel.push(r.code);
      state.carSel = sel;
      viewCarrera();
    };
    wrapR.appendChild(chip);
  });
  $view.appendChild(chipsR);

  const two = $view;  // las gráficas van a ANCHO COMPLETO, una tras otra
  const pace = F(d.pace);
  const allT = pace.flatMap((p) => p.times);
  // resumen con ALCANCE explícito: tu selección vs toda la carrera
  let sumPace = d.summaries.pace || "";
  {
    const conBest = d.results.filter((r) => r.best_lap_s != null);
    const selBest = conBest.filter((r) => selC.has(r.code));
    if (conBest.length && selBest.length) {
      const bAll = conBest.reduce((a, r) => (r.best_lap_s < a.best_lap_s ? r : a));
      const bSel = selBest.reduce((a, r) => (r.best_lap_s < a.best_lap_s ? r : a));
      sumPace = selC.has(bAll.code)
        ? `MEJOR VUELTA de toda la carrera: ${bAll.best_lap} de ${bAll.code} — está en tu selección.`
        : `Entre tus seleccionados, la MEJOR VUELTA es ${bSel.best_lap} de ${bSel.code}; la de toda la carrera fue ${bAll.best_lap} de ${bAll.code} (no seleccionado).`;
      // la vuelta mínima NO es ritmo sostenido: la mediana responde otra pregunta
      const medDe = (p) => { const s = [...p.times].sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };
      const conMed = pace.filter((p) => p.times.length >= 5);
      if (conMed.length) {
        const mejorMed = conMed.reduce((a, p) => (medDe(p) < medDe(a) ? p : a));
        sumPace += ` MEJOR RITMO MEDIANO entre seleccionados: ${mejorMed.code} (${fmtLap(medDe(mejorMed))}) — una vuelta mínima no sustituye al ritmo sostenido.`;
      }
    }
  }
  const c1 = chartCard({
    title: "Ritmo vuelta a vuelta", sub: "pilotos seleccionados · sin vueltas de pits",
    summary: sumPace,
    tips: [
      "<b>¿Una línea consistentemente abajo?</b> → mejor ritmo APARENTE: el tiempo observado mezcla coche, combustible, goma, tráfico y gestión — compara stints equivalentes antes de concluir.",
      "Cada stint es una traza separada (color del punto = compuesto); los huecos son vueltas excluidas: no se unen con diagonales.",
      "<b>¿Escalones hacia abajo?</b> → goma nueva tras parar; compáralo con la estrategia.",
      "<b>¿Todos suben a la vez?</b> → coche de seguridad o lluvia.",
    ],
  });
  two.appendChild(c1.card);
  two.appendChild(el(`<div style="height:20px"></div>`));
  const tmin = Math.min(...allT), tmax = Math.max(...allT);
  const ticks = [];
  for (let t = Math.ceil(tmin); t <= tmax; t += Math.max(1, Math.round((tmax - tmin) / 5))) ticks.push(t);
  const trazasPace = [];
  const finPace = [];
  pace.forEach((p) => {
    const stintsDe = ((d.strategy || []).find((x) => x.code === p.code) || {}).stints
      || [{ from: -1e9, to: 1e9, compound: "?", color: p.color }];
    let primera = true;
    stintsDe.forEach((st) => {
      const idx = p.laps.map((l, i) => [l, i]).filter(([l]) => l >= st.from && l <= st.to);
      if (!idx.length) return;
      const xsL = [], ysL = [], cdL = [];
      idx.forEach(([l, i], j) => {
        if (j && l - idx[j - 1][0] > 1) { xsL.push(null); ysL.push(null); cdL.push(""); }
        xsL.push(l); ysL.push(p.times[i]); cdL.push(fmtLap(p.times[i]));
      });
      trazasPace.push({ type: "scatter", mode: "lines+markers", name: p.code,
        legendgroup: p.code, showlegend: primera, connectgaps: false,
        x: xsL, y: ysL,
        line: { color: p.color, width: 1.6 },
        marker: { size: 5, color: st.color || p.color, line: { color: "#11141b", width: 1 } },
        customdata: cdL.map((t2) => [t2, st.compound]),
        hovertemplate: `<b>${p.code}</b> · V%{x}<br>%{customdata[0]} · %{customdata[1]}<extra></extra>` });
      primera = false;
    });
    if (p.laps.length)
      finPace.push({ x: p.laps[p.laps.length - 1], y: p.times[p.times.length - 1],
        text: p.code, showarrow: false, xanchor: "left", xshift: 6,
        font: { size: 10, color: p.color } });
  });
  Plotly.newPlot(c1.plot, trazasPace, baseLayout({
    height: 470, margin: { l: 64, r: 46, t: 16, b: 40 },
    annotations: finPace,
    xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } } },
    yaxis: { ...baseLayout().yaxis, tickvals: ticks, ticktext: ticks.map(fmtLap) },
    legend: { orientation: "h", y: -0.18, font: { size: 10.5 } },
  }), PLOTLY_CFG);

  // pits y estrategia (mismo muro que ANÁLISIS)
  const stratF = F(d.strategy);
  if (stratF.length) {
    const pitsBy = {};
    (d.pits || []).forEach((p) => { pitsBy[p.code] = p; });
    const colBy = {};
    d.results.forEach((r) => { colBy[r.code] = r.color; });
    const rowsP = stratF.map((s2) => ({
      code: s2.code, color: colBy[s2.code] || "#9aa0aa",
      segs: s2.stints.map((x) => ({ compound: x.compound, color: x.color,
                                    from: x.from, to: x.to, laps: x.laps })),
      stops: (pitsBy[s2.code] || {}).stops || [],
      totalLost: (pitsBy[s2.code] || {}).total_lost ?? null,
    }));
    two.appendChild(cardMuroPits({ rows: rowsP, summary: d.summaries.strategy || "" }));
    two.appendChild(el(`<div style="height:20px"></div>`));
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
    title: "Speed trap oficial (radar en recta)",
    sub: "rombo = MÁXIMA de la carrera (una sola muestra) · punto hueco = MEDIANA de sus vueltas (lo repetible) · escala ampliada, no inicia en 0",
    tips: ["La MÁXIMA es una sola muestra: puede venir de rebufo, aerodinámica activa en modo recta, despliegue eléctrico, viento o una salida mejor — no identifica la causa por sí sola.",
           "La MEDIANA responde otra pregunta: qué velocidad podía repetir vuelta tras vuelta. Compara las dos.",
           "<b>¿Máxima alta y mediana baja?</b> → el pico fue circunstancial (rebufo/una vuelta); no concluyas configuración."],
  });
  $view.appendChild(el(`<div style="height:18px"></div>`));
  $view.appendChild(c3.card);
  const st = [...d.speedtrap].reverse();
  const xsAll = st.flatMap((s) => [s.vmax, s.vmed].filter((v) => v != null));
  Plotly.newPlot(c3.plot, [
    { type: "scatter", mode: "markers", name: "mediana",
      y: st.map((s) => s.code), x: st.map((s) => s.vmed),
      marker: { size: 8, color: "rgba(0,0,0,0)", symbol: "circle-open",
                line: { color: "#8a94a4", width: 1.6 } },
      customdata: st.map((s) => [s.iqr, s.n]),
      hovertemplate: "<b>%{y}</b> · mediana %{x:.0f} km/h<br>IQR %{customdata[0]} · %{customdata[1]} vueltas<extra></extra>" },
    { type: "scatter", mode: "markers+text", name: "máxima",
      y: st.map((s) => s.code), x: st.map((s) => s.vmax),
      marker: { size: 10, color: st.map((s) => s.color), symbol: "diamond",
                line: { color: "#11141b", width: 1.5 } },
      text: st.map((s) => ` ${s.vmax.toFixed(0)}`), textposition: "middle right",
      textfont: { size: 10, color: "#c8cdd6" },
      hovertemplate: "<b>%{y}</b> · máxima %{x:.0f} km/h<extra></extra>" },
  ], baseLayout({
    height: chartHeight({ items: st.length, min: 280, max: 520, per: 30 }),
    margin: { l: 52, r: 56, t: 12, b: 40 },
    annotations: [{ xref: "paper", yref: "paper", x: 0.005, y: 0.01, xanchor: "left",
      text: "ESCALA AMPLIADA · EJE NO INICIA EN 0", showarrow: false,
      font: { size: 8.5, color: "#77839a" } }],
    xaxis: { ...baseLayout().xaxis, range: [Math.min(...xsAll) - 6, Math.max(...xsAll) + 9],
             title: { text: "KM/H", font: { size: 10 } } },
    yaxis: { ...baseLayout().yaxis, gridcolor: "rgba(0,0,0,0)" },
    legend: { orientation: "h", y: 1.1, x: 1, xanchor: "right", font: { size: 10 } },
    showlegend: true,
  }), PLOTLY_CFG);
}

/* ───────────────────────────── vista H2H */
async function viewH2H() {
  skeleton([70, 110, 420]);
  const drivers = await api("/drivers");
  $view.innerHTML = "";

  $view.appendChild(heroTitle("Head-to-Head", "duelo histórico · delta de mejor vuelta en cada GP común"));
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

  if (!state.h2hSource) state.h2hSource = "race";
  const anios = (state.seasons || []).map((x) => x.year);
  const filtros = el(`<div style="display:flex;gap:18px;flex-wrap:wrap;align-items:center;margin-bottom:16px">
    <span class="pills">
      <button class="pill ${!state.h2hYear ? "active" : ""}" data-y="">TODAS</button>
      ${anios.map((y) => `<button class="pill ${state.h2hYear === y ? "active" : ""}" data-y="${y}">${y}</button>`).join("")}
    </span>
    <span class="pills">
      <button class="pill ${state.h2hSource === "race" ? "active" : ""}" data-s="race">CARRERA (mejor vuelta)</button>
      <button class="pill ${state.h2hSource === "quali" ? "active" : ""}" data-s="quali">QUALY (a una vuelta)</button>
    </span></div>`);
  filtros.querySelectorAll("[data-y]").forEach((b) => {
    b.onclick = () => { state.h2hYear = b.dataset.y ? +b.dataset.y : null; viewH2H(); };
  });
  filtros.querySelectorAll("[data-s]").forEach((b) => {
    b.onclick = () => { state.h2hSource = b.dataset.s; viewH2H(); };
  });
  $view.appendChild(filtros);

  if (window._h2hA === window._h2hB) {
    $view.appendChild(el(`<div class="empty">Elige dos pilotos distintos.</div>`));
    return;
  }
  const d = await api(`/h2h?a=${window._h2hA}&b=${window._h2hB}&source=${state.h2hSource}`
                      + (state.h2hYear ? `&year=${state.h2hYear}` : ""));

  // ¿qué estás viendo? — el alcance y la métrica, sin ambigüedad
  $view.appendChild(el(`<div class="chart-summary" style="margin:0 0 18px">
    <b>¿Qué comparas aquí?</b> A ${d.a ? d.a.code : window._h2hA} y ${d.b ? d.b.code : window._h2hB}
    en <b>cada Gran Premio que corrieron juntos</b> (${d.alcance || "todas las temporadas de la base"}).
    Cada barra = un GP; su altura = la diferencia entre <b>la mejor vuelta de cada uno</b>
    ${state.h2hSource === "quali" ? "en la clasificación (Q1-Q3)" : "en la carrera"} de ese fin de semana.</div>`));
  if (!d.deltas.length) {
    $view.appendChild(el(`<div class="empty">${d.summary}</div>`));
    return;
  }

  const mas = d.median < 0 ? d.a : d.b;
  const enPista = (d.a.ahead + d.b.ahead) ? (d.a.ahead >= d.b.ahead ? d.a : d.b) : null;

  // test binomial bilateral de la FRECUENCIA: 17-16 en 33 duelos es el
  // reparto más parejo posible (p=1.00) — frecuencia y magnitud son
  // historias distintas y se reportan por separado
  const pBinom = (() => {
    const n = d.deltas.length, k = d.a.wins;
    if (!n) return null;
    const logC = (nn, kk) => {
      let s = 0;
      for (let i = 1; i <= kk; i++) s += Math.log(nn - kk + i) - Math.log(i);
      return s;
    };
    const pk = (kk) => Math.exp(logC(n, kk) + n * Math.log(0.5));
    const pObs = pk(k);
    let p = 0;
    for (let kk = 0; kk <= n; kk++) if (pk(kk) <= pObs + 1e-12) p += pk(kk);
    return Math.min(1, p);
  })();

  // bootstrap pareado de la MEDIANA normalizada (%) con IC 95%
  const pctsValidos = (d.pcts || []).filter((p, i) => !(d.outlier && d.outlier[i]));
  let icMed = null;
  if (pctsValidos.length >= 8) {
    const medArr = (a) => { const s = [...a].sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };
    const difs = [];
    for (let it = 0; it < 5000; it++) {
      const re = pctsValidos.map(() => pctsValidos[Math.floor(Math.random() * pctsValidos.length)]);
      difs.push(medArr(re));
    }
    difs.sort((x, y) => x - y);
    icMed = [difs[Math.floor(0.025 * difs.length)], difs[Math.floor(0.975 * difs.length)]];
  }
  const medPct = d.med_pct != null ? d.med_pct : 0;
  const concluyenteMed = icMed && (icMed[0] > 0 === icMed[1] > 0);
  const nExcl = (d.outlier || []).filter(Boolean).length;

  $view.appendChild(el(`<div class="tiles" style="margin-bottom:18px">
    <div class="card tile" style="--tc:${d.a.color}"><div class="label">Frecuencia · ${d.a.code} vs ${d.b.code}</div>
      <div class="value">${d.a.wins}–${d.b.wins}</div>
      <div class="hint">${pBinom != null ? (pBinom > 0.05 ? `sin diferencia estadística (p=${pBinom.toFixed(2)})` : `diferencia significativa (p=${pBinom.toFixed(3)})`) : ""} · ${d.deltas.length} GPs</div></div>
    <div class="card tile" style="--tc:${mas.color}"><div class="label">Magnitud mediana</div>
      <div class="value">${Math.abs(medPct).toFixed(2)}%</div>
      <div class="hint">a favor de ${mas.code} (${Math.abs(d.median).toFixed(3)}s brutos)${icMed ? ` · IC 95% [${icMed[0].toFixed(2)}, ${icMed[1].toFixed(2)}] → ${concluyenteMed ? "concluyente" : "INCONCLUSA"}` : ""}</div></div>
    ${enPista ? `<div class="card tile" style="--tc:${enPista.color}"><div class="label">Clasificado por delante</div>
      <div class="value">${Math.max(d.a.ahead, d.b.ahead)}–${Math.min(d.a.ahead, d.b.ahead)}</div>
      <div class="hint">${enPista.code} · influido por DNFs, sanciones y maquinaria</div></div>` : ""}
    <div class="card tile"><div class="label">Calidad de la muestra</div>
      <div class="value">${d.deltas.length - nExcl}</div>
      <div class="hint">GPs válidos para agregados · ${nExcl} atípicos excluidos (|Δ|&gt;2.5s)</div></div>
  </div>`));

  const usaPct = (d.pcts || []).length === d.deltas.length;
  const { card, plot } = chartCard({
    title: `${d.a.code} vs ${d.b.code} · Δ ritmo normalizado por GP`,
    sub: `abajo = ${d.a.code} más rápido · eje en % del tiempo de vuelta (0.5s en 60s ≠ 0.5s en 100s) · segundos en el hover`,
    summary: d.summary,
    tips: [
      `<b>¿Barra hacia abajo?</b> → ${d.a.code} hizo mejor vuelta ese GP (abajo = más rápido, como el delta del dashboard).`,
      "El eje va en % del tiempo de vuelta: así los circuitos cortos y largos pesan igual. Los segundos brutos viven en el hover.",
      "<b>¿Barras tenues?</b> → atípicos (|Δ|&gt;2.5s): lluvia, abandono o SC — no entran en los agregados.",
      "Este duelo mezcla piloto, coche, equipo y condiciones: no mide 'solo manos y pies'.",
    ],
  });
  $view.appendChild(card);
  const ejeY = usaPct ? d.pcts : d.deltas;
  Plotly.newPlot(plot, [{
    type: "bar", x: d.gps, y: ejeY,
    marker: { color: ejeY.map((v, i) => {
        const c = v < 0 ? d.a.color : d.b.color;
        return d.outlier && d.outlier[i] ? rgba(c, 0.3) : c;
      }),
      line: { color: "#11141b", width: 2 } },
    customdata: d.deltas,
    hovertemplate: usaPct
      ? "%{x}<br>Δ = %{y:+.3f}% del tiempo de vuelta<br>(%{customdata:+.3f}s brutos)<extra></extra>"
      : "%{x}<br>Δ = %{y:+.3f}s (A − B)<extra></extra>",
  }], baseLayout({
    height: 430, margin: { l: 58, r: 16, t: 16, b: 86 },
    xaxis: { ...baseLayout().xaxis, tickangle: -38, tickfont: { size: 10 } },
    yaxis: { ...baseLayout().yaxis,
             title: { text: usaPct ? "% DEL TIEMPO DE VUELTA (A − B)" : "SEGUNDOS (A − B)", font: { size: 10 } },
             zeroline: true, zerolinecolor: "rgba(255,255,255,.35)", zerolinewidth: 1 },
  }), PLOTLY_CFG);

  // ── DUELO POR SECTORES + PUNTOS POR TEMPORADA ──────────────────────────
  const rowX = el(`<div class="grid cols-2" style="margin-top:20px"></div>`);
  $view.appendChild(rowX);

  if (d.sectores && Object.keys(d.sectores).length) {
    const cSec = chartCard({
      title: "¿Dónde le gana? · duelo por sectores",
      sub: `mediana del mejor sector en carreras comunes · abajo = ${d.a.code} más rápido`,
      tips: [`<b>¿${d.a.code} gana S1 pero pierde S3?</b> → su ventaja vive en esa parte del circuito: frenadas, curvas o tracción según el sector.`,
             "Si uno gana los 3 sectores, la diferencia es global (coche o momento de forma); si se reparten, es estilo de pilotaje."],
    });
    rowX.appendChild(cSec.card);
    const ks = Object.keys(d.sectores);
    Plotly.newPlot(cSec.plot, [{
      type: "bar", x: ks.map((k) => k.toUpperCase()), y: ks.map((k) => d.sectores[k]),
      marker: { color: ks.map((k) => d.sectores[k] < 0 ? d.a.color : d.b.color),
                line: { color: "#11141b", width: 2 } },
      text: ks.map((k) => `${d.sectores[k] < 0 ? d.a.code : d.b.code} +${Math.abs(d.sectores[k]).toFixed(3)}s`),
      textposition: "outside", textfont: { size: 11, color: "#9aa0aa" },
      hovertemplate: "%{x} · Δ %{y:+.3f}s (A − B)<extra></extra>",
    }], baseLayout({
      height: 340, margin: { l: 56, r: 16, t: 24, b: 40 },
      yaxis: { ...baseLayout().yaxis, title: { text: "SEGUNDOS (A − B)", font: { size: 10 } },
               zeroline: true, zerolinecolor: "rgba(255,255,255,.3)" },
    }), PLOTLY_CFG);
  }

  if (d.temporadas && d.temporadas.length) {
    const filas = d.temporadas.map((t) => {
      const ganaA = t.a > t.b;
      return `<tr><td class="num"><b>${t.year}</b></td>
        <td class="num" style="${ganaA ? "font-weight:800" : "color:var(--ink3)"}">${t.a.toFixed(0)}</td>
        <td class="num" style="${!ganaA ? "font-weight:800" : "color:var(--ink3)"}">${t.b.toFixed(0)}</td>
        <td>${drvChip(ganaA ? d.a.code : d.b.code, ganaA ? d.a.color : d.b.color)}</td></tr>`;
    }).join("");
    rowX.appendChild(el(`<div class="card table-wrap">
      <div class="chart-head" style="padding:0 0 8px"><h2>Puntos por temporada</h2>
        <span class="sub">Carrera + Sprint · negrita = quien sumó más ese año</span></div>
      <table><thead><tr><th class="num">Año</th>
        <th class="num">${d.a.code}</th><th class="num">${d.b.code}</th><th>Ganó</th></tr></thead>
      <tbody>${filas}</tbody></table></div>`));
  }
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

  $view.appendChild(heroTitle("Análisis", "telemetría y ritmo de cualquier sesión · vuelta a vuelta"));
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
      `<option value="${e.gp}" ${e.gp === state.telGp ? "selected" : ""}>R${e.round} · ${banderaGP(e.gp)} ${e.gp.replace(" Grand Prix", "")}${e.sessions.some((x) => x.cached) ? " ●" : ""}</option>`).join("");
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

  // cabecera de misión: identidad de la sesión + estado de los datos
  const ronda = (() => {
    try {
      const ev = (state.schedCache[state.telYear].events || []).find((e) => e.gp === state.telGp);
      return ev ? ev.round : null;
    } catch (e) { return null; }
  })();
  zone.appendChild(el(`<div class="mission card">
    <div>
      <div class="kicker">SESSION ANALYSIS${ronda ? ` / R${ronda}` : ""} · ${state.telYear}</div>
      <h3>${banderaGP(state.telGp)} ${state.telGp.replace(" Grand Prix", "")}</h3>
      <div class="meta">${state.telSes} · ${d.drivers.length} coches en análisis · referencia ${d.ref}</div>
    </div>
    <div class="status"><i></i>DATA READY</div>
  </div>`));

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
      title="${a.name} · ${a.team}${a.pos ? ` · P${a.pos}` : ""}"><i></i>${a.pos ? `<span class="ref-tag">P${a.pos}</span> ` : ""}${a.code}${isRef ? ' <span class="ref-tag">REF</span>' : ""}</span>`);
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

  // ── pestañas reales: solo se muestra la activa (adiós al documento infinito)
  const TABS = [["resumen", "RESUMEN"], ["ritmo", "RITMO"], ["estrategia", "ESTRATEGIA"],
                ["telemetria", "TELEMETRÍA"], ["fisica", "FÍSICA"], ["replay", "REPLAY"]];
  if (!TABS.some(([k]) => k === state.anaTab)) state.anaTab = "resumen";
  const bar = el(`<div class="ana-tabs">${TABS.map(([k, t]) =>
    `<button class="ana-tab ${state.anaTab === k ? "active" : ""}" data-tab="${k}">${t}</button>`).join("")}
    <span class="ana-sel" title="Ir a la selección de pilotos">${d.drivers.map((x) =>
      `<span><i style="background:${x.color}"></i>${x.code}${x.code === d.ref ? " <small>REF</small>" : ""}</span>`).join("")}</span></div>`);
  zone.appendChild(bar);
  // clic en los pilotos de la barra → volver arriba a cambiar la selección
  bar.querySelector(".ana-sel").onclick = () => {
    const y = chipsCard.getBoundingClientRect().top + scrollY - (_tbH + 80);
    window.scrollTo({ top: Math.max(0, y), behavior: "smooth" });
  };

  const wraps = {};
  TABS.forEach(([k]) => { wraps[k] = el(`<div></div>`); zone.appendChild(wraps[k]); });
  const SS = { resumen: el(`<div></div>`), ritmo: el(`<div></div>`), estrategia: el(`<div></div>`) };
  const TL = { resumen: el(`<div></div>`), telemetria: el(`<div></div>`),
               fisica: el(`<div></div>`), replay: el(`<div></div>`) };
  wraps.resumen.append(SS.resumen, TL.resumen);
  wraps.ritmo.append(SS.ritmo);
  wraps.estrategia.append(SS.estrategia);
  wraps.telemetria.append(TL.telemetria);
  wraps.fisica.append(TL.fisica);
  wraps.replay.append(TL.replay);

  const activar = (k) => {
    state.anaTab = k;
    bar.querySelectorAll(".ana-tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === k));
    TABS.forEach(([t]) => { wraps[t].style.display = t === k ? "" : "none"; });
    // las gráficas dibujadas mientras su pestaña estaba oculta salen sin ancho: reajustar
    wraps[k].querySelectorAll(".js-plotly-plot").forEach((p) => {
      try { Plotly.Plots.resize(p); } catch (e) { /* aún sin dibujar */ }
    });
  };
  bar.querySelectorAll(".ana-tab").forEach((b) => { b.onclick = () => activar(b.dataset.tab); });

  // dibujar TODO con las zonas visibles (Plotly necesita ancho real)…
  drawSessionStats(SS, ss, state.telSel);
  drawTelCharts(TL.telemetria, d, TL);
  // …y recién entonces encender la pestaña activa
  activar(state.anaTab);
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

function drawTelCharts(zone, d, Z = null) {
  // enrutador de pestañas: sin Z (modo vs-vueltas) todo cae en la misma zona
  const T = Z || { resumen: zone, telemetria: zone, fisica: zone, replay: zone };
  const SYNC = [];   // gráficas vs distancia: zoom y cursor compartidos
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

  // marcadores compartidos por los mapas del circuito: curvas con fondo legible,
  // rombo de meta y flecha de sentido — mismos símbolos en todos los mapas
  const marcadoresMapa = () => {
    const refM = d.drivers[0];
    const anns = (d.corners || []).map((c) => ({
      x: c.x, y: c.y, text: String(c.n), showarrow: false,
      bgcolor: "rgba(3,5,7,.72)", bordercolor: "rgba(255,255,255,.10)",
      borderwidth: 1, borderpad: 2, font: { size: 10.5, color: "#b8c7d5" },
    }));
    let meta = null;
    if (refM && refM.x && refM.x.length > 10) {
      const nM = refM.x.length, iA = Math.floor(nM * 0.03), iB = Math.floor(nM * 0.055);
      anns.push({ x: refM.x[iB], y: refM.y[iB], ax: refM.x[iA], ay: refM.y[iA],
        axref: "x", ayref: "y", text: "", showarrow: true, arrowhead: 2,
        arrowsize: 1.3, arrowwidth: 1.6, arrowcolor: "#e8eaed" });
      meta = { type: "scatter", mode: "markers+text", x: [refM.x[0]], y: [refM.y[0]],
        showlegend: false, hoverinfo: "skip",
        marker: { size: 10, color: "#e8eaed", symbol: "diamond",
                  line: { color: "#11141b", width: 1.5 } },
        text: ["META"], textposition: "top center",
        textfont: { size: 9, color: "#8a919e" } };
    }
    return { anns, meta };
  };

  // interpolación lineal (x ascendente) — para alinear señales entre pilotos
  const interpLin = (xs, ys, x2) => {
    let j = 0;
    return x2.map((v) => {
      while (j < xs.length - 2 && xs[j + 1] < v) j++;
      const t2 = Math.max(0, Math.min(1, (v - xs[j]) / ((xs[j + 1] - xs[j]) || 1)));
      return ys[j] + t2 * (ys[j + 1] - ys[j]);
    });
  };

  T.telemetria.appendChild(el(`<div class="section-title" id="sec-tel">Telemetría de vuelta</div>`));

  // ── circuito: mapa analítico — velocidad / tiempo por metro / dv-ds,
  //    auto-rotado para llenar el lienzo y con los puntos clave marcados
  const refC = d.drivers[0];
  if (refC && refC.x && refC.x.length > 10) {
    const nP = refC.x.length;
    const dTotC = refC.d[refC.d.length - 1];
    // AUTO-ROTACIÓN: prueba 180 ángulos y elige el que maximiza la escala
    const targetW = Math.max(600, (T.resumen.clientWidth || 1400) - 110);
    const targetH = 540;
    let mejorRot = { esc: 0, th: 0 };
    for (let deg = 0; deg < 180; deg += 1) {
      const th = (deg * Math.PI) / 180, c2 = Math.cos(th), s2 = Math.sin(th);
      let mnx = 1e12, mxx = -1e12, mny = 1e12, mxy = -1e12;
      for (let i = 0; i < nP; i += 4) {
        const rx = refC.x[i] * c2 - refC.y[i] * s2;
        const ry = refC.x[i] * s2 + refC.y[i] * c2;
        if (rx < mnx) mnx = rx; if (rx > mxx) mxx = rx;
        if (ry < mny) mny = ry; if (ry > mxy) mxy = ry;
      }
      const esc = Math.min(targetW / (mxx - mnx || 1), targetH / (mxy - mny || 1));
      if (esc > mejorRot.esc) mejorRot = { esc, th };
    }
    const co = Math.cos(mejorRot.th), si = Math.sin(mejorRot.th);
    const RX = refC.x.map((x, i) => x * co - refC.y[i] * si);
    const RY = refC.x.map((x, i) => x * si + refC.y[i] * co);
    const rotP = (x, y) => [x * co - y * si, x * si + y * co];
    const cornersR = (d.corners || []).map((c) => {
      const [x, y] = rotP(c.x, c.y);
      return { ...c, x, y };
    });

    // puntos y métricas clave
    const vmax = Math.max(...refC.speed), vmin = Math.min(...refC.speed);
    const iMax = refC.speed.indexOf(vmax), iMin = refC.speed.indexOf(vmin);
    const curvaEn = (dist) => cornersR.length
      ? cornersR.reduce((a, c) => (Math.abs(c.d - dist) < Math.abs(a.d - dist) ? c : a)) : null;
    const cLenta = curvaEn(refC.d[iMin]);
    // consumo de tiempo por curva: t(d+120) − t(d−120) con el tiempo calibrado
    const tAt = (dist) => {
      let lo = 0, hi = refC.d.length - 1;
      if (dist <= refC.d[0]) return refC.t[0];
      if (dist >= refC.d[hi]) return refC.t[hi];
      while (hi - lo > 1) { const m = (lo + hi) >> 1; (refC.d[m] <= dist ? lo = m : hi = m); }
      const f = (dist - refC.d[lo]) / Math.max(refC.d[hi] - refC.d[lo], 1e-6);
      return refC.t[lo] + f * (refC.t[hi] - refC.t[lo]);
    };
    const consumo = cornersR.map((c) => ({
      n: c.n, x: c.x, y: c.y,
      t: tAt(Math.min(c.d + 120, dTotC)) - tAt(Math.max(c.d - 120, 0)),
    })).sort((a, b) => b.t - a.t);
    const criticas = new Set(consumo.slice(0, 2).map((c) => c.n));
    const sumCir = `Vmax ${Math.round(vmax)} km/h · Vmin ${Math.round(vmin)} km/h` +
      `${cLenta ? ` (T${cLenta.n})` : ""}` +
      (consumo.length >= 2
        ? ` · mayor consumo de tiempo: T${consumo[0].n} (${consumo[0].t.toFixed(1)}s) y T${consumo[1].n} (${consumo[1].t.toFixed(1)}s).`
        : ".");

    const cCir = chartCard({
      title: "Circuito · mapa analítico",
      sub: `vuelta de referencia de ${refC.code} (V${refC.lap_number}) · GPS remuestreado cada 5 m y suavizado · trazado auto-rotado para llenar el lienzo`,
      summary: sumCir,
      legendHtml: `<div class="pills" style="padding:0 18px 10px">
        <button class="pill" data-m="vel">VELOCIDAD</button>
        <button class="pill" data-m="tpm">TIEMPO POR METRO</button>
        <button class="pill" data-m="grad">ACELERACIÓN / FRENADA</button>
        <button class="pill" data-esc="1" style="margin-left:auto">ESCALA FIJA 0-360</button></div>`,
      tips: ["La velocidad NO equivale a tiempo: dt = ds/v. En curva lenta, cada km/h vale mucho más que en recta — por eso existe el modo TIEMPO POR METRO, que enseña dónde se consume la vuelta de verdad.",
             "<b>VELOCIDAD:</b> azul hielo = vuela, rojo = se arrastra. <b>TIEMPO POR METRO:</b> rojo = ahí se gasta la vuelta. <b>ACELERACIÓN/FRENADA:</b> azul = acelera, rojo = frena, gris = estable.",
             "Los rombos marcan Vmax y Vmin; las curvas con borde brillante son las que MÁS TIEMPO consumen (±120 m alrededor).",
             "ESCALA FIJA (0-360) hace comparables los colores entre vueltas y sesiones; la escala auto da más contraste dentro de esta vuelta.",
             "El rombo blanco es la meta y la flecha el sentido de giro."],
    });
    T.resumen.appendChild(cCir.card);
    T.resumen.appendChild(el(`<div style="height:18px"></div>`));

    // gradiente dv/ds (los canales ya vienen suavizados del backend)
    const grad = refC.speed.map((v, i) => {
      const i0 = Math.max(0, i - 1), i1 = Math.min(nP - 1, i + 1);
      return (refC.speed[i1] - refC.speed[i0]) / Math.max(refC.d[i1] - refC.d[i0], 1e-6);
    });
    const gMax = Math.max(...grad.map(Math.abs));
    const msm = refC.speed.map((v) => 3600 / Math.max(v, 30));   // ms por metro

    const iA2 = Math.floor(nP * 0.03), iB2 = Math.floor(nP * 0.055);
    const dibujaCir = () => {
      const modo = state.cirModo || "vel";
      const fija = !!state.cirFija;
      cCir.card.querySelectorAll("[data-m]").forEach((b) =>
        b.classList.toggle("active", b.dataset.m === modo));
      const bEsc = cCir.card.querySelector("[data-esc]");
      bEsc.classList.toggle("active", fija);
      bEsc.style.display = modo === "vel" ? "" : "none";
      const M = {
        vel: { c: refC.speed,
               scale: [[0, "#E0243F"], [0.5, "#FFC400"], [1, "#38bdf8"]],
               min: fija ? 0 : undefined, max: fija ? 360 : undefined,
               titulo: "KM/H", hover: "%{marker.color:.0f} km/h" },
        tpm: { c: msm,
               scale: [[0, "#38bdf8"], [0.5, "#FFC400"], [1, "#E0243F"]],
               min: undefined, max: undefined,
               titulo: "MS / METRO", hover: "%{marker.color:.0f} ms por metro" },
        grad: { c: grad,
                scale: [[0, "#E0243F"], [0.5, "#39424e"], [1, "#38bdf8"]],
                min: -gMax, max: gMax,
                titulo: "ΔKM/H POR M", hover: "%{marker.color:+.1f} km/h por m" },
      }[modo];
      const trazas = [
        { type: "scatter", mode: "lines", x: RX, y: RY, hoverinfo: "skip",
          showlegend: false, line: { color: "rgba(255,255,255,.07)", width: 11 } },
        { type: "scatter", mode: "markers", x: RX, y: RY, showlegend: false,
          marker: { size: 5, color: M.c, colorscale: M.scale,
                    cmin: M.min, cmax: M.max,
                    colorbar: { thickness: 12, outlinewidth: 0, len: 0.8,
                                title: { text: M.titulo, font: { size: 9.5, color: "#8a919e" } },
                                tickfont: { size: 9.5, color: "#8a919e" } } },
          hovertemplate: M.hover + "<extra></extra>" },
        { type: "scatter", mode: "markers+text", showlegend: false, hoverinfo: "skip",
          x: [RX[0]], y: [RY[0]],
          marker: { size: 10, color: "#e8eaed", symbol: "diamond",
                    line: { color: "#11141b", width: 1.5 } },
          text: ["META"], textposition: "top center",
          textfont: { size: 9, color: "#8a919e" } },
        { type: "scatter", mode: "markers+text", showlegend: false, hoverinfo: "skip",
          x: [RX[iMax], RX[iMin]], y: [RY[iMax], RY[iMin]],
          marker: { size: 9, color: ["#38bdf8", "#E0243F"], symbol: "diamond",
                    line: { color: "#0b0d12", width: 1.5 } },
          text: [`VMAX ${Math.round(vmax)}`, `VMIN ${Math.round(vmin)}${cLenta ? " · T" + cLenta.n : ""}`],
          textposition: ["bottom center", "top center"],
          textfont: { size: 9.5, color: ["#7dd3fc", "#ff8181"] } },
      ];
      Plotly.react(cCir.plot, trazas, baseLayout({
        height: 600, margin: { l: 8, r: 8, t: 8, b: 8 },
        xaxis: { visible: false }, yaxis: { visible: false, scaleanchor: "x" },
        annotations: [
          ...cornersR.map((c) => ({
            x: c.x, y: c.y, text: String(c.n), showarrow: false,
            bgcolor: "rgba(3,5,7,.72)",
            bordercolor: criticas.has(c.n) ? "rgba(56,189,248,.8)" : "rgba(255,255,255,.10)",
            borderwidth: 1, borderpad: 2,
            font: { size: criticas.has(c.n) ? 11.5 : 10.5,
                    color: criticas.has(c.n) ? "#cfe9fb" : "#b8c7d5" },
          })),
          { x: RX[iB2], y: RY[iB2], ax: RX[iA2], ay: RY[iA2],
            axref: "x", ayref: "y", text: "", showarrow: true, arrowhead: 2,
            arrowsize: 1.3, arrowwidth: 1.6, arrowcolor: "#e8eaed" },
        ],
      }), PLOTLY_CFG);
    };
    cCir.card.querySelectorAll("[data-m]").forEach((b) => {
      b.onclick = () => { state.cirModo = b.dataset.m; dibujaCir(); };
    });
    cCir.card.querySelector("[data-esc]").onclick = () => {
      state.cirFija = !state.cirFija; dibujaCir();
    };
    dibujaCir();
  }

  if (d.dtw && d.dtw.length) {
    T.telemetria.appendChild(el(`<div class="card" style="margin-bottom:18px">
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

  // fila 1: mapa de dominancia (46%) + G-G cuadrada con métricas (54%)
  const row1 = el(`<div class="grid cols-46-54" style="margin-bottom:18px"></div>`);
  T.fisica.appendChild(row1);

  // ── dominancia: cobertura (tramos) e impacto (ventaja acumulada) por piloto
  const nSegs = (d.segments || []).length;
  const sectorDe = (s) => 1 + (d.cuts || []).filter((c) => c <= (s.d0 + s.d1) / 2).length;
  const domStats = {};
  (d.segments || []).forEach((s) => {
    const e2 = domStats[s.code] = domStats[s.code] || { n: 0, t: 0, color: s.color };
    e2.n += 1; e2.t += s.margin || 0;
  });
  const porSector = {};
  (d.segments || []).forEach((s) => {
    const sec = sectorDe(s);
    porSector[sec] = porSector[sec] || {};
    porSector[sec][s.code] = (porSector[sec][s.code] || 0) + (s.margin || 0);
  });
  const domOrden = Object.entries(domStats).sort((a, b) => b[1].n - a[1].n);
  const masTramos = domOrden[0];
  const masTiempo = [...domOrden].sort((a, b) => b[1].t - a[1].t)[0];
  const ganadorSec = Object.keys(porSector).sort().map((sec) => {
    const g = Object.entries(porSector[sec]).sort((a, b) => b[1] - a[1])[0];
    return `S${sec}: ${g[0]}`;
  }).join(" · ");
  const sumMapa = masTramos
    ? `${masTramos[0]} ganó más tramos (${masTramos[1].n} de ${nSegs})` +
      (masTiempo && masTiempo[0] !== masTramos[0]
        ? `, pero la mayor ventaja acumulada es de ${masTiempo[0]} (${masTiempo[1].t.toFixed(3)}s). `
        : ` y también la mayor ventaja acumulada (${masTramos[1].t.toFixed(3)}s). `) +
      `Dominio por sector — ${ganadorSec}.`
    : (d.summaries.map || "");
  const domBarHtml = nSegs ? `<div class="dom-bar">
    <div class="dom-title">MINI-SECTORES GANADOS · ${nSegs} TRAMOS · barra = cobertura · cifra final = ventaja acumulada</div>
    ${domOrden.map(([code, s2]) => `
      <div class="dom-row"><b style="color:${s2.color}">${code}</b>
        <span class="dom-track"><i style="width:${(s2.n / nSegs * 100).toFixed(0)}%;background:${s2.color}"></i></span>
        <small>${s2.n} · ${(s2.n / nSegs * 100).toFixed(0)}% · ${s2.t.toFixed(3)}s</small></div>`).join("")}
  </div>` : "";

  const cMap = chartCard({
    title: "Mapa de dominancia",
    sub: "cada tramo = el piloto con MENOR TIEMPO en ese mini-sector · grosor = tamaño de la ventaja",
    summary: sumMapa,
    legendHtml: domBarHtml,
    tips: ["<b>¿Un color domina las rectas y otro las curvas?</b> → configuraciones distintas: menos ala vs más carga.",
           "<b>¿Línea gruesa?</b> → ventaja clara en ese tramo; fina = se ganó por milésimas.",
           "Pasa el cursor por un tramo: quién lo ganó, por cuánto y en qué sector.",
           "La barra de abajo separa COBERTURA (tramos ganados) de IMPACTO (segundos sumados): ganar 11 tramos por milésimas puede valer menos que ganar 7 con ventajas grandes."],
  });
  row1.appendChild(cMap.card);
  {
    const maxMargen = Math.max(...(d.segments || []).map((s) => s.margin || 0), 0.001);
    const anchoPor = (m2 = 0) => 5 + 3 * Math.sqrt((m2 || 0) / maxMargen);
    // pista base continua: los colores van montados sobre el asfalto
    const base = (d.segments || []).map((s) => ({
      type: "scatter", mode: "lines", x: s.x, y: s.y, showlegend: false,
      hoverinfo: "skip", line: { color: "rgba(255,255,255,.10)", width: 10 },
    }));
    const segTraces = (d.segments || []).map((s) => ({
      type: "scatter", mode: "lines", x: s.x, y: s.y, showlegend: false,
      line: { color: s.color, width: anchoPor(s.margin) },
      customdata: s.x.map(() => [s.n, s.code,
        s.margin != null ? s.margin.toFixed(3) : "—", sectorDe(s)]),
      hovertemplate: "<b>Mini-sector %{customdata[0]}</b> · S%{customdata[3]}<br>" +
        "Más rápido: %{customdata[1]}<br>Ventaja: %{customdata[2]}s<extra></extra>",
    }));
    const legendTraces = d.drivers.map((x) => ({
      type: "scatter", mode: "lines", x: [null], y: [null], name: x.code,
      line: { color: x.color, width: 5 },
    }));
    const marcasDom = marcadoresMapa();
    Plotly.newPlot(cMap.plot,
      [...base, ...segTraces, ...legendTraces, marcasDom.meta].filter(Boolean),
      baseLayout({
        height: 560, margin: { l: 10, r: 10, t: 10, b: 10 },
        xaxis: { visible: false }, yaxis: { visible: false, scaleanchor: "x" },
        legend: { orientation: "h", y: -0.02, x: 0.5, xanchor: "center" },
        annotations: marcasDom.anns,
      }), PLOTLY_CFG);
  }

  // ── G-G cuadrada: envolvente operativa P95 + panel de máximos
  {
    // máximos por piloto DESDE su envolvente: lateral, frenada, tracción
    const mets = d.drivers.filter((x) => x.env_x && x.env_x.length).map((x) => ({
      code: x.code, color: x.color, drv: x,
      lat: Math.max(...x.env_x.map(Math.abs), 0),
      fren: Math.abs(Math.min(...x.env_y, 0)),
      trac: Math.max(...x.env_y, 0),
    })).sort((a, b) => b.lat - a.lat);
    const lider = (k) => mets.reduce((a, b2) => (b2[k] > a[k] ? b2 : a), mets[0]);
    const lLat = lider("lat"), lFren = lider("fren"), lTrac = lider("trac");
    const sumGG = mets.length
      ? `${lLat.code} alcanzó el mayor apoyo lateral: ${lLat.lat.toFixed(1)}G` +
        (mets[1] ? ` (+${(lLat.lat - mets[1].lat).toFixed(1)}G sobre ${mets[1].code})` : "") +
        `. Mayor frenada: ${lFren.code} (${lFren.fren.toFixed(1)}G) · mayor tracción: ${lTrac.code} (${lTrac.trac.toFixed(1)}G).`
      : (d.summaries.gg || "");

    const cGG = chartCard({
      title: "G-G · aceleración alcanzada",
      sub: "envolvente operativa P95 · más lejos del centro = más aceleración combinada",
      summary: sumGG,
      legendHtml: `<div class="pills gg-modes" style="padding:0 18px 10px">
        <button class="pill" data-m="env">ENVOLVENTES</button>
        <button class="pill" data-m="ref">NUBE REFERENCIA</button>
        <button class="pill" data-m="all">TODAS LAS MUESTRAS</button></div>`,
      tips: ["<b>¿Una envolvente más ancha a los lados?</b> → más agarre lateral aprovechado: carga aerodinámica, goma o confianza.",
             "<b>¿Más profunda abajo?</b> → frena más fuerte y tarde; abajo es FRENADA, arriba TRACCIÓN.",
             "<b>¿'Cuadrada' en las esquinas?</b> → combina frenada y giro a la vez (trail braking): pilotaje al límite.",
             "Esto es lo ALCANZADO por cada dupla piloto-coche en esa vuelta (percentil 95 de sus muestras), no el límite físico absoluto del monoplaza.",
             "La referencia va sólida y con relleno; los rivales, en línea discontinua. Los botones muestran u ocultan las nubes de puntos."],
    });
    cGG.card.classList.add("gg-card");
    row1.appendChild(cGG.card);

    const tabla = el(`<div class="gg-metrics">
      <div class="gg-m-title">MÁXIMOS DE LA VUELTA</div>
      <table><thead><tr><th></th><th class="num">LATERAL</th><th class="num">FRENADA</th><th class="num">TRACCIÓN</th></tr></thead>
      <tbody>${mets.map((m2) => `<tr>
        <td><b style="color:${m2.color}">${m2.code}</b></td>
        <td class="num${m2 === lLat ? " gg-lead" : ""}">${m2.lat.toFixed(1)}G</td>
        <td class="num${m2 === lFren ? " gg-lead" : ""}">${m2.fren.toFixed(1)}G</td>
        <td class="num${m2 === lTrac ? " gg-lead" : ""}">${m2.trac.toFixed(1)}G</td></tr>`).join("")}
      </tbody></table></div>`);
    cGG.card.querySelector(".chart-body").appendChild(tabla);

    const puntoExtremo = (drv, tipo) => {
      const ex = drv.env_x, ey = drv.env_y;
      let idx = 0;
      for (let i2 = 1; i2 < ex.length; i2++) {
        if (tipo === "lat" ? Math.abs(ex[i2]) > Math.abs(ex[idx])
          : tipo === "fren" ? ey[i2] < ey[idx] : ey[i2] > ey[idx]) idx = i2;
      }
      return [ex[idx], ey[idx]];
    };
    const tamGG = () => {
      const disp = cGG.plot.parentElement ? cGG.plot.parentElement.clientWidth : 0;
      if (!disp) return 560;
      return Math.max(360, Math.min(620, disp > 700 ? disp - 300 : disp - 24));
    };

    const dibujaGG = () => {
      const modo = state.ggMode || "env";
      cGG.card.querySelectorAll(".gg-modes .pill").forEach((b) =>
        b.classList.toggle("active", b.dataset.m === modo));
      const maxAbs = Math.max(2.5, ...d.drivers.flatMap((x) =>
        [...(x.env_x || []), ...(x.env_y || [])].map(Math.abs))) * 1.15;
      const circulos = [];
      for (let g = 1; g <= Math.floor(maxAbs); g++)
        circulos.push({ type: "circle", x0: -g, x1: g, y0: -g, y1: g,
          line: { color: "rgba(255,255,255,.09)", width: 1, dash: "dot" } });
      // orientación de fondo casi invisible: arriba tracción, abajo frenada
      const zonas = [
        { type: "rect", x0: -maxAbs, x1: maxAbs, y0: 0, y1: maxAbs, layer: "below",
          fillcolor: "rgba(56,189,248,.025)", line: { width: 0 } },
        { type: "rect", x0: -maxAbs, x1: maxAbs, y0: -maxAbs, y1: 0, layer: "below",
          fillcolor: "rgba(224,36,63,.025)", line: { width: 0 } },
      ];
      const trazas = [];
      const conPuntos = modo === "all" ? d.drivers : modo === "ref" ? d.drivers.slice(0, 1) : [];
      conPuntos.forEach((x) => trazas.push({
        type: "scattergl", mode: "markers", name: x.code, legendgroup: x.code,
        showlegend: false, x: x.glat, y: x.glong,
        marker: { color: rgba(x.color, modo === "all" ? 0.07 : 0.12), size: 2 },
        hoverinfo: "skip" }));
      d.drivers.forEach((x, i2) => {
        if (!x.env_x) return;
        const esRef = i2 === 0;
        trazas.push({ type: "scatter", mode: "lines", name: x.code, legendgroup: x.code,
          x: x.env_x, y: x.env_y,
          line: { color: x.color, width: esRef ? 3.5 : 2.2,
                  dash: esRef ? "solid" : "dash", shape: "linear" },
          fill: esRef ? "toself" : "none",
          fillcolor: esRef ? rgba(x.color, 0.06) : undefined,
          hovertemplate: `<b>${x.code}</b><br>lat %{x:.2f}G · long %{y:.2f}G<extra></extra>` });
      });
      // solo los LÍDERES de cada categoría llevan marcador (no una constelación)
      [[lLat, "lat", "LAT"], [lFren, "fren", "FRENADA"], [lTrac, "trac", "TRACCIÓN"]]
        .forEach(([m2, tipo, tag]) => {
          if (!m2) return;
          const [px, py] = puntoExtremo(m2.drv, tipo);
          trazas.push({ type: "scatter", mode: "markers+text", x: [px], y: [py],
            showlegend: false, hoverinfo: "skip",
            marker: { size: 9, color: m2.color, symbol: "diamond",
                      line: { color: "#0b0d12", width: 1.5 } },
            text: [`${m2.code} ${m2[tipo].toFixed(1)}G ${tag}`],
            textposition: py >= 0 ? "top center" : "bottom center",
            textfont: { size: 9.5, color: m2.color } });
        });
      const lado = tamGG();
      Plotly.react(cGG.plot, trazas, baseLayout({
        width: lado, height: lado,
        margin: { l: 46, r: 12, t: 12, b: 40 },
        shapes: [...zonas, ...circulos],
        annotations: [
          { x: 0, y: maxAbs * 0.95, text: "↑ TRACCIÓN", showarrow: false,
            font: { size: 9.5, color: "#5d7288" } },
          { x: 0, y: -maxAbs * 0.95, text: "↓ FRENADA", showarrow: false,
            font: { size: 9.5, color: "#5d7288" } },
          { x: -maxAbs * 0.93, y: 0, text: "CURVA DER.", textangle: -90, showarrow: false,
            font: { size: 9.5, color: "#5d7288" } },
          { x: maxAbs * 0.93, y: 0, text: "CURVA IZQ.", textangle: 90, showarrow: false,
            font: { size: 9.5, color: "#5d7288" } },
          ...circulos.map((c, i2) => ({ x: 0.1, y: (i2 + 1), text: `${i2 + 1}G`,
            showarrow: false, xanchor: "left",
            font: { size: 8.5, color: "rgba(255,255,255,.28)" } })),
        ],
        xaxis: { ...baseLayout().xaxis, range: [-maxAbs, maxAbs], zeroline: true,
                 zerolinecolor: "rgba(255,255,255,.14)", showgrid: false,
                 title: { text: "G LATERAL", font: { size: 10 } } },
        yaxis: { ...baseLayout().yaxis, range: [-maxAbs, maxAbs], zeroline: true,
                 zerolinecolor: "rgba(255,255,255,.14)", showgrid: false,
                 scaleanchor: "x", scaleratio: 1,
                 title: { text: "G LONG.", font: { size: 10 } } },
        legend: { orientation: "h", y: -0.1, x: 0.5, xanchor: "center" },
      }), PLOTLY_CFG);
    };
    cGG.card.querySelectorAll(".gg-modes .pill").forEach((b) => {
      b.onclick = () => { state.ggMode = b.dataset.m; dibujaGG(); };
    });
    dibujaGG();
    // el cuadrado se recalibra cuando la tarjeta cambia de tamaño (pestañas, resize)
    let ggLock = false;
    new ResizeObserver(() => {
      if (ggLock) return;
      ggLock = true;
      requestAnimationFrame(() => {
        ggLock = false;
        const lado = tamGG();
        if (cGG.plot._fullLayout && Math.abs((cGG.plot.layout.width || 0) - lado) > 10)
          Plotly.relayout(cGG.plot, { width: lado, height: lado });
      });
    }).observe(cGG.card);
  }

    if (d.micro) {
    const m = d.micro;
    const colorDe = (k) => (d.drivers.find((x) => x.code === k) || {}).color || "#ddd";
    if (m.keys.length === 2) {
      // DOS pilotos: una sola franja — color = ganador, intensidad = magnitud,
      // gris = inconcluso (<10 ms). Cobertura e impacto por separado.
      const [ka, kb] = m.keys;
      let total = 0, ganaA = 0, ganaB = 0, inconc = 0, mayor = null;
      const filas = m.sectors.map((sc) => {
        const celdas = sc.cells.map((c, j) => {
          const dj = (c.gaps[ka] || 0) - (c.gaps[kb] || 0);   // >0: gana kb
          total += dj;
          const mag = Math.abs(dj);
          let bg = "rgba(107,114,128,.22)";
          let titulo = `diferencia ${(mag * 1000).toFixed(0)} ms · inconclusa`;
          if (mag >= 0.010) {
            const quien = dj > 0 ? kb : ka;
            bg = rgba(colorDe(quien), mag >= 0.05 ? 0.85 : 0.38);
            titulo = `${quien} gana ${(mag * 1000).toFixed(0)} ms`;
            if (dj > 0) ganaB++; else ganaA++;
            if (!mayor || mag > mayor.mag) mayor = { mag, quien, sector: sc.label, j: j + 1 };
          } else inconc++;
          return `<span class="ms-cell" style="background:${bg}"
            title="${sc.label} · tramo ${j + 1}: ${titulo}"></span>`;
        }).join("");
        return `<div class="ms-sector"><div class="ms-head"><b>${sc.label}</b>
          <span>gana ${sc.winner} +${sc.margin.toFixed(3)}s</span></div>
          <div class="ms-row">${celdas}</div></div>`;
      }).join("");
      const quienTotal = total > 0 ? kb : ka;
      T.telemetria.appendChild(el(`<div class="card chart-card" style="margin-bottom:18px">
        <div class="chart-head"><div class="chart-head-row"><h2>Micro-sectores</h2></div>
          <span class="sub">color = quién ganó el tramo · intensidad = magnitud (tenue 10-50 ms, intensa >50 ms) · gris = inconcluso (&lt;10 ms)</span></div>
        <div style="padding:8px 18px 2px"><div class="ms-wrap">${filas}</div></div>
        <div class="chart-summary">IMPACTO: ${quienTotal} gana ${Math.abs(total).toFixed(3)}s en total.
          COBERTURA: ${ka} ${ganaA} tramos · ${kb} ${ganaB} · ${inconc} inconclusos.${mayor
          ? ` MAYOR GANANCIA: ${mayor.quien} en ${mayor.sector}, tramo ${mayor.j} (${(mayor.mag * 1000).toFixed(0)} ms).` : ""}
          Cobertura e impacto son cosas distintas: se puede ganar más tramos y menos tiempo.</div>
        <details class="chart-guide"><summary>¿Cómo leer esta gráfica?</summary><ul>
          <li><b>¿Celda intensa?</b> → ventaja mayor a 50 ms: ahí vive la diferencia real; búscala en el perfil de velocidad.</li>
          <li><b>¿Celda gris?</b> → menos de 10 ms: dentro del error de la telemetría, no concluyas nada con ella.</li>
          <li>La suma de todos los tramos cierra con la diferencia de vuelta (tiempos calibrados a los oficiales).</li>
          <li>Pasa el cursor por una celda para el detalle exacto.</li>
        </ul></details></div>`));
    } else {
      const lbls = `<div class="ms-col-lbl"><div class="ms-head">&nbsp;</div>${m.keys.map((k) =>
        `<div class="ms-lbl" style="color:${colorDe(k)}">${k}</div>`).join("")}</div>`;
      const secs = m.sectors.map((sc) => {
        const rows = m.keys.map((k) => `<div class="ms-row">${sc.cells.map((c) =>
          `<span class="ms-cell ms-${c.colors[k]}" title="${k}: +${c.gaps[k].toFixed(3)}s vs el mejor del tramo"></span>`).join("")}</div>`).join("");
        return `<div class="ms-sector"><div class="ms-head"><b>${sc.label}</b>
          <span>gana ${sc.winner} +${sc.margin.toFixed(3)}s</span></div>${rows}</div>`;
      }).join("");
      T.telemetria.appendChild(el(`<div class="card chart-card" style="margin-bottom:18px">
        <div class="chart-head"><div class="chart-head-row"><h2>Micro-sectores</h2></div>
          <span class="sub">morado = más rápido · verde = empate (&lt;0.02s) · amarillo = más lento</span></div>
        <div style="padding:8px 18px 2px"><div class="ms-wrap">${lbls}${secs}</div></div>
        ${d.summaries.micro ? `<div class="chart-summary">${d.summaries.micro}</div>` : ""}
        <details class="chart-guide"><summary>¿Cómo leer esta gráfica?</summary><ul>
          <li><b>¿Una fila casi toda morada en un sector?</b> → ahí vive su ventaja; ve a ese tramo en la gráfica de velocidad.</li>
          <li><b>¿Mucho verde?</b> → van empatados; la vuelta se decide en los pocos tramos con color.</li>
          <li>Pasa el cursor sobre una celda para ver el tiempo exacto perdido en ese tramo.</li>
        </ul></details></div>`));
    }
  }

  // ── PERFIL DE VELOCIDAD + franja Δv + VENTAJA ACUMULADA (cierra con oficiales)
  let sumVel = d.summaries.speed || "";
  if (d.drivers.length >= 2 && d.drivers.every((x) => x.lap_time)) {
    const masRapido = d.drivers.reduce((a, b) => (b.lap_time < a.lap_time ? b : a));
    const masVmax = d.drivers.reduce((a, b) => (b.vmax > a.vmax ? b : a));
    const otro = [...d.drivers].filter((x) => x !== masRapido)
      .sort((a, b) => a.lap_time - b.lap_time)[0];
    sumVel = `${masRapido.code} fue ${(otro.lap_time - masRapido.lap_time).toFixed(3)}s más rápido` +
      (masVmax !== masRapido
        ? ` aunque ${masVmax.code} alcanzó ${(masVmax.vmax - masRapido.vmax).toFixed(0)} km/h más de punta: la vuelta se gana donde la velocidad es baja y cada km/h vale más tiempo.`
        : ` y además registró la mayor punta (${masVmax.vmax.toFixed(0)} km/h).`);
  }
  const cVel = chartCard({
    title: "Perfil de velocidad",
    sub: `${lapLabels} · sólida = referencia, discontinua = rivales · sectores estimados por telemetría calibrada`,
    summary: sumVel,
    tips: ["<b>¿Una línea llega más alto en recta?</b> → es el resultado NETO: menos ala, mejor tracción previa, rebufo o modo de motor — crúzala con acelerador y marchas antes de atribuir la causa.",
           "<b>¿Valle más estrecho en una curva?</b> → frena más tarde y suelta antes: ahí gana el tiempo.",
           "5 km/h extra en curva lenta valen MÁS tiempo que 5 km/h en recta: el tiempo por metro va con 1/v² — por eso se puede perder la vuelta ganando la Vmax.",
           "La franja de abajo es la DIFERENCIA de velocidad: hace visible por qué la ventaja acumulada sube o baja."],
  });
  T.telemetria.appendChild(cVel.card);
  Plotly.newPlot(cVel.plot, d.drivers.map((x, i) => ({
    type: "scatter", mode: "lines", name: x.code, x: x.d, y: x.speed,
    line: { color: x.color, width: 1.9, dash: DASHES[i % DASHES.length] },
    hovertemplate: `<b>${x.code}</b> · %{y:.0f} km/h<extra></extra>`,
  })), baseLayout({
    height: 480, hovermode: "x unified", shapes: sectorShapes,
    annotations: [...sectorAnnots, ...winnerAnnots, ...zoneAnnots,
      ...(d.corners || []).map((c) => ({ x: c.d, yref: "paper", y: 1.005,
        text: String(c.n), showarrow: false, font: { size: 8, color: "#5f6b7d" } }))],
    margin: { l: 56, r: 14, t: 42, b: 48 },
    xaxis: { ...baseLayout().xaxis, title: { text: "DISTANCIA DE VUELTA (M) · arriba: curvas", font: { size: 10 } } },
    yaxis: { ...baseLayout().yaxis, title: { text: "KM/H", font: { size: 10 } } },
    legend: { orientation: "h", y: 1.08, x: 1, xanchor: "right" },
  }), PLOTLY_CFG);
  SYNC.push(cVel.plot);

  // franja Δv (rival − referencia), alineada por fracción de vuelta
  const rivalesV = d.drivers.slice(1);
  if (rivalesV.length) {
    const refV = d.drivers[0];
    const dTotR = refV.d[refV.d.length - 1];
    const sRef = refV.d.map((v) => v / dTotR);
    const plotDv = el(`<div></div>`);
    cVel.card.querySelector(".chart-body").appendChild(plotDv);
    const series = rivalesV.map((r) => {
      const dTotB = r.d[r.d.length - 1];
      const vOnRef = interpLin(r.d.map((v) => v / dTotB), r.speed, sRef);
      return { r, dv: vOnRef.map((v, i) => v - refV.speed[i]) };
    });
    const trazasDv = [];
    if (series.length === 1) {
      const { r, dv } = series[0];
      trazasDv.push({ type: "scatter", mode: "lines", x: refV.d,
        y: dv.map((v) => Math.max(v, 0)), fill: "tozeroy",
        fillcolor: rgba(r.color, 0.1), line: { width: 0 },
        hoverinfo: "skip", showlegend: false });
      trazasDv.push({ type: "scatter", mode: "lines", x: refV.d,
        y: dv.map((v) => Math.min(v, 0)), fill: "tozeroy",
        fillcolor: rgba(refV.color, 0.1), line: { width: 0 },
        hoverinfo: "skip", showlegend: false });
    }
    series.forEach(({ r, dv }) => trazasDv.push({
      type: "scatter", mode: "lines", name: `Δv ${r.code}`, x: refV.d, y: dv,
      line: { color: r.color, width: 1.5 },
      hovertemplate: `<b>Δv ${r.code} − ${d.ref}</b> · %{y:+.0f} km/h<extra></extra>` }));
    Plotly.newPlot(plotDv, trazasDv, baseLayout({
      height: 170, hovermode: "x unified", shapes: sectorShapes,
      margin: { l: 56, r: 14, t: 6, b: 30 },
      annotations: [{ xref: "paper", yref: "paper", x: 0.005, y: 0.96, xanchor: "left",
        text: `Δ VELOCIDAD · rival − ${d.ref} · arriba = rival más rápido`,
        showarrow: false, font: { size: 9, color: "#77839a" } }],
      xaxis: { ...baseLayout().xaxis, showticklabels: false },
      yaxis: { ...baseLayout().yaxis, title: { text: "ΔKM/H", font: { size: 9 } },
               zeroline: true, zerolinecolor: "rgba(255,255,255,.3)" },
      showlegend: false,
    }), PLOTLY_CFG);
    SYNC.push(plotDv);
  }
  T.telemetria.appendChild(el(`<div style="height:18px"></div>`));

  // VENTAJA ACUMULADA (delta calibrado: el final ES la diferencia oficial)
  const conDelta = d.drivers.filter((x) => x.delta);
  if (conDelta.length) {
    const cals = d.drivers.filter((x) => x.t_cal_ms != null)
      .map((x) => `${x.code} ${x.t_cal_ms >= 0 ? "+" : ""}${Math.round(x.t_cal_ms)} ms`);
    const peorCal = Math.max(0, ...d.drivers.map((x) => Math.abs(x.t_cal_ms || 0)));
    const calidad = peorCal <= 100 ? "buena" : peorCal <= 300 ? "aceptable" : "baja";

    const rival0 = conDelta[0];
    const finD = rival0.delta[rival0.delta.length - 1];
    const enDist = (dist) => {
      const dd2 = rival0.delta_d;
      let j = 0;
      while (j < dd2.length - 1 && dd2[j + 1] < dist) j++;
      return rival0.delta[j];
    };
    let ganancias = "";
    if ((d.cuts || []).length === 2) {
      const g1 = enDist(d.cuts[0]);
      const g2 = enDist(d.cuts[1]) - enDist(d.cuts[0]);
      const g3 = finD - enDist(d.cuts[1]);
      const gTxt = (v, lbl) => `${lbl}: ${v <= 0 ? rival0.code : d.ref} +${Math.abs(v).toFixed(3)}`;
      ganancias = ` Ganancias por sector — ${gTxt(g1, "S1")} · ${gTxt(g2, "S2")} · ${gTxt(g3, "S3")}.`;
    }
    const sumDelta = `${finD <= 0 ? rival0.code : d.ref} termina delante por ${Math.abs(finD).toFixed(3)}s — el punto final cierra con los tiempos oficiales.` + ganancias;

    const cDelta = chartCard({
      title: `Ventaja acumulada vs ${d.ref}`,
      sub: `arriba = ${d.ref} por delante · abajo = el rival por delante`,
      summary: sumDelta,
      tips: [`<b>¿La línea baja?</b> → el rival le está GANANDO tiempo a ${d.ref}; la INCLINACIÓN es la velocidad a la que lo gana.`,
             "<b>¿Sube de golpe en una curva?</b> → ahí lo pierde: compara esa frenada en el perfil de velocidad y la Δv.",
             "El punto final ES la diferencia real de vuelta: el tiempo integrado de cada piloto se calibra a su tiempo oficial y la corrección aplicada se declara abajo.",
             "Con un solo rival, el sombreado colorea quién va por delante en cada tramo."],
    });
    T.telemetria.appendChild(cDelta.card);
    const trazasDelta = [];
    if (conDelta.length === 1) {
      trazasDelta.push({ type: "scatter", mode: "lines", x: rival0.delta_d,
        y: rival0.delta.map((v) => Math.max(v, 0)), fill: "tozeroy",
        fillcolor: rgba(d.drivers[0].color, 0.08), line: { width: 0 },
        hoverinfo: "skip", showlegend: false });
      trazasDelta.push({ type: "scatter", mode: "lines", x: rival0.delta_d,
        y: rival0.delta.map((v) => Math.min(v, 0)), fill: "tozeroy",
        fillcolor: rgba(rival0.color, 0.08), line: { width: 0 },
        hoverinfo: "skip", showlegend: false });
    }
    conDelta.forEach((x) => trazasDelta.push({
      type: "scatter", mode: "lines", name: `Δ ${x.code}`, x: x.delta_d, y: x.delta,
      line: { color: x.color, width: 2 },
      hovertemplate: `<b>${x.code}</b> · Δ %{y:+.3f}s<extra></extra>`,
    }));
    const anotsD = conDelta.map((r) => ({
      x: r.delta_d[r.delta_d.length - 1], y: r.delta[r.delta.length - 1],
      text: `${r.code} ${r.delta[r.delta.length - 1] >= 0 ? "+" : ""}${r.delta[r.delta.length - 1].toFixed(3)}s`,
      showarrow: false, xanchor: "left", xshift: 6,
      font: { size: 10, color: r.color } }));
    if (conDelta.length === 1) {
      const iMax = rival0.delta.indexOf(Math.max(...rival0.delta));
      const iMin = rival0.delta.indexOf(Math.min(...rival0.delta));
      if (rival0.delta[iMax] > 0.05)
        anotsD.push({ x: rival0.delta_d[iMax], y: rival0.delta[iMax], ay: -16, ax: 0,
          text: `máx ${d.ref} +${rival0.delta[iMax].toFixed(2)}`, showarrow: true,
          arrowcolor: "rgba(255,255,255,.3)", font: { size: 9, color: "#8a919e" } });
      if (rival0.delta[iMin] < -0.05)
        anotsD.push({ x: rival0.delta_d[iMin], y: rival0.delta[iMin], ay: 16, ax: 0,
          text: `máx ${rival0.code} ${rival0.delta[iMin].toFixed(2)}`, showarrow: true,
          arrowcolor: "rgba(255,255,255,.3)", font: { size: 9, color: "#8a919e" } });
    }
    Plotly.newPlot(cDelta.plot, trazasDelta, baseLayout({
      height: 340, hovermode: "x unified", shapes: sectorShapes,
      annotations: [...sectorAnnots, ...anotsD],
      margin: { l: 56, r: 64, t: 30, b: 48 },
      xaxis: { ...baseLayout().xaxis, title: { text: "DISTANCIA DE VUELTA (M)", font: { size: 10 } } },
      yaxis: { ...baseLayout().yaxis, title: { text: `SEGUNDOS VS ${d.ref}`, font: { size: 10 } },
               zeroline: true, zerolinecolor: accLine(0.5), zerolinewidth: 1.5 },
      legend: { orientation: "h", y: 1.1, x: 1, xanchor: "right" },
    }), PLOTLY_CFG);
    const badgeD = el(`<div class="chart-summary${calidad === "baja" ? " warn" : ""}">DELTA CALIBRADO A TIEMPOS OFICIALES · corrección de integración aplicada: ${cals.join(" · ") || "n/d"} · calidad ${calidad}</div>`);
    cDelta.card.insertBefore(badgeD, cDelta.card.querySelector(".chart-guide"));
    SYNC.push(cDelta.plot);
    T.telemetria.appendChild(el(`<div style="height:18px"></div>`));
  }

  // ── ENTRADAS DEL PILOTO: acelerador + estado de freno + marcha, UN panel
  {
    // métricas por DISTANCIA (la malla es uniforme de ~5 m y se declara)
    const met = d.drivers.map((x) => {
      const n = x.throttle.length;
      let fondo = 0, lift = 0, frenando = 0, cambios = 0;
      for (let i = 0; i < n; i++) {
        const bOn = typeof x.brake[i] === "boolean" ? x.brake[i] : x.brake[i] >= 5;
        if (x.throttle[i] >= 99) fondo++;
        if (x.throttle[i] < 95 && !bOn) lift++;
        if (bOn) frenando++;
        if (i && x.gear[i] !== x.gear[i - 1]) cambios++;
      }
      const paso = x.d[x.d.length - 1] / n;
      return { code: x.code, fondoPct: (fondo / n) * 100, frenPct: (frenando / n) * 100,
               liftM: lift * paso, cambios };
    });
    const sumIn = met.map((m2) =>
      `${m2.code}: ${m2.fondoPct.toFixed(1)}% a fondo · frena en ${m2.frenPct.toFixed(1)}% · levanta sin frenar ${m2.liftM.toFixed(0)} m · ${m2.cambios} cambios`)
      .join("  —  ") + " (todo por distancia).";
    const cIn = chartCard({
      title: "Entradas del piloto",
      sub: "acelerador · estado de frenado · marcha — mismo eje de distancia, cursor y zoom compartidos",
      summary: sumIn,
      tips: ["El acelerador es la ORDEN del piloto, no el rendimiento: un promedio menor puede ser una vuelta mejor. Compáralo con velocidad y ventaja acumulada.",
             "<b>El freno de esta fuente es BINARIO</b> (activo/inactivo): dice CUÁNDO frena, no cuánta presión aplica. La intensidad vive en la gráfica de aceleración longitudinal (FÍSICA).",
             "<b>¿Dos activaciones de freno seguidas?</b> → chicane, liberación intermedia o corrección: confirma con velocidad y G longitudinal antes de concluir.",
             "Una marcha distinta en la misma curva no implica más velocidad por sí sola: pueden variar relaciones de caja, régimen o gestión.",
             "Los porcentajes se miden POR DISTANCIA (malla uniforme de ~5 m), no por tiempo."],
    });
    T.telemetria.appendChild(cIn.card);
    T.telemetria.appendChild(el(`<div style="height:18px"></div>`));
    const cuerpoIn = cIn.card.querySelector(".chart-body");
    const pThr = cIn.plot;
    const pBrk = el(`<div></div>`); cuerpoIn.appendChild(pBrk);
    const pGear = el(`<div></div>`); cuerpoIn.appendChild(pGear);

    // 1) acelerador
    Plotly.newPlot(pThr, d.drivers.map((x, i) => ({
      type: "scatter", mode: "lines", name: x.code, x: x.d, y: x.throttle,
      line: { color: x.color, width: 1.6, dash: DASHES[i % DASHES.length] },
      hovertemplate: `<b>${x.code}</b> · gas %{y:.0f}%<extra></extra>`,
    })), baseLayout({
      height: 210, hovermode: "x unified", shapes: sectorShapes,
      margin: { l: 52, r: 12, t: 22, b: 6 },
      annotations: [...sectorAnnots],
      xaxis: { ...baseLayout().xaxis, showticklabels: false },
      yaxis: { ...baseLayout().yaxis, title: { text: "% PEDAL", font: { size: 9.5 } } },
      legend: { orientation: "h", y: 1.24, x: 1, xanchor: "right", font: { size: 10 } },
    }), PLOTLY_CFG);
    SYNC.push(pThr);

    // 2) freno como CARRILES on/off: dos estados no necesitan 100 unidades de eje
    const codesIn = d.drivers.map((x) => x.code);
    Plotly.newPlot(pBrk, d.drivers.map((x) => {
      const ys = [];
      for (let i = 0; i < x.d.length; i++) {
        const on = typeof x.brake[i] === "boolean" ? x.brake[i] : x.brake[i] >= 5;
        ys.push(on ? x.code : null);
      }
      return { type: "scatter", mode: "lines", name: x.code, x: x.d, y: ys,
        connectgaps: false, showlegend: false,
        line: { color: x.color, width: 12 },
        hovertemplate: `<b>${x.code}</b> · frenando<extra></extra>` };
    }), baseLayout({
      height: 56 + d.drivers.length * 30, hovermode: "closest", shapes: sectorShapes,
      margin: { l: 52, r: 12, t: 8, b: 6 },
      xaxis: { ...baseLayout().xaxis, showticklabels: false },
      yaxis: { ...baseLayout().yaxis, type: "category",
               categoryorder: "array", categoryarray: [...codesIn].reverse(),
               gridcolor: "rgba(0,0,0,0)", tickfont: { size: 10 } },
      showlegend: false,
    }), PLOTLY_CFG);
    SYNC.push(pBrk);

    // 3) marchas + diferencias SOSTENIDAS anotadas (≥20 m, solo con 2 pilotos)
    const anotG = [];
    if (d.drivers.length === 2) {
      const [a, b] = d.drivers;
      const gB = interpLin(b.d.map((v) => v / b.d[b.d.length - 1]), b.gear,
                           a.d.map((v) => v / a.d[a.d.length - 1]));
      let iniG = null;
      const zonasDif = [];
      for (let i = 0; i < a.d.length; i++) {
        const dif = Math.round(gB[i]) !== a.gear[i];
        if (dif && iniG == null) iniG = i;
        else if (!dif && iniG != null) {
          if (a.d[i - 1] - a.d[iniG] >= 20) zonasDif.push([iniG, i - 1]);
          iniG = null;
        }
      }
      zonasDif.sort((z1, z2) => (a.d[z2[1]] - a.d[z2[0]]) - (a.d[z1[1]] - a.d[z1[0]]));
      zonasDif.slice(0, 4).forEach(([i0, i1]) => {
        const mid = (a.d[i0] + a.d[i1]) / 2;
        const c2 = (d.corners || []).length
          ? d.corners.reduce((p, q) => (Math.abs(q.d - mid) < Math.abs(p.d - mid) ? q : p)) : null;
        anotG.push({ x: mid, yref: "paper", y: 1.07, showarrow: false,
          text: `${c2 ? "T" + c2.n + ": " : ""}${a.code} ${a.gear[i0]}ª · ${b.code} ${Math.round(gB[i0])}ª`,
          font: { size: 8.5, color: "#8a919e" } });
      });
    }
    Plotly.newPlot(pGear, d.drivers.map((x) => ({
      type: "scatter", mode: "lines", name: x.code, x: x.d, y: x.gear,
      line: { color: x.color, width: 1.6, shape: "hv" },
      hovertemplate: `<b>${x.code}</b> · %{y}ª<extra></extra>`,
    })), baseLayout({
      height: 190, hovermode: "x unified", shapes: sectorShapes,
      margin: { l: 52, r: 12, t: 20, b: 40 },
      annotations: anotG,
      xaxis: { ...baseLayout().xaxis, title: { text: "DISTANCIA DE VUELTA (M)", font: { size: 10 } } },
      yaxis: { ...baseLayout().yaxis, title: { text: "MARCHA", font: { size: 9.5 } }, dtick: 1 },
      showlegend: false,
    }), PLOTLY_CFG);
    SYNC.push(pGear);
  }
  T.fisica.appendChild(el(`<div class="section-title" id="sec-fis">Física del coche</div>`));

  // ── ACELERACIÓN LONGITUDINAL: zonas de frenada + panel de diferencia
  const cGl = chartCard({
    title: "Aceleración longitudinal",
    sub: "estimada desde la velocidad · −G = desaceleración · +G = aceleración",
    tips: ["<b>Pico negativo</b> → la desaceleración máxima de esa zona; el valor robusto (percentil 5) está en la tabla.",
           "<b>Inicio del descenso</b> → dónde empieza a frenar: comparar inicios dice quién frena MÁS TARDE.",
           "<b>Regreso a cero</b> → suelta el freno; si sube a positivo, ya está traccionando a la salida.",
           "El panel de abajo es la DIFERENCIA (rival − referencia) alineada por distancia: debajo de cero el rival desacelera más; cerca de cero van iguales.",
           "Diferencias menores a 0.05 G se consideran similares: esta señal es una derivada estimada, no un acelerómetro."],
  });
  T.fisica.appendChild(cGl.card);
  T.fisica.appendChild(el(`<div style="height:18px"></div>`));
  {
    const refG = d.drivers[0];
    const curvaDe = (dm) => {
      if (!(d.corners || []).length) return "—";
      const c = d.corners.reduce((a, c2) => (Math.abs(c2.d - dm) < Math.abs(a.d - dm) ? c2 : a));
      return "T" + c.n;
    };
    // detección de zonas de frenada: sostenida (<-0.25G), fin al volver a -0.15G
    const zonasDe = (drv, dMin = -Infinity, dMax = Infinity) => {
      const zs = [];
      let a = null;
      for (let i = 0; i < drv.d.length; i++) {
        const dentro = drv.d[i] >= dMin && drv.d[i] <= dMax;
        const g = dentro ? drv.glong[i] : 1;
        if (a == null && g < -0.25) a = i;
        else if (a != null && g > -0.15) {
          if (drv.d[i - 1] - drv.d[a] >= 25) zs.push([a, i - 1]);
          a = null;
        }
      }
      if (a != null && drv.d[drv.d.length - 1] - drv.d[a] >= 25) zs.push([a, drv.d.length - 1]);
      return zs.map(([i0, i1]) => {
        const seg = drv.glong.slice(i0, i1 + 1);
        const ordn = [...seg].sort((x, y) => x - y);
        const pico = ordn[Math.max(0, Math.floor(0.05 * (ordn.length - 1)))];
        let dur = 0;
        for (let i = i0 + 1; i <= i1; i++) {
          const vm = Math.max(5, (drv.speed[i] + drv.speed[i - 1]) / 2) / 3.6;
          dur += (drv.d[i] - drv.d[i - 1]) / vm;
        }
        const vIni = drv.speed[i0];
        const vMin = Math.min(...drv.speed.slice(i0, i1 + 1));
        return { d0: drv.d[i0], d1: drv.d[i1], dPico: drv.d[i0 + seg.indexOf(Math.min(...seg))],
                 pico, dur, vPerdida: vIni - vMin };
      });
    };
    const zonasRef = zonasDe(refG);

    // por cada zona de la referencia, la frenada de cada piloto en esa ventana
    const filasZona = [];
    zonasRef.forEach((z) => {
      const etiqueta = curvaDe(z.dPico);
      d.drivers.forEach((drv) => {
        const zz = drv === refG ? z
          : (zonasDe(drv, z.d0 - 60, z.d1 + 60)[0] || null);
        filasZona.push({ zona: etiqueta, code: drv.code, color: drv.color, z: zz });
      });
    });

    // diferencia rival − referencia sobre la MISMA cuadrícula de distancia
    const interpola = (xs, ys, x2) => {
      let j = 0;
      return x2.map((v) => {
        while (j < xs.length - 2 && xs[j + 1] < v) j++;
        const t2 = Math.max(0, Math.min(1, (v - xs[j]) / ((xs[j + 1] - xs[j]) || 1)));
        return ys[j] + t2 * (ys[j + 1] - ys[j]);
      });
    };
    const rivales = d.drivers.slice(1).map((drv) => ({
      code: drv.code, color: drv.color,
      delta: interpola(drv.d, drv.glong, refG.d).map((g, i) => g - refG.glong[i]),
    }));

    // resumen calculado con las zonas, no con los píxeles
    const picos = filasZona.filter((f) => f.z);
    const mayor = picos.length ? picos.reduce((a, b) => (b.z.pico < a.z.pico ? b : a)) : null;
    let masTardeTxt = "";
    if (rivales.length && zonasRef.length) {
      const rival = d.drivers[1];
      let tarde = 0, comparadas = 0;
      zonasRef.forEach((z) => {
        const zr = zonasDe(rival, z.d0 - 60, z.d1 + 60)[0];
        if (zr) { comparadas += 1; if (zr.d0 > z.d0 + 3) tarde += 1; }
      });
      masTardeTxt = comparadas
        ? ` ${rival.code} frena más tarde que ${refG.code} en ${tarde} de ${comparadas} zonas.` : "";
    }
    let difTxt = "";
    if (rivales.length) {
      const difMedia = rivales[0].delta.reduce((a, v) => a + Math.abs(v), 0) / rivales[0].delta.length;
      difTxt = ` Diferencia media |ΔG|: ${difMedia.toFixed(2)} G → perfiles ${difMedia < 0.05 ? "muy similares" : "con diferencias reales"}.`;
    }
    const sumGl = mayor
      ? `Mayor pico de frenada: ${mayor.code} (${mayor.z.pico.toFixed(1)} G en ${mayor.zona}).` + masTardeTxt + difTxt
      : "";
    const resumenGl = el(`<div class="chart-summary" style="display:${sumGl ? "" : "none"}">${sumGl}</div>`);
    const warnGl = el(`<div class="chart-summary warn">DATO INFERIDO · derivada de la velocidad sobre malla uniforme de distancia, no acelerómetro del coche.</div>`);
    const tablaGl = el(`<div class="table-wrap">${filasZona.length ? `
      <div class="gg-m-title" style="margin:10px 18px 6px">ZONAS DE FRENADA · INICIO = QUIÉN FRENA MÁS TARDE · PICO = P5 ROBUSTO</div>
      <table style="width:calc(100% - 36px);margin:0 18px 8px"><thead><tr>
        <th>ZONA</th><th>PILOTO</th><th class="num">INICIO (M)</th><th class="num">PICO (G)</th>
        <th class="num">DURACIÓN (S)</th><th class="num">VEL. PERDIDA</th></tr></thead>
      <tbody>${filasZona.map((f) => `<tr>
        <td>${f.zona}</td><td><b style="color:${f.color}">${f.code}</b></td>
        <td class="num">${f.z ? f.z.d0.toFixed(0) : "—"}</td>
        <td class="num">${f.z ? f.z.pico.toFixed(2) : "—"}</td>
        <td class="num">${f.z ? f.z.dur.toFixed(2) : "—"}</td>
        <td class="num">${f.z ? "−" + f.z.vPerdida.toFixed(0) + " km/h" : "—"}</td></tr>`).join("")}
      </tbody></table>` : ""}</div>`);
    const guiaGl = cGl.card.querySelector(".chart-guide");
    cGl.card.insertBefore(resumenGl, guiaGl);
    cGl.card.insertBefore(warnGl, guiaGl);
    cGl.card.insertBefore(tablaGl, guiaGl);

    // gráfica principal: referencia sólida, rivales discontinuos, hover completo
    const trazasGl = d.drivers.map((x, i) => ({
      type: "scatter", mode: "lines", name: x.code, x: x.d, y: x.glong,
      line: { color: x.color, width: i === 0 ? 2.2 : 1.7, dash: i === 0 ? "solid" : "dash" },
      customdata: x.d.map((dm, k) => [dm, x.speed[k],
        (typeof x.brake[k] === "boolean" ? x.brake[k] : x.brake[k] >= 5) ? "sí" : "no",
        x.throttle[k], x.gear[k]]),
      hovertemplate: `<b>${x.code}</b> · %{customdata[0]:.0f} m<br>` +
        "%{y:+.2f} G · %{customdata[1]:.0f} km/h<br>" +
        "freno %{customdata[2]} · gas %{customdata[3]:.0f}% · %{customdata[4]}ª<extra></extra>",
    }));
    const finales = d.drivers.map((x) => ({
      x: x.d[x.d.length - 1], y: x.glong[x.glong.length - 1], text: x.code,
      showarrow: false, xanchor: "left", xshift: 5,
      font: { size: 10, color: x.color } }));
    Plotly.newPlot(cGl.plot, trazasGl, baseLayout({
      height: 340, hovermode: "x unified", shapes: [
        ...sectorShapes,
        { type: "rect", xref: "paper", x0: 0, x1: 1, y0: 0, y1: 8, layer: "below",
          fillcolor: "rgba(56,189,248,.025)", line: { width: 0 } },
        { type: "rect", xref: "paper", x0: 0, x1: 1, y0: -8, y1: 0, layer: "below",
          fillcolor: "rgba(224,36,63,.03)", line: { width: 0 } },
      ],
      margin: { l: 50, r: 46, t: 30, b: 44 },
      annotations: [...sectorAnnots, ...finales,
        ...(d.corners || []).map((c) => ({ x: c.d, yref: "paper", y: 1.01,
          text: String(c.n), showarrow: false,
          font: { size: 8, color: "#5f6b7d" } }))],
      xaxis: { ...baseLayout().xaxis, title: { text: "DISTANCIA DE VUELTA (M) · arriba: curvas", font: { size: 10 } } },
      yaxis: { ...baseLayout().yaxis, title: { text: "ACELERACIÓN LONGITUDINAL (G)", font: { size: 10 } },
               zeroline: true, zerolinecolor: "rgba(255,255,255,.25)" },
      legend: { orientation: "h", y: 1.12, x: 1, xanchor: "right" },
    }), PLOTLY_CFG);

    // panel de diferencia ΔG (rival − referencia), misma cuadrícula y zoom
    if (rivales.length) {
      const plotDif = el(`<div></div>`);
      cGl.card.querySelector(".chart-body").appendChild(plotDif);
      Plotly.newPlot(plotDif, rivales.map((r) => ({
        type: "scatter", mode: "lines", name: `Δ ${r.code}`,
        x: refG.d, y: r.delta,
        line: { color: r.color, width: 1.6 },
        hovertemplate: `<b>Δ ${r.code} − ${refG.code}</b> · %{y:+.2f} G<extra></extra>`,
      })), baseLayout({
        height: 180, hovermode: "x unified", shapes: sectorShapes,
        margin: { l: 50, r: 46, t: 6, b: 34 },
        annotations: [{ xref: "paper", yref: "paper", x: 0.005, y: 0.95, xanchor: "left",
          text: `DIFERENCIA vs ${refG.code} · abajo = desacelera más que la referencia`,
          showarrow: false, font: { size: 9, color: "#77839a" } }],
        xaxis: { ...baseLayout().xaxis, showticklabels: false },
        yaxis: { ...baseLayout().yaxis, title: { text: "ΔG", font: { size: 9 } },
                 zeroline: true, zerolinecolor: "rgba(255,255,255,.3)" },
        showlegend: false,
      }), PLOTLY_CFG);
      SYNC.push(plotDif);
    }
  }

  // ── ENTREGA LONGITUDINAL EN RECTA: proxy honesto (ex-"ERS")
  //    mediana por bloques de 5 km/h + banda Q25-Q75, rango comparable,
  //    selector por recta (zonas de alta velocidad) y muestras opcionales
  {
    const cErs = chartCard({
      title: "Entrega longitudinal en recta",
      sub: "aceleración neta a fondo vs velocidad · proxy de motor térmico, MGU-K y drag · mediana por bloques de 5 km/h",
      legendHtml: `<div class="pills ers-ctl" style="padding:0 18px 10px"></div>`,
      tips: ["La línea es la MEDIANA por bloque de 5 km/h; la banda, el 50% central de las muestras. <b>¿Bandas traslapadas?</b> → la diferencia NO es concluyente.",
             "La aceleración cae con la velocidad porque el drag crece con v²: <b>una caída suave es NORMAL</b>, no es clipping. Sospecha solo de caídas abruptas y persistentes en la misma recta.",
             "Se excluyen frenadas, curvas, cambios de marcha (con sus muestras vecinas) y derivadas fuera de patrón (&lt; −2 m/s²).",
             "2026: ya NO existe el DRS. La aerodinámica activa (modo recta/curva) y el Overtake Mode cambian esta curva y NO vienen en la fuente de datos — por eso es un proxy inferido.",
             "Solo se compara el RANGO DE VELOCIDAD cubierto por todos los pilotos; fuera de él no se declara ganador."],
    });
    SYNC.push(cGl.plot);
    T.fisica.appendChild(cErs.card);
    T.fisica.appendChild(el(`<div style="height:18px"></div>`));

    const resumenErs = el(`<div class="chart-summary"></div>`);
    const warnErs = el(`<div class="chart-summary warn">PROXY INFERIDO · no mide directamente la energía del ERS ni confirma el Overtake Mode.</div>`);
    const tablaErs = el(`<div class="table-wrap"></div>`);
    const guiaErs = cErs.card.querySelector(".chart-guide");
    cErs.card.insertBefore(resumenErs, guiaErs);
    cErs.card.insertBefore(warnErs, guiaErs);
    cErs.card.insertBefore(tablaErs, guiaErs);

    // muestras limpias: a fondo, sin freno, poca carga lateral, sin cambio de
    // marcha adyacente; derivadas fuera de patrón (< -2 m/s²) no puntúan
    const muestrasDe = (x, zona) => {
      const xs = [], ys = [];
      for (let i = 1; i < x.d.length - 1; i++) {
        const frenando = typeof x.brake[i] === "boolean" ? x.brake[i] : x.brake[i] >= 5;
        if (x.throttle[i] < 95 || frenando || Math.abs(x.glat[i]) >= 0.5) continue;
        if (x.gear && (x.gear[i] !== x.gear[i - 1] || x.gear[i + 1] !== x.gear[i])) continue;
        if (zona && !(x.d[i] >= zona.d0 && x.d[i] <= zona.d1)) continue;
        const a = x.glong[i] * 9.81;
        if (a < -2) continue;
        xs.push(x.speed[i]); ys.push(a);
      }
      return { xs, ys };
    };
    const BIN = 5;
    const binea = (xs, ys) => {
      const mapa2 = new Map();
      xs.forEach((v, i) => {
        const b = Math.floor(v / BIN) * BIN;
        if (!mapa2.has(b)) mapa2.set(b, []);
        mapa2.get(b).push(ys[i]);
      });
      return [...mapa2.entries()].map(([v, arr]) => {
        const s = [...arr].sort((a, b) => a - b);
        const q = (p) => s[Math.round(p * (s.length - 1))];
        return { v: v + BIN / 2, med: q(0.5), q25: q(0.25), q75: q(0.75), n: s.length };
      }).filter((r) => r.n >= 5).sort((a, b) => a.v - b.v);
    };

    const zonasErs = d.zones || [];
    const ctlErs = cErs.card.querySelector(".ers-ctl");
    ctlErs.innerHTML = [
      `<button class="pill" data-z="-1">TODAS LAS RECTAS</button>`,
      ...zonasErs.map((z, i) =>
        `<button class="pill" data-z="${i}">RECTA ${i + 1} · ${z.d0}-${z.d1}m</button>`),
      `<button class="pill" data-pts="1" style="margin-left:auto">MOSTRAR MUESTRAS</button>`,
    ].join("");

    const renderErs = () => {
      const iZona = state.ersZona != null ? state.ersZona : -1;
      const zona = iZona >= 0 ? zonasErs[iZona] : null;
      ctlErs.querySelectorAll("[data-z]").forEach((b) =>
        b.classList.toggle("active", +b.dataset.z === iZona));
      ctlErs.querySelector("[data-pts]").classList.toggle("active", !!state.ersPts);

      const pilotos = d.drivers
        .map((x) => { const m3 = muestrasDe(x, zona); return { x, ...m3, bins: binea(m3.xs, m3.ys) }; })
        .filter((p) => p.bins.length >= 3);
      let v0 = null, v1 = null;
      if (pilotos.length) {
        v0 = Math.max(...pilotos.map((p) => p.bins[0].v));
        v1 = Math.min(...pilotos.map((p) => p.bins[p.bins.length - 1].v));
      }
      const enRango = (p) => p.bins.filter((r) => r.v >= v0 && r.v <= v1);

      const trazas = [];
      if (state.ersPts) pilotos.forEach((p) => trazas.push({
        type: "scattergl", mode: "markers", name: p.x.code, showlegend: false,
        legendgroup: p.x.code, x: p.xs, y: p.ys,
        marker: { color: rgba(p.x.color, 0.1), size: 2 }, hoverinfo: "skip" }));
      pilotos.forEach((p) => {
        const B = enRango(p);
        if (B.length < 2) return;
        trazas.push({ type: "scatter", mode: "lines", showlegend: false, legendgroup: p.x.code,
          x: [...B.map((r) => r.v), ...[...B].reverse().map((r) => r.v)],
          y: [...B.map((r) => r.q75), ...[...B].reverse().map((r) => r.q25)],
          fill: "toself", fillcolor: rgba(p.x.color, 0.08),
          line: { width: 0 }, hoverinfo: "skip" });
        trazas.push({ type: "scatter", mode: "lines", name: p.x.code, legendgroup: p.x.code,
          x: B.map((r) => r.v), y: B.map((r) => r.med),
          line: { color: p.x.color, width: 2.2 },
          customdata: B.map((r) => [r.n, r.q25.toFixed(1), r.q75.toFixed(1)]),
          hovertemplate: `<b>${p.x.code}</b> · %{x:.0f} km/h<br>mediana %{y:.1f} m/s² · 50% central %{customdata[1]} a %{customdata[2]}<br>%{customdata[0]} muestras<extra></extra>` });
      });
      const anots = pilotos.map((p) => {
        const B = enRango(p);
        if (!B.length) return null;
        const u = B[B.length - 1];
        return { x: u.v, y: u.med, text: p.x.code, showarrow: false, xanchor: "left",
                 xshift: 6, font: { size: 10.5, color: p.x.color } };
      }).filter(Boolean);
      if (v0 != null && v1 > v0)
        anots.push({ xref: "paper", yref: "paper", x: 0.99, y: 0.98, xanchor: "right",
          text: `RANGO COMPARABLE · ${Math.round(v0)}-${Math.round(v1)} KM/H`,
          showarrow: false, font: { size: 9.5, color: "#77839a" } });

      Plotly.react(cErs.plot, trazas, baseLayout({
        height: 460, margin: { l: 56, r: 64, t: 16, b: 46 },
        annotations: anots,
        xaxis: { ...baseLayout().xaxis, title: { text: "VELOCIDAD (KM/H)", font: { size: 10 } },
                 showgrid: true, gridcolor: "rgba(255,255,255,.05)", griddash: "dot" },
        yaxis: { ...baseLayout().yaxis, title: { text: "ACELERACIÓN (M/S²)", font: { size: 10 } },
                 zeroline: true, zerolinecolor: "rgba(255,255,255,.25)" },
        legend: { orientation: "h", y: 1.08, x: 1, xanchor: "right" },
      }), PLOTLY_CFG);

      // tabla 200/250/300 + caída + tiempo estimado 200→300 (solo rango común)
      const cerca = (p, v) => p.bins.find((r) => Math.abs(r.v - v) <= BIN / 2 + 0.01);
      const t2030 = (p) => {
        if (v0 == null || v0 > 200 || v1 < 300) return null;
        let t = 0;
        for (let v = 200; v < 300; v += BIN) {
          const r = p.bins.find((r2) => r2.v === v + BIN / 2);
          if (!r || r.med < 0.3) return null;
          t += (BIN / 3.6) / r.med;
        }
        return t;
      };
      tablaErs.innerHTML = pilotos.length ? `
        <div class="gg-m-title" style="margin:10px 18px 6px">ENTREGA POR VELOCIDAD · ACELERACIÓN MEDIANA (M/S²)</div>
        <table style="width:calc(100% - 36px);margin:0 18px 8px"><thead><tr>
          <th></th><th class="num">200 KM/H</th><th class="num">250 KM/H</th>
          <th class="num">300 KM/H</th><th class="num">CAÍDA 250→300</th>
          <th class="num">200→300 ESTIMADO</th></tr></thead>
        <tbody>${pilotos.map((p) => {
          const a200 = cerca(p, 200), a250 = cerca(p, 250), a300 = cerca(p, 300);
          const caida = (a250 && a300) ? a300.med - a250.med : null;
          const t = t2030(p);
          return `<tr><td><b style="color:${p.x.color}">${p.x.code}</b></td>
            <td class="num">${a200 ? a200.med.toFixed(1) : "—"}</td>
            <td class="num">${a250 ? a250.med.toFixed(1) : "—"}</td>
            <td class="num">${a300 ? a300.med.toFixed(1) : "—"}</td>
            <td class="num">${caida != null ? caida.toFixed(1) : "—"}</td>
            <td class="num">${t != null ? t.toFixed(2) + " s" : "—"}</td></tr>`;
        }).join("")}</tbody></table>` : "";

      // conclusión calculada, con la prudencia como norma
      let conc = "";
      if (pilotos.length >= 2 && v0 != null && v1 > v0) {
        const finales = pilotos
          .map((p) => { const B = enRango(p); return { code: p.x.code, r: B[B.length - 1] }; })
          .filter((f) => f.r);
        const ord3 = [...finales].sort((a, b) => b.r.med - a.r.med);
        const separadas = ord3.length >= 2 && ord3[0].r.q25 > ord3[1].r.q75;
        conc = `En el rango comparable (${Math.round(v0)}-${Math.round(v1)} km/h), ` +
          (separadas
            ? `${ord3[0].code} entrega más aceleración a alta velocidad que ${ord3[1].code} y sus bandas NO se traslapan: diferencia real.`
            : `las bandas de ${ord3[0].code} y ${ord3[1].code} se traslapan a alta velocidad: diferencia no concluyente.`) +
          ` Ningún recorte de potencia puede confirmarse con una sola vuelta.`;
      } else if (!pilotos.length) {
        conc = "Sin muestras suficientes con este filtro (prueba otra recta o TODAS).";
      }
      resumenErs.textContent = conc;
      resumenErs.style.display = conc ? "" : "none";
    };
    ctlErs.querySelectorAll("[data-z]").forEach((b) => {
      b.onclick = () => { state.ersZona = +b.dataset.z; renderErs(); };
    });
    ctlErs.querySelector("[data-pts]").onclick = () => {
      state.ersPts = !state.ersPts; renderErs();
    };
    renderErs();
  }

  // ── acciones del piloto: estados EXCLUYENTES ponderados por tiempo real
  //    ('en curva' era geometría disfrazada de acción: vive en el mapa)
  {
    const accionesDe = (x) => {
      let wF = 0, wP = 0, wC = 0, wB = 0, wT = 0;
      for (let i = 0; i < x.throttle.length; i++) {
        const w = 1 / Math.max(x.speed[i], 5);   // dt ∝ Δd/v en malla uniforme
        const brk = typeof x.brake[i] === "boolean" ? x.brake[i] : x.brake[i] >= 5;
        wT += w;
        if (brk) wB += w;
        else if (x.throttle[i] >= 95) wF += w;
        else if (x.throttle[i] <= 5) wC += w;
        else wP += w;
      }
      return { fondo: (wF / wT) * 100, parcial: (wP / wT) * 100,
               coast: (wC / wT) * 100, freno: (wB / wT) * 100 };
    };
    const acc = d.drivers.map((x) => ({ x, a: accionesDe(x) }));
    let sumPh = "";
    if (acc.length >= 2) {
      const difs = ["fondo", "parcial", "coast", "freno"].map((k) => ({
        k, d: acc[1].a[k] - acc[0].a[k] }));
      const mayor = difs.reduce((a, b) => (Math.abs(b.d) > Math.abs(a.d) ? b : a));
      const NOM = { fondo: "a fondo", parcial: "gas parcial", coast: "coast", freno: "frenada" };
      sumPh = Math.abs(mayor.d) < 2
        ? "Los porcentajes globales son prácticamente iguales; las diferencias importantes hay que buscarlas POR CURVA (mapa de dominancia y entradas del piloto)."
        : `Mayor diferencia global: ${NOM[mayor.k]} (${acc[1].x.code} ${mayor.d >= 0 ? "+" : ""}${mayor.d.toFixed(1)} pp vs ${acc[0].x.code}). Confírmala por curva antes de concluir estilo.`;
    }
    const cPh = chartCard({
      title: "Acciones del piloto · % del tiempo",
      sub: "estados excluyentes: frenada / a fondo / gas parcial / coast · ponderado por tiempo · la geometría (curva o recta) vive en el mapa del circuito",
      summary: sumPh,
      tips: ["Los cuatro estados SÍ suman 100% porque son excluyentes por definición (freno manda; luego el umbral de gas).",
             "Diferencias menores a ~2 pp no dan para conclusiones: dependen de umbrales, muestreo y suavizado.",
             "% DEL TIEMPO ≠ % de la distancia: un piloto más lento pasa más tiempo en las mismas curvas.",
             "'En curva' no está aquí a propósito: es una condición geométrica, no una acción — se puede ir a fondo EN una curva."],
    });
    T.fisica.appendChild(cPh.card);
    const phSeries = [
      { key: "fondo", name: "A fondo", color: "#2dd4bf" },
      { key: "parcial", name: "Gas parcial", color: "#3F7BF0" },
      { key: "coast", name: "Coast", color: "#6b7280" },
      { key: "freno", name: "Frenada", color: "#ff6b6b" },
    ];
    Plotly.newPlot(cPh.plot, phSeries.map((s) => ({
      type: "bar", orientation: "h", name: s.name,
      y: acc.map(({ x }) => x.code).reverse(),
      x: acc.map(({ a }) => a[s.key]).reverse(),
      marker: { color: s.color, line: { color: "#11141b", width: 2 } },
      text: acc.map(({ a }) => a[s.key] >= 6 ? `${a[s.key].toFixed(0)}%` : "").reverse(),
      textposition: "inside", textfont: { size: 10.5, color: "#0b0d12" },
      hovertemplate: `%{y} · ${s.name}: %{x:.1f}% del tiempo<extra></extra>`,
    })), baseLayout({
      height: chartHeight({ items: acc.length, min: 200, max: 300, per: 34 }),
      barmode: "stack",
      margin: { l: 46, r: 12, t: 12, b: 36 },
      xaxis: { ...baseLayout().xaxis, ticksuffix: "%" },
      yaxis: { ...baseLayout().yaxis, gridcolor: "rgba(0,0,0,0)" },
      legend: { orientation: "h", y: 1.16, x: 0.5, xanchor: "center" },
    }), PLOTLY_CFG);
  }

  T.fisica.appendChild(el(`<div style="height:18px"></div>`));
  sincronizaX(SYNC);
  drawReplay(T.replay, d);
}


/* ───────────────────────────── REPLAY fantasma (Canvas 2D + rAF, 60 fps) */

function drawReplay(zone, d) {
  const cars = d.drivers.filter((x) => x.x && x.x.length && x.lap_time);
  if (cars.length < 1) return;

  const ref = cars[0];
  const refD = ref.d[ref.d.length - 1];
  // los tiempos vienen CALIBRADOS al oficial desde el backend: t[fin] = LapTime
  const Tmax = Math.max(...cars.map((c) => c.t[c.t.length - 1]));
  const prog = (car, dist) => dist / car.d[car.d.length - 1];

  // resumen deportivo calculado (no ficha técnica) + calidad de sincronización
  const curvaCerca = (dist) => {
    if (!(d.corners || []).length) return "";
    const c2 = d.corners.reduce((p, q) => (Math.abs(q.d - dist) < Math.abs(p.d - dist) ? q : p));
    return `T${c2.n}`;
  };
  let resumenRep = `El gap de cada tarjeta es tiempo real contra ${d.ref} al MISMO progreso de vuelta.`;
  const r1 = cars[1];
  if (r1 && r1.delta && r1.lap_time && ref.lap_time) {
    const df = r1.lap_time - ref.lap_time;
    const quien = df <= 0 ? r1.code : ref.code;
    const iMx = r1.delta.indexOf(Math.max(...r1.delta));
    const iMn = r1.delta.indexOf(Math.min(...r1.delta));
    resumenRep = `${quien} termina ${Math.abs(df * 1000).toFixed(0)} ms por delante. ` +
      `Máxima ventaja de ${ref.code}: ${Math.max(0, r1.delta[iMx]).toFixed(2)}s cerca de ${curvaCerca(r1.delta_d[iMx])}; ` +
      `máxima de ${r1.code}: ${Math.abs(Math.min(0, r1.delta[iMn])).toFixed(2)}s cerca de ${curvaCerca(r1.delta_d[iMn])}.`;
  }
  const cals = cars.filter((c) => c.t_cal_ms != null)
    .map((c) => `${c.code} ${c.t_cal_ms >= 0 ? "+" : ""}${Math.round(c.t_cal_ms)} ms`);

  zone.appendChild(el(`<div class="section-title" id="sec-replay">Replay de vuelta
    <small> · fantasmas sincronizados a los tiempos oficiales</small></div>`));
  const card = el(`<div class="card chart-card">
    <div class="chart-head"><div class="chart-head-row"><h2>Replay fantasma</h2></div>
      <span class="sub">todos arrancan a la vez; delante = mayor PROGRESO de vuelta (referencia común) · espacio = play · flechas = ±0.5s (shift ±5s)</span></div>
    <div style="padding:10px 18px 6px">
      <div class="replay-controls">
        <button class="btn-red" id="rpPlay">▶ PLAY</button>
        <select id="rpSpeed" style="padding:8px 34px 8px 12px">
          <option value="0.25">0.25×</option><option value="0.5">0.5×</option>
          <option value="1" selected>1×</option>
          <option value="2">2×</option><option value="4">4×</option></select>
        <input type="range" id="rpScrub" min="0" max="1000" value="0" style="flex:1">
        <b id="rpTime" style="font-variant-numeric:tabular-nums;min-width:104px;text-align:right">0.0 / ${Tmax.toFixed(1)}s</b>
      </div>
      <canvas id="rpCanvas" style="width:100%;display:block;border-radius:10px"></canvas>
      <div id="rpHud" class="replay-hud"></div>
      <canvas id="rpTele" style="width:100%;display:block;border-radius:10px;margin-top:10px"></canvas>
    </div>
    <div class="chart-summary" style="margin-top:8px">${resumenRep}</div>
    ${cals.length ? `<div class="chart-summary warn">REPLAY SINCRONIZADO A TIEMPOS OFICIALES · corrección de integración aplicada: ${cals.join(" · ")}.</div>` : ""}
    <details class="chart-guide"><summary>¿Cómo leer esta gráfica?</summary><ul>
      <li><b>¿Un fantasma se acerca en las curvas y se aleja en las rectas?</b> → coche con más carga aerodinámica: gana en curva, paga en recta.</li>
      <li>El gap (segundos) es la métrica principal; los metros son su explicación espacial sobre la línea de la referencia.</li>
      <li><b>¿El gap crece de golpe en una zona?</b> → búscala en la ventaja acumulada y los micro-sectores.</li>
      <li>Usa 0.25× para estudiar una frenada; la estela siempre representa los últimos 1.2 s de vuelta, a cualquier velocidad.</li>
    </ul></details></div>`);
  zone.appendChild(card);

  const canvas = card.querySelector("#rpCanvas");
  const hud = card.querySelector("#rpHud");
  const btn = card.querySelector("#rpPlay");
  const selV = card.querySelector("#rpSpeed");
  const scrub = card.querySelector("#rpScrub");
  const lblT = card.querySelector("#rpTime");

  // línea de tiempo con cortes de sector (fracciones del tiempo de la ref)
  if ((d.cuts || []).length === 2) {
    const fDe = (dist) => {
      let lo = 0, hi = ref.d.length - 1;
      while (hi - lo > 1) { const m = (lo + hi) >> 1; (ref.d[m] <= dist ? lo = m : hi = m); }
      return (ref.t[lo] / Tmax) * 100;
    };
    const [f1, f2] = d.cuts.map(fDe);
    scrub.style.background = `linear-gradient(90deg,
      rgba(255,255,255,.08) 0%, rgba(255,255,255,.08) ${f1 - 0.3}%,
      rgba(255,255,255,.55) ${f1 - 0.3}%, rgba(255,255,255,.55) ${f1 + 0.3}%,
      rgba(255,255,255,.08) ${f1 + 0.3}%, rgba(255,255,255,.08) ${f2 - 0.3}%,
      rgba(255,255,255,.55) ${f2 - 0.3}%, rgba(255,255,255,.55) ${f2 + 0.3}%,
      rgba(255,255,255,.08) ${f2 + 0.3}%, rgba(255,255,255,.08) 100%)`;
  }

  // mundo → pantalla (DPR limitado a 2: retina x3 triplicaba la memoria)
  const xs = ref.x, ys = ref.y;
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  let W = 800, H = 560, k = 1, ox = 0, oy = 0;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
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
  const at = (car, tau2) => {
    const t = car.t;
    if (tau2 >= t[t.length - 1]) {
      const i = t.length - 1;
      return { x: car.x[i], y: car.y[i], v: car.speed[i], dist: car.d[i], fin: true };
    }
    let lo = 0, hi = t.length - 1;
    while (hi - lo > 1) { const m = (lo + hi) >> 1; (t[m] <= tau2 ? lo = m : hi = m); }
    const f = (tau2 - t[lo]) / Math.max(t[hi] - t[lo], 1e-6);
    const L = (a) => a[lo] + (a[hi] - a[lo]) * f;
    return { x: L(car.x), y: L(car.y), v: L(car.speed), dist: L(car.d), fin: false };
  };
  // gap vs referencia por PROGRESO COMÚN: cada trayectoria mide distinto,
  // así que se compara a igual fracción de vuelta (cierra con los oficiales)
  const gapVsRef = (car, tau2, dist) => {
    if (car === ref) return 0;
    const dEq = prog(car, dist) * refD;
    let lo = 0, hi = ref.d.length - 1;
    if (dEq >= ref.d[hi]) return tau2 - ref.t[hi];
    while (hi - lo > 1) { const m = (lo + hi) >> 1; (ref.d[m] <= dEq ? lo = m : hi = m); }
    const f = (dEq - ref.d[lo]) / Math.max(ref.d[hi] - ref.d[lo], 1e-6);
    return tau2 - (ref.t[lo] + (ref.t[hi] - ref.t[lo]) * f);
  };

  const ctx = canvas.getContext("2d");
  const trails = new Map(cars.map((c) => [c.code, []]));
  let tau = 0, playing = false, last = null, raf = null, arrastrando = false;
  let dtF = 0.016;
  const cam = { cx: null, cy: null, k: null };

  // HUD: se construye UNA vez; después solo cambia el texto (~12 Hz)
  hud.innerHTML = "";
  const hudN = new Map();
  cars.forEach((c) => {
    const nodo = el(`<span class="chip" style="--cc:${c.color}"><i></i><b>${c.code}</b>&nbsp;<span class="rh-v"></span>&nbsp;<span class="rh-g"></span>&nbsp;<span class="rh-m" style="color:var(--ink3);font-size:11px"></span></span>`);
    hud.appendChild(nodo);
    hudN.set(c.code, { v: nodo.querySelector(".rh-v"), g: nodo.querySelector(".rh-g"),
                       m: nodo.querySelector(".rh-m") });
  });
  let hudLast = 0;
  const updateHud = (estados, force) => {
    const now = performance.now();
    if (!force && now - hudLast < 80) return;
    hudLast = now;
    const pRef = prog(ref, estados[0].p.dist);
    estados.forEach(({ c, p }) => {
      const n = hudN.get(c.code);
      n.v.textContent = p.fin ? c.lap_label : `${p.v.toFixed(0)} km/h`;
      if (c === ref) { n.g.textContent = "REF"; n.g.style.color = "var(--ink3)"; n.m.textContent = ""; return; }
      const g = p.fin ? (c.lap_time - ref.lap_time) : gapVsRef(c, tau, p.dist);
      n.g.textContent = `${g >= 0 ? "+" : ""}${g.toFixed(p.fin ? 3 : 2)}s`;
      n.g.style.color = g > 0 ? "#ff8181" : "#7dffb0";
      const dm = (prog(c, p.dist) - pRef) * refD;
      n.m.textContent = p.fin ? "" : `${dm >= 0 ? "+" : ""}${dm.toFixed(0)} m`;
    });
    lblT.textContent = `${tau.toFixed(1)} / ${Tmax.toFixed(1)}s`;
    if (!arrastrando) scrub.value = Math.round((tau / Tmax) * 1000);
  };

  // ── tira de telemetría sincronizada (velocidad / gas / freno / marcha) ──
  const tele = card.querySelector("#rpTele");
  const tctx = tele.getContext("2d");
  const Dmax = Math.max(...cars.map((c) => c.d[c.d.length - 1]));
  const vMax = Math.max(...cars.map((c) => Math.max(...c.speed))) * 1.05;
  const BANDS = [
    { key: "speed", lbl: "VEL",   min: 0,  max: vMax, frac: 0.42 },
    { key: "throttle", lbl: "GAS", min: 0, max: 105,  frac: 0.20 },
    { key: "brake", lbl: "FRENO", min: 0,  max: 105,  frac: 0.14 },
    { key: "gear", lbl: "MARCHA", min: 0.5, max: 8.5, frac: 0.24 },
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
      if (g.key === "brake") {
        // el freno es BINARIO: bloques on/off por carril, no una línea de 0-100
        const laneH = (g.y1 - g.y0) / cars.length;
        cars.forEach((car, j) => {
          c.fillStyle = car.color; c.globalAlpha = 0.55;
          let d0 = null;
          for (let i = 0; i <= car.d.length; i++) {
            const on = i < car.d.length &&
              (typeof car.brake[i] === "boolean" ? car.brake[i] : car.brake[i] >= 5);
            if (on && d0 == null) d0 = car.d[i];
            else if (!on && d0 != null) {
              c.fillRect(px(d0), g.y0 + j * laneH + 1, Math.max(1.5, px(car.d[i - 1]) - px(d0)), laneH - 2);
              d0 = null;
            }
          }
          c.globalAlpha = 1;
        });
        return;
      }
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
    estados.forEach(({ c, p }, j) => {
      const i = idxAt(c, p.dist), X = px(p.dist);
      bandGeo.forEach((g) => {
        // marcha y freno son discretos: se usa la muestra vigente, sin interpolar
        const Y = g.key === "brake"
          ? g.y0 + (j + 0.5) * ((g.y1 - g.y0) / cars.length)
          : py(g, c[g.key][i]);
        tctx.fillStyle = c.color;
        tctx.beginPath();
        tctx.arc(X, Y, 3.6, 0, 7);
        tctx.fill();
        tctx.strokeStyle = "#0b0d12"; tctx.lineWidth = 1.4; tctx.stroke();
      });
    });
  };

  const frame = (force) => {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    ctx.drawImage(staticLayer, 0, 0, W, H);
    const estados = cars.map((c) => ({ c, p: at(c, tau) }));
    // estelas por TIEMPO DE SIMULACIÓN: siempre los últimos 1.2 s de vuelta,
    // sin importar FPS ni la velocidad de reproducción
    estados.forEach(({ c, p }) => {
      const tr = trails.get(c.code);
      if (!tr.length || tr[tr.length - 1].tau !== tau) tr.push({ tau, x: p.x, y: p.y });
      while (tr.length && tau - tr[0].tau > 1.2) tr.shift();
      for (let i = 0; i < tr.length; i++) {
        ctx.globalAlpha = (1 - (tau - tr[i].tau) / 1.2) * 0.35;
        ctx.fillStyle = c.color;
        ctx.beginPath();
        ctx.arc(sx(tr[i].x), sy(tr[i].y), 2.4, 0, 7);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    });
    estados.forEach(({ c, p }) => {
      const X = sx(p.x), Y = sy(p.y);
      ctx.shadowColor = c.color; ctx.shadowBlur = 12;
      ctx.fillStyle = c.color;
      ctx.beginPath(); ctx.arc(X, Y, 6, 0, 7); ctx.fill();
      ctx.shadowBlur = 0;
      if (c === ref) { ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.5; ctx.stroke(); }
      ctx.font = "800 10px Inter, sans-serif"; ctx.textAlign = "center";
      const wTxt = ctx.measureText(c.code).width;
      ctx.fillStyle = "rgba(3,5,7,.75)";
      ctx.fillRect(X - wTxt / 2 - 4, Y - 24, wTxt + 8, 13);
      ctx.fillStyle = c.color;
      ctx.fillText(c.code, X, Y - 14);
    });
    // CLOSE-UP: cámara SUAVIZADA sobre los dos primeros fantasmas
    if (cars.length >= 2) {
      const pw = Math.min(360, W * 0.32), ph = Math.round(pw * 0.62);
      const px0 = W - pw - 14, py0 = 14;
      const a = estados[0].p, b = estados[1].p;
      const cxT = (a.x + b.x) / 2, cyT = (a.y + b.y) / 2;
      const sep = Math.hypot(a.x - b.x, a.y - b.y);
      const kT = Math.min(4 * k, (pw * 0.6) / Math.max(sep, 30));
      const al = 1 - Math.exp(-dtF / 0.28);
      cam.cx = cam.cx == null ? cxT : cam.cx + al * (cxT - cam.cx);
      cam.cy = cam.cy == null ? cyT : cam.cy + al * (cyT - cam.cy);
      cam.k = cam.k == null ? kT : cam.k + al * (kT - cam.k);
      const k2 = cam.k;
      const S = (x, y) => [px0 + pw / 2 + (x - cam.cx) * k2, py0 + ph / 2 - (y - cam.cy) * k2];
      ctx.save();
      ctx.beginPath(); ctx.roundRect(px0, py0, pw, ph, 10); ctx.clip();
      ctx.fillStyle = "rgba(10,12,17,.96)"; ctx.fillRect(px0, py0, pw, ph);
      // solo el tramo LOCAL del circuito (no todo Silverstone por cuadro)
      const iA = idxAt(ref, a.dist);
      const iB = idxAt(ref, prog(estados[1].c, b.dist) * refD);
      const lo2 = Math.max(0, Math.min(iA, iB) - 70);
      const hi2 = Math.min(xs.length - 1, Math.max(iA, iB) + 70);
      ctx.strokeStyle = "rgba(255,255,255,.1)";
      ctx.lineWidth = Math.max(10, (k2 / k) * 5);
      ctx.lineJoin = ctx.lineCap = "round";
      ctx.beginPath();
      for (let i = lo2; i <= hi2; i++) {
        const [X2, Y2] = S(xs[i], ys[i]);
        (i > lo2 ? ctx.lineTo(X2, Y2) : ctx.moveTo(X2, Y2));
      }
      ctx.stroke();
      estados.slice(0, 2).forEach(({ c, p }) => {
        const [X2, Y2] = S(p.x, p.y);
        ctx.shadowColor = c.color; ctx.shadowBlur = 12;
        ctx.fillStyle = c.color;
        ctx.beginPath(); ctx.arc(X2, Y2, 8, 0, 7); ctx.fill();
        ctx.shadowBlur = 0;
        ctx.font = "800 10px Inter, sans-serif"; ctx.textAlign = "center";
        ctx.fillStyle = "#0b0d12"; ctx.fillText(c.code[0], X2, Y2 + 3.5);
      });
      ctx.restore();
      ctx.strokeStyle = "rgba(255,255,255,.18)"; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.roundRect(px0, py0, pw, ph, 10); ctx.stroke();
      ctx.font = "700 9px Inter, sans-serif"; ctx.fillStyle = "#8a919e";
      ctx.textAlign = "left";
      const dm2 = (prog(estados[1].c, b.dist) - prog(ref, a.dist)) * refD;
      ctx.fillText(`CLOSE-UP · ${curvaCerca(a.dist)} · Δ ${dm2 >= 0 ? "+" : ""}${dm2.toFixed(0)} m`, px0 + 10, py0 + 16);
      // escala: sin ella el zoom variable engaña al ojo
      const esc = 20 * k2;
      ctx.strokeStyle = "rgba(255,255,255,.5)"; ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(px0 + 10, py0 + ph - 10); ctx.lineTo(px0 + 10 + esc, py0 + ph - 10);
      ctx.stroke();
      ctx.fillText("20 m", px0 + 12 + esc, py0 + ph - 7);
    }
    updateHud(estados, force);
    drawTele(estados);
  };

  // ── ciclo de vida: limpiar rAF, observador y teclas al salir del replay ──
  let ro = null;
  const onVis = () => { last = null; };
  const onKey = (e) => {
    if (!canvas.isConnected) { destruye(); return; }
    if (!canvas.offsetParent) return;              // pestaña REPLAY no visible
    if (/INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
    if (e.code === "Space") { e.preventDefault(); btn.click(); }
    else if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      e.preventDefault();
      const paso = (e.shiftKey ? 5 : 0.5) * (e.key === "ArrowLeft" ? -1 : 1);
      tau = Math.max(0, Math.min(Tmax, tau + paso));
      trails.forEach((t) => { t.length = 0; });
      frame(true);
    }
  };
  const destruye = () => {
    playing = false;
    if (raf != null) cancelAnimationFrame(raf);
    if (ro) ro.disconnect();
    document.removeEventListener("keydown", onKey);
    document.removeEventListener("visibilitychange", onVis);
  };

  const loop = (ts) => {
    if (!canvas.isConnected) { destruye(); return; }
    if (!playing) return;
    if (last != null) {
      dtF = Math.min((ts - last) / 1000, 0.05);   // pestaña oculta: sin saltos
      tau = Math.min(Tmax, tau + dtF * (+selV.value));
    }
    last = ts;
    frame(false);
    if (tau >= Tmax) { playing = false; btn.textContent = "↻ REPETIR"; frame(true); return; }
    raf = requestAnimationFrame(loop);
  };
  btn.onclick = () => {
    if (playing) { playing = false; btn.textContent = "▶ PLAY"; cancelAnimationFrame(raf); return; }
    if (tau >= Tmax) { tau = 0; trails.forEach((t) => { t.length = 0; }); }
    playing = true; last = null; btn.textContent = "❚❚ PAUSA";
    raf = requestAnimationFrame(loop);
  };
  scrub.oninput = (e) => {
    arrastrando = true;
    tau = (+e.target.value / 1000) * Tmax;
    trails.forEach((t) => { t.length = 0; });
    cam.cx = cam.cy = cam.k = null;
    frame(true);
    arrastrando = false;
  };
  document.addEventListener("keydown", onKey);
  document.addEventListener("visibilitychange", onVis);
  ro = new ResizeObserver(() => {
    if (!canvas.isConnected) { destruye(); return; }
    fit(); buildStatic(); fitTele(); frame(true);
  });
  ro.observe(canvas);
  fit(); buildStatic(); fitTele(); frame(true);
}

/* ───────────────────────────── RITMO DE SESIÓN (estadística de toda la sesión) */


const COMP_COLORS = { SOFT: "#E0243F", MEDIUM: "#FFC400", HARD: "#E8EAED",
                      INTERMEDIATE: "#2ECC71", WET: "#3F7BF0" };

function timeTicks(vals) {
  const mn = Math.min(...vals), mx = Math.max(...vals);
  const paso = Math.max(0.5, Math.round((mx - mn) / 6 * 2) / 2);
  const ticks = [];
  for (let t = Math.ceil(mn * 2) / 2; t <= mx; t += paso) ticks.push(Math.round(t * 2) / 2);
  return { tickvals: ticks, ticktext: ticks.map(fmtLap) };
}

function drawSessionStats(Zss, ss, sel) {
  const render = () => {
    Object.values(Zss).forEach((z) => { z.innerHTML = ""; });
    const usarSel = !state.ritmoAll && sel && sel.length;
    const f = (arr) => (usarSel ? (arr || []).filter((x) => sel.includes(x.code)) : (arr || []));
    const ss2 = { ...ss, box: f(ss.box), cv: f(ss.cv), evo: f(ss.evo),
                  deg: f(ss.deg), grid: f(ss.grid), stints: f(ss.stints),
                  positions: f(ss.positions), gaps: f(ss.gaps), pits: f(ss.pits) };
    if (ss.trap && usarSel) {
      const idx = ss.trap.drivers.map((c, i) => [c, i]).filter(([c]) => sel.includes(c));
      ss2.trap = idx.length >= 1
        ? { drivers: idx.map(([c]) => c), laps: ss.trap.laps, z: idx.map(([, i]) => ss.trap.z[i]) }
        : null;
    }
    drawSessionStatsInner(Zss, ss2, render);
  };
  render();
}

function drawSessionStatsInner(Z, ss, rerender) {
  Z.ritmo.appendChild(el(`<div class="section-title" id="sec-ritmo">Ritmo de sesión
    <small> · ${ss.session} · toda la sesión, no solo la vuelta rápida</small></div>`));
  const tg = el(`<div class="pills" style="margin-bottom:14px">
    <button class="pill ${!state.ritmoAll ? "active" : ""}">PILOTOS SELECCIONADOS</button>
    <button class="pill ${state.ritmoAll ? "active" : ""}">TODO EL CAMPO</button></div>`);
  const [tgA, tgB] = tg.querySelectorAll("button");
  tgA.onclick = () => { state.ritmoAll = false; rerender(); };
  tgB.onclick = () => { state.ritmoAll = true; rerender(); };
  Z.ritmo.appendChild(tg);

  let sumRitmo = "";
  if (ss.cv.length) {
    const rap = [...ss.cv].sort((a, b) => a.median - b.median)[0];
    const con = ss.cv[0];
    const alcance = state.ritmoAll ? "de todo el campo" : "entre tus seleccionados";
    sumRitmo = `Mejor ritmo mediano ${alcance}: ${rap.code} (${rap.median_label}). Más consistente: ` +
               `${con.code} (CV ${con.cv.toFixed(2)}%). El más rápido no siempre es el más regular.`;
  }

  // tiles: veredicto
  if (ss.cv.length) {
    const rapido = [...ss.cv].sort((a, b) => a.median - b.median)[0];
    const consistente = ss.cv[0];
    Z.resumen.appendChild(el(`<div class="tiles" style="margin-bottom:18px">
      <div class="card tile" style="--tc:${rapido.color}"><div class="label">Mejor ritmo (mediana)</div>
        <div class="value">${rapido.code}</div><div class="hint">${rapido.median_label} · ${rapido.laps} vueltas limpias</div></div>
      <div class="card tile" style="--tc:${consistente.color}"><div class="label">Más consistente</div>
        <div class="value">${consistente.code}</div><div class="hint">CV ${consistente.cv.toFixed(2)}% · σ ${consistente.sigma.toFixed(3)}s</div></div>
      ${(() => {
        const ord2 = [...ss.cv].sort((a, b) => a.median - b.median);
        if (ord2.length < 2) return "";
        const dif = ord2[1].median - ord2[0].median;
        return `<div class="card tile" style="--tc:${ord2[1].color}"><div class="label">Diferencia</div>
        <div class="value">+${dif.toFixed(3)}s</div><div class="hint">${ord2[1].code} vs ${ord2[0].code} · por vuelta (mediana)</div></div>`;
      })()}
      <div class="card tile"><div class="label">Vueltas de la sesión</div>
        <div class="value">${ss.n_laps}</div><div class="hint">${ss.type === "race" ? "carrera" : ss.type === "quali" ? "clasificación" : "práctica"}</div></div>
    </div>`));
  }

  // tablero de qualy
  if (ss.quali && ss.quali.length) {
    Z.resumen.appendChild(el(`<div class="section-title">Clasificación Q1 · Q2 · Q3
      <small> · ${ss.summaries.quali || ""}</small></div>`));
    const rows = ss.quali.map((r) => `<tr><td class="num">${r.pos ?? "—"}</td>
      <td>${drvChip(r.code, r.color)}</td>
      <td class="num">${r.q1}</td><td class="num">${r.q2}</td><td class="num">${r.q3}</td>
      <td class="num"><b>${r.gap}</b></td><td>${r.corte}</td></tr>`).join("");
    Z.resumen.appendChild(el(`<div class="card table-wrap" style="margin-bottom:18px"><table>
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
             "Las vueltas excluidas arrancan OCULTAS (estiran la escala); el botón dice cuántas son SC/VSC, pit y atípicas. Los ◆ PIT se marcan SIEMPRE abajo: son eventos de carrera, no errores.",
             "Toca un piloto en la leyenda para aislarlo."],
      legendHtml: `<div class="compound-legend">${Object.entries(COMP_COLORS).map(([k, v]) =>
        `<span class="chip" style="--cc:${v}"><i></i>${k}</span>`).join("")}
        <span class="chip" style="--cc:#5b616d"><i></i>✕ atípica</span>
        <span class="chip" style="--cc:#fff"><i></i>◆ pit</span>
        <button class="pill" id="evoTgl" style="margin-left:auto">${state.evoOut === true ? "OCULTAR ATÍPICAS" : "MOSTRAR ATÍPICAS"}</button></div>`,
    });
    Z.ritmo.appendChild(cEvo.card);
    Z.ritmo.appendChild(el(`<div style="height:20px"></div>`));
    cEvo.card.querySelector("#evoTgl").onclick = () => {
      state.evoOut = state.evoOut !== true;
      rerender();
    };
    const traces = [];
    const outX = [], outY = [];
    const pitX = [], pitY = [], pitC = [];
    const enSC = (lap) => (ss.sc_ranges || []).some(([a, b]) => lap >= a && lap <= b);
    let nSC = 0, nPit = 0, nAtip = 0;
    ss.evo.forEach((e) => {
      // una traza POR STINT: cambiar de compuesto o parar NO es una evolución
      // continua; y dentro del stint, las vueltas faltantes cortan la línea
      const stintsDe = (ss.stints || []).filter((s) => s.code === e.code)
        .sort((a, b) => a.from - b.from);
      const tramos = stintsDe.length ? stintsDe : [{ from: -1e9, to: 1e9 }];
      let primera = true;
      tramos.forEach((st) => {
        const limpio = e.points.filter((p) => !p.out && p.lap >= st.from && p.lap <= st.to);
        if (!limpio.length) return;
        const xsL = [], ysL = [], cdL = [];
        limpio.forEach((p, i) => {
          if (i && p.lap - limpio[i - 1].lap > 1) { xsL.push(null); ysL.push(null); cdL.push(["", ""]); }
          xsL.push(p.lap); ysL.push(p.t); cdL.push([fmtLap(p.t), p.comp]);
        });
        traces.push({ type: "scatter", mode: "lines+markers", name: e.code,
          legendgroup: e.code, showlegend: primera, connectgaps: false,
          x: xsL, y: ysL,
          line: { color: e.color, width: 1.7 },
          marker: { size: 6, color: cdL.map((cd) => COMP_COLORS[cd[1]] || e.color),
                    line: { color: "#11141b", width: 1 } },
          customdata: cdL,
          hovertemplate: `<b>${e.code}</b> · V%{x}<br>%{customdata[0]} · %{customdata[1]}<extra></extra>` });
        primera = false;
      });
      e.points.filter((p) => p.out).forEach((p) => {
        outX.push(p.lap); outY.push(p.t);
        if (p.pit) nPit++; else if (enSC(p.lap)) nSC++; else nAtip++;
      });
      e.points.filter((p) => p.pit).forEach((p) => { pitX.push(p.lap); pitY.push(p.t); pitC.push(e.color); });
    });
    const mostrar = state.evoOut === true;   // ocultas por defecto
    if (!mostrar && outX.length)
      cEvo.card.querySelector("#evoTgl").textContent =
        `${outX.length} OCULTAS · ${nSC} SC/VSC · ${nPit} PIT · ${nAtip} ATÍPICAS · MOSTRAR`;
    if (mostrar && outX.length)
      traces.push({ type: "scatter", mode: "markers", name: "Excluidas",
        x: outX, y: outY, marker: { symbol: "x-thin-open", size: 6, color: "#5b616d" },
        hoverinfo: "skip" });
    // los PIT son eventos estructurales: siempre visibles (con atípicas
    // ocultas se marcan abajo, porque su tiempo real queda fuera de escala)
    if (mostrar && pitX.length)
      traces.push({ type: "scatter", mode: "markers", name: "Pit",
        x: pitX, y: pitY, marker: { symbol: "diamond", size: 7, color: pitC,
        line: { color: "#fff", width: 1 } },
        hovertemplate: "PIT · V%{x}<extra></extra>" });
    // el RANGO del eje lo decide el toggle: con atípicas ocultas la escala
    // es la de las vueltas limpias (antes los pits de 2:20 aplastaban todo)
    const limpiasY = ss.evo.flatMap((e) => e.points.filter((p) => !p.out).map((p) => p.t));
    const todasY = ss.evo.flatMap((e) => e.points.map((p) => p.t));
    const ys = (mostrar ? todasY : limpiasY).filter((v) => v != null);
    const tt = timeTicks(ys.length ? ys : [60, 120]);
    const pad = (Math.max(...ys) - Math.min(...ys)) * 0.05 + 0.15;
    const rangoY = [Math.min(...ys) - pad, Math.max(...ys) + pad];
    const maxLapEvo = Math.max(...ss.evo.flatMap((e) => e.points.map((p) => p.lap)));
    const scShapesEvo = (ss.sc_ranges || []).map(([l0, l1]) => ({
      type: "rect", x0: Math.max(1, l0) - 0.5, x1: Math.min(l1, maxLapEvo) + 0.5,
      yref: "paper", y0: 0, y1: 1,
      fillcolor: "rgba(255,196,0,.07)", line: { width: 0 }, layer: "below" }));
    const pitAnnots = !mostrar ? pitX.map((l, i) => ({
      x: l, yref: "paper", y: 0.015, text: "◆", showarrow: false,
      font: { size: 10, color: pitC[i] } })) : [];
    Plotly.newPlot(cEvo.plot, traces, baseLayout({
      height: 560, hovermode: "closest", shapes: scShapesEvo,
      annotations: [...(ss.sc_ranges || []).map(([l0, l1]) => ({
        x: (Math.max(1, l0) + Math.min(l1, maxLapEvo)) / 2, yref: "paper", y: 1.03,
        text: "SC/VSC", showarrow: false,
        font: { size: 9, color: "#FFC400" } })), ...pitAnnots],
      margin: { l: 64, r: 14, t: 30, b: 44 },
      xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } } },
      yaxis: { ...baseLayout().yaxis, ...tt, range: rangoY },
      legend: { orientation: "h", y: -0.12, font: { size: 10.5 } },
    }), PLOTLY_CFG);
  }

  // ── POSICIÓN + GAP AL LÍDER: un panel sincronizado (misma historia)
  if (ss.positions && ss.positions.length) {
    const maxLapP = Math.max(...ss.positions.flatMap((x) => x.laps));
    const scShapesLap = (ss.sc_ranges || []).map(([l0, l1]) => ({
      type: "rect", x0: Math.max(1, l0) - 0.5, x1: Math.min(l1, maxLapP) + 0.5,
      yref: "paper", y0: 0, y1: 1,
      fillcolor: "rgba(255,196,0,.07)", line: { width: 0 }, layer: "below" }));

    // resumen de historia de carrera, calculado
    let sumLap = "";
    {
      const lideres = {};
      ss.positions.forEach((x) => x.pos.forEach((p) => {
        if (p === 1) lideres[x.code] = (lideres[x.code] || 0) + 1;
      }));
      const led = Object.entries(lideres).sort((a, b) => b[1] - a[1])[0];
      const partes = [];
      if (led) partes.push(`${led[0]} lideró ${led[1]} de ${maxLapP} vueltas.`);
      ss.positions.forEach((x) => {
        const peor = Math.max(...x.pos), fin2 = x.pos[x.pos.length - 1];
        if (peor - fin2 >= 3)
          partes.push(`${x.code} cayó hasta P${peor} y recuperó hasta P${fin2}.`);
      });
      sumLap = partes.join(" ");
    }

    const cPG = chartCard({
      title: "Posición y gap al líder",
      sub: "posición OFICIAL al cierre de cada vuelta (escalones) · abajo: segundos tras el líder · zoom y cursor compartidos",
      summary: sumLap,
      tips: ["La posición es un ESCALÓN por vuelta: P3→P7 no 'pasa por' P4-P6, cambia al cierre de la vuelta. Y P1−P2 no mide rendimiento (pueden separarlos 0.2s o 20s): por eso el gap va debajo, sincronizado.",
             "<b>¿Caída de posiciones + escalón de ~20s en el gap?</b> → pit stop (los ◆ lo marcan). <b>¿Todas las líneas del gap se comprimen?</b> → SC: el pelotón se reagrupa.",
             "Los huecos en el gap son vueltas sin marca de tiempo fiable: se CORTAN, no se inventan.",
             "El gap abre en vista CABEZA (0-60s) para no dejar que un doblado aplaste la resolución; usa TODO para el panorama completo.",
             "Con 2 pilotos seleccionados, ENTRE SELECCIONADOS resta sus gaps y muestra su duelo directo."],
    });
    Z.ritmo.appendChild(cPG.card);
    Z.ritmo.appendChild(el(`<div style="height:20px"></div>`));
    const pPos = cPG.plot;
    const pGap = el(`<div></div>`);
    cPG.card.querySelector(".chart-body").appendChild(pGap);

    // pits ◆ sobre la línea de posición
    const pitMarks = [];
    (ss.pits || []).forEach((pp) => {
      const serie = ss.positions.find((x) => x.code === pp.code);
      if (!serie) return;
      (pp.stops || []).forEach((st) => {
        const i = serie.laps.indexOf(st.lap);
        if (i >= 0) pitMarks.push({ lap: st.lap, pos: serie.pos[i], color: serie.color });
      });
    });
    const finLbls = ss.positions.map((x) => ({
      x: x.laps[x.laps.length - 1], y: x.pos[x.pos.length - 1],
      text: `${x.code} · P${x.pos[x.pos.length - 1]}`, showarrow: false,
      xanchor: "left", xshift: 6, font: { size: 10, color: x.color } }));
    Plotly.newPlot(pPos, [
      ...ss.positions.map((x) => ({
        type: "scatter", mode: "lines", name: x.code, legendgroup: x.code,
        x: x.laps, y: x.pos,
        line: { color: x.color, width: 2, shape: "hv" },
        hovertemplate: `<b>${x.code}</b> · V%{x} · P%{y}<extra></extra>`,
      })),
      { type: "scatter", mode: "markers", showlegend: false,
        x: pitMarks.map((m) => m.lap), y: pitMarks.map((m) => m.pos),
        marker: { symbol: "diamond", size: 7, color: pitMarks.map((m) => m.color),
                  line: { color: "#fff", width: 1 } },
        hovertemplate: "PIT · V%{x}<extra></extra>" },
    ], baseLayout({
      height: chartHeight({ items: ss.positions.length, min: 240, max: 320, per: 18 }),
      shapes: scShapesLap,
      margin: { l: 46, r: 66, t: 20, b: 6 },
      annotations: finLbls,
      xaxis: { ...baseLayout().xaxis, showticklabels: false },
      yaxis: { ...baseLayout().yaxis, title: { text: "POSICIÓN", font: { size: 10 } },
               autorange: "reversed", dtick: 1 },
      legend: { orientation: "h", y: 1.22, x: 1, xanchor: "right", font: { size: 10 } },
    }), PLOTLY_CFG);

    if (ss.gaps && ss.gaps.length) {
      const dosSel = ss.gaps.length === 2;
      const ctlG = el(`<div class="pills" style="padding:0 18px 12px">
        <button class="pill active" data-r="60">CABEZA · 0-60s</button>
        <button class="pill" data-r="0">TODO</button>
        <button class="pill" data-r="180">0-180s</button>
        ${dosSel ? `<span style="width:14px"></span>
        <button class="pill active" data-gm="lider">AL LÍDER</button>
        <button class="pill" data-gm="sel">ENTRE SELECCIONADOS</button>` : ""}</div>`);
      cPG.card.insertBefore(ctlG, cPG.card.querySelector(".chart-summary") || cPG.card.querySelector(".chart-guide"));

      const dibujaGap = () => {
        const modo = dosSel && state.gapModo === "sel" ? "sel" : "lider";
        ctlG.querySelectorAll("[data-gm]").forEach((b) =>
          b.classList.toggle("active", b.dataset.gm === modo));
        ctlG.querySelectorAll("[data-r]").forEach((b) =>
          b.style.display = modo === "sel" ? "none" : "");
        let trazasG;
        if (modo === "sel") {
          const [A, B] = ss.gaps;
          const porLap = new Map(B.laps.map((l, i) => [l, B.gap[i]]));
          const xsG = [], ysG = [];
          A.laps.forEach((l, i) => {
            const gb = porLap.get(l);
            xsG.push(l);
            ysG.push(A.gap[i] != null && gb != null ? +(A.gap[i] - gb).toFixed(2) : null);
          });
          trazasG = [{ type: "scatter", mode: "lines", name: `${A.code} − ${B.code}`,
            x: xsG, y: ysG, connectgaps: false,
            line: { color: A.color, width: 2 },
            hovertemplate: `V%{x} · ${A.code} %{y:+.1f}s vs ${B.code}<extra></extra>` }];
        } else {
          trazasG = ss.gaps.map((x) => ({
            type: "scatter", mode: "lines", name: x.code, legendgroup: x.code,
            showlegend: false, x: x.laps, y: x.gap, connectgaps: false,
            line: { color: x.color, width: 2 },
            hovertemplate: `<b>${x.code}</b> · V%{x}<br>+%{y:.1f}s<extra></extra>` }));
        }
        Plotly.react(pGap, trazasG, baseLayout({
          height: 380, shapes: scShapesLap,
          margin: { l: 46, r: 66, t: 8, b: 44 },
          xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } } },
          yaxis: { ...baseLayout().yaxis,
                   title: { text: modo === "sel" ? "DIFERENCIA (S)" : "SEGUNDOS TRAS EL LÍDER", font: { size: 10 } },
                   ...(modo === "sel"
                       ? { autorange: true, zeroline: true, zerolinecolor: "rgba(255,255,255,.3)" }
                       : { range: [60, -2], autorange: false }) },
          showlegend: false,
        }), PLOTLY_CFG);
      };
      ctlG.querySelectorAll("[data-r]").forEach((b) => {
        b.onclick = () => {
          ctlG.querySelectorAll("[data-r]").forEach((p) => p.classList.remove("active"));
          b.classList.add("active");
          const r = +b.dataset.r;
          Plotly.relayout(pGap, r ? { "yaxis.range": [r, -2], "yaxis.autorange": false }
                                  : { "yaxis.autorange": "reversed" });
        };
      });
      ctlG.querySelectorAll("[data-gm]").forEach((b) => {
        b.onclick = () => { state.gapModo = b.dataset.gm; dibujaGap(); };
      });
      dibujaGap();
      sincronizaX([pPos, pGap]);
    }
  }

  // DISTRIBUCIÓN DE RITMO: ancho completo, ordenado por mediana
  if (ss.box.length) {
    const med = (arr) => { const a = [...arr].sort((x, y) => x - y);
      return a.length % 2 ? a[(a.length - 1) / 2] : (a[a.length / 2 - 1] + a[a.length / 2]) / 2; };
    const orden = [...ss.box].sort((a, b) => med(a.times) - med(b.times));
    let sumBox = "";
    if (ss.box.length === 2 && ss.box[0].times.length >= 8 && ss.box[1].times.length >= 8) {
      // bootstrap de la diferencia de MEDIANAS (4,000 remuestreos)
      const medArr = (a) => { const s = [...a].sort((x, y) => x - y); return s[Math.floor(s.length / 2)]; };
      const [A, B] = [...ss.box].sort((a, b) => medArr(a.times) - medArr(b.times));
      const difs = [];
      for (let it = 0; it < 4000; it++) {
        const re = (arr) => arr[Math.floor(Math.random() * arr.length)];
        const sa = A.times.map(() => re(A.times)), sb = B.times.map(() => re(B.times));
        difs.push(medArr(sb) - medArr(sa));
      }
      difs.sort((x, y) => x - y);
      const lo = difs[Math.floor(0.025 * difs.length)], hi = difs[Math.floor(0.975 * difs.length)];
      const D = medArr(B.times) - medArr(A.times);
      sumBox = `Diferencia de medianas: ${A.code} ${D.toFixed(3)}s más rápido que ${B.code} · ` +
        `IC 95% bootstrap [${lo.toFixed(3)}, ${hi.toFixed(3)}] → ` +
        `${lo > 0 ? "diferencia CONCLUYENTE" : "diferencia INCONCLUSA"}. ` +
        `La dispersión mezcla compuestos, stints y tráfico: no es solo 'consistencia'.`;
    }
    const cBox = chartCard({
      title: "Distribución de ritmo",
      sub: "horizontal: más a la IZQUIERDA = más rápido · el más veloz arriba · cada punto = una vuelta limpia",
      summary: sumBox,
      tips: ["<b>¿Caja más a la izquierda?</b> → ese piloto rueda más rápido; los tiempos se leen como en una recta de meta.",
             "<b>¿Caja corta?</b> → piloto metrónomo: casi todas sus vueltas son iguales.",
             "<b>¿Caja adelantada pero larga?</b> → rápido pero irregular; la mediana (línea central) es su ritmo real.",
             "<b>¿Puntos sueltos lejos de la caja?</b> → vueltas raras que sobrevivieron al filtro: tráfico o goma muerta.",
             "Comparar MEDIANAS es más honesto que comparar la mejor vuelta."],
    });
    Z.ritmo.appendChild(cBox.card);
    Z.ritmo.appendChild(el(`<div style="height:20px"></div>`));
    const tt = timeTicks(ss.box.flatMap((b) => b.times));
    Plotly.newPlot(cBox.plot, orden.map((b) => ({
      type: "box", x: b.times, name: b.code,
      boxpoints: "all", jitter: 0.55, pointpos: 0, boxmean: true, width: 0.55,
      marker: { color: rgba(b.color, 0.4), size: 3.8 },
      line: { color: b.color, width: 2.2 },
      fillcolor: rgba(b.color, 0.13),
      customdata: b.times.map(fmtLap),
      hovertemplate: `<b>${b.code}</b> · %{customdata}<extra></extra>`,
    })), baseLayout({
      height: chartHeight({ items: ss.box.length, min: 280, max: 560, per: 44 }),
      showlegend: false,
      annotations: orden.map((b) => ({
        y: b.code, x: med(b.times), yshift: 25, showarrow: false,
        text: fmtLap(med(b.times)),
        font: { size: 10.5, color: b.color, family: "Inter" },
      })),
      margin: { l: 64, r: 14, t: 8, b: 44 },
      xaxis: { ...baseLayout().xaxis, ...tt, tickfont: { size: 11 } },
      yaxis: { ...baseLayout().yaxis, autorange: "reversed", gridcolor: "rgba(0,0,0,0)",
               tickfont: { size: 11.5 } },
    }), PLOTLY_CFG);
  }

  // CONSISTENCIA (CV): tabla a lo ancho
  if (ss.cv.length) {
    const badge = (v) => v < 0.9 ? ["#2ECC71", "Estable"] : v < 1.3 ? ["#FFC400", "Media"] : ["#FF5252", "Variable"];
    const madDe = (code) => {
      const b = (ss.box || []).find((x) => x.code === code);
      if (!b || !b.times.length) return null;
      const s = [...b.times].sort((x, y) => x - y);
      const med = s[Math.floor(s.length / 2)];
      const des = b.times.map((t2) => Math.abs(t2 - med)).sort((x, y) => x - y);
      return des[Math.floor(des.length / 2)];
    };
    const rows = ss.cv.map((r) => {
      const [c, t] = badge(r.cv);
      const mad = madDe(r.code);
      return `<tr><td>${drvChip(r.code, r.color)}</td><td class="num">${r.laps}</td>
        <td class="num">${r.median_label}</td>
        <td class="num"><b>${mad != null ? mad.toFixed(3) : "—"}</b></td>
        <td class="num">${r.iqr.toFixed(3)}</td><td class="num">${r.sigma.toFixed(3)}</td>
        <td class="num" style="color:${c}">${r.cv.toFixed(2)}% <small>${t}</small></td></tr>`;
    }).join("");
    Z.ritmo.appendChild(el(`<div class="card table-wrap" style="margin-bottom:20px">
      <div class="chart-head" style="padding:0 0 8px">
      <h2>Dispersión de vueltas limpias</h2><span class="sub">MAD e IQR son robustos; el CV (σ/mediana) queda como secundario · menor dispersión NO implica por sí sola mayor consistencia de conducción (mezcla compuestos, stints y tráfico)</span></div>
      <table><thead><tr><th>Piloto</th><th class="num">Vueltas</th><th class="num">Mediana</th>
      <th class="num">MAD</th><th class="num">IQR</th><th class="num">σ</th><th class="num">CV</th></tr></thead>
      <tbody>${rows}</tbody></table></div>`));
  }

  // ── ritmo AJUSTADO por efecto estimado del combustible (solo carrera):
  //    supuesto BAJO/BASE/ALTO con banda de sensibilidad, trazas por stint
  if (ss.type === "race" && ss.evo.length) {
    const K_BAJO = 0.025, K_BASE = 0.035, K_ALTO = 0.045;
    const cFuel = chartCard({
      title: "Ritmo ajustado por efecto estimado del combustible",
      sub: "tiempos trasladados a una referencia común de masa · NO elimina tráfico, pista ni gestión · banda = supuesto 25-45 ms/v",
      tips: ["<b>¿Tendencia cercana a cero tras ajustar?</b> → el tiempo no empeoró claramente BAJO EL SUPUESTO elegido; no prueba por sí sola que la goma 'aguantó'.",
             "<b>¿Sube bajo TODO el rango de la banda?</b> → la conclusión es robusta al supuesto de combustible: hay tendencia real de empeoramiento.",
             "<b>¿La historia cambia entre BAJO y ALTO?</b> → la conclusión depende del supuesto: trátala como inconclusa.",
             "La corrección es una ESTIMACIÓN lineal (no hay combustible medido); bajo SC o gestión la relación real cambia.",
             "Cada stint es una línea separada: cambiar de goma o parar no es una evolución continua."],
    });
    Z.ritmo.appendChild(cFuel.card);
    const ctl = el(`<div class="pills" style="padding:0 18px 10px">
      <span style="font-size:10px;letter-spacing:1.5px;color:var(--ink3);font-weight:700;align-self:center">EFECTO SUPUESTO</span>
      <button class="pill" data-k="${K_BAJO}">BAJO · 25</button>
      <button class="pill active" data-k="${K_BASE}">BASE · 35</button>
      <button class="pill" data-k="${K_ALTO}">ALTO · 45 ms/v</button></div>`);
    cFuel.card.insertBefore(ctl, cFuel.card.querySelector(".chart-guide"));
    const drawFuel = (k) => {
      ctl.querySelectorAll("[data-k]").forEach((b) =>
        b.classList.toggle("active", +b.dataset.k === k));
      const traces = [];
      ss.evo.forEach((e) => {
        const stintsDe = (ss.stints || []).filter((s) => s.code === e.code)
          .sort((a, b) => a.from - b.from);
        const tramos = stintsDe.length ? stintsDe : [{ from: -1e9, to: 1e9 }];
        let primera = true;
        tramos.forEach((st) => {
          const limpio = e.points.filter((p) => !p.out && p.lap >= st.from && p.lap <= st.to);
          if (limpio.length < 2) return;
          const xsL = [], loL = [], hiL = [], midL = [];
          limpio.forEach((p, i) => {
            if (i && p.lap - limpio[i - 1].lap > 1) {
              xsL.push(null); loL.push(null); hiL.push(null); midL.push(null);
            }
            xsL.push(p.lap);
            midL.push(p.t + k * (p.lap - 1));
            loL.push(p.t + K_BAJO * (p.lap - 1));
            hiL.push(p.t + K_ALTO * (p.lap - 1));
          });
          // banda de sensibilidad: si la conclusión cambia dentro de la banda,
          // depende del supuesto — el usuario lo VE en vez de creerle al slider
          traces.push({ type: "scatter", mode: "lines", showlegend: false,
            legendgroup: e.code, x: xsL, y: loL, connectgaps: false,
            line: { width: 0 }, hoverinfo: "skip" });
          traces.push({ type: "scatter", mode: "lines", showlegend: false,
            legendgroup: e.code, x: xsL, y: hiL, connectgaps: false,
            fill: "tonexty", fillcolor: rgba(e.color, 0.07),
            line: { width: 0 }, hoverinfo: "skip" });
          traces.push({ type: "scatter", mode: "lines", name: e.code,
            legendgroup: e.code, showlegend: primera, connectgaps: false,
            x: xsL, y: midL,
            line: { color: e.color, width: 1.7 },
            hovertemplate: `<b>${e.code}</b> · V%{x}<br>%{y:.3f}s ajustado<extra></extra>` });
          primera = false;
        });
      });
      Plotly.react(cFuel.plot, traces, baseLayout({
        height: 440, hovermode: "x unified",
        margin: { l: 64, r: 14, t: 14, b: 44 },
        xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } } },
        yaxis: { ...baseLayout().yaxis, title: { text: "SEGUNDOS (AJUSTADOS)", font: { size: 10 } } },
        legend: { orientation: "h", y: -0.12, font: { size: 10.5 } },
      }), PLOTLY_CFG);
    };
    ctl.querySelectorAll("[data-k]").forEach((b) => {
      b.onclick = () => drawFuel(+b.dataset.k);
    });
    drawFuel(K_BASE);
    Z.ritmo.appendChild(el(`<div style="height:18px"></div>`));
  }

  // MURO DE PITS (componente compartido con CARRERA)
  if (ss.stints && ss.stints.length) {
    const degPorStint = {};
    (ss.deg || []).forEach((r) => { degPorStint[`${r.code}|${r.stint}`] = r; });
    const pitsMap = {};
    (ss.pits || []).forEach((p) => { pitsMap[p.code] = p; });
    const orden = [...new Set(ss.stints.map((x) => x.code))];

    // solo cuentan las paradas MEDIBLES (las que cayeron bajo SC/VSC vienen sin dato)
    const medibles = (p) => p.stops.filter((s) => s.lost != null).length;
    const conDato = (ss.pits || []).filter((p) => p.total_lost != null && medibles(p) > 0);
    const porParada = (p) => p.total_lost / medibles(p);
    const cobertura = (p) => `${medibles(p)} de ${p.stops.length} paradas medibles`;
    let resumenPits = "";
    if (conDato.length === 1) {
      const p = conDato[0];
      resumenPits = `Solo ${p.code} tiene paradas medibles (${cobertura(p)}): pérdida promedio ` +
                    `estimada ~${porParada(p).toFixed(1)}s. El resto no es comparable ` +
                    `(SC/VSC o sin dato).`;
    } else if (conDato.length > 1) {
      const orden2 = [...conDato].sort((a, b) => porParada(a) - porParada(b));
      const rapida = orden2[0], lenta = orden2[orden2.length - 1];
      resumenPits = `Menor pérdida promedio estimada: ${rapida.code} ` +
                    `(~${porParada(rapida).toFixed(1)}s por parada, ${cobertura(rapida)}). ` +
                    `Mayor: ${lenta.code} (~${porParada(lenta).toFixed(1)}s, ${cobertura(lenta)}). ` +
                    `Paradas bajo SC no entran: no son comparables con paradas en verde.`;
    }

    const rows = orden.map((code) => {
      const segs = ss.stints.filter((x) => x.code === code)
        .sort((a, b) => a.from - b.from)
        .map((sg, i) => {
          const dg = degPorStint[`${code}|${i + 1}`];
          return { compound: sg.compound, color: sg.color, from: sg.from, to: sg.to,
            degTxt: dg ? `<em style="color:${dg.slope < 0 ? "#3F7BF0" : dg.slope < 0.05 ? "#2ECC71" : dg.slope < 0.1 ? "#FFC400" : "#FF5252"}">${(dg.slope * 1000).toFixed(0)} ms/v</em>` : "",
            extraTitle: dg ? ` · mediana ${fmtLap(dg.median)}` : "" };
        });
      const info = pitsMap[code];
      return { code, color: (ss.cv.find((c) => c.code === code) || {}).color || "#9aa0aa",
               segs, stops: info ? info.stops : [],
               totalLost: info ? info.total_lost : null };
    });
    Z.estrategia.appendChild(cardMuroPits({ rows, summary: resumenPits }));
  }

  // ── análisis de stint: degradación REAL (dentro del stint) + ritmo comparable
  //    Dos preguntas, dos gráficas: cuánto empeora la vuelta al envejecer la
  //    goma (pendiente robusta con IC) y qué ritmo comparable tiene cada stint
  //    a la MISMA edad de neumático. Nada de conectar compuestos distintos.
  if (ss.type === "race" && (ss.stints || []).length && (ss.evo || []).length) {
    const F_COMB = 0.035;  // s/vuelta: corrección de combustible DECLARADA
    const colorPil = (code) => (ss.evo.find((e) => e.code === code) || {}).color || "#9aa0aa";
    const comps = [...new Set(ss.stints.map((s) => s.compound))];
    const mediana2 = (arr) => { const s = [...arr].sort((a, b) => a - b);
      return s.length % 2 ? s[(s.length - 1) / 2] : (s[s.length / 2 - 1] + s[s.length / 2]) / 2; };

    // pendiente Theil-Sen (mediana de pendientes) + atípicos por MAD + IC por OLS
    const ajusta = (xs, ys) => {
      const pend = [];
      for (let i = 0; i < xs.length; i++)
        for (let j = i + 1; j < xs.length; j++)
          if (xs[j] !== xs[i]) pend.push((ys[j] - ys[i]) / (xs[j] - xs[i]));
      if (!pend.length) return null;
      const beta = mediana2(pend);
      const alfa = mediana2(xs.map((x, i) => ys[i] - beta * x));
      const res = xs.map((x, i) => ys[i] - (alfa + beta * x));
      const mRes = mediana2(res);
      const mad = mediana2(res.map((r) => Math.abs(r - mRes)));
      const lim = 3 * 1.4826 * Math.max(mad, 0.03);
      const dentro = res.map((r) => Math.abs(r - mRes) <= lim);
      const xi = xs.filter((_, i) => dentro[i]), yi = ys.filter((_, i) => dentro[i]);
      if (xi.length < 4) return null;
      const xm = xi.reduce((a, v) => a + v, 0) / xi.length;
      const ym = yi.reduce((a, v) => a + v, 0) / yi.length;
      const sxx = xi.reduce((a, v) => a + (v - xm) ** 2, 0);
      if (!sxx) return null;
      const bOls = xi.reduce((a, v, i) => a + (v - xm) * (yi[i] - ym), 0) / sxx;
      const s2 = Math.max(0, xi.reduce((a, v, i) => a + (yi[i] - (ym + bOls * (v - xm))) ** 2, 0) / (xi.length - 2));
      const se = Math.sqrt(s2 / sxx);
      const sePred5 = Math.sqrt(s2 * (1 / xi.length + (5 - xm) ** 2 / sxx));
      return { beta, alfa, ci: 2 * se, dentro, n: xi.length, sePred5 };
    };

    const stintsSel = (state.compFilter && comps.includes(state.compFilter)
      ? ss.stints.filter((s) => s.compound === state.compFilter) : ss.stints)
      .slice().sort((a, b) => (a.code < b.code ? -1 : a.code > b.code ? 1 : 0) || a.from - b.from);

    const stints = stintsSel.map((st) => {
      const pts = ((ss.evo.find((e) => e.code === st.code) || { points: [] }).points || [])
        .filter((p) => p.lap >= st.from && p.lap <= st.to && !p.out && !p.pit);
      const xs = pts.map((p) => p.lap - st.from + 1);
      const ys = pts.map((p) => p.t + F_COMB * (p.lap - 1));   // masa ~constante
      const fit = xs.length >= 5 ? ajusta(xs, ys) : null;
      const conf = !fit ? null : fit.n < 8 ? "BAJA" : fit.n <= 12 ? "MEDIA" : "BUENA";
      const nS = ss.stints.filter((s) => s.code === st.code && s.from < st.from).length + 1;
      return { ...st, nS, xs, ys, fit, conf, color: colorPil(st.code),
               t5: fit && Math.max(...xs) >= 5 ? fit.alfa + 5 * fit.beta : null };
    }).filter((s) => s.xs.length >= 3);

    if (stints.length) {
      const conFit = stints.filter((s) => s.fit);
      const concluyentes = conFit.filter((s) => s.fit.beta > 0 && s.fit.beta - s.fit.ci > 0)
        .sort((a, b) => b.fit.beta - a.fit.beta);
      const top = concluyentes[0] || null;
      const conT5 = stints.filter((s) => s.t5 != null).sort((a, b) => a.t5 - b.t5);
      const mejor5 = conT5[0] || null;
      const incierto = conFit.length ? [...conFit].sort((a, b) => a.fit.n - b.fit.n)[0] : null;

      Z.estrategia.appendChild(el(`<div class="section-title">Análisis de stint y degradación
        <small> · tiempos a masa constante (+${(F_COMB * 1000).toFixed(0)} ms/vuelta de combustible, declarado) · pendiente robusta con IC 95%</small></div>`));
      const pillsEl = el(`<div class="pills" style="margin-bottom:14px">
        <button class="pill ${!state.compFilter ? "active" : ""}" data-c="">TODAS</button>
        ${comps.map((c) => `<button class="pill ${state.compFilter === c ? "active" : ""}"
          data-c="${c}" style="--cc:${COMP_COLORS[c] || "#6b7280"}">${c}</button>`).join("")}</div>`);
      pillsEl.querySelectorAll("[data-c]").forEach((b) => {
        b.onclick = () => { state.compFilter = b.dataset.c || null; rerender(); };
      });
      Z.estrategia.appendChild(pillsEl);

      Z.estrategia.appendChild(el(`<div class="tiles" style="margin-bottom:18px">
        <div class="card tile" style="--tc:${top ? top.color : "#5b616d"}">
          <div class="label">Mayor degradación concluyente</div>
          <div class="value" style="font-size:22px">${top ? `${top.code} · S${top.nS}` : "ninguna"}</div>
          <div class="hint">${top
            ? `${top.compound} · +${(top.fit.beta * 1000).toFixed(0)}±${(top.fit.ci * 1000).toFixed(0)} ms/v · ${top.fit.n} vueltas limpias · confianza ${top.conf}`
            : "ninguna pendiente positiva con el IC completo sobre cero"}</div></div>
        ${mejor5 ? `<div class="card tile" style="--tc:${mejor5.color}">
          <div class="label">Mejor ritmo comparable (edad 5)</div>
          <div class="value" style="font-size:22px">${mejor5.code} · S${mejor5.nS}</div>
          <div class="hint">${mejor5.compound} · ${fmtLap(mejor5.t5)} estimado con 5 vueltas de goma</div></div>` : ""}
        ${incierto ? `<div class="card tile" style="--tc:${incierto.color}">
          <div class="label">Mayor incertidumbre</div>
          <div class="value" style="font-size:22px">${incierto.code} · S${incierto.nS}</div>
          <div class="hint">${incierto.fit.n} vueltas limpias · IC ±${(incierto.fit.ci * 1000).toFixed(0)} ms/v</div></div>` : ""}
      </div>`));

      // gráfica 1: degradación DENTRO del stint (edad vs segundos perdidos)
      const conAjuste = stints.filter((s) => s.fit);
      if (conAjuste.length) {
        const cDeg = chartCard({
          title: "Degradación dentro del stint",
          sub: "X = edad del neumático · Y = segundos perdidos vs el inicio (masa constante) · huecos = vueltas excluidas",
          tips: ["<b>¿Línea que sube?</b> → cada vuelta es más lenta que la anterior a masa constante: tendencia real de degradación (goma + pista + gestión).",
                 "<b>±IC en la leyenda</b>: si el intervalo llega al cero, la tendencia NO es concluyente.",
                 "<b>Puntos huecos</b> → vueltas atípicas excluidas del ajuste robusto (tráfico, errores, SC).",
                 "La pendiente observada mezcla goma, pista, tráfico y gestión; el combustible sí está corregido (35 ms/v declarados)."],
        });
        Z.estrategia.appendChild(cDeg.card);
        Z.estrategia.appendChild(el(`<div style="height:20px"></div>`));
        const DASH_ST = ["solid", "dash", "dot", "longdash"];
        const trazasDeg = [];
        conAjuste.forEach((s) => {
          const base = s.fit.alfa + s.fit.beta;
          const nombre = `${s.code} S${s.nS} · ${s.fit.beta >= 0 ? "+" : ""}${(s.fit.beta * 1000).toFixed(0)}±${(s.fit.ci * 1000).toFixed(0)} ms/v`;
          const xIn = s.xs.filter((_, i) => s.fit.dentro[i]);
          const yIn = s.ys.filter((_, i) => s.fit.dentro[i]).map((v) => v - base);
          const xOut = s.xs.filter((_, i) => !s.fit.dentro[i]);
          const yOut = s.ys.filter((_, i) => !s.fit.dentro[i]).map((v) => v - base);
          trazasDeg.push({ type: "scatter", mode: "markers", name: nombre, legendgroup: nombre,
            x: xIn, y: yIn,
            marker: { size: 7, color: s.color, symbol: "circle",
                      line: { color: COMP_COLORS[s.compound] || "#11141b", width: 1.5 } },
            hovertemplate: `<b>${s.code} S${s.nS}</b> · edad %{x}<br>%{y:+.2f}s vs inicio<extra></extra>` });
          if (xOut.length) trazasDeg.push({ type: "scatter", mode: "markers", showlegend: false,
            legendgroup: nombre, x: xOut, y: yOut,
            marker: { size: 7, color: "rgba(0,0,0,0)", symbol: "circle-open",
                      line: { color: "#6b7280", width: 1.5 } },
            hovertemplate: "excluida del ajuste · %{y:+.2f}s<extra></extra>" });
          const eMax = Math.max(...s.xs);
          trazasDeg.push({ type: "scatter", mode: "lines", showlegend: false, legendgroup: nombre,
            x: [1, eMax], y: [0, s.fit.beta * (eMax - 1)],
            line: { color: s.color, width: 2, dash: DASH_ST[(s.nS - 1) % DASH_ST.length] },
            hoverinfo: "skip" });
        });
        Plotly.newPlot(cDeg.plot, trazasDeg, baseLayout({
          height: 400, margin: { l: 56, r: 16, t: 14, b: 46 },
          xaxis: { ...baseLayout().xaxis, title: { text: "EDAD DEL NEUMÁTICO (VUELTAS)", font: { size: 10 } }, dtick: 2 },
          yaxis: { ...baseLayout().yaxis, title: { text: "SEGUNDOS PERDIDOS VS INICIO", font: { size: 10 } },
                   zeroline: true, zerolinecolor: "rgba(255,255,255,.25)" },
          legend: { orientation: "h", y: -0.16, font: { size: 10 } },
        }), PLOTLY_CFG);
      }

      // gráfica 2: ritmo comparable a edad común (SIN conectar compuestos)
      if (conT5.length) {
        // comparación pareada HONESTA: diferencia con su propio IC, y solo
        // entre stints del mismo compuesto; el veredicto se declara
        let sumCmp = top
          ? `Mayor pendiente concluyente: ${top.code} S${top.nS} (${top.compound}, +${(top.fit.beta * 1000).toFixed(0)} ms/v, confianza ${top.conf}). `
          : "Ninguna pendiente de degradación es concluyente en esta selección (IC cruzando el cero o pocas vueltas limpias). ";
        const pares = [];
        conT5.forEach((a) => conT5.forEach((b) => {
          if (a.code < b.code && a.compound === b.compound) pares.push([a, b]);
        }));
        if (pares.length) {
          const [pa, pb] = pares.sort((p1, p2) =>
            Math.abs(p2[0].t5 - p2[1].t5) - Math.abs(p1[0].t5 - p1[1].t5))[0];
          const rap2 = pa.t5 <= pb.t5 ? pa : pb, len2 = pa.t5 <= pb.t5 ? pb : pa;
          const D = len2.t5 - rap2.t5;
          const seD = Math.sqrt((rap2.fit.sePred5 || 0) ** 2 + (len2.fit.sePred5 || 0) ** 2);
          sumCmp += `El modelo estima que ${rap2.code} S${rap2.nS} ${rap2.compound} fue ` +
            `${D.toFixed(2)}s más rápido que ${len2.code} S${len2.nS} a igual vuelta de stint y ` +
            `combustible equivalente (IC de la diferencia ±${(2 * seD).toFixed(2)}s → ` +
            `${D > 2 * seD ? "diferencia CONCLUYENTE" : "diferencia INCONCLUSA"}). ` +
            `La comparación no controla evolución de pista ni tráfico.`;
        }
        const cCmp = chartCard({
          title: "Ritmo típico por stint · comparable a la vuelta 5",
          sub: "punto = ritmo estimado en la VUELTA 5 del stint · corrección ESTIMADA de combustible (35 ms/v) · barra = IC 95% del ritmo medio · agrupado por compuesto",
          summary: sumCmp,
          tips: ["Cada stint se evalúa a la MISMA vuelta de stint (la 5ª): comparar medianas de stints de distinta duración mezcla ritmo con longitud. Ojo: es vuelta DEL STINT, no edad física total — una goma usada previamente empieza más vieja.",
                 "La barra es el IC 95% del ritmo MEDIO estimado (no el rango de una vuelta individual, que sería más ancho). <b>¿Barras que se traslapan?</b> → no declares ganador.",
                 "La corrección de combustible es una ESTIMACIÓN (35 ms/v constantes): bajo SC o gestión la relación real cambia.",
                 "Stints sin 5 vueltas limpias quedan fuera. Diferencias entre stints del mismo compuesto también cargan pista, tráfico y momento de carrera."],
        });
        Z.estrategia.appendChild(cCmp.card);
        Z.estrategia.appendChild(el(`<div style="height:20px"></div>`));
        const ordC = [...conT5].sort((a, b) =>
          (a.compound < b.compound ? -1 : a.compound > b.compound ? 1 : a.t5 - b.t5));
        const etiquetas = ordC.map((s) => `${s.code} · S${s.nS} ${s.compound}`);
        const ttC = timeTicks(ordC.map((s) => s.t5));
        Plotly.newPlot(cCmp.plot, [{
          type: "scatter", mode: "markers+text",
          y: etiquetas, x: ordC.map((s) => s.t5),
          error_x: { type: "data", array: ordC.map((s) => 2 * (s.fit.sePred5 || 0)),
                     color: "rgba(148,163,184,.45)", thickness: 1.4, width: 5 },
          marker: { size: 11, color: ordC.map((s) => COMP_COLORS[s.compound] || "#9aa0aa"),
                    line: { color: ordC.map((s) => s.color), width: 2 } },
          text: ordC.map((s) => `  ${fmtLap(s.t5)} · n=${s.fit.n}`),
          textposition: "middle right", textfont: { size: 9.5, color: "#8a94a4" },
          customdata: ordC.map((s) => [fmtLap(s.t5), s.fit.n, s.conf]),
          hovertemplate: "<b>%{y}</b><br>%{customdata[0]} en la vuelta 5 · %{customdata[1]} vueltas limpias · confianza %{customdata[2]}<extra></extra>",
          showlegend: false,
        }], baseLayout({
          height: chartHeight({ items: ordC.length, min: 260, max: 520, per: 42 }),
          margin: { l: 150, r: 100, t: 10, b: 44 },
          xaxis: { ...baseLayout().xaxis, ...ttC, tickfont: { size: 10.5 } },
          yaxis: { ...baseLayout().yaxis, autorange: "reversed", gridcolor: "rgba(255,255,255,.05)",
                   tickfont: { size: 11 } },
        }), PLOTLY_CFG);
      }

      // tabla completa: todos los números que sustentan las tarjetas
      const conDatos = stints.filter((s) => s.fit);
      if (conDatos.length) {
        Z.estrategia.appendChild(el(`<div class="card table-wrap" style="margin-bottom:20px">
          <div class="chart-head" style="padding:0 0 8px"><h2>Detalle por stint</h2>
          <span class="sub">pendiente robusta (Theil-Sen) · IC 95% aproximado · atípicos excluidos por MAD</span></div>
          <table><thead><tr><th>Piloto</th><th class="num">Stint</th><th>Compuesto</th>
            <th class="num">V. limpias</th><th class="num">Pendiente (ms/v)</th>
            <th class="num">IC 95%</th><th>Confianza</th><th class="num">Ritmo edad 5</th></tr></thead>
          <tbody>${conDatos.map((s) => {
            const b = s.fit.beta * 1000, c = s.fit.ci * 1000;
            const concl = b > 0 && b - c > 0;
            return `<tr><td>${drvChip(s.code, s.color)}</td><td class="num">S${s.nS}</td>
              <td><span class="chip" style="--cc:${COMP_COLORS[s.compound] || "#6b7280"}"><i></i>${s.compound}</span></td>
              <td class="num">${s.fit.n}</td>
              <td class="num" style="${concl ? "font-weight:800" : ""}">${b >= 0 ? "+" : ""}${b.toFixed(0)}</td>
              <td class="num">±${c.toFixed(0)}</td>
              <td>${s.conf}${concl ? "" : " · no concluyente"}</td>
              <td class="num">${s.t5 != null ? fmtLap(s.t5) : "—"}</td></tr>`;
          }).join("")}</tbody></table></div>`));
      }
    }
  }

  // ── parrilla → meta: dumbbell de cambio NETO de posición
  if (ss.grid && ss.grid.length) {
    const mejorG = [...ss.grid].sort((a, b) => b.delta - a.delta)[0];
    const cGr = chartCard({
      title: "Parrilla → meta · cambio neto de posición",
      sub: "círculo hueco = salida · relleno = meta · el cambio NETO no distingue adelantamientos, estrategia, sanciones ni retiros rivales",
      summary: (mejorG && mejorG.delta > 0)
        ? `${mejorG.code} logró el mayor avance neto entre los seleccionados: P${mejorG.grid} → P${mejorG.pos} (+${mejorG.delta}). El cambio neto no dice CÓMO se consiguió.`
        : "",
      tips: ["<b>¿Línea larga hacia la izquierda?</b> → gran avance NETO; puede venir de adelantamientos, estrategia o retiros ajenos — crúzalo con el lap chart.",
             "<b>¿Hacia la derecha?</b> → perdió posiciones netas: problema, sanción o estrategia que no pagó.",
             "La posición es ordinal: +2 posiciones no equivale a 'el doble de mejora' — P1-P2 pueden separarse 0.2s o 20s."],
    });
    Z.estrategia.appendChild(cGr.card);
    Z.estrategia.appendChild(el(`<div style="height:18px"></div>`));
    const filasG = [...ss.grid].sort((a, b) => a.pos - b.pos);
    const trazasG2 = [];
    filasG.forEach((x) => {
      trazasG2.push({ type: "scatter", mode: "lines", showlegend: false,
        x: [x.grid, x.pos], y: [x.code, x.code],
        line: { color: x.delta > 0 ? "rgba(46,204,113,.6)" : x.delta < 0 ? "rgba(255,82,82,.6)" : "rgba(120,130,145,.5)", width: 3 },
        hoverinfo: "skip" });
      trazasG2.push({ type: "scatter", mode: "markers", showlegend: false,
        x: [x.grid], y: [x.code],
        marker: { size: 9, color: "rgba(0,0,0,0)", line: { color: "#8a94a4", width: 1.5 } },
        hovertemplate: `<b>${x.code}</b> · salida P%{x}<extra></extra>` });
      trazasG2.push({ type: "scatter", mode: "markers", showlegend: false,
        x: [x.pos], y: [x.code],
        marker: { size: 10, color: (ss.evo.find((e) => e.code === x.code) || {}).color || "#9aa0aa",
                  line: { color: "#11141b", width: 1.5 } },
        hovertemplate: `<b>${x.code}</b> · meta P%{x}<extra></extra>` });
    });
    Plotly.newPlot(cGr.plot, trazasG2, baseLayout({
      height: chartHeight({ items: filasG.length, min: 220, max: 460, per: 34 }),
      margin: { l: 52, r: 70, t: 12, b: 40 },
      annotations: filasG.map((x) => ({
        x: x.pos, y: x.code, xanchor: x.pos <= x.grid ? "right" : "left",
        xshift: x.pos <= x.grid ? -12 : 12, showarrow: false,
        text: `${x.delta > 0 ? "+" : ""}${x.delta}`,
        font: { size: 10, color: x.delta > 0 ? "#2ECC71" : x.delta < 0 ? "#FF5252" : "#8a94a4" } })),
      xaxis: { ...baseLayout().xaxis, title: { text: "POSICIÓN (P1 A LA IZQUIERDA)", font: { size: 10 } },
               autorange: "reversed", dtick: 1, showgrid: true,
               gridcolor: "rgba(255,255,255,.05)", griddash: "dot" },
      yaxis: { ...baseLayout().yaxis, autorange: "reversed", gridcolor: "rgba(0,0,0,0)",
               tickfont: { size: 11 } },
    }), PLOTLY_CFG);
  }

  // ── speed trap: solo vueltas COMPARABLES en la escala; SC/pit en gris
  if (ss.trap) {
    const pitSet = new Set();
    (ss.pits || []).forEach((pp) => (pp.stops || []).forEach((st) => {
      pitSet.add(pp.code + "|" + st.lap);
      pitSet.add(pp.code + "|" + (st.lap + 1));
    }));
    const enSCt = (lap) => (ss.sc_ranges || []).some(([a, b]) => lap >= a && lap <= b);
    const esValida = (code, lap) => !enSCt(lap) && !pitSet.has(code + "|" + lap);
    const zV = ss.trap.drivers.map((c, i) => ss.trap.z[i].map((v, j) =>
      (v != null && esValida(c, ss.trap.laps[j])) ? v : null));
    const zExc = ss.trap.drivers.map((c, i) => ss.trap.z[i].map((v, j) =>
      (v != null && !esValida(c, ss.trap.laps[j])) ? 1 : null));
    const nExc = zExc.flat().filter((v) => v != null).length;
    const medDe = (fila) => {
      const v = fila.filter((x) => x != null).sort((a, b) => a - b);
      return v.length ? v[Math.floor(v.length / 2)] : null;
    };
    const medianas = ss.trap.drivers.map((c, i) => ({ c, m: medDe(zV[i]) }));
    let mejor = { v: 0, c: "" };
    zV.forEach((fila, i) => fila.forEach((v) => {
      if (v != null && v > mejor.v) mejor = { v, c: ss.trap.drivers[i] };
    }));
    const sumTrap = `${mejor.c} registró la mayor Vmax VÁLIDA: ${mejor.v.toFixed(0)} km/h. ` +
      `Medianas válidas: ${medianas.filter((m2) => m2.m != null)
        .map((m2) => `${m2.c} ${m2.m.toFixed(0)}`).join(" · ")} km/h. ` +
      `${nExc} celdas excluidas de la escala por SC/VSC o pit.`;

    const cTr = chartCard({
      title: "Speed trap por vuelta",
      sub: "velocidad punta por vuelta · solo vueltas COMPARABLES colorean la escala · gris = SC/VSC o pit",
      summary: sumTrap,
      legendHtml: `<div class="pills" style="padding:0 18px 10px">
        <button class="pill" data-tm="abs">ABSOLUTA</button>
        <button class="pill" data-tm="med">VS SU MEDIANA</button>
        ${ss.trap.drivers.length === 2 ? `<button class="pill" data-tm="duel">ENTRE PILOTOS</button>` : ""}</div>`,
      tips: ["<b>¿Una fila que se apaga al final?</b> → gestionaba o perdió rebufo; verifica que no sean celdas grises (no comparables).",
             "VS SU MEDIANA responde: ¿esta vuelta tuvo una punta inusual PARA ESE PILOTO? — mejor que la absoluta para encontrar diferencias.",
             "Un pico aislado puede venir de rebufo, aerodinámica activa en modo recta, despliegue eléctrico o viento: la gráfica sola no identifica la causa.",
             "Solo se rotulan los máximos de cada piloto; el resto vive en el hover."],
    });
    Z.ritmo.appendChild(cTr.card);
    Z.ritmo.appendChild(el(`<div style="height:18px"></div>`));

    const dibujaTrap = () => {
      const modo = state.trapModo || "abs";
      cTr.card.querySelectorAll("[data-tm]").forEach((b) =>
        b.classList.toggle("active", b.dataset.tm === modo));
      const capaGris = { type: "heatmap", x: ss.trap.laps, y: ss.trap.drivers, z: zExc,
        colorscale: [[0, "#343b45"], [1, "#343b45"]], showscale: false,
        hoverongaps: false, xgap: 2, ygap: 3,
        hovertemplate: "<b>%{y}</b> · V%{x}<br>no comparable (SC/VSC o pit)<extra></extra>" };
      let capa, anots = [];
      if (modo === "med") {
        const zM = zV.map((fila, i) => fila.map((v) =>
          v != null && medianas[i].m != null ? +(v - medianas[i].m).toFixed(1) : null));
        const mx = Math.max(...zM.flat().filter((v) => v != null).map(Math.abs), 1);
        capa = { z: zM, zmin: -mx, zmax: mx,
          colorscale: [[0, "#E0243F"], [0.5, "#39424e"], [1, "#38bdf8"]],
          barTitulo: "Δ VS SU MEDIANA",
          hover: "<b>%{y}</b> · V%{x}<br>%{z:+.0f} km/h vs su mediana<extra></extra>" };
      } else if (modo === "duel" && ss.trap.drivers.length === 2) {
        const dif = ss.trap.laps.map((_, j) =>
          (zV[0][j] != null && zV[1][j] != null) ? +(zV[0][j] - zV[1][j]).toFixed(1) : null);
        const mx = Math.max(...dif.filter((v) => v != null).map(Math.abs), 1);
        capa = { z: [dif], y: [`${ss.trap.drivers[0]} − ${ss.trap.drivers[1]}`],
          zmin: -mx, zmax: mx,
          colorscale: [[0, "#E0243F"], [0.5, "#39424e"], [1, "#38bdf8"]],
          barTitulo: "Δ KM/H",
          hover: "V%{x} · %{z:+.0f} km/h<extra></extra>" };
      } else {
        const planos = zV.flat().filter((v) => v != null).sort((a, b) => a - b);
        capa = { z: zV,
          zmin: planos[Math.floor(planos.length * 0.04)] || 0,
          zmax: planos[planos.length - 1],
          colorscale: [[0, "#081726"], [0.55, "#155d8f"], [1, "#2f9fdd"]],
          barTitulo: "KM/H",
          hover: "<b>%{y}</b> · V%{x}<br>%{z:.0f} km/h<extra></extra>" };
        // solo se rotulan los máximos por piloto (104 números eran ruido)
        zV.forEach((fila, i) => {
          let jMax = -1;
          fila.forEach((v, j) => { if (v != null && (jMax < 0 || v > fila[jMax])) jMax = j; });
          if (jMax >= 0) anots.push({ x: ss.trap.laps[jMax], y: ss.trap.drivers[i],
            text: fila[jMax].toFixed(0), showarrow: false,
            font: { size: 10, color: "#fff", family: "Inter Black, Inter, sans-serif" } });
        });
      }
      const filasN = capa.y ? 1 : ss.trap.drivers.length;
      Plotly.react(cTr.plot, [
        ...(modo === "duel" ? [] : [capaGris]),
        { type: "heatmap", x: ss.trap.laps, y: capa.y || ss.trap.drivers, z: capa.z,
          colorscale: capa.colorscale, zmin: capa.zmin, zmax: capa.zmax,
          hoverongaps: false, xgap: 2, ygap: 3,
          hovertemplate: capa.hover,
          colorbar: { thickness: 12, outlinewidth: 0,
            title: { text: capa.barTitulo, font: { size: 9.5, color: "#8a94a4" } },
            tickfont: { size: 10, color: "#9aa0aa" } } },
      ], baseLayout({
        height: Math.max(230, filasN * 46 + 150),
        margin: { l: 100, r: 70, t: 14, b: 44 },
        annotations: anots,
        xaxis: { ...baseLayout().xaxis, title: { text: "VUELTA", font: { size: 10 } }, dtick: 2 },
        yaxis: { ...baseLayout().yaxis, autorange: "reversed", gridcolor: "rgba(0,0,0,0)",
                 tickfont: { size: 11 } },
      }), PLOTLY_CFG);
    };
    cTr.card.querySelectorAll("[data-tm]").forEach((b) => {
      b.onclick = () => { state.trapModo = b.dataset.tm; dibujaTrap(); };
    });
    dibujaTrap();
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
    Z.ritmo.appendChild(el(`<details class="card" style="margin-bottom:20px">
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

function cardMuroPits({ rows, summary, sub }) {
  // escala ABSOLUTA: todas las filas comparten el eje 1..L (vuelta total)
  const L = Math.max(...rows.map((r) =>
    r.segs.length ? (r.segs[r.segs.length - 1].to || 0) : 0), 1);
  const filas = rows.map((r) => {
    const strip = r.segs.map((sg, i) => {
      const laps = sg.laps ?? (sg.to - sg.from + 1);
      const stop = r.stops && r.stops[i];
      const left = (((sg.from - 1) / L) * 100).toFixed(2);
      const width = ((laps / L) * 100).toFixed(2);
      const badge = (i < r.segs.length - 1)
        ? `<span class="pit-badge" style="left:${((sg.to / L) * 100).toFixed(2)}%" title="Parada en la vuelta ${sg.to}${stop && stop.lost != null ? ` · ~${stop.lost.toFixed(1)}s de pérdida estimada` : " · pérdida no medible (SC/VSC o sin dato)"}">V${sg.to}${stop && stop.lost != null ? `<small>+${stop.lost.toFixed(1)}s</small>` : ""}</span>` : "";
      return `<span class="stint-seg" style="--cc:${sg.color};left:${left}%;width:${width}%"
        title="${sg.compound} · V${sg.from}-V${sg.to} (${laps} vueltas)${sg.extraTitle || ""}">
        <i></i><b>${sg.compound[0]}</b> ${laps}v ${sg.degTxt || ""}</span>${badge}`;
    }).join("");
    const nP = r.segs.length - 1;
    const tot = r.totalLost != null ? ` · ~${r.totalLost.toFixed(1)}s en pits` : "";
    return `<div class="pit-row">
      <div class="pit-who">${drvChip(r.code, r.color)}
        <small>${nP} parada${nP === 1 ? "" : "s"}${tot}</small></div>
      <div class="pit-strip">${strip}</div></div>`;
  }).join("");
  return el(`<div class="card chart-card keep-card" style="margin-bottom:20px">
    <div class="chart-head"><h2>Pits y estrategia</h2>
      <span class="sub">${sub || "eje común de vueltas: V## queda alineado entre pilotos · +s = pérdida ESTIMADA en la parada"}</span></div>
    <div style="padding:10px 18px 4px">${filas}</div>
    <div class="compound-legend" style="margin-top:6px">${Object.entries(COMP_COLORS).map(([k, v]) =>
      `<span class="chip" style="--cc:${v}"><i></i>${k}</span>`).join("")}</div>
    ${summary ? `<div class="chart-summary">${summary}</div>` : ""}
    <details class="chart-guide"><summary>¿Cómo leer esta gráfica?</summary><ul>
      <li><b>¿Paró antes que su rival directo?</b> → intento de undercut: goma nueva para atacar en las vueltas siguientes.</li>
      <li><b>¿Bloque largo al final?</b> → estiró el stint (overcut) o apostó a un SC tardío.</li>
      <li><b>¿+s alto en una parada?</b> → parada lenta o tráfico al salir; posiciones perdidas sin pelear.</li>
      <li>DEFINICIÓN de la pérdida: (vuelta de entrada + vuelta de salida) − 2× su mediana de vueltas limpias. Es una ESTIMACIÓN; las paradas bajo SC/VSC no son medibles ni comparables con paradas en verde.</li>
      <li>Una pendiente negativa dentro del stint no es automáticamente 'buena': puede ser combustible, evolución de pista o calentamiento.</li>
      <li>Pasa el cursor por bloques y badges para el detalle exacto.</li>
    </ul></details></div>`);
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
  $view.appendChild(heroTitle("Equipos", "evolución y desarrollo · déficit % al pole · convergencia"));
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

  // predicción de la próxima carrera: tendencia amortiguada + Monte Carlo
  state._pcache = state._pcache || {};
  let pred = null;
  try {
    pred = state._pcache[key] || (state._pcache[key] =
      await api(`/teams/predict/${state.year}?source=${state.teamSource}`));
  } catch (e) { pred = null; }
  if (pred && pred.teams && pred.teams.length >= 3) {
    const rot = pred.next_gp ? `Ronda ${pred.next_round} · ${pred.next_gp}` : `Ronda ${pred.next_round}`;
    $view.appendChild(el(`<div class="card" style="margin-bottom:18px">
      <div class="chart-head" style="padding:0 0 6px"><h2>Predicción · ${rot}</h2>
      <span class="sub">regresión ponderada por recencia + 4,000 ESCENARIOS DE RITMO (no simula carreras) · siempre sobre TODO el campo</span></div>
      ${(pred.summary || []).map((p) => `<div class="chart-summary ${/^(LÍMITES|OJO)/.test(p) ? "warn" : ""}" style="margin:8px 0 0">${p}</div>`).join("")}
    </div>`));

    const rowP = el(`<div class="grid cols-2" style="margin-bottom:20px"></div>`);
    $view.appendChild(rowP);

    // A) ritmo proyectado con margen de error
    const cA = chartCard({
      title: "Ritmo proyectado + intervalo predictivo",
      sub: "punto = proyección · barra = INTERVALO PREDICTIVO CENTRAL 80% (P10-P90)",
      tips: ["<b>¿Dos barras se traslapan?</b> → no es prueba formal de empate, pero la pelea no está decidida; la COMPARACIÓN DIRECTA del resumen da la probabilidad exacta.",
             "<b>¿Barra larga?</b> → equipo irregular: el modelo confía poco en él, y por eso mismo puede sorprender.",
             `0 pp = el mejor proyectado. En una vuelta de ~${Math.round(pred.pole_med || 85)}s, 0.5 pp son ~${((pred.pole_med || 85) * 0.005).toFixed(2)}s.`,
             "El modelo pesa más las últimas carreras (media vida: 3 rondas) y amortigua la tendencia para no sobre-extrapolar."],
    });
    rowP.appendChild(cA.card);
    const tA = pred.teams;   // ya viene del más rápido al más lento
    Plotly.newPlot(cA.plot, [{
      type: "scatter", mode: "markers",
      y: tA.map((t) => t.team), x: tA.map((t) => t.gap),
      error_x: { type: "data", symmetric: false,
                 array: tA.map((t) => t.hi - t.gap),
                 arrayminus: tA.map((t) => t.gap - t.lo),
                 color: "rgba(148,163,184,.45)", thickness: 1.4, width: 5 },
      marker: { size: 12, color: tA.map((t) => t.color),
                line: { color: "#11141b", width: 1.5 } },
      hovertemplate: tA.map((t) => `<b>${t.team}</b><br>gap proyectado +${t.gap.toFixed(2)}% (≈+${t.gap_s.toFixed(2)}s/vuelta)<br>margen 80%: ${t.lo.toFixed(2)}% a ${t.hi.toFixed(2)}%<extra></extra>`),
    }], baseLayout({
      height: Math.max(420, tA.length * 40 + 130), showlegend: false,
      margin: { l: 110, r: 24, t: 14, b: 46 },
      xaxis: { ...baseLayout().xaxis, title: { text: "GAP AL MEJOR PROYECTADO (%)", font: { size: 10 } },
               zeroline: true, zerolinecolor: "rgba(255,255,255,.3)", ticksuffix: "%" },
      yaxis: { ...baseLayout().yaxis, autorange: "reversed",
               gridcolor: "rgba(255,255,255,.05)", tickfont: { size: 11 } },
    }), PLOTLY_CFG);

    // B) probabilidades del Monte Carlo
    const cB = chartCard({
      title: "Probabilidades · 4,000 escenarios de ritmo",
      sub: "barra sólida = más rápido EN RITMO · fondo tenue = top 3 de ritmo · bullet: la sólida vive DENTRO de la tenue · solo equipos con ≥1%",
      tips: ["Son escenarios de RITMO, no carreras: el modelo no conoce lluvia, abandonos ni estrategia.",
             "Los equipos ausentes rondan el 0%: su probabilidad combinada de ser los más rápidos es <1%.",
             "P(más rápido) ≤ P(top 3) siempre: por eso la barra sólida vive dentro de la tenue (bullet).",
             "<b>Probabilidad no es destino:</b> 40% significa que en 6 de cada 10 escenarios el más rápido fue OTRO.",
             "El error Monte Carlo con 4,000 escenarios es ±1.6 pp como máximo: los enteros mostrados son estables."],
    });
    rowP.appendChild(cB.card);
    // solo equipos con opciones reales (≥1% al top 3): diez barras en 0% no informan
    const tB = pred.teams.filter((t) => t.p_top3 >= 0.01)
      .sort((a, b) => a.p_win - b.p_win || a.p_top3 - b.p_top3);
    Plotly.newPlot(cB.plot, [
      { type: "bar", orientation: "h", name: "TOP 3 DE RITMO", width: 0.62,
        y: tB.map((t) => t.team), x: tB.map((t) => t.p_top3 * 100),
        marker: { color: tB.map((t) => rgba(t.color, 0.25)), line: { color: "#11141b", width: 1 } },
        text: tB.map((t) => ` ${(t.p_top3 * 100).toFixed(0)}% `), textposition: "outside",
        textfont: { size: 9.5, color: "#77839a" },
        hovertemplate: "<b>%{y}</b> · %{x:.0f}% de estar en el top 3 de ritmo<extra></extra>" },
      { type: "bar", orientation: "h", name: "MÁS RÁPIDO", width: 0.3,
        y: tB.map((t) => t.team), x: tB.map((t) => t.p_win * 100),
        marker: { color: tB.map((t) => t.color), line: { color: "#11141b", width: 1 } },
        text: tB.map((t) => t.p_win >= 0.06 ? `${(t.p_win * 100).toFixed(0)}%` : ""),
        textposition: "inside", textfont: { size: 10, color: "#0b0d12" },
        hovertemplate: "<b>%{y}</b> · %{x:.0f}% de ser el más rápido en ritmo<extra></extra>" },
    ], baseLayout({
      height: Math.max(360, tB.length * 44 + 130), barmode: "overlay", bargap: 0.2,
      margin: { l: 110, r: 52, t: 14, b: 46 },
      xaxis: { ...baseLayout().xaxis, title: { text: "PROBABILIDAD (%)", font: { size: 10 } },
               range: [0, 106], ticksuffix: "%" },
      yaxis: { ...baseLayout().yaxis, gridcolor: "rgba(0,0,0,0)", tickfont: { size: 11 } },
      legend: { orientation: "h", y: 1.08, x: 1, xanchor: "right", font: { size: 10 } },
    }), PLOTLY_CFG);
  }

  const conSlope = d.teams.filter((t) => t.slope != null);

  // 1) evolución del déficit al pole
  const c1 = chartCard({
    title: "Déficit al pole por equipo (pp)",
    sub: "0 = hizo la pole · normalizado por tiempo de vuelta; AÚN condicionado por circuito y sesión",
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

  // 3) tendencia estimada: FOREST PLOT con IC 95% (el R² no es credibilidad)
  if (conSlope.length >= 2) {
    const cF = chartCard({
      title: "Tendencia estimada · pp por ronda",
      sub: "punto = pendiente · barra = IC 95% · verde = mejora concluyente, rojo = empeora concluyente, gris = el intervalo cruza el cero",
      tips: ["<b>¿Barra completa a la izquierda del cero?</b> → mejora CONCLUYENTE: hasta el peor caso del intervalo recorta.",
             "<b>¿La barra cruza el cero?</b> → inconcluso: con ~9 rondas una sola carrera rara mueve la recta; no declares desarrollo.",
             "La pendiente puede cargar el ORDEN de los circuitos del calendario (no solo desarrollo): una racha de pistas favorables se disfraza de mejora.",
             "Unidad honesta: puntos porcentuales por ronda (pp/ronda), no '%' multiplicativo."],
    });
    $view.appendChild(cF.card);
    $view.appendChild(el(`<div style="height:20px"></div>`));
    const ordF = [...conSlope].sort((a, b) => a.slope - b.slope);
    const colorF = (t) => {
      const ci = t.ci || 0;
      if (t.slope + ci < 0) return "#2ECC71";
      if (t.slope - ci > 0) return "#FF5252";
      return "#8a94a4";
    };
    Plotly.newPlot(cF.plot, [{
      type: "scatter", mode: "markers",
      y: ordF.map((t) => t.team), x: ordF.map((t) => t.slope),
      error_x: { type: "data", array: ordF.map((t) => t.ci || 0),
                 color: "rgba(148,163,184,.5)", thickness: 1.6, width: 5 },
      marker: { size: 10, color: ordF.map(colorF),
                line: { color: "#11141b", width: 1.5 } },
      customdata: ordF.map((t) => [(t.ci || 0).toFixed(3), t.rounds]),
      hovertemplate: "<b>%{y}</b> · %{x:+.3f} pp/ronda<br>IC 95% ±%{customdata[0]} · %{customdata[1]} rondas<extra></extra>",
      showlegend: false,
    }], baseLayout({
      height: chartHeight({ items: ordF.length, min: 320, max: 560, per: 36 }),
      margin: { l: 110, r: 30, t: 26, b: 46 },
      shapes: [{ type: "line", x0: 0, x1: 0, yref: "paper", y0: 0, y1: 1,
                 line: { color: "rgba(255,255,255,.3)", dash: "dash", width: 1 } }],
      annotations: [
        { xref: "paper", yref: "paper", x: 0.02, y: 1.04, xanchor: "left",
          text: "← MEJORA", showarrow: false, font: { size: 9.5, color: "#2ECC71" } },
        { xref: "paper", yref: "paper", x: 0.98, y: 1.04, xanchor: "right",
          text: "EMPEORA →", showarrow: false, font: { size: 9.5, color: "#FF5252" } },
      ],
      xaxis: { ...baseLayout().xaxis, title: { text: "PENDIENTE (PP/RONDA) · IC 95%", font: { size: 10 } },
               showgrid: true, gridcolor: "rgba(255,255,255,.05)", griddash: "dot" },
      yaxis: { ...baseLayout().yaxis, gridcolor: "rgba(0,0,0,0)", tickfont: { size: 11 } },
    }), PLOTLY_CFG);

    // BASELINE LINEAL: la extrapolación de esas rectas, recentrada y con IP 80%
    const conProy = conSlope.filter((t) => t.proy != null);
    if (conProy.length) {
      const cP = chartCard({
        title: `Baseline lineal · Ronda ${d.next_round}`,
        sub: "extrapolación de la recta de cada equipo, RECENTRADA contra el mejor · punto = central · barra = intervalo predictivo 80% · sin efecto circuito",
        tips: ["Es la VARA DE MEDIR del modelo de predicción de arriba: si el modelo completo no le gana, no vale su complejidad.",
               "El mejor queda en 0 por recentrado GLOBAL: ya no se recorta a cada equipo en cero (eso destruía las diferencias relativas entre los rápidos).",
               "Sin intervalos, 0.00 y 0.04 parecían seguros; con ellos se ve el traslape. NO es una clasificación esperada.",
               "Una recta supone mejorar o empeorar eternamente al mismo ritmo: una pendiente grande extrapola dinámicas absurdas — úsala como referencia, no como expectativa."],
      });
      $view.appendChild(cP.card);
      $view.appendChild(el(`<div style="height:20px"></div>`));
      const badgeP = el(`<div class="chart-summary warn">BASELINE · referencia lineal sin efecto circuito ni condiciones de sesión; interpretar con sus intervalos.</div>`);
      cP.card.insertBefore(badgeP, cP.card.querySelector(".chart-guide"));
      const vistaP = el(`<div class="pills" style="padding:0 18px 10px">
        <button class="pill active" data-v="cont">CONTENDIENTES · 0-1.5 PP</button>
        <button class="pill" data-v="todo">TODO EL CAMPO</button></div>`);
      cP.card.insertBefore(vistaP, badgeP);
      const ordP = [...conProy].sort((a, b) => a.proy - b.proy);
      const dibujaBase = (rango) => {
        Plotly.react(cP.plot, [{
          type: "scatter", mode: "markers",
          y: ordP.map((t) => t.team), x: ordP.map((t) => t.proy),
          error_x: { type: "data", array: ordP.map((t) => t.proy_ip || 0),
                     color: "rgba(148,163,184,.5)", thickness: 1.4, width: 5 },
          marker: { size: 10, color: ordP.map((t) => t.color),
                    line: { color: "#11141b", width: 1.5 } },
          customdata: ordP.map((t) => [(t.proy_ip || 0).toFixed(2)]),
          hovertemplate: "<b>%{y}</b> · %{x:.2f} pp sobre el mejor<br>IP 80%: ±%{customdata[0]} pp<extra></extra>",
          showlegend: false,
        }], baseLayout({
          height: chartHeight({ items: ordP.length, min: 300, max: 520, per: 34 }),
          margin: { l: 110, r: 30, t: 12, b: 46 },
          shapes: [{ type: "line", x0: 0, x1: 0, yref: "paper", y0: 0, y1: 1,
                     line: { color: "rgba(255,255,255,.3)", dash: "dash", width: 1 } }],
          xaxis: { ...baseLayout().xaxis,
                   title: { text: "PP SOBRE EL MEJOR PROYECTADO · IP 80%", font: { size: 10 } },
                   ...(rango ? { range: rango, autorange: false } : { autorange: true }),
                   showgrid: true, gridcolor: "rgba(255,255,255,.05)", griddash: "dot" },
          yaxis: { ...baseLayout().yaxis, autorange: "reversed",
                   gridcolor: "rgba(0,0,0,0)", tickfont: { size: 11 } },
        }), PLOTLY_CFG);
      };
      vistaP.querySelectorAll("[data-v]").forEach((b) => {
        b.onclick = () => {
          vistaP.querySelectorAll(".pill").forEach((p) => p.classList.remove("active"));
          b.classList.add("active");
          dibujaBase(b.dataset.v === "cont" ? [-0.15, 1.5] : null);
        };
      });
      dibujaBase([-0.15, 1.5]);
    }
  }

  // 5) huella de circuito
  if (d.huella && d.huella.teams.length) {
    const cH = chartCard({
      title: "Rendimiento inesperado por ronda",
      sub: "residuo vs su nivel + tendencia (base: déficit a la MEDIANA) · azul = mejor de lo esperado · rojo = peor · solo hover, sin números",
      tips: ["<b>Celda azul intensa</b> → ese fin de semana rindió por ENCIMA de su expectativa (nivel + evolución ya descontados).",
             "<b>Columna entera teñida</b> → sesión atípica para todos (lluvia/banderas): ruido de ronda, no circuito.",
             "Un solo fin de semana NO es afinidad con el circuito: para eso harían falta repeticiones del mismo trazado o características técnicas de las pistas.",
             "Se resta la tendencia propia: el desarrollo ya no se disfraza de 'circuito' (y el líder ya no es una fila ornamental de ceros)."],
    });
    $view.appendChild(cH.card);
    $view.appendChild(el(`<div style="height:20px"></div>`));
    const zAbs = d.huella.z.flat().filter((v) => v != null).map(Math.abs)
      .sort((a, b) => a - b);
    const zTope = zAbs[Math.floor(0.95 * (zAbs.length - 1))] || 1;
    Plotly.newPlot(cH.plot, [{
      type: "heatmap", x: d.huella.labels, y: d.huella.teams, z: d.huella.z,
      colorscale: "RdBu", reversescale: true, zmid: 0,
      zmin: -zTope, zmax: zTope, xgap: 2, ygap: 3,
      hovertemplate: "<b>%{y}</b> · %{x}<br>%{z:+.2f} pp vs su expectativa (− = mejor)<extra></extra>",
      colorbar: { thickness: 12, outlinewidth: 0,
        title: { text: "PP · − MEJOR", font: { size: 9, color: "#8a94a4" } },
        tickfont: { size: 10, color: "#9aa0aa" } },
    }], baseLayout({
      height: Math.max(340, d.huella.teams.length * 36 + 150),
      margin: { l: 110, r: 70, t: 14, b: 70 },
      xaxis: { ...baseLayout().xaxis, tickangle: -32, tickfont: { size: 10 } },
      yaxis: { ...baseLayout().yaxis, autorange: "reversed", gridcolor: "rgba(0,0,0,0)",
               tickfont: { size: 11 } },
    }), PLOTLY_CFG);
  }

  // dispersión del campo: SOLO estado del campo (el baseline vive arriba,
  //    junto al forest de tendencias — no son la misma pregunta)
  if (d.conv) {
    const xsC = d.conv.rounds, ysC = d.conv.sigma;
    const nC = xsC.length;
    const deltaRec = nC >= 2 ? ysC[nC - 1] - ysC[nC - 2] : null;
    const dirC = d.conv.slope > 0 ? "al alza" : "a la baja";
    const ciC = d.conv.ci || 0;
    const verdC = Math.abs(d.conv.slope) <= ciC ? "inconclusa"
      : Math.abs(d.conv.slope) > 2 * ciC ? `${dirC} (evidencia fuerte)`
      : `${dirC} (evidencia moderada)`;
    // banda de IC 95% de la RECTA de tendencia (client-side, OLS clásico)
    const xmC = xsC.reduce((a, v) => a + v, 0) / nC;
    const sxxC = xsC.reduce((a, v) => a + (v - xmC) ** 2, 0) || 1;
    const resC = ysC.map((v, i) => v - d.conv.trend[i]);
    const sresC = Math.sqrt(resC.reduce((a, v) => a + v * v, 0) / Math.max(nC - 2, 1));
    const T95C = { 1: 12.71, 2: 4.30, 3: 3.18, 4: 2.78, 5: 2.57, 6: 2.45, 7: 2.36, 8: 2.31 };
    const t95C = T95C[nC - 2] || 2.26;
    const seFit = (x) => sresC * Math.sqrt(1 / nC + (x - xmC) ** 2 / sxxC);
    const c6 = chartCard({
      title: "Dispersión del campo completo (σ y MAD por ronda)",
      sub: "σ = clásica, sensible a rezagados · MAD = robusta · banda amarilla = IC 95% de la tendencia · escala ampliada (no inicia en cero)",
      summary: `Tendencia global: ${d.conv.slope > 0 ? "+" : ""}${d.conv.slope} pp/ronda (IC 95% ±${ciC.toFixed(3)} → ${verdC}).` +
        (deltaRec != null ? ` Última ronda: ${deltaRec >= 0 ? "+" : ""}${deltaRec.toFixed(2)} pp vs la anterior.` : "") +
        ` Con ${nC} rondas, la señal sigue condicionada por el calendario. Siempre sobre TODO el campo.`,
      tips: ["La tendencia global y el cambio reciente son escalas temporales distintas: aquí se reportan las dos.",
             "<b>¿σ sube pero MAD no?</b> → uno o dos equipos rezagados dominan la dispersión clásica; el pelotón central no se abrió.",
             "σ creciente NO implica 'el líder se escapa': puede ser la cola rezagándose o un solo equipo extremo.",
             "La banda amarilla es el IC de la RECTA: si cabe una recta plana dentro, la 'apertura' no está demostrada."],
    });
    $view.appendChild(c6.card);
    Plotly.newPlot(c6.plot, [
      { type: "scatter", mode: "lines", showlegend: false, hoverinfo: "skip",
        x: xsC, y: xsC.map((x) => d.conv.trend[xsC.indexOf(x)] - t95C * seFit(x)),
        line: { width: 0 } },
      { type: "scatter", mode: "lines", showlegend: false, hoverinfo: "skip",
        x: xsC, y: xsC.map((x) => d.conv.trend[xsC.indexOf(x)] + t95C * seFit(x)),
        fill: "tonexty", fillcolor: "rgba(255,196,0,.08)", line: { width: 0 } },
      { type: "scatter", mode: "lines+markers", name: "σ clásica",
        x: xsC, y: ysC, line: { color: "#5B8FD9", width: 2.2 },
        marker: { size: 7 },
        hovertemplate: "Ronda %{x}<br>σ = %{y:.3f} pp<extra></extra>" },
      ...(d.conv.mad ? [{ type: "scatter", mode: "lines+markers", name: "MAD robusta",
        x: xsC, y: d.conv.mad,
        line: { color: "#2dd4bf", width: 1.8, dash: "dot" }, marker: { size: 5 },
        hovertemplate: "Ronda %{x}<br>MAD = %{y:.3f} pp<extra></extra>" }] : []),
      { type: "scatter", mode: "lines", name: "tendencia σ",
        x: xsC, y: d.conv.trend,
        line: { color: "#FFC400", width: 2, dash: "dash" }, hoverinfo: "skip" },
    ], baseLayout({
      height: 380, margin: { l: 56, r: 70, t: 14, b: 44 },
      annotations: [
        { x: xsC[nC - 1], y: ysC[nC - 1], text: `σ ${ysC[nC - 1].toFixed(2)}`,
          showarrow: false, xanchor: "left", xshift: 8,
          font: { size: 10, color: "#5B8FD9" } },
        { xref: "paper", yref: "paper", x: 0.005, y: 0.02, xanchor: "left",
          text: "ESCALA AMPLIADA · NO INICIA EN CERO", showarrow: false,
          font: { size: 8.5, color: "#77839a" } },
      ],
      xaxis: { ...baseLayout().xaxis, title: { text: "RONDA", font: { size: 10 } }, dtick: 1 },
      yaxis: { ...baseLayout().yaxis, title: { text: "DISPERSIÓN (PP)", font: { size: 10 } } },
      legend: { orientation: "h", y: 1.1, x: 1, xanchor: "right" },
    }), PLOTLY_CFG);
  }
}

/* la topbar es sticky y su altura varía con el wrap: se mide de verdad
   para que la barra de pestañas de ANÁLISIS se pegue justo debajo */
let _tbH = 0;
const fijaAlturaTopbar = () => {
  const tb = document.querySelector(".topbar");
  if (!tb) return;
  const h = Math.round(tb.getBoundingClientRect().height);
  if (h && h !== _tbH) {
    _tbH = h;
    document.documentElement.style.setProperty("--topbar-h", h + "px");
  }
};
addEventListener("scroll", fijaAlturaTopbar, { passive: true });
addEventListener("resize", fijaAlturaTopbar);
addEventListener("load", fijaAlturaTopbar);
if (document.fonts && document.fonts.ready)
  document.fonts.ready.then(fijaAlturaTopbar);   // la fuente DIN cambia la altura
fijaAlturaTopbar();

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
  setTimeout(() => { t.classList.add("out"); setTimeout(() => t.remove(), 320); }, ms);
}

/* ── motion: revelado escalonado + contadores de misión ─────────────────────
   Sin IntersectionObserver (no dispara en algunos contextos embebidos):
   un ticker con rAF compara scroll y revela lo que entra en pantalla. */
const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
let _revN = 0, _revT = 0, _pendientes = 0;

function contarTiles(cont) {
  cont.querySelectorAll(".value").forEach((v) => {
    const txt = v.textContent.trim();
    const m = txt.match(/^(\d[\d.,]*)/);
    if (!m) return;
    const sufijo = txt.slice(m[1].length);
    if (sufijo.startsWith(":")) return;              // tiempos 1:34.058: no contar
    const fin = parseFloat(m[1].replace(/,/g, ""));
    if (!isFinite(fin) || fin === 0) return;
    const dec = (m[1].split(".")[1] || "").length;
    const t0 = performance.now(), dur = 700;
    const paso = (t) => {
      const p = Math.min(1, (t - t0) / dur);
      const e = 1 - Math.pow(1 - p, 3);
      v.textContent = (fin * e).toFixed(dec) + sufijo;
      if (p < 1) requestAnimationFrame(paso);
    };
    requestAnimationFrame(paso);
  });
}

function chequeaReveals() {
  if (!_pendientes) return;
  // algunos contextos embebidos reportan innerHeight 0 → triple respaldo
  const vh = Math.max(window.innerHeight || 0,
                      document.documentElement.clientHeight || 0, 500);
  const ahora = performance.now();
  document.querySelectorAll(".reveal:not(.in)").forEach((el2) => {
    const r = el2.getBoundingClientRect();
    const forzar = ahora - (+el2.dataset.rev || 0) > 4000;   // garantía absoluta
    if (forzar || (r.top < vh * 0.94 && r.bottom > -40)) {
      el2.classList.add("in");
      _pendientes--;
      if (el2.matches(".tiles")) contarTiles(el2);
    }
  });
}

const REVEAL_SEL = ".card, .section-title, .podium-hero, .race-grid, .tiles, .pills";
function armaReveal(node) {
  if (node.nodeType !== 1 || !node.matches(REVEAL_SEL)) return;
  const padre = node.closest(".card");
  if (padre && padre !== node) return;               // solo el nivel superior
  const ahora = performance.now();
  if (ahora - _revT > 700) _revN = 0;                // nueva tanda → reinicia cascada
  _revT = ahora;
  node.classList.add("reveal");
  node.dataset.rev = performance.now();
  node.style.setProperty("--d", `${Math.min(_revN++ * 55, 385)}ms`);
  _pendientes++;
}
if (!REDUCED) {
  let _chequeoProgramado = false;
  new MutationObserver((muts) => {
    muts.forEach((m) => m.addedNodes.forEach(armaReveal));
    if (!_chequeoProgramado) {
      _chequeoProgramado = true;
      setTimeout(() => { _chequeoProgramado = false; chequeaReveals(); }, 60);
    }
  }).observe($view, { childList: true, subtree: true });

  const alScroll = () => {
    document.querySelector(".topbar")?.classList.toggle("scrolled", window.scrollY > 10);
    chequeaReveals();
  };
  window.addEventListener("scroll", alScroll, { passive: true });
  window.addEventListener("resize", chequeaReveals, { passive: true });
  setInterval(chequeaReveals, 1200);   // corre incluso con la pestaña oculta
  // respaldo por rAF para contextos donde el evento scroll sea irregular
  let _lastY = -1;
  (function tick() {
    if (window.scrollY !== _lastY) { _lastY = window.scrollY; alScroll(); }
    requestAnimationFrame(tick);
  })();
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
  const bt = document.getElementById("btnTheme");
  if (bt) bt.onclick = (e) => {
    e.preventDefault();
    const nuevo = (document.documentElement.dataset.theme === "spacex") ? "habib" : "spacex";
    document.documentElement.dataset.theme = nuevo;
    localStorage.setItem("tema", nuevo);
    toast(nuevo === "spacex" ? "Tema SPACEX: negro misión + azul hielo."
                             : "Tema HABIB: broadcast clásico rojo.");
    route();
  };
  try {
    const meta = await api("/meta");
    state.seasons = meta.seasons;
    state.year = meta.seasons.length ? meta.seasons[0].year : null;
  } catch (e) { /* la ruta mostrará el error */ }
  window.addEventListener("hashchange", route);
  route();
})();
