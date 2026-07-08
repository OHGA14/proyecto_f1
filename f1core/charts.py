"""Constructores de figuras Plotly (puros: reciben datos, devuelven go.Figure)."""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from f1core.config import (DIST_CHART_CONFIG, MICRO_PURPLE, MICRO_GREEN,
                           MICRO_YELLOW, COMPOUND_COLORS)
from f1core.colors import get_neon_color, get_driver_color, get_driver_name, _adjust_luminance
from f1core.timeutils import format_time, _format_sector_time
from f1core.laps import _mark_outlier_laps
from f1core.physics import _build_minisector_layout


def make_god_chart(fig, title, y_label, x_label="Distancia (m)", height=600):

    """

    Motor Gráfico 'GOD MODE v4.0 - BROADCAST SPEC':

    - Neon cyan accent (#00f2ff) para precisión de ingeniería.

    - Ultra-thin punteadas spikes (1px dotted) para crosshairs invisibles.

    - Grid completamente eliminado.

    - Tooltips con borde neon para máxima legibilidad en broadcast.

    """

    # Clean professional layout for broadcast

    fig.update_layout(

        template="plotly_dark",

        title=dict(text=f"{title}", font=dict(size=20, color="#FFFFFF", family="Roboto"), x=0, y=0.98),

        plot_bgcolor="rgba(0,0,0,0)",

        paper_bgcolor="rgba(0,0,0,0)",

        height=height,

        hovermode="x unified",

        margin=dict(l=48, r=12, t=56, b=42),

        legend=dict(orientation="h", y=1.02, x=1, xanchor="right", bgcolor="rgba(0,0,0,0)", font=dict(family="Roboto", size=12, color="#AAA")),

        xaxis=dict(title=dict(text=x_label, font=dict(family="Roboto", size=12, color="#AAA")), showgrid=False, zeroline=False, showline=True, linecolor="#2b2b2b",
                   showspikes=True, spikemode="across", spikesnap="cursor", spikethickness=1, spikedash="dot", spikecolor="rgba(255,255,255,0.35)"),

        yaxis=dict(title=dict(text=y_label, font=dict(family="Roboto", size=12, color="#AAA")), showgrid=False, zeroline=False, showline=True, linecolor="#2b2b2b"),

        font=dict(family="Roboto", color="#ddd")

    )

    # Hover label: simple, no neon borders

    hover_cfg = dict(bgcolor="rgba(20,20,20,0.9)", font=dict(family="Roboto", size=12, color="#FFF"), align="left")

    fig.update_traces(hoverlabel=hover_cfg)

    fig.update_layout(hoverlabel=hover_cfg)

    return fig

