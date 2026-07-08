"""HISTÓRICO: análisis multi-GP desde la base DuckDB (sin cargar FastF1)."""
import pandas as pd
import streamlit as st

from f1core import db
from f1core.charts import (build_historic_pace_chart, build_championship_chart,
                           build_h2h_history_chart)
from f1core.colors import get_neon_color
from f1core.config import _TEAM_COLORS_NORM
from app.components import render_chart_guide

# paleta de respaldo para pilotos históricos sin color propio ni de equipo
_PALETA = ["#FF2D2D", "#18BFA3", "#BE5F00", "#27508C", "#FFC400", "#FF2E9A",
           "#0E3D80", "#17664B", "#A7AEB0", "#9B59B6", "#2ECC71", "#E67E22"]


def _colores_para(drivers, equipo_por_piloto):
    """Color por piloto: DRIVER_DB/selección → color de su equipo → paleta."""
    out, usados = {}, 0
    for drv in drivers:
        c = get_neon_color(drv)
        if not c or c.upper() == "#FFFFFF":
            team = str(equipo_por_piloto.get(drv, "")).lower()
            c = _TEAM_COLORS_NORM.get(team)
        if not c or c in out.values():
            c = _PALETA[usados % len(_PALETA)]
            usados += 1
        out[drv] = c
    return out


