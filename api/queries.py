"""Consultas y formateo JSON para la API (lee DuckDB en solo-lectura por petición).

Los colores de display están VALIDADOS para fondo oscuro #11141b (banda de
luminosidad, croma, separación CVD y contraste 3:1) manteniendo la identidad
de cada equipo. Los tiempos siempre en segundos.
"""
import os

from f1core import db
from f1core.config import DRIVER_DB

DB_PATH = os.environ.get("F1_DB_PATH", db.DB_PATH)

# Paleta de display por equipo (validada, ver docstring). El 2º piloto de un
# equipo recibe la variante clara para no confundirse con su compañero.
TEAM_DISPLAY = [
    (("red bull",), "#5B8FD9"),
    (("ferrari",), "#E0243F"),
    (("mercedes",), "#14A38C"),
    (("mclaren",), "#C46A0A"),
    (("aston",), "#23855E"),
    (("alpine",), "#FF2E9A"),
    (("williams",), "#2C5FC4"),
    (("audi",), "#D23A18"),
    (("haas",), "#6E8FD0"),
    (("racing bulls", "rb f1", "alphatauri", "toro rosso"), "#3F7BF0"),
    (("sauber", "alfa romeo"), "#52E252"),
    (("cadillac",), "#C9A227"),
]
_FALLBACK = ["#FF2D2D", "#FFC400", "#9B59B6", "#2ECC71", "#E67E22", "#95A5B8"]

COMPOUND_DISPLAY = {
    "SOFT": "#E0243F", "MEDIUM": "#FFC400", "HARD": "#E8EAED",
    "INTERMEDIATE": "#2ECC71", "WET": "#3F7BF0", "UNKNOWN": "#6b7280",
}


def team_color(team):
    t = str(team or "").lower()
    for keys, color in TEAM_DISPLAY:
        if any(k in t for k in keys):
            return color
    return None


def _mix_white(hex_color, frac=0.45):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    mix = tuple(round(c + (255 - c) * frac) for c in (r, g, b))
    return "#{:02X}{:02X}{:02X}".format(*mix)


def driver_colors(pairs):
    """[(code, team)] → {code: color}; el 2º piloto del equipo va aclarado."""
    seen, out, fb = {}, {}, 0
    for code, team in pairs:
        base = team_color(team)
        if base is None:
            base = _FALLBACK[fb % len(_FALLBACK)]
            fb += 1
        n = seen.get(base, 0)
        out[code] = base if n == 0 else _mix_white(base, 0.45 if n == 1 else 0.7)
        seen[base] = n + 1
    return out


def driver_name(code):
    return DRIVER_DB.get(code, {}).get("name", code)


def _con():
    if not db.db_exists(DB_PATH):
        # primera ejecución sin datos: crea la base vacía (esquema incluido)
        db.connect(path=DB_PATH).close()
    # reintento corto: durante una actualización el escritor toma la base
    # por ráfagas de ~1 s; esperar un poco evita errores 500 transitorios
    import time
    ultimo = None
    for _ in range(6):
        try:
            return db.connect(path=DB_PATH, read_only=True)
        except Exception as e:
            ultimo = e
            time.sleep(0.4)
    raise ultimo


def fmt_lap(s):
    if s is None:
        return "—"
    return f"{int(s // 60)}:{s % 60:06.3f}"


# ================================================================== endpoints

def meta():
    con = _con()
    try:
        seasons = db.query(con, """
            SELECT year, count(DISTINCT round) FILTER (WHERE session='Race') AS races,
                   count(*) AS sessions, sum(n_laps) AS laps
            FROM sessions GROUP BY year ORDER BY year DESC""")
        total = db.query(con, "SELECT count(*) n FROM laps")["n"][0]
        return {"seasons": seasons.to_dict("records"), "total_laps": int(total)}
    finally:
        con.close()


def championship(year):
    con = _con()
    try:
        pts = db.query(con, """
            SELECT s.round, s.gp, r.abbr, r.team, COALESCE(r.points, 0) AS pts
            FROM results r JOIN sessions s USING(session_id)
            WHERE s.year = ? AND s.session IN ('Race','Sprint')""", [year])
        wins = db.query(con, """
            SELECT r.abbr, count(*) AS w
            FROM results r JOIN sessions s USING(session_id)
            WHERE s.year = ? AND s.session='Race' AND r.position=1
            GROUP BY 1""", [year]).set_index("abbr")["w"]
        podios = db.query(con, """
            SELECT r.abbr, count(*) AS p
            FROM results r JOIN sessions s USING(session_id)
            WHERE s.year = ? AND s.session='Race' AND r.position<=3
            GROUP BY 1""", [year]).set_index("abbr")["p"]
        if pts.empty:
            return {"gps": [], "drivers": [], "summary": "Sin datos de esta temporada."}
        g = (pts.groupby(["round", "gp", "abbr"], as_index=False)
                .agg(pts=("pts", "sum"), team=("team", "last")).sort_values("round"))
        g["cum"] = g.groupby("abbr")["pts"].cumsum()
        rondas = g[["round", "gp"]].drop_duplicates().sort_values("round")
        gps = [gp.replace(" Grand Prix", "") for gp in rondas["gp"]]
        equipo = g.groupby("abbr")["team"].last()
        final = (g[g["round"] == g["round"].max()]
                 .sort_values("cum", ascending=False))
        colores = driver_colors([(c, equipo[c]) for c in final["abbr"]])
        drivers = []
        for _, row in final.iterrows():
            code = row["abbr"]
            serie = g[g["abbr"] == code].set_index("round")["cum"]
            drivers.append({
                "code": code, "name": driver_name(code), "team": equipo[code],
                "color": colores[code],
                "points": [serie.get(r) for r in rondas["round"]],
                "total": float(row["cum"]),
                "wins": int(wins.get(code, 0)), "podiums": int(podios.get(code, 0)),
            })
        lid, seg = drivers[0], (drivers[1] if len(drivers) > 1 else None)
        gap = f", +{lid['total'] - seg['total']:.0f} sobre {seg['code']}" if seg else ""
        rey_w = max(drivers, key=lambda d: d["wins"])
        summary = (f"{lid['code']} lidera el campeonato {year} con {lid['total']:.0f} pts{gap}. "
                   f"Más victorias: {rey_w['code']} ({rey_w['wins']}).")
        return {"gps": gps, "drivers": drivers, "summary": summary}
    finally:
        con.close()


