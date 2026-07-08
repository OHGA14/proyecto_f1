"""Componentes de UI Streamlit: tarjetas, tablas, guías, grid de pilotos."""
import re
import html
import textwrap

import pandas as pd
import numpy as np
import streamlit as st

from f1core.config import (DIST_CHART_CONFIG, MICRO_PURPLE, MICRO_GREEN,
                           MICRO_YELLOW, COMPOUND_COLORS)
from f1core.colors import get_neon_color, get_driver_info, get_driver_name, _hex_to_rgb
from f1core.timeutils import format_time, _format_sector_time
from f1core.laps import _mark_outlier_laps


def plot_wide(fig, config=None):
    """Muestra una gráfica a todo el ancho con el zoom profesional activado."""
    st.plotly_chart(fig, use_container_width=True, config=config or DIST_CHART_CONFIG)

def render_clean_metric_table(df_or_dict, numeric_fmt='{:.3f}', col1="Piloto", col2="Valores", title=None, caption=None):

    """Render a minimal HTML metric table.

    Accepts a DataFrame (single-row) or a list/dict of summaries.

    Produces a clean, horizontal-rule-only table with right-aligned numbers.

    col1/col2 nombran las columnas; title/caption añaden un encabezado que
    explica qué mide la tabla (para que no aparezca un genérico 'Metric/Value').

    """

    header = ''
    if title:
        header += f'<div style="font-weight:600;color:#ddd;font-size:14px;margin-top:6px;">{html.escape(str(title))}</div>'
    if caption:
        header += f'<div style="color:#888;font-size:12px;margin-bottom:4px;">{html.escape(str(caption))}</div>'

    # Normalize input to list of rows

    rows = []

    if isinstance(df_or_dict, dict):

        rows = list(df_or_dict.items())

    elif isinstance(df_or_dict, pd.DataFrame):

        if len(df_or_dict) == 1:

            rows = [(col, df_or_dict.iloc[0][col]) for col in df_or_dict.columns]

        else:

            # For multi-row DF, show each row as a labeled dict

            rows = [(str(i), r.to_dict()) for i, r in df_or_dict.iterrows()]

    elif isinstance(df_or_dict, (list, tuple)):

        rows = list(df_or_dict)

    else:

        try:

            rows = list(dict(df_or_dict).items())

        except Exception:

            rows = []

    # Build HTML

    html_table = [header + '<table style="width:100%;">']

    html_table.append('<thead><tr>')

    html_table.append(f'<th style="padding:8px 6px; color:#AAA; font-family:Roboto, sans-serif;">{html.escape(str(col1))}</th>')

    html_table.append(f'<th style="padding:8px 6px; color:#AAA; font-family:Roboto, sans-serif; text-align:right;">{html.escape(str(col2))}</th>')

    html_table.append('</tr></thead>')

    html_table.append('<tbody>')

    for k, v in rows:

        # format numbers neatly

        if isinstance(v, (int, float, np.floating, np.integer)):

            val = numeric_fmt.format(v)

        else:

            val = html.escape(str(v))

        html_table.append(f'<tr><td style="padding:8px 6px; color:#DDD;">{html.escape(str(k))}</td><td style="padding:8px 6px; text-align:right; color:#DDD;">{val}</td></tr>')

    html_table.append('</tbody></table>')

    return textwrap.dedent(''.join(html_table))

def html_preserve_spaces_smart(text, width=80):

    """Función más inteligente que preserva secuencias de espacios

    visibles sin romper por completo el wrapping. Reemplaza n espacios

    por (n-1) `&nbsp;` + ' ' para mantener la apariencia y permitir quiebres.

    """

    wrapped = textwrap.fill(text, width=width, replace_whitespace=False, drop_whitespace=False)

    escaped = html.escape(wrapped)

    def repl(m):

        s = m.group(0)

        if len(s) == 1:

            return ' '

        return '&nbsp;' * (len(s) - 1) + ' '

    result = re.sub(r' +', repl, escaped)

    return textwrap.dedent(f'<div style="white-space: pre-wrap;">{result}</div>')

