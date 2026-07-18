"""Estimación energética NIVEL 1 desde telemetría pública — dinámica
longitudinal inversa y detección de candidatos a recorte (super clipping).

Todo lo que sale de aquí es ESTIMACIÓN declarada, nunca medición: sin mapa
ICE ni sensores DC públicos, la potencia eléctrica exacta no es identificable.
Este módulo se limita a lo defendible:

  · potencia_rueda_kw — física longitudinal con supuestos declarados
  · candidatos_recorte — el 'nivel medio' del análisis: tramos a fondo, sin
    freno, en recta, donde el coche desacelera (FUERTE ≈ harvesting a fondo,
    la firma literal del super clipping) o se amesetá prematuramente (DÉBIL)

Sanity check reglamentario: los ajustes 2026 apuntan a 2-4 s de super
clipping por vuelta — si el detector marca 11 s en todos los circuitos,
no es una conspiración, es un bug.
"""
import numpy as np

# SUPUESTOS del modelo físico (declarados en la interfaz):
SUPUESTOS = {
    "masa_kg": 800.0,   # mínimo 2026 (~768 kg) + combustible medio
    "cda_m2": 1.35,     # área de arrastre efectiva (varía con el aero activo)
    "crr": 0.012,       # resistencia a la rodadura
    "rho": 1.21,        # densidad del aire (kg/m³)
}


def potencia_rueda_kw(v_ms, a_ms2, masa_kg=None, cda_m2=None, crr=None,
                      rho=None, g=9.81):
    """P_rueda ≈ (m·a + ½ρ·CdA·v² + Crr·m·g) · v — dinámica longitudinal
    inversa. Positiva = el tren empuja; muy negativa en frenada (frenos, no
    ERS: interpretar solo tramos de tracción)."""
    masa_kg = SUPUESTOS["masa_kg"] if masa_kg is None else masa_kg
    cda_m2 = SUPUESTOS["cda_m2"] if cda_m2 is None else cda_m2
    crr = SUPUESTOS["crr"] if crr is None else crr
    rho = SUPUESTOS["rho"] if rho is None else rho
    v = np.asarray(v_ms, dtype=float)
    a = np.asarray(a_ms2, dtype=float)
    fuerza = masa_kg * a + 0.5 * rho * cda_m2 * v ** 2 + crr * masa_kg * g
    return fuerza * v / 1000.0


def candidatos_recorte(d, v_kph, a_ms2, throttle, brake, dt, zonas,
                       glat=None, v_min_kph=250.0, min_dur_s=0.3,
                       glat_max=0.5):
    """Candidatos a recorte de potencia / super clipping en una vuelta.

    Excluye curvas rápidas a fondo (|G lateral| ≥ glat_max): ahí la velocidad
    se pierde por carga lateral y arrastre de neumático, no por clipping —
    sin este filtro, Maggotts/Becketts entera parece una conspiración.

    FUERTE: a fondo, sin freno, en recta, v≥v_min y DESACELERANDO
            (a < −0.3 m/s²) de forma sostenida — la firma del super clipping.
    DÉBIL:  mismas condiciones pero meseta prematura (a < 0.3) en una banda
            de velocidad donde la envolvente empírica de la propia vuelta
            dice que el coche normalmente aún empuja (p90 ≥ 1.5 m/s²).

    Devuelve lista de tramos {d0, d1, dur_s, tipo} y nunca los llama
    'confirmados': sin sensores DC, son candidatos.
    """
    d = np.asarray(d, dtype=float)
    v = np.asarray(v_kph, dtype=float)
    a = np.asarray(a_ms2, dtype=float)
    th = np.asarray(throttle, dtype=float)
    br = np.asarray(brake, dtype=float)
    dt = np.asarray(dt, dtype=float)

    fondo = (th >= 95.0) & (br < 5.0)
    if glat is not None:
        fondo = fondo & (np.abs(np.asarray(glat, dtype=float)) < glat_max)
    en_zona = np.zeros(len(d), dtype=bool)
    for z in zonas or []:
        en_zona |= (d >= float(z["d0"])) & (d <= float(z["d1"]))
    base = fondo & en_zona & (v >= v_min_kph)
    if not base.any():
        return []

    # envolvente empírica de aceleración a fondo por banda de 10 km/h:
    # dice cuánto 'debería' empujar el coche a esa velocidad EN ESTA vuelta
    bandas = (v // 10).astype(int)
    esperada = {}
    for b in np.unique(bandas[fondo]):
        vals = a[fondo & (bandas == b)]
        if len(vals) >= 5:
            esperada[int(b)] = float(np.percentile(vals, 90))
    env = np.array([esperada.get(int(b), 0.0) for b in bandas])

    fuerte = base & (a < -0.3)
    debil = base & ~fuerte & (a < 0.3) & (env >= 1.5)

    tramos = []
    for marca, tipo in ((fuerte, "fuerte"), (debil, "debil")):
        i = 0
        n = len(marca)
        while i < n:
            if marca[i]:
                j = i
                while j < n and marca[j]:
                    j += 1
                dur = float(dt[i:j].sum())
                if dur >= min_dur_s:
                    tramos.append({"d0": round(float(d[i])),
                                   "d1": round(float(d[j - 1])),
                                   "dur_s": round(dur, 2), "tipo": tipo})
                i = j
            else:
                i += 1
    tramos.sort(key=lambda t: t["d0"])
    return tramos