def races(year):
    con = _con()
    try:
        ses = db.query(con, """
            SELECT session_id, round, gp, date, n_laps
            FROM sessions WHERE year = ? AND session = 'Race'
            ORDER BY round""", [year])
        pod = db.query(con, """
            SELECT r.session_id, r.abbr, r.team, r.position
            FROM results r JOIN sessions s USING(session_id)
            WHERE s.year = ? AND s.session='Race' AND r.position <= 3""", [year])
        out = []
        for _, row in ses.iterrows():
            p = pod[pod["session_id"] == row["session_id"]].sort_values("position")
            podium = [{"code": r["abbr"], "team": r["team"],
                       "color": team_color(r["team"]) or "#9aa0aa"}
                      for _, r in p.iterrows()]
            out.append({
                "sid": row["session_id"], "round": int(row["round"]),
                "gp": row["gp"], "label": row["gp"].replace(" Grand Prix", ""),
                "date": str(row["date"])[:10], "n_laps": int(row["n_laps"]),
                "podium": podium,
            })
        return out
    finally:
        con.close()


def session_detail(sid):
    con = _con()
    try:
        info = db.query(con, "SELECT * FROM sessions WHERE session_id=?", [sid])
        if info.empty:
            return None
        info = info.iloc[0]
        res = db.query(con, """
            SELECT abbr, full_name, team, grid, position, points, status
            FROM results WHERE session_id=? AND position IS NOT NULL
            ORDER BY position""", [sid])
        best = db.query(con, """
            SELECT driver, MIN(time_s) AS best_s FROM laps
            WHERE session_id=? AND time_s IS NOT NULL AND is_accurate
            GROUP BY 1""", [sid]).set_index("driver")["best_s"]
        colores = driver_colors([(r["abbr"], r["team"]) for _, r in res.iterrows()])

        results = []
        for _, r in res.iterrows():
            code = r["abbr"]
            grid = int(r["grid"]) if r["grid"] and r["grid"] == r["grid"] else None
            pos = int(r["position"])
            results.append({
                "pos": pos, "code": code, "name": r["full_name"], "team": r["team"],
                "color": colores.get(code, "#9aa0aa"), "grid": grid,
                "delta_pos": (grid - pos) if grid else None,
                "points": float(r["points"] or 0), "status": r["status"],
                "best_lap_s": float(best[code]) if code in best.index else None,
                "best_lap": fmt_lap(float(best[code])) if code in best.index else "—",
            })

        # ritmo vuelta a vuelta (solo vueltas representativas)
        laps = db.query(con, """
            SELECT driver, lap, time_s FROM laps
            WHERE session_id=? AND time_s IS NOT NULL AND is_accurate
              AND NOT is_pit_in AND NOT is_pit_out
            ORDER BY driver, lap""", [sid])
        pace = [{"code": d, "color": colores.get(d, "#9aa0aa"),
                 "laps": g["lap"].tolist(), "times": g["time_s"].round(3).tolist()}
                for d, g in laps.groupby("driver") if d in colores]

        # estrategia: stints por piloto (orden = posición final)
        stints = db.query(con, """
            SELECT driver, stint, compound,
                   MIN(lap) AS lap_ini, MAX(lap) AS lap_fin, count(*) AS vueltas
            FROM laps WHERE session_id=? AND stint IS NOT NULL
            GROUP BY 1, 2, 3 ORDER BY driver, stint""", [sid])
        orden = [r["code"] for r in results]
        strategy = []
        for code in orden:
            s = stints[stints["driver"] == code]
            if s.empty:
                continue
            strategy.append({"code": code, "stints": [
                {"compound": str(r["compound"]).upper(),
                 "color": COMPOUND_DISPLAY.get(str(r["compound"]).upper(),
                                               COMPOUND_DISPLAY["UNKNOWN"]),
                 "from": int(r["lap_ini"]), "to": int(r["lap_fin"]),
                 "laps": int(r["vueltas"])} for _, r in s.iterrows()]})

        # paradas con tiempo perdido: (in-lap + out-lap) - 2 × mediana limpia
        lapsall = db.query(con, """
            SELECT driver, lap, time_s, is_pit_in, is_pit_out
            FROM laps WHERE session_id=? AND time_s IS NOT NULL""", [sid])
        pits = []
        for code in orden:
            sub = lapsall[lapsall["driver"] == code]
            limpio = sub[~sub["is_pit_in"] & ~sub["is_pit_out"]]["time_s"]
            med = float(limpio.median()) if len(limpio) >= 3 else None
            segs = next((s_["stints"] for s_ in strategy if s_["code"] == code), [])
            stops = []
            for a, b in zip(segs, segs[1:]):
                lap_in = a["to"]
                t_in = sub[sub["lap"] == lap_in]["time_s"]
                t_out = sub[sub["lap"] == lap_in + 1]["time_s"]
                lost = None
                if med and len(t_in) and len(t_out):
                    lost = round(float(t_in.iloc[0] + t_out.iloc[0]) - 2 * med, 1)
                    if lost < 0:
                        lost = None  # SC comprimió los tiempos: dato contaminado
                stops.append({"lap": int(lap_in), "comp": b["compound"],
                              "color": b["color"], "lost": lost})
            con_dato = [x["lost"] for x in stops if x["lost"] is not None]
            pits.append({"code": code, "stops": stops,
                         "total_lost": round(sum(con_dato), 1) if con_dato else None})

        vmax = db.query(con, """
            SELECT driver, MAX(speed_st) AS vmax FROM laps
            WHERE session_id=? AND speed_st IS NOT NULL
            GROUP BY 1 ORDER BY vmax DESC LIMIT 10""", [sid])
        speedtrap = [{"code": r["driver"], "vmax": float(r["vmax"]),
                      "color": colores.get(r["driver"], "#9aa0aa")}
                     for _, r in vmax.iterrows()]

        # lap chart: posición real vuelta a vuelta
        posdf = db.query(con, """
            SELECT driver, lap, position FROM laps
            WHERE session_id=? AND position IS NOT NULL
            ORDER BY driver, lap""", [sid])
        laps_chart = [{"code": d, "color": colores.get(d, "#9aa0aa"),
                       "laps": g["lap"].tolist(),
                       "pos": g["position"].astype(int).tolist()}
                      for d, g in posdf.groupby("driver") if d in colores]

        # gap al líder por vuelta (tiempo acumulado vs el mejor acumulado)
        alldf = db.query(con, """
            SELECT driver, lap, time_s FROM laps
            WHERE session_id=? AND time_s IS NOT NULL ORDER BY lap""", [sid])
        gaps = []
        if not alldf.empty:
            piv = alldf.pivot_table(index="lap", columns="driver",
                                    values="time_s", aggfunc="first")
            cum = piv.cumsum()
            lider = cum.min(axis=1)
            gapdf = cum.sub(lider, axis=0)
            for d in gapdf.columns:
                if d not in colores:
                    continue
                serie = gapdf[d].dropna()
                gaps.append({"code": d, "color": colores.get(d, "#9aa0aa"),
                             "laps": serie.index.astype(int).tolist(),
                             "gap": serie.round(2).tolist()})

        # vueltas bajo SC/VSC (para sombrear): status contiene 4 (SC) / 6-7 (VSC)
        scdf = db.query(con, """
            SELECT DISTINCT lap FROM laps
            WHERE session_id=? AND (track_status LIKE '%4%' OR
                  track_status LIKE '%6%' OR track_status LIKE '%7%')
            ORDER BY lap""", [sid])
        sc_ranges, run = [], []
        for lp in scdf["lap"].astype(int).tolist():
            if run and lp == run[-1] + 1:
                run.append(lp)
            else:
                if run:
                    sc_ranges.append([run[0], run[-1]])
                run = [lp]
        if run:
            sc_ranges.append([run[0], run[-1]])

        # mejores sectores + vuelta ideal
        secdf = db.query(con, """
            SELECT driver, MIN(s1_s) s1, MIN(s2_s) s2, MIN(s3_s) s3
            FROM laps WHERE session_id=? GROUP BY 1
            HAVING s1 IS NOT NULL AND s2 IS NOT NULL AND s3 IS NOT NULL""", [sid])
        sectors = None
        if not secdf.empty:
            best_s = {k: float(secdf[k].min()) for k in ("s1", "s2", "s3")}
            best_who = {k: secdf.loc[secdf[k].idxmin(), "driver"] for k in ("s1", "s2", "s3")}
            rows = []
            orden_sec = [r["code"] for r in results if r["code"] in set(secdf["driver"])]
            secix = secdf.set_index("driver")
            for code in orden_sec[:12]:
                r = secix.loc[code]
                ideal = float(r["s1"] + r["s2"] + r["s3"])
                rows.append({"code": code, "color": colores.get(code, "#9aa0aa"),
                             "s1": round(float(r["s1"]), 3), "s2": round(float(r["s2"]), 3),
                             "s3": round(float(r["s3"]), 3), "ideal": fmt_lap(ideal),
                             "best": [k for k in ("s1", "s2", "s3")
                                      if float(r[k]) == best_s[k]]})
            ideal_total = sum(best_s.values())
            sectors = {"rows": rows,
                       "session_ideal": {"label": fmt_lap(ideal_total),
                                         "detail": " · ".join(
                                             f"{k.upper()} {best_who[k]} {best_s[k]:.3f}"
                                             for k in ("s1", "s2", "s3"))}}

        # resúmenes calculados (marca de la casa)
        summaries = {}
        if results:
            w = results[0]
            summaries["podium"] = (f"Ganó {w['name']} ({w['team']})"
                                   + (f", saliendo P{w['grid']}." if w['grid'] else "."))
            if best.size:
                fl_code = best.idxmin()
                summaries["pace"] = (f"Vuelta más rápida de toda la carrera: "
                                     f"{fmt_lap(float(best.min()))} de {fl_code}.")
            paradas = {s_["code"]: len(s_["stints"]) - 1 for s_ in strategy}
            if paradas:
                import statistics
                moda = statistics.mode(paradas.values())
                summaries["strategy"] = (f"Estrategia dominante en toda la parrilla: "
                                         f"{moda} parada(s). "
                                         f"El ganador hizo {paradas.get(w['code'], '?')}.")
            subida = max((r for r in results if r["delta_pos"] is not None),
                         key=lambda r: r["delta_pos"], default=None)
            if subida and subida["delta_pos"] > 0:
                summaries["results"] = (f"Mayor remontada: {subida['code']} "
                                        f"(+{subida['delta_pos']} posiciones desde P{subida['grid']}).")
            if laps_chart:
                cambios = {lc["code"]: (lc["pos"][0] - lc["pos"][-1])
                           for lc in laps_chart if lc["pos"]}
                if cambios:
                    top_g = max(cambios, key=cambios.get)
                    summaries["lapchart"] = (
                        f"{top_g} fue quien más posiciones ganó en pista "
                        f"({cambios[top_g]:+d}). "
                        + (f"Hubo SC/VSC en {len(sc_ranges)} tramo(s) (bandas grises)."
                           if sc_ranges else "Carrera sin coche de seguridad."))
            if gaps:
                fin = sorted(((g["code"], g["gap"][-1]) for g in gaps if g["gap"]),
                             key=lambda x: x[1])
                if len(fin) > 1:
                    summaries["gaps"] = (f"Gap final del 2º ({fin[1][0]}): "
                                         f"{fin[1][1]:.1f}s. Las caídas bruscas de "
                                         f"todas las líneas = pit stops o SC.")
            if sectors:
                summaries["sectors"] = (f"Vuelta ideal de la sesión: "
                                        f"{sectors['session_ideal']['label']} "
                                        f"({sectors['session_ideal']['detail']}).")
        return {
            "info": {"sid": sid, "year": int(info["year"]), "gp": info["gp"],
                     "session": info["session"], "date": str(info["date"])[:10],
                     "n_laps": int(info["n_laps"]), "circuit": info["circuit"]},
            "results": results, "pace": pace, "strategy": strategy, "pits": pits,
            "speedtrap": speedtrap, "laps_chart": laps_chart, "gaps": gaps,
            "sc_ranges": sc_ranges, "sectors": sectors, "summaries": summaries,
        }
    finally:
        con.close()


