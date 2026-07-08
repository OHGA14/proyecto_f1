"""Tests del motor de datos (f1core/db.py) con sesiones falsas — sin red ni FastF1."""
import pandas as pd
import pytest

from f1core import db


class SesionFalsa:
    """Imita lo mínimo de una sesión FastF1 cargada."""

    def __init__(self, year=2026, gp="Test Grand Prix", name="Race", round_no=1,
                 drivers=("AAA", "BBB"), n_laps=3):
        self.event = pd.Series({"year": year, "EventName": gp,
                                "RoundNumber": round_no, "Location": "Testville"})
        self.name = name
        self.date = pd.Timestamp("2026-01-01 14:00")
        rows = []
        for d_i, drv in enumerate(drivers):
            for lap in range(1, n_laps + 1):
                rows.append({
                    "Driver": drv, "Team": f"Equipo {d_i}", "LapNumber": lap,
                    "LapTime": pd.Timedelta(seconds=90 + d_i + lap * 0.1),
                    "Sector1Time": pd.Timedelta(seconds=30),
                    "Sector2Time": pd.Timedelta(seconds=30),
                    "Sector3Time": pd.Timedelta(seconds=30 + d_i + lap * 0.1),
                    "Compound": "SOFT", "TyreLife": lap, "Stint": 1,
                    "SpeedST": 300 + d_i * 5, "SpeedFL": 280.0,
                    "PitInTime": pd.NaT, "PitOutTime": pd.NaT,
                    "TrackStatus": "1", "IsAccurate": True,
                })
        self.laps = pd.DataFrame(rows)
        self.results = pd.DataFrame([
            {"Abbreviation": drv, "FullName": f"Piloto {drv}", "TeamName": f"Equipo {i}",
             "GridPosition": i + 1, "Position": i + 1, "Points": 25 - i * 7,
             "Status": "Finished", "Q1": pd.Timedelta(seconds=89),
             "Q2": pd.Timedelta(seconds=88), "Q3": pd.Timedelta(seconds=87)}
            for i, drv in enumerate(drivers)])


@pytest.fixture
def con(tmp_path):
    c = db.connect(path=str(tmp_path / "test.duckdb"))
    yield c
    c.close()


def test_ingesta_basica(con):
    sid = db.ingest_session(con, SesionFalsa())
    assert sid == "2026|Test Grand Prix|Race"
    assert con.execute("SELECT count(*) FROM laps").fetchone()[0] == 6
    assert con.execute("SELECT count(*) FROM results").fetchone()[0] == 2
    ses = db.list_sessions(con)
    assert len(ses) == 1 and ses.iloc[0]["n_drivers"] == 2 and ses.iloc[0]["n_laps"] == 3


def test_conversion_de_tiempos(con):
    db.ingest_session(con, SesionFalsa())
    t = con.execute("SELECT time_s FROM laps WHERE driver='AAA' AND lap=1").fetchone()[0]
    assert t == pytest.approx(90.1)  # 90 + 0 + 1*0.1
    q3 = con.execute("SELECT q3_s FROM results WHERE abbr='BBB'").fetchone()[0]
    assert q3 == pytest.approx(87.0)


def test_idempotencia(con):
    db.ingest_session(con, SesionFalsa())
    db.ingest_session(con, SesionFalsa())  # re-ingesta: reemplaza, no duplica
    assert con.execute("SELECT count(*) FROM laps").fetchone()[0] == 6
    assert con.execute("SELECT count(*) FROM sessions").fetchone()[0] == 1


def test_consulta_multi_gp(con):
    db.ingest_session(con, SesionFalsa(gp="GP Uno", round_no=1))
    db.ingest_session(con, SesionFalsa(gp="GP Dos", round_no=2, drivers=("AAA", "CCC")))
    df = db.query(con, """
        SELECT s.gp, l.driver, MIN(l.time_s) best
        FROM laps l JOIN sessions s USING(session_id)
        GROUP BY 1, 2 ORDER BY 1, 2""")
    assert len(df) == 4  # 2 GPs × 2 pilotos
    assert set(df["gp"]) == {"GP Uno", "GP Dos"}
    # AAA corrió los dos GPs: la consulta multi-GP lo cruza sin cargar nada
    assert (df["driver"] == "AAA").sum() == 2


def test_laps_sin_resultados(con):
    ses = SesionFalsa()
    ses.results = pd.DataFrame()  # sesión sin clasificación publicada
    sid = db.ingest_session(con, ses)
    assert con.execute("SELECT count(*) FROM laps").fetchone()[0] == 6
    assert con.execute("SELECT count(*) FROM results WHERE session_id=?", [sid]).fetchone()[0] == 0
