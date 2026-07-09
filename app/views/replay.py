"""REPLAY: animación sincronizada de vueltas."""
from f1core.charts import _add_corner_labels
from f1core.colors import _adjust_luminance
from f1core.colors import get_driver_color
from f1core.colors import get_driver_name
from f1core.laps import get_selected_lap
from f1core.racecontrol import _has_yellow_track_status
from f1core.racecontrol import _parse_race_control_messages
from f1core.racecontrol import _parse_track_status
from f1core.racecontrol import _segments_to_distance
from f1core.timeutils import _get_sector_cut_distances
from plotly.subplots import make_subplots
import numpy as np
import plotly.graph_objects as go
import streamlit as st
# @IMPORTS@  (generado por fix_names)


def render(ctx):
    lap_mode = ctx.get("lap_mode")
    laps = ctx.get("laps")
    race = ctx.get("race")
    selected_abbr = ctx.get("selected_abbr")
    target_lap = ctx.get("target_lap")
    # @UNPACK@  (generado por fix_names)
    st.markdown("### ▶ REPLAY")
    st.caption(
        "Reproduce la vuelta de los 2 primeros pilotos seleccionados. El **mapa grande** los sincroniza por "
        "distancia (ambos en el mismo punto) para comparar telemetría; el **CLOSE-UP** de abajo es una cámara "
        "que los sigue en la **carrera real** (mismo tiempo), así ves cómo se abre/cierra el hueco de milésimas al darle Play."
    )

    if len(selected_abbr) < 1:
        st.info("Selecciona al menos un piloto para el modo REPLAY.")
    else:
        replay_drivers = [d for d in selected_abbr]  # TODOS los seleccionados
        yellow_available = _has_yellow_track_status(race)

        if "replay_speed_opt" not in st.session_state:
            st.session_state.replay_speed_opt = "1x"
        if "replay_n_frames" not in st.session_state:
            st.session_state.replay_n_frames = 450
        if "replay_tail_len" not in st.session_state:
            st.session_state.replay_tail_len = 12
        if "replay_compact_mode" not in st.session_state:
            st.session_state.replay_compact_mode = False
        if "replay_show_context" not in st.session_state:
            st.session_state.replay_show_context = True
        if "replay_show_yellow" not in st.session_state:
            st.session_state.replay_show_yellow = False
        if "replay_map_height" not in st.session_state:
            st.session_state.replay_map_height = 600
        if "replay_offset_factor" not in st.session_state:
            st.session_state.replay_offset_factor = 0.8
        speed_opt = st.session_state.replay_speed_opt
        n_frames = st.session_state.replay_n_frames
        tail_len = st.session_state.replay_tail_len
        compact_mode = st.session_state.replay_compact_mode
        show_context = st.session_state.replay_show_context
        show_yellow = st.session_state.replay_show_yellow if yellow_available else False
        map_height = st.session_state.replay_map_height
        offset_factor = st.session_state.replay_offset_factor

        # Load telemetry for chosen lap (todos los pilotos)
        replay_data = {}
        replay_laps = {}
        for d in replay_drivers:
            chosen, lap_source = get_selected_lap(laps, d, lap_mode, target_lap)
            if chosen is None:
                continue
            try:
                car = chosen.get_car_data().add_distance()
                tel = chosen.get_telemetry().add_distance()
            except Exception:
                continue
            replay_data[d] = {"car": car, "tel": tel}
            replay_laps[d] = chosen

        replay_drivers = [d for d in replay_drivers if d in replay_data]

        if len(replay_data) == 0:
            st.info("No hay datos de telemetria para REPLAY.")
        else:
            # ── Selector de piloto de REFERENCIA (delta + centro del close-up) ──
            if st.session_state.get('replay_ref') not in replay_drivers:
                st.session_state['replay_ref'] = replay_drivers[0]
            rc1, rc2 = st.columns(2)
            with rc1:
                ref = st.selectbox(
                    "Piloto de REFERENCIA (delta y close-up)", replay_drivers,
                    format_func=get_driver_name, key="replay_ref"
                )
            _rivales = [d for d in replay_drivers if d != ref]
            if _rivales:
                if st.session_state.get('replay_rival') not in _rivales:
                    st.session_state['replay_rival'] = _rivales[0]
                with rc2:
                    rival = st.selectbox(
                        "Rival del CLOSE-UP (duelo directo vs referencia)", _rivales,
                        format_func=get_driver_name, key="replay_rival"
                    )
            else:
                rival = None

            st.caption(
                "El **mapa grande** anima a **todos** los pilotos seleccionados como fantasmas sincronizados por "
                "distancia (todos en el mismo punto de la pista). El **DELTA** de abajo mide a cada uno contra la "
                "**referencia**. El **CLOSE-UP** es un duelo directo referencia vs rival en la **carrera real** "
                "(mismo tiempo), donde ves cómo se abre/cierra el hueco al darle Play."
            )

            max_dist = min([replay_data[d]["car"]["Distance"].max() for d in replay_data])
            d_grid = np.linspace(0, max_dist, n_frames)

            interp = {}
            for d, data in replay_data.items():
                car = data["car"].dropna(subset=['Distance']).sort_values('Distance')
                tel = data["tel"].dropna(subset=['Distance', 'X', 'Y']).sort_values('Distance')
                interp[d] = {
                    "x": np.interp(d_grid, tel['Distance'], tel['X']),
                    "y": np.interp(d_grid, tel['Distance'], tel['Y']),
                    "speed": np.interp(d_grid, car['Distance'], car['Speed']) if 'Speed' in car.columns else None,
                    "gear": np.interp(d_grid, car['Distance'], car['nGear']) if 'nGear' in car.columns else None
                }

            # a = referencia, b = rival (así el close-up y el delta principal reusan la lógica de 2 coches)
            a = ref
            b = rival

            # ── Tiempo acumulado por piloto (a partir de la velocidad) para delta/close-up ──
            cum_t = {}
            for d in replay_drivers:
                if interp[d]["speed"] is None:
                    cum_t[d] = None
                    continue
                sp = np.maximum(interp[d]["speed"] / 3.6, 0.1)
                ds = np.diff(d_grid)
                v = (sp[:-1] + sp[1:]) * 0.5
                t = np.zeros_like(d_grid)
                t[1:] = np.cumsum(ds / v)
                cum_t[d] = t

            # Delta de CADA piloto (≠ ref) contra la referencia, en ms
            delta_all = {}
            if cum_t.get(ref) is not None:
                for d in replay_drivers:
                    if d == ref or cum_t.get(d) is None:
                        continue
                    delta_all[d] = (cum_t[d] - cum_t[ref]) * 1000.0

            # Delta principal (referencia vs rival) para el close-up y las métricas
            delta_ms = None
            delta_max = None
            delta_max_dist = None
            show_delta = len(delta_all) > 0
            if b is not None and b in delta_all:
                delta_ms = delta_all[b]
                max_idx = int(np.argmax(np.abs(delta_ms)))
                delta_max = delta_ms[max_idx]
                delta_max_dist = d_grid[max_idx]

            # ── CLOSE-UP: duelo directo referencia (a) vs rival (b) en "carrera real" ──
            has_closeup = (b is not None) and (delta_ms is not None)
            cu = None
            CU_K = 45
            if has_closeup:
                _ts = max(float(np.ptp(interp[a]["x"])), float(np.ptp(interp[a]["y"]))) or 1.0
                xa_cu, ya_cu = interp[a]["x"], interp[a]["y"]
                t_a = cum_t[a]
                t_b = cum_t[b]
                d_b_time = np.interp(t_a, t_b, d_grid)          # distancia de B al tiempo de A
                xb_cu = np.interp(d_b_time, d_grid, interp[b]["x"])
                yb_cu = np.interp(d_b_time, d_grid, interp[b]["y"])
                cx_cu = (xa_cu + xb_cu) / 2.0
                cy_cu = (ya_cu + yb_cu) / 2.0
                sep_cu = np.hypot(xa_cu - xb_cu, ya_cu - yb_cu)
                max_sep_half = (float(np.nanmax(sep_cu)) / 2.0) if sep_cu.size else _ts * 0.03
                cu_W = max(_ts * 0.05, max_sep_half * 1.35)
                cu = {"xa": xa_cu, "ya": ya_cu, "xb": xb_cu, "yb": yb_cu,
                      "cx": cx_cu, "cy": cy_cu, "W": cu_W}

            context_segments = []
            if show_context:
                base_segments = _parse_race_control_messages(race)
                if not base_segments:
                    base_segments = _parse_track_status(race)
                if not show_yellow:
                    base_segments = [s for s in base_segments if s["type"] != "YELLOW"]
                car_ref = replay_data[a]["car"] if a in replay_data else None
                context_segments = _segments_to_distance(base_segments, car_ref)

            # Canales de telemetría
            telemetry_rows = []
            if any(interp[d]["speed"] is not None for d in replay_drivers):
                telemetry_rows.append(("speed", "SPEED", "km/h"))
            if any(interp[d]["gear"] is not None for d in replay_drivers):
                telemetry_rows.append(("gear", "GEAR", "Marcha"))
            if show_delta:
                telemetry_rows.append(("delta", "DELTA", "Delta (ms)"))

            # Métricas en el frame 0
            speed_now = interp[a]["speed"][0] if interp[a]["speed"] is not None else None
            m1, m2 = st.columns(2)
            m1.metric("Distancia actual", f"{d_grid[0]:.0f} m")
            m2.metric("Velocidad actual", f"{speed_now:.0f} km/h" if speed_now is not None else "N/D")

            if has_closeup:
                d1, d2, d3 = st.columns(3)
                d1.metric(f"Δ {b} vs {a}", f"{delta_ms[0]:+.1f} ms")
                d2.metric("Δ máximo", f"{delta_max:+.1f} ms")
                d3.metric("Distancia Δ máx", f"{delta_max_dist:.0f} m")

            st.markdown("#### Circuito + telemetría sincronizada")

            telemetry_row_height = 200 if compact_mode else 240
            map_height_adj = int(map_height * (0.85 if compact_mode else 1.0))
            closeup_height = int(map_height_adj * 0.62) if has_closeup else 0
            cu_aspect = (1000.0 / max(closeup_height, 1)) if has_closeup else 1.0
            n_tel = max(len(telemetry_rows), 1)
            total_rows = (2 if has_closeup else 1) + len(telemetry_rows)
            row_heights_px = [map_height_adj]
            if has_closeup:
                row_heights_px.append(closeup_height)
            row_heights_px += [telemetry_row_height] * n_tel
            row_total = float(sum(row_heights_px))
            row_heights = [h / row_total for h in row_heights_px]
            fig = make_subplots(
                rows=total_rows, cols=1, shared_xaxes=False,
                vertical_spacing=0.08, row_heights=row_heights
            )
            first_tel_row = 3 if has_closeup else 2

            # ── Colores por piloto (desambiguando compañeros de equipo) ──
            col = {}
            _used_cols = []
            for d in replay_drivers:
                _c = get_driver_color(d, laps)
                while _c.lower() in [x.lower() for x in _used_cols]:
                    _c = _adjust_luminance(_c, 1.35)
                col[d] = _c
                _used_cols.append(_c)
            color_a = col.get(a)
            color_b = col.get(b) if b else None

            # ── Línea central del trazado = promedio de todos los pilotos ──
            xC = np.mean(np.vstack([interp[d]["x"] for d in replay_drivers]), axis=0)
            yC = np.mean(np.vstack([interp[d]["y"] for d in replay_drivers]), axis=0)

            dx = np.gradient(xC)
            dy = np.gradient(yC)
            nx = -dy
            ny = dx
            norm = np.hypot(nx, ny)
            norm = np.where(norm > 1e-9, norm, 1.0)
            nx /= norm
            ny /= norm

            track_scale = max(float(np.ptp(xC)), float(np.ptp(yC)))
            base_offset = track_scale * 0.02
            offset_value = base_offset * float(offset_factor)

            # ── Posición de cada fantasma: repartidos por el ancho de la pista ──
            n_drv = len(replay_drivers)
            display_xy = {}
            for k, d in enumerate(replay_drivers):
                spread = (k - (n_drv - 1) / 2.0) / max((n_drv - 1) / 2.0, 0.5) if n_drv > 1 else 0.0
                off = offset_value * spread
                display_xy[d] = (interp[d]["x"] + nx * off, interp[d]["y"] + ny * off)

            # ── FONDO DEL MAPA: trazado gris + dominio por mini-sector (entre TODOS) ──
            fig.add_trace(go.Scatter(
                x=xC, y=yC, mode='lines',
                line=dict(color="#3a3a3a", width=8),
                hoverinfo='skip', showlegend=False
            ), row=1, col=1)

            replay_dom_wins = {d: 0 for d in replay_drivers}
            cum_time_replay = {}
            for d in replay_drivers:
                tel_d = replay_data[d]["tel"].dropna(subset=['Distance', 'Time']).sort_values('Distance')
                cum_time_replay[d] = np.interp(d_grid, tel_d['Distance'].values, tel_d['Time'].dt.total_seconds().values)
            n_ms_replay = 30
            bnd = np.linspace(0, len(d_grid) - 1, n_ms_replay + 1).astype(int)
            for s in range(n_ms_replay):
                i0, i1 = bnd[s], bnd[s + 1]
                seg_times = {d: cum_time_replay[d][i1] - cum_time_replay[d][i0] for d in replay_drivers}
                win_d = min(seg_times, key=seg_times.get)
                replay_dom_wins[win_d] += 1
                fig.add_trace(go.Scatter(
                    x=xC[i0:i1 + 2], y=yC[i0:i1 + 2], mode='lines',
                    line=dict(color=col[win_d], width=8),
                    hoverinfo='skip', showlegend=False
                ), row=1, col=1)

            # Curvas numeradas + línea de meta
            try:
                _circ_replay = race.get_circuit_info()
            except Exception:
                _circ_replay = None
            if _circ_replay is not None:
                try:
                    _add_corner_labels(fig, _circ_replay.corners, xC, yC, row=1, col=1)
                except Exception:
                    pass
            fig.add_trace(go.Scatter(
                x=[xC[0]], y=[yC[0]], mode='markers',
                marker=dict(size=16, color="#FFFFFF", line=dict(color="#0e1117", width=2), symbol="square"),
                hovertemplate="Meta / Salida<extra></extra>", showlegend=False
            ), row=1, col=1)

            # ── Marcadores + estelas de TODOS los pilotos (orden fijo para los frames) ──
            marker_idx = {}
            tail_idx = {}
            for d in replay_drivers:
                _hx = col[d].lstrip('#')
                _lum = (0.299 * int(_hx[0:2], 16) + 0.587 * int(_hx[2:4], 16) + 0.114 * int(_hx[4:6], 16)) / 255.0 if len(_hx) >= 6 else 0.5
                _tcolor = "#0e1117" if _lum > 0.6 else "#FFFFFF"
                marker_idx[d] = len(fig.data)
                fig.add_trace(go.Scatter(
                    x=[display_xy[d][0][0]], y=[display_xy[d][1][0]],
                    mode='markers+text', text=[d], textposition="middle center",
                    textfont=dict(color=_tcolor, size=9),
                    marker=dict(size=15, color=col[d], line=dict(width=2, color="#FFFFFF")),
                    hoverinfo='skip', showlegend=False
                ), row=1, col=1)
            for d in replay_drivers:
                tail_idx[d] = len(fig.data)
                fig.add_trace(go.Scatter(
                    x=display_xy[d][0][:1], y=display_xy[d][1][:1],
                    mode='lines', line=dict(color=col[d], width=3),
                    opacity=0.6, hoverinfo='skip', showlegend=False
                ), row=1, col=1)

            # ── CLOSE-UP (fila 2): duelo referencia (a) vs rival (b), mundo trasladado ──
            cu_track_idx = cu_marker_a_idx = cu_marker_b_idx = None
            if has_closeup:
                fig.add_shape(type="rect", xref="x2 domain", yref="y2 domain",
                              x0=0, y0=0, x1=1, y1=1, line=dict(color="#666", width=1.5),
                              fillcolor="rgba(255,255,255,0.015)", layer="below")
                _hi0 = min(n_frames, CU_K + 1)
                cu_track_idx = len(fig.data)
                fig.add_trace(go.Scatter(
                    x=cu["xa"][0:_hi0] - cu["cx"][0], y=cu["ya"][0:_hi0] - cu["cy"][0],
                    mode='lines', line=dict(color="#666", width=7),
                    hoverinfo='skip', showlegend=False
                ), row=2, col=1)
                cu_marker_a_idx = len(fig.data)
                fig.add_trace(go.Scatter(
                    x=[cu["xa"][0] - cu["cx"][0]], y=[cu["ya"][0] - cu["cy"][0]], mode='markers+text',
                    text=[a], textposition="top center", textfont=dict(color="#FFFFFF", size=12),
                    marker=dict(size=22, color=color_a, line=dict(width=2, color="#FFFFFF"), symbol="square"),
                    hoverinfo='skip', showlegend=False
                ), row=2, col=1)
                cu_marker_b_idx = len(fig.data)
                fig.add_trace(go.Scatter(
                    x=[cu["xb"][0] - cu["cx"][0]], y=[cu["yb"][0] - cu["cy"][0]], mode='markers+text',
                    text=[b], textposition="bottom center", textfont=dict(color="#FFFFFF", size=12),
                    marker=dict(size=22, color=color_b, line=dict(width=2, color="#FFFFFF"), symbol="square"),
                    hoverinfo='skip', showlegend=False
                ), row=2, col=1)

            # ── Telemetría: líneas estáticas + marcadores ──
            tel_marker_indices = {}
            delta_range = None
            if show_delta and delta_all:
                _all_abs = max([float(np.nanmax(np.abs(v))) for v in delta_all.values()] + [1.0])
                delta_range = [-_all_abs * 1.1, _all_abs * 1.1]

            cursor_indices = {}
            cursor_y_ranges = {}
            row_map = {}
            speed_range = [0, 360]
            gear_range = [1, 8]

            replay_corner_dists, replay_corner_nums = [], []
            try:
                if _circ_replay is not None:
                    for _, _c in _circ_replay.corners.iterrows():
                        replay_corner_dists.append(float(_c['Distance']))
                        replay_corner_nums.append(str(int(_c['Number'])))
            except Exception:
                pass
            replay_sector_cuts = None
            try:
                replay_sector_cuts, _ = _get_sector_cut_distances(replay_laps.get(a), replay_data[a]["tel"])
            except Exception:
                replay_sector_cuts = None

            row_idx = first_tel_row
            for key, title, y_label in telemetry_rows:
                if key == "delta":
                    for d in replay_drivers:
                        if d not in delta_all:
                            continue
                        data = delta_all[d]
                        fig.add_trace(go.Scatter(
                            x=d_grid, y=data, mode='lines',
                            line=dict(color=col[d], width=2),
                            name=f"Δ {d}",
                            hovertemplate=f"{d} vs {a}<br>Dist: %{{x:.0f}} m<br>Delta: %{{y:+.1f}} ms<extra></extra>",
                            showlegend=True
                        ), row=row_idx, col=1)
                        fig.add_trace(go.Scatter(
                            x=[d_grid[0]], y=[data[0]], mode='markers',
                            marker=dict(size=7, color=col[d], line=dict(width=1, color="#FFFFFF")),
                            hoverinfo='skip', showlegend=False
                        ), row=row_idx, col=1)
                        tel_marker_indices[(key, d, row_idx)] = len(fig.data) - 1
                    # línea base 0 (la referencia)
                    fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.35)", width=1, dash="dot"), row=row_idx, col=1)
                else:
                    for d in replay_drivers:
                        data = interp[d][key]
                        if data is None:
                            continue
                        hover_t = f"Distancia: %{{x:.0f}} m<br>{title}: %{{y:.1f}} {y_label}<extra></extra>"
                        if key == "gear":
                            hover_t = f"Distancia: %{{x:.0f}} m<br>{title}: %{{y:.0f}} {y_label}<extra></extra>"
                        fig.add_trace(go.Scatter(
                            x=d_grid, y=data, mode='lines',
                            line=dict(color=col[d], width=2),
                            name=f"{d} {title}",
                            hovertemplate=hover_t, showlegend=True
                        ), row=row_idx, col=1)
                        fig.add_trace(go.Scatter(
                            x=[d_grid[0]], y=[data[0]], mode='markers',
                            marker=dict(size=7, color=col[d], line=dict(width=1, color="#FFFFFF")),
                            hoverinfo='skip', showlegend=False
                        ), row=row_idx, col=1)
                        tel_marker_indices[(key, d, row_idx)] = len(fig.data) - 1
                if key == "speed":
                    fig.update_yaxes(title_text=y_label, row=row_idx, col=1, showgrid=True, gridcolor="#1b1b1b", range=speed_range, automargin=True, title_standoff=18)
                    cursor_y = speed_range
                elif key == "gear":
                    fig.update_yaxes(title_text=y_label, row=row_idx, col=1, showgrid=True, gridcolor="#1b1b1b", range=gear_range, automargin=True, title_standoff=18)
                    cursor_y = gear_range
                else:
                    fig.update_yaxes(title_text=y_label, row=row_idx, col=1, showgrid=True, gridcolor="#1b1b1b", range=delta_range, automargin=True, title_standoff=18)
                    cursor_y = delta_range

                fig.add_trace(go.Scatter(
                    x=[d_grid[0], d_grid[0]], y=cursor_y, mode='lines',
                    line=dict(color="rgba(255,255,255,0.35)", width=1),
                    hoverinfo='skip', showlegend=False
                ), row=row_idx, col=1)
                cursor_indices[row_idx] = len(fig.data) - 1
                cursor_y_ranges[row_idx] = cursor_y
                row_map[key] = row_idx

                for _cd in replay_corner_dists:
                    fig.add_vline(x=_cd, line=dict(color="rgba(255,255,255,0.13)", width=1, dash="dot"), row=row_idx, col=1)
                if replay_sector_cuts and len(replay_sector_cuts) >= 2:
                    for (_sc, _nxt) in zip(replay_sector_cuts[:-1], replay_sector_cuts[1:]):
                        fig.add_vline(x=float(_sc[1]), line=dict(color="rgba(255,255,255,0.42)", width=1.2), row=row_idx, col=1)
                    if row_idx == first_tel_row:
                        _lx = [float(sc[1]) for sc, nxt in zip(replay_sector_cuts[:-1], replay_sector_cuts[1:])]
                        _lt = [str(nxt[0]) for sc, nxt in zip(replay_sector_cuts[:-1], replay_sector_cuts[1:])]
                        _ytop = (cursor_y[1] if isinstance(cursor_y, (list, tuple)) else 1.0) * 0.9
                        fig.add_trace(go.Scatter(
                            x=_lx, y=[_ytop] * len(_lx), mode='text', text=_lt,
                            textfont=dict(color="#CCC", size=12, family="Roboto"),
                            textposition="middle right", hoverinfo='skip', showlegend=False
                        ), row=row_idx, col=1)

                _is_bottom = (row_idx == total_rows)
                if _is_bottom and replay_corner_dists:
                    fig.update_xaxes(tickmode='array', tickvals=replay_corner_dists, ticktext=replay_corner_nums,
                                     tickfont=dict(color="#8A8A8A", size=10), title_text=None, showgrid=False, row=row_idx, col=1)
                elif _is_bottom:
                    fig.update_xaxes(title_text=None, showgrid=False, row=row_idx, col=1)
                else:
                    fig.update_xaxes(showticklabels=False, title_text=None, showgrid=False, row=row_idx, col=1)
                row_idx += 1

            if show_context:
                status_colors = {"SC": "#FFD000", "VSC": "#FFB000", "YELLOW": "#FFE066", "RED": "#FF3B30"}
                speed_row = row_map.get("speed")
                gear_row = row_map.get("gear")
                if not context_segments:
                    st.caption("No hay datos de banderas para este evento.")
                else:
                    for seg in context_segments:
                        color = status_colors.get(seg["type"], "#888888")
                        x0 = seg["start_dist"]; x1 = seg["end_dist"]
                        if speed_row is not None:
                            fig.add_shape(type="rect", x0=x0, x1=x1, y0=speed_range[1] * 0.93, y1=speed_range[1],
                                          fillcolor=color, opacity=0.25, line_width=0, row=speed_row, col=1)
                            fig.add_shape(type="line", x0=x0, x1=x0, y0=speed_range[0], y1=speed_range[1],
                                          line=dict(color=color, width=1, dash="dot"), row=speed_row, col=1)
                            fig.add_shape(type="line", x0=x1, x1=x1, y0=speed_range[0], y1=speed_range[1],
                                          line=dict(color=color, width=1, dash="dot"), row=speed_row, col=1)
                            fig.add_trace(go.Scatter(
                                x=[(x0 + x1) / 2.0], y=[speed_range[1] * 0.965], mode='markers',
                                marker=dict(size=6, color=color),
                                hovertemplate=f"{seg['type']}<br>Distancia: {x0:.0f}-{x1:.0f} m<extra></extra>",
                                showlegend=False
                            ), row=speed_row, col=1)
                        if gear_row is not None:
                            fig.add_shape(type="line", x0=x0, x1=x0, y0=gear_range[0], y1=gear_range[1],
                                          line=dict(color=color, width=1, dash="dot"), row=gear_row, col=1)
                            fig.add_shape(type="line", x0=x1, x1=x1, y0=gear_range[0], y1=gear_range[1],
                                          line=dict(color=color, width=1, dash="dot"), row=gear_row, col=1)

            cu_label_ann = None
            if has_closeup:
                cu_label_ann = {
                    "text": f"CLOSE-UP · {a} vs {b} · carrera real (mismo tiempo)", "xref": "x2 domain", "yref": "y2 domain",
                    "x": 0.02, "y": 0.97, "xanchor": "left", "yanchor": "top", "showarrow": False,
                    "font": {"size": 12, "color": "#999"}, "bgcolor": "rgba(255,255,255,0.03)",
                    "bordercolor": "#555", "borderwidth": 1, "borderpad": 3
                }

            # ── Frames ──
            frames = []
            for i in range(n_frames):
                start = max(0, i - tail_len)
                frame_data = []
                frame_traces = []

                for d in replay_drivers:
                    frame_data.append(go.Scatter(x=[display_xy[d][0][i]], y=[display_xy[d][1][i]]))
                    frame_traces.append(marker_idx[d])
                for d in replay_drivers:
                    frame_data.append(go.Scatter(x=display_xy[d][0][start:i + 1], y=display_xy[d][1][start:i + 1]))
                    frame_traces.append(tail_idx[d])

                if has_closeup:
                    _cxi = float(cu["cx"][i]); _cyi = float(cu["cy"][i])
                    _tlo = max(0, i - CU_K); _thi = min(n_frames, i + CU_K + 1)
                    frame_data.append(go.Scatter(x=cu["xa"][_tlo:_thi] - _cxi, y=cu["ya"][_tlo:_thi] - _cyi)); frame_traces.append(cu_track_idx)
                    frame_data.append(go.Scatter(x=[cu["xa"][i] - _cxi], y=[cu["ya"][i] - _cyi])); frame_traces.append(cu_marker_a_idx)
                    frame_data.append(go.Scatter(x=[cu["xb"][i] - _cxi], y=[cu["yb"][i] - _cyi])); frame_traces.append(cu_marker_b_idx)

                for (key, d, r_idx), t_idx in tel_marker_indices.items():
                    if key == "delta":
                        data = delta_all.get(d)
                    else:
                        data = interp[d][key]
                    if data is None:
                        continue
                    frame_data.append(go.Scatter(x=[d_grid[i]], y=[data[i]]))
                    frame_traces.append(t_idx)

                for r_idx, t_idx in cursor_indices.items():
                    y_vals = cursor_y_ranges.get(r_idx, [0, 1])
                    frame_data.append(go.Scatter(x=[d_grid[i], d_grid[i]], y=y_vals))
                    frame_traces.append(t_idx)

                frame_anns = []
                if has_closeup:
                    frame_anns.append({
                        "x": 0.5, "y": 1.045, "xref": "paper", "yref": "paper", "showarrow": False,
                        "font": {"size": 13, "color": "#E6E6E6"},
                        "text": f"Δ {b} vs {a}: {delta_ms[i]:+.1f} ms  ·  Δ máx: {delta_max:+.1f} ms @ {delta_max_dist:.0f} m"
                    })
                    frame_anns.append(cu_label_ann)

                frame_layout = {"annotations": frame_anns} if frame_anns else None
                assert all(t is not None for t in frame_data)
                frames.append(go.Frame(name=str(i), data=frame_data, traces=frame_traces, layout=frame_layout))

            fig.frames = frames

            # ── Layout ──
            map_x = [xC] + [display_xy[d][0] for d in replay_drivers]
            map_y = [yC] + [display_xy[d][1] for d in replay_drivers]
            x_min = float(np.nanmin(np.concatenate(map_x)))
            x_max = float(np.nanmax(np.concatenate(map_x)))
            y_min = float(np.nanmin(np.concatenate(map_y)))
            y_max = float(np.nanmax(np.concatenate(map_y)))
            pad_x = (x_max - x_min) * 0.05 if x_max > x_min else 1
            pad_y = (y_max - y_min) * 0.05 if y_max > y_min else 1
            fig.update_xaxes(visible=False, row=1, col=1, range=[x_min - pad_x, x_max + pad_x])
            fig.update_yaxes(visible=False, row=1, col=1, scaleanchor="x", scaleratio=1, range=[y_min - pad_y, y_max + pad_y])

            if has_closeup:
                _W = float(cu["W"])
                fig.update_xaxes(visible=False, row=2, col=1, range=[-_W * cu_aspect, _W * cu_aspect])
                fig.update_yaxes(visible=False, row=2, col=1, range=[-_W, _W])

            frame_duration = 80 if speed_opt == "0.5x" else (40 if speed_opt == "1x" else 20)
            fig_height = map_height_adj + closeup_height + telemetry_row_height * max(len(telemetry_rows), 1) + 90

            base_annotations = []
            if has_closeup:
                base_annotations.append({
                    "x": 0.5, "y": 1.045, "xref": "paper", "yref": "paper", "showarrow": False,
                    "font": {"size": 13, "color": "#E6E6E6"},
                    "text": f"Δ {b} vs {a}: {delta_ms[0]:+.1f} ms  ·  Δ máx: {delta_max:+.1f} ms @ {delta_max_dist:.0f} m"
                })
                base_annotations.append(cu_label_ann)

            fig.update_layout(
                template="habib_dark",
                height=fig_height,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=True,
                margin=dict(l=40, r=20, t=96, b=40),
                font=dict(size=14),
                uirevision="replay",
                annotations=base_annotations,
                legend=dict(orientation="h", yanchor="bottom", y=1.11, xanchor="right", x=1.0, bgcolor="rgba(0,0,0,0)"),
                updatemenus=[{
                    "type": "buttons", "showactive": False, "x": 0.0, "y": 1.13,
                    "xanchor": "left", "yanchor": "top",
                    "bgcolor": "rgba(255,255,255,0.06)", "bordercolor": "rgba(255,255,255,0.25)",
                    "font": {"color": "#FFFFFF", "size": 13},
                    "buttons": [
                        {"label": "Play", "method": "animate",
                         "args": [None, {"frame": {"duration": frame_duration, "redraw": False}, "fromcurrent": True, "transition": {"duration": frame_duration, "easing": "linear"}}]},
                        {"label": "Pause", "method": "animate",
                         "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate", "transition": {"duration": 0}}]}
                    ]
                }],
                sliders=[{
                    "active": 0, "currentvalue": {"prefix": "Distancia (m): "}, "pad": {"t": 20},
                    "steps": [
                        {"label": f"{d_grid[i]:.0f}", "method": "animate", "args": [[str(i)], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}]}
                        for i in range(n_frames)
                    ]
                }]
            )

            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True, "scrollZoom": False, "doubleClick": "reset"})

            # ── Leyenda del mapa ──
            leg_map = " &nbsp; ".join(
                f"<span style='color:{col[d]};font-weight:700;'>● {d}</span>" for d in replay_drivers
            )
            if replay_dom_wins:
                _wins_txt = " · ".join(
                    f"<span style='color:{col[d]};'>{d} {replay_dom_wins.get(d, 0)}</span>"
                    for d in sorted(replay_drivers, key=lambda x: -replay_dom_wins.get(x, 0))
                )
                leg_map += f" &nbsp;·&nbsp; mini-sectores liderados (de 30): {_wins_txt}"
            st.markdown(
                f"<div style='font-size:12px;color:#aaa;margin-top:2px;'>{leg_map}. "
                "El trazado se pinta con el color del más rápido en cada mini-sector. "
                "Los <b>números</b> son las curvas y el <b>punto blanco</b> es la meta.</div>",
                unsafe_allow_html=True
            )

            st.markdown("#### Controles")
            c1, c2, c3 = st.columns(3)
            with c1:
                st.selectbox("Velocidad", ["0.5x", "1x", "2x"], key="replay_speed_opt")
                st.slider("Resolución (frames)", 300, 600, step=50, key="replay_n_frames")
            with c2:
                st.slider("Estela / cola (puntos)", 0, 25, step=2, key="replay_tail_len")
                st.slider("Altura del mapa (px)", 480, 720, step=20, key="replay_map_height")
            with c3:
                st.toggle("Modo compacto", key="replay_compact_mode")
                st.toggle("Contexto (SC/VSC/Bandera roja)", key="replay_show_context")
                if yellow_available:
                    st.toggle("Mostrar amarillas", key="replay_show_yellow")

            st.slider("Separación de fantasmas en la pista", 0.2, 2.0, step=0.1, key="replay_offset_factor",
                      help="Aparta a los fantasmas a lo ancho de la pista para que no se solapen (van sincronizados por distancia, así que sin separación quedan encimados).")

            with st.expander("ℹ ¿Qué hace cada control?"):
                st.markdown(
                    "- **Play / Pause** (arriba del mapa): inicia o pausa la animación. La barra inferior es una línea de tiempo por distancia; arrástrala para saltar a cualquier punto de la vuelta.\n"
                    "- **Piloto de REFERENCIA**: contra quién se mide el DELTA de todos y el centro del close-up.\n"
                    "- **Rival del CLOSE-UP**: el segundo coche del duelo directo en el recuadro de abajo.\n"
                    "- **Velocidad**: ritmo de reproducción (0.5x lento · 2x rápido).\n"
                    "- **Resolución (frames)**: número de pasos de la animación. Más frames = movimiento más suave pero más pesado.\n"
                    "- **Estela / cola**: cuántos puntos de rastro deja cada coche detrás (0 = sin cola).\n"
                    "- **Altura del mapa**: tamaño del circuito en pantalla.\n"
                    "- **Modo compacto**: reduce la altura de las gráficas de telemetría.\n"
                    "- **Contexto (SC/VSC/Bandera roja)**: sombrea los tramos bajo coche de seguridad, VSC o bandera roja.\n"
                    "- **Mostrar amarillas**: añade las zonas de bandera amarilla (solo si hubo).\n"
                    "- **Separación de fantasmas**: los aparta a lo ancho de la pista para verlos a todos sin que se encimen."
                )