def h2h(code_a, code_b, source="race", year=None):
    """Duelo histórico entre dos pilotos: delta de mejor vuelta por GP común
    (carrera o qualy), duelo de posiciones, sectores y puntos por temporada.
    `year` acota a una temporada; None = todas las de la base."""
    import numpy as np
    con = _con()
    try:
        fy = " AND s.year = ? " if year else " "
        py = [year] if year else []
        # ── mejor vuelta por GP común (carrera o qualy) ────────────────────
        if source == "quali":
            raw = db.query(con, """
                SELECT s.year, s.round, s.gp, r.abbr AS driver,
                       r.q1_s, r.q2_s, r.q3_s, r.team
                FROM results r JOIN sessions s USING(session_id)
                WHERE s.session = 'Qualifying' AND r.abbr IN (?, ?)""" + fy,
                [code_a, code_b] + py)
            if not raw.empty:
                raw["best_s"] = raw[["q1_s", "q2_s", "q3_s"]].min(axis=1, skipna=True)
                raw = raw.dropna(subset=["best_s"])
            best = raw
        else:
            best = db.query(con, """
                SELECT s.year, s.round, s.gp, l.driver, MIN(l.time_s) AS best_s,
                       arg_min(l.team, l.time_s) AS team
                FROM laps l JOIN sessions s USING(session_id)
                WHERE s.session='Race' AND l.time_s IS NOT NULL AND l.is_accurate
                  AND l.driver IN (?, ?)""" + fy + """
                GROUP BY 1, 2, 3, 4""", [code_a, code_b] + py)
        vacio = {"gps": [], "deltas": [], "outlier": [], "summary": "Sin datos comunes.",
                 "source": source}
        if best.empty:
            return vacio
        a = best[best["driver"] == code_a]
        b = best[best["driver"] == code_b]
        m = a.merge(b, on=["year", "round", "gp"], suffixes=("_a", "_b"))
        m = m.sort_values(["year", "round"])
        if m.empty:
            vacio["summary"] = f"{code_a} y {code_b} no comparten ningún GP en la base."
            return vacio
        gps = [f"{r['gp'].replace(' Grand Prix', '')} {str(r['year'])[2:]}"
               for _, r in m.iterrows()]
        deltas = (m["best_s_a"] - m["best_s_b"]).round(3).tolist()
        outlier = [abs(d) > 2.5 for d in deltas]   # lluvia/incidente: no es ritmo puro
        col_a = team_color(m.iloc[-1]["team_a"]) or "#FF2D2D"
        col_b = team_color(m.iloc[-1]["team_b"]) or "#5B8FD9"
        if col_a == col_b:
            col_b = _mix_white(col_b, 0.5)
        wins_a = sum(1 for d in deltas if d < 0)
        n = len(deltas)
        limpios = [d for d, o in zip(deltas, outlier) if not o] or deltas
        mediana = float(np.median(limpios))
        media = float(np.mean(limpios))
        mas = code_a if mediana < 0 else code_b

        # ── duelo de posiciones (carreras comunes) ─────────────────────────
        posr = db.query(con, """
            SELECT s.year, s.round, r.abbr, r.position
            FROM results r JOIN sessions s USING(session_id)
            WHERE s.session='Race' AND r.position IS NOT NULL
              AND r.abbr IN (?, ?)""" + fy, [code_a, code_b] + py)
        ahead_a = ahead_b = 0
        if not posr.empty:
            piv = posr.pivot_table(index=["year", "round"], columns="abbr",
                                   values="position", aggfunc="first").dropna()
            if code_a in piv.columns and code_b in piv.columns:
                ahead_a = int((piv[code_a] < piv[code_b]).sum())
                ahead_b = int((piv[code_b] < piv[code_a]).sum())

        # ── duelo por sectores (promedio de mejores sectores, carreras) ────
        sec = db.query(con, """
            SELECT s.year, s.round, l.driver,
                   MIN(l.s1_s) AS s1, MIN(l.s2_s) AS s2, MIN(l.s3_s) AS s3
            FROM laps l JOIN sessions s USING(session_id)
            WHERE s.session='Race' AND l.driver IN (?, ?)""" + fy + """
            GROUP BY 1, 2, 3""", [code_a, code_b] + py)
        sectores = None
        if not sec.empty:
            sa = sec[sec["driver"] == code_a]
            sb = sec[sec["driver"] == code_b]
            ms = sa.merge(sb, on=["year", "round"], suffixes=("_a", "_b"))
            if len(ms) >= 2:
                sectores = {}
                for k in ("s1", "s2", "s3"):
                    dif = (ms[f"{k}_a"] - ms[f"{k}_b"]).dropna()
                    dif = dif[dif.abs() < 2.5]
                    if len(dif):
                        sectores[k] = round(float(dif.median()), 3)

        # ── puntos por temporada ───────────────────────────────────────────
        pts = db.query(con, """
            SELECT s.year, r.abbr, SUM(COALESCE(r.points, 0)) AS pts
            FROM results r JOIN sessions s USING(session_id)
            WHERE s.session IN ('Race','Sprint') AND r.abbr IN (?, ?)
            GROUP BY 1, 2 ORDER BY 1""", [code_a, code_b])
        temporadas = []
        for year, g in pts.groupby("year"):
            fila = {"year": int(year), "a": 0.0, "b": 0.0}
            for _, r in g.iterrows():
                fila["a" if r["abbr"] == code_a else "b"] = float(r["pts"])
            temporadas.append(fila)

        que = "vuelta rápida de carrera" if source == "race" else "mejor vuelta de qualy"
        alcance = f"temporada {year}" if year else "todas las temporadas de la base"
        summary = (f"En {n} GPs comunes de {alcance} ({que}): {code_a} más rápido en {wins_a}, "
                   f"{code_b} en {n - wins_a}. Ventaja MEDIANA de {mas}: "
                   f"{abs(mediana):.3f}s (media {abs(media):.3f}s, sin atípicas). "
                   + (f"En pista, {code_a if ahead_a >= ahead_b else code_b} terminó "
                      f"delante {max(ahead_a, ahead_b)}-{min(ahead_a, ahead_b)}."
                      if (ahead_a + ahead_b) else ""))
        return {"gps": gps, "deltas": deltas, "outlier": outlier, "source": source,
                "year": year, "alcance": alcance,
                "a": {"code": code_a, "name": driver_name(code_a), "color": col_a,
                      "wins": wins_a, "ahead": ahead_a},
                "b": {"code": code_b, "name": driver_name(code_b), "color": col_b,
                      "wins": n - wins_a, "ahead": ahead_b},
                "median": round(mediana, 3), "media": round(media, 3),
                "sectores": sectores, "temporadas": temporadas,
                "summary": summary}
    finally:
        con.close()