def render_driver_card(name, pos_str, time_str, lap_title, lap_caption, lap_value, color, desc=None, champ_pts=None, phase_stats=None):

    """Construye el HTML de la tarjeta de piloto sin sangrías en el string

    para evitar problemas de espacios por la indentación del código.

    `desc` puede ser texto libre; si se proporciona, se procesa con

    `html_preserve_spaces_smart` para mantener múltiples espacios.

    """

    name_esc = html.escape(name)

    pos_esc = html.escape(pos_str)

    time_esc = html.escape(time_str)

    lap_title_esc = html.escape(str(lap_title))
    lap_caption_esc = html.escape(str(lap_caption))
    lap_value_esc = html.escape(str(lap_value))

    desc_html = html_preserve_spaces_smart(desc) if desc else ''

    pts_html = ''
    if champ_pts is not None:
        _pts_txt = f'{int(champ_pts)}' if float(champ_pts).is_integer() else f'{champ_pts:g}'
        pts_html = (f'<span class="dc-pts" title="Puntos del campeonato de pilotos a la altura de este GP">'
                    f'{_pts_txt} pts</span>')

    bars_html = ''
    if phase_stats is not None:
        _ft, _hb, _cn = phase_stats

        def _dcbar(_lbl, _val, _col):
            _w = max(0.0, min(_val, 100.0))
            return (f'<div class="dc-brow"><span class="dc-blab">{_lbl}</span>'
                    f'<div class="dc-btrack"><div class="dc-bfill" style="width:{_w:.0f}%;background:{_col};"></div></div>'
                    f'<span class="dc-bval">{_val:.0f}%</span></div>')
        bars_html = ('<div class="dc-bars" title="% del tiempo de la vuelta">'
                     + _dcbar('A fondo', _ft, '#00E676')
                     + _dcbar('Frenada', _hb, '#FF5252')
                     + _dcbar('En curva', _cn, '#F2C94C')
                     + '</div>')

    card = (
        f'<div class="driver-card" style="--tc:{color}; background:linear-gradient(155deg,{color}1f,rgba(255,255,255,0.012));">'
        f'<div class="dc-head">'
        f'<div style="display:flex;align-items:baseline;gap:9px;min-width:0;">'
        f'<div class="dc-name" style="color:{color};">{name_esc.split()[-1].upper()}</div>'
        f'{pts_html}'
        f'</div>'
        f'<div class="dc-pos" style="background:{color};">{pos_esc}</div>'
        f'</div>'
        f'<div class="dc-body">'
        f'<div>'
        f'<div class="dc-label">{lap_title_esc}</div>'
        f'<div class="dc-time">{time_esc}</div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<div class="dc-label">{lap_caption_esc}</div>'
        f'<div class="dc-lapval">{lap_value_esc}</div>'
        f'</div>'
        f'</div>'
        f'{bars_html}'
        f'{desc_html}'
        f'</div>'
    )

    return textwrap.dedent(card)

def show_insight(title, text):

    """Muestra un cuadro de insight con título escapado y texto pasado

    por la preservación inteligente de espacios.

    """

    title_esc = html.escape(title)

    text_html = html_preserve_spaces_smart(text) if text else ''

    content = (

        f'<div class="insight-box">'

        f'<div class="insight-title">ℹ {title_esc}</div>'

        f'{text_html}'

        f'</div>'

    )

    st.markdown(textwrap.dedent(content), unsafe_allow_html=True)