def build_microsector_bar(tel_list, color_map, sector_cuts=None, mini_per_sector=8, threshold_s=0.02, height=None, title=None):
    """Barra tipo MultiViewer AGRUPADA POR SECTOR (S1/S2/S3): una fila por
    vuelta/piloto; dentro de cada sector, sus mini-sectores. En cada mini-sector
    el más rápido va en morado, empate (<umbral) en verde, el más lento en
    amarillo. Encima, la cabecera de cada sector marca quién lo ganó y por cuánto.
    Devuelve (fig, wins_dict, sector_summary)."""
    cleaned, mini_bounds, mat = _build_minisector_layout(tel_list, sector_cuts, mini_per_sector)
    if cleaned is None:
        return None, {}, []
    labels = [lbl for lbl, _ in cleaned]
    n = mat.shape[1]
    wins = {l: 0 for l in labels}
    n_rows = len(labels)

    # Layout en X con separación entre sectores
    GAP = 0.8
    x0s, x1s = [], []
    sector_spans = {}
    sector_order = []
    cur_x = 0.0
    prev_sector = None
    for s in range(n):
        s_lbl = mini_bounds[s][0]
        if prev_sector is not None and s_lbl != prev_sector:
            cur_x += GAP
        x0 = cur_x
        x1 = cur_x + 0.86
        x0s.append(x0)
        x1s.append(x1)
        if s_lbl not in sector_spans:
            sector_spans[s_lbl] = [x0, x1]
            sector_order.append(s_lbl)
        else:
            sector_spans[s_lbl][1] = x1
        cur_x += 1.0
        prev_sector = s_lbl
    total_x = cur_x

    fig = go.Figure()
    best_row = mat.min(axis=0)

    # Rectángulos de mini-sectores
    for s in range(n):
        col_times = mat[:, s]
        order = np.argsort(col_times)
        best_i = int(order[0])
        best_t = col_times[best_i]
        second_t = col_times[int(order[1])] if len(order) > 1 else best_t
        margin = second_t - best_t
        for row_i, label in enumerate(labels):
            y = n_rows - 1 - row_i
            gap = col_times[row_i] - best_t
            if row_i == best_i:
                col = MICRO_PURPLE if margin > threshold_s else MICRO_GREEN
                if margin > threshold_s:
                    wins[label] += 1
            else:
                col = MICRO_GREEN if gap <= threshold_s else MICRO_YELLOW
            fig.add_shape(
                type="rect", x0=x0s[s], x1=x1s[s], y0=y + 0.10, y1=y + 0.86,
                fillcolor=col, line=dict(color="#0e1117", width=1), layer="below"
            )

    # Nombre de cada piloto/vuelta a la izquierda + hover por mini-sector
    for row_i, label in enumerate(labels):
        y = n_rows - 1 - row_i
        fig.add_annotation(
            x=-0.6, y=y + 0.48, text=label, showarrow=False, xanchor="right",
            font=dict(color=color_map.get(label, "#DDD"), size=13, family="Roboto")
        )
        hov = []
        centers = []
        for s in range(n):
            centers.append((x0s[s] + x1s[s]) / 2.0)
            s_lbl, d0, d1 = mini_bounds[s]
            gap = mat[row_i, s] - best_row[s]
            hov.append(
                f"<b>{label}</b> · {s_lbl}<br>Mini-sector ({d0:.0f}-{d1:.0f} m)"
                f"<br>Tiempo: {mat[row_i, s]:.3f}s<br>Δ vs mejor: {gap:+.3f}s"
            )
        fig.add_trace(go.Scatter(
            x=centers, y=[y + 0.48] * n,
            mode='markers', marker=dict(size=16, color="rgba(0,0,0,0)"),
            hovertext=hov, hoverinfo="text", showlegend=False
        ))

    # Cabecera de sector: divisor + etiqueta + ganador del sector
    sector_summary = []
    y_top = n_rows
    for s_lbl in sector_order:
        x_start, x_end = sector_spans[s_lbl]
        x_mid = (x_start + x_end) / 2.0
        # Tiempo total del sector por piloto
        idxs = [i for i, mb in enumerate(mini_bounds) if mb[0] == s_lbl]
        sec_times = {labels[r]: float(mat[r, idxs].sum()) for r in range(n_rows)}
        win_label = min(sec_times, key=sec_times.get)
        others = [t for l, t in sec_times.items() if l != win_label]
        margin = (min(others) - sec_times[win_label]) if others else 0.0
        win_col = color_map.get(win_label, MICRO_PURPLE)
        sector_summary.append({"sector": s_lbl, "winner": win_label, "margin": margin, "times": sec_times})

        # línea de base bajo el sector
        fig.add_shape(type="rect", x0=x_start, x1=x_end, y0=y_top + 0.06, y1=y_top + 0.30,
                      fillcolor=win_col, line=dict(width=0), layer="below")
        fig.add_annotation(
            x=x_mid, y=y_top + 0.62, showarrow=False,
            text=f"<b>{s_lbl}</b>", font=dict(color="#EEE", size=13, family="Roboto")
        )
        fig.add_annotation(
            x=x_mid, y=y_top + 0.18, showarrow=False,
            text=f"{win_label} +{margin:.2f}s" if margin > 0 else win_label,
            font=dict(color=win_col, size=11, family="Roboto")
        )

    if height is None:
        height = 46 * n_rows + 72
    fig.update_xaxes(visible=False, range=[-3.6, total_x - 0.1])
    fig.update_yaxes(visible=False, range=[-0.1, n_rows + 1.0])
    fig.update_layout(
        template="plotly_dark", height=height,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30 if title else 10, b=6),
        title=dict(text=title, font=dict(size=14, color="#DDD")) if title else None,
        hovermode="closest"
    )
    return fig, wins, sector_summary