def drivers_index():
    """Pilotos disponibles en la base (para los selectores), con nº de GPs."""
    con = _con()
    try:
        d = db.query(con, """
            SELECT l.driver AS code, count(DISTINCT s.session_id) AS gps,
                   arg_max(l.team, s.date) AS team
            FROM laps l JOIN sessions s USING(session_id)
            WHERE s.session='Race'
            GROUP BY 1 ORDER BY gps DESC, code""")
        return [{"code": r["code"], "name": driver_name(r["code"]),
                 "gps": int(r["gps"]), "team": r["team"],
                 "color": team_color(r["team"]) or "#9aa0aa"}
                for _, r in d.iterrows()]
    finally:
        con.close()


def historic_pace(year):
    """Ritmo puro por GP: % sobre la mejor vuelta de cada carrera del año."""
    con = _con()
    try:
        best = db.query(con, """
            SELECT s.round, s.gp, l.driver, MIN(l.time_s) AS best_s,
                   arg_min(l.team, l.time_s) AS team
            FROM laps l JOIN sessions s USING(session_id)
            WHERE s.year = ? AND s.session = 'Race'
              AND l.time_s IS NOT NULL AND l.is_accurate
            GROUP BY 1, 2, 3""", [year])
        if best.empty:
            return {"gps": [], "drivers": [], "summary": ""}
        field = best.groupby("round")["best_s"].transform("min")
        best["pct"] = (best["best_s"] / field - 1) * 100
        best["label"] = best["gp"].str.replace(" Grand Prix", "", regex=False)
        rondas = best[["round", "label"]].drop_duplicates().sort_values("round")
        # top 6 por número de GPs disputados
        top = (best.groupby("driver")["gp"].nunique()
                   .sort_values(ascending=False).head(6).index.tolist())
        equipo = best.groupby("driver")["team"].last().to_dict()
        colores = driver_colors([(c, equipo.get(c, "")) for c in top])
        drivers = []
        for c in top:
            sub = best[best["driver"] == c].set_index("round")
            drivers.append({"code": c, "color": colores[c],
                            "pct": [round(float(sub.loc[r, "pct"]), 3)
                                    if r in sub.index else None
                                    for r in rondas["round"]]})
        medias = best[best["driver"].isin(top)].groupby("driver")["pct"].mean()
        lider = medias.idxmin()
        summary = (f"{lider} es el más cercano al límite en {year}: en promedio "
                   f"quedó a +{medias.min():.2f}% de la mejor vuelta de cada GP.")
        return {"gps": rondas["label"].tolist(), "drivers": drivers,
                "summary": summary}
    finally:
        con.close()


