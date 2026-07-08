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
from app.views import (panorama as view_panorama, telemetria as view_telemetria,
                       vs_vueltas as view_vs_vueltas, carrera as view_carrera,
                       fisica as view_fisica, replay as view_replay,
                       historico as view_historico)


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

tabs = st.tabs(["PANORAMA", "TELEMETRÍA", "VS VUELTAS", "CARRERA", "FÍSICA", "REPLAY", "HISTÓRICO"])

# --- TAB 1: PANORAMA ---

with tabs[0]:
    view_panorama.render(globals())

with tabs[1]:
    view_telemetria.render(globals())

with tabs[2]:
    view_vs_vueltas.render(globals())

with tabs[3]:
    view_carrera.render(globals())

with tabs[4]:
    view_fisica.render(globals())

with tabs[5]:
    view_replay.render(globals())

with tabs[6]:
    view_historico.render(globals())

