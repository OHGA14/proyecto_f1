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
from f1core.physics import compute_gg_from_telemetry, build_gg_envelope, _dtw_distance
from f1core.timeutils import _get_sector_cut_distances
from api.queries import driver_colors, driver_name, fmt_lap, COMPOUND_DISPLAY

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

def _lap_channels(sid, code, lap_number=None):
    """Canales de una vuelta de un piloto (rápida si lap_number=None). Cacheado."""
    key = (sid, code, lap_number)
    if key in _TEL_CACHE:
        return _TEL_CACHE[key]
    s = _ready_session(sid)
    mode = "Vuelta Rápida" if lap_number is None else "manual"
    lap, _why = get_selected_lap(s.laps, code, mode, lap_number)
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
    # cuts llega como [("S1", d1), ("S2", d2), ("S3", fin)] → solo las 2 fronteras
    cut_ds = [float(c[1]) for c in cuts[:2]] if cuts else []
    out = {
        "d": d, "t": t_cum, "dt": dt, "x": x, "y": y,
        "speed": gg["speed_kmh"], "throttle": gg["throttle"],
        "brake": gg["brake"], "gear": gg["gear"],
        "glat": gg["glat"], "glong": gg["glong"],
        "lap_time": lt, "lap_number": int(lap["LapNumber"]),
        "cuts": cut_ds,
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
    # orden: POSICIÓN FINAL de la sesión (carrera/qualy); vuelta rápida
    # solo como respaldo (prácticas sin clasificación)
    best = laps.groupby("Driver")["LapTime"].min()
    pos_of = {}
    try:
        res = s.results
        if res is not None and len(res):
            for _, r in res.iterrows():
                p = r.get("Position")
                if p is not None and p == p:
                    pos_of[str(r["Abbreviation"])] = float(p)
    except Exception:
        pass
    codes.sort(key=lambda c: (pos_of.get(c, 999),
                              best.get(c).total_seconds()
                              if best.get(c) is not None else 9e9))
    cols = driver_colors([(c, team_of[c]) for c in codes])
    return [{"code": c, "name": driver_name(c), "team": team_of[c],
             "color": cols[c],
             "pos": int(pos_of[c]) if c in pos_of else None} for c in codes]


def laps_of(sid, code):
    """Vueltas válidas de un piloto en la sesión (para el modo VS VUELTAS)."""
    s = _ready_session(sid)
    if s is None:
        return None
    sub = s.laps.pick_driver(code)
    out = []
    best = None
    for _, r in sub.iterrows():
        lt = r["LapTime"]
        if lt is None or lt != lt:
            continue
        secs = lt.total_seconds()
        out.append({"lap": int(r["LapNumber"]), "time_s": round(secs, 3),
                    "label": f"V{int(r['LapNumber'])} — {fmt_lap(secs)}"})
        if best is None or secs < best[1]:
            best = (int(r["LapNumber"]), secs)
    for o in out:
        o["fastest"] = best is not None and o["lap"] == best[0]
    return sorted(out, key=lambda o: o["lap"])


def analysis(sid, codes=None, lap=None):
    """Modo PILOTOS: vuelta rápida (o la vuelta `lap`) de cada piloto."""
    s = _ready_session(sid)
    if s is None:
        return None
    disponibles = available_drivers(sid)
    if not disponibles:
        return None
    if not codes:
        codes = [d["code"] for d in disponibles[:2]]
    colores = {d["code"]: d["color"] for d in disponibles}
    nombres = {d["code"]: d["name"] for d in disponibles}
    entries = []
    for c in codes:
        ch = _lap_channels(sid, c, lap)
        if ch is not None:
            entries.append({"key": c, "name": nombres.get(c, c),
                            "color": colores.get(c, "#9aa0aa"), "ch": ch})
    out = _assemble(s, entries)
    out["available"] = disponibles
    out["mode"] = "pilotos"
    return out


def vslaps(sid, code, lap_a, lap_b):
    """Modo VS VUELTAS: dos vueltas del MISMO piloto (A = color piloto, B = blanco)."""
    s = _ready_session(sid)
    if s is None:
        return None
    disponibles = available_drivers(sid)
    colores = {d["code"]: d["color"] for d in (disponibles or [])}
    entries = []
    for lp, col in ((lap_a, colores.get(code, "#FF2D2D")), (lap_b, "#FFFFFF")):
        ch = _lap_channels(sid, code, lp)
        if ch is not None:
            entries.append({"key": f"V{lp}", "name": f"{code} vuelta {lp}",
                            "color": col, "ch": ch})
    out = _assemble(s, entries)
    out["available"] = disponibles
    out["mode"] = "vueltas"
    out["driver"] = code
    return out


def _assemble(s, entries):
    """Arma la respuesta de análisis para N 'entradas' (pilotos o vueltas)."""
    if not entries:
        return {"drivers": [], "summaries": {}}
    ref = entries[0]
    ch_ref = ref["ch"]
    step = max(1, len(ch_ref["d"]) // _N_POINTS)

    # circuito: curvas (número + distancia + XY)
    corners = []
    try:
        ci = s.get_circuit_info()
        for _, r in ci.corners.iterrows():
            corners.append({"n": int(r["Number"]), "d": float(r["Distance"]),
                            "x": float(r["X"]), "y": float(r["Y"])})
    except Exception:
        pass

    drivers = []
    for e in entries:
        ch = e["ch"]
        st = max(1, len(ch["d"]) // _N_POINTS)
        item = {
            "code": e["key"], "name": e["name"], "color": e["color"],
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
            # posición y tiempo acumulado: alimentan el REPLAY en canvas
            "x": _downsample(ch["x"], st, 0),
            "y": _downsample(ch["y"], st, 0),
            "t": _downsample(ch["t"], st, 3),
        }
        f, fr, cu = _phase_pcts(ch["throttle"], ch["brake"], ch["dt"])
        item["phases"] = {"fondo": f, "frenada": fr, "curva": cu}
        # envolvente de agarre (percentil 95 por ángulo) + máximos
        env = build_gg_envelope(np.asarray(ch["glat"], dtype=float),
                                np.asarray(ch["glong"], dtype=float))
        if env is not None:
            item["env_x"] = [round(float(v), 3) for v in env[0]]
            item["env_y"] = [round(float(v), 3) for v in env[1]]
        item["g_lat_max"] = round(float(np.percentile(np.abs(ch["glat"]), 99.5)), 2)
        item["g_brake_max"] = round(float(-np.percentile(-np.asarray(ch["glong"]), 99.5)), 2)
        if e is not ref:
            dx, dv = _delta_series(ch_ref["d"], ch_ref["t"], ch["d"], ch["t"])
            item["delta_d"] = _downsample(dx, step, 1)
            item["delta"] = _downsample(dv, step, 3)
        drivers.append(item)

    colores = {e["key"]: e["color"] for e in entries}
    chans = {e["key"]: e["ch"] for e in entries}
    keys = [e["key"] for e in entries]

    # mapa de dominancia sobre la línea de la referencia
    d_total = float(ch_ref["d"][-1])
    bounds = np.linspace(0, d_total, _N_MINISECTORS + 1)
    segments = []
    for i in range(_N_MINISECTORS):
        d0, d1 = bounds[i], bounds[i + 1]
        # mejor Y segundo mejor tiempo del tramo → el margen dice POR CUÁNTO
        best_k, best_t, second_t = None, None, None
        for k in keys:
            ch = chans[k]
            tt = np.interp([d0, d1], ch["d"], ch["t"])
            dtse = float(tt[1] - tt[0])
            if best_t is None or dtse < best_t:
                second_t = best_t
                best_k, best_t = k, dtse
            elif second_t is None or dtse < second_t:
                second_t = dtse
        m = (ch_ref["d"] >= d0) & (ch_ref["d"] <= d1 + 1)
        segments.append({"x": _downsample(ch_ref["x"][m], 2, 0),
                         "y": _downsample(ch_ref["y"][m], 2, 0),
                         "code": best_k, "color": colores.get(best_k, "#9aa0aa"),
                         "n": i + 1, "d0": round(float(d0)), "d1": round(float(d1)),
                         "margin": (round(second_t - best_t, 3)
                                    if second_t is not None else None)})
    dom_counts = {}
    for seg in segments:
        dom_counts[seg["code"]] = dom_counts.get(seg["code"], 0) + 1

    # DTW: similitud de la forma de la vuelta vs la referencia
    dtw = []
    if len(entries) > 1:
        grid_max = min(float(e["ch"]["d"][-1]) for e in entries)
        grid = np.linspace(0.0, grid_max, 220)
        prof = {e["key"]: np.interp(grid, e["ch"]["d"], e["ch"]["speed"])
                for e in entries}
        for e in entries[1:]:
            cost, path = _dtw_distance(prof[ref["key"]], prof[e["key"]])
            if not path:
                continue
            media = cost / len(path)
            if media < 2:
                etiqueta = "casi idénticas"
            elif media < 5:
                etiqueta = "muy parecidas"
            elif media < 10:
                etiqueta = "parecidas"
            elif media < 18:
                etiqueta = "diferentes"
            else:
                etiqueta = "muy distintas"
            imax, jmax = max(path, key=lambda ij: abs(prof[ref["key"]][ij[0]]
                                                      - prof[e["key"]][ij[1]]))
            d_max = float(grid[imax])
            curva = min(corners, key=lambda c: abs(c["d"] - d_max))["n"] if corners else None
            dtw.append({"code": e["key"], "mean_kmh": round(media, 1),
                        "label": etiqueta, "corner": curva,
                        "at_m": round(d_max)})

    # micro-sectores estilo MultiViewer (morado/verde/amarillo)
    micro = None
    if len(entries) > 1:
        cuts = ch_ref.get("cuts") or []
        if len(cuts) >= 2:
            spans = [("S1", 0.0, float(cuts[0])), ("S2", float(cuts[0]), float(cuts[1])),
                     ("S3", float(cuts[1]), d_total)]
            per = 8
        else:
            spans = [("VUELTA", 0.0, d_total)]
            per = 24
        UMBRAL = 0.02
        wins = {k: 0 for k in keys}
        sectores = []
        for lbl, s0, s1 in spans:
            edges = np.linspace(s0, s1, per + 1)
            celdas = []
            for i in range(per):
                tiempos = {}
                for k in keys:
                    ch = chans[k]
                    tt = np.interp([edges[i], edges[i + 1]], ch["d"], ch["t"])
                    tiempos[k] = float(tt[1] - tt[0])
                orden = sorted(tiempos, key=tiempos.get)
                mejor, t_mejor = orden[0], tiempos[orden[0]]
                margen = tiempos[orden[1]] - t_mejor if len(orden) > 1 else 0.0
                cols, gaps = {}, {}
                for k in keys:
                    gap = tiempos[k] - t_mejor
                    gaps[k] = round(gap, 3)
                    if k == mejor:
                        cols[k] = "p" if margen > UMBRAL else "g"
                    else:
                        cols[k] = "g" if gap <= UMBRAL else "y"
                if cols[mejor] == "p":
                    wins[mejor] += 1
                celdas.append({"colors": cols, "gaps": gaps})
            tot = {k: float(np.interp(s1, chans[k]["d"], chans[k]["t"])
                            - np.interp(s0, chans[k]["d"], chans[k]["t"])) for k in keys}
            orden_s = sorted(tot, key=tot.get)
            margen_s = tot[orden_s[1]] - tot[orden_s[0]] if len(orden_s) > 1 else 0.0
            sectores.append({"label": lbl, "winner": orden_s[0],
                             "margin": round(margen_s, 3), "cells": celdas})
        micro = {"sectors": sectores, "wins": wins, "keys": keys}

    # sectores: tiempo por sector de cada entrada + ganador y margen
    sectors = []
    cuts = ch_ref.get("cuts") or []
    if len(cuts) >= 2:
        spans_s = [("S1", 0.0, cuts[0]), ("S2", cuts[0], cuts[1]),
                   ("S3", cuts[1], d_total)]
        for lbl, a, b in spans_s:
            tiempos = {}
            for k in keys:
                ch = chans[k]
                tt = np.interp([a, b], ch["d"], ch["t"])
                tiempos[k] = round(float(tt[1] - tt[0]), 3)
            orden_s = sorted(tiempos, key=tiempos.get)
            margen = (tiempos[orden_s[1]] - tiempos[orden_s[0]]) if len(orden_s) > 1 else 0.0
            sectors.append({"label": lbl, "d0": round(a), "d1": round(b),
                            "winner": orden_s[0], "margin": round(margen, 3),
                            "color": colores.get(orden_s[0], "#9aa0aa")})

    # zonas de alta velocidad de la referencia (>80% de su vmax, tramos >=5%)
    zones = []
    v = np.asarray(ch_ref["speed"], dtype=float)
    alto = v > 0.8 * float(v.max())
    i = 0
    while i < len(alto):
        if alto[i]:
            j = i
            while j < len(alto) and alto[j]:
                j += 1
            d0, d1 = float(ch_ref["d"][i]), float(ch_ref["d"][min(j, len(alto) - 1)])
            if (d1 - d0) >= 0.05 * d_total:
                zones.append({"d0": round(d0), "d1": round(d1)})
            i = j
        else:
            i += 1

    # resúmenes calculados (firma de la casa)
    summaries = {}
    rapido = min(drivers, key=lambda d: d["lap_time"] or 9e9)
    summaries["speed"] = (f"Vuelta más rápida: {rapido['lap_label']} de "
                          f"{rapido['code']} (V{rapido['lap_number']}). "
                          f"V. máx: " + " · ".join(f"{d['code']} {d['vmax']:.0f} km/h"
                                                   for d in drivers) + ".")
    if len(drivers) > 1 and drivers[1].get("delta") is not None:
        fin = drivers[1]["delta"][-1]
        quien = ref["key"] if fin > 0 else drivers[1]["code"]
        summaries["delta"] = (f"Al final de la vuelta, {quien} queda delante por "
                              f"{abs(fin):.3f}s. Recuerda: línea hacia abajo = "
                              f"gana tiempo a {ref['key']}.")
    lider_dom = max(dom_counts, key=dom_counts.get)
    summaries["map"] = (f"{lider_dom} domina {dom_counts[lider_dom]} de "
                        f"{_N_MINISECTORS} mini-sectores del trazado.")
    fondos = " · ".join(f"{d['code']} {d['phases']['fondo']:.0f}%" for d in drivers)
    summaries["phases"] = f"% de la vuelta a fondo: {fondos}."
    summaries["gg"] = ("Límites de la vuelta: " + " · ".join(
        f"{d['code']} apoya {d['g_lat_max']:.1f}G laterales y frena a {abs(d['g_brake_max']):.1f}G"
        for d in drivers) + ".")
    summaries["throttle"] = ("Gas medio en la vuelta: " + " · ".join(
        f"{e['key']} {float(np.mean(e['ch']['throttle'])):.0f}%" for e in entries) + ".")
    summaries["brake"] = ("Porcentaje de la vuelta frenando: " + " · ".join(
        f"{e['key']} {float(np.mean(np.asarray(e['ch']['brake'], dtype=float) > 0.05) * 100):.0f}%"
        for e in entries) + ".")
    if dtw:
        partes = "; ".join(f"{x['code']} difiere {x['mean_kmh']} km/h de media "
                           f"({x['label']}, máx. en curva {x['corner']})" for x in dtw)
        summaries["dtw"] = f"Similitud DTW vs {ref['key']}: {partes}."
    if micro:
        g = " · ".join(f"{k} {v}" for k, v in sorted(micro["wins"].items(),
                                                     key=lambda kv: -kv[1]))
        summaries["micro"] = f"Mini-sectores ganados (morado): {g}."

    return {"ref": ref["key"], "drivers": drivers, "corners": corners,
            "cuts": ch_ref.get("cuts") or [], "segments": segments,
            "dtw": dtw, "micro": micro, "sectors": sectors, "zones": zones,
            "summaries": summaries, "info": {"total_m": round(d_total)}}


# ────────────────────────────────────────────── estadísticas de sesión (RITMO)

def session_stats(sid):
    """Análisis de ritmo de TODA la sesión cargada (boxplot, CV, evolución,
    degradación por stint, parrilla→meta, heatmap de speed trap, tablero de
    qualy). Reproduce el bloque PANORAMA/CARRERA del laboratorio."""
    s = _ready_session(sid)
    if s is None:
        return None
    disponibles = available_drivers(sid)
    colores = {d["code"]: d["color"] for d in disponibles}
    orden = [d["code"] for d in disponibles]
    name = str(s.name)
    tipo = ("quali" if ("Qualifying" in name or "Shootout" in name)
            else "race" if name in ("Race", "Sprint") else "practice")

    df = s.laps.copy()
    df["t"] = df["LapTime"].dt.total_seconds()
    n_laps = int(df["LapNumber"].max()) if len(df) else 0

    box, cv, evo = [], [], []
    for code in orden:
        valid = df[(df["Driver"] == code) & df["t"].notna()]
        if valid.empty:
            continue
        t = valid["t"]
        q1, q3 = t.quantile(.25), t.quantile(.75)
        lim = q3 + 1.5 * (q3 - q1)
        pit = valid["PitInTime"].notna() | valid["PitOutTime"].notna()
        clean = valid[~pit & (valid["t"] <= lim)]["t"]
        if len(clean) < 2:
            clean = t[t <= lim]
        if clean.empty:
            continue
        box.append({"code": code, "color": colores.get(code),
                    "times": [round(float(x), 3) for x in clean]})
        med = float(clean.median())
        sig = float(clean.std()) if len(clean) > 1 else 0.0
        cv.append({"code": code, "color": colores.get(code),
                   "median": round(med, 3), "median_label": fmt_lap(med),
                   "sigma": round(sig, 3),
                   "iqr": round(float(clean.quantile(.75) - clean.quantile(.25)), 3),
                   "cv": round(sig / med * 100, 3) if med else 0.0,
                   "laps": int(len(clean))})
        pts = []
        for _, r in valid.iterrows():
            es_pit = (r["PitInTime"] == r["PitInTime"]) or (r["PitOutTime"] == r["PitOutTime"])
            pts.append({"lap": int(r["LapNumber"]), "t": round(float(r["t"]), 3),
                        "comp": str(r.get("Compound", "")).upper(),
                        "pit": bool(es_pit),
                        "out": bool(es_pit or r["t"] > lim)})
        evo.append({"code": code, "color": colores.get(code), "points": pts})

    # degradación por stint (pendiente s/vuelta sobre vueltas limpias)
    deg = []
    sub_all = df[df["t"].notna() & df["Stint"].notna()
                 & df["PitInTime"].isna() & df["PitOutTime"].isna()]
    for code in orden:
        for stint, g in sub_all[sub_all["Driver"] == code].groupby("Stint"):
            tq3 = g["t"].quantile(.75)
            lim = tq3 + 1.5 * (tq3 - g["t"].quantile(.25))
            g2 = g[g["t"] <= lim]
            if len(g2) < 5:
                continue
            slope = float(np.polyfit(g2["LapNumber"], g2["t"], 1)[0])
            if abs(slope) > 0.3:
                continue  # stint contaminado (SC/lluvia/paradas), no es degradación real
            comp = str(g2["Compound"].iloc[0]).upper()
            deg.append({"code": code, "color": colores.get(code), "stint": int(stint),
                        "compound": comp,
                        "comp_color": COMPOUND_DISPLAY.get(comp, "#6b7280"),
                        "laps": int(len(g2)),
                        "median": round(float(g2["t"].median()), 3),
                        "slope": round(slope, 4)})

    # parrilla → meta (solo carrera) y tablero de qualy
    gridfin, quali = [], None
    res = s.results if s.results is not None else None
    if res is not None and len(res):
        if tipo == "race":
            for _, r in res.iterrows():
                try:
                    gp, ps = float(r["GridPosition"]), float(r["Position"])
                except Exception:
                    continue
                if gp != gp or ps != ps or gp == 0:
                    continue
                code = str(r["Abbreviation"])
                gridfin.append({"code": code, "color": colores.get(code, "#9aa0aa"),
                                "grid": int(gp), "pos": int(ps), "delta": int(gp - ps)})
            gridfin.sort(key=lambda x: x["delta"], reverse=True)
        elif tipo == "quali":
            def _sec(v):
                try:
                    return v.total_seconds() if v == v and v is not None else None
                except Exception:
                    return None
            filas = []
            pole = None
            for _, r in res.sort_values("Position").iterrows():
                code = str(r["Abbreviation"])
                q1v, q2v, q3v = _sec(r.get("Q1")), _sec(r.get("Q2")), _sec(r.get("Q3"))
                if q3v is not None and (pole is None or q3v < pole):
                    pole = q3v
                corte = "Q3" if q3v is not None else ("Elim. Q2" if q2v is not None else "Elim. Q1")
                filas.append({"pos": int(r["Position"]) if r["Position"] == r["Position"] else None,
                              "code": code, "color": colores.get(code, "#9aa0aa"),
                              "q1": fmt_lap(q1v), "q2": fmt_lap(q2v), "q3": fmt_lap(q3v),
                              "q3_s": q3v, "corte": corte})
            for f in filas:
                f["gap"] = (f"+{f['q3_s'] - pole:.3f}" if f["q3_s"] is not None and pole is not None
                            and f["q3_s"] > pole else ("POLE" if f["q3_s"] == pole else "—"))
                del f["q3_s"]
            quali = filas

    # heatmap de speed trap (piloto × vuelta)
    trap = None
    if "SpeedST" in df.columns:
        stdf = df[df["SpeedST"].notna()]
        codes_t = [c for c in orden if c in set(stdf["Driver"])]
        if codes_t and n_laps > 1:
            lapsx = list(range(1, n_laps + 1))
            z = []
            for c in codes_t:
                m = stdf[stdf["Driver"] == c].set_index("LapNumber")["SpeedST"]
                z.append([float(m[lp]) if lp in m.index else None for lp in lapsx])
            trap = {"drivers": codes_t, "laps": lapsx, "z": z}

    # vueltas bajo SC/VSC (para sombrear la evolución y el lap chart)
    sc_ranges, run = [], []
    if "TrackStatus" in df.columns:
        mask = df["TrackStatus"].astype(str).str.contains("4|6|7", regex=True)
        for lp in sorted(df[mask]["LapNumber"].dropna().astype(int).unique().tolist()):
            if run and lp == run[-1] + 1:
                run.append(lp)
            else:
                if run:
                    sc_ranges.append([run[0], run[-1]])
                run = [lp]
        if run:
            sc_ranges.append([run[0], run[-1]])

    # stints completos (gantt de gestión de neumáticos)
    stints = []
    if "Stint" in df.columns:
        for (code, st), g in df[df["Stint"].notna()].groupby(["Driver", "Stint"]):
            comp = str(g["Compound"].iloc[0]).upper()
            stints.append({"code": str(code), "stint": int(st), "compound": comp,
                           "color": COMPOUND_DISPLAY.get(comp, "#6b7280"),
                           "from": int(g["LapNumber"].min()),
                           "to": int(g["LapNumber"].max())})

    # paradas: vuelta de entrada, goma nueva y tiempo perdido vs vueltas limpias
    pits_out = []
    med_por = {c["code"]: c["median"] for c in cv}
    for code in orden:
        segs = sorted([x for x in stints if x["code"] == code], key=lambda x: x["from"])
        if not segs:
            continue
        sub = df[df["Driver"] == code]
        stops = []
        for a, b in zip(segs, segs[1:]):
            lap_in = a["to"]
            t_in = sub[sub["LapNumber"] == lap_in]["t"]
            t_out = sub[sub["LapNumber"] == lap_in + 1]["t"]
            lost = None
            if (len(t_in) and len(t_out) and code in med_por
                    and t_in.notna().all() and t_out.notna().all()):
                lost = round(float(t_in.iloc[0] + t_out.iloc[0]) - 2 * med_por[code], 1)
                if lost < 0:
                    lost = None  # dato contaminado (SC comprimió los tiempos)
            stops.append({"lap": int(lap_in), "comp": b["compound"],
                          "color": b["color"], "lost": lost})
        con_dato = [x["lost"] for x in stops if x["lost"] is not None]
        pits_out.append({"code": code, "color": colores.get(code), "stops": stops,
                         "total_lost": round(sum(con_dato), 1) if con_dato else None})

    # posición vuelta a vuelta + gap al líder (carrera)
    positions, gaps = [], []
    if tipo == "race":
        if "Position" in df.columns:
            posdf = df[df["Position"].notna()]
            for code in orden:
                g = posdf[posdf["Driver"] == code].sort_values("LapNumber")
                if g.empty:
                    continue
                positions.append({"code": code, "color": colores.get(code),
                                  "laps": g["LapNumber"].astype(int).tolist(),
                                  "pos": g["Position"].astype(int).tolist()})
        piv = df[df["t"].notna()].pivot_table(index="LapNumber", columns="Driver",
                                              values="t", aggfunc="first")
        if len(piv):
            cum = piv.cumsum()
            lider = cum.min(axis=1)
            gapdf = cum.sub(lider, axis=0)
            for code in orden:
                if code not in gapdf.columns:
                    continue
                serie = gapdf[code].dropna()
                gaps.append({"code": code, "color": colores.get(code),
                             "laps": serie.index.astype(int).tolist(),
                             "gap": serie.round(2).tolist()})

    summaries = {}
    if cv:
        rapido = min(cv, key=lambda x: x["median"])
        consistente = min(cv, key=lambda x: x["cv"])
        summaries["ritmo"] = (f"Mejor ritmo mediano: {rapido['code']} "
                              f"({rapido['median_label']}). Más consistente: "
                              f"{consistente['code']} (CV {consistente['cv']:.2f}%). "
                              f"Ojo: el más rápido no siempre es el más regular.")
    if deg:
        peor = max(deg, key=lambda x: x["slope"])
        summaries["deg"] = (f"Mayor degradación: {peor['code']} en el stint "
                            f"{peor['stint']} ({peor['compound']}): "
                            f"+{peor['slope']*1000:.0f} ms por vuelta.")
    if gridfin:
        top = gridfin[0]
        if top["delta"] > 0:
            summaries["grid"] = (f"Mayor remontada: {top['code']} "
                                 f"(P{top['grid']} → P{top['pos']}, +{top['delta']}).")
    if trap:
        zmax, quien = 0.0, ""
        for i, c in enumerate(trap["drivers"]):
            fila = [v for v in trap["z"][i] if v]
            if fila and max(fila) > zmax:
                zmax, quien = max(fila), c
        summaries["trap"] = f"Récord del speed trap: {zmax:.0f} km/h de {quien}."
    if quali:
        summaries["quali"] = (f"Pole: {quali[0]['code']} ({quali[0]['q3']}). "
                              f"El tablero marca en qué ronda quedó eliminado cada piloto.")

    return {"type": tipo, "session": name, "n_laps": n_laps, "box": box,
            "cv": sorted(cv, key=lambda x: x["cv"]), "evo": evo, "deg": deg,
            "grid": gridfin, "quali": quali, "trap": trap,
            "sc_ranges": sc_ranges, "stints": stints, "pits": pits_out,
            "positions": positions, "gaps": gaps, "summaries": summaries}


def schedule(year):
    """Calendario del año (FastF1): GPs con sus sesiones, para los selectores."""
    ff1.Cache.enable_cache(CACHE_DIR)
    try:
        ev = ff1.get_event_schedule(year, include_testing=False)
    except Exception as e:
        return {"year": year, "events": [], "error": f"{type(e).__name__}: {e}"}
    cacheados = {c["sid"] for c in catalog()}
    events = []
    for _, r in ev.iterrows():
        gp = str(r["EventName"])
        sesiones = []
        for i in range(1, 6):
            nom = r.get(f"Session{i}")
            if nom is None or nom != nom or not str(nom).strip():
                continue
            nom = str(nom)
            sesiones.append({"session": nom,
                             "cached": session_id(year, gp, nom) in cacheados})
        if sesiones:
            events.append({"gp": gp, "round": int(r["RoundNumber"]),
                           "sessions": sesiones})
    return {"year": year, "events": events}