def trap_records(year):
    """Récord de speed trap de cada GP del año (carrera)."""
    con = _con()
    try:
        vmax = db.query(con, """
            SELECT s.round, s.gp, l.driver, MAX(l.speed_st) AS vmax,
                   arg_max(l.team, l.speed_st) AS team
            FROM laps l JOIN sessions s USING(session_id)
            WHERE s.year = ? AND s.session = 'Race' AND l.speed_st IS NOT NULL
            GROUP BY 1, 2, 3
            QUALIFY row_number() OVER (PARTITION BY s.round ORDER BY vmax DESC) = 1
            ORDER BY s.round""", [year])
        return [{"gp": r["gp"].replace(" Grand Prix", ""), "code": r["driver"],
                 "vmax": float(r["vmax"]),
                 "color": team_color(r["team"]) or "#9aa0aa"}
                for _, r in vmax.iterrows()]
    finally:
        con.close()


def _base_deficits(con, year, source):
    """Mejor vuelta por equipo y ronda → déficit % al pole y a la mediana.
    Compartido por team_evolution y team_predict."""
    if source == "race":
        base = db.query(con, """
            SELECT s.round, s.gp, l.team, MIN(l.time_s) AS best_s
            FROM laps l JOIN sessions s USING(session_id)
            WHERE s.year = ? AND s.session = 'Race'
              AND l.time_s IS NOT NULL AND l.is_accurate
              AND l.team IS NOT NULL AND l.team != 'None'
            GROUP BY 1, 2, 3""", [year])
    else:
        raw = db.query(con, """
            SELECT s.round, s.gp, r.team, r.q1_s, r.q2_s, r.q3_s
            FROM results r JOIN sessions s USING(session_id)
            WHERE s.year = ? AND s.session = 'Qualifying'""", [year])
        if not raw.empty:
            # mejor tiempo del piloto = mínimo entre Q1/Q2/Q3 (ignora nulos)
            raw["best_s"] = raw[["q1_s", "q2_s", "q3_s"]].min(axis=1, skipna=True)
            raw = raw.dropna(subset=["best_s"])
            base = (raw.groupby(["round", "gp", "team"], as_index=False)
                       .agg(best_s=("best_s", "min")))
        else:
            base = raw
    if base.empty:
        return base
    base = base.sort_values("round").reset_index(drop=True)
    base["pole"] = base.groupby("round")["best_s"].transform("min")
    base["mediana"] = base.groupby("round")["best_s"].transform("median")
    base["deficit"] = ((base["best_s"] - base["pole"]) / base["pole"] * 100).round(3)
    base["deficit_med"] = ((base["best_s"] - base["mediana"]) / base["mediana"] * 100).round(3)
    return base


