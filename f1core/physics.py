"""Física del coche: fuerzas G, envolvente G-G, DTW, mini-sectores, suavizado."""
import pandas as pd
import numpy as np
from scipy.signal import savgol_filter


def _build_minisector_layout(tel_list, sector_cuts=None, mini_per_sector=8):
    """Construye los mini-sectores AGRUPADOS por sector de pista (S1/S2/S3).

    sector_cuts: lista [(label, dist_fin_acumulada)] de _get_sector_cut_distances.
    Cada sector se subdivide en `mini_per_sector` mini-sectores de distancia igual.
    Devuelve (cleaned, mini_bounds, mat) donde:
      - mini_bounds: lista de (sector_label, d0, d1) por mini-sector
      - mat: matriz (n_pilotos, n_mini) con el tiempo de cada mini-sector.
    """
    cleaned = []
    for label, tel in tel_list:
        if tel is None:
            return None, None, None
        t = tel.dropna(subset=['Distance', 'Time']).sort_values('Distance')
        if t.empty:
            return None, None, None
        cleaned.append((label, t))
    max_d = min(t['Distance'].max() for _, t in cleaned)
    min_d = max(t['Distance'].min() for _, t in cleaned)
    if not np.isfinite(max_d) or max_d <= min_d:
        return None, None, None

    # Rango de cada sector (S1/S2/S3). sector_cuts trae la distancia FINAL de cada sector.
    seg_ranges = []
    if sector_cuts:
        prev = min_d
        for s_lbl, end_d in sector_cuts:
            s0 = max(min_d, prev)
            s1 = min(max_d, float(end_d))
            if s1 > s0:
                seg_ranges.append((s_lbl, s0, s1))
            prev = float(end_d)
    if not seg_ranges:
        seg_ranges = [("Vuelta", min_d, max_d)]

    mini_bounds = []
    for s_lbl, s0, s1 in seg_ranges:
        edges = np.linspace(s0, s1, mini_per_sector + 1)
        for j in range(mini_per_sector):
            mini_bounds.append((s_lbl, edges[j], edges[j + 1]))

    n = len(mini_bounds)
    mat = np.zeros((len(cleaned), n))
    for row_i, (label, t) in enumerate(cleaned):
        dvals = t['Distance'].values
        tvals = t['Time'].dt.total_seconds().values
        for s, (_, d0, d1) in enumerate(mini_bounds):
            mat[row_i, s] = np.interp(d1, dvals, tvals) - np.interp(d0, dvals, tvals)
    return cleaned, mini_bounds, mat