def _add_corner_labels(fig, corners_df, ref_x, ref_y, row=None, col=None, offset_frac=0.055, size=17):
    """Coloca los números de curva DESPLAZADOS hacia afuera de la línea de carrera
    (para que no queden tapados por el trazado grueso) con una pequeña guía que
    los conecta al ápice. Un solo trace por tipo = eficiente."""
    ref_x = np.asarray(ref_x, dtype=float)
    ref_y = np.asarray(ref_y, dtype=float)
    cx = float(np.nanmean(ref_x))
    cy = float(np.nanmean(ref_y))
    scale = max(float(np.nanmax(ref_x) - np.nanmin(ref_x)), float(np.nanmax(ref_y) - np.nanmin(ref_y)))
    off = scale * offset_frac
    lx, ly, txt = [], [], []
    guide_x, guide_y = [], []
    try:
        rows = list(corners_df.iterrows())
    except Exception:
        return
    for _, c in rows:
        try:
            ax, ay = float(c['X']), float(c['Y'])
            num = str(int(c['Number']))
        except Exception:
            continue
        dx, dy = ax - cx, ay - cy
        n = np.hypot(dx, dy) or 1.0
        ox, oy = ax + dx / n * off, ay + dy / n * off
        lx.append(ox)
        ly.append(oy)
        txt.append(num)
        guide_x += [ax, ox, None]
        guide_y += [ay, oy, None]
    kw = dict(row=row, col=col) if row is not None else {}
    # guía tenue del ápice al número
    fig.add_trace(go.Scatter(
        x=guide_x, y=guide_y, mode='lines',
        line=dict(color="rgba(255,255,255,0.25)", width=1),
        hoverinfo='skip', showlegend=False
    ), **kw)
    # círculo + número (fondo opaco para que se lea)
    fig.add_trace(go.Scatter(
        x=lx, y=ly, mode='markers+text',
        marker=dict(size=size, color="#12151c", line=dict(color="#FFFFFF", width=1.4)),
        text=txt, textposition="middle center",
        textfont=dict(color="#FFFFFF", size=11, family="Roboto"),
        hoverinfo='skip', showlegend=False
    ), **kw)

