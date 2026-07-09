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
    return db.connect(path=DB_PATH, read_only=True)


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

        vmax = db.query(con, """
            SELECT driver, MAX(speed_st) AS vmax FROM laps
            WHERE session_id=? AND speed_st IS NOT NULL
            GROUP BY 1 ORDER BY vmax DESC LIMIT 10""", [sid])
        speedtrap = [{"code": r["driver"], "vmax": float(r["vmax"]),
                      "color": colores.get(r["driver"], "#9aa0aa")}
                     for _, r in vmax.iterrows()]

        # resúmenes calculados (marca de la casa)
        summaries = {}
        if results:
            w = results[0]
            summaries["podium"] = (f"Ganó {w['name']} ({w['team']})"
                                   + (f", saliendo P{w['grid']}." if w['grid'] else "."))
            if best.size:
                fl_code = best.idxmin()
                summaries["pace"] = (f"Vuelta más rápida: {fmt_lap(float(best.min()))} "
                                     f"de {fl_code}.")
            paradas = {s_["code"]: len(s_["stints"]) - 1 for s_ in strategy}
            if paradas:
                import statistics
                moda = statistics.mode(paradas.values())
                summaries["strategy"] = (f"Estrategia dominante: {moda} parada(s). "
                                         f"El ganador hizo {paradas.get(w['code'], '?')}.")
            subida = max((r for r in results if r["delta_pos"] is not None),
                         key=lambda r: r["delta_pos"], default=None)
            if subida and subida["delta_pos"] > 0:
                summaries["results"] = (f"Mayor remontada: {subida['code']} "
                                        f"(+{subida['delta_pos']} posiciones desde P{subida['grid']}).")
        return {
            "info": {"sid": sid, "year": int(info["year"]), "gp": info["gp"],
                     "session": info["session"], "date": str(info["date"])[:10],
                     "n_laps": int(info["n_laps"]), "circuit": info["circuit"]},
            "results": results, "pace": pace, "strategy": strategy,
            "speedtrap": speedtrap, "summaries": summaries,
        }
    finally:
        con.close()


def h2h(code_a, code_b):
    con = _con()
    try:
        best = db.query(con, """
            SELECT s.year, s.round, s.gp, l.driver, MIN(l.time_s) AS best_s,
                   arg_min(l.team, l.time_s) AS team
            FROM laps l JOIN sessions s USING(session_id)
            WHERE s.session='Race' AND l.time_s IS NOT NULL AND l.is_accurate
              AND l.driver IN (?, ?)
            GROUP BY 1, 2, 3, 4""", [code_a, code_b])
        if best.empty:
            return {"gps": [], "deltas": [], "summary": "Sin datos comunes."}
        a = best[best["driver"] == code_a]
        b = best[best["driver"] == code_b]
        m = a.merge(b, on=["year", "round", "gp"], suffixes=("_a", "_b"))
        m = m.sort_values(["year", "round"])
        if m.empty:
            return {"gps": [], "deltas": [], "summary":
                    f"{code_a} y {code_b} no comparten ningún GP en la base."}
        gps = [f"{r['gp'].replace(' Grand Prix', '')} {str(r['year'])[2:]}"
               for _, r in m.iterrows()]
        deltas = (m["best_s_a"] - m["best_s_b"]).round(3).tolist()
        col_a = team_color(m.iloc[-1]["team_a"]) or "#FF2D2D"
        col_b = team_color(m.iloc[-1]["team_b"]) or "#5B8FD9"
        if col_a == col_b:  # compañeros de equipo
            col_b = _mix_white(col_b, 0.5)
        wins_a = sum(1 for d in deltas if d < 0)
        n = len(deltas)
        media = sum(deltas) / n
        mas = code_a if media < 0 else code_b
        summary = (f"En {n} GPs comunes: {code_a} fue más rápido en {wins_a}, "
                   f"{code_b} en {n - wins_a}. Ventaja media de {mas}: "
                   f"{abs(media):.3f}s por vuelta rápida.")
        return {"gps": gps, "deltas": deltas,
                "a": {"code": code_a, "name": driver_name(code_a), "color": col_a,
                      "wins": wins_a},
                "b": {"code": code_b, "name": driver_name(code_b), "color": col_b,
                      "wins": n - wins_a},
                "media": round(media, 3), "summary": summary}
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
