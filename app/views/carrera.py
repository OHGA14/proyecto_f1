"""CARRERA: ritmo, estrategia, lap chart, gaps."""
import html
from app.components import plot_wide
from app.components import render_chart_guide
from app.components import render_clean_metric_table
from app.components import render_gp_tempo_table
from f1core.charts import make_god_chart
from f1core.colors import _get_team_for_driver
from f1core.colors import get_driver_info
from f1core.colors import get_driver_name
from f1core.colors import get_neon_color
from f1core.config import DIST_CHART_CONFIG
from f1core.config import _TEAM_COLORS_NORM
from f1core.racecontrol import _parse_race_control_messages
from f1core.racecontrol import _parse_track_status
from f1core.racecontrol import _sc_vsc_lap_ranges
from f1core.racecontrol import _segments_to_laps
from f1core.racecontrol import get_pits_dataframe
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
    style_map = ctx.get("style_map")
    # @UNPACK@  (generado por fix_names)

    # ── TIEMPOS POR VUELTA (TABLA) ─────────────────────────────────────────
    # La gráfica de evolución del ritmo vive ahora SOLO en PANORAMA (no duplicar).

    st.markdown("#### TIEMPOS POR VUELTA (TABLA)")
    st.caption("La gráfica de evolución del ritmo está ahora en la pestaña **PANORAMA**. Aquí queda la tabla vuelta a vuelta con los compuestos.")

    if not laps_vip.empty and laps_vip['LapNumber'].notna().any():
        min_lap_gpt = int(laps_vip['LapNumber'].min())
        max_lap_gpt = int(laps_vip['LapNumber'].max())
        if max_lap_gpt > min_lap_gpt:
            rng_gpt = st.slider(
                "Vueltas visibles en la tabla:",
                min_lap_gpt, max_lap_gpt,
                (min_lap_gpt, min(min_lap_gpt + 7, max_lap_gpt)),
                key="gpt_table_range"
            )
        else:
            rng_gpt = (min_lap_gpt, max_lap_gpt)
        render_gp_tempo_table(laps_vip, selected_abbr, rng_gpt[0], rng_gpt[1])

    st.divider()

    # ── PACE EVOLUTION ─────────────────────────────────────────────────────

    if 'pace_context_layers' not in st.session_state:
        st.session_state['pace_context_layers'] = ["SC", "VSC", "Red"]
    if 'pace_pits_view' not in st.session_state:
        st.session_state['pace_pits_view'] = "Tabla"
    if 'pace_pits_show' not in st.session_state:
        st.session_state['pace_pits_show'] = True

    st.markdown("#### Capas de contexto")
    # El default vive en session_state (pre-sembrado arriba); pasar también
    # default= aquí genera el warning de Streamlit por doble asignación.
    pace_layers = st.multiselect(
        "Capas de contexto",
        options=["Yellow", "VSC", "SC", "Red"],
        key="pace_context_layers"
    )

    fig_p = go.Figure()

    ritmo_metrics = {}

    for d in selected_abbr:

        df = laps_vip[laps_vip['Driver'] == d]

        c = get_neon_color(d); name = get_driver_name(d)

        hover = [f"<b>{name}</b><br>Vuelta: {l}<br>Tiempo: {t}" for l, t in zip(df['LapNumber'], df['TimeReadable'])]

        fig_p.add_trace(go.Scatter(x=df['LapNumber'], y=df['Smooth'], mode='lines+markers', name=d, line=dict(color=c, width=2.5, dash=style_map.get(d,'solid')), marker=dict(size=5, color=c, opacity=0.7), hoverinfo="text", hovertext=hover))

        # collect metrics

        if not df['Smooth'].dropna().empty:

            ritmo_metrics[get_driver_name(d)] = {'Avg Pace (s)': float(df['Smooth'].mean()), 'Std (s)': float(df['Smooth'].std())}



        pits = df[df['IsPit']==True]

        if not pits.empty:

             hover_pit = [f"<b>PIT STOP ({name})</b><br>Vuelta {l}<br>Entrada" for l in pits['LapNumber']]

             fig_p.add_trace(go.Scatter(x=pits['LapNumber'], y=pits['Smooth'], mode='markers', name=f"{d} PIT", marker=dict(symbol='diamond', size=14, color='#ffffff', line=dict(width=2, color=c)), hoverinfo="text", hovertext=hover_pit, showlegend=False))

    fig_p.update_yaxes(autorange="reversed")

    show_pits = st.session_state.get('pace_pits_show', True)
    pit_drivers = list(selected_abbr)
    pit_df_out = pd.DataFrame()
    if show_pits:
        # Los pits ya se marcan con rombos blancos en el bucle anterior;
        # aquí solo se calcula el DataFrame para la tabla/gráfica de pits.
        pit_df_out = get_pits_dataframe(race, laps, pit_drivers)

    layer_map = {"Yellow": "YELLOW", "VSC": "VSC", "SC": "SC", "Red": "RED"}
    selected_types = {layer_map[l] for l in pace_layers if l in layer_map}
    if selected_types:
        rcm_segments = _parse_race_control_messages(race)
        ts_segments = _parse_track_status(race)
        segments = []
        if rcm_segments:
            segments.extend(rcm_segments)
        else:
            segments.extend([s for s in ts_segments if s["type"] in {"SC", "VSC", "RED"}])
        if "YELLOW" in selected_types:
            segments.extend([s for s in ts_segments if s["type"] == "YELLOW"])
        segments = [s for s in segments if s["type"] in selected_types]

        mapped, unmapped = _segments_to_laps(segments, laps)
        if not mapped and not unmapped:
            st.caption("No hay datos de banderas para este evento.")
        if unmapped:
            st.warning("Evento sin mapeo a vuelta; se omitieron algunos eventos.")

        status_colors = {
            "SC": "#FFD000",
            "VSC": "#FFB000",
            "YELLOW": "#FFE066",
            "RED": "#FF3B30"
        }
        y_anchor = float(laps_vip['Smooth'].min()) if not laps_vip['Smooth'].dropna().empty else 0.0
        annotation_count = 0
        for seg in mapped:
            color = status_colors.get(seg["type"], "#888888")
            lap_start = seg["lap_start"]
            lap_end = seg["lap_end"]
            if lap_start == lap_end:
                fig_p.add_vline(x=lap_start, line_color=color, opacity=0.25, line_width=2)
            else:
                fig_p.add_vrect(x0=lap_start, x1=lap_end, fillcolor=color, opacity=0.15, line_width=0)
            mid = (lap_start + lap_end) / 2.0
            fig_p.add_trace(go.Scatter(
                x=[mid],
                y=[y_anchor],
                mode='markers',
                marker=dict(size=6, color=color, opacity=0.85),
                hovertemplate=f"{seg['type']}<br>Vueltas: {lap_start}-{lap_end}<extra></extra>",
                showlegend=False
            ))
            if annotation_count < 8:
                fig_p.add_annotation(
                    x=lap_start,
                    y=1.02,
                    xref="x",
                    yref="paper",
                    text=seg["type"],
                    showarrow=False,
                    font=dict(size=10, color=color)
                )
                annotation_count += 1

    st.plotly_chart(make_god_chart(fig_p, "RITMO DE CARRERA", "Tiempo (s)", "Vueltas", 600), use_container_width=True)

    render_chart_guide(
        summary_text=" ".join(
            f"{name}: ritmo promedio {v['Avg Pace (s)']:.3f}s (±{v['Std (s)']:.3f}s)."
            for name, v in ritmo_metrics.items()
        ) if ritmo_metrics else None,
        how_to_read=(
            "- Ritmo **suavizado** de cada piloto durante la carrera. Eje Y **invertido**: **más arriba = más rápido**.\n"
            "- Los **rombos blancos** marcan la vuelta en que entró a boxes.\n"
            "- Las **franjas de color** son Safety Car (amarillo), VSC (naranja) o bandera roja: ahí los ritmos se igualan.\n"
            "- **¿Dos líneas que se van separando poco a poco?** → uno degrada más o tiene más ritmo puro.\n"
            "- **¿Una línea sube (mejora) justo tras una parada?** → gomas nuevas rindiendo."
        )
    )

    st.markdown("#### Pits")
    pits_view = st.radio("Pits: vista", ["Tabla", "Gráfica"], horizontal=True, key="pace_pits_view")
    show_pits_toggle = st.toggle("Mostrar pits", key="pace_pits_show")
    show_pits = show_pits_toggle

    if not show_pits:
        st.caption("Pits ocultos.")
    else:
        if pit_df_out.empty:
            pit_cols_ok = 'PitInTime' in laps.columns and 'PitOutTime' in laps.columns
            pit_has_data = pit_cols_ok and (laps['PitInTime'].notna().any() or laps['PitOutTime'].notna().any())
            if pit_has_data:
                st.caption("Sin paradas de los pilotos seleccionados.")
            else:
                st.warning("No hay datos de pits disponibles en esta sesión.")
        elif pits_view == "Tabla":
            pit_df_out = pit_df_out.sort_values(['DriverCode', 'LapNumber'])
            df_view = pit_df_out.copy()
            df_view['Piloto'] = df_view['DriverCode'].apply(get_driver_name)
            df_view['Pit lane (s)'] = df_view['PitDuration_s'].round(2)
            view_cols = ['Piloto', 'LapNumber', 'Pit lane (s)']
            rename = {'LapNumber': 'Vuelta'}
            if 'CompoundAfter' in df_view.columns:
                df_view['Goma nueva'] = df_view['CompoundAfter']
                view_cols.append('Goma nueva')
            st.dataframe(df_view[view_cols].rename(columns=rename).set_index('Piloto'), use_container_width=True)
        else:
            fig_pits = go.Figure()
            for d in pit_drivers:
                d_pits = pit_df_out[pit_df_out['DriverCode'] == d]
                if d_pits.empty:
                    continue
                fig_pits.add_trace(go.Bar(
                    x=d_pits['LapNumber'],
                    y=d_pits['PitDuration_s'],
                    name=d,
                    marker_color=get_neon_color(d),
                    text=[f"{v:.1f}s" for v in d_pits['PitDuration_s']],
                    textposition="outside",
                    hovertemplate=f"{get_driver_name(d)}<br>Vuelta %{{x}}<br>Pit lane: %{{y:.2f}}s<extra></extra>"
                ))
            fig_pits.update_layout(
                template="habib_dark",
                height=340,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=40, r=20, t=40, b=40),
                xaxis=dict(title="Vuelta de entrada a pits", dtick=1),
                yaxis=dict(title="Tiempo en pit lane (s)"),
                legend=dict(orientation="h", y=1.08, x=0)
            )
            st.plotly_chart(fig_pits, use_container_width=True)

        if not pit_df_out.empty:
            pit_parts = []
            for d in pit_drivers:
                d_pits = pit_df_out[pit_df_out['DriverCode'] == d]
                if d_pits.empty:
                    continue
                pit_parts.append(
                    f"{d}: {len(d_pits)} parada(s) en vuelta(s) {', '.join(map(str, d_pits['LapNumber'].tolist()))}, "
                    f"mejor pit lane {d_pits['PitDuration_s'].min():.2f}s."
                )
            render_chart_guide(
                summary_text=" ".join(pit_parts) if pit_parts else None,
                how_to_read=(
                    "- El número es el **tiempo total en el pit lane** (de entrada a salida), no solo los segundos con el coche detenido.\n"
                    "- Incluye recorrer el pit lane a velocidad limitada (~20 s en casi todos los circuitos) + la parada en sí.\n"
                    "- **¿Diferencias de 1-3 s entre paradas?** → cosa del equipo (cambio de gomas). **¿Mayores?** → un problema o una reparación.\n"
                    "- 'Goma nueva' es el compuesto con el que salió tras esa parada."
                )
            )

    # Metrics table: Average pace and consistency

    if ritmo_metrics:

        tbl = [(k, f"Avg: {v['Avg Pace (s)']:.3f}s · Std: {v['Std (s)']:.3f}s") for k, v in ritmo_metrics.items()]

        st.markdown(render_clean_metric_table(
            tbl, col1="Piloto", col2="Ritmo medio / variación",
            title="Ritmo de carrera",
            caption="Avg = tiempo de vuelta medio (suavizado) · Std = variación entre vueltas (menor = más consistente)."
        ), unsafe_allow_html=True)



    ref_gap = st.selectbox("Referencia Gaps:", selected_abbr, format_func=get_driver_name, key="ref_gap_carrera")

    try:

        base = laps.pick_driver(ref_gap)[['LapNumber', 'Time']].rename(columns={'Time':'RefTime'})

        merged = laps_vip.merge(base, on='LapNumber', how='left')

        merged['Gap'] = (merged['Time'] - merged['RefTime']).dt.total_seconds()

        fig_gap = go.Figure()

        gap_metrics = {}

        for d in selected_abbr:

            df = merged[merged['Driver'] == d]

            c = get_neon_color(d); name = get_driver_name(d)

            hover = [f"<b>{name}</b><br>Gap: {g:+.2f}s" for g in df['Gap']]

            fig_gap.add_trace(go.Scatter(x=df['LapNumber'], y=df['Gap'], mode='lines+markers', name=d, line=dict(color=c, width=2.5), marker=dict(size=5, color=c, opacity=0.7), hoverinfo="text", hovertext=hover))

            if not df['Gap'].dropna().empty:

                gap_metrics[get_driver_name(d)] = {'Mean Gap (s)': float(df['Gap'].mean()), 'Std Gap (s)': float(df['Gap'].std())}

        fig_gap.update_yaxes(autorange="reversed")

        st.plotly_chart(make_god_chart(fig_gap, f"DISTANCIA RELATIVA vs {get_driver_name(ref_gap)}", "Segundos", "Vueltas", 500), use_container_width=True)

        render_chart_guide(
            summary_text=" ".join(
                f"{name}: gap promedio {v['Mean Gap (s)']:+.2f}s vs {get_driver_name(ref_gap)}."
                for name, v in gap_metrics.items() if name != get_driver_name(ref_gap)
            ) if gap_metrics else None,
            how_to_read=(
                f"- A cuánto tiempo va cada piloto de **{get_driver_name(ref_gap)}** en cada vuelta.\n"
                "- **Gap positivo** = va por DETRÁS de la referencia · **negativo** = va por DELANTE.\n"
                "- **¿Una línea que se ALEJA de 0?** → pierde tiempo sostenidamente. **¿Que CONVERGE hacia 0?** → está recortando, viene de caza.\n"
                "- Los **saltos bruscos** suelen ser paradas en pits o Safety Car, no ritmo real."
            )
        )

        if gap_metrics:

            tbl_gap = [(k, f"Mean: {v['Mean Gap (s)']:.3f}s · Std: {v['Std Gap (s)']:.3f}s") for k, v in gap_metrics.items()]

            st.markdown(render_clean_metric_table(
                tbl_gap, col1="Piloto", col2=f"Gap medio vs {ref_gap}",
                title="Distancia relativa",
                caption=f"Mean = gap medio respecto a {get_driver_name(ref_gap)} (+ por detrás, − por delante) · Std = cuánto oscila ese gap."
            ), unsafe_allow_html=True)

    except: pass

    # ── STINT ANALYSIS ─────────────────────────────────────────────────────
    st.divider()
    st.markdown("#### ANÁLISIS DE STINT Y DEGRADACIÓN")
    st.caption("Ritmo medio y pendiente de degradación por stint. Un slope positivo indica pérdida de tiempo por vuelta (degradación).")

    try:
        stint_rows = []
        for d in selected_abbr:
            df_d = laps_vip[laps_vip['Driver'] == d].copy()
            if df_d.empty:
                continue
            df_d = df_d.sort_values('LapNumber').reset_index(drop=True)
            # Usar el número de stint oficial de FastF1 si existe; si no, derivarlo de los pits
            if 'Stint' in df_d.columns and df_d['Stint'].notna().any():
                df_d['Stint'] = df_d['Stint'].ffill().bfill().astype(int)
            else:
                pit_flags = df_d['IsPit'].fillna(False).astype(bool)
                stint_id = pit_flags.shift(1, fill_value=False).cumsum()
                df_d['Stint'] = (stint_id + 1).astype(int)

            for stint_num, grp in df_d.groupby('Stint'):
                # Excluir SC/VSC, in-laps y out-laps del cálculo de ritmo
                grp_clean = grp
                if 'IsScVsc' in grp.columns:
                    grp_clean = grp_clean[~grp_clean['IsScVsc']]
                if 'IsPit' in grp.columns:
                    grp_clean = grp_clean[~grp_clean['IsPit'].fillna(False).astype(bool)]
                if 'IsOutLap' in grp.columns:
                    grp_clean = grp_clean[~grp_clean['IsOutLap'].fillna(False).astype(bool)]
                clean = grp_clean['Seconds'].dropna()
                # Filter outliers (>107% of stint median)
                if clean.empty:
                    continue
                med = clean.median()
                clean = clean[clean <= med * 1.07]
                if len(clean) < 2:
                    continue
                laps_arr = grp.loc[clean.index, 'LapNumber'].values
                pace_med = float(clean.median())
                # Pendiente de degradación (s/vuelta) contra el número REAL de
                # vuelta: usar un índice 0..n sesgaría el valor si se
                # descartaron vueltas intermedias del stint.
                slope = float(np.polyfit(laps_arr.astype(float), clean.values, 1)[0])
                stint_rows.append({
                    'Driver': d,
                    'Name': get_driver_name(d),
                    'Color': get_neon_color(d),
                    'Stint': stint_num,
                    'Laps': len(clean),
                    'FirstLap': int(laps_arr.min()),
                    'LastLap': int(laps_arr.max()),
                    'MedianPace_s': pace_med,
                    'Slope_s_per_lap': slope,
                })

        if stint_rows:
            df_stint = pd.DataFrame(stint_rows)

            # Chart: median pace per stint per driver
            fig_stint = go.Figure()
            for d in selected_abbr:
                ds = df_stint[df_stint['Driver'] == d]
                if ds.empty:
                    continue
                c = get_neon_color(d)
                name = get_driver_name(d)
                hover_s = [
                    f"<b>{name} – Stint {row.Stint}</b><br>"
                    f"Vueltas: {row.FirstLap}–{row.LastLap} ({row.Laps} vueltas)<br>"
                    f"Ritmo mediano: {row.MedianPace_s:.3f}s<br>"
                    f"Degradación: {row.Slope_s_per_lap:+.4f}s/vuelta"
                    for row in ds.itertuples()
                ]
                fig_stint.add_trace(go.Scatter(
                    x=ds['Stint'], y=ds['MedianPace_s'],
                    mode='lines+markers', name=d,
                    line=dict(color=c, width=2.5),
                    marker=dict(size=9, color=c, symbol='circle', line=dict(width=1.5, color='white')),
                    hoverinfo="text", hovertext=hover_s
                ))
            fig_stint.update_layout(
                template="habib_dark",
                xaxis=dict(title="Stint", tickmode='linear', dtick=1),
                yaxis=dict(title="Ritmo mediano (s)", autorange="reversed"),
                margin=dict(l=50, r=20, t=40, b=40),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(make_god_chart(fig_stint, "RITMO MEDIANO POR STINT", "Segundos", "Stint", 380), use_container_width=True)

            stint_summary = None
            if not df_stint.empty:
                best_deg_row = df_stint.loc[df_stint['Slope_s_per_lap'].idxmin()]
                worst_deg_row = df_stint.loc[df_stint['Slope_s_per_lap'].idxmax()]
                stint_summary = (
                    f"Mejor gestión: {best_deg_row['Name']} en el stint {int(best_deg_row['Stint'])} "
                    f"({best_deg_row['Slope_s_per_lap']:+.3f}s/vuelta). "
                    f"Mayor degradación: {worst_deg_row['Name']} en el stint {int(worst_deg_row['Stint'])} "
                    f"({worst_deg_row['Slope_s_per_lap']:+.3f}s/vuelta)."
                )
            render_chart_guide(
                summary_text=stint_summary,
                how_to_read=(
                    "- Cada punto es el **ritmo mediano** de un stint (tramo entre paradas). Eje Y invertido: **más arriba = más rápido**.\n"
                    "- **¿Comparas el mismo stint entre pilotos?** → ves quién tenía mejor ritmo con ese juego de gomas.\n"
                    "- En la tabla, la **degradación** es la pendiente: **+0.05 s/vuelta** = cada vuelta era 5 centésimas más lenta que la anterior.\n"
                    "- **¿Un stint más rápido que el anterior?** → goma nueva más blanda o coche más ligero (menos gasolina)."
                )
            )

            # Summary table
            disp = df_stint[['Name', 'Stint', 'Laps', 'FirstLap', 'LastLap', 'MedianPace_s', 'Slope_s_per_lap']].copy()
            disp['MedianPace_s'] = disp['MedianPace_s'].apply(lambda x: f"{x:.3f}s")
            disp['Slope_s_per_lap'] = disp['Slope_s_per_lap'].apply(lambda x: f"{x:+.4f}s/v")
            disp.columns = ['Piloto', 'Stint', 'Vueltas', 'Inicio', 'Fin', 'Ritmo Mediano', 'Degradación']
            st.dataframe(disp.set_index('Piloto'), use_container_width=True)
        else:
            st.info("No hay datos de stint suficientes para calcular degradación.")
    except Exception as _e_stint:
        st.caption(f"Stint analysis no disponible: {_e_stint}")

    # ── TIRE DEGRADATION (from old tab 4) ──────────────────────────────────

    st.divider()

    """

    PRINCIPIOS COLE NUSSBAUMER:

    1. DATOS LIMPIOS: Solo vueltas representativas (sin pits, sin Safety Car)

    2. REGRESIÓN LINEAL: Pendiente = Degradación Real (s/vuelta), Intercepto = Ritmo Base

    3. DISEÑO VISUAL: Ruido desaturado (opacidad 0.2), Tendencia sólida y brillante (width=3)

    4. TABLA INSIGHTS: Semáforo de datos (Verde/Amarillo/Rojo) para degradación

    """



    comp = laps_vip['Compound'].dropna().unique()

    if len(comp) > 0:

        sel = st.radio("Compuesto de Neumático:", comp, horizontal=True, key="compound_carrera")

        deg = laps_vip[laps_vip['Compound'] == sel].copy()



        # =========== INGENIERÍA DE DATOS ===========

        # Elimina in-laps, out-laps y vueltas bajo SC/VSC antes de la regresión:
        # son lentas por contexto, no por degradación de la goma.

        deg_clean = deg[~deg['IsPit']].copy()

        if 'IsOutLap' in deg_clean.columns:
            deg_clean = deg_clean[~deg_clean['IsOutLap'].fillna(False).astype(bool)]

        if 'IsScVsc' in deg_clean.columns:
            deg_clean = deg_clean[~deg_clean['IsScVsc'].fillna(False).astype(bool)]

        deg_clean = deg_clean.dropna(subset=['TyreLife', 'Seconds'])



        # Filtra vueltas atípicamente lentas (Safety Car): Q3 + 1.5*IQR
        # POR PILOTO: un umbral global mezclaría ritmos distintos y eliminaría
        # vueltas válidas del piloto más lento.

        if len(deg_clean) > 0:

            def _iqr_filter_driver(grp):
                q1 = grp['Seconds'].quantile(0.25)
                q3 = grp['Seconds'].quantile(0.75)
                return grp[grp['Seconds'] <= q3 + 1.5 * (q3 - q1)]

            deg_clean = deg_clean.groupby('Driver', group_keys=False).apply(_iqr_filter_driver).copy()



        if deg_clean.empty:

            st.warning("No hay datos suficientes para análisis de degradación (después de limpieza).")

        else:

            # =========== CÁLCULO MATEMÁTICO ===========

            fig_d_deg = go.Figure()

            insights = []



            for d in selected_abbr:

                df_pilot = deg_clean[deg_clean['Driver'] == d].copy()

                if len(df_pilot) < 3:

                    continue  # Necesita al menos 3 puntos



                c = get_neon_color(d)

                name = get_driver_name(d)



                # Scatter de ruido desaturado (Principio Cole: contexto visual)

                hover_scatter = [f"<b>{name}</b><br>Vuelta: {ln}<br>Goma: {v:.0f}<br>Tiempo: {t:.3f}s"

                                for ln, v, t in zip(df_pilot['LapNumber'], df_pilot['TyreLife'], df_pilot['Seconds'])]

                fig_d_deg.add_trace(go.Scatter(

                    x=df_pilot['TyreLife'], y=df_pilot['Seconds'], mode='markers',

                    name=name, marker=dict(color=c, size=5, opacity=0.2, line=dict(width=0)),

                    hoverinfo='text', hovertext=hover_scatter, showlegend=False

                ))



                # REGRESIÓN LINEAL: Calcula pendiente (degradación) e intercepto (ritmo base)

                try:

                    z = np.polyfit(df_pilot['TyreLife'], df_pilot['Seconds'], 1)

                    p = np.poly1d(z)

                    slope = z[0]  # Degradación (segundos por vida de goma)

                    intercept = z[1]  # Ritmo base teórico (V1 con goma nueva)



                    # Línea de tendencia sólida, gruesa, brillante (Principio Cole: atrae atención)

                    trend_x = np.linspace(df_pilot['TyreLife'].min(), df_pilot['TyreLife'].max(), 100)

                    trend_y = p(trend_x)

                    fig_d_deg.add_trace(go.Scatter(

                        x=trend_x, y=trend_y, mode='lines',

                        name=f"{d} (Deg: {slope:.4f} s/vuelta)",

                        line=dict(color=c, width=3, dash='solid'),

                        hoverinfo='skip', showlegend=True

                    ))



                    # Almacena datos para tabla insights

                    insights.append({

                        'driver': d,

                        'name': name,

                        'color': c,

                        'laps_analyzed': len(df_pilot),

                        'base_pace': intercept,

                        'degradation': slope,  # Segundos por vuelta de vida de goma

                        'max_tyre_life': df_pilot['TyreLife'].max()

                    })

                except Exception as e:

                    st.error(f"Error calculando regresión para {name}: {e}")



            fig_d_deg.update_layout(

                xaxis_title="Vida de Goma (Vueltas)",

                yaxis_title="Tiempo de Vuelta (s)",

                hovermode='closest'

            )

            # NO reversed: pendiente ascendente = degradación visible (más lento con goma usada)

            st.plotly_chart(make_god_chart(fig_d_deg, f"GESTIÓN DE NEUMÁTICOS: ANÁLISIS DE DEGRADACIÓN ({sel})",

                                          "Tiempo de Vuelta (s)", "Vida de Goma (Vueltas)", 550), use_container_width=True)

            deg_summary = None
            if insights:
                best_ins = min(insights, key=lambda x: x['degradation'])
                deg_summary = (
                    f"Con el compuesto {sel}, {best_ins['name']} tuvo la menor degradación "
                    f"({best_ins['degradation']:+.4f}s por vuelta de vida de goma, "
                    f"sobre {best_ins['laps_analyzed']} vueltas analizadas)."
                )
            render_chart_guide(
                summary_text=deg_summary,
                how_to_read=(
                    "- **Eje X**: vueltas de vida de la goma · **Eje Y**: tiempo de vuelta. Cada línea es un piloto con un compuesto.\n"
                    "- **¿La línea sube (muy inclinada)?** → la goma pierde rendimiento rápido: mucha degradación.\n"
                    "- **¿Línea casi PLANA?** → gestiona muy bien el neumático (o la pista mejoraba y lo compensa).\n"
                    "- Los **puntos tenues** son las vueltas reales; la **línea sólida** es la tendencia. Compara la misma goma entre pilotos: quién la cuida y quién la 'quema'."
                )
            )



            # =========== TABLA DE INSIGHTS CON SEMÁFORO ===========

            if insights:

                st.markdown("### TABLA DE INSIGHTS: Gestión de Neumáticos")

                st.caption(
                    "La **Evaluación** clasifica la pendiente de degradación (cuánto se ralentiza el piloto por cada vuelta "
                    "de vida de la goma). La columna **Por qué** traduce ese número a segundos perdidos reales."
                )

                # Ordena por degradación (menor = mejor gestión)
                insights.sort(key=lambda x: x['degradation'])

                def _evaluar_degradacion(deg, laps_n):
                    """Devuelve (etiqueta, color, icono, por_que) explicando la evaluación."""
                    loss10 = deg * 10.0          # segundos perdidos en 10 vueltas
                    loss_stint = deg * max(laps_n, 1)  # perdidos en el tramo analizado
                    if deg < -0.005:
                        return (
                            "Ritmo en mejora", "#4AA3FF", "▲",
                            f"El piloto fue <b>más rápido</b> con la goma más usada ({abs(deg):.3f}s/vuelta menos). "
                            "No es desgaste: manda la mejora de pista o el coche aligerándose de combustible."
                        )
                    if deg < 0.05:
                        return (
                            "Gestión excelente", "#27E36A", "●",
                            f"Solo pierde <b>{deg*1000:.0f} ms por vuelta</b> de vida de goma "
                            f"(≈ {loss10:.2f}s en 10 vueltas). Cuida muy bien el neumático."
                        )
                    if deg <= 0.10:
                        return (
                            "Degradación normal", "#F2C94C", "●",
                            f"Pierde <b>{deg*1000:.0f} ms por vuelta</b> (≈ {loss10:.2f}s en 10 vueltas). "
                            "Ritmo de caída típico de carrera; nada preocupante."
                        )
                    return (
                        "Degradación alta", "#FF4D4D", "●",
                        f"Pierde <b>{deg*1000:.0f} ms por vuelta</b> (≈ {loss10:.2f}s en 10 vueltas; "
                        f"~{loss_stint:.1f}s en las {laps_n} analizadas). La goma cae rápido: candidato a parar antes."
                    )

                table_html = '<table style="width:100%; border-collapse:collapse; background:rgba(255,255,255,0.02); border:1px solid #333;">'
                table_html += '<tr style="border-bottom:1px solid rgba(255,255,255,0.08);">'
                for h, al in [("Piloto", "left"), ("Vueltas", "center"), ("Ritmo base V1", "center"),
                              ("Degradación", "center"), ("Evaluación", "center"), ("Por qué", "left")]:
                    table_html += f'<th style="padding:10px 12px; color:#AAA; font-family:Roboto; text-align:{al}; font-size:13px;">{h}</th>'
                table_html += '</tr>'

                for row in insights:
                    status, color, icon, por_que = _evaluar_degradacion(row['degradation'], row['laps_analyzed'])
                    table_html += '<tr style="border-bottom:1px solid #2a2a2a;">'
                    table_html += f'<td style="padding:10px 12px; color:{row["color"]}; font-family:Roboto; font-weight:700;">{html.escape(row["name"])}</td>'
                    table_html += f'<td style="padding:10px 12px; color:#CCC; text-align:center;">{row["laps_analyzed"]}</td>'
                    table_html += f'<td style="padding:10px 12px; color:#CCC; text-align:center;">{format_time(row["base_pace"])}</td>'
                    table_html += f'<td style="padding:10px 12px; color:#CCC; text-align:center;">{row["degradation"]:+.3f} s/v</td>'
                    table_html += (
                        f'<td style="padding:10px 12px; text-align:center;">'
                        f'<span style="background:{color}22;color:{color};border:1px solid {color}55;border-radius:12px;'
                        f'padding:3px 10px;font-weight:700;font-size:12px;white-space:nowrap;">{icon} {status}</span></td>'
                    )
                    table_html += f'<td style="padding:10px 12px; color:#bbb; font-size:12px; line-height:1.4;">{por_que}</td>'
                    table_html += '</tr>'

                table_html += '</table>'
                st.markdown(table_html, unsafe_allow_html=True)

                st.markdown(
                    "<div style='font-size:12px;color:#888;margin-top:6px;'>"
                    "<b>Escala:</b> "
                    "<span style='color:#4AA3FF;'>▲ Ritmo en mejora</span> (deg &lt; 0) · "
                    "<span style='color:#27E36A;'>● Excelente</span> (&lt; 0.05 s/v) · "
                    "<span style='color:#F2C94C;'>● Normal</span> (0.05–0.10 s/v) · "
                    "<span style='color:#FF4D4D;'>● Alta</span> (&gt; 0.10 s/v). "
                    "'Ritmo base V1' = tiempo estimado con goma nueva (intercepto de la regresión)."
                    "</div>",
                    unsafe_allow_html=True
                )



    # ── WEATHER (wrapped in expander) ──────────────────────────────────────

    with st.expander("Clima de la Sesión"):

        try:

            w = race.weather_data.copy()

            w['Min'] = w['Time'].dt.total_seconds() / 60

            avg_track = float(w['TrackTemp'].mean()) if 'TrackTemp' in w.columns else None

            avg_air = float(w['AirTemp'].mean()) if 'AirTemp' in w.columns else None

            avg_delta = (avg_track - avg_air) if avg_track is not None and avg_air is not None else None

            m1_w, m2_w, m3_w = st.columns(3)

            with m1_w:

                st.metric("Temp pista prom.", f"{avg_track:.1f}°C" if avg_track is not None else "N/D")

            with m2_w:

                st.metric("Temp aire prom.", f"{avg_air:.1f}°C" if avg_air is not None else "N/D")

            with m3_w:

                st.metric("Δ pista-aire", f"{avg_delta:.1f}°C" if avg_delta is not None else "N/D")

            time_min_w = float(w['Min'].min()) if 'Min' in w.columns else 0.0

            time_max_w = float(w['Min'].max()) if 'Min' in w.columns else 0.0

            cursor_time_w = None

            if time_max_w > time_min_w:

                cursor_time_w = st.slider("Cursor tiempo (min)", time_min_w, time_max_w, time_min_w, step=1.0, key="weather_cursor_carrera")

            fig_w = go.Figure()

            if 'TrackTemp' in w.columns:

                fig_w.add_trace(go.Scatter(
                    x=w['Min'], y=w['TrackTemp'], name="Pista",
                    line=dict(color='#e74c3c', width=3),
                    hovertemplate="Min %{x:.1f}<br>Temp pista: %{y:.1f}°C<extra></extra>"
                ))

            if 'AirTemp' in w.columns:

                fig_w.add_trace(go.Scatter(
                    x=w['Min'], y=w['AirTemp'], name="Aire",
                    line=dict(color='#3498db', width=3),
                    hovertemplate="Min %{x:.1f}<br>Temp aire: %{y:.1f}°C<extra></extra>"
                ))

            if cursor_time_w is not None:

                fig_w.add_vline(x=cursor_time_w, line_dash="dot", line_color="#888")

            st.plotly_chart(make_god_chart(fig_w, "TEMPERATURAS", "°C", "Min", 420), use_container_width=True)

            sub_cols_w = st.columns(3)

            if 'WindSpeed' in w.columns:

                sub_cols_w[0].metric("Viento prom.", f"{float(w['WindSpeed'].mean()):.1f} km/h")

            if 'Humidity' in w.columns:

                sub_cols_w[1].metric("Humedad prom.", f"{float(w['Humidity'].mean()):.0f}%")

            if 'Rainfall' in w.columns:

                sub_cols_w[2].metric("Lluvia prom.", f"{float(w['Rainfall'].mean()):.2f} mm")

        except Exception:

            st.info("Datos de clima no disponibles.")

    # ── HEATMAP: velocidad punta (Speed Trap) por vuelta ──
    st.divider()
    st.markdown("**VELOCIDAD PUNTA (SPEED TRAP) POR VUELTA**")
    st.caption("Velocidad máxima en la trampa de velocidad en cada vuelta. Revela quién tiene menos drag / mejor punta y cómo cambia con el combustible, el rebufo (DRS/tow) y las tandas.")

    try:
        _stz = laps_vip.dropna(subset=['SpeedST', 'LapNumber']).copy()
        _stz = _stz[_stz['SpeedST'] > 0]
        if _stz.empty:
            st.info("No hay datos de velocidad punta (Speed Trap) para esta sesión.")
        else:
            _stz['LapNumber'] = _stz['LapNumber'].astype(int)
            _order_hm = [d for d in selected_abbr if d in set(_stz['Driver'].values)]
            _lap_min = int(_stz['LapNumber'].min())
            _lap_max = int(_stz['LapNumber'].max())
            _laps_axis = list(range(_lap_min, _lap_max + 1))
            _z = []
            for d in _order_hm:
                dd = _stz[_stz['Driver'] == d].groupby('LapNumber')['SpeedST'].max()
                _z.append([float(dd[l]) if l in dd.index else None for l in _laps_axis])
            if not _order_hm or not _laps_axis:
                st.info("No hay suficientes vueltas para el heatmap de velocidad punta.")
            else:
                fig_hm = go.Figure(go.Heatmap(
                    z=_z, x=_laps_axis, y=[get_driver_name(d) for d in _order_hm],
                    colorscale="Turbo", colorbar=dict(title="km/h"),
                    text=_z, texttemplate="%{z:.0f}", textfont=dict(size=9, color="#FFFFFF"),
                    hovertemplate="%{y}<br>Vuelta %{x}<br>%{z:.0f} km/h<extra></extra>",
                    hoverongaps=False
                ))
                fig_hm = make_god_chart(fig_hm, "VELOCIDAD PUNTA POR VUELTA (km/h)", "", "Vuelta", 120 + 42 * len(_order_hm))
                st.plotly_chart(fig_hm, use_container_width=True, config={"displayModeBar": False})
                _means = {d: float(_stz[_stz['Driver'] == d]['SpeedST'].mean()) for d in _order_hm}
                _maxs = {d: float(_stz[_stz['Driver'] == d]['SpeedST'].max()) for d in _order_hm}
                _top_mean = max(_means, key=_means.get)
                _top_max = max(_maxs, key=_maxs.get)
                render_chart_guide(
                    summary_text=(
                        f"{get_driver_name(_top_max)} marcó la punta más alta ({_maxs[_top_max]:.0f} km/h) y "
                        f"{get_driver_name(_top_mean)} tuvo la mayor media de velocidad punta ({_means[_top_mean]:.0f} km/h)."
                    ),
                    how_to_read=(
                        "- **Filas** = pilotos · **columnas** = vuelta · **color** = velocidad punta (más cálido = más rápido).\n"
                        "- **¿Un piloto SIEMPRE más cálido?** → menos drag (alerón más descargado) o mejor motor/ERS en recta.\n"
                        "- **¿Un salto puntual de color?** → suele ser rebufo/DRS (ir pegado a otro coche) o el combustible vaciándose.\n"
                        "- Los **huecos** (celdas vacías) son vueltas de entrada/salida de boxes o sin dato.\n"
                        "- Es la velocidad en la **trampa** oficial, no la punta absoluta de toda la vuelta."
                    )
                )
    except Exception as _e:
        st.info(f"No se pudo construir el heatmap de velocidad punta: {_e}")

    # ── LAP CHART: posición vuelta a vuelta (estilo MultiViewer) ──
    st.divider()
    st.markdown("**LAP CHART: posición de cada piloto vuelta a vuelta**")
    st.caption("La 'telaraña' de la carrera: cada línea es un piloto y su posición en cada vuelta (1º arriba). Los cruces son adelantamientos y paradas. Compañeros de equipo comparten color (uno sólido, otro punteado).")

    try:
        pos_laps = race.laps.dropna(subset=['Position', 'LapNumber', 'Driver']).copy()
        if pos_laps.empty:
            st.info("No hay datos de posición por vuelta para esta sesión.")
        else:
            pos_laps['LapNumber'] = pos_laps['LapNumber'].astype(int)
            pos_laps['Position'] = pos_laps['Position'].astype(int)
            _final_pos = pos_laps.sort_values('LapNumber').groupby('Driver')['Position'].last().sort_values()
            drivers_lc = [d for d in _final_pos.index if d in selected_abbr]
            if not drivers_lc:
                drivers_lc = list(_final_pos.index)
            n_drv_lc = len(drivers_lc)
            max_lap_lc = int(pos_laps['LapNumber'].max())
            _sel_pos = pos_laps[pos_laps['Driver'].isin(drivers_lc)]['Position']
            _pos_lo = int(_sel_pos.min()) if not _sel_pos.empty else 1
            _pos_hi = int(_sel_pos.max()) if not _sel_pos.empty else n_drv_lc
            team_seen_lc = {}
            fig_lc = go.Figure()
            _CC = {'SOFT': '#FF3B3B', 'MEDIUM': '#FFD23B', 'HARD': '#EDEDED',
                   'INTERMEDIATE': '#43B04A', 'WET': '#2B7FFF', 'UNKNOWN': '#AAAAAA'}
            _pit_x, _pit_y, _pit_c, _pit_t = [], [], [], []
            for d in drivers_lc:
                dd = pos_laps[pos_laps['Driver'] == d].sort_values('LapNumber')
                _team = _get_team_for_driver(race.laps, d)
                tkey = _team.lower() if isinstance(_team, str) else str(d)
                base = _TEAM_COLORS_NORM.get(tkey) if isinstance(_team, str) else None
                if not base:
                    base = get_driver_info(d)['color']
                _o = team_seen_lc.get(tkey, 0)
                team_seen_lc[tkey] = _o + 1
                _dash = 'solid' if _o == 0 else 'dash'
                fig_lc.add_trace(go.Scatter(
                    x=dd['LapNumber'], y=dd['Position'], mode='lines', name=d,
                    line=dict(color=base, width=2.4, dash=_dash, shape='spline', smoothing=0.5),
                    hovertemplate=f"{get_driver_name(d)}<br>Vuelta %{{x}} · P%{{y}}<extra></extra>"
                ))
                _last = dd.iloc[-1]
                fig_lc.add_annotation(
                    x=int(_last['LapNumber']), y=int(_last['Position']), text=f" {d}",
                    xanchor="left", yanchor="middle", showarrow=False,
                    font=dict(color=base, size=11, family="Roboto")
                )
                # Marcas de PIT (Opción tyre-age): inicio de cada stint > 1, color = compuesto nuevo
                if 'Stint' in dd.columns:
                    for _sid, _g in dd.dropna(subset=['Stint']).groupby('Stint'):
                        if int(_sid) <= 1:
                            continue
                        _row = _g.sort_values('LapNumber').iloc[0]
                        _comp = str(_row.get('Compound', 'UNKNOWN')).upper() if pd.notna(_row.get('Compound', None)) else 'UNKNOWN'
                        _pit_x.append(int(_row['LapNumber']))
                        _pit_y.append(int(_row['Position']))
                        _pit_c.append(_CC.get(_comp, _CC['UNKNOWN']))
                        _pit_t.append(f"{d} · PIT → {_comp.title()} (V{int(_row['LapNumber'])})")
            if _pit_x:
                fig_lc.add_trace(go.Scatter(
                    x=_pit_x, y=_pit_y, mode='markers', name='Pit',
                    marker=dict(symbol='diamond', size=9, color=_pit_c, line=dict(color='#0e1117', width=1.2)),
                    text=_pit_t, hovertemplate="%{text}<extra></extra>", showlegend=False
                ))
            fig_lc = make_god_chart(fig_lc, "LAP CHART · POSICIÓN VUELTA A VUELTA", "Posición", "Vuelta", 300 + 20 * n_drv_lc)
            fig_lc.update_layout(showlegend=False, hovermode="closest")
            fig_lc.update_yaxes(autorange="reversed", tickmode='array',
                                tickvals=list(range(_pos_lo, _pos_hi + 1)),
                                ticktext=[f"{p}º" for p in range(_pos_lo, _pos_hi + 1)])
            fig_lc.update_xaxes(range=[0.5, max_lap_lc + 3], dtick=5)
            # Sombreado de SC / VSC (Opción ventanas de pit / Safety Car)
            for _typ, _l0, _l1 in _sc_vsc_lap_ranges(race):
                _fc = "rgba(255,208,0,0.10)" if _typ == "SC" else "rgba(255,176,0,0.08)"
                fig_lc.add_vrect(x0=_l0 - 0.5, x1=_l1 + 0.5, fillcolor=_fc, line_width=0, layer="below")
                fig_lc.add_annotation(x=(_l0 + _l1) / 2.0, xref="x", y=1.0, yref="paper",
                                      text=_typ, showarrow=False, yanchor="bottom",
                                      font=dict(color="#FFD000", size=11, family="Roboto"))
            st.plotly_chart(fig_lc, use_container_width=True, config=DIST_CHART_CONFIG)
            _first_pos = pos_laps.sort_values('LapNumber').groupby('Driver')['Position'].first()
            _gains = (_first_pos - _final_pos)
            _gains = _gains[_gains.index.isin(drivers_lc)]
            _climber = _gains.idxmax()
            _dropper = _gains.idxmin()
            render_chart_guide(
                summary_text=(
                    f"{get_driver_name(_climber)} fue quien más ganó posiciones (+{int(_gains[_climber])}) y "
                    f"{get_driver_name(_dropper)} el que más perdió ({int(_gains[_dropper])})."
                ) if len(_gains) and (_gains[_climber] != 0 or _gains[_dropper] != 0) else None,
                how_to_read=(
                    "- **Eje Y**: posición (1º arriba) · **Eje X**: vuelta. Cada línea es un piloto.\n"
                    "- **¿Dos líneas se cruzan?** → hubo un adelantamiento (en pista o por paradas).\n"
                    "- **¿Una línea cae en picada y luego sube?** → una parada en boxes. Los **rombos** marcan el pit, con el color del compuesto NUEVO que montó.\n"
                    "- Las **bandas amarillas** son Safety Car / VSC: clave para ver quién aprovechó la parada 'barata'.\n"
                    "- Compañeros de equipo comparten color: **línea sólida** = uno, **punteada** = el otro.\n"
                    "- Líneas planas arriba = dominio; mucho cruce en la zona media = la pelea real de la carrera."
                )
            )
    except Exception as _e:
        st.info(f"No se pudo construir el lap chart: {_e}")

    # ── GAP AL LÍDER vuelta a vuelta (hueco de tiempo) ──
    st.divider()
    st.markdown("**GAP AL LÍDER: hueco de tiempo vuelta a vuelta**")
    st.caption("La carrera en TIEMPO (no en posiciones): el hueco de cada piloto respecto al líder en cada vuelta. Los saltos revelan undercuts, tráfico, Safety Cars y quién se escapa o recorta.")

    try:
        gl = race.laps.dropna(subset=['Driver', 'LapNumber', 'Time']).copy()
        if gl.empty:
            st.info("No hay datos de tiempo por vuelta para el gap al líder.")
        else:
            gl['LapNumber'] = gl['LapNumber'].astype(int)
            gl['Tsec'] = gl['Time'].dt.total_seconds()
            leader_t = gl.groupby('LapNumber')['Tsec'].min()
            _final_pos_g = race.laps.dropna(subset=['Position', 'LapNumber']).sort_values('LapNumber').groupby('Driver')['Position'].last().sort_values()
            _order_g = [d for d in _final_pos_g.index if d in set(gl['Driver'].values) and d in selected_abbr]
            if not _order_g:
                _order_g = [d for d in _final_pos_g.index if d in set(gl['Driver'].values)]
            team_seen_g = {}
            fig_gl = go.Figure()
            max_lap_g = int(gl['LapNumber'].max())
            _gap_hi = 0.0
            for d in _order_g:
                dd = gl[gl['Driver'] == d].sort_values('LapNumber')
                gap = dd['Tsec'].values - leader_t.reindex(dd['LapNumber'].values).values
                _team = _get_team_for_driver(race.laps, d)
                tkey = _team.lower() if isinstance(_team, str) else str(d)
                base = _TEAM_COLORS_NORM.get(tkey) if isinstance(_team, str) else None
                if not base:
                    base = get_driver_info(d)['color']
                _o = team_seen_g.get(tkey, 0)
                team_seen_g[tkey] = _o + 1
                _dash = 'solid' if _o == 0 else 'dash'
                _gv = gap[np.isfinite(gap)]
                if _gv.size:
                    _gap_hi = max(_gap_hi, float(np.nanpercentile(_gv, 90)))
                fig_gl.add_trace(go.Scatter(
                    x=dd['LapNumber'], y=gap, mode='lines', name=d,
                    line=dict(color=base, width=2, dash=_dash),
                    hovertemplate=f"{get_driver_name(d)}<br>Vuelta %{{x}} · +%{{y:.1f}} s<extra></extra>"
                ))
            fig_gl = make_god_chart(fig_gl, "GAP AL LÍDER (s) POR VUELTA", "Segundos tras el líder", "Vuelta", 520)
            fig_gl.update_layout(showlegend=True, hovermode="closest")
            _cap = max(_gap_hi * 1.12, 5.0)
            fig_gl.update_yaxes(range=[_cap, -1.0])  # líder (0) arriba, los de atrás abajo
            fig_gl.update_xaxes(range=[0.5, max_lap_g + 1], dtick=5)
            for _typ, _l0, _l1 in _sc_vsc_lap_ranges(race):
                _fc = "rgba(255,208,0,0.10)" if _typ == "SC" else "rgba(255,176,0,0.08)"
                fig_gl.add_vrect(x0=_l0 - 0.5, x1=_l1 + 0.5, fillcolor=_fc, line_width=0, layer="below")
            st.plotly_chart(fig_gl, use_container_width=True, config=DIST_CHART_CONFIG)
            render_chart_guide(
                summary_text=None,
                how_to_read=(
                    "- **Eje Y**: segundos por detrás del líder (arriba = líder, en 0) · **Eje X**: vuelta.\n"
                    "- **¿Una línea se aleja (baja) y luego vuelve?** → una parada en boxes (pierde ~20-25 s y recupera al parar los demás).\n"
                    "- **¿Dos líneas que se JUNTAN justo antes de una parada?** → un undercut / overcut en juego.\n"
                    "- Bajo **Safety Car / VSC** (bandas amarillas) los huecos se **comprimen**: ahí las paradas salen 'baratas'.\n"
                    "- El eje se recorta al grupo de cabeza (percentil 90), así que los coches doblados pueden quedar fuera por abajo."
                )
            )
    except Exception as _e:
        st.info(f"No se pudo construir el gap al líder: {_e}")

    # ── ESTRATEGIA DE NEUMÁTICOS: stints por piloto ──
    st.divider()
    st.markdown("**ESTRATEGIA DE NEUMÁTICOS: tandas (stints) y paradas por piloto**")
    st.caption("La estrategia de la carrera: cada barra es un piloto y sus tandas coloreadas por compuesto; cada corte es una parada en boxes.")

    _COMP_COL = {'SOFT': '#FF3B3B', 'MEDIUM': '#FFD23B', 'HARD': '#EDEDED',
                 'INTERMEDIATE': '#43B04A', 'WET': '#2B7FFF', 'UNKNOWN': '#888888'}
    try:
        _sl = race.laps.dropna(subset=['Driver', 'LapNumber', 'Stint']).copy()
        if 'Compound' not in _sl.columns or _sl.empty:
            st.info("No hay datos de compuestos/stints para esta sesión.")
        else:
            _sl['LapNumber'] = _sl['LapNumber'].astype(int)
            _fp = race.laps.dropna(subset=['Position', 'LapNumber']).sort_values('LapNumber').groupby('Driver')['Position'].last().sort_values()
            _order_ts = [d for d in _fp.index if d in set(_sl['Driver'].values) and d in selected_abbr]
            if not _order_ts:
                _order_ts = [d for d in _fp.index if d in set(_sl['Driver'].values)]
            if not _order_ts:
                _order_ts = sorted(_sl['Driver'].unique())
            fig_ts = go.Figure()
            _stops = {}
            for d in _order_ts:
                dd = _sl[_sl['Driver'] == d].sort_values('LapNumber')
                _stints = list(dd.groupby('Stint'))
                _stops[d] = max(len(_stints) - 1, 0)
                for _sid, g in _stints:
                    comp = str(g['Compound'].iloc[0]).upper() if pd.notna(g['Compound'].iloc[0]) else 'UNKNOWN'
                    ls = int(g['LapNumber'].min())
                    le = int(g['LapNumber'].max())
                    length = le - ls + 1
                    col = _COMP_COL.get(comp, _COMP_COL['UNKNOWN'])
                    fig_ts.add_trace(go.Bar(
                        y=[get_driver_name(d)], x=[length], base=ls - 1, orientation='h',
                        marker=dict(color=col, line=dict(color='#0e1117', width=1)),
                        text=[comp[:1]], textposition='inside', insidetextanchor='middle',
                        textfont=dict(color='#0e1117', size=10),
                        hovertemplate=f"{get_driver_name(d)}<br>{comp.title()}<br>Vueltas {ls}–{le} ({length})<extra></extra>",
                        showlegend=False
                    ))
            fig_ts = make_god_chart(fig_ts, "ESTRATEGIA DE NEUMÁTICOS (stints por piloto)", "", "Vuelta", 140 + 30 * len(_order_ts))
            fig_ts.update_layout(barmode='overlay', hovermode="closest", bargap=0.35)
            fig_ts.update_yaxes(autorange="reversed")
            fig_ts.update_xaxes(rangemode="tozero")
            st.plotly_chart(fig_ts, use_container_width=True, config={"displayModeBar": False})
            _leg = " &nbsp;&nbsp; ".join(
                f"<span style='color:{_COMP_COL[c]};font-weight:800;'>■</span> {c.title()}"
                for c in ['SOFT', 'MEDIUM', 'HARD', 'INTERMEDIATE', 'WET']
            )
            st.markdown(f"<div style='font-size:12px;color:#bbb;'>{_leg}</div>", unsafe_allow_html=True)
            if _stops:
                _common = max(set(_stops.values()), key=list(_stops.values()).count)
                _summary_ts = f"La estrategia más común fue de {_common} parada(s)."
            else:
                _summary_ts = None
            render_chart_guide(
                summary_text=_summary_ts,
                how_to_read=(
                    "- Cada **barra** es un piloto (1º arriba) y sus **tandas**; los colores son los compuestos: rojo=blando, amarillo=medio, blanco=duro, verde=intermedio, azul=lluvia.\n"
                    "- Cada **corte** entre colores es una **parada en boxes**; nº de segmentos − 1 = nº de paradas.\n"
                    "- **¿Un stint largo con duro?** → estrategia conservadora a 1 parada. **¿Varios cortos?** → agresiva a 2-3 paradas.\n"
                    "- **¿Un piloto paró ANTES que su rival directo?** → intentó un undercut (adelantar por boxes). **¿Alargó la tanda?** → overcut."
                )
            )
    except Exception as _e:
        st.info(f"No se pudo construir la estrategia de neumáticos: {_e}")

    # ── PARRILLA → META: posiciones ganadas / perdidas ──
    st.divider()
    st.markdown("**PARRILLA → META: posiciones ganadas y perdidas**")
    st.caption("Cuántas posiciones ganó o perdió cada piloto entre la salida (parrilla) y la meta. Verde = escaló, rojo = cedió.")
    try:
        _res = race.results
        if 'GridPosition' not in getattr(_res, 'columns', []) or 'Position' not in getattr(_res, 'columns', []):
            st.info("No hay datos de parrilla / resultado para esta sesión.")
        else:
            _gr = _res.dropna(subset=['Position', 'GridPosition'])
            _gr = _gr[_gr['GridPosition'] > 0]
            if _gr.empty:
                st.info("No hay parrilla de salida válida (sesión sin salida desde parrilla).")
            else:
                _rowsg = [(r['Abbreviation'], int(r['GridPosition']), int(r['Position']), int(r['GridPosition']) - int(r['Position']))
                          for _, r in _gr.iterrows()]
                _selg = [x for x in _rowsg if x[0] in selected_abbr] or _rowsg
                _selg = sorted(_selg, key=lambda x: x[3])
                fig_gf = go.Figure(go.Bar(
                    y=[get_driver_name(x[0]) for x in _selg], x=[x[3] for x in _selg], orientation='h',
                    marker=dict(color=["#00E676" if x[3] > 0 else ("#FF5252" if x[3] < 0 else "#888888") for x in _selg],
                                line=dict(color='#0e1117', width=1)),
                    text=[f"{x[3]:+d}" if x[3] != 0 else "0" for x in _selg], textposition='outside',
                    textfont=dict(color="#ddd", size=12),
                    hovertext=[f"{get_driver_name(x[0])}<br>Parrilla P{x[1]} → Meta P{x[2]}<br>{x[3]:+d} posiciones" for x in _selg],
                    hoverinfo="text", showlegend=False
                ))
                fig_gf.add_vline(x=0, line=dict(color="rgba(255,255,255,0.4)", width=1))
                fig_gf = make_god_chart(fig_gf, "POSICIONES GANADAS / PERDIDAS (parrilla → meta)", "", "Posiciones", 130 + 30 * len(_selg))
                fig_gf.update_layout(hovermode="closest")
                st.plotly_chart(fig_gf, use_container_width=True, config={"displayModeBar": False})
                _asc = sorted(_rowsg, key=lambda x: -x[3])
                render_chart_guide(
                    summary_text=(f"{get_driver_name(_asc[0][0])} fue el que más escaló (P{_asc[0][1]}→P{_asc[0][2]}, {_asc[0][3]:+d}) y "
                                  f"{get_driver_name(_asc[-1][0])} el que más cedió (P{_asc[-1][1]}→P{_asc[-1][2]}, {_asc[-1][3]:+d})."),
                    how_to_read=(
                        "- **Verde (+)** = ganó posiciones respecto a donde salió · **Rojo (−)** = las perdió.\n"
                        "- Es el 'saldo' de la carrera: junta salida, ritmo, estrategia y adelantamientos en un solo número.\n"
                        "- **¿+grande?** → remontada (salió mal clasificado o con penalización). **¿−grande?** → problemas, pinchazo o mala estrategia.\n"
                        "- No separa los adelantamientos en pista de los ganados por paradas — para el detalle mira el **Lap Chart**."
                    )
                )
    except Exception as _e:
        st.info(f"No se pudo construir parrilla→meta: {_e}")

    # ── RITMO CORREGIDO POR COMBUSTIBLE ──
    st.divider()
    st.markdown("**RITMO CORREGIDO POR COMBUSTIBLE**")
    st.caption("Quita el efecto del depósito (el coche se aligera y va más rápido según se vacía) para ver la degradación PURA del neumático de los pilotos seleccionados.")
    fuel_k = st.slider("Efecto del combustible (s por vuelta de carga)", 0.00, 0.10, 0.035, 0.005, key="fuel_k",
                       help="Cuánto más lento va el coche por cada vuelta de combustible a bordo. Típico ~0.03-0.05 s/vuelta. Súbelo/bájalo hasta que el ritmo a principio de tanda quede plano.")
    try:
        _fl = laps_vip[laps_vip['IsPit'] == False].copy() if 'IsPit' in laps_vip.columns else laps_vip.copy()
        _fl = _fl.dropna(subset=['LapNumber', 'LapTime', 'Driver'])
        if _fl.empty:
            st.info("No hay vueltas limpias para corregir por combustible.")
        else:
            _fl['LapNumber'] = _fl['LapNumber'].astype(int)
            fig_fc = go.Figure()
            _any_fc = False
            for d in selected_abbr:
                dd = _fl[_fl['Driver'] == d].sort_values('LapNumber')
                if dd.empty:
                    continue
                sec = dd['LapTime'].dt.total_seconds().values
                lapn = dd['LapNumber'].values.astype(float)
                med = np.median(sec)
                m = sec < med + 3.0  # descarta SC / tráfico
                corr = sec + fuel_k * (lapn - 1.0)  # normaliza a depósito lleno (quita la mejora por peso)
                if m.sum() < 2:
                    continue
                _any_fc = True
                fig_fc.add_trace(go.Scatter(
                    x=lapn[m], y=corr[m], mode='lines+markers', name=get_driver_name(d),
                    line=dict(color=get_neon_color(d), width=2), marker=dict(size=4),
                    hovertemplate=f"{get_driver_name(d)}<br>Vuelta %{{x:.0f}}<br>Corregido: %{{y:.2f}} s<extra></extra>"
                ))
            if _any_fc:
                fig_fc = make_god_chart(fig_fc, "RITMO CORREGIDO POR COMBUSTIBLE (s/vuelta)", "Tiempo corregido (s)", "Vuelta", 460)
                plot_wide(fig_fc)
                render_chart_guide(
                    summary_text=None,
                    how_to_read=(
                        f"- A cada vuelta se le suma **{fuel_k:.3f} s por cada vuelta de combustible ya gastada**, como si todos corrieran con el depósito lleno.\n"
                        "- Así se **quita la mejora** por el coche que se aligera y queda a la vista la **degradación real del neumático**.\n"
                        "- Tras corregir: línea que **sube** = la goma se degrada de verdad; línea **plana** = gestión excelente.\n"
                        "- Los **escalones** hacia abajo son cambios a goma nueva (paradas).\n"
                        "- El factor es ajustable: súbelo/bájalo hasta que el ritmo a principio de cada tanda quede plano."
                    )
                )
            else:
                st.info("No hay suficientes vueltas limpias de los pilotos seleccionados.")
    except Exception as _e:
        st.info(f"No se pudo construir el ritmo corregido: {_e}")

# --- TAB 5: FÍSICA ---