def render(ctx):
    selected_abbr = ctx.get("selected_abbr") or []

    st.markdown("### HISTÓRICO: comparación entre Grandes Premios")
    st.caption(
        "Esta pestaña lee la base de datos local (DuckDB), no FastF1: responde al instante "
        "y cruza todos los GPs registrados. La base se alimenta SOLA: cada sesión que "
        "cargas en el dashboard se añade automáticamente. Para ingesta masiva: "
        "`python ingest.py --cached`."
    )

    if not db.db_exists():
        st.info("Aún no existe la base de datos. Carga cualquier sesión (se registra sola) "
                "o ejecuta `python ingest.py --cached` en una terminal.")
        return

    con = db.connect(read_only=True)
    try:
        sesiones = db.list_sessions(con)
        if sesiones.empty:
            st.info("La base existe pero está vacía. Carga una sesión o ejecuta "
                    "`python ingest.py --cached`.")
            return

        # ==================================================== 1. CAMPEONATO
        st.markdown("**CAMPEONATO: puntos acumulados por piloto**")
        anios = db.query(con, """
            SELECT DISTINCT s.year FROM results r JOIN sessions s USING(session_id)
            WHERE s.session IN ('Race','Sprint') ORDER BY s.year DESC""")["year"].tolist()
        if not anios:
            st.info("Aún no hay resultados de carrera en la base.")
        else:
            anio = st.selectbox("Temporada:", anios, key="hist_year")
            pts = db.query(con, """
                SELECT s.round, s.gp, r.abbr, r.team, COALESCE(r.points, 0) AS pts
                FROM results r JOIN sessions s USING(session_id)
                WHERE s.year = ? AND s.session IN ('Race','Sprint')""", [anio])
            # suma Sprint + Carrera del mismo fin de semana y acumula por ronda
            g = (pts.groupby(["round", "gp", "abbr"], as_index=False)
                    .agg(pts=("pts", "sum"), team=("team", "last"))
                    .sort_values("round"))
            g["cum_points"] = g.groupby("abbr")["pts"].cumsum()
            g["label"] = g["gp"].str.replace(" Grand Prix", "", regex=False)
            g["orden"] = g["round"]
            final = g[g["round"] == g["round"].max()].sort_values("cum_points",
                                                                  ascending=False)
            top = final.head(10)["abbr"].tolist()
            equipo = g.groupby("abbr")["team"].last().to_dict()
            dfc = g[g["abbr"].isin(top)].rename(columns={"abbr": "driver"})
            colores = _colores_para(top, equipo)
            st.plotly_chart(build_championship_chart(dfc, colores),
                            use_container_width=True)

            lid = final.iloc[0]
            gap2 = float(lid["cum_points"] - final.iloc[1]["cum_points"]) if len(final) > 1 else 0
            wins = db.query(con, """
                SELECT r.abbr, count(*) AS w FROM results r JOIN sessions s USING(session_id)
                WHERE s.year = ? AND s.session = 'Race' AND r.position = 1
                GROUP BY 1 ORDER BY w DESC""", [anio])
            rey = f" {wins.iloc[0]['abbr']} tiene más victorias ({int(wins.iloc[0]['w'])})." if not wins.empty else ""
            render_chart_guide(
                summary_text=(f"Temporada {anio} ({g['round'].nunique()} GPs en la base): "
                              f"{lid['abbr']} lidera con {int(lid['cum_points'])} pts, "
                              f"+{int(gap2)} sobre el segundo.{rey}"),
                how_to_read=(
                    "- **¿Dos líneas se separan?** → uno está sumando mucho más por fin de "
                    "semana; mira en qué GP empezó la brecha.\n"
                    "- **¿Una línea se aplana?** → racha mala: abandonos o fuera de puntos.\n"
                    "- **¿Se cruzan?** → cambio de liderato real en el campeonato.\n"
                    "- Incluye puntos de Sprint del mismo fin de semana (si esa Sprint está "
                    "en la base)."),
                key="hist_champ")

        st.divider()

        # ==================================================== 2. RITMO PURO POR GP
        best = db.query(con, """
            SELECT s.year, s.round, s.gp, l.driver, MIN(l.time_s) AS best_s
            FROM laps l JOIN sessions s USING(session_id)
            WHERE s.session = 'Race' AND l.time_s IS NOT NULL AND l.is_accurate
            GROUP BY 1, 2, 3, 4
        """)
        if best.empty:
            st.info("Todavía no hay carreras en la base (solo otras sesiones).")
        else:
            field_best = best.groupby(["year", "round", "gp"])["best_s"].transform("min")
            best["pct"] = (best["best_s"] / field_best - 1) * 100
            best["label"] = (best["gp"].str.replace(" Grand Prix", "", regex=False)
                             + " " + best["year"].astype(str).str[2:])
            best["orden"] = best["year"] * 100 + best["round"]

            en_db = set(best["driver"].unique())
            drivers = [d for d in selected_abbr if d in en_db]
            if len(drivers) < 2:
                drivers = (best.groupby("driver")["gp"].nunique()
                           .sort_values(ascending=False).head(6).index.tolist())
            dfp = best[best["driver"].isin(drivers)].sort_values("orden")

            st.markdown("**RITMO PURO POR GP · % sobre la mejor vuelta de cada carrera**")
            colores = _colores_para(drivers, {})
            st.plotly_chart(build_historic_pace_chart(dfp, colores),
                            use_container_width=True)

            medias = dfp.groupby("driver")["pct"].mean().sort_values()
            lider = medias.index[0]
            n_gps = dfp["label"].nunique()
            ceros = dfp[dfp["pct"] == 0].groupby("driver").size().sort_values(ascending=False)
            rey = f"{ceros.index[0]} hizo la vuelta más rápida en {ceros.iloc[0]} de {n_gps} GPs. " if len(ceros) else ""
            render_chart_guide(
                summary_text=(f"En {n_gps} carreras registradas, {lider} es el más cercano al "
                              f"límite: en promedio quedó a +{medias.iloc[0]:.2f}% de la mejor "
                              f"vuelta de cada GP. {rey}"),
                how_to_read=(
                    "- **¿Una línea toca el 0%?** → ese piloto hizo LA vuelta más rápida de esa carrera.\n"
                    "- **¿Una línea se mantiene plana y baja en todos los GPs?** → ritmo de élite constante, "
                    "sin importar el circuito.\n"
                    "- **¿Un pico hacia arriba en un GP concreto?** → ahí sufrió (tráfico, coche, lluvia); "
                    "compáralo con sus compañeros en ese mismo GP.\n"
                    "- La métrica es % sobre la mejor vuelta del GP, por eso se pueden comparar "
                    "circuitos totalmente distintos."),
                key="hist_pace")

            st.divider()

            # ================================================ 3. H2H HISTÓRICO
            st.markdown("**HEAD-TO-HEAD HISTÓRICO · Δ de mejor vuelta por GP**")
            frecuentes = (best.groupby("driver")["gp"].nunique()
                          .sort_values(ascending=False).index.tolist())
            def_a = selected_abbr[0] if len(selected_abbr) > 0 and selected_abbr[0] in en_db else frecuentes[0]
            def_b = selected_abbr[1] if len(selected_abbr) > 1 and selected_abbr[1] in en_db else \
                    next(d for d in frecuentes if d != def_a)
            c1, c2 = st.columns(2)
            drv_a = c1.selectbox("Piloto A:", frecuentes,
                                 index=frecuentes.index(def_a), key="hist_a")
            drv_b = c2.selectbox("Piloto B:", frecuentes,
                                 index=frecuentes.index(def_b), key="hist_b")
            if drv_a == drv_b:
                st.info("Elige dos pilotos distintos.")
            else:
                a = best[best["driver"] == drv_a][["label", "orden", "best_s"]]
                b = best[best["driver"] == drv_b][["label", "orden", "best_s"]]
                m = a.merge(b, on=["label", "orden"], suffixes=("_a", "_b"))
                if m.empty:
                    st.info("No comparten ningún GP en la base.")
                else:
                    m["delta_s"] = m["best_s_a"] - m["best_s_b"]
                    cols = _colores_para([drv_a, drv_b], {})
                    st.plotly_chart(
                        build_h2h_history_chart(m, drv_a, drv_b,
                                                cols[drv_a], cols[drv_b]),
                        use_container_width=True)
                    wins_a = int((m["delta_s"] < 0).sum())
                    n = len(m)
                    media = m["delta_s"].mean()
                    mas = drv_a if media < 0 else drv_b
                    render_chart_guide(
                        summary_text=(f"En {n} GPs comunes: {drv_a} fue más rápido en "
                                      f"{wins_a}, {drv_b} en {n - wins_a}. Ventaja media "
                                      f"de {mas}: {abs(media):.3f}s por vuelta rápida."),
                        how_to_read=(
                            f"- **¿Barra hacia abajo?** → {drv_a} hizo mejor vuelta ese GP "
                            "(misma convención que el delta: abajo = más rápido).\n"
                            "- **¿Barras gigantes (>1s)?** → probablemente lluvia, abandono "
                            "temprano o safety car; no siempre es ritmo puro.\n"
                            "- **¿Patrón por tipo de circuito?** → fíjate si uno domina en "
                            "urbanos y el otro en circuitos rápidos."),
                        key="hist_h2h")

        st.divider()

        # ==================================================== 4. SPEED TRAP
        vmax = db.query(con, """
            SELECT s.gp, s.year, l.driver, MAX(l.speed_st) AS vmax
            FROM laps l JOIN sessions s USING(session_id)
            WHERE s.session = 'Race' AND l.speed_st IS NOT NULL
            GROUP BY 1, 2, 3 QUALIFY row_number() OVER (PARTITION BY s.gp, s.year ORDER BY vmax DESC) = 1
            ORDER BY vmax DESC
        """)
        if not vmax.empty:
            st.markdown("**RÉCORD DE SPEED TRAP POR GP (carrera)**")
            vmax["GP"] = vmax["gp"] + " " + vmax["year"].astype(str)
            tabla = vmax[["GP", "driver", "vmax"]].rename(
                columns={"driver": "Piloto", "vmax": "km/h"})
            st.dataframe(tabla, use_container_width=True, hide_index=True)

        # ==================================================== 5. INVENTARIO
        with st.expander(f"Sesiones en la base ({len(sesiones)})"):
            st.dataframe(sesiones, use_container_width=True, hide_index=True)
    finally:
        con.close()