def render_broadcast_title(gp, year, session):

    """Construye el bloque de título principal sin sangrías que puedan

    colarse desde la indentación del código.

    """

    gp_esc = html.escape(str(gp).upper())

    session_esc = html.escape(str(session))

    year_esc = html.escape(str(year))

    return textwrap.dedent(

        '<style>'
        '@keyframes hc-flagwave{0%,100%{transform:perspective(140px) rotateY(0deg) skewX(0deg);}'
        '25%{transform:perspective(140px) rotateY(-10deg) skewX(-5deg);}'
        '50%{transform:perspective(140px) rotateY(0deg) skewX(0deg);}'
        '75%{transform:perspective(140px) rotateY(10deg) skewX(5deg);}}'
        '.hc-flag{display:inline-block;width:46px;height:31px;flex:0 0 auto;border:1px solid #4a4a4a;'
        'border-radius:2px;box-shadow:0 2px 7px rgba(0,0,0,.55);transform-origin:left center;'
        'animation:hc-flagwave 1.7s ease-in-out infinite;'
        'background:conic-gradient(#111 25%,#f4f4f4 0 50%,#111 0 75%,#f4f4f4 0);background-size:15.4px 15.4px;}'
        '</style>'

        f'<div style="border-left: 6px solid #333; padding-left: 20px; margin-top: 10px; margin-bottom: 30px;">'

        f'<h1 style="margin: 0; line-height: 1; font-size: 48px; font-weight: 800; font-style: italic; letter-spacing: -1px; display: flex; align-items: center; gap: 18px;">'
        f'<span class="hc-flag"></span><span>{gp_esc} {year_esc}</span></h1>'

        f'<h3 style="margin: 8px 0 0 0; font-size: 24px; font-weight: 400; color: #888; letter-spacing: 0.5px;">{session_esc} SESSION | DATA ANALYTICS</h3>'

        f'</div>'

    )

def render_summary_card(driver_name, color, title_val, main_value, sub_stats=None):

    """

    Genera una tarjeta de resumen estandarizada para gráficas.

    

    Args:

        driver_name (str): Nombre del piloto.

        color (str): Color hexadecimal del equipo.

        title_val (str): Título/etiqueta de la métrica principal (ej: 'Vel Max', 'Mediana').

        main_value: Valor principal a mostrar (número).

        sub_stats (dict): Diccionario opcional de estadísticas secundarias {label: value}.

    

    Returns:

        str: HTML limpio sin sangría (ya processado con textwrap.dedent).

    """

    if sub_stats is None:

        sub_stats = {}

    

    # Convertir valores a strings seguros

    driver_name = str(driver_name)

    main_value = str(main_value)

    

    # Construir HTML sin indentación

    card_html = (

        '<div style="flex:1 1 220px;min-width:180px;background:rgba(255,255,255,0.02);border-radius:8px;'

        f'border-left:6px solid {color};padding:10px;font-family:Roboto;color:#ddd;">'

        '<div style="display:flex;justify-content:space-between;align-items:flex-start;">'

        f'<div><div style="font-family:Roboto;font-weight:700;color:{color};font-size:13px;">{driver_name}</div>'

        f'<div style="margin-top:4px;font-size:12px;color:#999;">{title_val}</div></div></div>'

        '<div style="margin-top:8px;color:#fff;font-size:18px;font-weight:700;">'

        f'{main_value}'

        '</div>'

    )

    

    # Añadir estadísticas secundarias si existen

    if sub_stats:

        card_html += '<div style="margin-top:6px;color:#ccc;font-size:12px;line-height:1.6;border-top:1px solid rgba(255,255,255,0.06);padding-top:6px;">'

        for label, value in sub_stats.items():

            safe_label = html.escape(str(label))

            safe_value = html.escape(str(value))

            card_html += f'<div>{safe_label}: <b style="color:#AAA;">{safe_value}</b></div>'

        card_html += '</div>'

    

    card_html += '</div>'

    

    return textwrap.dedent(card_html)

def render_microsector_legend():
    st.markdown(
        f"<div style='font-size:12px;color:#aaa;margin-top:4px;'>"
        f"<span style='color:{MICRO_PURPLE};font-weight:700;'>■</span> Más rápido &nbsp;·&nbsp; "
        f"<span style='color:{MICRO_GREEN};font-weight:700;'>■</span> Empate (&lt;0.02s) &nbsp;·&nbsp; "
        f"<span style='color:{MICRO_YELLOW};font-weight:700;'>■</span> Más lento &nbsp;·&nbsp; "
        f"la franja bajo cada sector = color del piloto que ganó ese sector</div>",
        unsafe_allow_html=True
    )