def build_minisector_dominance_map(tel_dict, driver_colors, circuit=None, n_sectors=30, height=560):
    """Mapa del circuito estilo F1 MultiViewer / GP Tempo: la línea de carrera
    se divide en mini-sectores y cada tramo se pinta con el color del piloto MÁS
    RÁPIDO en ese tramo (entre TODOS los seleccionados). Marca curvas numeradas y
    la línea de meta. Devuelve (fig, wins_dict)."""
    cleaned = {}
    for d, tel in tel_dict.items():
        if tel is None:
            continue
        t = tel.dropna(subset=['X', 'Y', 'Distance', 'Time']).sort_values('Distance')
        if not t.empty:
            cleaned[d] = t
    drivers = list(cleaned.keys())
    if not drivers:
        return go.Figure(), {}

    max_d = min(t['Distance'].max() for t in cleaned.values())
    min_d = max(t['Distance'].min() for t in cleaned.values())
    if not np.isfinite(max_d) or max_d <= min_d:
        return go.Figure(), {}

    # Línea de referencia: promedio de las trazadas (centro de pista)
    fine = np.linspace(min_d, max_d, 800)
    xs = np.mean([np.interp(fine, cleaned[d]['Distance'].values, cleaned[d]['X'].values) for d in drivers], axis=0)
    ys = np.mean([np.interp(fine, cleaned[d]['Distance'].values, cleaned[d]['Y'].values) for d in drivers], axis=0)

    bounds = np.linspace(min_d, max_d, n_sectors + 1)
    wins = {d: 0 for d in drivers}

    fig = go.Figure()
    # Trazado base (gris) para que no queden huecos
    fig.add_trace(go.Scatter(
        x=xs, y=ys, mode='lines',
        line=dict(color="#3a3a3a", width=9),
        hoverinfo='skip', showlegend=False
    ))

    for s in range(n_sectors):
        d0, d1 = bounds[s], bounds[s + 1]
        times = {}
        for d in drivers:
            dd = cleaned[d]['Distance'].values
            tt = cleaned[d]['Time'].dt.total_seconds().values
            times[d] = np.interp(d1, dd, tt) - np.interp(d0, dd, tt)
        order = sorted(times.items(), key=lambda kv: kv[1])
        best_d = order[0][0]
        margin = (order[1][1] - order[0][1]) if len(order) > 1 else 0.0
        wins[best_d] += 1

        idx0 = int(np.searchsorted(fine, d0))
        idx1 = int(np.searchsorted(fine, d1)) + 1  # solapa 1 punto para no dejar hueco
        seg_x = xs[idx0:idx1 + 1]
        seg_y = ys[idx0:idx1 + 1]
        col = driver_colors.get(best_d, "#AAAAAA")
        rank_txt = "<br>".join(f"{i+1}. {dd} (+{tt - order[0][1]:.3f}s)" if i else f"1. {dd} " for i, (dd, tt) in enumerate(order[:4]))
        hov = f"<b>Mini-sector {s + 1}</b><br>Más rápido: {best_d} (+{margin:.3f}s vs 2º)<br>{rank_txt}"
        fig.add_trace(go.Scatter(
            x=seg_x, y=seg_y, mode='lines',
            line=dict(color=col, width=9),
            hoverinfo='text', hovertext=[hov] * len(seg_x),
            showlegend=False
        ))

    # Curvas numeradas (desplazadas hacia afuera para que no las tape el trazado)
    if circuit is not None:
        try:
            _add_corner_labels(fig, circuit.corners, xs, ys)
        except Exception:
            pass

    # Línea de meta / salida
    fig.add_trace(go.Scatter(
        x=[xs[0]], y=[ys[0]], mode='markers',
        marker=dict(size=18, color="#FFFFFF", line=dict(color="#0e1117", width=2), symbol="square"),
        hovertemplate="Meta / Salida<extra></extra>", showlegend=False
    ))

    x_min, x_max = float(np.nanmin(xs)), float(np.nanmax(xs))
    y_min, y_max = float(np.nanmin(ys)), float(np.nanmax(ys))
    pad_x = (x_max - x_min) * 0.06 or 1
    pad_y = (y_max - y_min) * 0.06 or 1
    fig.update_layout(
        template="plotly_dark", height=height,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(visible=False, showgrid=False, scaleanchor="y", scaleratio=1, range=[x_min - pad_x, x_max + pad_x]),
        yaxis=dict(visible=False, showgrid=False, range=[y_min - pad_y, y_max + pad_y]),
        hovermode="closest", showlegend=False
    )
    return fig, wins

def apply_distance_axis(fig, corners_df=None, sector_cuts=None):
    """Estilo GP Tempo para las gráficas por DISTANCIA: líneas punteadas en cada
    curva con su número en el eje X (sin etiqueta 'Distancia'), y divisores de
    sector S1/S2/S3. `sector_cuts` = [("S1", d1), ("S2", d2), ("S3", maxd)]
    tal cual lo devuelve _get_sector_cut_distances."""
    # Divisores de sector (líneas sólidas tenues): el límite S1|S2 se etiqueta "S2",
    # el S2|S3 se etiqueta "S3" (donde empieza cada sector).
    if sector_cuts and len(sector_cuts) >= 2:
        for (sc, nxt) in zip(sector_cuts[:-1], sector_cuts[1:]):
            bx = float(sc[1])
            blabel = str(nxt[0])
            fig.add_vline(x=bx, line=dict(color="rgba(255,255,255,0.45)", width=1.3))
            fig.add_annotation(
                x=bx, y=1.0, yref="paper", text=blabel, showarrow=False,
                font=dict(color="#CCC", size=12, family="Roboto"),
                yanchor="bottom", xanchor="left", xshift=3
            )
    # Curvas numeradas como referencia del eje X
    if corners_df is not None:
        try:
            cds = [float(c['Distance']) for _, c in corners_df.iterrows()]
            nums = [str(int(c['Number'])) for _, c in corners_df.iterrows()]
        except Exception:
            cds, nums = [], []
        for cd in cds:
            fig.add_vline(x=cd, line=dict(color="rgba(255,255,255,0.14)", width=1, dash="dot"))
        if cds:
            fig.update_xaxes(tickmode='array', tickvals=cds, ticktext=nums,
                             tickfont=dict(color="#8A8A8A", size=11))
    # Sin etiqueta en el eje de abajo (las curvas son la referencia)
    fig.update_xaxes(title_text=None)
    return fig

