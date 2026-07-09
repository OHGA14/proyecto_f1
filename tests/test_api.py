"""Tests de la API FastAPI contra una base temporal (sin red ni FastF1)."""
import pytest
from fastapi.testclient import TestClient

from f1core import db
from api import queries
from api.main import app
from tests.test_db import SesionFalsa


@pytest.fixture
def client(tmp_path, monkeypatch):
    path = str(tmp_path / "api.duckdb")
    con = db.connect(path=path)
    db.ingest_session(con, SesionFalsa(gp="GP Uno", round_no=1))
    db.ingest_session(con, SesionFalsa(gp="GP Dos", round_no=2))
    con.close()
    monkeypatch.setattr(queries, "DB_PATH", path)
    return TestClient(app)


def test_meta(client):
    m = client.get("/api/meta").json()
    assert m["seasons"][0]["year"] == 2026
    assert m["seasons"][0]["races"] == 2
    assert m["total_laps"] == 12


def test_championship(client):
    c = client.get("/api/championship/2026").json()
    assert len(c["gps"]) == 2
    lider = c["drivers"][0]
    assert lider["code"] == "AAA" and lider["total"] == 50  # 25 pts × 2 carreras
    assert lider["wins"] == 2
    assert "AAA lidera" in c["summary"]
    assert lider["color"].startswith("#")


def test_session_detail(client):
    d = client.get("/api/session/detail",
                   params={"sid": "2026|GP Uno|Race"}).json()
    assert len(d["results"]) == 2 and d["results"][0]["pos"] == 1
    assert len(d["pace"]) == 2 and len(d["strategy"]) == 2
    assert d["results"][0]["best_lap"].startswith("1:30")
    assert "Ganó" in d["summaries"]["podium"]


def test_session_404(client):
    r = client.get("/api/session/detail", params={"sid": "1999|Nada|Race"})
    assert r.status_code == 404


def test_h2h(client):
    h = client.get("/api/h2h", params={"a": "aaa", "b": "BBB"}).json()  # case-insensitive
    assert len(h["deltas"]) == 2
    assert h["a"]["wins"] == 2  # AAA siempre 1s más rápido en la sesión falsa
    assert "AAA" in h["summary"]


def test_drivers_index(client):
    d = client.get("/api/drivers").json()
    assert {x["code"] for x in d} == {"AAA", "BBB"}
    assert d[0]["gps"] == 2
