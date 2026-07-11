"""Actualizador global: detecta las sesiones ya disputadas de la temporada que
faltan en DuckDB (Carrera / Qualy / Sprint), las descarga de FastF1 y las
ingesta — en un hilo, con progreso consultable. Idempotente: correrlo dos
veces no duplica nada.

Las prácticas se omiten a propósito: solo aportan a ANÁLISIS, que ya las
descarga bajo demanda.
"""
import datetime
import threading
import time

import pandas as pd
import fastf1 as ff1

from f1core import db

CACHE_DIR = "cache.nosync"
SESIONES_CLAVE = {"Race", "Sprint", "Qualifying", "Sprint Qualifying", "Sprint Shootout"}

_LOCK = threading.Lock()
_STATE = {"running": False, "log": [], "found": 0, "ok": 0, "fail": 0,
          "finished_at": None}


def _log(msg):
    _STATE["log"].append(msg)


def _pendientes(events, have_sids, now_utc):
    """Sesiones clave YA DISPUTADAS que faltan en la base. Pura y testeable.

    events: [{"year", "gp", "sessions": [{"name", "date_utc"}]}]
    """
    out = []
    for ev in events:
        for s in ev["sessions"]:
            if s["name"] not in SESIONES_CLAVE:
                continue
            if s["date_utc"] is None or s["date_utc"] >= now_utc:
                continue
            sid = f"{ev['year']}|{ev['gp']}|{s['name']}"
            if sid not in have_sids:
                out.append((ev["year"], ev["gp"], s["name"]))
    return out


def _leer_calendario(year):
    ff1.Cache.enable_cache(CACHE_DIR)
    cal = ff1.get_event_schedule(year, include_testing=False)
    events = []
    for _, r in cal.iterrows():
        sesiones = []
        for i in range(1, 6):
            nom = r.get(f"Session{i}")
            if nom is None or nom != nom or not str(nom).strip():
                continue
            fecha = r.get(f"Session{i}DateUtc")
            try:
                fecha = pd.Timestamp(fecha).to_pydatetime() if fecha == fecha else None
            except Exception:
                fecha = None
            sesiones.append({"name": str(nom), "date_utc": fecha})
        events.append({"year": year, "gp": str(r["EventName"]), "sessions": sesiones})
    return events


def _worker():
    try:
        year = datetime.date.today().year
        _log(f"Leyendo calendario {year}…")
        events = _leer_calendario(year)
        con = db.connect()
        have = {r[0] for r in con.execute("SELECT session_id FROM sessions").fetchall()}
        con.close()
        pend = _pendientes(events, have, datetime.datetime.utcnow())
        _STATE["found"] = len(pend)
        if not pend:
            _log("La base ya está al día.")
        for y, gp, name in pend:
            try:
                _log(f"Bajando {gp.replace(' Grand Prix', '')} · {name}…")
                s = ff1.get_session(y, gp, name)
                s.load(telemetry=False, weather=False, messages=False)
                # conexión CORTA por sesión: la web puede seguir leyendo
                # la base entre ingesta e ingesta (DuckDB = 1 escritor O lectores)
                con = db.connect()
                db.ingest_session(con, s)
                con.close()
                _STATE["ok"] += 1
                _log(f"Listo: {gp.replace(' Grand Prix', '')} · {name}")
            except Exception as e:
                _STATE["fail"] += 1
                _log(f"Falló {gp.replace(' Grand Prix', '')} · {name} ({type(e).__name__})")
    except Exception as e:
        _log(f"Error general: {type(e).__name__}: {e}")
    finally:
        _STATE["running"] = False
        _STATE["finished_at"] = time.time()


def start():
    with _LOCK:
        if _STATE["running"]:
            return status()
        _STATE.update(running=True, log=[], found=0, ok=0, fail=0, finished_at=None)
    threading.Thread(target=_worker, daemon=True).start()
    return status()


def status():
    return {k: _STATE[k] for k in ("running", "log", "found", "ok", "fail", "finished_at")}
