import streamlit as st

import fastf1 as ff1

from fastf1 import plotting

from fastf1 import utils

import pandas as pd

import numpy as np

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import plotly.express as px

from scipy.signal import savgol_filter

import os

import warnings

import textwrap

import re

import html

import colorsys

# ==============================================================================
# IMPORTS DEL PROYECTO (Fase 1: f1core = lógica pura, app = UI)
# ==============================================================================
from f1core.config import (DRIVER_DB, DRIVER_COLORS, TEAM_COLORS, _TEAM_COLORS_NORM,
                           DIST_CHART_CONFIG, MICRO_PURPLE, MICRO_GREEN, MICRO_YELLOW,
                           COMPOUND_COLORS, SESSION_SHORT)
from f1core.colors import (get_driver_info, get_driver_name, get_neon_color,
                           set_selection_colors, _hex_to_rgb, _rgb_to_hex,
                           _adjust_luminance, maybe_adjust_if_same, _get_team_column,
                           _get_team_for_driver, get_driver_color,
                           _distinct_teammate_color, build_driver_colors)
from f1core.timeutils import (format_time, _to_seconds, _describe_circuit_zone,
                              _get_sector_times_seconds, _format_sector_time,
                              _get_sector_cut_distances)
from f1core.racecontrol import (_has_yellow_track_status, _parse_race_control_messages,
                                _parse_track_status, _segments_to_distance,
                                _sc_vsc_lap_ranges, _build_lap_timeline,
                                _segments_to_laps, _get_pits_from_laps,
                                _get_pits_from_session, get_pits_dataframe)
from f1core.laps import (_is_valid_lap, get_selected_lap, _filter_pace_laps,
                         _mark_outlier_laps)
from f1core.physics import (compute_gg_from_telemetry, build_gg_envelope, _dtw_distance,
                            _build_minisector_layout, _adaptive_smooth)
from f1core.charts import (make_god_chart, apply_distance_axis, build_microsector_bar,
                           _add_corner_labels, build_minisector_dominance_map,
                           build_gp_tempo_chart)
from app.theme import apply_theme
from app.components import (render_clean_metric_table, html_preserve_spaces_smart,
                            render_driver_card, show_insight, render_broadcast_title,
                            render_summary_card, render_microsector_legend,
                            render_theoretical_best, render_chart_guide,
                            render_driver_grid, render_gp_tempo_table, plot_wide)
from app.data import (get_cached_telemetry, load_session_data, get_lap_phase_stats,
                      get_schedule, get_event_sessions, get_championship_points)


# ==============================================================================

# 0. CONFIGURACIÓN Y ESTILOS

# ==============================================================================

warnings.simplefilter(action='ignore', category=FutureWarning)

warnings.simplefilter(action='ignore', category=UserWarning)

# Evitar errores de asignación en Pandas

pd.options.mode.chained_assignment = None

st.set_page_config(

    page_title="HABIB CONTROL · F1 Telemetry",

    page_icon="",

    layout="wide",

    initial_sidebar_state="expanded"

)

plotting.setup_mpl(misc_mpl_mods=False)

# CSS: ESTILO "DARK NEON PRO" (INTACTO)# 0. CONFIGURACIÓN Y ESTILOS --- BORRAR EL st.markdown ANTIGUO Y PEGAR ESTE ---

# --- BORRAR TODO EL BLOQUE st.markdown DE ESTILOS ACTUAL Y PEGAR ESTE ---

apply_theme()

# --- FIN DEL NUEVO CSS ---

# --- FIN DEL BLOQUE CSS ---


# ==============================================================================

# 1. DATOS MAESTROS

# ==============================================================================







# Colores CONSCIENTES DE LA SELECCIÓN: se rellena tras conocer selected_abbr.
# Si un equipo tiene un solo piloto seleccionado, este usa el color base del
# equipo; si hay dos, el 2º recibe un color claramente distinto.












# --- BORRAR LA FUNCIÓN make_god_chart ANTIGUA Y PEGAR ESTA ---


# Config para gráficas por distancia: zoom con arrastre y rueda, doble clic para
# resetear. Sirve para "abrir" zonas donde las diferencias son mínimas.


























# ============================================================================== 
# TRACK MAP HELPERS
# ==============================================================================

# ==============================================================================
# MICRO-SECTORES (barra estilo F1 MultiViewer)
# ==============================================================================

# Convención de la torre de tiempos: morado = el más rápido, verde = empate
# (dentro del umbral), amarillo = más lento.







# ==============================================================================
# G-G PLOT HELPERS
# ==============================================================================



# ==============================================================================
# PACE BOXPLOT HELPERS
# ==============================================================================


# ==============================================================================
# GUÍA DE LECTURA DE GRÁFICAS (resumen + desplegable)
# ==============================================================================




# ==============================================================================
# GP TEMPO: EVOLUCIÓN DE TIEMPOS POR VUELTA + TABLA
# ==============================================================================







# ==============================================================================

# 2. CARGA DE DATOS

# ==============================================================================






# Etiquetas cortas para mostrar las sesiones

# ==============================================================================

# 3. SIDEBAR

# ==============================================================================

with st.sidebar:

    st.markdown("""
<style>
@keyframes hc-pulse { 0%,100%{opacity:1;transform:scale(1);} 50%{opacity:.3;transform:scale(.8);} }
.hc-brand{ padding:4px 0 12px 0; margin:-6px 0 8px 0; border-bottom:1px solid rgba(255,255,255,.06); }
.hc-live{ display:flex; align-items:center; gap:7px; font-size:9px; letter-spacing:2.6px;
          color:#9aa0aa; font-weight:700; text-transform:uppercase; margin-bottom:9px; }
.hc-dot{ width:7px; height:7px; border-radius:50%; background:#FF2D2D; flex:0 0 auto;
         box-shadow:0 0 9px 1px rgba(255,45,45,.85); animation:hc-pulse 1.4s ease-in-out infinite; }
.hc-word{ font-family:'Arial Narrow','Inter',system-ui,sans-serif; font-weight:800;
          font-size:31px; line-height:.92; letter-spacing:.4px; white-space:nowrap; }
.hc-word .a{ color:#F3F4F6; }
.hc-word .b{ background:linear-gradient(93deg,#FF2D2D 0%,#FF7A00 52%,#FFC400 100%);
             -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; }
.hc-bar{ height:3px; width:100%; margin-top:9px; border-radius:2px;
         background:linear-gradient(90deg,#FF2D2D 0%,#FF7A00 38%,rgba(255,196,0,.15) 78%,transparent 100%); }
.hc-sub{ margin-top:8px; font-size:9.5px; letter-spacing:3.4px; color:#697079;
         font-weight:600; text-transform:uppercase; }
</style>
<div class="hc-brand">
  <div class="hc-live"><span class="hc-dot"></span>LIVE TELEMETRY</div>
  <div class="hc-word"><span class="a">HABIB</span> <span class="b">CONTROL</span></div>
  <div class="hc-bar"></div>
  <div class="hc-sub">F1 · DATA DASHBOARD</div>
</div>
""", unsafe_allow_html=True)

    year = st.selectbox("TEMPORADA", [2026, 2025, 2024, 2023, 2022], index=0)

    gps = get_schedule(year)

    # Por defecto el GP más reciente ya corrido (último de la lista filtrada)
    def_ix = gps.index("Las Vegas Grand Prix") if "Las Vegas Grand Prix" in gps else max(len(gps) - 1, 0)

    gp = st.selectbox("GRAN PREMIO", gps, index=def_ix)

    # Sesiones REALES de ESTE GP (normal vs sprint). Así aparece la Sprint Quali
    # solo en los fines de semana sprint, sin saltárnosla.

    event_sessions = get_event_sessions(year, gp)
    if not event_sessions:
        event_sessions = ['Practice 1', 'Practice 2', 'Practice 3', 'Qualifying', 'Race']

    _sess_display_opts = [SESSION_SHORT.get(s, s) for s in event_sessions]
    _def_sess_idx = event_sessions.index('Race') if 'Race' in event_sessions else len(event_sessions) - 1

    session_display = st.selectbox("SESIÓN", _sess_display_opts, index=_def_sess_idx)
    # El identificador que pasamos a FastF1 es el NOMBRE de sesión (lo acepta tal cual)
    session = event_sessions[_sess_display_opts.index(session_display)]

    

    _c_load, _c_refresh = st.columns([3, 2])
    with _c_load:
        _load_clicked = st.button("CARGAR DATOS", type="primary", use_container_width=True)
    with _c_refresh:
        _refresh_clicked = st.button(
            "Buscar nuevos", use_container_width=True,
            help="Limpia la caché y RECARGA en el acto la sesión actual desde los servidores de F1 (por si ya se corrió una sesión nueva). Te avisa cuando los datos están listos."
        )

    if _refresh_clicked:
        # Limpia los cachés de Streamlit (calendario + sesiones + telemetría) para
        # forzar una consulta FRESCA a FastF1, y RECARGA la sesión actual en el acto
        # (así el usuario no tiene que volver a pulsar CARGAR DATOS).
        st.cache_data.clear()
        st.cache_resource.clear()
        for _k in list(st.session_state.keys()):
            if _k.startswith(('tel_', 'ab_tel_', 'telemetry_cache')) or _k == 'race_data':
                del st.session_state[_k]
        with st.spinner("Buscando y cargando datos nuevos de F1…"):
            _rd = load_session_data(year, gp, session)
        st.session_state['race_data'] = _rd
        st.session_state['_refresh_result'] = 'ok' if _rd is not None else 'fail'
        st.rerun()

    if _load_clicked:

        with st.spinner("Sincronizando satélites de telemetría..."):

            st.session_state['race_data'] = load_session_data(year, gp, session)

            st.rerun()

    # Aviso de resultado tras "Buscar nuevos" (se muestra ya con la página recargada)
    _rr = st.session_state.pop('_refresh_result', None)
    if _rr == 'ok':
        try:
            st.toast("Datos nuevos listos para usar.")
        except Exception:
            pass
        st.success(f"Datos nuevos cargados y listos — {gp} · {session_display}.")
    elif _rr == 'fail':
        st.warning("Caché actualizada, pero esa sesión aún no tiene datos (quizá no se ha corrido). Prueba otra sesión o vuelve más tarde.")

    if 'race_data' not in st.session_state or st.session_state['race_data'] is None:

        st.info("Esperando datos..."); st.stop()



    race = st.session_state['race_data']

    # Badge de sesión cargada
    try:
        _ev = race.event.get('EventName', gp)
        _sess_badge = session_display
        st.markdown(
            f"<div style='background:rgba(0,200,100,0.08);border:1px solid rgba(0,200,100,0.3);"
            f"border-radius:6px;padding:6px 10px;margin-bottom:8px;font-size:12px;color:#6EE7A0;'>"
            f"<b>{_ev}</b><br>{year} · {_sess_badge}</div>",
            unsafe_allow_html=True
        )
    except Exception:
        pass

    drivers = race.drivers

    driver_opts = [race.get_driver(d)['Abbreviation'] for d in drivers]

    

    st.divider()

    st.markdown(textwrap.dedent("""### CONFIG TELEMETRÍA"""))

    # Filtro Top Pilotos

    pilot_filter = st.radio("Filtro Pilotos:", ['Manual', 'Top 3', 'Top 5', 'Top 10'], horizontal=True)

    TOP_N_MAP = {'Top 3': 3, 'Top 5': 5, 'Top 10': 10}

    if pilot_filter == 'Manual':

        st.caption("Toca los pilotos para incluir/quitar (el 1º y 2º mandan como A/B):")

        selected_abbr = render_driver_grid(driver_opts, n_cols=3)

    else:

        try:

            top_n = TOP_N_MAP.get(pilot_filter, 3)

            top_df = race.results.sort_values('Position')

            selected_abbr = top_df['Abbreviation'].head(top_n).tolist()

            # Sincroniza el grid para que al volver a Manual queden marcados
            st.session_state['grid_sel'] = list(selected_abbr)

            st.markdown(textwrap.dedent(f"""**Modo {pilot_filter} activo — seleccionando automáticamente:** {', '.join(selected_abbr)}"""))

        except Exception:

            selected_abbr = render_driver_grid(driver_opts, n_cols=3)

    if not selected_abbr:

        st.stop()

    

    lap_mode = st.radio("Modo Análisis:", ["Vuelta Rápida", "Vuelta Específica"], horizontal=True)

    target_lap = None

    if lap_mode == "Vuelta Específica":

        max_laps = int(race.laps['LapNumber'].max())

        target_lap = st.slider("Seleccionar Vuelta:", 1, max_laps, int(max_laps/2))

# ==============================================================================

# 4. PROCESAMIENTO DE DATOS

# ==============================================================================

laps = race.laps

# Colores conscientes de la selección: piloto solo de un equipo → color base;
# dos compañeros → el 2º con un color claramente distinto. Rellena el mapa global
# que consultan get_neon_color/get_driver_color en TODO el dashboard.
set_selection_colors(build_driver_colors(selected_abbr, laps))

laps_vip = laps[laps['Driver'].isin(selected_abbr)].copy()

laps_vip['Seconds'] = laps_vip['LapTime'].dt.total_seconds()

laps_vip.dropna(subset=['Seconds'], inplace=True)

# Marcar pit laps (entrada) y out-laps (salida de pits, también lentas)
laps_vip['IsPit'] = ~pd.isna(laps_vip['PitInTime'])
laps_vip['IsOutLap'] = ~pd.isna(laps_vip['PitOutTime']) if 'PitOutTime' in laps_vip.columns else False

# Marcar vueltas bajo SC/VSC para filtrado opcional en gráficas
if 'TrackStatus' in laps_vip.columns:
    laps_vip['IsScVsc'] = laps_vip['TrackStatus'].astype(str).str.contains("4|5|6", regex=True)
else:
    laps_vip['IsScVsc'] = False

# Suavizado de ritmo adaptativo: ventana proporcional al número de vueltas del piloto

laps_vip['Smooth'] = laps_vip.groupby('Driver')['Seconds'].transform(_adaptive_smooth)

laps_vip['TimeReadable'] = laps_vip['Smooth'].apply(format_time)

line_styles = ['solid', 'dash', 'dot', 'longdash']

style_map = {d: line_styles[i % len(line_styles)] for i, d in enumerate(selected_abbr)}

# ==============================================================================

# 5. DASHBOARD

# ==============================================================================

# --- BORRAR st.title(...) Y PEGAR ESTO ---

# TÍTULO ESTILO BROADCAST

_title_col, _map_col = st.columns([5, 2])
with _title_col:
    st.markdown(textwrap.dedent(render_broadcast_title(gp, year, session_display)), unsafe_allow_html=True)
    # Head-to-head COMPACTO (2 primeros pilotos) junto al mapa — visible en todas las pestañas
    if len(selected_abbr) >= 2:
        _ha, _hb = selected_abbr[0], selected_abbr[1]
        _hla, _ = get_selected_lap(laps, _ha, lap_mode, target_lap)
        _hlb, _ = get_selected_lap(laps, _hb, lap_mode, target_lap)
        if _hla is not None and _hlb is not None:
            _hta = _hla['LapTime'].total_seconds() if pd.notna(_hla['LapTime']) else None
            _htb = _hlb['LapTime'].total_seconds() if pd.notna(_hlb['LapTime']) else None
            _hca, _hcb = get_neon_color(_ha), get_neon_color(_hb)
            _s1a, _s2a, _s3a = _get_sector_times_seconds(_hla)
            _s1b, _s2b, _s3b = _get_sector_times_seconds(_hlb)
            if _hta is not None and _htb is not None:
                _dtot = _hta - _htb
                _fast = _ha if _dtot < 0 else (_hb if _dtot > 0 else None)
                _fast_html = (f"<span style='color:{get_neon_color(_fast)};font-weight:800;'>{get_driver_name(_fast)}</span>"
                              if _fast else "Empate")
                _dtot_txt = f"{_dtot:+.3f}s"
            else:
                _fast_html, _dtot_txt = "N/D", "N/D"

            def _sec_cell(sa, sb, lbl):
                if sa is None or sb is None:
                    return f"<span style='color:#666;'>{lbl} —</span>"
                _d = sb - sa
                _w = _ha if _d > 0 else (_hb if _d < 0 else None)
                _wc = get_neon_color(_w) if _w else '#888'
                _wn = _w if _w else '='
                return f"{lbl} <b style='color:{_wc};'>{_d:+.3f}</b> <span style='color:{_wc};'>{_wn}</span>"

            _sec_html = " &nbsp;·&nbsp; ".join([
                _sec_cell(_s1a, _s1b, 'S1'), _sec_cell(_s2a, _s2b, 'S2'), _sec_cell(_s3a, _s3b, 'S3')
            ])
            st.markdown(
                "<div style='display:flex;flex-wrap:wrap;gap:16px;align-items:center;background:rgba(255,255,255,.03);"
                "border:1px solid #333;border-radius:8px;padding:9px 14px;margin-top:2px;'>"
                "<div><div style='font-size:10px;letter-spacing:1.5px;color:#888;'>HEAD TO HEAD</div>"
                f"<div style='font-size:15px;font-weight:700;'><span style='color:{_hca};'>{_ha}</span> "
                f"<span style='color:#666;'>vs</span> <span style='color:{_hcb};'>{_hb}</span></div></div>"
                "<div style='border-left:1px solid #333;padding-left:16px;'>"
                "<div style='font-size:10px;letter-spacing:1.5px;color:#888;'>Δ TOTAL · MÁS RÁPIDO</div>"
                f"<div style='font-size:15px;font-weight:700;'>{_dtot_txt} · {_fast_html}</div></div>"
                "<div style='border-left:1px solid #333;padding-left:16px;font-size:12px;color:#bbb;'>"
                f"<div style='font-size:10px;letter-spacing:1.5px;color:#888;'>Δ POR SECTOR (B−A)</div>{_sec_html}</div>"
                "</div>",
                unsafe_allow_html=True
            )
