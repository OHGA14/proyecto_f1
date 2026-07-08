"""Colores de pilotos/equipos y mapa de colores consciente de la selección."""
import colorsys

from f1core.config import DRIVER_DB, DRIVER_COLORS, TEAM_COLORS, _TEAM_COLORS_NORM


def set_selection_colors(mapping):
    """Rellena el mapa global que get_neon_color/get_driver_color consultan primero."""
    global _SELECTION_COLORS
    _SELECTION_COLORS = dict(mapping or {})


def get_driver_info(abbr): return DRIVER_DB.get(abbr, {'name': abbr, 'color': '#FFFFFF'})

def get_driver_name(abbr): return get_driver_info(abbr)['name']

def get_neon_color(abbr):
    if abbr in _SELECTION_COLORS:
        return _SELECTION_COLORS[abbr]
    return get_driver_info(abbr)['color']

_SELECTION_COLORS = {}

def _hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

def _rgb_to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)

def _adjust_luminance(hex_color, factor):
    r, g, b = _hex_to_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    l = min(max(l * factor, 0), 1)
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
    return _rgb_to_hex((int(r2 * 255), int(g2 * 255), int(b2 * 255)))

def maybe_adjust_if_same(color_a, color_b):
    if color_a.strip().lower() == color_b.strip().lower():
        return _adjust_luminance(color_a, 1.2), _adjust_luminance(color_b, 0.8)
    return color_a, color_b

_team_col_warned = False

def _get_team_column(laps_df):
    global _team_col_warned
    for col in ("Team", "TeamName", "Constructor", "ConstructorName"):
        if col in laps_df.columns:
            return col
    if not _team_col_warned:
        print(f"[f1core] No se encontró columna de equipo en laps. Columnas disponibles: {list(laps_df.columns)}")
        _team_col_warned = True
    return None

def _get_team_for_driver(laps_df, driver_code):
    col = _get_team_column(laps_df)
    if not col:
        return None
    subset = laps_df[laps_df['Driver'] == driver_code]
    if subset.empty and 'Abbreviation' in laps_df.columns:
        subset = laps_df[laps_df['Abbreviation'] == driver_code]
    if subset.empty:
        return None
    return subset.iloc[0][col]

def get_driver_color(driver_code, laps_df):
    if driver_code in _SELECTION_COLORS:
        return _SELECTION_COLORS[driver_code]
    if driver_code in DRIVER_COLORS:
        return DRIVER_COLORS[driver_code]
    team_name = _get_team_for_driver(laps_df, driver_code)
    if isinstance(team_name, str):
        team_color = _TEAM_COLORS_NORM.get(team_name.lower())
        if team_color:
            return team_color
    return "#AAAAAA"

def _distinct_teammate_color(base_hex, order):
    """Color claramente distinto para el 2º+ piloto del mismo equipo: mezcla
    fuerte del color base hacia el blanco (queda pálido, muy diferente del color
    saturado del 1º, pero conserva el tono del equipo)."""
    r, g, b = _hex_to_rgb(base_hex)
    mix = 0.60 if order == 1 else min(0.60 + 0.18 * order, 0.85)
    r = int(r + (255 - r) * mix)
    g = int(g + (255 - g) * mix)
    b = int(b + (255 - b) * mix)
    return _rgb_to_hex((r, g, b))

def build_driver_colors(selected_codes, laps_df):
    """Colores conscientes de la selección. El 1º piloto de cada equipo usa el
    color BASE del equipo (color original); si hay un 2º compañero seleccionado,
    este recibe un color claramente distinto. Así un piloto solo se ve con el
    color de su escudería, y dos compañeros no se confunden."""
    out = {}
    team_count = {}
    used = []
    for d in selected_codes:
        team = _get_team_for_driver(laps_df, d)
        if isinstance(team, str) and team.strip():
            team_key = team.strip().lower()
            base = _TEAM_COLORS_NORM.get(team_key) or get_driver_info(d)['color']
        else:
            team_key = f"__{d}__"
            base = get_driver_info(d)['color']
        order = team_count.get(team_key, 0)
        team_count[team_key] = order + 1
        color = base if order == 0 else _distinct_teammate_color(base, order)
        guard = 0
        while color.lower() in [c.lower() for c in used] and guard < 6:
            color = _adjust_luminance(color, 1.22)
            guard += 1
        out[d] = color
        used.append(color)
    return out