def compute_gg_from_telemetry(tel, dist_step=5.0):
    """Calcula G lateral y longitudinal sobre una MALLA UNIFORME de distancia.

    Por qué: la telemetría de get_telemetry() mezcla datos de coche y posición
    con timestamps irregulares (dt de 0.004s a 0.22s); derivar velocidad contra
    ese tiempo produce picos falsos de ±30G. Remuestreando cada 5 m y suavizando
    salen valores físicos (~1.5G tracción, ~5G frenada, ~5-6G lateral).

    Además FastF1 entrega X/Y en DECÍMETROS: sin convertir a metros la curvatura
    sale 10x menor y la G lateral queda aplastada cerca de 0.
    """
    t = tel.copy()
    if 'Distance' not in t.columns:
        t = t.add_distance()
    t_clean = t.dropna(subset=['X', 'Y', 'Speed', 'Time', 'Distance']).copy()
    if len(t_clean) < 15:
        return None

    dist = t_clean['Distance'].values
    time_s = t_clean['Time'].dt.total_seconds().values
    speed_ms = t_clean['Speed'].values / 3.6
    x = t_clean['X'].values / 10.0
    y = t_clean['Y'].values / 10.0

    d_grid = np.arange(dist.min(), dist.max(), dist_step)
    if len(d_grid) < 15:
        return None
    v = np.interp(d_grid, dist, speed_ms)
    t_g = np.interp(d_grid, dist, time_s)
    x_g = np.interp(d_grid, dist, x)
    y_g = np.interp(d_grid, dist, y)

    win = 11 if len(d_grid) > 11 else max((len(d_grid) // 2) * 2 - 1, 3)
    v = savgol_filter(v, win, 2)
    x_g = savgol_filter(x_g, win, 2)
    y_g = savgol_filter(y_g, win, 2)

    glong = np.gradient(v, t_g) / 9.81
    glong = savgol_filter(glong, win, 2)

    dx = np.gradient(x_g, dist_step)
    dy = np.gradient(y_g, dist_step)
    d2x = np.gradient(dx, dist_step)
    d2y = np.gradient(dy, dist_step)
    cross = dx * d2y - dy * d2x
    denominator = np.power(dx ** 2 + dy ** 2, 1.5)
    curvature = np.where(denominator > 1e-9, np.abs(cross) / np.maximum(denominator, 1e-9), 0.0)
    sign_factor = np.sign(cross)
    sign_factor[sign_factor == 0] = 1
    glat = (v ** 2 * curvature) / 9.81 * sign_factor
    glat = savgol_filter(glat, win, 2)

    glat = np.nan_to_num(glat, nan=0, posinf=0, neginf=0)
    glong = np.nan_to_num(glong, nan=0, posinf=0, neginf=0)

    # Descartar picos físicamente imposibles residuales y los bordes de la
    # vuelta, donde el gradiente numérico es poco fiable.
    valid = (np.abs(glat) <= 6.5) & (np.abs(glong) <= 6.5)
    if len(valid) > 10:
        valid[:3] = False
        valid[-3:] = False
    if valid.sum() < 15:
        return None

    def _grid_channel(col, as_int=False):
        if col not in t_clean.columns:
            return None
        try:
            vals = t_clean[col].astype(float).values
        except (TypeError, ValueError):
            return None
        finite = np.isfinite(vals)
        if finite.sum() < 2:
            return None
        arr = np.interp(d_grid, dist[finite], vals[finite])
        if as_int:
            arr = np.round(arr)
        return arr[valid]

    data = {
        "glat": glat[valid],
        "glong": glong[valid],
        "speed_kmh": (v * 3.6)[valid],
        "distance": d_grid[valid],
        "gear": _grid_channel('nGear', as_int=True),
        "throttle": _grid_channel('Throttle'),
        "brake": _grid_channel('Brake')
    }
    return data

def build_gg_envelope(glat, glong, percentile=95, bins=48):
    r = np.sqrt(glat**2 + glong**2)
    ang = np.arctan2(glong, glat)
    edges = np.linspace(-np.pi, np.pi, bins + 1)
    pts = []
    for i in range(bins):
        mask = (ang >= edges[i]) & (ang < edges[i + 1])
        if np.any(mask):
            r_p = np.percentile(r[mask], percentile)
            ang_mid = (edges[i] + edges[i + 1]) / 2
            pts.append((ang_mid, r_p))
    if len(pts) < 6:
        return None
    angs = np.array([p[0] for p in pts])
    rs = np.array([p[1] for p in pts])
    xs = rs * np.cos(angs)
    ys = rs * np.sin(angs)
    xs = np.append(xs, xs[0])
    ys = np.append(ys, ys[0])
    return xs, ys

def _dtw_distance(a, b):
    """Dynamic Time Warping entre dos series 1D (numpy o lista). Devuelve
    (coste_total, camino), donde camino = lista de pares (i, j) del alineamiento
    óptimo. Implementación pura en Python (rápida para ~200-300 puntos) para no
    depender de librerías externas (fastdtw, tslearn…)."""
    a = [float(x) for x in a]
    b = [float(x) for x in b]
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return float('nan'), []
    INF = float('inf')
    D = [[INF] * (m + 1) for _ in range(n + 1)]
    D[0][0] = 0.0
    for i in range(1, n + 1):
        ai = a[i - 1]
        Di = D[i]
        Dprev = D[i - 1]
        for j in range(1, m + 1):
            c = ai - b[j - 1]
            if c < 0:
                c = -c
            best = Dprev[j]
            v2 = Di[j - 1]
            if v2 < best:
                best = v2
            v3 = Dprev[j - 1]
            if v3 < best:
                best = v3
            Di[j] = c + best
    # Backtrack: reconstruye el camino óptimo desde la esquina final
    i, j = n, m
    path = [(i - 1, j - 1)]
    while i > 1 or j > 1:
        if i == 1:
            j -= 1
        elif j == 1:
            i -= 1
        else:
            d1 = D[i - 1][j - 1]
            d2 = D[i - 1][j]
            d3 = D[i][j - 1]
            if d1 <= d2 and d1 <= d3:
                i -= 1
                j -= 1
            elif d2 <= d3:
                i -= 1
            else:
                j -= 1
        path.append((i - 1, j - 1))
    path.reverse()
    return D[n][m], path

def _adaptive_smooth(series, base_window=3, max_window=5):
    n = len(series)
    w = min(max_window, max(2, n // 8)) if n >= base_window else 1
    return series.rolling(window=w, min_periods=1, center=True).mean()
