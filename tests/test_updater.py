"""Tests de la lógica de detección del actualizador global (pura, sin red)."""
import datetime

from api.updater import _pendientes


def _eventos():
    d = datetime.datetime
    return [
        {"year": 2026, "gp": "British Grand Prix", "sessions": [
            {"name": "Practice 1", "date_utc": d(2026, 7, 3, 11)},
            {"name": "Qualifying", "date_utc": d(2026, 7, 4, 14)},
            {"name": "Race", "date_utc": d(2026, 7, 5, 14)},
        ]},
        {"year": 2026, "gp": "Belgian Grand Prix", "sessions": [
            {"name": "Qualifying", "date_utc": d(2026, 7, 18, 14)},
            {"name": "Race", "date_utc": d(2026, 7, 19, 14)},
        ]},
        {"year": 2026, "gp": "Sin Fecha Grand Prix", "sessions": [
            {"name": "Race", "date_utc": None},
        ]},
    ]


AHORA = datetime.datetime(2026, 7, 10, 12)


def test_detecta_lo_que_falta():
    pend = _pendientes(_eventos(), have_sids=set(), now_utc=AHORA)
    # British Q y Race ya pasaron; las prácticas se omiten; Bélgica es futuro
    assert pend == [(2026, "British Grand Prix", "Qualifying"),
                    (2026, "British Grand Prix", "Race")]


def test_no_repite_lo_ya_ingerido():
    have = {"2026|British Grand Prix|Race"}
    pend = _pendientes(_eventos(), have, AHORA)
    assert pend == [(2026, "British Grand Prix", "Qualifying")]


def test_al_dia():
    have = {"2026|British Grand Prix|Race", "2026|British Grand Prix|Qualifying"}
    assert _pendientes(_eventos(), have, AHORA) == []


def test_futuro_y_sin_fecha_se_ignoran():
    despues = datetime.datetime(2026, 7, 20, 12)  # ya pasó Bélgica
    pend = _pendientes(_eventos(), set(), despues)
    assert (2026, "Belgian Grand Prix", "Race") in pend
    assert all(gp != "Sin Fecha Grand Prix" for _, gp, _ in pend)