def team_evolution(year, source="quali"):
    """Evolución de equipos: déficit % al pole (y a la mediana) por ronda,
    pendientes de desarrollo con R², convergencia de la parrilla, huella de
    circuito y proyección ingenua. `source` = 'quali' (Q1-Q3) o 'race'
    (mejor vuelta de carrera, cobertura completa)."""
    import numpy as np
    con = _con()
    try:
        base = _base_deficits(con, year, source)
        if base.empty:
            return {"rounds": [], "teams": [], "summary": None, "source": source}

        rondas = base[["round", "gp"]].drop_duplicates().sort_values("round")
        labels = [g.replace(" Grand Prix", "") for g in rondas["gp"]]
        rlist = rondas["round"].tolist()

        # orden de equipos por déficit promedio (los rápidos primero)
        orden = base.groupby("team")["deficit"].mean().sort_values().index.tolist()
        colores = {t: (team_color(t) or "#9aa0aa") for t in orden}

        teams = []
        for t in orden:
            sub = base[base["team"] == t].set_index("round")
            serie = [round(float(sub.loc[r, "deficit"]), 3) if r in sub.index else None
                     for r in rlist]
            serie_med = [round(float(sub.loc[r, "deficit_med"]), 3) if r in sub.index else None
                         for r in rlist]
            item = {"team": t, "color": colores[t], "deficit": serie,
                    "deficit_med": serie_med,
                    "media": round(float(sub["deficit"].mean()), 3),
                    "rounds": int(sub.index.nunique())}
            # pendiente de desarrollo + R² (mínimo 3 rondas)
            if sub.index.nunique() >= 3:
                x = sub.index.values.astype(float)
                y = sub["deficit"].values.astype(float)
                b1, b0 = np.polyfit(x, y, 1)
                y_hat = b0 + b1 * x
                ss_res = float(((y - y_hat) ** 2).sum())
                ss_tot = float(((y - y.mean()) ** 2).sum())
                r2 = max(0.0, 1 - ss_res / ss_tot) if ss_tot > 0 else 0.0
                item.update(slope=round(float(b1), 4), r2=round(r2, 3),
                            proy=round(max(0.0, float(b0 + b1 * (max(rlist) + 1))), 3))
            teams.append(item)

        # convergencia: σ (muestral) del déficit por ronda + tendencia lineal
        disp = base.groupby("round")["deficit"].std().dropna()
        conv = None
        if len(disp) >= 3:
            b1s, b0s = np.polyfit(disp.index.values.astype(float), disp.values, 1)
            conv = {"rounds": disp.index.astype(int).tolist(),
                    "sigma": [round(float(v), 3) for v in disp.values],
                    "trend": [round(float(b0s + b1s * r), 3) for r in disp.index],
                    "slope": round(float(b1s), 4)}

        # huella de circuito: residuo vs el promedio PROPIO del equipo
        pivote = base.pivot_table(index="team", columns="round", values="deficit")
        residuos = pivote.sub(pivote.mean(axis=1), axis=0).reindex(orden)
        huella = {"teams": orden,
                  "labels": [f"R{r} {labels[rlist.index(r)]}" for r in pivote.columns],
                  "z": [[round(float(v), 2) if v == v else None for v in fila]
                        for fila in residuos.values]}
        # la huella más marcada (mejor pista relativa de algún equipo)
        mejor_celda = None
        arr = residuos.values
        if arr.size:
            with np.errstate(invalid="ignore"):
                idx = np.unravel_index(np.nanargmin(arr), arr.shape)
            mejor_celda = {"team": orden[idx[0]],
                           "gp": huella["labels"][idx[1]],
                           "val": round(float(arr[idx]), 2)}

        # resumen ejecutivo calculado
        con_pend = [t for t in teams if "slope" in t]
        resumen = None
        if len(teams) >= 2:
            lider, seg = teams[0], teams[1]
            partes = [f"RITMO: {lider['team']} manda con {lider['media']:.2f}% de "
                      f"déficit promedio; {seg['team']} lo persigue ({seg['media']:.2f}%)."]
            if con_pend:
                mejor = min(con_pend, key=lambda t: t["slope"])
                peor = max(con_pend, key=lambda t: t["slope"])
                def cred(r2):
                    return "tendencia sólida" if r2 >= 0.5 else "tendencia aún ruidosa"
                partes.append(f"DESARROLLO: {mejor['team']} es quien más recorta "
                              f"({mejor['slope']:+.3f} %/carrera, R² {mejor['r2']:.2f} → {cred(mejor['r2'])}); "
                              f"{peor['team']} se rezaga ({peor['slope']:+.3f} %/carrera, "
                              f"R² {peor['r2']:.2f} → {cred(peor['r2'])}).")
            if conv:
                partes.append("CONVERGENCIA: la parrilla se está "
                              + ("APRETANDO" if conv["slope"] < 0 else "ABRIENDO")
                              + f" ({conv['slope']:+.3f} puntos de σ por carrera).")
            if mejor_celda:
                partes.append(f"HUELLA DE CIRCUITO: la más marcada es {mejor_celda['team']} "
                              f"en {mejor_celda['gp']} ({mejor_celda['val']:+.2f}% vs su promedio).")
            proys = sorted((t for t in con_pend if "proy" in t), key=lambda t: t["proy"])[:3]
            if proys:
                partes.append("PROYECCIÓN R" + str(max(rlist) + 1) + " (ingenua): "
                              + " · ".join(f"{t['team']} {t['proy']:.2f}%" for t in proys) + ".")
            resumen = partes

        return {"source": source, "rounds": rlist, "labels": labels,
                "n_rounds": len(rlist), "teams": teams, "conv": conv,
                "huella": huella, "next_round": max(rlist) + 1,
                "summary": resumen}
    finally:
        con.close()


