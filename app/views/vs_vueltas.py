"""VS VUELTAS: comparador de 2 vueltas del mismo piloto."""
from app.components import plot_wide
from app.components import render_chart_guide
from app.components import render_microsector_legend
from app.components import render_summary_card
from app.components import render_theoretical_best
from app.data import get_event_sessions
from app.data import load_session_data
from f1core.charts import apply_distance_axis
from f1core.charts import build_microsector_bar
from f1core.charts import build_minisector_dominance_map
from f1core.charts import make_god_chart
from f1core.colors import get_driver_name
from f1core.colors import get_neon_color
from f1core.config import SESSION_SHORT
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
    race = ctx.get("race")
    session = ctx.get("session")
    year = ctx.get("year")
    # @UNPACK@  (generado por fix_names)

    st.markdown("### COMPARAR DOS VUELTAS DEL MISMO PILOTO")
    st.caption("Ideal para Qualy: compara una vuelta anterior con la definitiva (p. ej. primer intento de Q3 vs el último). Puedes elegir la **sesión** (Qualy o Carrera) independiente del sidebar, el piloto y las dos vueltas.")

    # Selector de sesión propio de esta pestaña (independiente del sidebar) con las
    # sesiones REALES de este GP (incluye Sprint Quali en los findes sprint).
    _ab_sessions = get_event_sessions(year, gp) or ['Qualifying', 'Race']
    _ab_disp = [SESSION_SHORT.get(s, s) for s in _ab_sessions]
    if session in _ab_sessions:
        _ab_def_i = _ab_sessions.index(session)
    elif 'Qualifying' in _ab_sessions:
        _ab_def_i = _ab_sessions.index('Qualifying')
    else:
        _ab_def_i = len(_ab_sessions) - 1
    # Evita el error de Streamlit si la sesión guardada no existe en este GP
    # (p. ej. venías de un finde sprint con "Sprint Quali" y cambias a uno normal)
    if st.session_state.get('ab_session_sel') not in _ab_disp:
        st.session_state.pop('ab_session_sel', None)
    ab_sess_label = st.radio(
        "Sesión a comparar:", _ab_disp,
        index=_ab_def_i, horizontal=True, key="ab_session_sel"
    )
    ab_session_code = _ab_sessions[_ab_disp.index(ab_sess_label)]

    if ab_session_code == session:
        ab_session_obj = race
    else:
        with st.spinner(f"Cargando datos de {ab_sess_label}…"):
            ab_session_obj = load_session_data(year, gp, ab_session_code)

    ab_valid = pd.DataFrame()
    if ab_session_obj is None:
        st.warning(f"No hay datos de {ab_sess_label} para {gp} {year}. Prueba con otra sesión.")
    else:
        ab_laps = ab_session_obj.laps
        try:
            ab_driver_opts = [ab_session_obj.get_driver(d)['Abbreviation'] for d in ab_session_obj.drivers]
        except Exception:
            ab_driver_opts = sorted(ab_laps['Driver'].dropna().unique().tolist()) if 'Driver' in ab_laps.columns else []

        if not ab_driver_opts:
            st.warning("No se encontraron pilotos en esta sesión.")
        else:
            # Evita errores de Streamlit si el piloto guardado no existe en la nueva sesión
            if st.session_state.get('ab_driver') not in ab_driver_opts:
                st.session_state.pop('ab_driver', None)
            ab_driver = st.selectbox("Piloto:", ab_driver_opts, format_func=get_driver_name, key="ab_driver")

            # Si cambia la sesión o el piloto, resetea las vueltas elegidas y la comparación
            _ab_ctx = f"{ab_session_code}|{ab_driver}"
            if st.session_state.get('_ab_ctx') != _ab_ctx:
                for _k in ('ab_lap_a', 'ab_lap_b'):
                    st.session_state.pop(_k, None)
                st.session_state['ab_compare_active'] = False
                st.session_state['_ab_ctx'] = _ab_ctx

            ab_laps_df = ab_laps.pick_driver(ab_driver)
            ab_valid = ab_laps_df[ab_laps_df['LapTime'].notna() & ab_laps_df['LapNumber'].notna()].sort_values('LapNumber')

    if len(ab_valid) < 2:
        st.info("Este piloto no tiene al menos 2 vueltas cronometradas en la sesión.")
    else:
        ab_lap_nums = ab_valid['LapNumber'].astype(int).tolist()
        ab_labels = {
            int(r['LapNumber']): f"V{int(r['LapNumber'])} — {format_time(r['LapTime'].total_seconds())}"
            for _, r in ab_valid.iterrows()
        }
        ab_sorted = ab_valid.sort_values('LapTime')
        ab_fast_n = int(ab_sorted.iloc[0]['LapNumber'])
        ab_second_n = int(ab_sorted.iloc[1]['LapNumber'])

        col_ab1, col_ab2 = st.columns(2)
        with col_ab1:
            ab_lap_a = st.selectbox(
                "Vuelta A:", ab_lap_nums,
                index=ab_lap_nums.index(ab_second_n),
                format_func=lambda n: ab_labels.get(n, str(n)),
                key="ab_lap_a"
            )
        with col_ab2:
            ab_lap_b = st.selectbox(
                "Vuelta B:", ab_lap_nums,
                index=ab_lap_nums.index(ab_fast_n),
                format_func=lambda n: ab_labels.get(n, str(n)),
                key="ab_lap_b"
            )

        if st.button("COMPARAR VUELTAS", type="primary", key="ab_btn"):
            st.session_state['ab_compare_active'] = True

        if ab_lap_a == ab_lap_b:
            st.warning("Selecciona dos vueltas distintas.")
        elif st.session_state.get('ab_compare_active', False):
            def _load_ab_tel(lap_number):
                # get_telemetry() trae X/Y además de Speed/Distance: necesario
                # para el mapa del circuito comparando las dos vueltas.
                key = f"ab_tel_{year}_{gp}_{ab_session_code}_{ab_driver}_{lap_number}"
                if key in st.session_state:
                    return st.session_state[key]
                row = ab_valid[ab_valid['LapNumber'] == lap_number].iloc[0]
                try:
                    tel = row.get_telemetry().add_distance()
                except Exception:
                    try:
                        tel = row.get_car_data().add_distance()
                    except Exception:
                        tel = None
                st.session_state[key] = tel
                return tel

            tel_a_ab = _load_ab_tel(ab_lap_a)
            tel_b_ab = _load_ab_tel(ab_lap_b)

            if tel_a_ab is None or tel_b_ab is None or tel_a_ab.empty or tel_b_ab.empty:
                st.warning("No hay telemetría disponible para alguna de las vueltas seleccionadas.")
            else:
                # La vuelta A mantiene el color original del piloto; la vuelta B va en blanco.
                c_lap_a = get_neon_color(ab_driver)
                c_lap_b = "#FFFFFF"
                lab_a, lab_b = f"V{ab_lap_a}", f"V{ab_lap_b}"

                row_a = ab_valid[ab_valid['LapNumber'] == ab_lap_a].iloc[0]
                row_b = ab_valid[ab_valid['LapNumber'] == ab_lap_b].iloc[0]
                t_a_s = float(row_a['LapTime'].total_seconds())
                t_b_s = float(row_b['LapTime'].total_seconds())
                ab_delta_total = t_b_s - t_a_s

                mc1, mc2, mc3 = st.columns(3)
                s1a_ab, s2a_ab, s3a_ab = _get_sector_times_seconds(row_a)
                s1b_ab, s2b_ab, s3b_ab = _get_sector_times_seconds(row_b)
                with mc1:
                    st.markdown(render_summary_card(
                        f"Vuelta A (V{ab_lap_a})", c_lap_a, "Tiempo", format_time(t_a_s),
                        sub_stats={"S1": _format_sector_time(s1a_ab), "S2": _format_sector_time(s2a_ab), "S3": _format_sector_time(s3a_ab)}
                    ), unsafe_allow_html=True)
                with mc2:
                    st.markdown(render_summary_card(
                        f"Vuelta B (V{ab_lap_b})", c_lap_b, "Tiempo", format_time(t_b_s),
                        sub_stats={"S1": _format_sector_time(s1b_ab), "S2": _format_sector_time(s2b_ab), "S3": _format_sector_time(s3b_ab)}
                    ), unsafe_allow_html=True)
                with mc3:
                    st.metric("Delta (B - A)", f"{ab_delta_total:+.3f}s")
                    st.caption("Negativo = la vuelta B fue más rápida.")

                st.markdown(
                    f"<div style='margin:4px 0 10px 0;font-size:13px;'>"
                    f"<span style='color:{c_lap_a};font-weight:700;'>● Vuelta A = V{ab_lap_a}</span> &nbsp;&nbsp; "
                    f"<span style='color:{c_lap_b};font-weight:700;'>● Vuelta B = V{ab_lap_b}</span></div>",
                    unsafe_allow_html=True
                )

                # Referencias del eje X estilo GP Tempo (curvas + sectores)
                try:
                    corners_ab = ab_session_obj.get_circuit_info().corners
                except Exception:
                    corners_ab = None
                try:
                    sector_cuts_ab_axis, _ = _get_sector_cut_distances(row_a, tel_a_ab)
                except Exception:
                    sector_cuts_ab_axis = None

                st.caption("**Arrastra sobre una zona** de cualquier gráfica para hacer zoom; **doble clic** para volver. Ideal para abrir las curvas donde la diferencia entre vueltas es de milésimas.")

                # Velocidad superpuesta
                fig_ab_s = go.Figure()
                for label, tel_ab, c_ab in [
                    (f"V{ab_lap_a}", tel_a_ab, c_lap_a),
                    (f"V{ab_lap_b}", tel_b_ab, c_lap_b)
                ]:
                    hover_ab = [f"<b>{label}</b><br>Vel: {v:.0f} km/h<br>Dist: {dist:.0f} m" for v, dist in zip(tel_ab['Speed'], tel_ab['Distance'])]
                    fig_ab_s.add_trace(go.Scatter(
                        x=tel_ab['Distance'], y=tel_ab['Speed'],
                        name=label, mode='lines',
                        line=dict(color=c_ab, width=2.5),
                        hoverinfo="text", hovertext=hover_ab
                    ))
                fig_ab_s = make_god_chart(fig_ab_s, f"VELOCIDAD: {get_driver_name(ab_driver)} · V{ab_lap_a} vs V{ab_lap_b}", "km/h", "Distancia (m)", 450)
                apply_distance_axis(fig_ab_s, corners_ab, sector_cuts_ab_axis)
                plot_wide(fig_ab_s)

                # Delta B vs A
                dist_ref_ab = tel_a_ab['Distance']
                time_a_ab = tel_a_ab['Time'].dt.total_seconds()
                time_b_interp = np.interp(dist_ref_ab, tel_b_ab['Distance'], tel_b_ab['Time'].dt.total_seconds())
                delta_ab = time_b_interp - time_a_ab
                fig_ab_d = go.Figure()
                fig_ab_d.add_trace(go.Scatter(
                    x=dist_ref_ab, y=delta_ab,
                    mode='lines', name=f"Δ V{ab_lap_b} vs V{ab_lap_a}",
                    line=dict(color=c_lap_b, width=2.5),
                    hovertext=[f"Dist: {dd:.0f} m<br>Δ: {v:+.3f}s" for dd, v in zip(dist_ref_ab, delta_ab)],
                    hoverinfo="text"
                ))
                fig_ab_d.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.35)", line_width=1)
                fig_ab_d = make_god_chart(fig_ab_d, f"DELTA: V{ab_lap_b} vs V{ab_lap_a}", "Segundos", "Distancia (m)", 380)
                apply_distance_axis(fig_ab_d, corners_ab, sector_cuts_ab_axis)
                plot_wide(fig_ab_d)

                ab_faster = f"V{ab_lap_b}" if ab_delta_total < 0 else f"V{ab_lap_a}"
                delta_arr = np.asarray(delta_ab)
                idx_max_gain = int(np.argmax(np.abs(np.gradient(delta_arr)))) if len(delta_arr) > 2 else 0
                render_chart_guide(
                    summary_text=(
                        f"{get_driver_name(ab_driver)}: la vuelta {ab_faster} fue más rápida por {abs(ab_delta_total):.3f}s. "
                        f"La mayor variación del delta ocurre alrededor de los {float(dist_ref_ab.iloc[idx_max_gain]):.0f} m."
                    ),
                    how_to_read=(
                        "- **Velocidad**: las dos curvas son el mismo piloto en dos vueltas → **donde una va por encima, esa vuelta pasó más rápido por ese punto**.\n"
                        "- **Delta**: **¿va por DEBAJO de 0?** → la vuelta B va ganando tiempo. **¿Por encima?** → va perdiendo (abajo = más rápido).\n"
                        "- **¿Un cambio brusco de pendiente en el delta?** → ahí, en esa curva concreta, es donde se ganó o se perdió el tiempo entre las dos vueltas.\n"
                        "- Perfecto para ver si mejoraste de una vuelta a la siguiente y **exactamente dónde**."
                    )
                )

                # ── MARCHAS / ACELERADOR / FRENO (las dos vueltas superpuestas) ──
                ab_pairs = [(lab_a, tel_a_ab, c_lap_a), (lab_b, tel_b_ab, c_lap_b)]

                if any('nGear' in t.columns for _, t, _ in ab_pairs):
                    fig_ab_g = go.Figure()
                    for label, tel_ab, c_ab in ab_pairs:
                        if 'nGear' not in tel_ab.columns:
                            continue
                        hov = [f"<b>{label}</b><br>Marcha: {g}<br>Dist: {dist:.0f} m" for g, dist in zip(tel_ab['nGear'], tel_ab['Distance'])]
                        fig_ab_g.add_trace(go.Scatter(x=tel_ab['Distance'], y=tel_ab['nGear'], name=label, mode='lines', line=dict(color=c_ab, width=2.5, shape='hv'), hoverinfo="text", hovertext=hov))
                    fig_ab_g.update_yaxes(tickmode='linear', dtick=1, range=[0, 9])
                    fig_ab_g = make_god_chart(fig_ab_g, f"MARCHAS: V{ab_lap_a} vs V{ab_lap_b}", "Gear", "Distancia (m)", 300)
                    apply_distance_axis(fig_ab_g, corners_ab, sector_cuts_ab_axis)
                    plot_wide(fig_ab_g)

                if any('Throttle' in t.columns for _, t, _ in ab_pairs):
                    fig_ab_t = go.Figure()
                    for label, tel_ab, c_ab in ab_pairs:
                        if 'Throttle' not in tel_ab.columns:
                            continue
                        hov = [f"<b>{label}</b><br>Gas: {v:.0f}%<br>Dist: {dist:.0f} m" for v, dist in zip(tel_ab['Throttle'], tel_ab['Distance'])]
                        fig_ab_t.add_trace(go.Scatter(x=tel_ab['Distance'], y=tel_ab['Throttle'], name=label, mode='lines', line=dict(color=c_ab, width=2.5), hoverinfo="text", hovertext=hov))
                    fig_ab_t.update_yaxes(range=[0, 105])
                    fig_ab_t = make_god_chart(fig_ab_t, f"ACELERADOR: V{ab_lap_a} vs V{ab_lap_b}", "%", "Distancia (m)", 300)
                    apply_distance_axis(fig_ab_t, corners_ab, sector_cuts_ab_axis)
                    plot_wide(fig_ab_t)

                if any('Brake' in t.columns for _, t, _ in ab_pairs):
                    fig_ab_b = go.Figure()
                    for label, tel_ab, c_ab in ab_pairs:
                        if 'Brake' not in tel_ab.columns:
                            continue
                        raw_brake = tel_ab['Brake']
                        if raw_brake.dtype == bool or set(raw_brake.dropna().unique()).issubset({0, 1, True, False}):
                            b_val = raw_brake.astype(float) * 100
                        elif raw_brake.max() <= 1.0:
                            b_val = raw_brake * 100
                        else:
                            b_val = raw_brake
                        hov = [f"<b>{label}</b><br>Freno: {v:.0f}%<br>Dist: {dist:.0f} m" for v, dist in zip(b_val, tel_ab['Distance'])]
                        fig_ab_b.add_trace(go.Scatter(x=tel_ab['Distance'], y=b_val, name=label, mode='lines', line=dict(color=c_ab, width=2.5), hoverinfo="text", hovertext=hov))
                    fig_ab_b.update_yaxes(range=[0, 105])
                    fig_ab_b = make_god_chart(fig_ab_b, f"FRENO: V{ab_lap_a} vs V{ab_lap_b}", "%", "Distancia (m)", 300)
                    apply_distance_axis(fig_ab_b, corners_ab, sector_cuts_ab_axis)
                    plot_wide(fig_ab_b)

                # ── MAPA estilo "dominio por mini-sector" para las 2 vueltas ──
                has_xy = all(col in tel_a_ab.columns for col in ('X', 'Y')) and all(col in tel_b_ab.columns for col in ('X', 'Y'))
                if has_xy:
                    st.markdown("### Mapa del circuito · dominio por mini-sector")
                    st.markdown(
                        f"<span style='color:{c_lap_a};font-weight:700;'>● V{ab_lap_a}</span> &nbsp; "
                        f"<span style='color:{c_lap_b};font-weight:700;'>● V{ab_lap_b}</span>",
                        unsafe_allow_html=True
                    )
                    try:
                        circuit_ab = ab_session_obj.get_circuit_info()
                    except Exception:
                        circuit_ab = None
                    fig_ab_map, ab_map_wins = build_minisector_dominance_map(
                        {lab_a: tel_a_ab, lab_b: tel_b_ab},
                        {lab_a: c_lap_a, lab_b: c_lap_b},
                        circuit=circuit_ab,
                        n_sectors=32,
                        height=560
                    )
                    st.plotly_chart(fig_ab_map, use_container_width=True)
                    if ab_map_wins:
                        st.caption(
                            f"Cada tramo se pinta con la vuelta más rápida ahí · "
                            f"Mini-sectores liderados (de 32): V{ab_lap_a} = {ab_map_wins.get(lab_a, 0)} · "
                            f"V{ab_lap_b} = {ab_map_wins.get(lab_b, 0)}. Los números son las curvas y el punto blanco es la meta."
                        )

                    st.markdown("**Micro-sectores por sector (S1/S2/S3): comparación tramo a tramo**")
                    ms_cuts_ab, _ = _get_sector_cut_distances(row_a, tel_a_ab)
                    ms_fig_ab, ms_wins_ab, ms_summary_ab = build_microsector_bar(
                        [(lab_a, tel_a_ab), (lab_b, tel_b_ab)],
                        {lab_a: c_lap_a, lab_b: c_lap_b},
                        sector_cuts=ms_cuts_ab, mini_per_sector=8
                    )
                    if ms_fig_ab is not None:
                        st.plotly_chart(ms_fig_ab, use_container_width=True, config={"displayModeBar": False})
                        render_microsector_legend()
                        st.caption(
                            f"Mini-sectores ganados: V{ab_lap_a} = {ms_wins_ab.get(lab_a, 0)} · "
                            f"V{ab_lap_b} = {ms_wins_ab.get(lab_b, 0)}. "
                            "Sirve para ver si la mejora fue en un punto concreto o repartida por toda la vuelta."
                        )
                        render_theoretical_best(ms_summary_ab, {lab_a: c_lap_a, lab_b: c_lap_b}, unit_label="vuelta")

# --- TAB 4: CARRERA ---
