"""HISTÓRICO: análisis multi-GP desde la base DuckDB (sin cargar FastF1)."""
import pandas as pd
import streamlit as st

from f1core import db
from f1core.charts import build_historic_pace_chart
from f1core.colors import get_neon_color
from app.components import render_chart_guide


def render(ctx):
    selected_abbr = ctx.get("selected_abbr") or []

    st.markdown("### HISTÓRICO: comparación entre Grandes Premios")
    st.caption(
        "Esta pestaña lee la base de datos local (DuckDB), no FastF1: responde al instante "
        "y cruza todos los GPs ingeridos. Para añadir sesiones: "
        "`python ingest.py --cached` (ingiere lo ya descargado) o "
        "`python ingest.py <año> \"<GP>\" \"<sesión>\"`."
    )

    if not db.db_exists():
        st.info("Aún no existe la base de datos. Ejecuta `python ingest.py --cached` "
                "en una terminal y recarga.")
        return

    con = db.connect(read_only=True)
    try:
        sesiones = db.list_sessions(con)
        if sesiones.empty:
            st.info("La base existe pero está vacía. Ejecuta `python ingest.py --cached`.")
            return

        # ------------------------------------------------ ritmo multi-GP (carreras)
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

            # pilotos: la selección del sidebar si está en la base; si no, los 6 con más GPs
            en_db = set(best["driver"].unique())
            drivers = [d for d in selected_abbr if d in en_db]
            if len(drivers) < 2:
                drivers = (best.groupby("driver")["gp"].nunique()
                           .sort_values(ascending=False).head(6).index.tolist())
            dfp = best[best["driver"].isin(drivers)].sort_values("orden")

            st.markdown("**RITMO PURO POR GP · % sobre la mejor vuelta de cada carrera**")
            colors = {d: get_neon_color(d) for d in drivers}
            st.plotly_chart(build_historic_pace_chart(dfp, colors),
                            use_container_width=True)

            # resumen calculado
            medias = dfp.groupby("driver")["pct"].mean().sort_values()
            lider = medias.index[0]
            n_gps = dfp["label"].nunique()
            ceros = dfp[dfp["pct"] == 0].groupby("driver").size().sort_values(ascending=False)
            rey = f"{ceros.index[0]} hizo la vuelta más rápida en {ceros.iloc[0]} de {n_gps} GPs. " if len(ceros) else ""
            render_chart_guide(
                summary_text=(f"En {n_gps} carreras ingeridas, {lider} es el más cercano al "
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

        # ------------------------------------------------ velocidad punta por GP
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

        # ------------------------------------------------ sesiones en la base
        with st.expander(f"Sesiones en la base ({len(sesiones)})"):
            st.dataframe(sesiones, use_container_width=True, hide_index=True)
    finally:
        con.close()
