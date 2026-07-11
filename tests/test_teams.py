"""Tests de team_evolution con datos sintéticos de resultado conocido a mano."""
import pandas as pd
import pytest

from f1core import db
from api import queries
from tests.test_db import SesionFalsa


def _quali(year, gp, round_no, tiempos):
    """Sesión de qualy falsa: tiempos = {equipo: [(piloto, q3_s), ...]}."""
    ses = SesionFalsa(year=year, gp=gp, name="Qualifying", round_no=round_no)
    filas = []
    pos = 1
    for team, pilotos in tiempos.items():
        for code, q3 in pilotos:
            filas.append({"Abbreviation": code, "FullName": code, "TeamName": team,
                          "GridPosition": pos, "Position": pos, "Points": 0,
                          "Status": "Finished",
                          "Q1": pd.Timedelta(seconds=q3 + 1.0),
                          "Q2": pd.Timedelta(seconds=q3 + 0.5),
                          "Q3": pd.Timedelta(seconds=q3)})
            pos += 1
    ses.results = pd.DataFrame(filas)
    return ses


@pytest.fixture
def con_teams(tmp_path, monkeypatch):
    path = str(tmp_path / "teams.duckdb")
    con = db.connect(path=path)
    # 4 rondas: Alfa mejora linealmente (90.0, 89.8, 89.6, 89.4 → siempre pole),
    # Beta constante en 91.0 → su déficit SUBE porque el pole baja.
    for i, ronda in enumerate([1, 2, 3, 4]):
        alfa = 90.0 - 0.2 * i
        db.ingest_session(con, _quali(2026, f"GP {ronda}", ronda, {
            "Alfa": [("AAA", alfa), ("AAB", alfa + 0.3)],
            "Beta": [("BBB", 91.0), ("BBC", 91.4)],
        }))
    con.close()
    monkeypatch.setattr(queries, "DB_PATH", path)
    return path


def test_deficit_al_pole(con_teams):
    out = queries.team_evolution(2026, "quali")
    assert out["n_rounds"] == 4
    alfa = next(t for t in out["teams"] if t["team"] == "Alfa")
    beta = next(t for t in out["teams"] if t["team"] == "Beta")
    # Alfa hace la pole siempre → déficit 0 en todas las rondas
    assert alfa["deficit"] == [0.0, 0.0, 0.0, 0.0]
    # Beta ronda 1: (91.0 - 90.0) / 90.0 * 100 = 1.111
    assert beta["deficit"][0] == pytest.approx(1.111, abs=1e-3)
    # Beta ronda 4: (91.0 - 89.4) / 89.4 * 100 = 1.790
    assert beta["deficit"][3] == pytest.approx(1.790, abs=1e-3)
    # el orden pone al más rápido primero
    assert out["teams"][0]["team"] == "Alfa"


def test_pendiente_y_r2(con_teams):
    out = queries.team_evolution(2026, "quali")
    beta = next(t for t in out["teams"] if t["team"] == "Beta")
    # déficit de Beta crece casi linealmente → pendiente positiva y R² ~1
    assert beta["slope"] > 0.2
    assert beta["r2"] > 0.99
    # proyección R5 = extrapolación de la recta (nunca negativa)
    assert beta["proy"] >= beta["deficit"][3]
    alfa = next(t for t in out["teams"] if t["team"] == "Alfa")
    assert alfa["slope"] == pytest.approx(0.0, abs=1e-9)  # clavado en 0
    assert alfa["proy"] == 0.0                             # clip inferior en 0


def test_deficit_vs_mediana(con_teams):
    out = queries.team_evolution(2026, "quali")
    alfa = next(t for t in out["teams"] if t["team"] == "Alfa")
    beta = next(t for t in out["teams"] if t["team"] == "Beta")
    # con 2 equipos la mediana es el punto medio → simétricos y de signo opuesto
    assert alfa["deficit_med"][0] < 0 < beta["deficit_med"][0]
    assert alfa["deficit_med"][0] == pytest.approx(-beta["deficit_med"][0], abs=0.02)


def test_convergencia_divergente(con_teams):
    out = queries.team_evolution(2026, "quali")
    # el gap Alfa-Beta crece cada ronda → σ sube → pendiente positiva (diverge)
    assert out["conv"] is not None
    assert out["conv"]["slope"] > 0
    assert len(out["conv"]["sigma"]) == 4


def test_huella_y_resumen(con_teams):
    out = queries.team_evolution(2026, "quali")
    assert out["huella"]["teams"] == ["Alfa", "Beta"]
    assert len(out["huella"]["z"][0]) == 4
    # residuos de cada equipo suman ~0 (son desvíos de su propio promedio)
    assert sum(out["huella"]["z"][1]) == pytest.approx(0.0, abs=0.05)
    assert any("RITMO" in p for p in out["summary"])
    assert any("DESARROLLO" in p for p in out["summary"])


def test_source_race(con_teams):
    # sin carreras en la base → respuesta vacía y sin excepción
    out = queries.team_evolution(2026, "race")
    assert out["teams"] == [] and out["source"] == "race"