with _map_col:
    # Mapa de pista (dominio por mini-sector) junto al título — visible en todas las pestañas
    _cur_sig_top = (year, gp, session, tuple(selected_abbr), lap_mode, target_lap)
    _tc_top = st.session_state.get('telemetry_cache')
    _map_xy_top = dict(_tc_top.get('tel_xy', {})) if (_tc_top and _tc_top.get('sig') == _cur_sig_top) else {}
    _map_drv_top = [d for d in selected_abbr if d in _map_xy_top]
    if len(_map_drv_top) < 2:
        # Caché aún no coincide (recién cargado / cambió la selección): calcula fresco los 2 primeros
        for _d in selected_abbr[:2]:
            if _d in _map_xy_top:
                continue
            try:
                _lp, _ = get_selected_lap(laps, _d, lap_mode, target_lap)
                if _lp is None:
                    continue
                _txy = _lp.get_telemetry().add_distance().dropna(subset=['X', 'Y', 'Distance'])
                if not _txy.empty:
                    _map_xy_top[_d] = _txy
            except Exception:
                pass
        _map_drv_top = [d for d in selected_abbr if d in _map_xy_top]

    if len(_map_drv_top) >= 2:
        _mc_top, _used_top = {}, []
        for _d in _map_drv_top:
            _c = get_driver_color(_d, laps)
            while _c.lower() in [x.lower() for x in _used_top]:
                _c = _adjust_luminance(_c, 1.35)
            _mc_top[_d] = _c
            _used_top.append(_c)
        try:
            _circ_top = race.get_circuit_info()
        except Exception:
            _circ_top = None
        _dom_top, _ = build_minisector_dominance_map(
            {_d: _map_xy_top[_d] for _d in _map_drv_top}, _mc_top,
            circuit=_circ_top, n_sectors=22, height=260
        )
        st.plotly_chart(_dom_top, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            "&nbsp;".join(f"<span style='color:{_mc_top[_d]};font-weight:700;font-size:11px;'>● {_d}</span>" for _d in _map_drv_top),
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            "<div style='height:150px;display:flex;align-items:center;justify-content:center;"
            "border:1px dashed #333;border-radius:8px;color:#666;font-size:12px;text-align:center;line-height:1.5;'>"
            "Mapa de pista<br>(dominio por mini-sector)<br><span style='font-size:10px;'>elige ≥2 pilotos</span></div>",
            unsafe_allow_html=True
        )

## --- COPIA Y PEGA ESTO REEMPLAZANDO TU BUCLE FOR ---

# --- COPIA Y PEGA ESTO REEMPLAZANDO TU BUCLE FOR ---

# Puntos del campeonato de pilotos (Ergast) para mostrarlos junto al nombre
try:
    _round_no = int(race.event.get('RoundNumber')) if pd.notna(race.event.get('RoundNumber')) else 0
except Exception:
    _round_no = 0
champ_points_map, champ_round = get_championship_points(year, _round_no) if _round_no else ({}, None)

cols = st.columns(len(selected_abbr))

for i, d in enumerate(selected_abbr):
    lap, lap_source = get_selected_lap(laps, d, lap_mode, target_lap)

    pos_str = "N/A"
    try:
        pos = race.results.loc[race.results['Abbreviation'] == d, 'Position'].values[0]
        pos_str = f"P{int(pos)}"
    except Exception:
        pos_str = "N/A"

    if lap_mode == "Vuelta Rápida":
        lap_title = "MEJOR VUELTA"
        lap_caption = "EN VUELTA"
        lap_value = int(lap['LapNumber']) if lap is not None and pd.notna(lap['LapNumber']) else "-"
    else:
        lap_title = f"VUELTA {target_lap}"
        lap_caption = "SELECCIONADA"
        lap_value = int(target_lap) if target_lap is not None else "-"

    if lap is not None and pd.notna(lap.get('LapTime', None)):
        time_str = format_time(lap['LapTime'].total_seconds())
        desc = None
    else:
        time_str = "N/D"
        desc = f"No hay datos para vuelta {target_lap}" if lap_mode == "Vuelta Específica" else "Sin datos de vuelta rápida"

    with cols[i]:
        c = get_neon_color(d)
        name = get_driver_name(d)
        _phase = get_lap_phase_stats(year, gp, session, d, lap_mode, target_lap)
        html_card = render_driver_card(
            name=name,
            pos_str=pos_str,
            time_str=time_str,
            lap_title=lap_title,
            lap_caption=lap_caption,
            lap_value=lap_value,
            color=c,
            desc=desc,
            champ_pts=champ_points_map.get(d),
            phase_stats=_phase
        )
        st.markdown(textwrap.dedent(html_card), unsafe_allow_html=True)

# --- FIN DEL BLOQUE A PEGAR ---

# --- FIN DEL BLOQUE A PEGAR ---

tabs = st.tabs(["PANORAMA", "TELEMETRÍA", "VS VUELTAS", "CARRERA", "FÍSICA", "REPLAY"])

# --- TAB 1: PANORAMA ---

