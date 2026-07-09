"""Telemetría bajo demanda para la web: carga sesiones FastF1 en memoria
(en un hilo, con estado consultable) y sirve el análisis de vuelta rápida
como JSON reutilizando la física de f1core.

La primera carga de una sesión tarda ~40-90 s (FastF1); después queda en
memoria (máx. 2 sesiones, se desaloja la más vieja). El análisis por piloto
se cachea por (sesión, piloto).
"""
import os
import re
import threading
import time

import numpy as np
import fastf1 as ff1

from f1core.laps import get_selected_lap
from f1core.physics import compute_gg_from_telemetry
from f1core.timeutils import _get_sector_cut_distances
from api.queries import driver_colors, driver_name, fmt_lap

CACHE_DIR = "cache.nosync"
_LOCK = threading.Lock()
_SESSIONS = {}      # sid -> {status, session, error, ts}
_TEL_CACHE = {}     # (sid, code) -> canal dict por piloto
_MAX_LOADED = 2
_N_POINTS = 700     # puntos por canal enviados a la web
_N_MINISECTORS = 28


def session_id(year, gp, session_name):
    return f"{year}|{gp}|{session_name}"


# ────────────────────────────────────────────── catálogo y ciclo de carga

def catalog():
    """Sesiones disponibles en la caché de FastF1 (carga rápida, sin red)."""
    out = []
    if not os.path.isdir(CACHE_DIR):
        return out
    for year in sorted(os.listdir(CACHE_DIR), reverse=True):
        ydir = os.path.join(CACHE_DIR, year)
        if not (year.isdigit() and os.path.isdir(ydir)):
            continue
        for evdir in sorted(os.listdir(ydir)):
            m = re.match(r"\d{4}-\d{2}-\d{2}_(.+)", evdir)
            if not m:
                continue
            gp = m.group(1).replace("_", " ")
            for sesdir in sorted(os.listdir(os.path.join(ydir, evdir))):
                sm = re.match(r"\d{4}-\d{2}-\d{2}_(.+)", sesdir)
                if not sm:
                    continue
                full = os.path.join(ydir, evdir, sesdir)
                if not os.path.exists(os.path.join(full, "car_data.ff1pkl")):
                    continue  # sin telemetría descargada no hay análisis
                ses = sm.group(1).replace("_", " ")
                sid = session_id(int(year), gp, ses)
                st = _SESSIONS.get(sid, {}).get("status")
                out.append({"sid": sid, "year": int(year), "gp": gp,
                            "session": ses, "status": st or "cold"})
    return out


def start_load(year, gp, session_name):
    sid = session_id(year, gp, session_name)
    with _LOCK:
        ent = _SESSIONS.get(sid)
        if ent and ent["status"] in ("loading", "ready"):
            return {"sid": sid, "status": ent["status"]}
        _SESSIONS[sid] = {"status": "loading", "session": None,
                          "error": None, "ts": time.time()}
    threading.Thread(target=_load_worker, daemon=True,
                     args=(sid, year, gp, session_name)).start()
    return {"sid": sid, "status": "loading"}


def _load_worker(sid, year, gp, session_name):
    try:
        ff1.Cache.enable_cache(CACHE_DIR)
        s = ff1.get_session(year, gp, session_name)
        s.load()
        try:  # auto-ingesta a DuckDB: el histórico se alimenta también desde la web
            from f1core import db
            con = db.connect()
            db.ingest_session(con, s)
            con.close()
        except Exception:
            pass
        with _LOCK:
            _SESSIONS[sid].update(status="ready", session=s, ts=time.time())
            _evict_locked()
    except Exception as e:
        with _LOCK:
            _SESSIONS[sid].update(status="error",
                                  error=f"{type(e).__name__}: {e}")


def _evict_locked():
    ready = [k for k, v in _SESSIONS.items() if v["status"] == "ready"]
    while len(ready) > _MAX_LOADED:
        old = min(ready, key=lambda k: _SESSIONS[k]["ts"])
        del _SESSIONS[old]
        ready.remove(old)
        for key in [k for k in _TEL_CACHE if k[0] == old]:
            del _TEL_CACHE[key]


def status(sid):
    ent = _SESSIONS.get(sid)
    if not ent:
        return {"sid": sid, "status": "cold"}
    return {"sid": sid, "status": ent["status"], "error": ent["error"]}


