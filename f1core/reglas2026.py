"""Constantes reglamentarias FIA 2026 — las gráficas citan REGLAS, no números
mágicos. Fuente: FIA 2026 Formula One Regulations Section C (técnico) más los
ajustes de temporada anunciados desde Miami 2026.

Todo lo que aquí es SUPUESTO (no regla) está marcado como tal: la potencia del
motor térmico no es un límite publicado por sensor, es la cifra de diseño
ampliamente reportada del reparto ~50/50 de 2026.
"""
import datetime

import numpy as np

# ── Reglamento técnico base 2026 (Section C) ────────────────────────────────
P_ERS_MAX_KW = 350.0        # potencia eléctrica DC máxima del ERS-K
DELTA_SOC_MAX_MJ = 4.0      # delta de estado de carga del Energy Store en pista
TORQUE_MGUK_MAX_NM = 500.0  # par mecánico máximo del MGU-K

# ── Ajustes de temporada 2026 (anunciados desde Miami) ──────────────────────
AJUSTES_MIAMI_DESDE = datetime.date(2026, 5, 1)
RECARGA_QUALY_MJ = 7.0              # antes 8 MJ
SUPERCLIP_OBJETIVO_S = (2.0, 4.0)   # duración objetivo de super clipping/vuelta
SUPERCLIP_PICO_KW = 350.0

# ── SUPUESTOS declarados (no son reglas medibles públicas) ──────────────────
ICE_BASE_KW = 400.0     # motor térmico 2026 (~536 hp), cifra de diseño reportada
ETA_TREN = 0.96         # eficiencia del tren motriz (supuesto)


def limite_despliegue_kw(v_kph):
    """Límite BASE de despliegue del ERS-K según velocidad (aprox. C5.2.8):
    350 kW planos hasta ~290 km/h, rampa 1800−5v hasta 340, caída fuerte
    6900−20v hasta 345, y 0 después."""
    v = np.asarray(v_kph, dtype=float)
    out = np.where(v < 340.0, 1800.0 - 5.0 * v,
                   np.where(v < 345.0, 6900.0 - 20.0 * v, 0.0))
    return np.clip(out, 0.0, P_ERS_MAX_KW)


def limite_override_kw(v_kph):
    """Límite con Manual Override / Overtake activo (aprox.): 7100−20v
    hasta 355 km/h."""
    v = np.asarray(v_kph, dtype=float)
    out = np.where(v < 355.0, 7100.0 - 20.0 * v, 0.0)
    return np.clip(out, 0.0, P_ERS_MAX_KW)


def techo_potencia_rueda_kw(v_kph, ice_kw=ICE_BASE_KW, eta=ETA_TREN):
    """Techo REGULATORIO ESTIMADO de potencia en rueda: (ICE supuesto +
    límite ERS por velocidad) × eficiencia del tren. Es una referencia para
    comparar estimaciones, no una medición."""
    return (ice_kw + limite_despliegue_kw(v_kph)) * eta
