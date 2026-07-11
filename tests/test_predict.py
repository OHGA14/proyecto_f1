"""Matemática del predictor de la próxima carrera (f1core.predict)."""
import numpy as np

from f1core.predict import predice, simula_carrera, backtesta, PISO_SIGMA


def test_predice_necesita_tres_puntos():
    assert predice([1, 2], [1.0, 1.1], 3) is None


def test_predice_serie_plana_devuelve_el_nivel():
    # sin tendencia, la predicción es el propio nivel y sigma queda en el piso
    pred, sigma = predice([1, 2, 3, 4, 5], [1.5] * 5, 6)
    assert abs(pred - 1.5) < 1e-9
    assert sigma == PISO_SIGMA


def test_predice_amortigua_la_pendiente():
    # serie que cae 0.2 por ronda: la recta pura (phi=1) continúa exacto a 0.8;
    # con phi=0 queda el puro nivel; el default debe caer ENTRE ambos
    x, y = [1, 2, 3, 4, 5], [1.8, 1.6, 1.4, 1.2, 1.0]
    recta_pura = predice(x, y, 6, phi=1.0)[0]
    solo_nivel = predice(x, y, 6, phi=0.0)[0]
    amortiguada = predice(x, y, 6)[0]
    assert abs(recta_pura - 0.8) < 1e-9
    assert recta_pura < amortiguada < solo_nivel


def test_predice_pesa_mas_lo_reciente():
    # mismo pasado lejano, presente distinto: la predicción sigue al presente
    viejo_bueno = predice([1, 2, 3, 4, 5, 6], [1.0, 1.0, 1.0, 2.0, 2.0, 2.0], 7)[0]
    viejo_malo = predice([1, 2, 3, 4, 5, 6], [2.0, 2.0, 2.0, 1.0, 1.0, 1.0], 7)[0]
    assert viejo_bueno > 1.5          # domina el presente alto
    assert viejo_malo < 1.5           # domina el presente bajo


def test_simula_carrera_es_coherente():
    p_win, p_top3 = simula_carrera([0.0, 0.5, 1.0, 2.0], [0.1, 0.1, 0.1, 0.1])
    assert abs(sum(p_win) - 1.0) < 1e-9        # alguien gana siempre
    assert abs(sum(p_top3) - 3.0) < 1e-9       # el top 3 tiene 3 lugares
    assert p_win[0] > 0.9                      # el claramente más rápido domina
    assert p_top3[3] < 0.05                    # el claramente más lento casi nunca entra


def test_simula_carrera_es_reproducible():
    a = simula_carrera([0.0, 0.3], [0.2, 0.2])
    b = simula_carrera([0.0, 0.3], [0.2, 0.2])
    assert a == b                              # misma semilla → mismo resultado


def test_simula_la_varianza_da_boletos():
    # mismo ritmo medio: el equipo irregular gana en las simulaciones extremas,
    # pero un gap claro con poco ruido no se voltea
    p_win, _ = simula_carrera([0.0, 0.05], [0.05, 0.8])
    assert 0.25 < p_win[1] < 0.75


def test_backtesta_series_lineales():
    # tres equipos con déficit estable y ordenado: el modelo debe clavarlo
    series = {
        "A": [(r, 0.0) for r in range(1, 8)],
        "B": [(r, 0.5) for r in range(1, 8)],
        "C": [(r, 1.0) for r in range(1, 8)],
    }
    v = backtesta(series)
    assert v["total"] == 4                     # rondas 4..7 evaluables
    assert v["aciertos"] == 4
    assert v["mae"] <= v["mae_base"] + 1e-9    # no pierde contra 'repetir la última'
    assert v["mae"] < 0.01


def test_backtesta_sin_datos_suficientes():
    assert backtesta({"A": [(1, 0.0), (2, 0.1)]}) is None
