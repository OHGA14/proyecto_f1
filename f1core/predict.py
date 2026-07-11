"""Predicción de la próxima carrera a partir del déficit % por ronda.

Modelo: TENDENCIA AMORTIGUADA ponderada por recencia (variante del método
de Holt). Dos ingredientes:

  · nivel  = media ponderada por recencia (las carreras recientes pesan más;
             el peso se reduce a la mitad cada `media_vida` rondas)
  · tendencia = pendiente de la recta ponderada, pero aplicada solo en una
             fracción phi (amortiguación): extrapolar la pendiente completa
             sobre-dispara — el backtest 2026 lo confirmó (MAE 1.07% con
             phi=1 vs 0.86% con phi=0.3 en carrera).

Tres piezas puras (sin base de datos, sin web — solo numpy):

1. predice — predicción puntual + sigma (error típico del propio modelo).
2. simula_carrera — Monte Carlo: se "corren" n carreras sembrando cada
   equipo con ruido normal(pred, sigma) y se cuenta cuántas veces termina
   como el más rápido / en el top 3.
3. backtesta — validación honesta: para cada ronda ya corrida, entrena
   SOLO con las anteriores y predice; compara el error del modelo contra
   el baseline "repetir la última carrera".
"""
import numpy as np

# nadie predice ritmo de F1 con menos de ±0.08% (~0.07s) de error típico:
# piso de sigma para no vender certezas falsas cuando el ajuste sale "perfecto"
PISO_SIGMA = 0.08
MEDIA_VIDA = 3.0   # rondas: el peso de una carrera se reduce a la mitad cada 3
PHI = 0.3          # amortiguación de la pendiente (0 = solo nivel, 1 = recta pura)


def predice(x, y, x_next, media_vida=MEDIA_VIDA, phi=PHI):
    """Tendencia amortiguada en x_next. Devuelve (pred, sigma) o None si <3 puntos."""
    if len(x) < 3:
        return None
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    w = 0.5 ** ((x.max() - x) / media_vida)
    # np.polyfit minimiza sum((w_i * res_i)^2) → pasar sqrt(peso)
    b1, _ = np.polyfit(x, y, 1, w=np.sqrt(w))
    xw = float(np.sum(w * x) / np.sum(w))
    yw = float(np.sum(w * y) / np.sum(w))
    pred = yw + phi * float(b1) * (x_next - xw)
    # sigma = error típico del PROPIO predictor sobre los datos vistos
    res = y - (yw + phi * b1 * (x - xw))
    sigma = float(np.sqrt(np.sum(w * res ** 2) / np.sum(w)))
    n = len(x)
    if n > 2:                       # corrección por grados de libertad
        sigma *= float(np.sqrt(n / (n - 2)))
    return float(pred), max(sigma, PISO_SIGMA)


def simula_carrera(preds, sigmas, n=4000, seed=7):
    """Monte Carlo: n carreras simuladas → (p_mas_rapido, p_top3) por equipo."""
    m = np.asarray(preds, dtype=float)
    s = np.asarray(sigmas, dtype=float)
    rng = np.random.default_rng(seed)
    muestras = rng.normal(m, s, size=(n, len(m)))
    orden = muestras.argsort(axis=1)
    p_win = np.bincount(orden[:, 0], minlength=len(m)) / n
    k = min(3, len(m))
    p_top3 = np.bincount(orden[:, :k].ravel(), minlength=len(m)) / n
    return p_win.tolist(), p_top3.tolist()


def backtesta(series, min_prev=3, media_vida=MEDIA_VIDA, phi=PHI):
    """Re-juega la temporada: en cada ronda entrena con las anteriores.

    series: {equipo: [(ronda, deficit), ...]} (se ordena internamente).
    Devuelve {"mae", "mae_base", "aciertos", "total"} o None si no hay
    suficientes rondas evaluables. mae_base = baseline "repetir la última".
    """
    series = {t: sorted(pts) for t, pts in series.items()}
    rondas = sorted({r for pts in series.values() for r, _ in pts})
    err_mod, err_base = [], []
    aciertos = total = 0
    for k in rondas:
        preds, reales = {}, {}
        for team, pts in series.items():
            prev = [(r, v) for r, v in pts if r < k]
            real = [v for r, v in pts if r == k]
            if len(prev) < min_prev or not real:
                continue
            p = predice([r for r, _ in prev], [v for _, v in prev], k,
                        media_vida, phi)
            preds[team], reales[team] = p[0], real[0]
            err_mod.append(abs(p[0] - real[0]))
            err_base.append(abs(prev[-1][1] - real[0]))
        if len(preds) >= 3:
            total += 1
            if min(preds, key=preds.get) == min(reales, key=reales.get):
                aciertos += 1
    if not err_mod or total == 0:
        return None
    return {"mae": round(float(np.mean(err_mod)), 3),
            "mae_base": round(float(np.mean(err_base)), 3),
            "aciertos": aciertos, "total": total}