def _ready_session(sid):
    ent = _SESSIONS.get(sid)
    if not ent or ent["status"] != "ready":
        return None
    return ent["session"]


# ────────────────────────────────────────────── helpers puros (testeables)

def _delta_series(d_ref, t_ref, d_b, t_b):
    """Delta de tiempo de B respecto a la referencia sobre la malla de la
    referencia. Positivo = B va por detrás (ref más rápido hasta ese punto)."""
    d_max = min(d_ref[-1], d_b[-1])
    mask = d_ref <= d_max
    t_b_on_ref = np.interp(d_ref[mask], d_b, t_b)
    return d_ref[mask], t_b_on_ref - t_ref[mask]


def _phase_pcts(throttle, brake, dt):
    """(% a fondo, % frenada, % en curva) ponderado por tiempo real."""
    total = float(dt.sum())
    if total <= 0:
        return 0.0, 0.0, 0.0
    th = np.asarray(throttle, dtype=float)
    br = np.asarray(brake, dtype=float)
    fondo = float(dt[(th >= 98) & (br < 0.05)].sum()) / total * 100
    frenada = float(dt[br >= 0.05].sum()) / total * 100
    return round(fondo, 1), round(frenada, 1), round(100 - fondo - frenada, 1)


def _downsample(arr, step, nd=None):
    a = np.asarray(arr)[::step]
    if nd is not None:
        a = np.round(a, nd)
    return a.tolist()


# ────────────────────────────────────────────── análisis de vuelta rápida

def _driver_channels(sid, code):
    """Canales de la vuelta rápida de un piloto (cacheado). None si no hay."""
    key = (sid, code)
    if key in _TEL_CACHE:
        return _TEL_CACHE[key]
    s = _ready_session(sid)
    lap, _why = get_selected_lap(s.laps, code, "Vuelta Rápida")
    if lap is None:
        return None
    tel = lap.get_telemetry().add_distance()
    gg = compute_gg_from_telemetry(tel)
    if gg is None:
        return None
    d = np.asarray(gg["distance"], dtype=float)
    v_ms = np.maximum(np.asarray(gg["speed_kmh"], dtype=float) / 3.6, 0.1)
    dd = np.diff(d, prepend=float(d[0]))
    dd[0] = 0.0
    dt = dd / v_ms
    t_cum = np.cumsum(dt)
    x = np.interp(d, tel["Distance"], tel["X"])
    y = np.interp(d, tel["Distance"], tel["Y"])
    lt = lap["LapTime"].total_seconds() if lap["LapTime"] is not None else None
    cuts, _approx = _get_sector_cut_distances(lap, tel)
    out = {
        "d": d, "t": t_cum, "dt": dt, "x": x, "y": y,
        "speed": gg["speed_kmh"], "throttle": gg["throttle"],
        "brake": gg["brake"], "gear": gg["gear"],
        "glat": gg["glat"], "glong": gg["glong"],
        "lap_time": lt, "lap_number": int(lap["LapNumber"]),
        "cuts": list(cuts) if cuts else [],
    }
    _TEL_CACHE[key] = out
    return out


def available_drivers(sid):
    s = _ready_session(sid)
    if s is None:
        return None
    laps = s.laps
    codes = sorted(laps["Driver"].dropna().unique().tolist())
    team_of = {}
    for c in codes:
        sub = laps[laps["Driver"] == c]
        team_of[c] = str(sub.iloc[0].get("Team", "")) if not sub.empty else ""
    # orden: mejor vuelta ascendente (los rápidos primero)
    best = laps.groupby("Driver")["LapTime"].min()
    codes.sort(key=lambda c: (best.get(c) is None,
                              best.get(c).total_seconds() if best.get(c) is not None else 9e9))
    cols = driver_colors([(c, team_of[c]) for c in codes])
    return [{"code": c, "name": driver_name(c), "team": team_of[c],
             "color": cols[c]} for c in codes]