def build_gp_tempo_chart(laps_vip_df, drivers, show_outliers=True, height=560):
    """Gráfica estilo GP Tempo: tiempo de vuelta crudo por vuelta, línea por
    piloto, marcadores coloreados por compuesto, eje Y con formato m:ss."""
    fig = go.Figure()
    all_secs = []

    for d in drivers:
        df = laps_vip_df[laps_vip_df['Driver'] == d].sort_values('LapNumber').copy()
        if df.empty:
            continue
        df['IsOutlier'] = _mark_outlier_laps(df)
        if not show_outliers:
            df = df[~df['IsOutlier']]
        if df.empty:
            continue
        c = get_neon_color(d)
        name = get_driver_name(d)
        all_secs.extend(df['Seconds'].dropna().tolist())

        comp_colors = [
            COMPOUND_COLORS.get(str(comp).upper(), COMPOUND_COLORS['UNKNOWN'])
            if pd.notna(comp) else COMPOUND_COLORS['UNKNOWN']
            for comp in (df['Compound'] if 'Compound' in df.columns else [None] * len(df))
        ]
        hover = [
            f"<b>{name}</b><br>Vuelta {int(ln)}<br>Tiempo: {format_time(s)}"
            f"<br>Compuesto: {comp if pd.notna(comp) else 'N/D'}"
            + ("<br>Vuelta atípica (pit/SC/outlier)" if o else "")
            for ln, s, comp, o in zip(
                df['LapNumber'], df['Seconds'],
                df['Compound'] if 'Compound' in df.columns else [None] * len(df),
                df['IsOutlier']
            )
        ]
        fig.add_trace(go.Scatter(
            x=df['LapNumber'], y=df['Seconds'],
            mode='lines+markers',
            name=d,
            line=dict(color=c, width=2),
            marker=dict(size=7, color=comp_colors, line=dict(width=1.5, color=c)),
            hoverinfo="text", hovertext=hover
        ))

    if all_secs:
        y_min, y_max = min(all_secs), max(all_secs)
        pad = (y_max - y_min) * 0.05 if y_max > y_min else 1
        tick_step = max(round((y_max - y_min) / 6), 2)
        tick_vals = np.arange(np.floor(y_min / tick_step) * tick_step, y_max + tick_step, tick_step)
        fig.update_yaxes(
            tickvals=tick_vals,
            ticktext=[format_time(v) for v in tick_vals],
            range=[y_min - pad, y_max + pad]
        )

    fig.update_layout(
        template="plotly_dark",
        height=height,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.05, x=0.5, xanchor="center", font=dict(size=12)),
        xaxis=dict(title="TIME / LAP NUMBER", showgrid=True, gridcolor="rgba(255,255,255,0.07)", griddash="dot", dtick=6),
        yaxis=dict(title="LAP TIME", showgrid=True, gridcolor="rgba(255,255,255,0.07)", griddash="dot"),
        margin=dict(l=60, r=20, t=40, b=50),
        hovermode="closest"
    )
    return fig


