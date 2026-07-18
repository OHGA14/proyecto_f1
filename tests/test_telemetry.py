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


def test_delta_series_alinea_por_fraccion_y_cierra():
    # trayectorias de longitud DISTINTA (líneas distintas): se alinean por
    # fracción de vuelta, la malla de la referencia se conserva completa y
    # el último punto cierra con la diferencia total de tiempos
    d_ref = np.linspace(0, 1000, 101)
    t_ref = np.linspace(0, 90, 101)
    d_b = np.linspace(0, 900, 91)            # la vuelta de B mide menos
    t_b = np.linspace(0, 89, 91)             # y B es 1s más rápido
    dx, dv = _delta_series(d_ref, t_ref, d_b, t_b)
    assert dx[-1] == 1000                    # malla completa, sin recortes
    assert abs(dv[0]) < 1e-9                 # arranca en cero
    assert abs(dv[-1] - (-1.0)) < 1e-9       # cierra: B gana exactamente 1s


def test_delta_series_mismos_tiempos_da_cero():
    d_ref = np.linspace(0, 1000, 101)
    d_b = np.linspace(0, 900, 91)
    dx, dv = _delta_series(d_ref, d_ref / 50, d_b, d_b / 45)  # 20s ambos
    assert np.allclose(dv[-1], 0, atol=1e-9)


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
