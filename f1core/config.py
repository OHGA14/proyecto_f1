"""Constantes y datos maestros: pilotos, equipos, colores, sesiones."""


DRIVER_DB = {

    # ── 2026 PARRILLA OFICIAL ──────────────────────────────────────────────────

    # Cada equipo mantiene su tono, pero los DOS pilotos usan colores distintos
    # (piloto 1 = color base del equipo, piloto 2 = variante clara) para poder
    # distinguirlos en las gráficas.

    # Red Bull (base #27508C)
    'VER': {'name': 'Max Verstappen',    'color': '#27508C'},
    'HAD': {'name': 'Isack Hadjar',      'color': '#6E9BD8'},

    # Ferrari (base #A20020)
    'LEC': {'name': 'Charles Leclerc',   'color': '#A20020'},
    'HAM': {'name': 'Lewis Hamilton',    'color': '#F23D57'},

    # Mercedes (base #18BFA3)
    'RUS': {'name': 'George Russell',    'color': '#18BFA3'},
    'ANT': {'name': 'Kimi Antonelli',    'color': '#7CF0DC'},

    # McLaren (base #BE5F00)
    'NOR': {'name': 'Lando Norris',      'color': '#BE5F00'},
    'PIA': {'name': 'Oscar Piastri',     'color': '#FFA24A'},

    # Aston Martin (base #17664B)
    'ALO': {'name': 'Fernando Alonso',   'color': '#17664B'},
    'STR': {'name': 'Lance Stroll',      'color': '#46C293'},

    # Alpine (base ROSA #FF2E9A)
    'GAS': {'name': 'Pierre Gasly',      'color': '#FF2E9A'},
    'COL': {'name': 'Franco Colapinto',  'color': '#FF9AD1'},

    # Williams (base #0E3D80)
    'SAI': {'name': 'Carlos Sainz',      'color': '#0E3D80'},
    'ALB': {'name': 'Alexander Albon',   'color': '#4E8AD6'},

    # Audi (base #B82100)
    'HUL': {'name': 'Nico Hülkenberg',   'color': '#B82100'},
    'BOR': {'name': 'Gabriel Bortoleto', 'color': '#FF6A45'},

    # Haas (base #A7AEB0)
    'OCO': {'name': 'Esteban Ocon',      'color': '#A7AEB0'},
    'BEA': {'name': 'Oliver Bearman',    'color': '#6C7376'},

    # Racing Bulls (base #3062DE)
    'LAW': {'name': 'Liam Lawson',       'color': '#3062DE'},
    'LIN': {'name': 'Arvid Lindblad',    'color': '#8DAAF2'},

    # Cadillac (base #79797C)
    'PER': {'name': 'Sergio Pérez',      'color': '#A6A6AA'},
    'BOT': {'name': 'Valtteri Bottas',   'color': '#5A5A5E'},

    # ── PILOTOS HISTÓRICOS (compatibilidad sesiones anteriores) ───────────────
    'TSU': {'name': 'Yuki Tsunoda',      'color': '#6692FF'},
    'RIC': {'name': 'Daniel Ricciardo',  'color': '#6692FF'},
    'MAG': {'name': 'Kevin Magnussen',   'color': '#B6BABD'},
    'ZHO': {'name': 'Zhou Guanyu',       'color': '#52E252'},
    'SAR': {'name': 'Logan Sargeant',    'color': '#37BEDD'},
    'DEV': {'name': 'Nyck de Vries',     'color': '#6692FF'},
    'HUL_OLD': {'name': 'Nico Hülkenberg (2024)', 'color': '#52E252'},

}

DRIVER_COLORS = {abbr: info['color'] for abbr, info in DRIVER_DB.items()}

TEAM_COLORS = {
    # ── 2026 ──────────────────────────────────────────────────────────────────
    "Red Bull":        "#27508C",
    "Red Bull Racing": "#27508C",
    "Ferrari":         "#A20020",
    "Mercedes":        "#18BFA3",
    "McLaren":         "#BE5F00",
    "Aston Martin":    "#17664B",
    "Alpine":          "#FF2E9A",
    "Williams":        "#0E3D80",
    "Audi":            "#B82100",
    "Haas":            "#A7AEB0",
    "Haas F1 Team":    "#A7AEB0",
    "Racing Bulls":    "#3062DE",
    "RB":              "#3062DE",
    "Cadillac":        "#79797C",
    "Cadillac F1":     "#79797C",
    # ── Compatibilidad temporadas anteriores ──────────────────────────────────
    "Kick Sauber":     "#52E252",
    "Sauber":          "#52E252",
    "AlphaTauri":      "#4E7C9B",
    "Toro Rosso":      "#4E7C9B",
}

_TEAM_COLORS_NORM = {k.lower(): v for k, v in TEAM_COLORS.items()}

DIST_CHART_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "scrollZoom": False,  # evita el zoom accidental al mover la ruedita del ratón
    "doubleClick": "reset",
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
}

MICRO_PURPLE = "#B026FF"
MICRO_GREEN = "#00E676"
MICRO_YELLOW = "#F2C94C"

COMPOUND_COLORS = {
    'SOFT': '#FF3333',
    'MEDIUM': '#FFD500',
    'HARD': '#EAEAEA',
    'INTERMEDIATE': '#43B02A',
    'WET': '#0067AD',
    'UNKNOWN': '#888888'
}

SESSION_SHORT = {
    'Practice 1': 'FP1', 'Practice 2': 'FP2', 'Practice 3': 'FP3',
    'Sprint Qualifying': 'Sprint Quali', 'Sprint Shootout': 'Sprint Shootout',
    'Sprint': 'Sprint', 'Qualifying': 'Qualy', 'Race': 'Carrera',
}
