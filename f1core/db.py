"""Capa de datos DuckDB: sesiones, resultados y vueltas de todos los GPs ingeridos.

La base vive en data.nosync/f1.duckdb (fuera de git y de iCloud; se regenera con
ingest.py). Permite consultas multi-GP/multi-temporada en milisegundos, sin cargar
sesiones de FastF1 (~40 s cada una).
"""
import os

import duckdb
import pandas as pd

DB_DIR = "data.nosync"
DB_PATH = os.path.join(DB_DIR, "f1.duckdb")

_DDL = [
    """CREATE TABLE IF NOT EXISTS sessions(
        session_id TEXT PRIMARY KEY,
        year INTEGER, round INTEGER, gp TEXT, session TEXT,
        date TIMESTAMP, circuit TEXT,
        n_laps INTEGER, n_drivers INTEGER,
        ingested_at TIMESTAMP DEFAULT current_timestamp)""",
    """CREATE TABLE IF NOT EXISTS results(
        session_id TEXT, abbr TEXT, full_name TEXT, team TEXT,
        grid DOUBLE, position DOUBLE, points DOUBLE, status TEXT,
        q1_s DOUBLE, q2_s DOUBLE, q3_s DOUBLE)""",
    """CREATE TABLE IF NOT EXISTS laps(
        session_id TEXT, driver TEXT, team TEXT, lap INTEGER,
        time_s DOUBLE, s1_s DOUBLE, s2_s DOUBLE, s3_s DOUBLE,
        compound TEXT, tyre_life DOUBLE, stint DOUBLE,
        speed_st DOUBLE, speed_fl DOUBLE,
        is_pit_in BOOLEAN, is_pit_out BOOLEAN,
        track_status TEXT, is_accurate BOOLEAN)""",
    # migraciones sobre bases existentes (idempotentes)
    "ALTER TABLE laps ADD COLUMN IF NOT EXISTS position DOUBLE",
]


def connect(path=DB_PATH, read_only=False):
    """Abre (y si hace falta crea) la base. read_only=True para la UI."""
    if not read_only:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    con = duckdb.connect(path, read_only=read_only)
    if not read_only:
        for stmt in _DDL:
            con.execute(stmt)
    return con


def db_exists(path=DB_PATH):
    return os.path.exists(path)


def _seconds(series):
    """Serie de Timedelta → segundos (float, NaN→None al insertar)."""
    return series.dt.total_seconds() if hasattr(series, "dt") else series


def session_key(year, gp, session_name):
    return f"{year}|{gp}|{session_name}"


def ingest_session(con, ses):
    """Ingesta idempotente de una sesión FastF1 YA CARGADA (ses.load() previo).

    Reemplaza lo que hubiera de esa sesión. Devuelve el session_id.
    """
    ev = ses.event
    sid = session_key(int(ev.year), str(ev["EventName"]), str(ses.name))

    # --- laps ---------------------------------------------------------------
    laps = ses.laps.copy()
    for col in ("Team", "Compound", "TyreLife", "Stint", "SpeedST", "SpeedFL",
                "TrackStatus", "IsAccurate", "PitInTime", "PitOutTime",
                "Sector1Time", "Sector2Time", "Sector3Time", "Position"):
        if col not in laps.columns:
            laps[col] = None
    df_laps = pd.DataFrame({
        "session_id": sid,
        "driver": laps["Driver"].astype(str),
        "team": laps["Team"].astype(str),
        "lap": laps["LapNumber"].astype("Int64"),
        "time_s": _seconds(laps["LapTime"]),
        "s1_s": _seconds(laps["Sector1Time"]),
        "s2_s": _seconds(laps["Sector2Time"]),
        "s3_s": _seconds(laps["Sector3Time"]),
        "compound": laps["Compound"].astype(str),
        "tyre_life": pd.to_numeric(laps["TyreLife"], errors="coerce"),
        "stint": pd.to_numeric(laps["Stint"], errors="coerce"),
        "speed_st": pd.to_numeric(laps["SpeedST"], errors="coerce"),
        "speed_fl": pd.to_numeric(laps["SpeedFL"], errors="coerce"),
        "is_pit_in": laps["PitInTime"].notna(),
        "is_pit_out": laps["PitOutTime"].notna(),
        "track_status": laps["TrackStatus"].astype(str),
        "is_accurate": laps["IsAccurate"].fillna(False).astype(bool),
        # va al FINAL: la columna se añadió por ALTER y el INSERT usa SELECT *
        "position": pd.to_numeric(laps["Position"], errors="coerce"),
    })

    # --- results ------------------------------------------------------------
    res = ses.results.copy() if ses.results is not None else pd.DataFrame()
    if not res.empty:
        for col in ("Abbreviation", "FullName", "TeamName", "GridPosition",
                    "Position", "Points", "Status", "Q1", "Q2", "Q3"):
            if col not in res.columns:
                res[col] = None
        df_res = pd.DataFrame({
            "session_id": sid,
            "abbr": res["Abbreviation"].astype(str),
            "full_name": res["FullName"].astype(str),
            "team": res["TeamName"].astype(str),
            "grid": pd.to_numeric(res["GridPosition"], errors="coerce"),
            "position": pd.to_numeric(res["Position"], errors="coerce"),
            "points": pd.to_numeric(res["Points"], errors="coerce"),
            "status": res["Status"].astype(str),
            "q1_s": _seconds(res["Q1"]),
            "q2_s": _seconds(res["Q2"]),
            "q3_s": _seconds(res["Q3"]),
        })
    else:
        df_res = pd.DataFrame()

    # --- sessions -----------------------------------------------------------
    df_ses = pd.DataFrame([{
        "year": int(ev.year),
        "round": int(ev["RoundNumber"]),
        "gp": str(ev["EventName"]),
        "session": str(ses.name),
        "date": pd.Timestamp(ses.date) if ses.date is not None else None,
        "circuit": str(ev.get("Location", "")),
        "n_laps": int(df_laps["lap"].max()) if len(df_laps) else 0,
        "n_drivers": int(df_laps["driver"].nunique()),
    }])
    df_ses.insert(0, "session_id", sid)

    # --- reemplazo idempotente ------------------------------------------------
    con.execute("DELETE FROM laps WHERE session_id = ?", [sid])
    con.execute("DELETE FROM results WHERE session_id = ?", [sid])
    con.execute("DELETE FROM sessions WHERE session_id = ?", [sid])
    con.register("_df_laps", df_laps)
    con.execute("INSERT INTO laps SELECT * FROM _df_laps")
    if not df_res.empty:
        con.register("_df_res", df_res)
        con.execute("INSERT INTO results SELECT * FROM _df_res")
    con.register("_df_ses", df_ses)
    con.execute("""INSERT INTO sessions(session_id, year, round, gp, session, date,
                   circuit, n_laps, n_drivers)
                   SELECT * FROM _df_ses""")
    return sid


def list_sessions(con):
    return con.execute(
        "SELECT year, round, gp, session, n_laps, n_drivers, date "
        "FROM sessions ORDER BY year, round, session").df()


def query(con, sql, params=None):
    """Consulta libre → DataFrame."""
    return con.execute(sql, params or []).df()