with tabs[0]:

    st.markdown("### PANORAMA: Visión General de Rendimiento")

    # --- SUMMARY INSIGHT ---

    if len(selected_abbr) >= 2:

        a, b = selected_abbr[0], selected_abbr[1]

        pace_a = _filter_pace_laps(laps.pick_driver(a), filter_outliers=True)

        pace_b = _filter_pace_laps(laps.pick_driver(b), filter_outliers=True)

        if len(pace_a) >= 3 and len(pace_b) >= 3:

            med_a, med_b = float(np.median(pace_a)), float(np.median(pace_b))

            delta_med = med_a - med_b

            faster = get_driver_name(a) if delta_med < 0 else get_driver_name(b)

            slower = get_driver_name(b) if delta_med < 0 else get_driver_name(a)

            iqr_a = float(np.percentile(pace_a, 75) - np.percentile(pace_a, 25))

            iqr_b = float(np.percentile(pace_b, 75) - np.percentile(pace_b, 25))

            more_consistent = get_driver_name(a) if iqr_a < iqr_b else get_driver_name(b)

            summary_cols_pan = st.columns(3)

            with summary_cols_pan[0]:

                st.metric("Más rápido", faster)

            with summary_cols_pan[1]:

                st.metric("Ventaja", f"{abs(delta_med):.3f}s")

            with summary_cols_pan[2]:

                st.metric("Más consistente", more_consistent)

            show_insight("Resumen de Sesión",
                f"{faster} fue {abs(delta_med):.3f}s más rápido que {slower} en mediana. "
                f"{more_consistent} fue más consistente (menor dispersión IQR)."
            )

    # --- SPEED TRAP METRICS ---

    st.divider()

    st.markdown("**VELOCIDAD MÁXIMA (SPEED TRAP)**")

    sp = laps_vip.dropna(subset=['SpeedST']).copy()

    sp = sp[sp['SpeedST'] > 0]

    if not sp.empty:

        speed_cols_pan = st.columns(len(selected_abbr))

        for i, d in enumerate(selected_abbr):

            df_sp = sp[sp['Driver'] == d]['SpeedST'].dropna()

            if not df_sp.empty:

                with speed_cols_pan[i]:

                    c = get_neon_color(d)

                    st.markdown(f"<span style='color:{c};font-weight:700;'>{get_driver_name(d)}</span>", unsafe_allow_html=True)

                    st.metric("Max", f"{df_sp.max():.1f} km/h")

                    st.metric("Mediana", f"{df_sp.median():.1f} km/h")

    else:

        st.info("No hay datos de Speed Trap disponibles.")

    st.divider()

    # --- BOX PLOT (from old stats tab) ---

    st.markdown("**FILTRADO ROBUSTO DE RITMO (IQR METHOD)**")

    laps_no_pit = laps_vip[laps_vip['IsPit'] == False].copy()

    if laps_no_pit.empty:

        st.info("No hay vueltas fuera de pits para analizar.")

    else:

        cleaned_frames = []

        for d in selected_abbr:

            df_d = laps_no_pit[laps_no_pit['Driver'] == d][['LapNumber', 'Seconds', 'Driver']].dropna(subset=['Seconds'])

            if df_d.empty:

                continue

            q1 = df_d['Seconds'].quantile(0.25)

            q3 = df_d['Seconds'].quantile(0.75)

            iqr = q3 - q1

            upper = q3 + 1.5 * iqr

            df_clean = df_d[df_d['Seconds'] <= upper]

            if not df_clean.empty:

                cleaned_frames.append(df_clean)

        if not cleaned_frames:

            st.info("Después del filtrado IQR no hay datos suficientes para mostrar Box Plot.")

        else:

            laps_clean = pd.concat(cleaned_frames)

            median_times = laps_clean.groupby('Driver')['Seconds'].median().sort_values()

            pilot_order = [d for d in median_times.index if d in selected_abbr]

            # BOX PLOT

            fig_box = go.Figure()

            for driver in pilot_order:

                data = laps_clean[laps_clean['Driver'] == driver]['Seconds']

                if data.empty:

                    continue

                color = get_neon_color(driver)

                name = get_driver_name(driver)

                fig_box.add_trace(go.Box(

                    y=data, name=name, marker=dict(color=color), boxpoints='outliers',

                    boxmean='sd', jitter=0.3, pointpos=-0.5,

                    hovertemplate="<b>%{fullData.name}</b><br>Tiempo: %{y:.3f}s<extra></extra>"

                ))

            # Línea de referencia = mediana del piloto más rápido (el "líder de ritmo")
            leader_median = float(median_times.iloc[0]) if not median_times.empty else None
            leader_driver = median_times.index[0] if not median_times.empty else None
            if leader_median is not None:
                fig_box.add_hline(
                    y=leader_median, line_dash="dot", line_color="rgba(0,242,255,0.55)", line_width=1.5,
                    annotation_text=f"Ritmo líder · {get_driver_name(leader_driver)}",
                    annotation_position="top left",
                    annotation_font_color="#00f2ff", annotation_font_size=11
                )

            fig_box = make_god_chart(fig_box, "DISTRIBUCIÓN DE RITMO (MEDIANA DE CARRERA)", "Tiempo de vuelta (s)", "Piloto", height=600)
            fig_box.update_yaxes(autorange="reversed")  # más rápido arriba (convención)

            st.plotly_chart(fig_box, use_container_width=True)

            # Resumen calculado: líder, gap al 2º y quién fue más regular (menor IQR)
            box_summary = None
            if not median_times.empty:
                iqr_map = {}
                for _d in pilot_order:
                    _g = laps_clean[laps_clean['Driver'] == _d]['Seconds'].dropna()
                    if len(_g) >= 2:
                        iqr_map[_d] = float(_g.quantile(0.75) - _g.quantile(0.25))
                box_fast = median_times.index[0]
                parts = [f"{get_driver_name(box_fast)} tiene el mejor ritmo mediano ({format_time(leader_median)})."]
                if len(median_times) > 1:
                    parts.append(f"El 2º ({get_driver_name(median_times.index[1])}) está a +{float(median_times.iloc[1] - leader_median):.3f}s/vuelta.")
                if iqr_map:
                    most_reg = min(iqr_map, key=iqr_map.get)
                    parts.append(f"El más regular fue {get_driver_name(most_reg)} (dispersión IQR de solo {iqr_map[most_reg]:.3f}s entre sus vueltas).")
                box_summary = " ".join(parts)
            render_chart_guide(
                summary_text=box_summary,
                how_to_read=(
                    "- **¿La caja de un piloto está más ARRIBA que las demás?** → tiene mejor ritmo (eje invertido: arriba = más rápido).\n"
                    "- **¿Su caja es CORTA (bajita)?** → es muy regular. **¿Es ALTA?** → su ritmo baila mucho de vuelta a vuelta.\n"
                    "- La **raya del centro** de la caja es su ritmo típico; la **línea cian punteada** es el ritmo del líder → mira a cuánto queda cada uno de ella.\n"
                    "- Rápido y regular NO son lo mismo: un piloto puede tener la caja arriba (rápido) pero alta (irregular).\n"
                    "- Los **puntos sueltos** por debajo son vueltas atípicas (tráfico, error); solo se usan vueltas limpias, sin pits ni Safety Car."
                )
            )

            # Estadísticas numéricas enriquecidas (por piloto)

            st.markdown("**RESUMEN DE RITMO (vueltas limpias por piloto)**")
            st.caption("Ordenado del más rápido al más lento por mediana. **Gap** = diferencia de ritmo mediano vs el líder · **IQR** = rango donde cae el 50% central de sus vueltas (dispersión) · **σ** = desviación típica.")

            cards_iqr = ['<div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:8px;">']

            for d in pilot_order:

                grp = laps_clean[laps_clean['Driver'] == d]['Seconds'].dropna()

                if grp.empty:
                    continue

                med = float(grp.median())
                std = float(grp.std(ddof=1)) if len(grp) >= 2 else 0.0
                iqr_v = float(grp.quantile(0.75) - grp.quantile(0.25)) if len(grp) >= 2 else 0.0
                best = float(grp.min())
                gap = (med - leader_median) if leader_median is not None else 0.0
                gap_txt = "Líder" if abs(gap) < 1e-6 else f"+{gap:.3f}s"

                sub_stats = {
                    'Gap vs líder': gap_txt,
                    'Mejor vuelta': format_time(best),
                    'Dispersión (IQR)': f'{iqr_v:.3f} s',
                    'Desv. típica (σ)': f'{std:.3f} s',
                    'Vueltas usadas': str(int(grp.count())),
                }

                card = render_summary_card(get_driver_name(d), get_neon_color(d), "Ritmo mediano", format_time(med), sub_stats)
                cards_iqr.append(card)

            cards_iqr.append('</div>')
            st.markdown(''.join(str(c) for c in cards_iqr), unsafe_allow_html=True)

            # --- CONSISTENCIA (Coeficiente de Variación) ---

            st.divider()

            st.markdown("**CONSISTENCIA (Coeficiente de Variación)**")

            st.caption(
                "El **CV** normaliza la variación de las vueltas por su ritmo: **CV = σ / mediana × 100**. "
                "Así puedes comparar la regularidad de pilotos con ritmos distintos en igualdad de condiciones "
                "(un σ de 0.3s pesa más en una vuelta corta que en una larga). Menor CV = más regular."
            )

            cv_rows = []

            for d in pilot_order:

                grp = laps_clean[laps_clean['Driver'] == d]['Seconds'].dropna()

                if len(grp) < 3:

                    continue

                med = float(grp.median())

                std = float(grp.std(ddof=1))

                cv = (std / med * 100) if med > 0 else None

                iqr_v = float(grp.quantile(0.75) - grp.quantile(0.25))

                cv_rows.append({'driver': d, 'name': get_driver_name(d), 'cv': cv, 'iqr': iqr_v, 'median': med, 'n': int(grp.count())})

            if cv_rows:

                cv_rows.sort(key=lambda x: x['cv'] if x['cv'] is not None else 999)

                valid_cv = [r['cv'] for r in cv_rows if r['cv'] is not None]
                max_cv = max(valid_cv) if valid_cv else 1.0

                def _cv_bucket(cv_v):
                    if cv_v is None:
                        return '#555', 'N/D'
                    if cv_v < 0.5:
                        return '#27AE60', '● Excelente'
                    if cv_v < 1.0:
                        return '#F39C12', '● Estable'
                    return '#E74C3C', '● Variable'

                cv_html = '<div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:8px;">'

                for row in cv_rows:

                    cv_v = row['cv']
                    bar_color, status = _cv_bucket(cv_v)
                    driver_color = get_neon_color(row['driver'])
                    bar_pct = (cv_v / max_cv * 100.0) if (cv_v is not None and max_cv > 0) else 0.0

                    cv_html += (
                        f'<div style="flex:1 1 180px;min-width:160px;background:rgba(255,255,255,0.02);'
                        f'border-radius:8px;border-left:6px solid {driver_color};padding:10px;">'
                        f'<div style="font-weight:700;color:{driver_color};font-size:13px;">{html.escape(row["name"])}</div>'
                        f'<div style="font-size:22px;font-weight:700;color:#fff;margin-top:4px;">'
                        f'{cv_v:.3f}%</div>'
                        f'<div style="font-size:11px;color:{bar_color};margin-top:2px;">{status}</div>'
                        f'<div style="height:6px;background:rgba(255,255,255,0.08);border-radius:3px;margin-top:6px;">'
                        f'<div style="height:6px;width:{bar_pct:.0f}%;background:{bar_color};border-radius:3px;"></div></div>'
                        f'<div style="font-size:11px;color:#999;margin-top:5px;">'
                        f'σ: {row["cv"]/100.0*row["median"]:.3f}s · IQR: {row["iqr"]:.3f}s · {row["n"]} vueltas</div>'
                        f'</div>'
                    )

                cv_html += '</div>'

                st.markdown(cv_html, unsafe_allow_html=True)

                # Resumen calculado: más y menos regular
                cv_summary = None
                if len(cv_rows) >= 1:
                    best_cv = cv_rows[0]
                    worst_cv = cv_rows[-1]
                    if len(cv_rows) >= 2 and best_cv['cv'] is not None and worst_cv['cv'] is not None:
                        cv_summary = (
                            f"{best_cv['name']} fue el más regular (CV {best_cv['cv']:.3f}%), y {worst_cv['name']} el que más varió "
                            f"(CV {worst_cv['cv']:.3f}%). Ojo: ritmo y consistencia son distintos — el más rápido no siempre es el más regular."
                        )
                    elif best_cv['cv'] is not None:
                        cv_summary = f"{best_cv['name']} fue el más regular con un CV de {best_cv['cv']:.3f}%."
                render_chart_guide(
                    summary_text=cv_summary,
                    how_to_read=(
                        "- **¿Un piloto tiene el CV más BAJO?** → sus vueltas se parecen mucho entre sí (muy regular). **¿CV alto?** → ritmo irregular (errores, tráfico, gestión de goma).\n"
                        "- **Barra corta = más consistente** (cada barra se compara con el peor de la selección).\n"
                        "- Regla rápida en carrera: **< 0.5%** excelente · **0.5–1%** estable · **> 1%** variable.\n"
                        "- Es normal que el CV suba a lo largo de la carrera (combustible + desgaste). Se calcula solo con vueltas limpias, así que no lo ensucian los pits ni el Safety Car."
                    )
                )

    st.divider()

    # --- EVOLUCIÓN DE TIEMPOS POR VUELTA (RITMO DE CARRERA) — debajo de Distribución de ritmo ---

    st.markdown("**EVOLUCIÓN DE TIEMPOS POR VUELTA (RITMO DE CARRERA)**")
    st.caption("Justo debajo de la Distribución de ritmo: primero ves el ritmo puro y la consistencia (boxplot + tarjetas), y aquí la 'película' cronológica que lo explica — pits, errores, tráfico y degradación del neumático.")

    if not laps_vip.empty and laps_vip['Seconds'].notna().any():

        fig_gpt_pan = build_gp_tempo_chart(
            laps_vip, selected_abbr,
            show_outliers=st.session_state.get('pan_gpt_outliers', True)
        )
        st.plotly_chart(fig_gpt_pan, use_container_width=True)
        st.toggle("Mostrar vueltas atípicas (pits, SC, tráfico)", value=True, key="pan_gpt_outliers")

        gpt_parts_pan = []
        for d in selected_abbr:
            dfd = laps_vip[laps_vip['Driver'] == d]
            secs_d = dfd['Seconds'].dropna()
            if secs_d.empty:
                continue
            best_idx = secs_d.idxmin()
            best_lap_n = int(dfd.loc[best_idx, 'LapNumber'])
            clean_d = dfd[~_mark_outlier_laps(dfd)]['Seconds'].dropna()
            med_txt = format_time(float(clean_d.median())) if not clean_d.empty else "N/D"
            gpt_parts_pan.append(
                f"{d}: mejor vuelta {format_time(float(secs_d.min()))} (V{best_lap_n}), mediana limpia {med_txt}."
            )
        render_chart_guide(
            summary_text=" ".join(gpt_parts_pan) if gpt_parts_pan else None,
            how_to_read=(
                "- **¿La línea de un piloto va más ABAJO?** → hizo esa vuelta más rápido (eje Y: abajo = mejor tiempo).\n"
                "- El **color del punto** es el compuesto (rojo=blando, amarillo=medio, blanco=duro): así comparas ritmos con la misma goma.\n"
                "- **¿Un pico hacia arriba?** → vuelta lenta: parada en pits, Safety Car o tráfico. Apaga 'Mostrar vueltas atípicas' para quitarlos.\n"
                "- **¿La línea sube poco a poco dentro de un stint?** → el neumático se está degradando.\n"
                "- Los **cruces** entre líneas te dicen quién apretó o aflojó el ritmo en ese punto de la carrera."
            )
        )
    else:
        st.info("No hay tiempos de vuelta suficientes para mostrar la evolución.")

    # ── CLASIFICACIÓN Q1/Q2/Q3 (solo en sesiones de qualifying) ──
    if session in ('Qualifying', 'Sprint Qualifying', 'Sprint Shootout'):
        st.divider()
        st.markdown("**CLASIFICACIÓN · Q1 / Q2 / Q3, gap a la pole y eliminados**")
        st.caption("Los tres cortes de la qualy: en qué segmento cayó cada piloto, sus tiempos y a cuánto quedó de la pole.")
        try:
            _qres = race.results.dropna(subset=['Position']).sort_values('Position')

            def _qsec(v):
                return v.total_seconds() if (v is not None and pd.notna(v) and hasattr(v, 'total_seconds')) else None

            _pole = None
            for _, r in _qres.iterrows():
                _b = next((q for q in [_qsec(r.get('Q3')), _qsec(r.get('Q2')), _qsec(r.get('Q1'))] if q is not None), None)
                if _b is not None:
                    _pole = _b
                    break
            _rows_q = ""
            for _, r in _qres.iterrows():
                code = r['Abbreviation']; pos = int(r['Position'])
                q1, q2, q3 = _qsec(r.get('Q1')), _qsec(r.get('Q2')), _qsec(r.get('Q3'))
                _best = next((q for q in [q3, q2, q1] if q is not None), None)
                _gap = (_best - _pole) if (_best is not None and _pole is not None) else None
                col = get_driver_color(code, race.laps)
                if q3 is not None:
                    seg, segc = "Q3", "#B026FF"
                elif q2 is not None:
                    seg, segc = "Elim. Q2", "#F2C94C"
                else:
                    seg, segc = "Elim. Q1", "#FF6B6B"
                gap_txt = "POLE" if pos == 1 else (f"+{_gap:.3f}" if _gap is not None else "—")
                _rows_q += (
                    f"<tr>"
                    f"<td style='padding:6px 10px;color:#888;'>{pos}</td>"
                    f"<td style='padding:6px 10px;font-weight:700;color:{col};'>{code}</td>"
                    f"<td style='padding:6px 10px;text-align:right;font-variant-numeric:tabular-nums;color:#bbb;'>{format_time(q1) if q1 is not None else '—'}</td>"
                    f"<td style='padding:6px 10px;text-align:right;font-variant-numeric:tabular-nums;color:#bbb;'>{format_time(q2) if q2 is not None else '—'}</td>"
                    f"<td style='padding:6px 10px;text-align:right;font-variant-numeric:tabular-nums;color:#fff;font-weight:600;'>{format_time(q3) if q3 is not None else '—'}</td>"
                    f"<td style='padding:6px 10px;text-align:right;color:#bbb;font-variant-numeric:tabular-nums;'>{gap_txt}</td>"
                    f"<td style='padding:6px 10px;color:{segc};font-weight:600;'>{seg}</td>"
                    f"</tr>"
                )
            st.markdown(
                "<table style='width:100%;border-collapse:collapse;'>"
                "<thead><tr style='color:#888;font-size:12px;text-align:left;'>"
                "<th style='padding:6px 10px;'>Pos</th><th style='padding:6px 10px;'>Piloto</th>"
                "<th style='padding:6px 10px;text-align:right;'>Q1</th><th style='padding:6px 10px;text-align:right;'>Q2</th>"
                "<th style='padding:6px 10px;text-align:right;'>Q3</th><th style='padding:6px 10px;text-align:right;'>Gap pole</th>"
                "<th style='padding:6px 10px;'>Corte</th></tr></thead>"
                f"<tbody>{_rows_q}</tbody></table>",
                unsafe_allow_html=True
            )
            render_chart_guide(
                summary_text=None,
                how_to_read=(
                    "- **¿Fila morada?** → llegó a Q3 (top 10). **¿Amarilla?** → cayó en Q2. **¿Roja?** → cayó en Q1.\n"
                    "- Los cortes: **Q1** elimina del 16º al 20º · **Q2** del 11º al 15º · **Q3** decide el top 10 y la pole.\n"
                    "- El **Gap pole** te dice a cuánto quedó cada uno del más rápido (P1 = POLE).\n"
                    "- **¿Lento en Q1/Q2 pero rápido en Q3?** → guardó gomas o dio el golpe al final, cuando de verdad contaba."
                )
            )
        except Exception as _e:
            st.info(f"No se pudo construir la clasificación: {_e}")

    # ── MEJORES SECTORES DEL CAMPO + vuelta ideal de la sesión ──
    st.divider()
    st.markdown("**MEJORES SECTORES DEL CAMPO · vuelta ideal de la sesión**")
    st.caption("El mejor tiempo de cada sector de cada piloto; en morado el más rápido de todo el campo. Abajo, la vuelta teórica ideal juntando los tres mejores sectores de la sesión.")
    try:
        _ls = race.laps
        _have = [(lbl, c) for lbl, c in [('S1', 'Sector1Time'), ('S2', 'Sector2Time'), ('S3', 'Sector3Time')] if c in _ls.columns]
        if not _have:
            st.info("No hay tiempos de sector para esta sesión.")
        else:
            _best_per, _overall = {}, {}
            for lbl, c in _have:
                bs = _ls.dropna(subset=[c]).groupby('Driver')[c].min()
                for drv, val in bs.items():
                    _best_per.setdefault(drv, {})[lbl] = val.total_seconds()
                if not bs.empty:
                    _overall[lbl] = (bs.min().total_seconds(), bs.idxmin())
            _drv_bs = [d for d in selected_abbr if d in _best_per] or list(_best_per.keys())

            def _theo(d):
                s = _best_per[d]
                vals = [s.get(lbl) for lbl, _ in _have]
                return sum(vals) if all(v is not None for v in vals) else 9e9

            _drv_bs = sorted(_drv_bs, key=_theo)
            _rows_bs = ""
            for d in _drv_bs:
                s = _best_per[d]; col = get_neon_color(d); cells = ""
                for lbl, _ in _have:
                    v = s.get(lbl)
                    _purple = (_overall.get(lbl, (None, None))[1] == d)
                    cells += (f"<td style='padding:6px 10px;text-align:right;font-variant-numeric:tabular-nums;"
                              f"color:{'#B026FF' if _purple else '#ddd'};font-weight:{'700' if _purple else '400'};'>"
                              f"{format_time(v) if v is not None else '—'}</td>")
                _t = _theo(d)
                cells += f"<td style='padding:6px 10px;text-align:right;color:#fff;font-weight:600;'>{format_time(_t) if _t < 9e8 else '—'}</td>"
                _rows_bs += f"<tr><td style='padding:6px 10px;font-weight:700;color:{col};'>{d}</td>{cells}</tr>"
            _heads = "".join(f"<th style='padding:6px 10px;text-align:right;'>{lbl}</th>" for lbl, _ in _have)
            st.markdown(
                "<table style='width:100%;border-collapse:collapse;'>"
                f"<thead><tr style='color:#888;font-size:12px;'><th style='padding:6px 10px;text-align:left;'>Piloto</th>{_heads}"
                "<th style='padding:6px 10px;text-align:right;'>Vuelta ideal</th></tr></thead>"
                f"<tbody>{_rows_bs}</tbody></table>",
                unsafe_allow_html=True
            )
            if all(lbl in _overall for lbl, _ in _have):
                _field_ideal = sum(_overall[lbl][0] for lbl, _ in _have)
                _parts = " · ".join(f"{lbl}: {_overall[lbl][1]} {format_time(_overall[lbl][0])}" for lbl, _ in _have)
                st.markdown(
                    f"<div style='margin-top:8px;font-size:13px;color:#ddd;'><b>Vuelta ideal de la sesión: "
                    f"{format_time(_field_ideal)}</b> &nbsp; ({_parts})</div>",
                    unsafe_allow_html=True
                )
            render_chart_guide(
                summary_text=None,
                how_to_read=(
                    "- **¿Una celda en MORADO?** → ese piloto fue el más rápido de TODO el campo en ese sector (el sector 'púrpura').\n"
                    "- La **Vuelta ideal** de cada piloto junta sus 3 mejores sectores, aunque los hiciera en vueltas distintas (su tope personal).\n"
                    "- La **vuelta ideal de la sesión** (abajo) combina los mejores sectores de cualquiera: el récord teórico absoluto del día.\n"
                    "- **¿Su vuelta ideal es mucho mejor que su vuelta real?** → dejó tiempo en la mesa; no encadenó sus mejores sectores en una sola vuelta.\n"
                    "- La tabla va ordenada por vuelta ideal, de la mejor a la peor."
                )
            )
    except Exception as _e:
        st.info(f"No se pudo construir el tablero de sectores: {_e}")

# --- TAB 2: TELEMETRÍA ---

with tabs[1]:

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

with tabs[2]:

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