def analysis(sid, codes=None):
    s = _ready_session(sid)
    if s is None:
        return None
    disponibles = available_drivers(sid)
    if not disponibles:
        return None
    if not codes:
        codes = [d["code"] for d in disponibles[:2]]
    colores = {d["code"]: d["color"] for d in disponibles}

    chan = {}
    for c in codes:
        ch = _driver_channels(sid, c)
        if ch is not None:
            chan[c] = ch
    if not chan:
        return {"available": disponibles, "drivers": [], "summaries": {}}
    codes = [c for c in codes if c in chan]
    ref = codes[0]
    ch_ref = chan[ref]
    step = max(1, len(ch_ref["d"]) // _N_POINTS)

    # circuito: curvas (número + distancia + XY) y cortes de sector de la ref
    corners = []
    try:
        ci = s.get_circuit_info()
        for _, r in ci.corners.iterrows():
            corners.append({"n": int(r["Number"]), "d": float(r["Distance"]),
                            "x": float(r["X"]), "y": float(r["Y"])})
    except Exception:
        pass

    drivers = []
    for c in codes:
        ch = chan[c]
        st = max(1, len(ch["d"]) // _N_POINTS)
        item = {
            "code": c, "name": driver_name(c), "color": colores.get(c, "#9aa0aa"),
            "lap_time": ch["lap_time"], "lap_label": fmt_lap(ch["lap_time"]),
            "lap_number": ch["lap_number"],
            "d": _downsample(ch["d"], st, 1),
            "speed": _downsample(ch["speed"], st, 1),
            "throttle": _downsample(ch["throttle"], st, 1),
            "brake": _downsample(np.asarray(ch["brake"], dtype=float) * 100, st, 0),
            "gear": _downsample(ch["gear"], st),
            "glat": _downsample(ch["glat"], st, 3),
            "glong": _downsample(ch["glong"], st, 3),
            "vmax": float(np.max(ch["speed"])),
        }
        f, fr, cu = _phase_pcts(ch["throttle"], ch["brake"], ch["dt"])
        item["phases"] = {"fondo": f, "frenada": fr, "curva": cu}
        if c != ref:
            dx, dv = _delta_series(ch_ref["d"], ch_ref["t"], ch["d"], ch["t"])
            item["delta_d"] = _downsample(dx, step, 1)
            item["delta"] = _downsample(dv, step, 3)
        drivers.append(item)

    # mapa de dominancia: la línea de la ref pintada por el más rápido por tramo
    d_total = float(ch_ref["d"][-1])
    bounds = np.linspace(0, d_total, _N_MINISECTORS + 1)
    segments = []
    for i in range(_N_MINISECTORS):
        d0, d1 = bounds[i], bounds[i + 1]
        best_c, best_t = None, None
        for c in codes:
            ch = chan[c]
            tt = np.interp([d0, d1], ch["d"], ch["t"])
            dtse = float(tt[1] - tt[0])
            if best_t is None or dtse < best_t:
                best_c, best_t = c, dtse
        m = (ch_ref["d"] >= d0) & (ch_ref["d"] <= d1 + 1)
        segments.append({"x": _downsample(ch_ref["x"][m], 2, 0),
                         "y": _downsample(ch_ref["y"][m], 2, 0),
                         "code": best_c, "color": colores.get(best_c, "#9aa0aa")})
    dom_counts = {}
    for seg in segments:
        dom_counts[seg["code"]] = dom_counts.get(seg["code"], 0) + 1

    # resúmenes calculados (firma de la casa)
    summaries = {}
    rapido = min(drivers, key=lambda d: d["lap_time"] or 9e9)
    summaries["speed"] = (f"Vuelta más rápida: {rapido['lap_label']} de "
                          f"{rapido['code']} (V{rapido['lap_number']}). "
                          f"V. máx: " + " · ".join(f"{d['code']} {d['vmax']:.0f} km/h"
                                                   for d in drivers) + ".")
    if len(drivers) > 1 and drivers[1].get("delta") is not None:
        fin = drivers[1]["delta"][-1]
        quien = ref if fin > 0 else drivers[1]["code"]
        summaries["delta"] = (f"Al final de la vuelta, {quien} queda delante por "
                              f"{abs(fin):.3f}s. Recuerda: línea hacia abajo = "
                              f"ese piloto gana tiempo a {ref}.")
    lider_dom = max(dom_counts, key=dom_counts.get)
    summaries["map"] = (f"{lider_dom} domina {dom_counts[lider_dom]} de "
                        f"{_N_MINISECTORS} mini-sectores del trazado.")
    fondos = " · ".join(f"{d['code']} {d['phases']['fondo']:.0f}%" for d in drivers)
    summaries["phases"] = f"% de la vuelta a fondo: {fondos}."

    return {"available": disponibles, "ref": ref, "drivers": drivers,
            "corners": corners, "cuts": ch_ref["cuts"], "segments": segments,
            "summaries": summaries,
            "info": {"sid": sid, "total_m": round(d_total)}}
