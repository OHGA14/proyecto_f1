# Arquitectura y decisiones — F1 Data Dashboard

Documento de referencia del proyecto: qué es, cómo está organizado, por qué se decidió así, y el plan de evolución. Actualizar al cerrar cada fase.

## Qué es

Dashboard de telemetría y estrategia de F1 (Streamlit + FastF1 + Plotly), en español, con una regla editorial: **toda gráfica lleva un resumen calculado con datos reales y una guía de lectura estilo tip** ("¿ves X? → significa Y"). Sin emojis; estética broadcast oscura con acentos rojos.

## Estructura (desde Fase 1)

```
app_f12025.py      Orquestador Streamlit: sidebar, contexto, 6 pestañas (~4,300 líneas)
f1core/            Lógica pura — PROHIBIDO importar streamlit aquí
  config.py        DRIVER_DB, colores de equipo/compuestos, constantes de sesión
  colors.py        Colores por selección (set_selection_colors + get_neon_color)
  timeutils.py     Formato de tiempos, sectores
  racecontrol.py   Track status (SC/VSC), race control, pits
  laps.py          Validación/selección/filtrado de vueltas
  physics.py       Fuerzas G (malla uniforme 5 m + savgol), DTW, mini-sectores
  charts.py        Constructores de figuras Plotly (datos → go.Figure)
app/               Capa de UI Streamlit
  theme.py         Todo el CSS global en apply_theme()
  components.py    Tarjetas de piloto, tablas, guías, grid de selección
  data.py          Caché @st.cache_* de sesiones FastF1, calendario, puntos
docs/              Este documento
legacy/            Versiones viejas (no versionado)
cache.nosync/      Caché FastF1 (~GB; fuera de git y de iCloud)
.venv.nosync/      Entorno virtual (fuera de iCloud)
```

**La regla de oro:** `f1core` nunca importa Streamlit. Cálculo recibe DataFrames y devuelve DataFrames; charts devuelven `go.Figure`. Esto permite reutilizar toda la lógica desde un script de ingesta, un backend API o cualquier UI futura.

## Decisiones técnicas clave

| Decisión | Por qué |
|---|---|
| `cache.nosync/` y `.venv.nosync/` | iCloud no sincroniza `*.nosync`; evita subir gigas. **iCloud borra symlinks** — no usar alias `.venv` |
| Caché FastF1 fuera de git | La historia vieja pesaba 4.1 GB; el repo limpio pesa <1 MB. Backup de la historia vieja: `~/proyecto_f1_OLD_git_backup` |
| `requirements.txt` congelado | Reproducible y deployable (streamlit 1.51.0, fastf1 3.8.3, plotly 6.5.0, pandas 2.3.3, numpy 2.3.5, scipy 1.16.3) |
| G's sobre malla uniforme de distancia | Timestamps crudos irregulares generan picos falsos de ±30G |
| X/Y de FastF1 en decímetros | Dividir /10 antes de curvatura/G lateral |
| Delta "abajo = más rápido" | Convención TV F1, pedida explícitamente |
| launch.json con ruta absoluta al streamlit global | macOS (TCC) bloquea ejecutar binarios dentro de iCloud Drive desde el lanzador de preview |

## Roadmap (acordado jul 2026)

- **Fase 0 — Higiene** ✅ (tag `fase-0`): .gitignore, repo limpio, requirements, venv, README
- **Fase 1 — Modularización** ✅ (tag `fase-1`): f1core/ + app/; main queda como orquestador
  - *Pendiente opcional 1b:* partir los cuerpos de las pestañas a `app/views/*.py`
- **Fase 2 — Capa de datos SQL**: DuckDB (tablas `sessions`, `results`, `laps`, `stints`, `lap_features`) + Parquet para telemetría + script `ingest.py`. Objetivo: arranque <1 s (hoy ~40 s) y análisis multi-GP/multi-temporada
- **Fase 3 — UI profesional**: FastAPI sirviendo los `go.Figure` como JSON (`fig.to_json()`) + frontend React/Next.js con `react-plotly.js`. Streamlit queda como laboratorio

## Si algo sale mal: cómo regresar

Cada fase queda committeada y con tag. Para volver:

```bash
git log --oneline            # ver historia
git stash                    # guarda cambios sin commitear (si los hay)
git checkout fase-1          # inspeccionar el estado de una fase (solo lectura)
git checkout main            # volver al presente
# retroceso REAL de la rama (destructivo, pedirlo con calma):
git reset --hard fase-1
```

Regla de trabajo: **no se empieza una fase con el árbol sucio** — todo committeado antes de tocar la siguiente.

## Convenciones al añadir gráficas

1. Constructor puro en `f1core/charts.py` (sin `st.`), render en la pestaña.
2. Siempre `render_chart_guide()` con resumen **calculado** (nunca inventado) + tips "¿ves X? → Y".
3. Nada de emojis en títulos/tips/captions; los títulos `**bold**` heredan la placa de acento por CSS.
4. Antes de añadir algo: revisar que no exista ya un equivalente (evitar duplicados).