def render_theoretical_best(sector_summary, color_map, unit_label="vuelta"):
    """Sorpresa: 'vuelta perfecta' combinando el mejor tiempo de cada sector
    entre las opciones comparadas, y cuánto ganaría cada uno con ella."""
    if not sector_summary:
        return
    labels = list(sector_summary[0]["times"].keys())
    best_lap = sum(min(sec["times"].values()) for sec in sector_summary)
    totals = {l: sum(sec["times"][l] for sec in sector_summary) for l in labels}
    real_best_label = min(totals, key=totals.get)
    real_best = totals[real_best_label]
    gain = real_best - best_lap

    chips = ""
    for sec in sector_summary:
        wl = sec["winner"]
        wc = color_map.get(wl, MICRO_PURPLE)
        chips += (
            f"<span style='display:inline-block;margin:2px 6px 2px 0;padding:3px 8px;border-radius:6px;"
            f"background:rgba(255,255,255,0.04);border-left:3px solid {wc};font-size:12px;'>"
            f"{sec['sector']}: <b style='color:{wc};'>{wl}</b> {sec['times'][wl]:.3f}s</span>"
        )

    st.markdown(
        f"<div style='background:rgba(176,38,255,0.06);border:1px solid rgba(176,38,255,0.35);"
        f"border-radius:8px;padding:10px 14px;margin-top:8px;'>"
        f"<div style='color:{MICRO_PURPLE};font-weight:700;font-size:13px;margin-bottom:4px;'>"
        f"Vuelta perfecta (mejor sector de cada uno)</div>"
        f"<div style='font-size:22px;font-weight:700;color:#fff;'>{format_time(best_lap)}</div>"
        f"<div style='font-size:12px;color:#bbb;margin:4px 0;'>{chips}</div>"
        f"<div style='font-size:12px;color:#999;'>Sería <b style='color:{MICRO_PURPLE};'>{gain:.3f}s</b> "
        f"más rápida que la mejor {unit_label} real ({format_time(real_best)}).</div>"
        f"</div>",
        unsafe_allow_html=True
    )

def render_chart_guide(summary_text=None, how_to_read=None, key=None):
    """Debajo de cada gráfica: un resumen calculado con datos reales y un
    desplegable que explica cómo leer la gráfica. Nada inventado: el resumen
    debe construirse siempre a partir de los datos ya calculados."""
    if summary_text:
        show_insight("Resumen (calculado con los datos de la sesión)", summary_text)
    if how_to_read:
        with st.expander("¿Cómo leer esta gráfica?"):
            st.markdown(how_to_read)

def render_driver_grid(driver_opts, n_cols=3, state_key="grid_sel"):
    """Selector de pilotos tipo 'chips' con color de equipo (toggle multi-selección).
    Devuelve la lista de códigos seleccionados en el orden en que se marcaron
    (el 1º y 2º mandan como A/B en las comparaciones)."""
    if state_key not in st.session_state:
        st.session_state[state_key] = list(driver_opts[:2])
    # Preservar orden y limpiar códigos que ya no existan en la sesión
    st.session_state[state_key] = [d for d in st.session_state[state_key] if d in driver_opts]
    sel = st.session_state[state_key]

    qa, qb = st.columns(2)
    with qa:
        if st.button("Todos", key="drvgrid_all", use_container_width=True):
            st.session_state[state_key] = list(driver_opts)
            sel = st.session_state[state_key]
    with qb:
        if st.button("Limpiar", key="drvgrid_clear", use_container_width=True):
            st.session_state[state_key] = []
            sel = st.session_state[state_key]

    css = ["<style>"]
    cols = st.columns(n_cols)
    for i, d in enumerate(driver_opts):
        with cols[i % n_cols]:
            if st.button(d, key=f"drvgrid_{d}", use_container_width=True, help=get_driver_name(d)):
                if d in sel:
                    sel.remove(d)
                else:
                    sel.append(d)
        color = get_neon_color(d)
        r, g, b = _hex_to_rgb(color)
        if d in sel:
            css.append(
                f".st-key-drvgrid_{d} button {{ background: rgba({r},{g},{b},0.20) !important;"
                f" border: 2px solid {color} !important; color: {color} !important;"
                f" font-weight: 800 !important; border-radius: 8px !important; }}"
            )
        else:
            css.append(
                f".st-key-drvgrid_{d} button {{ background: rgba(255,255,255,0.015) !important;"
                f" border: 1px solid rgba({r},{g},{b},0.40) !important; color: rgba({r},{g},{b},0.85) !important;"
                f" font-weight: 700 !important; border-radius: 8px !important; }}"
            )
    css.append("</style>")
    st.markdown("\n".join(css), unsafe_allow_html=True)
    st.caption(f"Seleccionados: {len(sel)}")
    return list(sel)

