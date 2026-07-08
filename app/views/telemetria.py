"""TELEMETRÍA: análisis de vuelta por distancia."""
from app.components import plot_wide
from app.components import render_chart_guide
from app.components import render_clean_metric_table
from app.components import render_microsector_legend
from app.components import render_summary_card
from app.components import render_theoretical_best
import textwrap
from f1core.charts import apply_distance_axis
from f1core.charts import build_microsector_bar
from f1core.charts import make_god_chart
from f1core.colors import _adjust_luminance
from f1core.colors import get_driver_color
from f1core.colors import get_driver_name
from f1core.colors import get_neon_color
from f1core.colors import maybe_adjust_if_same
from f1core.laps import get_selected_lap
from f1core.physics import _dtw_distance
from f1core.timeutils import _describe_circuit_zone
from f1core.timeutils import _format_sector_time
from f1core.timeutils import _get_sector_cut_distances
from f1core.timeutils import _get_sector_times_seconds
from f1core.timeutils import format_time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
# @IMPORTS@  (generado por fix_names)


def render(ctx):
    gp = ctx.get("gp")
    lap_mode = ctx.get("lap_mode")
    laps = ctx.get("laps")
    race = ctx.get("race")
    selected_abbr = ctx.get("selected_abbr")
    session = ctx.get("session")
    style_map = ctx.get("style_map")
    target_lap = ctx.get("target_lap")
    year = ctx.get("year")
    # @UNPACK@  (generado por fix_names)

    st.markdown(textwrap.dedent("""### ANÁLISIS DE VUELTA"""))



    _refc, _ = st.columns([1, 3])
    with _refc:
        ref = st.selectbox("Referencia Delta:", selected_abbr, format_func=get_driver_name)
    st.caption("Las gráficas se generan solas al cargar los datos o cambiar de pilotos/vuelta — ya no hace falta ningún botón.")

    # Firma de la selección: solo se vuelve a descargar la telemetría si algo cambió
    _tel_sig = (year, gp, session, tuple(selected_abbr), lap_mode, target_lap)

    if selected_abbr:

        try:

            with st.spinner("Procesando telemetría..."):

                _tc0 = st.session_state.get('telemetry_cache')
                if _tc0 and _tc0.get('sig') == _tel_sig and _tc0.get('tel_data'):
                    # Misma selección de antes → reutilizamos sin volver a descargar nada
                    tel_data = _tc0['tel_data']; tel_xy = _tc0['tel_xy']; lap_times = _tc0['lap_times']
                else:
                    tel_data = {}
                    tel_xy = {}
                    lap_times = {}

                    for d in selected_abbr:
                        chosen, lap_source = get_selected_lap(laps, d, lap_mode, target_lap)
                        if chosen is None:
                            st.warning(f"{d}: no hay datos para la vuelta seleccionada.")
                            continue

                        try:
                            t = chosen.get_car_data().add_distance()
                        except Exception:
                            st.warning(f"{d}: telemetría no disponible en esta sesión.")
                            continue
                        t['LapTimeStr'] = format_time(chosen['LapTime'].total_seconds())
                        tel_data[d] = t
                        lap_times[d] = {
                            'seconds': float(chosen['LapTime'].total_seconds()) if pd.notna(chosen['LapTime']) else None,
                            'label': format_time(chosen['LapTime'].total_seconds()) if pd.notna(chosen['LapTime']) else "-",
                            'lap_number': int(chosen['LapNumber']) if pd.notna(chosen['LapNumber']) else None
                        }
                        try:
                            t_xy = chosen.get_telemetry().add_distance()
                            t_xy_clean = t_xy.dropna(subset=['X', 'Y', 'Distance', 'Time']).copy()
                            if not t_xy_clean.empty:
                                tel_xy[d] = t_xy_clean
                        except Exception:
                            pass

                    st.session_state['telemetry_cache'] = {
                        'tel_data': tel_data,
                        'tel_xy': tel_xy,
                        'selected_abbr': list(selected_abbr),
                        'lap_times': lap_times,
                        'sig': _tel_sig
                    }

                circuit = race.get_circuit_info()



                if ref in tel_data:

                    ref_t = tel_data[ref]

                    ref_dist = ref_t['Distance']; ref_time = ref_t['Time'].dt.total_seconds()

                    # Referencias para el eje X estilo GP Tempo (curvas + sectores)
                    corners_tel = circuit.corners if circuit is not None else None
                    try:
                        _ref_lap, _ = get_selected_lap(laps, ref, lap_mode, target_lap)
                        sector_cuts_tel, _ = _get_sector_cut_distances(_ref_lap, ref_t)
                    except Exception:
                        sector_cuts_tel = None

                    st.caption("Las gráficas van a todo el ancho. Cuando la diferencia sea mínima, **arrastra sobre la zona** para hacer zoom; **doble clic** para volver. La barra de herramientas aparece al pasar el cursor.")

                    # --- DTW: SIMILITUD DE VUELTAS RÁPIDAS (solo en modo "Vuelta Rápida") ---
                    if lap_mode == "Vuelta Rápida" and len([d for d in selected_abbr if d in tel_data]) >= 2:
                        st.markdown("**SIMILITUD DE VUELTAS · Dynamic Time Warping (DTW)**")
                        st.caption(
                            f"Compara la **forma** de la vuelta rápida de {get_driver_name(ref)} (referencia) con la de cada piloto. "
                            "El DTW alinea las dos curvas de velocidad permitiendo pequeños desfases (frenar unos metros antes o después) "
                            "y mide cuánto difieren realmente."
                        )

                        _N_DTW = 200

                        def _speed_profile(_df):
                            _d = _df.dropna(subset=['Distance', 'Speed'])
                            if _d.empty:
                                return None, None
                            _dist = _d['Distance'].to_numpy(dtype=float)
                            _spd = _d['Speed'].to_numpy(dtype=float)
                            _grid = np.linspace(float(_dist.min()), float(_dist.max()), _N_DTW)
                            return _grid, np.interp(_grid, _dist, _spd)

                        _ref_grid, _ref_prof = _speed_profile(ref_t)
                        dtw_rows = []
                        if _ref_prof is not None:
                            for d in selected_abbr:
                                if d == ref or d not in tel_data:
                                    continue
                                _g, _prof = _speed_profile(tel_data[d])
                                if _prof is None:
                                    continue
                                _cost, _path = _dtw_distance(_ref_prof, _prof)
                                if not _path:
                                    continue
                                _avg = _cost / len(_path)
                                _diffs = [abs(_ref_prof[i] - _prof[j]) for i, j in _path]
                                _imax = _path[int(np.argmax(_diffs))][0]
                                _dmax = float(_ref_grid[_imax])
                                _corner_txt = f" · máx. diferencia ~{_dmax:.0f} m"
                                if corners_tel is not None and 'Distance' in corners_tel.columns:
                                    _cd = corners_tel.dropna(subset=['Distance'])
                                    if not _cd.empty:
                                        _ic = (_cd['Distance'] - _dmax).abs().idxmin()
                                        try:
                                            _cn = int(_cd.loc[_ic, 'Number'])
                                            _corner_txt = f" · máx. diferencia en la curva {_cn} (~{_dmax:.0f} m)"
                                        except Exception:
                                            pass
                                dtw_rows.append((d, _avg, _corner_txt))

                        if dtw_rows:
                            dtw_rows.sort(key=lambda r: r[1])

                            def _sim_label(_a):
                                if _a < 3:
                                    return "casi idénticas"
                                if _a < 6:
                                    return "muy parecidas"
                                if _a < 10:
                                    return "parecidas, con diferencias"
                                return "vueltas distintas"

                            tbl_dtw = [
                                (get_driver_name(d), f"{avg:.1f} km/h · {_sim_label(avg)}{ctxt}")
                                for (d, avg, ctxt) in dtw_rows
                            ]
                            st.markdown(render_clean_metric_table(
                                tbl_dtw, col1="Piloto", col2=f"DTW vs {ref} · menor = más parecida",
                                title="Similitud de la vuelta rápida (DTW)",
                                caption="La distancia DTW es la diferencia media de velocidad (km/h) entre las dos vueltas una vez alineadas en el tiempo. Más baja = trazado más parecido al del piloto de referencia."
                            ), unsafe_allow_html=True)

                            _best = dtw_rows[0]
                            _worst = dtw_rows[-1]
                            if len(dtw_rows) >= 2:
                                _dtw_sum = (
                                    f"{get_driver_name(_best[0])} hizo la vuelta más parecida a la de {get_driver_name(ref)} "
                                    f"(DTW {_best[1]:.1f} km/h), y {get_driver_name(_worst[0])} la más distinta (DTW {_worst[1]:.1f} km/h)."
                                )
                            else:
                                _dtw_sum = (
                                    f"La vuelta de {get_driver_name(_best[0])} difiere de la de {get_driver_name(ref)} "
                                    f"en {_best[1]:.1f} km/h de media (DTW)."
                                )
                            render_chart_guide(
                                summary_text=_dtw_sum,
                                how_to_read=(
                                    "- El **DTW** compara la FORMA de dos vueltas: alinea sus curvas de velocidad permitiendo pequeños desfases (frenar 5 m antes) y mide cuánto difieren de verdad.\n"
                                    "- **¿Número bajo (km/h)?** → esa vuelta se parece mucho a la del piloto de referencia. **¿Alto?** → conducción muy distinta.\n"
                                    "- 'Máx. diferencia en la curva X' te dice **dónde** se separaron más (frenada, línea o error distinto).\n"
                                    "- Es más justo que restar la velocidad punto a punto: no castiga desfases mínimos, mide la diferencia real de conducción."
                                )
                            )
                        else:
                            st.caption("No hay suficientes vueltas rápidas para calcular el DTW.")

                        st.divider()

                    # 1. DELTA

                    fig_d = go.Figure()

                    delta_finals = {}

                    ref_ln = lap_times.get(ref, {}).get('lap_number')
                    ref_ln_txt = f" V{ref_ln}" if ref_ln is not None else ""

                    # Referencia primero, con su color y nombre (línea base en 0).
                    if ref in tel_data:
                        fig_d.add_trace(go.Scatter(
                            x=ref_dist, y=[0] * len(ref_dist),
                            name=f"{ref}{ref_ln_txt} (referencia)",
                            mode='lines',
                            line=dict(color=get_neon_color(ref), dash="dot", width=2),
                            hoverinfo='skip'
                        ))

                    for d in selected_abbr:

                        if d in tel_data and d != ref:

                            t = tel_data[d]; c = get_neon_color(d); name = get_driver_name(d)

                            ln = lap_times.get(d, {}).get('lap_number')
                            ln_txt = f" · V{ln}" if ln is not None else ""
                            leg = f"Δ {d}" + (f" (V{ln})" if ln is not None else "")

                            delta = np.interp(ref_dist, t['Distance'], t['Time'].dt.total_seconds()) - ref_time

                            delta_finals[d] = float(np.asarray(delta)[-1])

                            hover = [f"<b>{name}{ln_txt}</b><br>Delta: {v:+.3f} s<br>Dist: {dd:.0f} m" for v, dd in zip(delta, ref_dist)]

                            fig_d.add_trace(go.Scatter(x=ref_dist, y=delta, name=leg, mode='lines', line=dict(color=c, width=2.5), hoverinfo="text", hovertext=hover))

                    fig_d.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.35)", line_width=1)
                    # NO reversed: negativo=más rápido=abajo, positivo=más lento=arriba (convención F1)

                    fig_d = make_god_chart(fig_d, f"DELTA vs {get_driver_name(ref)}{ref_ln_txt}", "Segundos (− = más rápido que la referencia)", "Distancia (m)", 400)
                    apply_distance_axis(fig_d, corners_tel, sector_cuts_tel)
                    plot_wide(fig_d)

                    delta_summary = None
                    if delta_finals:
                        delta_summary = " ".join(
                            f"{d} terminó la vuelta {abs(v):.3f}s {'más rápido' if v < 0 else 'más lento'} que {get_driver_name(ref)}."
                            for d, v in delta_finals.items()
                        )
                    render_chart_guide(
                        summary_text=delta_summary,
                        how_to_read=(
                            f"- La línea plana en 0 es **{get_driver_name(ref)}** (la referencia): todo se mide contra ella.\n"
                            "- **¿La línea de un piloto va por DEBAJO de 0?** → le está SACANDO tiempo a la referencia. **¿Por encima?** → lo está perdiendo. (Aquí **abajo = más rápido**, como en la tele.)\n"
                            "- **¿La línea BAJA en un tramo?** → ahí gana tiempo (mejor curva o frenada). **¿SUBE?** → ahí lo pierde.\n"
                            "- El **valor al final** de la vuelta es la diferencia total entre ambos; los tramos **planos** = van igual de rápido."
                        )
                    )

                    # 2. VELOCIDAD (Line = signal, Ghost points = noise)

                    fig_s = go.Figure()

                    speed_metrics = {}
                    speed_min_all, speed_max_all = [], []

                    for d in selected_abbr:

                        if d in tel_data:

                            t = tel_data[d]; c = get_neon_color(d); name = get_driver_name(d)

                            ln = lap_times.get(d, {}).get('lap_number')
                            ln_txt = f" · V{ln}" if ln is not None else ""
                            leg = f"{d} (V{ln})" if ln is not None else d

                            hover = [f"<b>{name}{ln_txt}</b><br>Vel: {v:.0f} km/h<br>Dist: {dist:.0f} m" for v, dist in zip(t['Speed'], t['Distance'])]

                            # Line (signal)

                            fig_s.add_trace(go.Scatter(x=t['Distance'], y=t['Speed'], name=leg, mode='lines', line=dict(color=c, width=2.5, dash=style_map.get(d, 'solid')), hoverinfo="text", hovertext=hover))

                            sp = t['Speed'].dropna()
                            if not sp.empty:
                                speed_min_all.append(float(sp.min()))
                                speed_max_all.append(float(sp.max()))

                            # collect metrics

                            speed_metrics[get_driver_name(d)] = {

                                'Max Speed (km/h)': float(np.nanmax(t['Speed'])) if 'Speed' in t else None,

                                'Min Speed (km/h)': float(np.nanmin(t['Speed'])) if 'Speed' in t else None,

                                'Avg Throttle (%)': float(np.nanmean(t['Throttle'])) if 'Throttle' in t else None

                            }

                    # Zoom del eje Y a la banda real de velocidades: separa las
                    # líneas verticalmente para que las diferencias sean visibles.
                    if speed_min_all and speed_max_all:
                        y_lo = max(0, min(speed_min_all) - 12)
                        y_hi = max(speed_max_all) + 12
                        fig_s.update_yaxes(range=[y_lo, y_hi])

                    fig_s = make_god_chart(fig_s, "VELOCIDAD (línea sólida = 1º piloto, guiones = siguientes)", "km/h", "Distancia (m)", 520)
                    apply_distance_axis(fig_s, corners_tel, sector_cuts_tel)

                    # ── Zonas de velocidad (BAJA/ALTA) + sector más rápido del campo ──
                    try:
                        _y_hi = (max(speed_max_all) + 12) if speed_max_all else 360.0
                        _rd = ref_t.dropna(subset=['Distance', 'Speed']).sort_values('Distance')
                        _rdist = _rd['Distance'].values.astype(float)
                        _rspd = _rd['Speed'].values.astype(float)
                        if _rspd.size > 5:
                            _vmx = float(np.nanmax(_rspd))

                            def _zone(v):
                                if v < 0.45 * _vmx:
                                    return 'BAJA'
                                if v > 0.80 * _vmx:
                                    return 'ALTA'
                                return 'MEDIA'
                            _zs = [_zone(v) for v in _rspd]
                            _zlab = {'BAJA': ('BAJA VEL', '#FF6B6B'), 'ALTA': ('ALTA VEL', '#6EE7A0')}
                            _minlen = 0.05 * ((_rdist[-1] - _rdist[0]) if _rdist.size > 1 else 1.0)
                            _i0 = 0
                            for _k in range(1, len(_zs) + 1):
                                if _k == len(_zs) or _zs[_k] != _zs[_i0]:
                                    _z = _zs[_i0]
                                    if _z in _zlab and (_rdist[_k - 1] - _rdist[_i0]) >= _minlen:
                                        _txt, _cc = _zlab[_z]
                                        fig_s.add_annotation(
                                            x=(_rdist[_i0] + _rdist[_k - 1]) / 2.0, y=_y_hi, yanchor='bottom',
                                            text=_txt, showarrow=False, opacity=0.85,
                                            font=dict(color=_cc, size=9, family='Roboto'))
                                    _i0 = _k
                        if sector_cuts_tel and len(sector_cuts_tel) >= 2:
                            _sect = {}
                            for d in selected_abbr:
                                _lp, _ = get_selected_lap(laps, d, lap_mode, target_lap)
                                if _lp is not None:
                                    _sect[d] = _get_sector_times_seconds(_lp)
                            for _si, (_a, _b) in enumerate(list(zip(sector_cuts_tel[:-1], sector_cuts_tel[1:]))[:3]):
                                _cand = {d: v[_si] for d, v in _sect.items() if v and v[_si] is not None}
                                if _cand:
                                    _win = min(_cand, key=_cand.get)
                                    _mid = (float(_a[1]) + float(_b[1])) / 2.0
                                    _mg = ""
                                    if len(_cand) >= 2:
                                        _sv = sorted(_cand.values())
                                        _mg = f" +{_sv[1] - _sv[0]:.3f}"
                                    fig_s.add_annotation(
                                        x=_mid, y=_y_hi, yanchor='bottom', yshift=15,
                                        text=f"S{_si + 1}: {_win}{_mg}", showarrow=False,
                                        font=dict(color=get_neon_color(_win), size=11, family='Roboto'))
                    except Exception:
                        pass

                    plot_wide(fig_s)

                    # Resumen calculado + guía de lectura
                    speed_valid = {k: v for k, v in speed_metrics.items() if v['Max Speed (km/h)'] is not None}
                    speed_summary = None
                    if speed_valid:
                        top_name = max(speed_valid, key=lambda k: speed_valid[k]['Max Speed (km/h)'])
                        slow_name = max(speed_valid, key=lambda k: speed_valid[k]['Min Speed (km/h)'])
                        speed_summary = (
                            f"{top_name} registró la velocidad punta más alta ({speed_valid[top_name]['Max Speed (km/h)']:.0f} km/h). "
                            f"{slow_name} mantuvo la velocidad mínima más alta en curva ({speed_valid[slow_name]['Min Speed (km/h)']:.0f} km/h)."
                        )
                    render_chart_guide(
                        summary_text=speed_summary,
                        how_to_read=(
                            "- **¿La línea de un piloto va por ENCIMA de otra?** → pasa más rápido por ese punto de la pista.\n"
                            "- Los **valles** son curvas (ahí frenó) y los **picos** son finales de recta (velocidad punta).\n"
                            "- **¿Su valle es menos profundo que el del rival?** → pasó esa curva más rápido (más confianza o mejor coche ahí).\n"
                            "- Arriba, las etiquetas **ALTA/BAJA VEL** marcan las zonas rápidas y lentas, y **S1/S2/S3** dicen quién ganó cada sector.\n"
                            "- Las verticales **T1, T2…** son las curvas: te ubican dónde pasa cada cosa."
                        )
                    )

                    # Metric table under speed

                    if speed_valid:

                        tbl = []

                        for k, v in speed_valid.items():

                            thr_txt = f" · Avg Throttle: {v['Avg Throttle (%)']:.0f}%" if v['Avg Throttle (%)'] is not None else ""

                            tbl.append((k, f"Max: {v['Max Speed (km/h)']:.1f} · Min: {v['Min Speed (km/h)']:.1f}{thr_txt}"))

                        st.markdown(render_clean_metric_table(
                            tbl, col1="Piloto", col2="Velocidad (km/h) y acelerador",
                            title="Resumen numérico de velocidad",
                            caption="Max = punta en recta · Min = velocidad más baja (curva más lenta) · Avg Throttle = % medio de acelerador en la vuelta."
                        ), unsafe_allow_html=True)

                    # 3. ACELERADOR (GIGANTE)

                    fig_gas = go.Figure()

                    throttle_metrics = {}

                    for d in selected_abbr:

                        if d in tel_data:

                            t = tel_data[d]; c = get_neon_color(d); name = get_driver_name(d)

                            ln = lap_times.get(d, {}).get('lap_number')
                            ln_txt = f" · V{ln}" if ln is not None else ""
                            leg = f"{d} (V{ln})" if ln is not None else d

                            hover = [f"<b>{name}{ln_txt}</b><br>Gas: {v:.0f}%<br>Dist: {dist:.0f} m" for v, dist in zip(t['Throttle'], t['Distance'])]

                            fig_gas.add_trace(go.Scatter(x=t['Distance'], y=t['Throttle'], name=leg, mode='lines', line=dict(color=c, width=2.5), hoverinfo="text", hovertext=hover))

                            throttle_metrics[get_driver_name(d)] = float(np.nanmean(t['Throttle']))

                    fig_gas.update_yaxes(range=[0, 105])

                    fig_gas = make_god_chart(fig_gas, "ACELERADOR", "%", "Distancia", 400)
                    apply_distance_axis(fig_gas, corners_tel, sector_cuts_tel)
                    plot_wide(fig_gas)

                    render_chart_guide(
                        summary_text=" ".join(
                            f"{name}: {v:.0f}% de acelerador promedio en la vuelta."
                            for name, v in throttle_metrics.items()
                        ) if throttle_metrics else None,
                        how_to_read=(
                            "- **100%** = a fondo (rectas) · **0%** = pie fuera (frenando). Cada valle es una curva.\n"
                            "- **¿La subida tras la curva es VERTICAL?** → pisotón decidido (buena tracción y confianza).\n"
                            "- **¿La subida es inclinada o escalonada?** → aplicó el gas poco a poco (el coche desliza o le falta confianza ahí).\n"
                            "- **¿Quién vuelve a pisar ANTES a la salida de la curva?** → gana velocidad en toda la recta que viene.\n"
                            "- Más % promedio suele ir de la mano de una vuelta más rápida en circuitos veloces."
                        )
                    )

                    if throttle_metrics:

                        tbl_th = [(k, f"Avg Throttle: {v:.0f}%") for k, v in throttle_metrics.items()]

                        st.markdown(render_clean_metric_table(
                            tbl_th, col1="Piloto", col2="Acelerador medio",
                            title="Uso medio del acelerador",
                            caption="% promedio de acelerador durante toda la vuelta. Más alto = más tiempo a fondo."
                        ), unsafe_allow_html=True)

                    # 4. FRENO (GIGANTE)

                    fig_brk = go.Figure()

                    brake_metrics = {}

                    for d in selected_abbr:

                        if d in tel_data:

                            t = tel_data[d]; c = get_neon_color(d); name = get_driver_name(d)

                            # Normalizar freno: FastF1 puede devolver bool, 0-1 o 0-100
                            raw_brake = t['Brake']
                            if raw_brake.dtype == bool or set(raw_brake.dropna().unique()).issubset({0, 1, True, False}):
                                b_val = raw_brake.astype(float) * 100
                            elif raw_brake.max() <= 1.0:
                                b_val = raw_brake * 100
                            else:
                                b_val = raw_brake

                            ln = lap_times.get(d, {}).get('lap_number')
                            ln_txt = f" · V{ln}" if ln is not None else ""
                            leg = f"{d} (V{ln})" if ln is not None else d

                            hover = [f"<b>{name}{ln_txt}</b><br>Freno: {v:.0f}%<br>Dist: {dist:.0f} m" for v, dist in zip(b_val, t['Distance'])]

                            fig_brk.add_trace(go.Scatter(x=t['Distance'], y=b_val, name=leg, mode='lines', line=dict(color=c, width=2.5), hoverinfo="text", hovertext=hover))

                            brake_metrics[get_driver_name(d)] = {'Avg Brake (%)': float(np.nanmean(b_val)), 'Max Brake (%)': float(np.nanmax(b_val))}

                    fig_brk.update_yaxes(range=[0, 105])

                    fig_brk = make_god_chart(fig_brk, "FRENO", "%", "Distancia", 400)
                    apply_distance_axis(fig_brk, corners_tel, sector_cuts_tel)
                    plot_wide(fig_brk)

                    render_chart_guide(
                        summary_text=" ".join(
                            f"{name}: freno promedio {v['Avg Brake (%)']:.0f}%."
                            for name, v in brake_metrics.items()
                        ) if brake_metrics else None,
                        how_to_read=(
                            "- Cada **pico** es una frenada; **cuanto más ancho, más tiempo estuvo frenando** en esa curva.\n"
                            "- **¿El pico de un piloto empieza más a la DERECHA (más tarde)** antes de la misma curva? → frenó después = le ganó metros y tiempo ahí.\n"
                            "- Crúzalo con el acelerador: quien **frena más tarde Y vuelve a acelerar antes** ataca mejor la curva.\n"
                            "- Nota: muchos coches reportan el freno como on/off (0 o 100%), no como presión real."
                        )
                    )

                    if brake_metrics:

                        tbl_bk = [(k, f"Avg: {v['Avg Brake (%)']:.0f}% · Max: {v['Max Brake (%)']:.0f}%") for k, v in brake_metrics.items()]

                        st.markdown(render_clean_metric_table(
                            tbl_bk, col1="Piloto", col2="Freno medio / máximo",
                            title="Uso del freno",
                            caption="Avg = presión media de freno en la vuelta · Max = pico de frenada."
                        ), unsafe_allow_html=True)

                    # 5. MARCHAS

                    fig_g = go.Figure()

                    for d in selected_abbr:

                        if d in tel_data:

                            t = tel_data[d]; c = get_neon_color(d); name = get_driver_name(d)

                            ln = lap_times.get(d, {}).get('lap_number')
                            ln_txt = f" · V{ln}" if ln is not None else ""
                            leg = f"{d} (V{ln})" if ln is not None else d

                            hover = [f"<b>{name}{ln_txt}</b><br>Marcha: {g}<br>Dist: {dist:.0f} m" for g, dist in zip(t['nGear'], t['Distance'])]

                            fig_g.add_trace(go.Scatter(x=t['Distance'], y=t['nGear'], name=leg, mode='lines', line=dict(color=c, width=2.5, shape='hv'), hoverinfo="text", hovertext=hover))

                    fig_g.update_yaxes(tickmode='linear', dtick=1, range=[0, 9])

                    fig_g = make_god_chart(fig_g, "MARCHAS", "Gear", "Distancia (m)", 300)
                    apply_distance_axis(fig_g, corners_tel, sector_cuts_tel)
                    plot_wide(fig_g)

                    gear_changes = {
                        d: int((tel_data[d]['nGear'].diff() != 0).sum())
                        for d in selected_abbr if d in tel_data and 'nGear' in tel_data[d].columns
                    }
                    render_chart_guide(
                        summary_text=" ".join(
                            f"{d}: {n} cambios de marcha en la vuelta." for d, n in gear_changes.items()
                        ) if gear_changes else None,
                        how_to_read=(
                            "- Cada **escalón** es un cambio de marcha; los que bajan son reducciones al frenar.\n"
                            "- **¿Un piloto va en marcha MÁS ALTA en la misma curva?** → suele pasarla más rápido (mejor trazada) o lleva relaciones distintas.\n"
                            "- **¿Quién sube de marcha ANTES a la salida?** → está acelerando antes y gana en la recta que viene.\n"
                            "- Una recta se ve como un escalón largo y plano en la marcha más alta; muchos escalones seguidos = zona técnica."
                        )
                    )

        except Exception as e: st.error(f"Error: {e}")

    if 'telemetry_cache' in st.session_state:
        cache = st.session_state['telemetry_cache']
        cached_abbr = cache.get('selected_abbr', [])
        tel_xy = cache.get('tel_xy', {})
        lap_times = cache.get('lap_times', {})

        if cached_abbr != list(selected_abbr):
            st.info("Sincronizando el mapa con la selección actual…")
        elif len(selected_abbr) < 2:
            st.warning("Selecciona al menos 2 pilotos para el mapa de pista.")
        else:
            driver_a, driver_b = selected_abbr[0], selected_abbr[1]
            if driver_a in tel_xy and driver_b in tel_xy:
                max_distance = min(tel_xy[driver_a]['Distance'].max(), tel_xy[driver_b]['Distance'].max())
                lap_a_obj, _ = get_selected_lap(laps, driver_a, lap_mode, target_lap)
                lap_b_obj, _ = get_selected_lap(laps, driver_b, lap_mode, target_lap)
                sector_cuts = None
                sectors_approx = False
                col_ctrl, col_map = st.columns([1, 3])

                with col_ctrl:
                    st.markdown("**Guía de comparación**")
                    analysis_labels = [
                        "Tramos cortos (frenada / tracción)",
                        "Curvas completas",
                        "Sectores largos"
                    ]
                    analysis_map = {
                        "Tramos cortos (frenada / tracción)": 180.0,
                        "Curvas completas": 350.0,
                        "Sectores largos": 600.0
                    }
                    analysis_type = st.radio("Tipo de análisis", analysis_labels, index=0, key="map_analysis_type")
                    window_m = analysis_map.get(analysis_type, 180.0)

                    color_map = st.checkbox("Colorear el circuito por piloto más rápido", value=True)
                    significant_only = st.checkbox("Resaltar solo diferencias significativas (>0.05 s)", value=False)
                    show_sectors = st.checkbox("Mostrar sectores (S1/S2/S3)", value=True)

                    cursor_pct = st.slider(
                        "Explorar punto del circuito",
                        0.0,
                        100.0,
                        float(st.session_state.get('cursor_pct_global', 10.0)),
                        step=1.0,
                        format="%0.0f%%"
                    )
                    cursor_m = (cursor_pct / 100.0) * float(max_distance)
                    st.session_state['cursor_pct_global'] = cursor_pct
                    st.session_state['cursor_m_global'] = cursor_m
                    st.session_state['window_m_global'] = window_m

                    t_a = tel_xy[driver_a].dropna(subset=['Distance', 'Time']).sort_values('Distance')
                    t_b = tel_xy[driver_b].dropna(subset=['Distance', 'Time']).sort_values('Distance')
                    cursor_m = max(0.0, min(cursor_m, max_distance))
                    delta_cursor = np.interp(cursor_m, t_b['Distance'].values, t_b['Time'].dt.total_seconds().values) - np.interp(cursor_m, t_a['Distance'].values, t_a['Time'].dt.total_seconds().values)
                    winner = driver_a if delta_cursor > 0 else driver_b if delta_cursor < 0 else "Empate"
                    zone_desc = _describe_circuit_zone(cursor_pct)
                    st.caption(f"Punto aproximado: {cursor_pct:.0f}% del circuito · {zone_desc}")
                    st.caption(f"En este punto: {get_driver_name(winner) if winner != 'Empate' else 'Empate'} ({delta_cursor:+.3f} s)")

                    if show_sectors:
                        sector_cuts, sectors_approx = _get_sector_cut_distances(lap_a_obj, t_a)
                        if sectors_approx:
                            st.caption("Sectores aproximados.")

                with col_map:
                    color_a = get_driver_color(driver_a, laps)
                    color_b = get_driver_color(driver_b, laps)
                    color_a, color_b = maybe_adjust_if_same(color_a, color_b)

                    lap_a = lap_times.get(driver_a, {})
                    lap_b = lap_times.get(driver_b, {})
                    lap_a_num = lap_a.get('lap_number')
                    lap_b_num = lap_b.get('lap_number')
                    lap_a_txt = f"V{lap_a_num}" if lap_a_num is not None else "N/D"
                    lap_b_txt = f"V{lap_b_num}" if lap_b_num is not None else "N/D"
                    if lap_a_num == lap_b_num and lap_a_num is not None:
                        lap_txt = f"Vuelta analizada: {lap_a_txt}"
                    else:
                        lap_txt = f"Vuelta analizada: {driver_a} {lap_a_txt} · {driver_b} {lap_b_txt}"

                    st.markdown(
                        f"<div style='background:rgba(255,255,255,0.03);border:1px solid #333;border-radius:6px;padding:8px 10px;margin-bottom:10px;'>"
                        f"<div style='font-size:13px;color:#bbb;'>Comparación basada en: <b>{analysis_type}</b></div>"
                        f"<div style='font-size:13px;color:#bbb;'>{lap_txt}</div>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

                    st.markdown(f"#### Head to head: {get_driver_name(driver_a)} vs {get_driver_name(driver_b)}")

                    lap_a_s = lap_a.get('seconds')
                    lap_b_s = lap_b.get('seconds')
                    delta_total = (lap_a_s - lap_b_s) if lap_a_s is not None and lap_b_s is not None else None
                    if delta_total is None:
                        faster_txt = "N/D"
                    elif abs(delta_total) < 1e-6:
                        faster_txt = "Empate"
                    else:
                        faster_txt = get_driver_name(driver_a) if delta_total < 0 else get_driver_name(driver_b)

                    def _spd_stats(_d):
                        if _d in tel_xy and 'Speed' in tel_xy[_d].columns:
                            _s = tel_xy[_d]['Speed'].dropna()
                            if not _s.empty:
                                return float(_s.max()), float(_s.std())
                        return None, None

                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        s1a, s2a, s3a = _get_sector_times_seconds(lap_a_obj)
                        _vmax_a, _std_a = _spd_stats(driver_a)
                        sub_stats_a = {
                            "S1": _format_sector_time(s1a),
                            "S2": _format_sector_time(s2a),
                            "S3": _format_sector_time(s3a),
                            "V. máx": f"{_vmax_a:.0f} km/h" if _vmax_a is not None else "—",
                            "σ vel": f"{_std_a:.1f} km/h" if _std_a is not None else "—"
                        }
                        st.markdown(render_summary_card(get_driver_name(driver_a), color_a, "Tiempo vuelta", lap_a.get('label', "-"), sub_stats=sub_stats_a), unsafe_allow_html=True)
                    with m2:
                        s1b, s2b, s3b = _get_sector_times_seconds(lap_b_obj)
                        _vmax_b, _std_b = _spd_stats(driver_b)
                        sub_stats_b = {
                            "S1": _format_sector_time(s1b),
                            "S2": _format_sector_time(s2b),
                            "S3": _format_sector_time(s3b),
                            "V. máx": f"{_vmax_b:.0f} km/h" if _vmax_b is not None else "—",
                            "σ vel": f"{_std_b:.1f} km/h" if _std_b is not None else "—"
                        }
                        st.markdown(render_summary_card(get_driver_name(driver_b), color_b, "Tiempo vuelta", lap_b.get('label', "-"), sub_stats=sub_stats_b), unsafe_allow_html=True)
                    with m3:
                        delta_label = f"{delta_total:+.3f}s" if delta_total is not None else "-"
                        st.metric("Delta total (A-B)", delta_label)
                    with m4:
                        st.metric("Más rápido", faster_txt)

                    if lap_a_obj is not None and lap_b_obj is not None:
                        s1a, s2a, s3a = _get_sector_times_seconds(lap_a_obj)
                        s1b, s2b, s3b = _get_sector_times_seconds(lap_b_obj)
                        if all(v is not None for v in [s1a, s2a, s3a, s1b, s2b, s3b]):
                            d1 = s1b - s1a
                            d2 = s2b - s2a
                            d3 = s3b - s3a
                            win1 = driver_a if d1 > 0 else driver_b if d1 < 0 else "Empate"
                            win2 = driver_a if d2 > 0 else driver_b if d2 < 0 else "Empate"
                            win3 = driver_a if d3 > 0 else driver_b if d3 < 0 else "Empate"
                            st.caption(
                                f"ΔS1: {d1:+.3f}s ({win1}) · ΔS2: {d2:+.3f}s ({win2}) · ΔS3: {d3:+.3f}s ({win3})"
                            )

                    # ── MAPA MULTI-PILOTO estilo MultiViewer / GP Tempo ──
                    # Todos los seleccionados con telemetría X/Y, no solo 2.
                    map_drivers = [d for d in cached_abbr if d in tel_xy]
                    map_colors = {}
                    used_colors = []
                    for d in map_drivers:
                        col = get_driver_color(d, laps)
                        # Desambiguar compañeros de equipo con el mismo color
                        while col.lower() in [c.lower() for c in used_colors]:
                            col = _adjust_luminance(col, 1.35)
                        map_colors[d] = col
                        used_colors.append(col)

                    try:
                        circuit_map = race.get_circuit_info()
                    except Exception:
                        circuit_map = None

                    st.info("El **mapa del circuito** (dominio por mini-sector sobre el trazado) ahora está **arriba, junto al título del Gran Premio** — visible en todas las pestañas.")

                    # ── Barra de micro-sectores por sector S1/S2/S3 (TODOS) ──
                    st.markdown("**Micro-sectores por sector (S1/S2/S3): comparación de todos los pilotos**")
                    ms_cuts, _ = _get_sector_cut_distances(lap_a_obj, t_a)
                    ms_fig, ms_wins, ms_summary = build_microsector_bar(
                        [(d, tel_xy[d]) for d in map_drivers],
                        map_colors,
                        sector_cuts=ms_cuts,
                        mini_per_sector=6 if len(map_drivers) > 4 else 8
                    )
                    if ms_fig is not None:
                        st.plotly_chart(ms_fig, use_container_width=True, config={"displayModeBar": False})
                        render_microsector_legend()
                        wins_ms_txt = " · ".join(f"{d}: {ms_wins.get(d, 0)}" for d in map_drivers)
                        st.caption(f"Mini-sectores ganados (morado): {wins_ms_txt}.")
                        render_theoretical_best(ms_summary, map_colors, unit_label="vuelta")

                    render_chart_guide(
                        summary_text=None,
                        how_to_read=(
                            "- Cada cuadrito es un **mini-sector**, pintado con el color del piloto **más rápido ahí**.\n"
                            "- **Morado** = mandó en ese mini-sector · **verde** = empate (<0.02 s) · **amarillo** = fue el más lento.\n"
                            "- **¿Un piloto con muchos morados en un sector y pocos en otro?** → ahí es donde gana y donde pierde la vuelta.\n"
                            "- La 'Vuelta perfecta' junta los mejores mini-sectores de cada uno: el tiempo que saldría combinándolos.\n"
                            "- El **mapa del circuito** con el dominio pintado está arriba, junto al título del GP."
                        )
                    )
            else:
                st.info("No hay telemetría X/Y suficiente para construir el mapa.")

# --- TAB 3: VS VUELTAS (comparar dos vueltas del mismo piloto) ---
