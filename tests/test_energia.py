"""Nivel 1 eléctrico 2026: reglas FIA, potencia en rueda y candidatos a recorte."""
import numpy as np

from f1core import energia, reglas2026


def test_limite_despliegue_curva():
    # 350 kW planos a baja/media velocidad, rampa después, cero a muy alta
    assert reglas2026.limite_despliegue_kw(200.0) == 350.0
    assert reglas2026.limite_despliegue_kw(290.0) == 350.0
    assert float(reglas2026.limite_despliegue_kw(320.0)) == 200.0   # 1800−5·320
    assert float(reglas2026.limite_despliegue_kw(342.0)) == 60.0    # 6900−20·342
    assert reglas2026.limite_despliegue_kw(350.0) == 0.0


def test_techo_potencia_rueda():
    # a 200 km/h: (400 ICE + 350 ERS) × 0.96 = 720 kW
    assert abs(float(reglas2026.techo_potencia_rueda_kw(200.0)) - 720.0) < 1e-6
    # a 350 km/h el ERS ya no aporta: 400 × 0.96 = 384 kW
    assert abs(float(reglas2026.techo_potencia_rueda_kw(350.0)) - 384.0) < 1e-6


def test_potencia_rueda_valor_a_mano():
    # v=50 m/s, a=0: solo arrastre + rodadura
    # F = 0.5·1.21·1.35·2500 + 0.012·800·9.81 = 2041.9 + 94.2 = 2136.1 N
    # P = 2136.1 · 50 / 1000 ≈ 106.8 kW
    p = float(energia.potencia_rueda_kw(np.array([50.0]), np.array([0.0]))[0])
    assert abs(p - 106.8) < 1.0
    # con a=10 m/s²: + 800·10·50/1000 = +400 kW
    p2 = float(energia.potencia_rueda_kw(np.array([50.0]), np.array([10.0]))[0])
    assert abs(p2 - (p + 400.0)) < 1.0


def _vuelta_sintetica(a_final):
    """Recta de 1000 m a fondo: acelera fuerte al inicio y `a_final` al final."""
    n = 200
    d = np.linspace(0, 1000, n)
    v = np.full(n, 300.0)
    a = np.where(d < 600, 3.0, a_final)     # empuja 3 m/s² y luego cambia
    th = np.full(n, 100.0)
    br = np.zeros(n)
    dt = np.full(n, 0.06)                   # ~12 s de recta
    zonas = [{"d0": 0, "d1": 1000}]
    return d, v, a, th, br, dt, zonas


def test_recorte_fuerte_detectado():
    # desacelera a fondo sin freno al final de la recta → candidato FUERTE
    d, v, a, th, br, dt, zonas = _vuelta_sintetica(-1.0)
    tramos = energia.candidatos_recorte(d, v, a, th, br, dt, zonas)
    fuertes = [t for t in tramos if t["tipo"] == "fuerte"]
    assert len(fuertes) == 1
    assert fuertes[0]["d0"] >= 590
    assert fuertes[0]["dur_s"] > 1.0


def test_sin_recorte_si_sigue_empujando():
    d, v, a, th, br, dt, zonas = _vuelta_sintetica(2.5)
    assert energia.candidatos_recorte(d, v, a, th, br, dt, zonas) == []


def test_sin_recorte_fuera_de_zona():
    d, v, a, th, br, dt, _ = _vuelta_sintetica(-1.0)
    assert energia.candidatos_recorte(d, v, a, th, br, dt, zonas=[]) == []


def test_curva_rapida_a_fondo_no_es_recorte():
    # desacelera a fondo PERO con 3G laterales (curva rápida): no es clipping
    d, v, a, th, br, dt, zonas = _vuelta_sintetica(-1.0)
    glat = np.where(d >= 600, 3.0, 0.0)
    tramos = energia.candidatos_recorte(d, v, a, th, br, dt, zonas, glat=glat)
    assert tramos == []


def test_meseta_prematura_es_debil():
    # meseta (a≈0) donde la envolvente dice que aún debería empujar 3 m/s²
    d, v, a, th, br, dt, zonas = _vuelta_sintetica(0.0)
    tramos = energia.candidatos_recorte(d, v, a, th, br, dt, zonas)
    assert any(t["tipo"] == "debil" for t in tramos)
    assert not any(t["tipo"] == "fuerte" for t in tramos)
