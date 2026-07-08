"""FÍSICA: fuerzas G, energía, fases de conducción."""
from app.components import plot_wide
from app.components import render_chart_guide
from app.data import get_cached_telemetry
from app.data import get_schedule
from app.data import load_session_data
from f1core.charts import apply_distance_axis
from f1core.charts import make_god_chart
from f1core.colors import get_driver_color
from f1core.colors import get_driver_name
from f1core.colors import get_neon_color
from f1core.colors import maybe_adjust_if_same
from f1core.laps import get_selected_lap
from f1core.physics import build_gg_envelope
from f1core.physics import compute_gg_from_telemetry
from f1core.timeutils import _get_sector_cut_distances
import numpy as np
import plotly.graph_objects as go
import streamlit as st
# @IMPORTS@  (generado por fix_names)


def render(ctx):
    gp = ctx.get("gp")
    lap_mode = ctx.get("lap_mode")
    laps = ctx.get("laps")
    race = ctx.get("race")
    selected_abbr = ctx.get("selected_abbr")
    session = ctx.get("session")
    target_lap = ctx.get("target_lap")
    year = ctx.get("year")
    # @UNPACK@  (generado por fix_names)

    # 1) G-FORCE LONGITUDINAL (ACELERACIÓN/FRENADA)

    st.markdown("**FUERZA G LONGITUDINAL: ¿dónde y cuán fuerte frena cada piloto?**")

    fig_long = go.Figure()

    glong_metrics = {}
    brake_zones = {}

    for d in selected_abbr:

        try:

            t = get_cached_telemetry(laps, d, lap_mode, target_lap)
            if t is None:
                continue

            # Mismo cálculo robusto que el G-G Plot (malla uniforme de distancia)
            gg_data = compute_gg_from_telemetry(t)
            if gg_data is None:
                continue
            dist_arr = gg_data['distance']
            glong = gg_data['glong']

            c = get_neon_color(d)

            name = get_driver_name(d)

            idx_brake = int(np.nanargmin(glong))
            glong_metrics[name] = {'max_accel': float(np.nanmax(glong)), 'max_brake': float(abs(np.nanmin(glong)))}
            brake_zones[name] = float(dist_arr[idx_brake])

            def _glong_hover_txt(val):
                if not np.isfinite(val):
                    return "Sin dato"
                if val < -0.15:
                    return f"Frenando: {abs(val):.2f}G"
                if val > 0.15:
                    return f"Acelerando: {val:.2f}G"
                return "Velocidad constante"

            hover = [
                f"<b>{name}</b><br>Dist: {dd:.0f} m<br>{_glong_hover_txt(val)}"
                for dd, val in zip(dist_arr, glong)
            ]

            fig_long.add_trace(go.Scatter(

                x=dist_arr, y=glong, mode='lines', name=name,

                line=dict(color=c, width=2),

                hovertext=hover, hoverinfo="text"

            ))

            # Marcar la frenada más fuerte de cada piloto
            fig_long.add_trace(go.Scatter(
                x=[dist_arr[idx_brake]], y=[float(glong[idx_brake])],
                mode='markers',
                marker=dict(symbol='triangle-down', size=12, color=c, line=dict(width=1.5, color='#FFFFFF')),
                hovertemplate=f"<b>{name}</b><br>Frenada más fuerte: {abs(float(glong[idx_brake])):.2f}G<br>Dist: {dist_arr[idx_brake]:.0f} m<extra></extra>",
                showlegend=False
            ))

        except:

            pass

    # Fondo: zona verde = acelerando, zona roja = frenando (lectura inmediata)
    fig_long.add_hrect(y0=0, y1=6, fillcolor="rgba(76,175,80,0.05)", line_width=0)
    fig_long.add_hrect(y0=-6, y1=0, fillcolor="rgba(231,76,60,0.06)", line_width=0)
    fig_long.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
    fig_long.add_annotation(x=0.01, y=0.95, xref="paper", yref="paper", text="ACELERANDO (pisa el gas)", showarrow=False, font=dict(size=12, color="#4CAF50"), xanchor="left")
    fig_long.add_annotation(x=0.01, y=0.05, xref="paper", yref="paper", text="FRENANDO (pisa el freno)", showarrow=False, font=dict(size=12, color="#E74C3C"), xanchor="left")

    fig_long.update_yaxes(range=[-6, 6], dtick=1)

    # Curvas + sectores en el eje X (mismo estilo que las demás gráficas por distancia)
    try:
        circuit_fisica = race.get_circuit_info()
        corners_fis = circuit_fisica.corners if circuit_fisica is not None else None
    except Exception:
        corners_fis = None
    sector_cuts_fis = None
    try:
        _ref_fis = selected_abbr[0]
        _lap_fis, _ = get_selected_lap(laps, _ref_fis, lap_mode, target_lap)
        _tel_fis = get_cached_telemetry(laps, _ref_fis, lap_mode, target_lap)
        if _lap_fis is not None and _tel_fis is not None:
            sector_cuts_fis, _ = _get_sector_cut_distances(_lap_fis, _tel_fis)
    except Exception:
        sector_cuts_fis = None

    fig_long = make_god_chart(fig_long, "FUERZA G LONGITUDINAL", "G (fuerza sobre el piloto)", "Distancia (m)", 500)
    apply_distance_axis(fig_long, corners_fis, sector_cuts_fis)
    plot_wide(fig_long)

    glong_parts = []
    for name, v in glong_metrics.items():
        zone_txt = f" (a los {brake_zones[name]:.0f} m)" if name in brake_zones else ""
        glong_parts.append(f"{name}: frenada más fuerte {v['max_brake']:.1f}G{zone_txt}; aceleración máxima {v['max_accel']:.1f}G.")
    render_chart_guide(
        summary_text=" ".join(glong_parts) if glong_parts else None,
        how_to_read=(
            "- Piensa en esta gráfica como **el pie del piloto**: verde (arriba) = pisa el acelerador; rojo (abajo) = pisa el freno.\n"
            "- **1G** ≈ tu propio peso. Una frenada de **4-5G** = el piloto siente 4-5 veces su peso lanzándolo hacia adelante.\n"
            "- Los **triángulos** marcan la frenada más fuerte de cada uno; las líneas T1, T2… son las curvas para ubicar dónde ocurre.\n"
            "- **¿Quién frena más TARDE (su pico rojo empieza más cerca de la curva) y más FUERTE?** → gana tiempo en esa frenada.\n"
            "- La aceleración (verde) es más suave que la frenada: el motor empuja menos de lo que muerden los frenos. Normal ver +1/+2G arriba y −4/−5G abajo."
        )
    )

    st.divider()

    # 2) G-G PLOT (LATERAL vs LONGITUDINAL) CON CONTROLES AVANZADOS

    st.markdown("**G-G PLOT (MANIOBRAS LATERALES + LONGITUDINALES)**")

    tgt = st.selectbox("Piloto G-G:", selected_abbr, format_func=get_driver_name, key='gg')
    compare = st.checkbox("Comparar con otro piloto", value=False)
    cmp_driver = None
    if compare and len(selected_abbr) > 1:
        cmp_opts = [d for d in selected_abbr if d != tgt]
        cmp_driver = st.selectbox("Piloto B:", cmp_opts, format_func=get_driver_name)

    color_mode = st.selectbox("Modo color", ["Velocidad", "Delta vs referencia", "Throttle", "Brake"], index=0)
    ref_driver = None
    if color_mode == "Delta vs referencia":
        ref_driver = st.selectbox("Referencia", selected_abbr, format_func=get_driver_name, key='gg_ref')
    speed_min = st.slider("Filtro velocidad (km/h)", 0, 330, 100)
    show_envelope = st.toggle("Mostrar envolvente (envelope)", value=False)

    try:
        t_main = get_cached_telemetry(laps, tgt, lap_mode, target_lap)
        # No usar st.stop() aquí: detendría toda la app (incluida la pestaña REPLAY)
        gg_main = compute_gg_from_telemetry(t_main) if t_main is not None else None
        gg_ref = None

        if t_main is None:
            st.warning(f"Telemetría no disponible para {get_driver_name(tgt)}.")
        elif gg_main is None:
            st.warning(f"Datos insuficientes para {get_driver_name(tgt)} (menos de 15 muestras).")
        else:
            fig_gg = go.Figure()
            color_a = get_driver_color(tgt, laps)

            if ref_driver and ref_driver != tgt:
                t_ref = get_cached_telemetry(laps, ref_driver, lap_mode, target_lap)
                if t_ref is not None:
                    gg_ref = compute_gg_from_telemetry(t_ref)

            def _apply_filter(gg):
                mask = gg["speed_kmh"] >= speed_min
                for k in ("glat", "glong", "speed_kmh", "distance"):
                    gg[k] = gg[k][mask]
                if gg["gear"] is not None:
                    gg["gear"] = gg["gear"][mask]
                if gg["throttle"] is not None:
                    gg["throttle"] = gg["throttle"][mask]
                if gg["brake"] is not None:
                    gg["brake"] = gg["brake"][mask]
                return gg

            gg_main = _apply_filter(gg_main)

            def _build_hover(gg):
                hover = []
                for i in range(len(gg["glat"])):
                    gear_txt = f"<br>Marcha: {int(gg['gear'][i])}" if gg["gear"] is not None else ""
                    hover.append(
                        f"G Lat: {gg['glat'][i]:+.2f}<br>G Long: {gg['glong'][i]:+.2f}"
                        f"<br>Vel: {gg['speed_kmh'][i]:.0f} km/h"
                        f"{gear_txt}<br>Dist: {gg['distance'][i]:.0f} m"
                    )
                return hover

            if compare and cmp_driver:
                t_cmp = get_cached_telemetry(laps, cmp_driver, lap_mode, target_lap)
                gg_cmp = compute_gg_from_telemetry(t_cmp) if t_cmp is not None else None
                if gg_cmp:
                    gg_cmp = _apply_filter(gg_cmp)

                    hover_a = _build_hover(gg_main)
                    hover_b = _build_hover(gg_cmp)
                    color_b = get_driver_color(cmp_driver, laps)
                    color_a, color_b = maybe_adjust_if_same(color_a, color_b)

                    fig_gg.add_trace(go.Scatter(
                        x=gg_main["glat"], y=gg_main["glong"],
                        mode='markers',
                        marker=dict(size=5, color=color_a, opacity=0.55, line=dict(width=0)),
                        hovertext=hover_a, hoverinfo="text",
                        name=tgt
                    ))
                    fig_gg.add_trace(go.Scatter(
                        x=gg_cmp["glat"], y=gg_cmp["glong"],
                        mode='markers',
                        marker=dict(size=5, color=color_b, opacity=0.45, line=dict(width=0)),
                        hovertext=hover_b, hoverinfo="text",
                        name=cmp_driver
                    ))

                    if show_envelope:
                        env_a = build_gg_envelope(gg_main["glat"], gg_main["glong"])
                        env_b = build_gg_envelope(gg_cmp["glat"], gg_cmp["glong"])
                        if env_a:
                            fig_gg.add_trace(go.Scatter(
                                x=env_a[0], y=env_a[1],
                                mode='lines',
                                line=dict(color=color_a, width=2),
                                hoverinfo='skip',
                                showlegend=False
                            ))
                        if env_b:
                            fig_gg.add_trace(go.Scatter(
                                x=env_b[0], y=env_b[1],
                                mode='lines',
                                line=dict(color=color_b, width=2),
                                hoverinfo='skip',
                                showlegend=False
                            ))
                else:
                    st.warning(f"Datos insuficientes para {get_driver_name(cmp_driver)}.")
            else:
                hover = _build_hover(gg_main)
                color_vals = gg_main["speed_kmh"]
                color_title = "Vel (km/h)"

                if color_mode == "Throttle" and gg_main["throttle"] is not None:
                    color_vals = gg_main["throttle"]
                    color_title = "Throttle (%)"
                elif color_mode == "Brake" and gg_main["brake"] is not None:
                    color_vals = gg_main["brake"]
                    color_title = "Brake (%)"
                elif color_mode == "Delta vs referencia" and gg_ref:
                    ref_speed = np.interp(gg_main["distance"], gg_ref["distance"], gg_ref["speed_kmh"])
                    color_vals = gg_main["speed_kmh"] - ref_speed
                    color_title = "Δ Vel (km/h)"

                fig_gg.add_trace(go.Scatter(
                    x=gg_main["glat"], y=gg_main["glong"],
                    mode='markers',
                    marker=dict(
                        size=5,
                        color=color_vals,
                        colorscale='Viridis',
                        showscale=True,
                        colorbar=dict(title=color_title, thickness=12, len=0.7),
                        line=dict(width=0)
                    ),
                    hovertext=hover,
                    hoverinfo="text",
                    name=tgt
                ))

                if show_envelope:
                    env = build_gg_envelope(gg_main["glat"], gg_main["glong"])
                    if env:
                        fig_gg.add_trace(go.Scatter(
                            x=env[0], y=env[1],
                            mode='lines',
                            line=dict(color=color_a, width=2),
                            hoverinfo='skip',
                            showlegend=False
                        ))

            max_range = max(np.max(np.abs(gg_main["glat"])), np.max(np.abs(gg_main["glong"])), 4)
            max_range = min(max_range + 0.5, 6)

            shapes = []
            for g_ref in [1, 2, 3, 4]:
                shapes.append(dict(
                    type="circle",
                    xref="x", yref="y",
                    x0=-g_ref, y0=-g_ref,
                    x1=g_ref, y1=g_ref,
                    line=dict(color="rgba(255,255,255,0.15)", width=1, dash="dot"),
                    fillcolor="rgba(0,0,0,0)"
                ))

            fig_gg.update_layout(
                template="plotly_dark",
                title=dict(text=f"<b>G-G PLOT: {get_driver_name(tgt)}</b>", font=dict(size=20, color="white")),
                height=680,
                plot_bgcolor="rgba(0,0,0,0.4)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(
                    range=[-max_range, max_range],
                    title="<b>G Lateral</b>",
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.05)",
                    zeroline=True,
                    zerolinewidth=1,
                    zerolinecolor="rgba(255,255,255,0.25)",
                    showline=True,
                    linecolor="#333"
                ),
                yaxis=dict(
                    range=[-max_range, max_range],
                    title="<b>G Longitudinal</b>",
                    showgrid=True,
                    gridcolor="rgba(255,255,255,0.05)",
                    zeroline=True,
                    zerolinewidth=1,
                    zerolinecolor="rgba(255,255,255,0.25)",
                    showline=True,
                    linecolor="#333",
                    scaleanchor="x",
                    scaleratio=1
                ),
                hovermode="closest",
                shapes=shapes,
                font=dict(family="Roboto", color="#ccc")
            )

            col_plot, col_stats = st.columns([3, 1])
            with col_plot:
                gg_cfg = {
                    "displayModeBar": True,
                    "scrollZoom": False,  # evita zoom accidental con la ruedita
                    "doubleClick": "reset",
                    "modeBarButtonsToRemove": ["lasso2d", "select2d"]
                }
                st.plotly_chart(fig_gg, use_container_width=True, config=gg_cfg)
            with col_stats:
                st.markdown("**Métricas G-G**")
                st.metric("Max lateral G", f"{np.max(np.abs(gg_main['glat'])):.2f}")
                st.metric("Max frenada G", f"{abs(np.min(gg_main['glong'])):.2f}")
                st.metric("Max tracción G", f"{np.max(gg_main['glong']):.2f}")
                if compare and cmp_driver and 'gg_cmp' in locals() and gg_cmp:
                    st.markdown(f"<span style='color:{color_b}; font-weight:600;'>{cmp_driver}</span>", unsafe_allow_html=True)
                    st.metric("Max lateral G", f"{np.max(np.abs(gg_cmp['glat'])):.2f}")
                    st.metric("Max frenada G", f"{abs(np.min(gg_cmp['glong'])):.2f}")
                    st.metric("Max tracción G", f"{np.max(gg_cmp['glong']):.2f}")

            render_chart_guide(
                summary_text=(
                    f"{get_driver_name(tgt)}: hasta {np.max(np.abs(gg_main['glat'])):.1f}G laterales, "
                    f"{abs(np.min(gg_main['glong'])):.1f}G de frenada y {np.max(gg_main['glong']):.1f}G de tracción "
                    f"(vueltas con velocidad ≥ {speed_min} km/h)."
                ),
                how_to_read=(
                    "- **Eje X**: G lateral (fuerza en las curvas) · **Eje Y**: G longitudinal (arriba = acelera, abajo = frena).\n"
                    "- Cada punto es un instante de la vuelta; los **círculos punteados** marcan 1, 2, 3 y 4G de referencia.\n"
                    "- **¿Los puntos llegan más LEJOS del centro?** → ese piloto lleva el coche más al límite.\n"
                    "- **¿El contorno es amplio y redondeado** (frena y gira a la vez)? → aprovecha bien el agarre combinado, no solo frena en recto.\n"
                    "- Los G se estiman de posición y velocidad GPS: son una aproximación, no el sensor real del coche."
                )
            )

    except Exception as e:
        st.error(f"Error al generar G-G Plot: {str(e)}")

    # ── DESPLIEGUE DE ENERGÍA: aceleración longitudinal vs velocidad (ERS/clipping) ──
    st.divider()
    st.markdown("**DESPLIEGUE DE ENERGÍA: aceleración longitudinal vs velocidad (ERS / clipping)**")
    st.caption("Solo con el coche a **pleno acelerador, en recta y sin frenar**: cómo despliega (y se queda sin) energía a lo largo del rango de velocidad. Es el gran diferenciador técnico de 2026.")

    ers_mode = st.radio(
        "Modo",
        ["Pilotos en esta sesión (estrategia ERS por escudería)",
         "Un piloto en 2 circuitos (efecto del trazado / drag)"],
        key="ers_mode", horizontal=True
    )

    def _ers_points(_tel):
        _gg = compute_gg_from_telemetry(_tel)
        if _gg is None or _gg.get('throttle') is None or _gg.get('brake') is None:
            return None, None
        _spd = _gg['speed_kmh']; _gl = _gg['glong'] * 9.81
        _thr = _gg['throttle']; _brk = _gg['brake']
        _brk_n = _brk / 100.0 if np.nanmax(_brk) > 1.5 else _brk
        _mask = (_thr >= 95) & (_brk_n < 0.1) & (np.abs(_gg['glat']) < 0.5) & np.isfinite(_spd) & np.isfinite(_gl)
        if _mask.sum() < 8:
            return None, None
        return _spd[_mask], _gl[_mask]

    def _add_ers_series(_fig, _sx, _sy, _color, _name, _dash='solid'):
        _fig.add_trace(go.Scatter(
            x=_sx, y=_sy, mode='markers', name=_name, legendgroup=_name,
            marker=dict(color=_color, size=5, opacity=0.26), showlegend=False,
            hovertemplate=f"{_name}<br>%{{x:.0f}} km/h<br>%{{y:.2f}} m/s²<extra></extra>"
        ))
        _xs = np.linspace(float(np.nanmin(_sx)), float(np.nanmax(_sx)), 60)
        try:
            _deg = 2 if len(np.unique(np.round(_sx))) > 3 else 1
            _ys = np.polyval(np.polyfit(_sx, _sy, _deg), _xs)
            _fig.add_trace(go.Scatter(
                x=_xs, y=_ys, mode='lines', name=_name, legendgroup=_name,
                line=dict(color=_color, width=3.5, dash=_dash),
                hovertemplate=f"{_name} · tendencia<br>%{{x:.0f}} km/h<br>%{{y:.2f}} m/s²<extra></extra>"
            ))
            return float(_xs[-1]), float(_ys[-1])
        except Exception:
            return None, None

    fig_ers = go.Figure()
    ers_parts = []
    _any_ers = False

    if ers_mode.startswith("Pilotos"):
        for d in selected_abbr:
            try:
                t = get_cached_telemetry(laps, d, lap_mode, target_lap)
                if t is None:
                    continue
                sx, sy = _ers_points(t)
                if sx is None:
                    continue
                _any_ers = True
                _xe, _ye = _add_ers_series(fig_ers, sx, sy, get_neon_color(d), get_driver_name(d))
                if _ye is not None:
                    ers_parts.append(f"{d}: a ~{_xe:.0f} km/h su empuje cae a {_ye:+.1f} m/s².")
            except Exception:
                pass
    else:
        _erc1, _erc2 = st.columns(2)
        with _erc1:
            ers_ref = st.selectbox("Piloto", selected_abbr, format_func=get_driver_name, key="ers_ref_driver")
        _other_gps = [g for g in get_schedule(year) if g != gp]
        with _erc2:
            ers_gp_b = st.selectbox(f"Comparar {gp} vs:", _other_gps, key="ers_gp_b") if _other_gps else None
        st.caption(f"**Circuito A** = {gp} (sesión actual, línea sólida) · **Circuito B** = el que elijas (línea punteada blanca). Mismo piloto: compara cómo el trazado y el drag mueven el punto de clipping.")
        try:
            tA = get_cached_telemetry(laps, ers_ref, lap_mode, target_lap)
            sxA, syA = _ers_points(tA) if tA is not None else (None, None)
            if sxA is not None:
                _any_ers = True
                _add_ers_series(fig_ers, sxA, syA, get_neon_color(ers_ref), f"{ers_ref} · {gp}", 'solid')
        except Exception:
            pass
        if ers_gp_b:
            try:
                with st.spinner(f"Cargando {ers_gp_b}…"):
                    sess_b = load_session_data(year, ers_gp_b, session)
                if sess_b is None:
                    st.info(f"No se pudieron cargar los datos de {ers_gp_b}.")
                else:
                    lap_b, _ = get_selected_lap(sess_b.laps, ers_ref, lap_mode, target_lap)
                    if lap_b is None:
                        st.info(f"{ers_ref} no tiene vuelta válida en {ers_gp_b}.")
                    else:
                        sxB, syB = _ers_points(lap_b.get_telemetry().add_distance())
                        if sxB is not None:
                            _any_ers = True
                            _add_ers_series(fig_ers, sxB, syB, "#FFFFFF", f"{ers_ref} · {ers_gp_b}", 'dash')
                        else:
                            st.info(f"No hay muestras a pleno gas en recta para {ers_ref} en {ers_gp_b}.")
            except Exception as _e:
                st.info(f"No se pudo comparar con {ers_gp_b}: {_e}")

    if _any_ers:
        fig_ers.add_hline(y=0, line=dict(color="rgba(255,255,255,0.35)", width=1, dash="dot"))
        fig_ers = make_god_chart(fig_ers, "ACELERACIÓN LONGITUDINAL vs VELOCIDAD (pleno gas · recta)", "Aceleración (m/s²)", "Velocidad (km/h)", 480)
        fig_ers.update_layout(showlegend=True)
        plot_wide(fig_ers)
        render_chart_guide(
            summary_text=" ".join(ers_parts) if ers_parts else None,
            how_to_read=(
                "- Solo instantes **a fondo, en recta y sin frenar**: es **empuje puro** (motor + ERS) contra la resistencia del aire.\n"
                "- **Y > 0** = el coche aún acelera (desplegando energía). A más velocidad la aceleración baja sola (drag + límite de potencia).\n"
                "- **¿La línea de tendencia se aplana o cae hacia 0 ANTES de la punta?** → ahí hay **clipping**: la batería/ERS se agotó (el diferenciador de 2026).\n"
                "- **Modo pilotos**: comparas escuderías en la misma pista → distinto *harvesting* (baja velocidad) y *deployment* (alta velocidad).\n"
                "- **Modo 2 circuitos**: el mismo piloto en dos trazados → cómo la pista y el drag mueven el punto de clipping. Se estima de la velocidad GPS."
            )
        )
    else:
        st.info("No hay suficientes muestras a pleno acelerador en recta para este análisis (prueba con una vuelta rápida).")

    # ── FASES DE CONDUCCIÓN: cómo se reparte la vuelta ──
    st.divider()
    st.markdown("**FASES DE CONDUCCIÓN: cómo se reparte la vuelta (a fondo / parcial / frenada / neutro)**")
    st.caption("Qué porcentaje del tiempo de la vuelta pasa cada piloto a pleno acelerador, con gas parcial, frenando, o sin gas ni freno (neutro/coasting).")

    phase_rows = []
    _PHASES = [("A fondo", "#00E676"), ("Parcial", "#F2C94C"), ("Frenada", "#FF5252"), ("Neutro", "#7A8290")]
    for d in selected_abbr:
        try:
            t = get_cached_telemetry(laps, d, lap_mode, target_lap)
            if t is None or 'Throttle' not in t.columns or 'Brake' not in t.columns:
                continue
            tt = t.dropna(subset=['Throttle', 'Brake', 'Time']).copy()
            if tt.empty:
                continue
            dt = tt['Time'].dt.total_seconds().diff().fillna(0).clip(lower=0).values
            thr = tt['Throttle'].astype(float).values
            _brk = tt['Brake']
            brk = _brk.astype(float).values
            brk_n = brk / 100.0 if np.nanmax(brk) > 1.5 else brk
            braking = brk_n > 0.05
            full = (~braking) & (thr >= 95)
            partial = (~braking) & (thr > 2) & (thr < 95)
            neutral = (~braking) & (thr <= 2)
            total = dt.sum() or 1.0
            phase_rows.append((d, {
                "A fondo": dt[full].sum() / total * 100.0,
                "Parcial": dt[partial].sum() / total * 100.0,
                "Frenada": dt[braking].sum() / total * 100.0,
                "Neutro": dt[neutral].sum() / total * 100.0,
            }))
        except Exception:
            pass

    if phase_rows:
        fig_ph = go.Figure()
        _pnames = [get_driver_name(d) for d, _ in phase_rows]
        for label, pcolor in _PHASES:
            _xvals = [p[label] for _, p in phase_rows]
            fig_ph.add_trace(go.Bar(
                y=_pnames, x=_xvals, name=label,
                orientation='h', marker=dict(color=pcolor),
                text=[f"{v:.0f}%" if v >= 6 else "" for v in _xvals],
                textposition='inside', insidetextanchor='middle',
                textfont=dict(color="#0e1117", size=12, family="Roboto"),
                hovertemplate="%{y}<br>" + label + ": %{x:.1f}%<extra></extra>"
            ))
        fig_ph = make_god_chart(fig_ph, "FASES DE CONDUCCIÓN (% del tiempo de vuelta)", "", "% del tiempo", 130 + 50 * len(phase_rows))
        fig_ph.update_layout(
            barmode='stack', margin=dict(l=120, r=20, t=78, b=42),
            legend=dict(orientation="h", y=1.22, x=0.5, xanchor="center", yanchor="bottom", font=dict(size=11))
        )
        fig_ph.update_xaxes(range=[0, 100], ticksuffix="%")
        st.plotly_chart(fig_ph, use_container_width=True, config={"displayModeBar": False})
        _fmax = max(phase_rows, key=lambda r: r[1]["A fondo"])
        render_chart_guide(
            summary_text=f"{get_driver_name(_fmax[0])} es quien más tiempo pasa a fondo en esta vuelta ({_fmax[1]['A fondo']:.0f}% del tiempo).",
            how_to_read=(
                "- **Verde (A fondo)**: acelerador ≥95% sin frenar · **Amarillo (Parcial)**: gas intermedio · **Rojo (Frenada)**: pisando el freno · **Gris (Neutro)**: ni gas ni freno (coasting).\n"
                "- Cada barra suma 100% del **tiempo** de la vuelta (ponderado por el tiempo real, no por número de puntos).\n"
                "- **¿Más verde?** → circuito de rectas o piloto más decidido a la salida. **¿Más amarillo?** → curvas rápidas donde se modula el gas.\n"
                "- **¿Mucho gris?** → gestión (lift-and-coast) o una vuelta no del todo al límite."
            )
        )
    else:
        st.info("No hay datos de acelerador/freno para las fases de conducción.")

# --- TAB 6: REPLAY ---