def build_historic_pace_chart(df, color_map, height=520):
    """Evolución multi-GP: % sobre la mejor vuelta de cada carrera (0% = fue el más rápido).

    df: columnas [label (GP corto), driver, pct]. La métrica es comparable entre
    circuitos porque normaliza contra la mejor vuelta de cada GP.
    """
    fig = go.Figure()
    for drv in df["driver"].unique():
        d = df[df["driver"] == drv].sort_values("orden")
        fig.add_trace(go.Scatter(
            x=d["label"], y=d["pct"], mode="lines+markers", name=drv,
            line=dict(color=color_map.get(drv, "#FFFFFF"), width=2.4, shape="spline"),
            marker=dict(size=7),
            hovertemplate=f"<b>{drv}</b> · %{{x}}<br>+%{{y:.2f}}% sobre la mejor vuelta<extra></extra>",
        ))
    fig.update_layout(
        template="plotly_dark", height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(14,17,23,1)",
        font=dict(family="Roboto", color="#e6e6e6"),
        yaxis=dict(title="% SOBRE LA MEJOR VUELTA DEL GP", ticksuffix="%",
                   showgrid=True, gridcolor="rgba(255,255,255,0.07)", griddash="dot",
                   zeroline=True, zerolinecolor="rgba(255,45,45,.55)", zerolinewidth=2),
        xaxis=dict(title="", showgrid=False),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center"),
        margin=dict(l=60, r=20, t=60, b=50), hovermode="x unified",
    )
    return fig


def build_championship_chart(df, color_map, height=520):
    """Puntos ACUMULADOS del campeonato por piloto a lo largo de la temporada.

    df: columnas [label (GP corto), orden, driver, cum_points].
    """
    fig = go.Figure()
    ultimo = df[df["orden"] == df["orden"].max()].set_index("driver")["cum_points"]
    for drv in df["driver"].unique():
        d = df[df["driver"] == drv].sort_values("orden")
        fig.add_trace(go.Scatter(
            x=d["label"], y=d["cum_points"], mode="lines+markers", name=drv,
            line=dict(color=color_map.get(drv, "#9aa0aa"), width=2.4),
            marker=dict(size=6),
            hovertemplate=f"<b>{drv}</b> · %{{x}}<br>%{{y:.0f}} pts acumulados<extra></extra>",
        ))
        if drv in ultimo.index:
            fig.add_annotation(x=d["label"].iloc[-1], y=float(ultimo[drv]),
                               text=f" {drv}", showarrow=False, xanchor="left",
                               font=dict(color=color_map.get(drv, "#9aa0aa"), size=11))
    fig.update_layout(
        template="plotly_dark", height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(14,17,23,1)",
        font=dict(family="Roboto", color="#e6e6e6"),
        yaxis=dict(title="PUNTOS ACUMULADOS", showgrid=True,
                   gridcolor="rgba(255,255,255,0.07)", griddash="dot"),
        xaxis=dict(title="", showgrid=False),
        showlegend=False, margin=dict(l=60, r=60, t=30, b=60), hovermode="x unified",
    )
    return fig


def build_h2h_history_chart(df, drv_a, drv_b, col_a, col_b, height=460):
    """Head-to-head histórico: Δ de mejor vuelta (A − B) por GP.

    Barra hacia ABAJO = A fue más rápido (convención delta del dashboard);
    hacia arriba = B. Color de la barra = color del ganador de ese GP.
    df: columnas [label, delta_s, orden].
    """
    d = df.sort_values("orden")
    colores = [col_a if v < 0 else col_b for v in d["delta_s"]]
    fig = go.Figure(go.Bar(
        x=d["label"], y=d["delta_s"], marker_color=colores,
        text=[f"{abs(v):.2f}s" for v in d["delta_s"]], textposition="outside",
        hovertemplate="%{x}<br>Δ = %{y:+.3f}s (A − B)<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="rgba(255,255,255,.35)", line_width=1)
    fig.update_layout(
        template="plotly_dark", height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(14,17,23,1)",
        font=dict(family="Roboto", color="#e6e6e6"),
        yaxis=dict(title=f"Δ MEJOR VUELTA (s) · abajo = {drv_a} más rápido",
                   showgrid=True, gridcolor="rgba(255,255,255,0.07)", griddash="dot"),
        xaxis=dict(title="", showgrid=False),
        margin=dict(l=60, r=20, t=30, b=60), hovermode="x",
    )
    return fig
