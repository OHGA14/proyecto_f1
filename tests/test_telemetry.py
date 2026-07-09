"""Tests de los helpers puros de api/telemetry.py (sin FastF1 ni red)."""
import numpy as np
import pytest

from api.telemetry import _delta_series, _phase_pcts


def test_delta_series_b_mas_lento():
    # ref recorre 1000 m a 50 m/s (20 s); B a 40 m/s (25 s)
    d = np.linspace(0, 1000, 101)
    t_ref = d / 50.0
    t_b = d / 40.0
    dx, dv = _delta_series(d, t_ref, d, t_b)
    assert dv[0] == pytest.approx(0.0)
    assert dv[-1] == pytest.approx(5.0)      # B pierde 5 s al final
    assert np.all(np.diff(dv) >= 0)          # pierde de forma monótona


def test_delta_series_recorta_al_mas_corto():
    d_ref = np.linspace(0, 1000, 101)
    d_b = np.linspace(0, 900, 91)            # la vuelta de B mide menos
    dx, dv = _delta_series(d_ref, d_ref / 50, d_b, d_b / 50)
    assert dx[-1] <= 900
    assert np.allclose(dv, 0, atol=1e-9)     # mismos tiempos → delta 0


def test_phase_pcts():
    # 10 muestras de 1 s: 5 a fondo, 3 frenando, 2 en curva
    throttle = np.array([100] * 5 + [0] * 3 + [50] * 2, dtype=float)
    brake = np.array([0] * 5 + [1] * 3 + [0] * 2, dtype=float)
    dt = np.ones(10)
    fondo, frenada, curva = _phase_pcts(throttle, brake, dt)
    assert (fondo, frenada, curva) == (50.0, 30.0, 20.0)
    assert fondo + frenada + curva == pytest.approx(100.0)


def test_phase_pcts_vacio():
    assert _phase_pcts(np.array([]), np.array([]), np.array([])) == (0.0, 0.0, 0.0)