with tabs[3]:

    # ── TIEMPOS POR VUELTA (TABLA) ─────────────────────────────────────────
    # La gráfica de evolución del ritmo vive ahora SOLO en PANORAMA (no duplicar).

    st.markdown("#### TIEMPOS POR VUELTA (TABLA)")
    st.caption("La gráfica de evolución del ritmo está ahora en la pestaña **PANORAMA**. Aquí queda la tabla vuelta a vuelta con los compuestos.")

    if not laps_vip.empty and laps_vip['LapNumber'].notna().any():
        min_lap_gpt = int(laps_vip['LapNumber'].min())
        max_lap_gpt = int(laps_vip['LapNumber'].max())
        if max_lap_gpt > min_lap_gpt:
            rng_gpt = st.slider(
                "Vueltas visibles en la tabla:",
                min_lap_gpt, max_lap_gpt,
                (min_lap_gpt, min(min_lap_gpt + 7, max_lap_gpt)),
                key="gpt_table_range"
            )
        else:
            rng_gpt = (min_lap_gpt, max_lap_gpt)
        render_gp_tempo_table(laps_vip, selected_abbr, rng_gpt[0], rng_gpt[1])

    st.divider()

    # ── PACE EVOLUTION ─────────────────────────────────────────────────────

    if 'pace_context_layers' not in st.session_state:
        st.session_state['pace_context_layers'] = ["SC", "VSC", "Red"]
    if 'pace_pits_view' not in st.session_state:
        st.session_state['pace_pits_view'] = "Tabla"
    if 'pace_pits_show' not in st.session_state:
        st.session_state['pace_pits_show'] = True

    st.markdown("#### Capas de contexto")
    # El default vive en session_state (pre-sembrado arriba); pasar también
    # default= aquí genera el warning de Streamlit por doble asignación.
    pace_layers = st.multiselect(
        "Capas de contexto",
        options=["Yellow", "VSC", "SC", "Red"],
        key="pace_context_layers"
    )

    fig_p = go.Figure()

    ritmo_metrics = {}

    for d in selected_abbr:

        df = laps_vip[laps_vip['Driver'] == d]

        c = get_neon_color(d); name = get_driver_name(d)

        hover = [f"<b>{name}</b><br>Vuelta: {l}<br>Tiempo: {t}" for l, t in zip(df['LapNumber'], df['TimeReadable'])]

        fig_p.add_trace(go.Scatter(x=df['LapNumber'], y=df['Smooth'], mode='lines+markers', name=d, line=dict(color=c, width=2.5, dash=style_map.get(d,'solid')), marker=dict(size=5, color=c, opacity=0.7), hoverinfo="text", hovertext=hover))

        # collect metrics

        if not df['Smooth'].dropna().empty:

            ritmo_metrics[get_driver_name(d)] = {'Avg Pace (s)': float(df['Smooth'].mean()), 'Std (s)': float(df['Smooth'].std())}



        pits = df[df['IsPit']==True]

        if not pits.empty:

             hover_pit = [f"<b>PIT STOP ({name})</b><br>Vuelta {l}<br>Entrada" for l in pits['LapNumber']]

             fig_p.add_trace(go.Scatter(x=pits['LapNumber'], y=pits['Smooth'], mode='markers', name=f"{d} PIT", marker=dict(symbol='diamond', size=14, color='#ffffff', line=dict(width=2, color=c)), hoverinfo="text", hovertext=hover_pit, showlegend=False))

    fig_p.update_yaxes(autorange="reversed")

    show_pits = st.session_state.get('pace_pits_show', True)
    pit_drivers = list(selected_abbr)
    pit_df_out = pd.DataFrame()
    if show_pits:
        # Los pits ya se marcan con rombos blancos en el bucle anterior;
        # aquí solo se calcula el DataFrame para la tabla/gráfica de pits.
        pit_df_out = get_pits_dataframe(race, laps, pit_drivers)

    layer_map = {"Yellow": "YELLOW", "VSC": "VSC", "SC": "SC", "Red": "RED"}
    selected_types = {layer_map[l] for l in pace_layers if l in layer_map}
    if selected_types:
        rcm_segments = _parse_race_control_messages(race)
        ts_segments = _parse_track_status(race)
        segments = []
        if rcm_segments:
            segments.extend(rcm_segments)
        else:
            segments.extend([s for s in ts_segments if s["type"] in {"SC", "VSC", "RED"}])
        if "YELLOW" in selected_types:
            segments.extend([s for s in ts_segments if s["type"] == "YELLOW"])
        segments = [s for s in segments if s["type"] in selected_types]

        mapped, unmapped = _segments_to_laps(segments, laps)
        if not mapped and not unmapped:
            st.caption("No hay datos de banderas para este evento.")
        if unmapped:
            st.warning("Evento sin mapeo a vuelta; se omitieron algunos eventos.")

        status_colors = {
            "SC": "#FFD000",
            "VSC": "#FFB000",
            "YELLOW": "#FFE066",
            "RED": "#FF3B30"
        }
        y_anchor = float(laps_vip['Smooth'].min()) if not laps_vip['Smooth'].dropna().empty else 0.0
        annotation_count = 0
        for seg in mapped:
            color = status_colors.get(seg["type"], "#888888")
            lap_start = seg["lap_start"]
            lap_end = seg["lap_end"]
            if lap_start == lap_end:
                fig_p.add_vline(x=lap_start, line_color=color, opacity=0.25, line_width=2)
            else:
                fig_p.add_vrect(x0=lap_start, x1=lap_end, fillcolor=color, opacity=0.15, line_width=0)
            mid = (lap_start + lap_end) / 2.0
            fig_p.add_trace(go.Scatter(
                x=[mid],
                y=[y_anchor],
                mode='markers',
                marker=dict(size=6, color=color, opacity=0.85),
                hovertemplate=f"{seg['type']}<br>Vueltas: {lap_start}-{lap_end}<extra></extra>",
                showlegend=False
            ))
            if annotation_count < 8:
                fig_p.add_annotation(
                    x=lap_start,
                    y=1.02,
                    xref="x",
                    yref="paper",
                    text=seg["type"],
                    showarrow=False,
                    font=dict(size=10, color=color)
                )
                annotation_count += 1

    st.plotly_chart(make_god_chart(fig_p, "RITMO DE CARRERA", "Tiempo (s)", "Vueltas", 600), use_container_width=True)

    render_chart_guide(
        summary_text=" ".join(
            f"{name}: ritmo promedio {v['Avg Pace (s)']:.3f}s (±{v['Std (s)']:.3f}s)."
            for name, v in ritmo_metrics.items()
        ) if ritmo_metrics else None,
        how_to_read=(
            "- Ritmo **suavizado** de cada piloto durante la carrera. Eje Y **invertido**: **más arriba = más rápido**.\n"
            "- Los **rombos blancos** marcan la vuelta en que entró a boxes.\n"
            "- Las **franjas de color** son Safety Car (amarillo), VSC (naranja) o bandera roja: ahí los ritmos se igualan.\n"
            "- **¿Dos líneas que se van separando poco a poco?** → uno degrada más o tiene más ritmo puro.\n"
            "- **¿Una línea sube (mejora) justo tras una parada?** → gomas nuevas rindiendo."
        )
    )

    st.markdown("#### Pits")
    pits_view = st.radio("Pits: vista", ["Tabla", "Gráfica"], horizontal=True, key="pace_pits_view")
    show_pits_toggle = st.toggle("Mostrar pits", key="pace_pits_show")
    show_pits = show_pits_toggle

    if not show_pits:
        st.caption("Pits ocultos.")
    else:
        if pit_df_out.empty:
            pit_cols_ok = 'PitInTime' in laps.columns and 'PitOutTime' in laps.columns
            pit_has_data = pit_cols_ok and (laps['PitInTime'].notna().any() or laps['PitOutTime'].notna().any())
            if pit_has_data:
                st.caption("Sin paradas de los pilotos seleccionados.")
            else:
                st.warning("No hay datos de pits disponibles en esta sesión.")
        elif pits_view == "Tabla":
            pit_df_out = pit_df_out.sort_values(['DriverCode', 'LapNumber'])
            df_view = pit_df_out.copy()
            df_view['Piloto'] = df_view['DriverCode'].apply(get_driver_name)
            df_view['Pit lane (s)'] = df_view['PitDuration_s'].round(2)
            view_cols = ['Piloto', 'LapNumber', 'Pit lane (s)']
            rename = {'LapNumber': 'Vuelta'}
            if 'CompoundAfter' in df_view.columns:
                df_view['Goma nueva'] = df_view['CompoundAfter']
                view_cols.append('Goma nueva')
            st.dataframe(df_view[view_cols].rename(columns=rename).set_index('Piloto'), use_container_width=True)
        else:
            fig_pits = go.Figure()
            for d in pit_drivers:
                d_pits = pit_df_out[pit_df_out['DriverCode'] == d]
                if d_pits.empty:
                    continue
                fig_pits.add_trace(go.Bar(
                    x=d_pits['LapNumber'],
                    y=d_pits['PitDuration_s'],
                    name=d,
                    marker_color=get_neon_color(d),
                    text=[f"{v:.1f}s" for v in d_pits['PitDuration_s']],
                    textposition="outside",
                    hovertemplate=f"{get_driver_name(d)}<br>Vuelta %{{x}}<br>Pit lane: %{{y:.2f}}s<extra></extra>"
                ))
            fig_pits.update_layout(
                template="plotly_dark",
                height=340,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=40, r=20, t=40, b=40),
                xaxis=dict(title="Vuelta de entrada a pits", dtick=1),
                yaxis=dict(title="Tiempo en pit lane (s)"),
                legend=dict(orientation="h", y=1.08, x=0)
            )
            st.plotly_chart(fig_pits, use_container_width=True)

        if not pit_df_out.empty:
            pit_parts = []
            for d in pit_drivers:
                d_pits = pit_df_out[pit_df_out['DriverCode'] == d]
                if d_pits.empty:
                    continue
                pit_parts.append(
                    f"{d}: {len(d_pits)} parada(s) en vuelta(s) {', '.join(map(str, d_pits['LapNumber'].tolist()))}, "
                    f"mejor pit lane {d_pits['PitDuration_s'].min():.2f}s."
                )
            render_chart_guide(
                summary_text=" ".join(pit_parts) if pit_parts else None,
                how_to_read=(
                    "- El número es el **tiempo total en el pit lane** (de entrada a salida), no solo los segundos con el coche detenido.\n"
                    "- Incluye recorrer el pit lane a velocidad limitada (~20 s en casi todos los circuitos) + la parada en sí.\n"
                    "- **¿Diferencias de 1-3 s entre paradas?** → cosa del equipo (cambio de gomas). **¿Mayores?** → un problema o una reparación.\n"
                    "- 'Goma nueva' es el compuesto con el que salió tras esa parada."
                )
            )

    # Metrics table: Average pace and consistency

    if ritmo_metrics:

        tbl = [(k, f"Avg: {v['Avg Pace (s)']:.3f}s · Std: {v['Std (s)']:.3f}s") for k, v in ritmo_metrics.items()]

        st.markdown(render_clean_metric_table(
            tbl, col1="Piloto", col2="Ritmo medio / variación",
            title="Ritmo de carrera",
            caption="Avg = tiempo de vuelta medio (suavizado) · Std = variación entre vueltas (menor = más consistente)."
        ), unsafe_allow_html=True)



    ref_gap = st.selectbox("Referencia Gaps:", selected_abbr, format_func=get_driver_name, key="ref_gap_carrera")

    try:

        base = laps.pick_driver(ref_gap)[['LapNumber', 'Time']].rename(columns={'Time':'RefTime'})

        merged = laps_vip.merge(base, on='LapNumber', how='left')

        merged['Gap'] = (merged['Time'] - merged['RefTime']).dt.total_seconds()

        fig_gap = go.Figure()

        gap_metrics = {}

        for d in selected_abbr:

            df = merged[merged['Driver'] == d]

            c = get_neon_color(d); name = get_driver_name(d)

            hover = [f"<b>{name}</b><br>Gap: {g:+.2f}s" for g in df['Gap']]

            fig_gap.add_trace(go.Scatter(x=df['LapNumber'], y=df['Gap'], mode='lines+markers', name=d, line=dict(color=c, width=2.5), marker=dict(size=5, color=c, opacity=0.7), hoverinfo="text", hovertext=hover))

            if not df['Gap'].dropna().empty:

                gap_metrics[get_driver_name(d)] = {'Mean Gap (s)': float(df['Gap'].mean()), 'Std Gap (s)': float(df['Gap'].std())}

        fig_gap.update_yaxes(autorange="reversed")

        st.plotly_chart(make_god_chart(fig_gap, f"DISTANCIA RELATIVA vs {get_driver_name(ref_gap)}", "Segundos", "Vueltas", 500), use_container_width=True)

        render_chart_guide(
            summary_text=" ".join(
                f"{name}: gap promedio {v['Mean Gap (s)']:+.2f}s vs {get_driver_name(ref_gap)}."
                for name, v in gap_metrics.items() if name != get_driver_name(ref_gap)
            ) if gap_metrics else None,
            how_to_read=(
                f"- A cuánto tiempo va cada piloto de **{get_driver_name(ref_gap)}** en cada vuelta.\n"
                "- **Gap positivo** = va por DETRÁS de la referencia · **negativo** = va por DELANTE.\n"
                "- **¿Una línea que se ALEJA de 0?** → pierde tiempo sostenidamente. **¿Que CONVERGE hacia 0?** → está recortando, viene de caza.\n"
                "- Los **saltos bruscos** suelen ser paradas en pits o Safety Car, no ritmo real."
            )
        )

        if gap_metrics:

            tbl_gap = [(k, f"Mean: {v['Mean Gap (s)']:.3f}s · Std: {v['Std Gap (s)']:.3f}s") for k, v in gap_metrics.items()]

            st.markdown(render_clean_metric_table(
                tbl_gap, col1="Piloto", col2=f"Gap medio vs {ref_gap}",
                title="Distancia relativa",
                caption=f"Mean = gap medio respecto a {get_driver_name(ref_gap)} (+ por detrás, − por delante) · Std = cuánto oscila ese gap."
            ), unsafe_allow_html=True)

    except: pass

    # ── STINT ANALYSIS ─────────────────────────────────────────────────────
    st.divider()
    st.markdown("#### ANÁLISIS DE STINT Y DEGRADACIÓN")
    st.caption("Ritmo medio y pendiente de degradación por stint. Un slope positivo indica pérdida de tiempo por vuelta (degradación).")

    try:
        stint_rows = []
        for d in selected_abbr:
            df_d = laps_vip[laps_vip['Driver'] == d].copy()
            if df_d.empty:
                continue
            df_d = df_d.sort_values('LapNumber').reset_index(drop=True)
            # Usar el número de stint oficial de FastF1 si existe; si no, derivarlo de los pits
            if 'Stint' in df_d.columns and df_d['Stint'].notna().any():
                df_d['Stint'] = df_d['Stint'].ffill().bfill().astype(int)
            else:
                pit_flags = df_d['IsPit'].fillna(False).astype(bool)
                stint_id = pit_flags.shift(1, fill_value=False).cumsum()
                df_d['Stint'] = (stint_id + 1).astype(int)

            for stint_num, grp in df_d.groupby('Stint'):
                # Excluir SC/VSC, in-laps y out-laps del cálculo de ritmo
                grp_clean = grp
                if 'IsScVsc' in grp.columns:
                    grp_clean = grp_clean[~grp_clean['IsScVsc']]
                if 'IsPit' in grp.columns:
                    grp_clean = grp_clean[~grp_clean['IsPit'].fillna(False).astype(bool)]
                if 'IsOutLap' in grp.columns:
                    grp_clean = grp_clean[~grp_clean['IsOutLap'].fillna(False).astype(bool)]
                clean = grp_clean['Seconds'].dropna()
                # Filter outliers (>107% of stint median)
                if clean.empty:
                    continue
                med = clean.median()
                clean = clean[clean <= med * 1.07]
                if len(clean) < 2:
                    continue
                laps_arr = grp.loc[clean.index, 'LapNumber'].values
                pace_med = float(clean.median())
                # Pendiente de degradación (s/vuelta) contra el número REAL de
                # vuelta: usar un índice 0..n sesgaría el valor si se
                # descartaron vueltas intermedias del stint.
                slope = float(np.polyfit(laps_arr.astype(float), clean.values, 1)[0])
                stint_rows.append({
                    'Driver': d,
                    'Name': get_driver_name(d),
                    'Color': get_neon_color(d),
                    'Stint': stint_num,
                    'Laps': len(clean),
                    'FirstLap': int(laps_arr.min()),
                    'LastLap': int(laps_arr.max()),
                    'MedianPace_s': pace_med,
                    'Slope_s_per_lap': slope,
                })

        if stint_rows:
            df_stint = pd.DataFrame(stint_rows)

            # Chart: median pace per stint per driver
            fig_stint = go.Figure()
            for d in selected_abbr:
                ds = df_stint[df_stint['Driver'] == d]
                if ds.empty:
                    continue
                c = get_neon_color(d)
                name = get_driver_name(d)
                hover_s = [
                    f"<b>{name} – Stint {row.Stint}</b><br>"
                    f"Vueltas: {row.FirstLap}–{row.LastLap} ({row.Laps} vueltas)<br>"
                    f"Ritmo mediano: {row.MedianPace_s:.3f}s<br>"
                    f"Degradación: {row.Slope_s_per_lap:+.4f}s/vuelta"
                    for row in ds.itertuples()
                ]
                fig_stint.add_trace(go.Scatter(
                    x=ds['Stint'], y=ds['MedianPace_s'],
                    mode='lines+markers', name=d,
                    line=dict(color=c, width=2.5),
                    marker=dict(size=9, color=c, symbol='circle', line=dict(width=1.5, color='white')),
                    hoverinfo="text", hovertext=hover_s
                ))
            fig_stint.update_layout(
                template="plotly_dark",
                xaxis=dict(title="Stint", tickmode='linear', dtick=1),
                yaxis=dict(title="Ritmo mediano (s)", autorange="reversed"),
                margin=dict(l=50, r=20, t=40, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(make_god_chart(fig_stint, "RITMO MEDIANO POR STINT", "Segundos", "Stint", 380), use_container_width=True)

            stint_summary = None
            if not df_stint.empty:
                best_deg_row = df_stint.loc[df_stint['Slope_s_per_lap'].idxmin()]
                worst_deg_row = df_stint.loc[df_stint['Slope_s_per_lap'].idxmax()]
                stint_summary = (
                    f"Mejor gestión: {best_deg_row['Name']} en el stint {int(best_deg_row['Stint'])} "
                    f"({best_deg_row['Slope_s_per_lap']:+.3f}s/vuelta). "
                    f"Mayor degradación: {worst_deg_row['Name']} en el stint {int(worst_deg_row['Stint'])} "
                    f"({worst_deg_row['Slope_s_per_lap']:+.3f}s/vuelta)."
                )
            render_chart_guide(
                summary_text=stint_summary,
                how_to_read=(
                    "- Cada punto es el **ritmo mediano** de un stint (tramo entre paradas). Eje Y invertido: **más arriba = más rápido**.\n"
                    "- **¿Comparas el mismo stint entre pilotos?** → ves quién tenía mejor ritmo con ese juego de gomas.\n"
                    "- En la tabla, la **degradación** es la pendiente: **+0.05 s/vuelta** = cada vuelta era 5 centésimas más lenta que la anterior.\n"
                    "- **¿Un stint más rápido que el anterior?** → goma nueva más blanda o coche más ligero (menos gasolina)."
                )
            )

            # Summary table
            disp = df_stint[['Name', 'Stint', 'Laps', 'FirstLap', 'LastLap', 'MedianPace_s', 'Slope_s_per_lap']].copy()
            disp['MedianPace_s'] = disp['MedianPace_s'].apply(lambda x: f"{x:.3f}s")
            disp['Slope_s_per_lap'] = disp['Slope_s_per_lap'].apply(lambda x: f"{x:+.4f}s/v")
            disp.columns = ['Piloto', 'Stint', 'Vueltas', 'Inicio', 'Fin', 'Ritmo Mediano', 'Degradación']
            st.dataframe(disp.set_index('Piloto'), use_container_width=True)
        else:
            st.info("No hay datos de stint suficientes para calcular degradación.")
    except Exception as _e_stint:
        st.caption(f"Stint analysis no disponible: {_e_stint}")

    # ── TIRE DEGRADATION (from old tab 4) ──────────────────────────────────

    st.divider()

    """

    PRINCIPIOS COLE NUSSBAUMER:

    1. DATOS LIMPIOS: Solo vueltas representativas (sin pits, sin Safety Car)

    2. REGRESIÓN LINEAL: Pendiente = Degradación Real (s/vuelta), Intercepto = Ritmo Base

    3. DISEÑO VISUAL: Ruido desaturado (opacidad 0.2), Tendencia sólida y brillante (width=3)

    4. TABLA INSIGHTS: Semáforo de datos (Verde/Amarillo/Rojo) para degradación

    """



    comp = laps_vip['Compound'].dropna().unique()

    if len(comp) > 0:

        sel = st.radio("Compuesto de Neumático:", comp, horizontal=True, key="compound_carrera")

        deg = laps_vip[laps_vip['Compound'] == sel].copy()



        # =========== INGENIERÍA DE DATOS ===========

        # Elimina in-laps, out-laps y vueltas bajo SC/VSC antes de la regresión:
        # son lentas por contexto, no por degradación de la goma.

        deg_clean = deg[~deg['IsPit']].copy()

        if 'IsOutLap' in deg_clean.columns:
            deg_clean = deg_clean[~deg_clean['IsOutLap'].fillna(False).astype(bool)]

        if 'IsScVsc' in deg_clean.columns:
            deg_clean = deg_clean[~deg_clean['IsScVsc'].fillna(False).astype(bool)]

        deg_clean = deg_clean.dropna(subset=['TyreLife', 'Seconds'])



        # Filtra vueltas atípicamente lentas (Safety Car): Q3 + 1.5*IQR
        # POR PILOTO: un umbral global mezclaría ritmos distintos y eliminaría
        # vueltas válidas del piloto más lento.

        if len(deg_clean) > 0:

            def _iqr_filter_driver(grp):
                q1 = grp['Seconds'].quantile(0.25)
                q3 = grp['Seconds'].quantile(0.75)
                return grp[grp['Seconds'] <= q3 + 1.5 * (q3 - q1)]

            deg_clean = deg_clean.groupby('Driver', group_keys=False).apply(_iqr_filter_driver).copy()



        if deg_clean.empty:

            st.warning("No hay datos suficientes para análisis de degradación (después de limpieza).")

        else:

            # =========== CÁLCULO MATEMÁTICO ===========

            fig_d_deg = go.Figure()

            insights = []



            for d in selected_abbr:

                df_pilot = deg_clean[deg_clean['Driver'] == d].copy()

                if len(df_pilot) < 3:

                    continue  # Necesita al menos 3 puntos



                c = get_neon_color(d)

                name = get_driver_name(d)



                # Scatter de ruido desaturado (Principio Cole: contexto visual)

                hover_scatter = [f"<b>{name}</b><br>Vuelta: {ln}<br>Goma: {v:.0f}<br>Tiempo: {t:.3f}s"

                                for ln, v, t in zip(df_pilot['LapNumber'], df_pilot['TyreLife'], df_pilot['Seconds'])]

                fig_d_deg.add_trace(go.Scatter(

                    x=df_pilot['TyreLife'], y=df_pilot['Seconds'], mode='markers',

                    name=name, marker=dict(color=c, size=5, opacity=0.2, line=dict(width=0)),

                    hoverinfo='text', hovertext=hover_scatter, showlegend=False

                ))



                # REGRESIÓN LINEAL: Calcula pendiente (degradación) e intercepto (ritmo base)

                try:

                    z = np.polyfit(df_pilot['TyreLife'], df_pilot['Seconds'], 1)

                    p = np.poly1d(z)

                    slope = z[0]  # Degradación (segundos por vida de goma)

                    intercept = z[1]  # Ritmo base teórico (V1 con goma nueva)



                    # Línea de tendencia sólida, gruesa, brillante (Principio Cole: atrae atención)

                    trend_x = np.linspace(df_pilot['TyreLife'].min(), df_pilot['TyreLife'].max(), 100)

                    trend_y = p(trend_x)

                    fig_d_deg.add_trace(go.Scatter(

                        x=trend_x, y=trend_y, mode='lines',

                        name=f"{d} (Deg: {slope:.4f} s/vuelta)",

                        line=dict(color=c, width=3, dash='solid'),

                        hoverinfo='skip', showlegend=True

                    ))



                    # Almacena datos para tabla insights

                    insights.append({

                        'driver': d,

                        'name': name,

                        'color': c,

                        'laps_analyzed': len(df_pilot),

                        'base_pace': intercept,

                        'degradation': slope,  # Segundos por vuelta de vida de goma

                        'max_tyre_life': df_pilot['TyreLife'].max()

                    })

                except Exception as e:

                    st.error(f"Error calculando regresión para {name}: {e}")



            fig_d_deg.update_layout(

                xaxis_title="Vida de Goma (Vueltas)",

                yaxis_title="Tiempo de Vuelta (s)",

                hovermode='closest'

            )

            # NO reversed: pendiente ascendente = degradación visible (más lento con goma usada)

            st.plotly_chart(make_god_chart(fig_d_deg, f"GESTIÓN DE NEUMÁTICOS: ANÁLISIS DE DEGRADACIÓN ({sel})",

                                          "Tiempo de Vuelta (s)", "Vida de Goma (Vueltas)", 550), use_container_width=True)

            deg_summary = None
            if insights:
                best_ins = min(insights, key=lambda x: x['degradation'])
                deg_summary = (
                    f"Con el compuesto {sel}, {best_ins['name']} tuvo la menor degradación "
                    f"({best_ins['degradation']:+.4f}s por vuelta de vida de goma, "
                    f"sobre {best_ins['laps_analyzed']} vueltas analizadas)."
                )
            render_chart_guide(
                summary_text=deg_summary,
                how_to_read=(
                    "- **Eje X**: vueltas de vida de la goma · **Eje Y**: tiempo de vuelta. Cada línea es un piloto con un compuesto.\n"
                    "- **¿La línea sube (muy inclinada)?** → la goma pierde rendimiento rápido: mucha degradación.\n"
                    "- **¿Línea casi PLANA?** → gestiona muy bien el neumático (o la pista mejoraba y lo compensa).\n"
                    "- Los **puntos tenues** son las vueltas reales; la **línea sólida** es la tendencia. Compara la misma goma entre pilotos: quién la cuida y quién la 'quema'."
                )
            )



            # =========== TABLA DE INSIGHTS CON SEMÁFORO ===========

            if insights:

                st.markdown("### TABLA DE INSIGHTS: Gestión de Neumáticos")

                st.caption(
                    "La **Evaluación** clasifica la pendiente de degradación (cuánto se ralentiza el piloto por cada vuelta "
                    "de vida de la goma). La columna **Por qué** traduce ese número a segundos perdidos reales."
                )

                # Ordena por degradación (menor = mejor gestión)
                insights.sort(key=lambda x: x['degradation'])

                def _evaluar_degradacion(deg, laps_n):
                    """Devuelve (etiqueta, color, icono, por_que) explicando la evaluación."""
                    loss10 = deg * 10.0          # segundos perdidos en 10 vueltas
                    loss_stint = deg * max(laps_n, 1)  # perdidos en el tramo analizado
                    if deg < -0.005:
                        return (
                            "Ritmo en mejora", "#4AA3FF", "▲",
                            f"El piloto fue <b>más rápido</b> con la goma más usada ({abs(deg):.3f}s/vuelta menos). "
                            "No es desgaste: manda la mejora de pista o el coche aligerándose de combustible."
                        )
                    if deg < 0.05:
                        return (
                            "Gestión excelente", "#27E36A", "●",
                            f"Solo pierde <b>{deg*1000:.0f} ms por vuelta</b> de vida de goma "
                            f"(≈ {loss10:.2f}s en 10 vueltas). Cuida muy bien el neumático."
                        )
                    if deg <= 0.10:
                        return (
                            "Degradación normal", "#F2C94C", "●",
                            f"Pierde <b>{deg*1000:.0f} ms por vuelta</b> (≈ {loss10:.2f}s en 10 vueltas). "
                            "Ritmo de caída típico de carrera; nada preocupante."
                        )
                    return (
                        "Degradación alta", "#FF4D4D", "●",
                        f"Pierde <b>{deg*1000:.0f} ms por vuelta</b> (≈ {loss10:.2f}s en 10 vueltas; "
                        f"~{loss_stint:.1f}s en las {laps_n} analizadas). La goma cae rápido: candidato a parar antes."
                    )

                table_html = '<table style="width:100%; border-collapse:collapse; background:rgba(255,255,255,0.02); border:1px solid #333;">'
                table_html += '<tr style="border-bottom:1px solid rgba(255,255,255,0.08);">'
                for h, al in [("Piloto", "left"), ("Vueltas", "center"), ("Ritmo base V1", "center"),
                              ("Degradación", "center"), ("Evaluación", "center"), ("Por qué", "left")]:
                    table_html += f'<th style="padding:10px 12px; color:#AAA; font-family:Roboto; text-align:{al}; font-size:13px;">{h}</th>'
                table_html += '</tr>'

                for row in insights:
                    status, color, icon, por_que = _evaluar_degradacion(row['degradation'], row['laps_analyzed'])
                    table_html += '<tr style="border-bottom:1px solid #2a2a2a;">'
                    table_html += f'<td style="padding:10px 12px; color:{row["color"]}; font-family:Roboto; font-weight:700;">{html.escape(row["name"])}</td>'
                    table_html += f'<td style="padding:10px 12px; color:#CCC; text-align:center;">{row["laps_analyzed"]}</td>'
                    table_html += f'<td style="padding:10px 12px; color:#CCC; text-align:center;">{format_time(row["base_pace"])}</td>'
                    table_html += f'<td style="padding:10px 12px; color:#CCC; text-align:center;">{row["degradation"]:+.3f} s/v</td>'
                    table_html += (
                        f'<td style="padding:10px 12px; text-align:center;">'
                        f'<span style="background:{color}22;color:{color};border:1px solid {color}55;border-radius:12px;'
                        f'padding:3px 10px;font-weight:700;font-size:12px;white-space:nowrap;">{icon} {status}</span></td>'
                    )
                    table_html += f'<td style="padding:10px 12px; color:#bbb; font-size:12px; line-height:1.4;">{por_que}</td>'
                    table_html += '</tr>'

                table_html += '</table>'
                st.markdown(table_html, unsafe_allow_html=True)

                st.markdown(
                    "<div style='font-size:12px;color:#888;margin-top:6px;'>"
                    "<b>Escala:</b> "
                    "<span style='color:#4AA3FF;'>▲ Ritmo en mejora</span> (deg &lt; 0) · "
                    "<span style='color:#27E36A;'>● Excelente</span> (&lt; 0.05 s/v) · "
                    "<span style='color:#F2C94C;'>● Normal</span> (0.05–0.10 s/v) · "
                    "<span style='color:#FF4D4D;'>● Alta</span> (&gt; 0.10 s/v). "
                    "'Ritmo base V1' = tiempo estimado con goma nueva (intercepto de la regresión)."
                    "</div>",
                    unsafe_allow_html=True
                )



    # ── WEATHER (wrapped in expander) ──────────────────────────────────────

    with st.expander("Clima de la Sesión"):

        try:

            w = race.weather_data.copy()

            w['Min'] = w['Time'].dt.total_seconds() / 60

            avg_track = float(w['TrackTemp'].mean()) if 'TrackTemp' in w.columns else None

            avg_air = float(w['AirTemp'].mean()) if 'AirTemp' in w.columns else None

            avg_delta = (avg_track - avg_air) if avg_track is not None and avg_air is not None else None

            m1_w, m2_w, m3_w = st.columns(3)

            with m1_w:

                st.metric("Temp pista prom.", f"{avg_track:.1f}°C" if avg_track is not None else "N/D")

            with m2_w:

                st.metric("Temp aire prom.", f"{avg_air:.1f}°C" if avg_air is not None else "N/D")

            with m3_w:

                st.metric("Δ pista-aire", f"{avg_delta:.1f}°C" if avg_delta is not None else "N/D")

            time_min_w = float(w['Min'].min()) if 'Min' in w.columns else 0.0

            time_max_w = float(w['Min'].max()) if 'Min' in w.columns else 0.0

            cursor_time_w = None

            if time_max_w > time_min_w:

                cursor_time_w = st.slider("Cursor tiempo (min)", time_min_w, time_max_w, time_min_w, step=1.0, key="weather_cursor_carrera")

            fig_w = go.Figure()

            if 'TrackTemp' in w.columns:

                fig_w.add_trace(go.Scatter(
                    x=w['Min'], y=w['TrackTemp'], name="Pista",
                    line=dict(color='#e74c3c', width=3),
                    hovertemplate="Min %{x:.1f}<br>Temp pista: %{y:.1f}°C<extra></extra>"
                ))

            if 'AirTemp' in w.columns:

                fig_w.add_trace(go.Scatter(
                    x=w['Min'], y=w['AirTemp'], name="Aire",
                    line=dict(color='#3498db', width=3),
                    hovertemplate="Min %{x:.1f}<br>Temp aire: %{y:.1f}°C<extra></extra>"
                ))

            if cursor_time_w is not None:

                fig_w.add_vline(x=cursor_time_w, line_dash="dot", line_color="#888")

            st.plotly_chart(make_god_chart(fig_w, "TEMPERATURAS", "°C", "Min", 420), use_container_width=True)

            sub_cols_w = st.columns(3)

            if 'WindSpeed' in w.columns:

                sub_cols_w[0].metric("Viento prom.", f"{float(w['WindSpeed'].mean()):.1f} km/h")

            if 'Humidity' in w.columns:

                sub_cols_w[1].metric("Humedad prom.", f"{float(w['Humidity'].mean()):.0f}%")

            if 'Rainfall' in w.columns:

                sub_cols_w[2].metric("Lluvia prom.", f"{float(w['Rainfall'].mean()):.2f} mm")

        except Exception:

            st.info("Datos de clima no disponibles.")

    # ── HEATMAP: velocidad punta (Speed Trap) por vuelta ──
    st.divider()
    st.markdown("**VELOCIDAD PUNTA (SPEED TRAP) POR VUELTA**")
    st.caption("Velocidad máxima en la trampa de velocidad en cada vuelta. Revela quién tiene menos drag / mejor punta y cómo cambia con el combustible, el rebufo (DRS/tow) y las tandas.")

    try:
        _stz = laps_vip.dropna(subset=['SpeedST', 'LapNumber']).copy()
        _stz = _stz[_stz['SpeedST'] > 0]
        if _stz.empty:
            st.info("No hay datos de velocidad punta (Speed Trap) para esta sesión.")
        else:
            _stz['LapNumber'] = _stz['LapNumber'].astype(int)
            _order_hm = [d for d in selected_abbr if d in set(_stz['Driver'].values)]
            _lap_min = int(_stz['LapNumber'].min())
            _lap_max = int(_stz['LapNumber'].max())
            _laps_axis = list(range(_lap_min, _lap_max + 1))
            _z = []
            for d in _order_hm:
                dd = _stz[_stz['Driver'] == d].groupby('LapNumber')['SpeedST'].max()
                _z.append([float(dd[l]) if l in dd.index else None for l in _laps_axis])
            if not _order_hm or not _laps_axis:
                st.info("No hay suficientes vueltas para el heatmap de velocidad punta.")
            else:
                fig_hm = go.Figure(go.Heatmap(
                    z=_z, x=_laps_axis, y=[get_driver_name(d) for d in _order_hm],
                    colorscale="Turbo", colorbar=dict(title="km/h"),
                    text=_z, texttemplate="%{z:.0f}", textfont=dict(size=9, color="#FFFFFF"),
                    hovertemplate="%{y}<br>Vuelta %{x}<br>%{z:.0f} km/h<extra></extra>",
                    hoverongaps=False
                ))
                fig_hm = make_god_chart(fig_hm, "VELOCIDAD PUNTA POR VUELTA (km/h)", "", "Vuelta", 120 + 42 * len(_order_hm))
                st.plotly_chart(fig_hm, use_container_width=True, config={"displayModeBar": False})
                _means = {d: float(_stz[_stz['Driver'] == d]['SpeedST'].mean()) for d in _order_hm}
                _maxs = {d: float(_stz[_stz['Driver'] == d]['SpeedST'].max()) for d in _order_hm}
                _top_mean = max(_means, key=_means.get)
                _top_max = max(_maxs, key=_maxs.get)
                render_chart_guide(
                    summary_text=(
                        f"{get_driver_name(_top_max)} marcó la punta más alta ({_maxs[_top_max]:.0f} km/h) y "
                        f"{get_driver_name(_top_mean)} tuvo la mayor media de velocidad punta ({_means[_top_mean]:.0f} km/h)."
                    ),
                    how_to_read=(
                        "- **Filas** = pilotos · **columnas** = vuelta · **color** = velocidad punta (más cálido = más rápido).\n"
                        "- **¿Un piloto SIEMPRE más cálido?** → menos drag (alerón más descargado) o mejor motor/ERS en recta.\n"
                        "- **¿Un salto puntual de color?** → suele ser rebufo/DRS (ir pegado a otro coche) o el combustible vaciándose.\n"
                        "- Los **huecos** (celdas vacías) son vueltas de entrada/salida de boxes o sin dato.\n"
                        "- Es la velocidad en la **trampa** oficial, no la punta absoluta de toda la vuelta."
                    )
                )
    except Exception as _e:
        st.info(f"No se pudo construir el heatmap de velocidad punta: {_e}")

    # ── LAP CHART: posición vuelta a vuelta (estilo MultiViewer) ──
    st.divider()
    st.markdown("**LAP CHART: posición de cada piloto vuelta a vuelta**")
    st.caption("La 'telaraña' de la carrera: cada línea es un piloto y su posición en cada vuelta (1º arriba). Los cruces son adelantamientos y paradas. Compañeros de equipo comparten color (uno sólido, otro punteado).")

    try:
        pos_laps = race.laps.dropna(subset=['Position', 'LapNumber', 'Driver']).copy()
        if pos_laps.empty:
            st.info("No hay datos de posición por vuelta para esta sesión.")
        else:
            pos_laps['LapNumber'] = pos_laps['LapNumber'].astype(int)
            pos_laps['Position'] = pos_laps['Position'].astype(int)
            _final_pos = pos_laps.sort_values('LapNumber').groupby('Driver')['Position'].last().sort_values()
            drivers_lc = [d for d in _final_pos.index if d in selected_abbr]
            if not drivers_lc:
                drivers_lc = list(_final_pos.index)
            n_drv_lc = len(drivers_lc)
            max_lap_lc = int(pos_laps['LapNumber'].max())
            _sel_pos = pos_laps[pos_laps['Driver'].isin(drivers_lc)]['Position']
            _pos_lo = int(_sel_pos.min()) if not _sel_pos.empty else 1
            _pos_hi = int(_sel_pos.max()) if not _sel_pos.empty else n_drv_lc
            team_seen_lc = {}
            fig_lc = go.Figure()
            _CC = {'SOFT': '#FF3B3B', 'MEDIUM': '#FFD23B', 'HARD': '#EDEDED',
                   'INTERMEDIATE': '#43B04A', 'WET': '#2B7FFF', 'UNKNOWN': '#AAAAAA'}
            _pit_x, _pit_y, _pit_c, _pit_t = [], [], [], []
            for d in drivers_lc:
                dd = pos_laps[pos_laps['Driver'] == d].sort_values('LapNumber')
                _team = _get_team_for_driver(race.laps, d)
                tkey = _team.lower() if isinstance(_team, str) else str(d)
                base = _TEAM_COLORS_NORM.get(tkey) if isinstance(_team, str) else None
                if not base:
                    base = get_driver_info(d)['color']
                _o = team_seen_lc.get(tkey, 0)
                team_seen_lc[tkey] = _o + 1
                _dash = 'solid' if _o == 0 else 'dash'
                fig_lc.add_trace(go.Scatter(
                    x=dd['LapNumber'], y=dd['Position'], mode='lines', name=d,
                    line=dict(color=base, width=2.4, dash=_dash, shape='spline', smoothing=0.5),
                    hovertemplate=f"{get_driver_name(d)}<br>Vuelta %{{x}} · P%{{y}}<extra></extra>"
                ))
                _last = dd.iloc[-1]
                fig_lc.add_annotation(
                    x=int(_last['LapNumber']), y=int(_last['Position']), text=f" {d}",
                    xanchor="left", yanchor="middle", showarrow=False,
                    font=dict(color=base, size=11, family="Roboto")
                )
                # Marcas de PIT (Opción tyre-age): inicio de cada stint > 1, color = compuesto nuevo
                if 'Stint' in dd.columns:
                    for _sid, _g in dd.dropna(subset=['Stint']).groupby('Stint'):
                        if int(_sid) <= 1:
                            continue
                        _row = _g.sort_values('LapNumber').iloc[0]
                        _comp = str(_row.get('Compound', 'UNKNOWN')).upper() if pd.notna(_row.get('Compound', None)) else 'UNKNOWN'
                        _pit_x.append(int(_row['LapNumber']))
                        _pit_y.append(int(_row['Position']))
                        _pit_c.append(_CC.get(_comp, _CC['UNKNOWN']))
                        _pit_t.append(f"{d} · PIT → {_comp.title()} (V{int(_row['LapNumber'])})")
            if _pit_x:
                fig_lc.add_trace(go.Scatter(
                    x=_pit_x, y=_pit_y, mode='markers', name='Pit',
                    marker=dict(symbol='diamond', size=9, color=_pit_c, line=dict(color='#0e1117', width=1.2)),
                    text=_pit_t, hovertemplate="%{text}<extra></extra>", showlegend=False
                ))
            fig_lc = make_god_chart(fig_lc, "LAP CHART · POSICIÓN VUELTA A VUELTA", "Posición", "Vuelta", 300 + 20 * n_drv_lc)
            fig_lc.update_layout(showlegend=False, hovermode="closest")
            fig_lc.update_yaxes(autorange="reversed", tickmode='array',
                                tickvals=list(range(_pos_lo, _pos_hi + 1)),
                                ticktext=[f"{p}º" for p in range(_pos_lo, _pos_hi + 1)])
            fig_lc.update_xaxes(range=[0.5, max_lap_lc + 3], dtick=5)
            # Sombreado de SC / VSC (Opción ventanas de pit / Safety Car)
            for _typ, _l0, _l1 in _sc_vsc_lap_ranges(race):
                _fc = "rgba(255,208,0,0.10)" if _typ == "SC" else "rgba(255,176,0,0.08)"
                fig_lc.add_vrect(x0=_l0 - 0.5, x1=_l1 + 0.5, fillcolor=_fc, line_width=0, layer="below")
                fig_lc.add_annotation(x=(_l0 + _l1) / 2.0, xref="x", y=1.0, yref="paper",
                                      text=_typ, showarrow=False, yanchor="bottom",
                                      font=dict(color="#FFD000", size=11, family="Roboto"))
            st.plotly_chart(fig_lc, use_container_width=True, config=DIST_CHART_CONFIG)
            _first_pos = pos_laps.sort_values('LapNumber').groupby('Driver')['Position'].first()
            _gains = (_first_pos - _final_pos)
            _gains = _gains[_gains.index.isin(drivers_lc)]
            _climber = _gains.idxmax()
            _dropper = _gains.idxmin()
            render_chart_guide(
                summary_text=(
                    f"{get_driver_name(_climber)} fue quien más ganó posiciones (+{int(_gains[_climber])}) y "
                    f"{get_driver_name(_dropper)} el que más perdió ({int(_gains[_dropper])})."
                ) if len(_gains) and (_gains[_climber] != 0 or _gains[_dropper] != 0) else None,
                how_to_read=(
                    "- **Eje Y**: posición (1º arriba) · **Eje X**: vuelta. Cada línea es un piloto.\n"
                    "- **¿Dos líneas se cruzan?** → hubo un adelantamiento (en pista o por paradas).\n"
                    "- **¿Una línea cae en picada y luego sube?** → una parada en boxes. Los **rombos** marcan el pit, con el color del compuesto NUEVO que montó.\n"
                    "- Las **bandas amarillas** son Safety Car / VSC: clave para ver quién aprovechó la parada 'barata'.\n"
                    "- Compañeros de equipo comparten color: **línea sólida** = uno, **punteada** = el otro.\n"
                    "- Líneas planas arriba = dominio; mucho cruce en la zona media = la pelea real de la carrera."
                )
            )
    except Exception as _e:
        st.info(f"No se pudo construir el lap chart: {_e}")

    # ── GAP AL LÍDER vuelta a vuelta (hueco de tiempo) ──
    st.divider()
    st.markdown("**GAP AL LÍDER: hueco de tiempo vuelta a vuelta**")
    st.caption("La carrera en TIEMPO (no en posiciones): el hueco de cada piloto respecto al líder en cada vuelta. Los saltos revelan undercuts, tráfico, Safety Cars y quién se escapa o recorta.")

    try:
        gl = race.laps.dropna(subset=['Driver', 'LapNumber', 'Time']).copy()
        if gl.empty:
            st.info("No hay datos de tiempo por vuelta para el gap al líder.")
        else:
            gl['LapNumber'] = gl['LapNumber'].astype(int)
            gl['Tsec'] = gl['Time'].dt.total_seconds()
            leader_t = gl.groupby('LapNumber')['Tsec'].min()
            _final_pos_g = race.laps.dropna(subset=['Position', 'LapNumber']).sort_values('LapNumber').groupby('Driver')['Position'].last().sort_values()
            _order_g = [d for d in _final_pos_g.index if d in set(gl['Driver'].values) and d in selected_abbr]
            if not _order_g:
                _order_g = [d for d in _final_pos_g.index if d in set(gl['Driver'].values)]
            team_seen_g = {}
            fig_gl = go.Figure()
            max_lap_g = int(gl['LapNumber'].max())
            _gap_hi = 0.0
            for d in _order_g:
                dd = gl[gl['Driver'] == d].sort_values('LapNumber')
                gap = dd['Tsec'].values - leader_t.reindex(dd['LapNumber'].values).values
                _team = _get_team_for_driver(race.laps, d)
                tkey = _team.lower() if isinstance(_team, str) else str(d)
                base = _TEAM_COLORS_NORM.get(tkey) if isinstance(_team, str) else None
                if not base:
                    base = get_driver_info(d)['color']
                _o = team_seen_g.get(tkey, 0)
                team_seen_g[tkey] = _o + 1
                _dash = 'solid' if _o == 0 else 'dash'
                _gv = gap[np.isfinite(gap)]
                if _gv.size:
                    _gap_hi = max(_gap_hi, float(np.nanpercentile(_gv, 90)))
                fig_gl.add_trace(go.Scatter(
                    x=dd['LapNumber'], y=gap, mode='lines', name=d,
                    line=dict(color=base, width=2, dash=_dash),
                    hovertemplate=f"{get_driver_name(d)}<br>Vuelta %{{x}} · +%{{y:.1f}} s<extra></extra>"
                ))
            fig_gl = make_god_chart(fig_gl, "GAP AL LÍDER (s) POR VUELTA", "Segundos tras el líder", "Vuelta", 520)
            fig_gl.update_layout(showlegend=True, hovermode="closest")
            _cap = max(_gap_hi * 1.12, 5.0)
            fig_gl.update_yaxes(range=[_cap, -1.0])  # líder (0) arriba, los de atrás abajo
            fig_gl.update_xaxes(range=[0.5, max_lap_g + 1], dtick=5)
            for _typ, _l0, _l1 in _sc_vsc_lap_ranges(race):
                _fc = "rgba(255,208,0,0.10)" if _typ == "SC" else "rgba(255,176,0,0.08)"
                fig_gl.add_vrect(x0=_l0 - 0.5, x1=_l1 + 0.5, fillcolor=_fc, line_width=0, layer="below")
            st.plotly_chart(fig_gl, use_container_width=True, config=DIST_CHART_CONFIG)
            render_chart_guide(
                summary_text=None,
                how_to_read=(
                    "- **Eje Y**: segundos por detrás del líder (arriba = líder, en 0) · **Eje X**: vuelta.\n"
                    "- **¿Una línea se aleja (baja) y luego vuelve?** → una parada en boxes (pierde ~20-25 s y recupera al parar los demás).\n"
                    "- **¿Dos líneas que se JUNTAN justo antes de una parada?** → un undercut / overcut en juego.\n"
                    "- Bajo **Safety Car / VSC** (bandas amarillas) los huecos se **comprimen**: ahí las paradas salen 'baratas'.\n"
                    "- El eje se recorta al grupo de cabeza (percentil 90), así que los coches doblados pueden quedar fuera por abajo."
                )
            )
    except Exception as _e:
        st.info(f"No se pudo construir el gap al líder: {_e}")

    # ── ESTRATEGIA DE NEUMÁTICOS: stints por piloto ──
    st.divider()
    st.markdown("**ESTRATEGIA DE NEUMÁTICOS: tandas (stints) y paradas por piloto**")
    st.caption("La estrategia de la carrera: cada barra es un piloto y sus tandas coloreadas por compuesto; cada corte es una parada en boxes.")

    _COMP_COL = {'SOFT': '#FF3B3B', 'MEDIUM': '#FFD23B', 'HARD': '#EDEDED',
                 'INTERMEDIATE': '#43B04A', 'WET': '#2B7FFF', 'UNKNOWN': '#888888'}
    try:
        _sl = race.laps.dropna(subset=['Driver', 'LapNumber', 'Stint']).copy()
        if 'Compound' not in _sl.columns or _sl.empty:
            st.info("No hay datos de compuestos/stints para esta sesión.")
        else:
            _sl['LapNumber'] = _sl['LapNumber'].astype(int)
            _fp = race.laps.dropna(subset=['Position', 'LapNumber']).sort_values('LapNumber').groupby('Driver')['Position'].last().sort_values()
            _order_ts = [d for d in _fp.index if d in set(_sl['Driver'].values) and d in selected_abbr]
            if not _order_ts:
                _order_ts = [d for d in _fp.index if d in set(_sl['Driver'].values)]
            if not _order_ts:
                _order_ts = sorted(_sl['Driver'].unique())
            fig_ts = go.Figure()
            _stops = {}
            for d in _order_ts:
                dd = _sl[_sl['Driver'] == d].sort_values('LapNumber')
                _stints = list(dd.groupby('Stint'))
                _stops[d] = max(len(_stints) - 1, 0)
                for _sid, g in _stints:
                    comp = str(g['Compound'].iloc[0]).upper() if pd.notna(g['Compound'].iloc[0]) else 'UNKNOWN'
                    ls = int(g['LapNumber'].min())
                    le = int(g['LapNumber'].max())
                    length = le - ls + 1
                    col = _COMP_COL.get(comp, _COMP_COL['UNKNOWN'])
                    fig_ts.add_trace(go.Bar(
                        y=[get_driver_name(d)], x=[length], base=ls - 1, orientation='h',
                        marker=dict(color=col, line=dict(color='#0e1117', width=1)),
                        text=[comp[:1]], textposition='inside', insidetextanchor='middle',
                        textfont=dict(color='#0e1117', size=10),
                        hovertemplate=f"{get_driver_name(d)}<br>{comp.title()}<br>Vueltas {ls}–{le} ({length})<extra></extra>",
                        showlegend=False
                    ))
            fig_ts = make_god_chart(fig_ts, "ESTRATEGIA DE NEUMÁTICOS (stints por piloto)", "", "Vuelta", 140 + 30 * len(_order_ts))
            fig_ts.update_layout(barmode='overlay', hovermode="closest", bargap=0.35)
            fig_ts.update_yaxes(autorange="reversed")
            fig_ts.update_xaxes(rangemode="tozero")
            st.plotly_chart(fig_ts, use_container_width=True, config={"displayModeBar": False})
            _leg = " &nbsp;&nbsp; ".join(
                f"<span style='color:{_COMP_COL[c]};font-weight:800;'>■</span> {c.title()}"
                for c in ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET']
            )
            st.markdown(f"<div style='font-size:12px;color:#bbb;'>{_leg}</div>", unsafe_allow_html=True)
            if _stops:
                _common = max(set(_stops.values()), key=list(_stops.values()).count)
                _summary_ts = f"La estrategia más común fue de {_common} parada(s)."
            else:
                _summary_ts = None
            render_chart_guide(
                summary_text=_summary_ts,
                how_to_read=(
                    "- Cada **barra** es un piloto (1º arriba) y sus **tandas**; los colores son los compuestos: rojo=blando, amarillo=medio, blanco=duro, verde=intermedio, azul=lluvia.\n"
                    "- Cada **corte** entre colores es una **parada en boxes**; nº de segmentos − 1 = nº de paradas.\n"
                    "- **¿Un stint largo con duro?** → estrategia conservadora a 1 parada. **¿Varios cortos?** → agresiva a 2-3 paradas.\n"
                    "- **¿Un piloto paró ANTES que su rival directo?** → intentó un undercut (adelantar por boxes). **¿Alargó la tanda?** → overcut."
                )
            )
    except Exception as _e:
        st.info(f"No se pudo construir la estrategia de neumáticos: {_e}")

    # ── PARRILLA → META: posiciones ganadas / perdidas ──
    st.divider()
    st.markdown("**PARRILLA → META: posiciones ganadas y perdidas**")
    st.caption("Cuántas posiciones ganó o perdió cada piloto entre la salida (parrilla) y la meta. Verde = escaló, rojo = cedió.")
    try:
        _res = race.results
        if 'GridPosition' not in getattr(_res, 'columns', []) or 'Position' not in getattr(_res, 'columns', []):
            st.info("No hay datos de parrilla / resultado para esta sesión.")
        else:
            _gr = _res.dropna(subset=['Position', 'GridPosition'])
            _gr = _gr[_gr['GridPosition'] > 0]
            if _gr.empty:
                st.info("No hay parrilla de salida válida (sesión sin salida desde parrilla).")
            else:
                _rowsg = [(r['Abbreviation'], int(r['GridPosition']), int(r['Position']), int(r['GridPosition']) - int(r['Position']))
                          for _, r in _gr.iterrows()]
                _selg = [x for x in _rowsg if x[0] in selected_abbr] or _rowsg
                _selg = sorted(_selg, key=lambda x: x[3])
                fig_gf = go.Figure(go.Bar(
                    y=[get_driver_name(x[0]) for x in _selg], x=[x[3] for x in _selg], orientation='h',
                    marker=dict(color=["#00E676" if x[3] > 0 else ("#FF5252" if x[3] < 0 else "#888888") for x in _selg],
                                line=dict(color='#0e1117', width=1)),
                    text=[f"{x[3]:+d}" if x[3] != 0 else "0" for x in _selg], textposition='outside',
                    textfont=dict(color="#ddd", size=12),
                    hovertext=[f"{get_driver_name(x[0])}<br>Parrilla P{x[1]} → Meta P{x[2]}<br>{x[3]:+d} posiciones" for x in _selg],
                    hoverinfo="text", showlegend=False
                ))
                fig_gf.add_vline(x=0, line=dict(color="rgba(255,255,255,0.4)", width=1))
                fig_gf = make_god_chart(fig_gf, "POSICIONES GANADAS / PERDIDAS (parrilla → meta)", "", "Posiciones", 130 + 30 * len(_selg))
                fig_gf.update_layout(hovermode="closest")
                st.plotly_chart(fig_gf, use_container_width=True, config={"displayModeBar": False})
                _asc = sorted(_rowsg, key=lambda x: -x[3])
                render_chart_guide(
                    summary_text=(f"{get_driver_name(_asc[0][0])} fue el que más escaló (P{_asc[0][1]}→P{_asc[0][2]}, {_asc[0][3]:+d}) y "
                                  f"{get_driver_name(_asc[-1][0])} el que más cedió (P{_asc[-1][1]}→P{_asc[-1][2]}, {_asc[-1][3]:+d})."),
                    how_to_read=(
                        "- **Verde (+)** = ganó posiciones respecto a donde salió · **Rojo (−)** = las perdió.\n"
                        "- Es el 'saldo' de la carrera: junta salida, ritmo, estrategia y adelantamientos en un solo número.\n"
                        "- **¿+grande?** → remontada (salió mal clasificado o con penalización). **¿−grande?** → problemas, pinchazo o mala estrategia.\n"
                        "- No separa los adelantamientos en pista de los ganados por paradas — para el detalle mira el **Lap Chart**."
                    )
                )
    except Exception as _e:
        st.info(f"No se pudo construir parrilla→meta: {_e}")

    # ── RITMO CORREGIDO POR COMBUSTIBLE ──
    st.divider()
    st.markdown("**RITMO CORREGIDO POR COMBUSTIBLE**")
    st.caption("Quita el efecto del depósito (el coche se aligera y va más rápido según se vacía) para ver la degradación PURA del neumático de los pilotos seleccionados.")
    fuel_k = st.slider("Efecto del combustible (s por vuelta de carga)", 0.00, 0.10, 0.035, 0.005, key="fuel_k",
                       help="Cuánto más lento va el coche por cada vuelta de combustible a bordo. Típico ~0.03-0.05 s/vuelta. Súbelo/bájalo hasta que el ritmo a principio de tanda quede plano.")
    try:
        _fl = laps_vip[laps_vip['IsPit'] == False].copy() if 'IsPit' in laps_vip.columns else laps_vip.copy()
        _fl = _fl.dropna(subset=['LapNumber', 'LapTime', 'Driver'])
        if _fl.empty:
            st.info("No hay vueltas limpias para corregir por combustible.")
        else:
            _fl['LapNumber'] = _fl['LapNumber'].astype(int)
            fig_fc = go.Figure()
            _any_fc = False
            for d in selected_abbr:
                dd = _fl[_fl['Driver'] == d].sort_values('LapNumber')
                if dd.empty:
                    continue
                sec = dd['LapTime'].dt.total_seconds().values
                lapn = dd['LapNumber'].values.astype(float)
                med = np.median(sec)
                m = sec < med + 3.0  # descarta SC / tráfico
                corr = sec + fuel_k * (lapn - 1.0)  # normaliza a depósito lleno (quita la mejora por peso)
                if m.sum() < 2:
                    continue
                _any_fc = True
                fig_fc.add_trace(go.Scatter(
                    x=lapn[m], y=corr[m], mode='lines+markers', name=get_driver_name(d),
                    line=dict(color=get_neon_color(d), width=2), marker=dict(size=4),
                    hovertemplate=f"{get_driver_name(d)}<br>Vuelta %{{x:.0f}}<br>Corregido: %{{y:.2f}} s<extra></extra>"
                ))
            if _any_fc:
                fig_fc = make_god_chart(fig_fc, "RITMO CORREGIDO POR COMBUSTIBLE (s/vuelta)", "Tiempo corregido (s)", "Vuelta", 460)
                plot_wide(fig_fc)
                render_chart_guide(
                    summary_text=None,
                    how_to_read=(
                        f"- A cada vuelta se le suma **{fuel_k:.3f} s por cada vuelta de combustible ya gastada**, como si todos corrieran con el depósito lleno.\n"
                        "- Así se **quita la mejora** por el coche que se aligera y queda a la vista la **degradación real del neumático**.\n"
                        "- Tras corregir: línea que **sube** = la goma se degrada de verdad; línea **plana** = gestión excelente.\n"
                        "- Los **escalones** hacia abajo son cambios a goma nueva (paradas).\n"
                        "- El factor es ajustable: súbelo/bájalo hasta que el ritmo a principio de cada tanda quede plano."
                    )
                )
            else:
                st.info("No hay suficientes vueltas limpias de los pilotos seleccionados.")
    except Exception as _e:
        st.info(f"No se pudo construir el ritmo corregido: {_e}")

# --- TAB 5: FÍSICA ---

with tabs[4]:

    # 1) G-FORCE LONGITUDINAL (ACELERACIÓN/FRENADA)

    st.markdown("**FUERZA G LONGITUDINAL: ¿dónde y cuán fuerte frena cada piloto?**")

    fig_long = go.Figure()

    glong_metrics = {}
    brake_zones = {}

    for d in selected_abbr:

        try:

            t = get_cached_telemetry(laps, d, lap_mode, target_lap)
            if t is None:
                continue

            # Mismo cálculo robusto que el G-G Plot (malla uniforme de distancia)
            gg_data = compute_gg_from_telemetry(t)
            if gg_data is None:
                continue
            dist_arr = gg_data['distance']
            glong = gg_data['glong']

            c = get_neon_color(d)

            name = get_driver_name(d)

            idx_brake = int(np.nanargmin(glong))
            glong_metrics[name] = {'max_accel': float(np.nanmax(glong)), 'max_brake': float(abs(np.nanmin(glong)))}
            brake_zones[name] = float(dist_arr[idx_brake])

            def _glong_hover_txt(val):
                if not np.isfinite(val):
                    return "Sin dato"
                if val < -0.15:
                    return f"Frenando: {abs(val):.2f}G"
                if val > 0.15:
                    return f"Acelerando: {val:.2f}G"
                return "Velocidad constante"

            hover = [
                f"<b>{name}</b><br>Dist: {dd:.0f} m<br>{_glong_hover_txt(val)}"
                for dd, val in zip(dist_arr, glong)
            ]

            fig_long.add_trace(go.Scatter(

                x=dist_arr, y=glong, mode='lines', name=name,

                line=dict(color=c, width=2),

                hovertext=hover, hoverinfo="text"

            ))

            # Marcar la frenada más fuerte de cada piloto
            fig_long.add_trace(go.Scatter(
                x=[dist_arr[idx_brake]], y=[float(glong[idx_brake])],
                mode='markers',
                marker=dict(symbol='triangle-down', size=12, color=c, line=dict(width=1.5, color='#FFFFFF')),
                hovertemplate=f"<b>{name}</b><br>Frenada más fuerte: {abs(float(glong[idx_brake])):.2f}G<br>Dist: {dist_arr[idx_brake]:.0f} m<extra></extra>",
                showlegend=False
            ))

        except:

            pass

    # Fondo: zona verde = acelerando, zona roja = frenando (lectura inmediata)
    fig_long.add_hrect(y0=0, y1=6, fillcolor="rgba(76,175,80,0.05)", line_width=0)
    fig_long.add_hrect(y0=-6, y1=0, fillcolor="rgba(231,76,60,0.06)", line_width=0)
    fig_long.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
    fig_long.add_annotation(x=0.01, y=0.95, xref="paper", yref="paper", text="ACELERANDO (pisa el gas)", showarrow=False, font=dict(size=12, color="#4CAF50"), xanchor="left")
    fig_long.add_annotation(x=0.01, y=0.05, xref="paper", yref="paper", text="FRENANDO (pisa el freno)", showarrow=False, font=dict(size=12, color="#E74C3C"), xanchor="left")

    fig_long.update_yaxes(range=[-6, 6], dtick=1)

    # Curvas + sectores en el eje X (mismo estilo que las demás gráficas por distancia)
    try:
        circuit_fisica = race.get_circuit_info()
        corners_fis = circuit_fisica.corners if circuit_fisica is not None else None
    except Exception:
        corners_fis = None
    sector_cuts_fis = None
    try:
        _ref_fis = selected_abbr[0]
        _lap_fis, _ = get_selected_lap(laps, _ref_fis, lap_mode, target_lap)
        _tel_fis = get_cached_telemetry(laps, _ref_fis, lap_mode, target_lap)
        if _lap_fis is not None and _tel_fis is not None:
            sector_cuts_fis, _ = _get_sector_cut_distances(_lap_fis, _tel_fis)
    except Exception:
        sector_cuts_fis = None

    fig_long = make_god_chart(fig_long, "FUERZA G LONGITUDINAL", "G (fuerza sobre el piloto)", "Distancia (m)", 500)
    apply_distance_axis(fig_long, corners_fis, sector_cuts_fis)
    plot_wide(fig_long)

    glong_parts = []
    for name, v in glong_metrics.items():
        zone_txt = f" (a los {brake_zones[name]:.0f} m)" if name in brake_zones else ""
        glong_parts.append(f"{name}: frenada más fuerte {v['max_brake']:.1f}G{zone_txt}; aceleración máxima {v['max_accel']:.1f}G.")
    render_chart_guide(
        summary_text=" ".join(glong_parts) if glong_parts else None,
        how_to_read=(
            "- Piensa en esta gráfica como **el pie del piloto**: verde (arriba) = pisa el acelerador; rojo (abajo) = pisa el freno.\n"
            "- **1G** ≈ tu propio peso. Una frenada de **4-5G** = el piloto siente 4-5 veces su peso lanzándolo hacia adelante.\n"
            "- Los **triángulos** marcan la frenada más fuerte de cada uno; las líneas T1, T2… son las curvas para ubicar dónde ocurre.\n"
            "- **¿Quién frena más TARDE (su pico rojo empieza más cerca de la curva) y más FUERTE?** → gana tiempo en esa frenada.\n"
            "- La aceleración (verde) es más suave que la frenada: el motor empuja menos de lo que muerden los frenos. Normal ver +1/+2G arriba y −4/−5G abajo."
        )
    )

    st.divider()

    # 2) G-G PLOT (LATERAL vs LONGITUDINAL) CON CONTROLES AVANZADOS

    st.markdown("**G-G PLOT (MANIOBRAS LATERALES + LONGITUDINALES)**")

    tgt = st.selectbox("Piloto G-G:", selected_abbr, format_func=get_driver_name, key='gg')
    compare = st.checkbox("Comparar con otro piloto", value=False)
    cmp_driver = None
    if compare and len(selected_abbr) > 1:
        cmp_opts = [d for d in selected_abbr if d != tgt]
        cmp_driver = st.selectbox("Piloto B:", cmp_opts, format_func=get_driver_name)

    color_mode = st.selectbox("Modo color", ["Velocidad", "Delta vs referencia", "Throttle", "Brake"], index=0)
    ref_driver = None
    if color_mode == "Delta vs referencia":
        ref_driver = st.selectbox("Referencia", selected_abbr, format_func=get_driver_name, key='gg_ref')
    speed_min = st.slider("Filtro velocidad (km/h)", 0, 330, 100)
    show_envelope = st.toggle("Mostrar envolvente (envelope)", value=False)

    try:
        t_main = get_cached_telemetry(laps, tgt, lap_mode, target_lap)
        # No usar st.stop() aquí: detendría toda la app (incluida la pestaña REPLAY)
        gg_main = compute_gg_from_telemetry(t_main) if t_main is not None else None
        gg_ref = None

        if t_main is None:
            st.warning(f"Telemetría no disponible para {get_driver_name(tgt)}.")
        elif gg_main is None:
            st.warning(f"Datos insuficientes para {get_driver_name(tgt)} (menos de 15 muestras).")
        else:
            fig_gg = go.Figure()
            color_a = get_driver_color(tgt, laps)

            if ref_driver and ref_driver != tgt:
                t_ref = get_cached_telemetry(laps, ref_driver, lap_mode, target_lap)
                if t_ref is not None:
                    gg_ref = compute_gg_from_telemetry(t_ref)

            def _apply_filter(gg):
                mask = gg["speed_kmh"] >= speed_min
                for k in ("glat", "glong", "speed_kmh", "distance"):
                    gg[k] = gg[k][mask]
                if gg["gear"] is not None:
                    gg["gear"] = gg["gear"][mask]
                if gg["throttle"] is not None:
                    gg["throttle"] = gg["throttle"][mask]
                if gg["brake"] is not None:
                    gg["brake"] = gg["brake"][mask]
                return gg

            gg_main = _apply_filter(gg_main)

            def _build_hover(gg):
                hover = []
                for i in range(len(gg["glat"])):
                    gear_txt = f"<br>Marcha: {int(gg['gear'][i])}" if gg["gear"] is not None else ""
                    hover.append(
                        f"G Lat: {gg['glat'][i]:+.2f}<br>G Long: {gg['glong'][i]:+.2f}"
                        f"<br>Vel: {gg['speed_kmh'][i]:.0f} km/h"
                        f"{gear_txt}<br>Dist: {gg['distance'][i]:.0f} m"
                    )
                return hover

            if compare and cmp_driver:
                t_cmp = get_cached_telemetry(laps, cmp_driver, lap_mode, target_lap)
                gg_cmp = compute_gg_from_telemetry(t_cmp) if t_cmp is not None else None
                if gg_cmp:
                    gg_cmp = _apply_filter(gg_cmp)

                    hover_a = _build_hover(gg_main)
                    hover_b = _build_hover(gg_cmp)
                    color_b = get_driver_color(cmp_driver, laps)
                    color_a, color_b = maybe_adjust_if_same(color_a, color_b)

                    fig_gg.add_trace(go.Scatter(
                        x=gg_main["glat"], y=gg_main["glong"],
                        mode='markers',
                        marker=dict(size=5, color=color_a, opacity=0.55, line=dict(width=0)),
                        hovertext=hover_a, hoverinfo="text",
                        name=tgt
                    ))
                    fig_gg.add_trace(go.Scatter(
                        x=gg_cmp["glat"], y=gg_cmp["glong"],
                        mode='markers',
                        marker=dict(size=5, color=color_b, opacity=0.45, line=dict(width=0)),
                        hovertext=hover_b, hoverinfo="text",
                        name=cmp_driver
                    ))

                    if show_envelope:
                        env_a = build_gg_envelope(gg_main["glat"], gg_main["glong"])
                        env_b = build_gg_envelope(gg_cmp["glat"], gg_cmp["glong"])
                        if env_a:
                            fig_gg.add_trace(go.Scatter(
                                x=env_a[0], y=env_a[1],
                                mode='lines',
                                line=dict(color=color_a, width=2),
                                hoverinfo='skip',
                                showlegend=False
                            ))
                        if env_b:
                            fig_gg.add_trace(go.Scatter(
                                x=env_b[0], y=env_b[1],
                                mode='lines',
                                line=dict(color=color_b, width=2),
                                hoverinfo='skip',
                                showlegend=False
                            ))
                else:
                    st.warning(f"Datos insuficientes para {get_driver_name(cmp_driver)}.")
            else:
                hover = _build_hover(gg_main)
                color_vals = gg_main["speed_kmh"]
                color_title = "Vel (km/h)"

                if color_mode == "Throttle" and gg_main["throttle"] is not None:
                    color_vals = gg_main["throttle"]
                    color_title = "Throttle (%)"
                elif color_mode == "Brake" and gg_main["brake"] is not None:
                    color_vals = gg_main["brake"]
                    color_title = "Brake (%)"
                elif color_mode == "Delta vs referencia" and gg_ref:
                    ref_speed = np.interp(gg_main["distance"], gg_ref["distance"], gg_ref["speed_kmh"])
                    color_vals = gg_main["speed_kmh"] - ref_speed
                    color_title = "Δ Vel (km/h)"

                fig_gg.add_trace(go.Scatter(
                    x=gg_main["glat"], y=gg_main["glong"],
                    mode='markers',
                    marker=dict(
                        size=5,
                        color=color_vals,
                        colorscale='Viridis',
                        showscale=True,
                        colorbar=dict(title=color_title, thickness=12, len=0.7),
                        line=dict(width=0)
                    ),
                    hovertext=hover,
                    hoverinfo="text",
                    name=tgt
                ))

                if show_envelope:
                    env = build_gg_envelope(gg_main["glat"], gg_main["glong"])
                    if env:
                        fig_gg.add_trace(go.Scatter(
                            x=env[0], y=env[1],
                            mode='lines',
                            line=dict(color=color_a, width=2),
                            hoverinfo='skip',
                            showlegend=False
                        ))

            max_range = max(np.max(np.abs(gg_main["glat"])), np.max(np.abs(gg_main["glong"])), 4)
            max_range = min(max_range + 0.5, 6)

            shapes = []
            for g_ref in [1, 2, 3, 4]:
                shapes.append(dict(
                    type="circle",
                    xref="x", yref="y",
                    x0=-g_ref, y0=-g_ref,
                    x1=g_ref, y1=g_ref,
                    line=dict(color="rgba(255,255,255,0.15)", width=1, dash="dot"),
                    fillcolor="rgba(0,0,0,0)"
                ))

            fig_gg.update_layout(
                template="plotly_dark",
                title=dict(text=f"<b>G-G PLOT: {get_driver_name(tgt)}</b>", font=dict(size=20, color="white")),
                height=680,
                plot_bgcolor="rgba(0,0,0,0.4)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(
                    range=[-max_range, max_range],
                    title="<b>G Lateral</b>",
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.05)",
                    zeroline=True,
                    zerolinewidth=1,
                    zerolinecolor="rgba(255,255,255,0.25)",
                    showline=True,
                    linecolor="#333"
                ),
                yaxis=dict(
                    range=[-max_range, max_range],
                    title="<b>G Longitudinal</b>",
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.05)",
                    zeroline=True,
                    zerolinewidth=1,
                    zerolinecolor="rgba(255,255,255,0.25)",
                    showline=True,
                    linecolor="#333",
                    scaleanchor="x",
                    scaleratio=1
                ),
                hovermode="closest",
                shapes=shapes,
                font=dict(family="Roboto", color="#ccc")
            )

            col_plot, col_stats = st.columns([3, 1])
            with col_plot:
                gg_cfg = {
                    "displayModeBar": True,
                    "scrollZoom": False,  # evita zoom accidental con la ruedita
                    "doubleClick": "reset",
                    "modeBarButtonsToRemove": ["lasso2d", "select2d"]
                }
                st.plotly_chart(fig_gg, use_container_width=True, config=gg_cfg)
            with col_stats:
                st.markdown("**Métricas G-G**")
                st.metric("Max lateral G", f"{np.max(np.abs(gg_main['glat'])):.2f}")
                st.metric("Max frenada G", f"{abs(np.min(gg_main['glong'])):.2f}")
                st.metric("Max tracción G", f"{np.max(gg_main['glong']):.2f}")
                if compare and cmp_driver and 'gg_cmp' in locals() and gg_cmp:
                    st.markdown(f"<span style='color:{color_b}; font-weight:600;'>{cmp_driver}</span>", unsafe_allow_html=True)
                    st.metric("Max lateral G", f"{np.max(np.abs(gg_cmp['glat'])):.2f}")
                    st.metric("Max frenada G", f"{abs(np.min(gg_cmp['glong'])):.2f}")
                    st.metric("Max tracción G", f"{np.max(gg_cmp['glong']):.2f}")

            render_chart_guide(
                summary_text=(
                    f"{get_driver_name(tgt)}: hasta {np.max(np.abs(gg_main['glat'])):.1f}G laterales, "
                    f"{abs(np.min(gg_main['glong'])):.1f}G de frenada y {np.max(gg_main['glong']):.1f}G de tracción "
                    f"(vueltas con velocidad ≥ {speed_min} km/h)."
                ),
                how_to_read=(
                    "- **Eje X**: G lateral (fuerza en las curvas) · **Eje Y**: G longitudinal (arriba = acelera, abajo = frena).\n"
                    "- Cada punto es un instante de la vuelta; los **círculos punteados** marcan 1, 2, 3 y 4G de referencia.\n"
                    "- **¿Los puntos llegan más LEJOS del centro?** → ese piloto lleva el coche más al límite.\n"
                    "- **¿El contorno es amplio y redondeado** (frena y gira a la vez)? → aprovecha bien el agarre combinado, no solo frena en recto.\n"
                    "- Los G se estiman de posición y velocidad GPS: son una aproximación, no el sensor real del coche."
                )
            )

    except Exception as e:
        st.error(f"Error al generar G-G Plot: {str(e)}")

    # ── DESPLIEGUE DE ENERGÍA: aceleración longitudinal vs velocidad (ERS/clipping) ──
    st.divider()
    st.markdown("**DESPLIEGUE DE ENERGÍA: aceleración longitudinal vs velocidad (ERS / clipping)**")
    st.caption("Solo con el coche a **pleno acelerador, en recta y sin frenar**: cómo despliega (y se queda sin) energía a lo largo del rango de velocidad. Es el gran diferenciador técnico de 2026.")

    ers_mode = st.radio(
        "Modo",
        ["Pilotos en esta sesión (estrategia ERS por escudería)",
         "Un piloto en 2 circuitos (efecto del trazado / drag)"],
        key="ers_mode", horizontal=True
    )

    def _ers_points(_tel):
        _gg = compute_gg_from_telemetry(_tel)
        if _gg is None or _gg.get('throttle') is None or _gg.get('brake') is None:
            return None, None
        _spd = _gg['speed_kmh']; _gl = _gg['glong'] * 9.81
        _thr = _gg['throttle']; _brk = _gg['brake']
        _brk_n = _brk / 100.0 if np.nanmax(_brk) > 1.5 else _brk
        _mask = (_thr >= 95) & (_brk_n < 0.1) & (np.abs(_gg['glat']) < 0.5) & np.isfinite(_spd) & np.isfinite(_gl)
        if _mask.sum() < 8:
            return None, None
        return _spd[_mask], _gl[_mask]

    def _add_ers_series(_fig, _sx, _sy, _color, _name, _dash='solid'):
        _fig.add_trace(go.Scatter(
            x=_sx, y=_sy, mode='markers', name=_name, legendgroup=_name,
            marker=dict(color=_color, size=5, opacity=0.26), showlegend=False,
            hovertemplate=f"{_name}<br>%{{x:.0f}} km/h<br>%{{y:.2f}} m/s²<extra></extra>"
        ))
        _xs = np.linspace(float(np.nanmin(_sx)), float(np.nanmax(_sx)), 60)
        try:
            _deg = 2 if len(np.unique(np.round(_sx))) > 3 else 1
            _ys = np.polyval(np.polyfit(_sx, _sy, _deg), _xs)
            _fig.add_trace(go.Scatter(
                x=_xs, y=_ys, mode='lines', name=_name, legendgroup=_name,
                line=dict(color=_color, width=3.5, dash=_dash),
                hovertemplate=f"{_name} · tendencia<br>%{{x:.0f}} km/h<br>%{{y:.2f}} m/s²<extra></extra>"
            ))
            return float(_xs[-1]), float(_ys[-1])
        except Exception:
            return None, None

    fig_ers = go.Figure()
    ers_parts = []
    _any_ers = False

    if ers_mode.startswith("Pilotos"):
        for d in selected_abbr:
            try:
                t = get_cached_telemetry(laps, d, lap_mode, target_lap)
                if t is None:
                    continue
                sx, sy = _ers_points(t)
                if sx is None:
                    continue
                _any_ers = True
                _xe, _ye = _add_ers_series(fig_ers, sx, sy, get_neon_color(d), get_driver_name(d))
                if _ye is not None:
                    ers_parts.append(f"{d}: a ~{_xe:.0f} km/h su empuje cae a {_ye:+.1f} m/s².")
            except Exception:
                pass
    else:
        _erc1, _erc2 = st.columns(2)
        with _erc1:
            ers_ref = st.selectbox("Piloto", selected_abbr, format_func=get_driver_name, key="ers_ref_driver")
        _other_gps = [g for g in get_schedule(year) if g != gp]
        with _erc2:
            ers_gp_b = st.selectbox(f"Comparar {gp} vs:", _other_gps, key="ers_gp_b") if _other_gps else None
        st.caption(f"**Circuito A** = {gp} (sesión actual, línea sólida) · **Circuito B** = el que elijas (línea punteada blanca). Mismo piloto: compara cómo el trazado y el drag mueven el punto de clipping.")
        try:
            tA = get_cached_telemetry(laps, ers_ref, lap_mode, target_lap)
            sxA, syA = _ers_points(tA) if tA is not None else (None, None)
            if sxA is not None:
                _any_ers = True
                _add_ers_series(fig_ers, sxA, syA, get_neon_color(ers_ref), f"{ers_ref} · {gp}", 'solid')
        except Exception:
            pass
        if ers_gp_b:
            try:
                with st.spinner(f"Cargando {ers_gp_b}…"):
                    sess_b = load_session_data(year, ers_gp_b, session)
                if sess_b is None:
                    st.info(f"No se pudieron cargar los datos de {ers_gp_b}.")
                else:
                    lap_b, _ = get_selected_lap(sess_b.laps, ers_ref, lap_mode, target_lap)
                    if lap_b is None:
                        st.info(f"{ers_ref} no tiene vuelta válida en {ers_gp_b}.")
                    else:
                        sxB, syB = _ers_points(lap_b.get_telemetry().add_distance())
                        if sxB is not None:
                            _any_ers = True
                            _add_ers_series(fig_ers, sxB, syB, "#FFFFFF", f"{ers_ref} · {ers_gp_b}", 'dash')
                        else:
                            st.info(f"No hay muestras a pleno gas en recta para {ers_ref} en {ers_gp_b}.")
            except Exception as _e:
                st.info(f"No se pudo comparar con {ers_gp_b}: {_e}")

    if _any_ers:
        fig_ers.add_hline(y=0, line=dict(color="rgba(255,255,255,0.35)", width=1, dash="dot"))
        fig_ers = make_god_chart(fig_ers, "ACELERACIÓN LONGITUDINAL vs VELOCIDAD (pleno gas · recta)", "Aceleración (m/s²)", "Velocidad (km/h)", 480)
        fig_ers.update_layout(showlegend=True)
        plot_wide(fig_ers)
        render_chart_guide(
            summary_text=" ".join(ers_parts) if ers_parts else None,
            how_to_read=(
                "- Solo instantes **a fondo, en recta y sin frenar**: es **empuje puro** (motor + ERS) contra la resistencia del aire.\n"
                "- **Y > 0** = el coche aún acelera (desplegando energía). A más velocidad la aceleración baja sola (drag + límite de potencia).\n"
                "- **¿La línea de tendencia se aplana o cae hacia 0 ANTES de la punta?** → ahí hay **clipping**: la batería/ERS se agotó (el diferenciador de 2026).\n"
                "- **Modo pilotos**: comparas escuderías en la misma pista → distinto *harvesting* (baja velocidad) y *deployment* (alta velocidad).\n"
                "- **Modo 2 circuitos**: el mismo piloto en dos trazados → cómo la pista y el drag mueven el punto de clipping. Se estima de la velocidad GPS."
            )
        )
    else:
        st.info("No hay suficientes muestras a pleno acelerador en recta para este análisis (prueba con una vuelta rápida).")

    # ── FASES DE CONDUCCIÓN: cómo se reparte la vuelta ──
    st.divider()
    st.markdown("**FASES DE CONDUCCIÓN: cómo se reparte la vuelta (a fondo / parcial / frenada / neutro)**")
    st.caption("Qué porcentaje del tiempo de la vuelta pasa cada piloto a pleno acelerador, con gas parcial, frenando, o sin gas ni freno (neutro/coasting).")

    phase_rows = []
    _PHASES = [("A fondo", "#00E676"), ("Parcial", "#F2C94C"), ("Frenada", "#FF5252"), ("Neutro", "#7A8290")]
    for d in selected_abbr:
        try:
            t = get_cached_telemetry(laps, d, lap_mode, target_lap)
            if t is None or 'Throttle' not in t.columns or 'Brake' not in t.columns:
                continue
            tt = t.dropna(subset=['Throttle', 'Brake', 'Time']).copy()
            if tt.empty:
                continue
            dt = tt['Time'].dt.total_seconds().diff().fillna(0).clip(lower=0).values
            thr = tt['Throttle'].astype(float).values
            _brk = tt['Brake']
            brk = _brk.astype(float).values
            brk_n = brk / 100.0 if np.nanmax(brk) > 1.5 else brk
            braking = brk_n > 0.05
            full = (~braking) & (thr >= 95)
            partial = (~braking) & (thr > 2) & (thr < 95)
            neutral = (~braking) & (thr <= 2)
            total = dt.sum() or 1.0
            phase_rows.append((d, {
                "A fondo": dt[full].sum() / total * 100.0,
                "Parcial": dt[partial].sum() / total * 100.0,
                "Frenada": dt[braking].sum() / total * 100.0,
                "Neutro": dt[neutral].sum() / total * 100.0,
            }))
        except Exception:
            pass

    if phase_rows:
        fig_ph = go.Figure()
        _pnames = [get_driver_name(d) for d, _ in phase_rows]
        for label, pcolor in _PHASES:
            _xvals = [p[label] for _, p in phase_rows]
            fig_ph.add_trace(go.Bar(
                y=_pnames, x=_xvals, name=label,
                orientation='h', marker=dict(color=pcolor),
                text=[f"{v:.0f}%" if v >= 6 else "" for v in _xvals],
                textposition='inside', insidetextanchor='middle',
                textfont=dict(color="#0e1117", size=12, family="Roboto"),
                hovertemplate="%{y}<br>" + label + ": %{x:.1f}%<extra></extra>"
            ))
        fig_ph = make_god_chart(fig_ph, "FASES DE CONDUCCIÓN (% del tiempo de vuelta)", "", "% del tiempo", 130 + 50 * len(phase_rows))
        fig_ph.update_layout(
            barmode='stack', margin=dict(l=120, r=20, t=78, b=42),
            legend=dict(orientation="h", y=1.22, x=0.5, xanchor="center", yanchor="bottom", font=dict(size=11))
        )
        fig_ph.update_xaxes(range=[0, 100], ticksuffix="%")
        st.plotly_chart(fig_ph, use_container_width=True, config={"displayModeBar": False})
        _fmax = max(phase_rows, key=lambda r: r[1]["A fondo"])
        render_chart_guide(
            summary_text=f"{get_driver_name(_fmax[0])} es quien más tiempo pasa a fondo en esta vuelta ({_fmax[1]['A fondo']:.0f}% del tiempo).",
            how_to_read=(
                "- **Verde (A fondo)**: acelerador ≥95% sin frenar · **Amarillo (Parcial)**: gas intermedio · **Rojo (Frenada)**: pisando el freno · **Gris (Neutro)**: ni gas ni freno (coasting).\n"
                "- Cada barra suma 100% del **tiempo** de la vuelta (ponderado por el tiempo real, no por número de puntos).\n"
                "- **¿Más verde?** → circuito de rectas o piloto más decidido a la salida. **¿Más amarillo?** → curvas rápidas donde se modula el gas.\n"
                "- **¿Mucho gris?** → gestión (lift-and-coast) o una vuelta no del todo al límite."
            )
        )
    else:
        st.info("No hay datos de acelerador/freno para las fases de conducción.")

# --- TAB 6: REPLAY ---

with tabs[5]:
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
                template="plotly_dark",
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
