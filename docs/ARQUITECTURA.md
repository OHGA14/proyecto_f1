# Arquitectura y decisiones — F1 Data Dashboard

Documento de referencia del proyecto: qué es, cómo está organizado, por qué se decidió así, y el plan de evolución. Actualizar al cerrar cada fase.

## Qué es

Dashboard de telemetría y estrategia de F1 (Streamlit + FastF1 + Plotly), en español, con una regla editorial: **toda gráfica lleva un resumen calculado con datos reales y una guía de lectura estilo tip** ("¿ves X? → significa Y"). Sin emojis; estética broadcast oscura con acentos rojos.

## Estructura (desde Fase 1)

```
app_f12025.py      Orquestador Streamlit: sidebar, contexto, despacho a vistas (~600 líneas)
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
  views/           Una vista por pestaña con render(ctx); ctx = globals() del main.
                   Las vistas leen el contexto con ctx.get("nombre") y NO comparten
                   variables entre sí (verificado: cero filtraciones entre pestañas)
f1core/db.py       Capa DuckDB: esquema, ingesta idempotente, consultas
ingest.py          CLI de ingesta FastF1 → DuckDB (una sesión o --cached)
api/               FastAPI: la base DuckDB como JSON + sirve la web (main.py, queries.py)
web/               Web broadcast sin build: index.html + styles.css + app.js + Plotly vendorizado
tests/             pytest: motor de datos y API (sin red, con sesiones falsas)
docs/              Este documento
data.nosync/       f1.duckdb (derivada, regenerable; fuera de git/iCloud)
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
- **Fase 1b — Vistas** ✅ (tag `fase-1b`): cada pestaña en `app/views/*.py`; main ~600 líneas
- **Fase 2 — Capa de datos SQL** ✅ (tags `fase-2`, `fase-2b`): DuckDB en `data.nosync/f1.duckdb` + `ingest.py` (CLI; `--cached` barre la caché FastF1: 49 sesiones 2023→2026 en ~45 s) + pestaña **HISTÓRICO** (solo lee la base; consultas multi-GP en milisegundos): campeonato acumulado por temporada, ritmo puro por GP, head-to-head histórico, récords de speed trap. **Auto-sincronización**: cada sesión cargada en el dashboard se ingesta sola (en `load_session_data`, idempotente, falla en silencio). **Tests**: `tests/test_db.py` (5 pruebas con sesión falsa, sin red) — correr con `.venv.nosync/bin/python -m pytest tests/`.
  - *Ideas futuras:* telemetría a Parquet por sesión; degradación por circuito

### Esquema de la base (data.nosync/f1.duckdb)

| Tabla | Clave | Columnas principales |
|---|---|---|
| `sessions` | `session_id` = "año\|GP\|sesión" | year, round, gp, session, date, circuit, n_laps, n_drivers |
| `results` | session_id + abbr | full_name, team, grid, position, points, status, q1_s/q2_s/q3_s |
| `laps` | session_id + driver + lap | time_s, s1/s2/s3_s, compound, tyre_life, stint, speed_st/fl, is_pit_in/out, track_status, is_accurate |

Todos los tiempos en SEGUNDOS (float). Re-ingerir una sesión la reemplaza (idempotente).
- **Fase 3a — API + web broadcast** ✅ (tag `fase-3a`): **FastAPI** (`api/`) expone la base DuckDB como JSON (`/api/meta`, `/api/championship/{año}`, `/api/races/{año}`, `/api/session/detail?sid=`, `/api/h2h?a=&b=`, `/api/drivers`; Swagger en `/docs`) y sirve la **web broadcast** (`web/`): SPA sin build (HTML/CSS/JS + Plotly.js vendorizado, cero node/npm) con 3 vistas — TEMPORADA (tiles + campeonato + clasificación), CARRERA (tarjetas de GP, podio hero, ritmo, estrategia Gantt, speed trap, resultados) y HEAD-TO-HEAD (selectores + tiles + delta por GP). Cada gráfica lleva resumen calculado por la API + guía tip (la firma de la casa). **Paleta de display por equipo VALIDADA** para fondo oscuro (banda de luminosidad, croma, separación CVD, contraste 3:1) en `api/queries.py`; el 2º piloto de un equipo va aclarado. Ejecutar: `uvicorn api.main:app --port 8600`. Tests en `tests/test_api.py` (TestClient + base temporal).
  - *Siguiente (3b):* telemetría bajo demanda en la API; migrar a React/Next si se quiere SSR/animaciones complejas — la API ya lo soporta sin cambios

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
