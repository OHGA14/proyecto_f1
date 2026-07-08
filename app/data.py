"""Acceso a datos con caché de Streamlit: sesiones FastF1, calendario, puntos."""
import os

import pandas as pd
import numpy as np
import fastf1 as ff1
import streamlit as st

from f1core.laps import get_selected_lap, _is_valid_lap

os.makedirs('cache.nosync', exist_ok=True)


def get_cached_telemetry(laps_df, driver, mode="Vuelta Rápida", lap_number=None):
    """Obtiene telemetría cacheada en session_state para evitar re-cargas.
    Respeta el modo de vuelta seleccionado en el sidebar."""
    cache_key = f"tel_{driver}_{mode}_{lap_number}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    try:
        lap, _ = get_selected_lap(laps_df, driver, mode, lap_number)
        if lap is None:
            return None
        tel = lap.get_telemetry().add_distance()
        st.session_state[cache_key] = tel
        return tel
    except Exception:
        return None

@st.cache_resource
def load_session_data(year, gp, session):

    ff1.Cache.enable_cache('cache.nosync')

    try:

        s = ff1.get_session(year, gp, session)

        s.load(telemetry=True, weather=True, messages=True)

    except Exception:
        return None

    # Auto-sincronización con la base histórica (DuckDB): cada sesión que se
    # carga en el dashboard queda registrada sin pasos manuales. Idempotente
    # (~1 s); si la base está ocupada o falla, el dashboard sigue normal.
    try:
        from f1core import db as _db
        _con = _db.connect()
        _db.ingest_session(_con, s)
        _con.close()
    except Exception:
        pass

    return s

@st.cache_data(show_spinner=False)
def get_lap_phase_stats(year, gp, session, driver, lap_mode, target_lap):
    """(% a fondo, % frenada, % en curva) de la vuelta seleccionada del piloto,
    ponderado por el TIEMPO real entre muestras. A fondo = throttle ≥ 98 sin
    frenar; Frenada = pisando freno; Curva = el resto (gas parcial/coasting).
    Cacheado por piloto para no recalcular en cada rerun."""
    try:
        sess = load_session_data(year, gp, session)
        if sess is None:
            return None
        lp, _ = get_selected_lap(sess.laps, driver, lap_mode, target_lap)
        if lp is None:
            return None
        car = lp.get_car_data()
        if car is None or car.empty or 'Throttle' not in car.columns or 'Brake' not in car.columns:
            return None
        c = car.dropna(subset=['Throttle', 'Brake', 'Time'])
        if c.empty:
            return None
        dt = c['Time'].dt.total_seconds().diff().fillna(0).clip(lower=0).values
        thr = c['Throttle'].astype(float).values
        brk = c['Brake'].astype(float).values
        brk_n = brk / 100.0 if np.nanmax(brk) > 1.5 else brk
        total = dt.sum() or 1.0
        braking = brk_n > 0.05
        full = (~braking) & (thr >= 98)
        corner = (~braking) & (~full)
        return (
            float(dt[full].sum() / total * 100.0),
            float(dt[braking].sum() / total * 100.0),
            float(dt[corner].sum() / total * 100.0),
        )
    except Exception:
        return None

@st.cache_data

def get_schedule(year):
    """Devuelve los GP cuyo fin de semana YA EMPEZÓ (al menos una sesión disputada),
    no todo el calendario. Así un GP aparece en cuanto corre FP1/Qualy, aunque la
    carrera aún no se haya disputado."""

    ff1.Cache.enable_cache('cache.nosync')

    try:

        s = ff1.get_event_schedule(year)

        s = s[s['EventFormat'] != 'testing']

        # Fecha de INICIO del fin de semana = primera sesión disponible del evento.
        session_date_cols = [c for c in s.columns if c.startswith('Session') and c.endswith('DateUtc')]
        if not session_date_cols:
            session_date_cols = [c for c in s.columns if c.startswith('Session') and c.endswith('Date')]

        now_utc = pd.Timestamp.now(tz='UTC')

        def _weekend_started(row):
            starts = []
            for c in session_date_cols:
                d = pd.to_datetime(row.get(c), errors='coerce', utc=True)
                if pd.notna(d):
                    starts.append(d)
            if not starts:
                d = pd.to_datetime(row.get('EventDate'), errors='coerce', utc=True)
                if pd.notna(d):
                    starts.append(d)
            return bool(starts) and min(starts) <= now_utc

        if session_date_cols or 'EventDate' in s.columns:
            mask = s.apply(_weekend_started, axis=1)
            past = s[mask]
            if not past.empty:
                s = past

        return s['EventName'].tolist()

    except: return ["Las Vegas Grand Prix"]

@st.cache_data
def get_event_sessions(year, gp):
    """Sesiones REALES de ese GP. Varía según el formato:
      - normal:  Practice 1/2/3, Qualifying, Race
      - sprint:  Practice 1, Sprint Qualifying, Sprint, Qualifying, Race
    Devuelve los nombres tal cual los acepta FastF1 (get_session(year, gp, nombre))."""
    ff1.Cache.enable_cache('cache.nosync')
    try:
        sched = ff1.get_event_schedule(year)
        row = sched[sched['EventName'] == gp]
        if row.empty:
            return []
        row = row.iloc[0]
        out = []
        for i in range(1, 6):
            name = row.get(f'Session{i}')
            if isinstance(name, str) and name.strip() and name.strip().lower() != 'none':
                out.append(name.strip())
        return out
    except Exception:
        return []

@st.cache_data(show_spinner=False)
def get_championship_points(year, round_no):
    """Puntos del campeonato de PILOTOS a la altura de esta ronda (vía Ergast).
    Devuelve (dict {codigo_piloto: puntos}, ronda_efectiva). Prueba la ronda
    actual (standings ya con esta carrera) y, si no hay, la anterior (standings
    de entrada). Si no hay datos (temporada futura / sin conexión), ({}, None)."""
    try:
        from fastf1.ergast import Ergast
        e = Ergast()
    except Exception:
        return {}, None
    try:
        round_no = int(round_no)
    except Exception:
        return {}, None
    for r in [round_no, round_no - 1]:
        if r < 1:
            continue
        try:
            resp = e.get_driver_standings(season=int(year), round=r)
            df = resp.content[0] if getattr(resp, 'content', None) else None
            if df is not None and not df.empty and 'driverCode' in df.columns:
                pts = {str(row['driverCode']): float(row['points']) for _, row in df.iterrows()}
                if pts:
                    return pts, r
        except Exception:
            continue
    return {}, None
