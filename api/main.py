"""HABIB CONTROL · F1 API — FastAPI sobre la base DuckDB.

Ejecutar:  .venv.nosync/bin/uvicorn api.main:app --port 8600
Web:       http://localhost:8600      (interfaz broadcast)
Docs API:  http://localhost:8600/docs (Swagger autogenerado)
"""
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from api import queries, telemetry, updater

app = FastAPI(
    title="HABIB CONTROL · F1 API",
    description="Datos históricos de F1 (DuckDB): campeonatos, carreras, "
                "estrategia y head-to-head. Todos los tiempos en segundos.",
    version="1.0.0",
)


@app.get("/api/meta")
def get_meta():
    """Temporadas disponibles y tamaño de la base."""
    return queries.meta()


@app.get("/api/championship/{year}")
def get_championship(year: int):
    """Puntos acumulados por piloto (Carrera + Sprint) de una temporada."""
    return queries.championship(year)


@app.get("/api/races/{year}")
def get_races(year: int):
    """Carreras de una temporada con su podio."""
    return queries.races(year)


@app.get("/api/session/detail")
def get_session_detail(sid: str = Query(..., description="ID 'año|GP|sesión'")):
    """Resultados, ritmo, estrategia y speed trap de una sesión."""
    out = queries.session_detail(sid)
    if out is None:
        raise HTTPException(404, f"Sesión no encontrada: {sid}")
    return out


@app.get("/api/h2h")
def get_h2h(a: str = Query(..., min_length=2, max_length=4),
            b: str = Query(..., min_length=2, max_length=4),
            source: str = "race", year: int | None = None):
    """Head-to-head histórico: deltas por GP (carrera o qualy), duelo de
    posiciones, sectores y puntos por temporada. `year` acota la temporada."""
    return queries.h2h(a.upper(), b.upper(),
                       source if source in ("race", "quali") else "race", year)


@app.get("/api/drivers")
def get_drivers():
    """Pilotos disponibles en la base (para selectores)."""
    return queries.drivers_index()


# ── Telemetría bajo demanda (vista ANÁLISIS) ─────────────────────────────────

@app.get("/api/telemetry/catalog")
def get_tel_catalog():
    """Sesiones con telemetría en la caché de FastF1 y su estado de carga."""
    return telemetry.catalog()


@app.post("/api/telemetry/load")
def post_tel_load(year: int, gp: str, session: str):
    """Empieza a cargar una sesión FastF1 en memoria (hilo en 2º plano)."""
    return telemetry.start_load(year, gp, session)


@app.get("/api/telemetry/status")
def get_tel_status(sid: str):
    """Estado de carga: cold / loading / ready / error."""
    return telemetry.status(sid)


@app.get("/api/telemetry/schedule")
def get_tel_schedule(year: int):
    """Calendario del año con las sesiones de cada GP (marca las cacheadas)."""
    return telemetry.schedule(year)


@app.get("/api/telemetry/analysis")
def get_tel_analysis(sid: str, drivers: str = "", lap: int | None = None):
    """Análisis de vuelta: canales por distancia, delta, G-G, fases, mapa,
    DTW, micro-sectores, sectores y zonas. `lap` = vuelta específica (opcional)."""
    codes = [c.strip().upper() for c in drivers.split(",") if c.strip()] or None
    out = telemetry.analysis(sid, codes, lap)
    if out is None:
        raise HTTPException(409, f"La sesión {sid} no está cargada (usa /api/telemetry/load).")
    return out


@app.get("/api/telemetry/sessionstats")
def get_tel_sessionstats(sid: str):
    """Ritmo de la sesión completa: boxplot, consistencia, evolución,
    degradación por stint, parrilla→meta, heatmap de speed trap, qualy."""
    out = telemetry.session_stats(sid)
    if out is None:
        raise HTTPException(409, f"La sesión {sid} no está cargada.")
    return out


@app.get("/api/telemetry/drivers")
def get_tel_drivers(sid: str):
    """Pilotos de la sesión cargada, ordenados por vuelta rápida."""
    out = telemetry.available_drivers(sid)
    if out is None:
        raise HTTPException(409, f"La sesión {sid} no está cargada.")
    return out


@app.get("/api/telemetry/laps")
def get_tel_laps(sid: str, driver: str):
    """Vueltas válidas de un piloto (para el modo VS VUELTAS)."""
    out = telemetry.laps_of(sid, driver.upper())
    if out is None:
        raise HTTPException(409, f"La sesión {sid} no está cargada.")
    return out


@app.get("/api/telemetry/vslaps")
def get_tel_vslaps(sid: str, driver: str, lap_a: int, lap_b: int):
    """Comparación de dos vueltas del MISMO piloto (A = color piloto, B = blanco)."""
    out = telemetry.vslaps(sid, driver.upper(), lap_a, lap_b)
    if out is None:
        raise HTTPException(409, f"La sesión {sid} no está cargada.")
    return out


@app.post("/api/update")
def post_update():
    """Actualiza TODO: baja e ingesta las sesiones nuevas de la temporada
    (Carrera/Qualy/Sprint ya disputadas que falten en la base)."""
    return updater.start()


@app.get("/api/update/status")
def get_update_status():
    """Progreso del actualizador: running, log, encontradas/ok/fallos."""
    return updater.status()


@app.get("/api/teams/{year}")
def get_teams(year: int, source: str = "quali"):
    """Evolución de equipos: déficit % al pole por ronda, pendientes de
    desarrollo, convergencia, huella de circuito y proyección.
    `source` = quali (Q1-Q3) o race (mejor vuelta de carrera)."""
    if source not in ("quali", "race"):
        raise HTTPException(422, "source debe ser 'quali' o 'race'")
    return queries.team_evolution(year, source)


@app.get("/api/teams/predict/{year}")
def get_teams_predict(year: int, source: str = "quali"):
    """Predicción de la próxima carrera: regresión ponderada por recencia,
    Monte Carlo (probabilidades) y backtest de validación."""
    if source not in ("quali", "race"):
        raise HTTPException(422, "source debe ser 'quali' o 'race'")
    out = queries.team_predict(year, source)
    # nombre del próximo GP desde el calendario (si FastF1 lo tiene a mano)
    if out.get("next_round"):
        try:
            ev = telemetry.schedule(year).get("events", [])
            gp = next((e["gp"] for e in ev if e["round"] == out["next_round"]), None)
            out["next_gp"] = gp.replace(" Grand Prix", "") if gp else None
        except Exception:
            out["next_gp"] = None
    return out


@app.get("/api/historic/pace/{year}")
def get_historic_pace(year: int):
    """Ritmo puro por GP de la temporada: % sobre la mejor vuelta de cada carrera."""
    return queries.historic_pace(year)


@app.get("/api/historic/trap/{year}")
def get_historic_trap(year: int):
    """Récord de speed trap de cada GP de la temporada."""
    return queries.trap_records(year)


@app.middleware("http")
async def _sin_cache_web(request, call_next):
    """La web (html/js/css) siempre se revalida: tras actualizar el proyecto,
    un simple Cmd+R trae la versión nueva. El vendor (plotly) sí se cachea."""
    resp = await call_next(request)
    path = request.url.path
    if (path == "/" or path.endswith((".html", ".js", ".css"))) and "/vendor/" not in path:
        resp.headers["Cache-Control"] = "no-cache"
    return resp


# La web broadcast se sirve desde el mismo proceso (sin node ni build).
_WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
if os.path.isdir(_WEB):
    app.mount("/", StaticFiles(directory=_WEB, html=True), name="web")