def render_gp_tempo_table(laps_vip_df, drivers, lap_from, lap_to):
    """Tabla estilo GP Tempo: filas = pilotos, columnas = vueltas.
    Cada celda muestra el tiempo con un punto del color del compuesto;
    vueltas atípicas van tachadas."""
    header_cells = ''.join(
        f'<th style="padding:10px 14px;text-align:center;color:#fff;font-size:15px;">{ln}</th>'
        for ln in range(lap_from, lap_to + 1)
    )
    rows_html = ''
    for d in drivers:
        df = laps_vip_df[laps_vip_df['Driver'] == d].sort_values('LapNumber').copy()
        df['IsOutlier'] = _mark_outlier_laps(df) if not df.empty else pd.Series(dtype=bool)
        by_lap = {int(r['LapNumber']): r for _, r in df.iterrows()}
        c = get_neon_color(d)
        cells = ''
        for ln in range(lap_from, lap_to + 1):
            r = by_lap.get(ln)
            if r is None or pd.isna(r.get('Seconds', np.nan)):
                inner = '<span style="color:#777;">N/A</span>'
                comp_dot = ''
            else:
                t_txt = format_time(r['Seconds'])
                style = 'text-decoration:line-through;color:#888;' if bool(r.get('IsOutlier', False)) else 'color:#eee;'
                inner = f'<span style="{style}">{t_txt}</span>'
                comp = str(r.get('Compound', '')).upper() if pd.notna(r.get('Compound', None)) else 'UNKNOWN'
                comp_c = COMPOUND_COLORS.get(comp, COMPOUND_COLORS['UNKNOWN'])
                comp_dot = (
                    f'<span title="{html.escape(comp)}" style="display:inline-block;width:11px;height:11px;'
                    f'border-radius:50%;background:{comp_c};margin-left:6px;vertical-align:middle;"></span>'
                )
            cells += (
                '<td style="padding:8px 10px;text-align:center;white-space:nowrap;">'
                f'<span style="background:rgba(255,255,255,0.04);border:1px solid #333;border-radius:8px;'
                f'padding:6px 10px;font-size:13px;">{inner}{comp_dot}</span></td>'
            )
        rows_html += (
            f'<tr style="border-top:1px solid rgba(255,255,255,0.06);">'
            f'<td style="padding:8px 12px;font-weight:700;color:{c};position:sticky;left:0;'
            f'background:#0e1117;z-index:1;">{d}</td>{cells}</tr>'
        )

    table = (
        '<div style="overflow-x:auto;border:1px solid #333;border-radius:8px;margin-top:6px;">'
        '<table style="border-collapse:collapse;width:max-content;min-width:100%;">'
        f'<thead><tr><th style="padding:10px 12px;text-align:left;color:#fff;position:sticky;left:0;'
        f'background:#0e1117;z-index:2;">Lap:</th>{header_cells}</tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>'
    )
    st.markdown(table, unsafe_allow_html=True)

    legend = ' '.join(
        f'<span style="margin-right:14px;"><span style="display:inline-block;width:10px;height:10px;'
        f'border-radius:50%;background:{col};margin-right:4px;vertical-align:middle;"></span>'
        f'<span style="color:#aaa;font-size:12px;">{name.title()}</span></span>'
        for name, col in COMPOUND_COLORS.items() if name != 'UNKNOWN'
    )
    st.markdown(
        f'<div style="margin-top:6px;">{legend}'
        '<span style="color:#777;font-size:12px;margin-left:10px;">Tiempo tachado = vuelta atípica (pit / SC / outlier)</span></div>',
        unsafe_allow_html=True
    )