def team_predict(year, source="quali"):
    """Predicción de la próxima carrera: regresión ponderada por recencia
    sobre el déficit % por ronda + Monte Carlo (4,000 carreras simuladas)
    + backtest honesto contra las rondas ya corridas."""
    import numpy as np
    from f1core import predict as P
    con = _con()
    try:
        base = _base_deficits(con, year, source)
    finally:
        con.close()
    vacio = {"source": source, "year": year, "next_round": None, "teams": [],
             "valid": None, "summary": None}
    if base.empty or base["round"].nunique() < 4:
        return vacio

    next_round = int(base["round"].max()) + 1
    # vuelta de pole típica del año → para traducir % a segundos por vuelta
    pole_med = float(base.groupby("round")["pole"].first().median())
    seg_pct = pole_med / 100.0

    series = {t: list(zip(sub["round"].astype(int), sub["deficit"].astype(float)))
              for t, sub in base.groupby("team")}

    equipos = []
    for t, pts in series.items():
        pts = sorted(pts)
        if len(pts) < 3:
            continue
        pred, sigma = P.predice([r for r, _ in pts], [v for _, v in pts], next_round)
        equipos.append({"team": t, "color": team_color(t) or "#9aa0aa",
                        "pred": pred, "sigma": sigma,
                        "last": pts[-1][1], "n": len(pts)})
    if len(equipos) < 3:
        return vacio

    p_win, p_top3 = P.simula_carrera([e["pred"] for e in equipos],
                                     [e["sigma"] for e in equipos])
    mejor = min(e["pred"] for e in equipos)
    for e, pw, p3 in zip(equipos, p_win, p_top3):
        gap = e["pred"] - mejor          # 0 = el mejor proyectado
        e.update(gap=round(gap, 3),
                 gap_s=round(gap * seg_pct, 3),
                 lo=round(gap - 1.28 * e["sigma"], 3),   # intervalo 80%
                 hi=round(gap + 1.28 * e["sigma"], 3),
                 p_win=round(float(pw), 3), p_top3=round(float(p3), 3),
                 pred=round(e["pred"], 3), sigma=round(e["sigma"], 3),
                 last=round(e["last"], 3))
    equipos.sort(key=lambda e: e["gap"])

    valid = P.backtesta(series)

    # resumen ejecutivo calculado
    top = sorted(equipos, key=lambda e: -e["p_win"])[:3]
    partes = [f"FAVORITO: {top[0]['team']} con {top[0]['p_win']*100:.0f}% de "
              f"probabilidad de ser el equipo más rápido; lo siguen "
              f"{top[1]['team']} ({top[1]['p_win']*100:.0f}%) y "
              f"{top[2]['team']} ({top[2]['p_win']*100:.0f}%)."]
    partes.append(f"RITMO PROYECTADO: {equipos[0]['team']} llega con el mejor "
                  f"ritmo puro; {equipos[1]['team']} a {equipos[1]['gap']:.2f}% "
                  f"(≈{equipos[1]['gap_s']:.2f}s por vuelta de {pole_med:.0f}s).")
    if top[0]["team"] != equipos[0]["team"]:
        partes.append(f"OJO: el favorito por probabilidad ({top[0]['team']}) no es "
                      f"el más rápido proyectado ({equipos[0]['team']}). No es un error: "
                      f"{top[0]['team']} es más irregular (σ ±{top[0]['sigma']:.2f}%) y esa "
                      f"variabilidad le da más boletos en los extremos de la simulación.")
    if valid:
        mae_s = valid["mae"] * seg_pct
        dif = valid["mae"] - valid["mae_base"]
        veredicto = ("SÍ le gana" if dif < -0.005
                     else ("empata" if abs(dif) <= 0.005 else "aún NO le gana"))
        partes.append(f"VALIDACIÓN: re-jugando la temporada ronda a ronda, el "
                      f"modelo erró en promedio ±{valid['mae']:.2f}% "
                      f"(≈{mae_s:.2f}s/vuelta) y acertó el equipo más rápido en "
                      f"{valid['aciertos']} de {valid['total']} carreras; el baseline "
                      f"'repetir la última carrera' habría errado ±{valid['mae_base']:.2f}% "
                      f"→ el modelo {veredicto}.")
    partes.append("LÍMITES: el modelo solo ve ritmo puro — no sabe de lluvia, "
                  "abandonos, sanciones ni estrategia. Son probabilidades, no destino.")

    return {"source": source, "year": year, "next_round": next_round,
            "pole_med": round(pole_med, 1), "teams": equipos, "valid": valid,
            "summary": partes}
