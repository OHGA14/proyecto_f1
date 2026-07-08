"""PANORAMA: visión general de rendimiento."""
import html
from app.components import render_chart_guide
from app.components import render_summary_card
from app.components import show_insight
from f1core.charts import build_gp_tempo_chart
from f1core.charts import make_god_chart
from f1core.colors import get_driver_color
from f1core.colors import get_driver_name
from f1core.colors import get_neon_color
from f1core.laps import _filter_pace_laps
from f1core.laps import _mark_outlier_laps
from f1core.timeutils import format_time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
# @IMPORTS@  (generado por fix_names)


def render(ctx):
    laps = ctx.get("laps")
    laps_vip = ctx.get("laps_vip")
    race = ctx.get("race")
    selected_abbr = ctx.get("selected_abbr")
    session = ctx.get("session")
    # @UNPACK@  (generado por fix_names)

    st.markdown("### PANORAMA: Visión General de Rendimiento")

    # --- SUMMARY INSIGHT ---

    if len(selected_abbr) >= 2:

        a, b = selected_abbr[0], selected_abbr[1]

        pace_a = _filter_pace_laps(laps.pick_driver(a), filter_outliers=True)

        pace_b = _filter_pace_laps(laps.pick_driver(b), filter_outliers=True)

        if len(pace_a) >= 3 and len(pace_b) >= 3:

            med_a, med_b = float(np.median(pace_a)), float(np.median(pace_b))

            delta_med = med_a - med_b

            faster = get_driver_name(a) if delta_med < 0 else get_driver_name(b)

            slower = get_driver_name(b) if delta_med < 0 else get_driver_name(a)

            iqr_a = float(np.percentile(pace_a, 75) - np.percentile(pace_a, 25))

            iqr_b = float(np.percentile(pace_b, 75) - np.percentile(pace_b, 25))

            more_consistent = get_driver_name(a) if iqr_a < iqr_b else get_driver_name(b)

            summary_cols_pan = st.columns(3)

            with summary_cols_pan[0]:

                st.metric("Más rápido", faster)

            with summary_cols_pan[1]:

                st.metric("Ventaja", f"{abs(delta_med):.3f}s")

            with summary_cols_pan[2]:

                st.metric("Más consistente", more_consistent)

            show_insight("Resumen de Sesión",
                f"{faster} fue {abs(delta_med):.3f}s más rápido que {slower} en mediana. "
                f"{more_consistent} fue más consistente (menor dispersión IQR)."
            )

    # --- SPEED TRAP METRICS ---

    st.divider()

    st.markdown("**VELOCIDAD MÁXIMA (SPEED TRAP)**")

    sp = laps_vip.dropna(subset=['SpeedST']).copy()

    sp = sp[sp['SpeedST'] > 0]

    if not sp.empty:

        speed_cols_pan = st.columns(len(selected_abbr))

        for i, d in enumerate(selected_abbr):

            df_sp = sp[sp['Driver'] == d]['SpeedST'].dropna()

            if not df_sp.empty:

                with speed_cols_pan[i]:

                    c = get_neon_color(d)

                    st.markdown(f"<span style='color:{c};font-weight:700;'>{get_driver_name(d)}</span>", unsafe_allow_html=True)

                    st.metric("Max", f"{df_sp.max():.1f} km/h")

                    st.metric("Mediana", f"{df_sp.median():.1f} km/h")

    else:

        st.info("No hay datos de Speed Trap disponibles.")

    st.divider()

    # --- BOX PLOT (from old stats tab) ---

    st.markdown("**FILTRADO ROBUSTO DE RITMO (IQR METHOD)**")

    laps_no_pit = laps_vip[laps_vip['IsPit'] == False].copy()

    if laps_no_pit.empty:

        st.info("No hay vueltas fuera de pits para analizar.")

    else:

        cleaned_frames = []

        for d in selected_abbr:

            df_d = laps_no_pit[laps_no_pit['Driver'] == d][['LapNumber', 'Seconds', 'Driver']].dropna(subset=['Seconds'])

            if df_d.empty:

                continue

            q1 = df_d['Seconds'].quantile(0.25)

            q3 = df_d['Seconds'].quantile(0.75)

            iqr = q3 - q1

            upper = q3 + 1.5 * iqr

            df_clean = df_d[df_d['Seconds'] <= upper]

            if not df_clean.empty:

                cleaned_frames.append(df_clean)

        if not cleaned_frames:

            st.info("Después del filtrado IQR no hay datos suficientes para mostrar Box Plot.")

        else:

            laps_clean = pd.concat(cleaned_frames)

            median_times = laps_clean.groupby('Driver')['Seconds'].median().sort_values()

            pilot_order = [d for d in median_times.index if d in selected_abbr]

            # BOX PLOT

            fig_box = go.Figure()

            for driver in pilot_order:

                data = laps_clean[laps_clean['Driver'] == driver]['Seconds']

                if data.empty:

                    continue

                color = get_neon_color(driver)

                name = get_driver_name(driver)

                fig_box.add_trace(go.Box(

                    y=data, name=name, marker=dict(color=color), boxpoints='outliers',

                    boxmean='sd', jitter=0.3, pointpos=-0.5,

                    hovertemplate="<b>%{fullData.name}</b><br>Tiempo: %{y:.3f}s<extra></extra>"

                ))

            # Línea de referencia = mediana del piloto más rápido (el "líder de ritmo")
            leader_median = float(median_times.iloc[0]) if not median_times.empty else None
            leader_driver = median_times.index[0] if not median_times.empty else None
            if leader_median is not None:
                fig_box.add_hline(
                    y=leader_median, line_dash="dot", line_color="rgba(0,242,255,0.55)", line_width=1.5,
                    annotation_text=f"Ritmo líder · {get_driver_name(leader_driver)}",
                    annotation_position="top left",
                    annotation_font_color="#00f2ff", annotation_font_size=11
                )

            fig_box = make_god_chart(fig_box, "DISTRIBUCIÓN DE RITMO (MEDIANA DE CARRERA)", "Tiempo de vuelta (s)", "Piloto", height=600)
            fig_box.update_yaxes(autorange="reversed")  # más rápido arriba (convención)

            st.plotly_chart(fig_box, use_container_width=True)

            # Resumen calculado: líder, gap al 2º y quién fue más regular (menor IQR)
            box_summary = None
            if not median_times.empty:
                iqr_map = {}
                for _d in pilot_order:
                    _g = laps_clean[laps_clean['Driver'] == _d]['Seconds'].dropna()
                    if len(_g) >= 2:
                        iqr_map[_d] = float(_g.quantile(0.75) - _g.quantile(0.25))
                box_fast = median_times.index[0]
                parts = [f"{get_driver_name(box_fast)} tiene el mejor ritmo mediano ({format_time(leader_median)})."]
                if len(median_times) > 1:
                    parts.append(f"El 2º ({get_driver_name(median_times.index[1])}) está a +{float(median_times.iloc[1] - leader_median):.3f}s/vuelta.")
                if iqr_map:
                    most_reg = min(iqr_map, key=iqr_map.get)
                    parts.append(f"El más regular fue {get_driver_name(most_reg)} (dispersión IQR de solo {iqr_map[most_reg]:.3f}s entre sus vueltas).")
                box_summary = " ".join(parts)
            render_chart_guide(
                summary_text=box_summary,
                how_to_read=(
                    "- **¿La caja de un piloto está más ARRIBA que las demás?** → tiene mejor ritmo (eje invertido: arriba = más rápido).\n"
                    "- **¿Su caja es CORTA (bajita)?** → es muy regular. **¿Es ALTA?** → su ritmo baila mucho de vuelta a vuelta.\n"
                    "- La **raya del centro** de la caja es su ritmo típico; la **línea cian punteada** es el ritmo del líder → mira a cuánto queda cada uno de ella.\n"
                    "- Rápido y regular NO son lo mismo: un piloto puede tener la caja arriba (rápido) pero alta (irregular).\n"
                    "- Los **puntos sueltos** por debajo son vueltas atípicas (tráfico, error); solo se usan vueltas limpias, sin pits ni Safety Car."
                )
            )

            # Estadísticas numéricas enriquecidas (por piloto)

            st.markdown("**RESUMEN DE RITMO (vueltas limpias por piloto)**")
            st.caption("Ordenado del más rápido al más lento por mediana. **Gap** = diferencia de ritmo mediano vs el líder · **IQR** = rango donde cae el 50% central de sus vueltas (dispersión) · **σ** = desviación típica.")

            cards_iqr = ['<div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:8px;">']

            for d in pilot_order:

                grp = laps_clean[laps_clean['Driver'] == d]['Seconds'].dropna()

                if grp.empty:
                    continue

                med = float(grp.median())
                std = float(grp.std(ddof=1)) if len(grp) >= 2 else 0.0
                iqr_v = float(grp.quantile(0.75) - grp.quantile(0.25)) if len(grp) >= 2 else 0.0
                best = float(grp.min())
                gap = (med - leader_median) if leader_median is not None else 0.0
                gap_txt = "Líder" if abs(gap) < 1e-6 else f"+{gap:.3f}s"

                sub_stats = {
                    'Gap vs líder': gap_txt,
                    'Mejor vuelta': format_time(best),
                    'Dispersión (IQR)': f'{iqr_v:.3f} s',
                    'Desv. típica (σ)': f'{std:.3f} s',
                    'Vueltas usadas': str(int(grp.count())),
                }

                card = render_summary_card(get_driver_name(d), get_neon_color(d), "Ritmo mediano", format_time(med), sub_stats)
                cards_iqr.append(card)

            cards_iqr.append('</div>')
            st.markdown(''.join(str(c) for c in cards_iqr), unsafe_allow_html=True)

            # --- CONSISTENCIA (Coeficiente de Variación) ---

            st.divider()

            st.markdown("**CONSISTENCIA (Coeficiente de Variación)**")

            st.caption(
                "El **CV** normaliza la variación de las vueltas por su ritmo: **CV = σ / mediana × 100**. "
                "Así puedes comparar la regularidad de pilotos con ritmos distintos en igualdad de condiciones "
                "(un σ de 0.3s pesa más en una vuelta corta que en una larga). Menor CV = más regular."
            )

            cv_rows = []

            for d in pilot_order:

                grp = laps_clean[laps_clean['Driver'] == d]['Seconds'].dropna()

                if len(grp) < 3:

                    continue

                med = float(grp.median())

                std = float(grp.std(ddof=1))

                cv = (std / med * 100) if med > 0 else None

                iqr_v = float(grp.quantile(0.75) - grp.quantile(0.25))

                cv_rows.append({'driver': d, 'name': get_driver_name(d), 'cv': cv, 'iqr': iqr_v, 'median': med, 'n': int(grp.count())})

            if cv_rows:

                cv_rows.sort(key=lambda x: x['cv'] if x['cv'] is not None else 999)

                valid_cv = [r['cv'] for r in cv_rows if r['cv'] is not None]
                max_cv = max(valid_cv) if valid_cv else 1.0

                def _cv_bucket(cv_v):
                    if cv_v is None:
                        return '#555', 'N/D'
                    if cv_v < 0.5:
                        return '#27AE60', '● Excelente'
                    if cv_v < 1.0:
                        return '#F39C12', '● Estable'
                    return '#E74C3C', '● Variable'

                cv_html = '<div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:8px;">'

                for row in cv_rows:

                    cv_v = row['cv']
                    bar_color, status = _cv_bucket(cv_v)
                    driver_color = get_neon_color(row['driver'])
                    bar_pct = (cv_v / max_cv * 100.0) if (cv_v is not None and max_cv > 0) else 0.0

                    cv_html += (
                        f'<div style="flex:1 1 180px;min-width:160px;background:rgba(255,255,255,0.02);'
                        f'border-radius:8px;border-left:6px solid {driver_color};padding:10px;">'
                        f'<div style="font-weight:700;color:{driver_color};font-size:13px;">{html.escape(row["name"])}</div>'
                        f'<div style="font-size:22px;font-weight:700;color:#fff;margin-top:4px;">'
                        f'{cv_v:.3f}%</div>'
                        f'<div style="font-size:11px;color:{bar_color};margin-top:2px;">{status}</div>'
                        f'<div style="height:6px;background:rgba(255,255,255,0.08);border-radius:3px;margin-top:6px;">'
                        f'<div style="height:6px;width:{bar_pct:.0f}%;background:{bar_color};border-radius:3px;"></div></div>'
                        f'<div style="font-size:11px;color:#999;margin-top:5px;">'
                        f'σ: {row["cv"]/100.0*row["median"]:.3f}s · IQR: {row["iqr"]:.3f}s · {row["n"]} vueltas</div>'
                        f'</div>'
                    )

                cv_html += '</div>'

                st.markdown(cv_html, unsafe_allow_html=True)

                # Resumen calculado: más y menos regular
                cv_summary = None
                if len(cv_rows) >= 1:
                    best_cv = cv_rows[0]
                    worst_cv = cv_rows[-1]
                    if len(cv_rows) >= 2 and best_cv['cv'] is not None and worst_cv['cv'] is not None:
                        cv_summary = (
                            f"{best_cv['name']} fue el más regular (CV {best_cv['cv']:.3f}%), y {worst_cv['name']} el que más varió "
                            f"(CV {worst_cv['cv']:.3f}%). Ojo: ritmo y consistencia son distintos — el más rápido no siempre es el más regular."
                        )
                    elif best_cv['cv'] is not None:
                        cv_summary = f"{best_cv['name']} fue el más regular con un CV de {best_cv['cv']:.3f}%."
                render_chart_guide(
                    summary_text=cv_summary,
                    how_to_read=(
                        "- **¿Un piloto tiene el CV más BAJO?** → sus vueltas se parecen mucho entre sí (muy regular). **¿CV alto?** → ritmo irregular (errores, tráfico, gestión de goma).\n"
                        "- **Barra corta = más consistente** (cada barra se compara con el peor de la selección).\n"
                        "- Regla rápida en carrera: **< 0.5%** excelente · **0.5–1%** estable · **> 1%** variable.\n"
                        "- Es normal que el CV suba a lo largo de la carrera (combustible + desgaste). Se calcula solo con vueltas limpias, así que no lo ensucian los pits ni el Safety Car."
                    )
                )

    st.divider()

    # --- EVOLUCIÓN DE TIEMPOS POR VUELTA (RITMO DE CARRERA) — debajo de Distribución de ritmo ---

    st.markdown("**EVOLUCIÓN DE TIEMPOS POR VUELTA (RITMO DE CARRERA)**")
    st.caption("Justo debajo de la Distribución de ritmo: primero ves el ritmo puro y la consistencia (boxplot + tarjetas), y aquí la 'película' cronológica que lo explica — pits, errores, tráfico y degradación del neumático.")

    if not laps_vip.empty and laps_vip['Seconds'].notna().any():

        fig_gpt_pan = build_gp_tempo_chart(
            laps_vip, selected_abbr,
            show_outliers=st.session_state.get('pan_gpt_outliers', True)
        )
        st.plotly_chart(fig_gpt_pan, use_container_width=True)
        st.toggle("Mostrar vueltas atípicas (pits, SC, tráfico)", value=True, key="pan_gpt_outliers")

        gpt_parts_pan = []
        for d in selected_abbr:
            dfd = laps_vip[laps_vip['Driver'] == d]
            secs_d = dfd['Seconds'].dropna()
            if secs_d.empty:
                continue
            best_idx = secs_d.idxmin()
            best_lap_n = int(dfd.loc[best_idx, 'LapNumber'])
            clean_d = dfd[~_mark_outlier_laps(dfd)]['Seconds'].dropna()
            med_txt = format_time(float(clean_d.median())) if not clean_d.empty else "N/D"
            gpt_parts_pan.append(
                f"{d}: mejor vuelta {format_time(float(secs_d.min()))} (V{best_lap_n}), mediana limpia {med_txt}."
            )
        render_chart_guide(
            summary_text=" ".join(gpt_parts_pan) if gpt_parts_pan else None,
            how_to_read=(
                "- **¿La línea de un piloto va más ABAJO?** → hizo esa vuelta más rápido (eje Y: abajo = mejor tiempo).\n"
                "- El **color del punto** es el compuesto (rojo=blando, amarillo=medio, blanco=duro): así comparas ritmos con la misma goma.\n"
                "- **¿Un pico hacia arriba?** → vuelta lenta: parada en pits, Safety Car o tráfico. Apaga 'Mostrar vueltas atípicas' para quitarlos.\n"
                "- **¿La línea sube poco a poco dentro de un stint?** → el neumático se está degradando.\n"
                "- Los **cruces** entre líneas te dicen quién apretó o aflojó el ritmo en ese punto de la carrera."
            )
        )
    else:
        st.info("No hay tiempos de vuelta suficientes para mostrar la evolución.")

    # ── CLASIFICACIÓN Q1/Q2/Q3 (solo en sesiones de qualifying) ──
    if session in ('Qualifying', 'Sprint Qualifying', 'Sprint Shootout'):
        st.divider()
        st.markdown("**CLASIFICACIÓN · Q1 / Q2 / Q3, gap a la pole y eliminados**")
        st.caption("Los tres cortes de la qualy: en qué segmento cayó cada piloto, sus tiempos y a cuánto quedó de la pole.")
        try:
            _qres = race.results.dropna(subset=['Position']).sort_values('Position')

            def _qsec(v):
                return v.total_seconds() if (v is not None and pd.notna(v) and hasattr(v, 'total_seconds')) else None

            _pole = None
            for _, r in _qres.iterrows():
                _b = next((q for q in [_qsec(r.get('Q3')), _qsec(r.get('Q2')), _qsec(r.get('Q1'))] if q is not None), None)
                if _b is not None:
                    _pole = _b
                    break
            _rows_q = ""
            for _, r in _qres.iterrows():
                code = r['Abbreviation']; pos = int(r['Position'])
                q1, q2, q3 = _qsec(r.get('Q1')), _qsec(r.get('Q2')), _qsec(r.get('Q3'))
                _best = next((q for q in [q3, q2, q1] if q is not None), None)
                _gap = (_best - _pole) if (_best is not None and _pole is not None) else None
                col = get_driver_color(code, race.laps)
                if q3 is not None:
                    seg, segc = "Q3", "#B026FF"
                elif q2 is not None:
                    seg, segc = "Elim. Q2", "#F2C94C"
                else:
                    seg, segc = "Elim. Q1", "#FF6B6B"
                gap_txt = "POLE" if pos == 1 else (f"+{_gap:.3f}" if _gap is not None else "—")
                _rows_q += (
                    f"<tr>"
                    f"<td style='padding:6px 10px;color:#888;'>{pos}</td>"
                    f"<td style='padding:6px 10px;font-weight:700;color:{col};'>{code}</td>"
                    f"<td style='padding:6px 10px;text-align:right;font-variant-numeric:tabular-nums;color:#bbb;'>{format_time(q1) if q1 is not None else '—'}</td>"
                    f"<td style='padding:6px 10px;text-align:right;font-variant-numeric:tabular-nums;color:#bbb;'>{format_time(q2) if q2 is not None else '—'}</td>"
                    f"<td style='padding:6px 10px;text-align:right;font-variant-numeric:tabular-nums;color:#fff;font-weight:600;'>{format_time(q3) if q3 is not None else '—'}</td>"
                    f"<td style='padding:6px 10px;text-align:right;color:#bbb;font-variant-numeric:tabular-nums;'>{gap_txt}</td>"
                    f"<td style='padding:6px 10px;color:{segc};font-weight:600;'>{seg}</td>"
                    f"</tr>"
                )
            st.markdown(
                "<table style='width:100%;border-collapse:collapse;'>"
                "<thead><tr style='color:#888;font-size:12px;text-align:left;'>"
                "<th style='padding:6px 10px;'>Pos</th><th style='padding:6px 10px;'>Piloto</th>"
                "<th style='padding:6px 10px;text-align:right;'>Q1</th><th style='padding:6px 10px;text-align:right;'>Q2</th>"
                "<th style='padding:6px 10px;text-align:right;'>Q3</th><th style='padding:6px 10px;text-align:right;'>Gap pole</th>"
                "<th style='padding:6px 10px;'>Corte</th></tr></thead>"
                f"<tbody>{_rows_q}</tbody></table>",
                unsafe_allow_html=True
            )
            render_chart_guide(
                summary_text=None,
                how_to_read=(
                    "- **¿Fila morada?** → llegó a Q3 (top 10). **¿Amarilla?** → cayó en Q2. **¿Roja?** → cayó en Q1.\n"
                    "- Los cortes: **Q1** elimina del 16º al 20º · **Q2** del 11º al 15º · **Q3** decide el top 10 y la pole.\n"
                    "- El **Gap pole** te dice a cuánto quedó cada uno del más rápido (P1 = POLE).\n"
                    "- **¿Lento en Q1/Q2 pero rápido en Q3?** → guardó gomas o dio el golpe al final, cuando de verdad contaba."
                )
            )
        except Exception as _e:
            st.info(f"No se pudo construir la clasificación: {_e}")

    # ── MEJORES SECTORES DEL CAMPO + vuelta ideal de la sesión ──
    st.divider()
    st.markdown("**MEJORES SECTORES DEL CAMPO · vuelta ideal de la sesión**")
    st.caption("El mejor tiempo de cada sector de cada piloto; en morado el más rápido de todo el campo. Abajo, la vuelta teórica ideal juntando los tres mejores sectores de la sesión.")
    try:
        _ls = race.laps
        _have = [(lbl, c) for lbl, c in [('S1', 'Sector1Time'), ('S2', 'Sector2Time'), ('S3', 'Sector3Time')] if c in _ls.columns]
        if not _have:
            st.info("No hay tiempos de sector para esta sesión.")
        else:
            _best_per, _overall = {}, {}
            for lbl, c in _have:
                bs = _ls.dropna(subset=[c]).groupby('Driver')[c].min()
                for drv, val in bs.items():
                    _best_per.setdefault(drv, {})[lbl] = val.total_seconds()
                if not bs.empty:
                    _overall[lbl] = (bs.min().total_seconds(), bs.idxmin())
            _drv_bs = [d for d in selected_abbr if d in _best_per] or list(_best_per.keys())

            def _theo(d):
                s = _best_per[d]
                vals = [s.get(lbl) for lbl, _ in _have]
                return sum(vals) if all(v is not None for v in vals) else 9e9

            _drv_bs = sorted(_drv_bs, key=_theo)
            _rows_bs = ""
            for d in _drv_bs:
                s = _best_per[d]; col = get_neon_color(d); cells = ""
                for lbl, _ in _have:
                    v = s.get(lbl)
                    _purple = (_overall.get(lbl, (None, None))[1] == d)
                    cells += (f"<td style='padding:6px 10px;text-align:right;font-variant-numeric:tabular-nums;"
                              f"color:{'#B026FF' if _purple else '#ddd'};font-weight:{'700' if _purple else '400'};'>"
                              f"{format_time(v) if v is not None else '—'}</td>")
                _t = _theo(d)
                cells += f"<td style='padding:6px 10px;text-align:right;color:#fff;font-weight:600;'>{format_time(_t) if _t < 9e8 else '—'}</td>"
                _rows_bs += f"<tr><td style='padding:6px 10px;font-weight:700;color:{col};'>{d}</td>{cells}</tr>"
            _heads = "".join(f"<th style='padding:6px 10px;text-align:right;'>{lbl}</th>" for lbl, _ in _have)
            st.markdown(
                "<table style='width:100%;border-collapse:collapse;'>"
                f"<thead><tr style='color:#888;font-size:12px;'><th style='padding:6px 10px;text-align:left;'>Piloto</th>{_heads}"
                "<th style='padding:6px 10px;text-align:right;'>Vuelta ideal</th></tr></thead>"
                f"<tbody>{_rows_bs}</tbody></table>",
                unsafe_allow_html=True
            )
            if all(lbl in _overall for lbl, _ in _have):
                _field_ideal = sum(_overall[lbl][0] for lbl, _ in _have)
                _parts = " · ".join(f"{lbl}: {_overall[lbl][1]} {format_time(_overall[lbl][0])}" for lbl, _ in _have)
                st.markdown(
                    f"<div style='margin-top:8px;font-size:13px;color:#ddd;'><b>Vuelta ideal de la sesión: "
                    f"{format_time(_field_ideal)}</b> &nbsp; ({_parts})</div>",
                    unsafe_allow_html=True
                )
            render_chart_guide(
                summary_text=None,
                how_to_read=(
                    "- **¿Una celda en MORADO?** → ese piloto fue el más rápido de TODO el campo en ese sector (el sector 'púrpura').\n"
                    "- La **Vuelta ideal** de cada piloto junta sus 3 mejores sectores, aunque los hiciera en vueltas distintas (su tope personal).\n"
                    "- La **vuelta ideal de la sesión** (abajo) combina los mejores sectores de cualquiera: el récord teórico absoluto del día.\n"
                    "- **¿Su vuelta ideal es mucho mejor que su vuelta real?** → dejó tiempo en la mesa; no encadenó sus mejores sectores en una sola vuelta.\n"
                    "- La tabla va ordenada por vuelta ideal, de la mejor a la peor."
                )
            )
    except Exception as _e:
        st.info(f"No se pudo construir el tablero de sectores: {_e}")

# --- TAB 2: TELEMETRÍA ---
