# F1 Data Dashboard

Plataforma de datos de Fórmula 1 en dos frentes: un **dashboard de telemetría** (Streamlit + FastF1 + Plotly) para el análisis profundo de cada sesión, y un **data center web** (FastAPI + DuckDB) estilo broadcast para el histórico multi-GP. Toda gráfica lleva resumen calculado con datos reales y guía de lectura.

## Web broadcast (FastAPI + DuckDB)

```bash
.venv/bin/uvicorn api.main:app --port 8600
# → http://localhost:8600        (web: TEMPORADA · CARRERA · ANÁLISIS · HEAD-TO-HEAD)
# → http://localhost:8600/docs   (API Swagger)
```

Cuatro vistas: campeonato con puntos acumulados y clasificación, detalle de carrera (podio, ritmo, estrategia de neumáticos, speed trap, resultados), **ANÁLISIS de telemetría** (mapa de dominancia por mini-sector, G-G, velocidad/delta/acelerador/freno/marchas por distancia y fases de conducción — carga sesiones FastF1 bajo demanda) y head-to-head histórico entre dos pilotos. Sin node ni build: HTML/CSS/JS con Plotly.js vendorizado, colores de equipo validados para accesibilidad (contraste y daltonismo).

## Vistas

| Pestaña | Contenido |
|---|---|
| **PANORAMA** | Veredicto de la sesión: más rápido, ventaja, consistencia, speed trap, distribución de ritmo, clasificación Q1/Q2/Q3, mejores sectores y vuelta ideal |
| **TELEMETRÍA** | Delta, velocidad, acelerador, freno y marchas por distancia; similitud DTW; micro-sectores estilo MultiViewer |
| **VS VUELTAS** | Comparador de 2 vueltas del mismo piloto |
| **CARRERA** | Lap chart, gap al líder, estrategia de neumáticos (Gantt), degradación por stint, parrilla→meta, ritmo corregido por combustible |
| **FÍSICA** | G-G plot, fuerza G longitudinal, despliegue de energía (ERS/clipping), fases de conducción |
| **REPLAY** | Replay animado N pilotos con close-up sincronizado y dominancia por mini-sector |
| **HISTÓRICO** | Análisis multi-GP desde base DuckDB local: campeonato acumulado por temporada, ritmo puro por carrera, head-to-head histórico entre 2 pilotos, récords de speed trap (responde en milisegundos, sin cargar FastF1) |

## Ejecutar

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m venv .venv   # una sola vez
.venv/bin/pip install -r requirements.txt                                       # una sola vez
.venv/bin/streamlit run app_f12025.py
```

> El proyecto vive en `~/proyectos/f1`, fuera de iCloud Drive (ver docs/ARQUITECTURA.md).

La primera carga de una sesión descarga los datos de FastF1 (~1–2 min) y los cachea en `cache.nosync/` (excluida de git y de iCloud). Las cargas siguientes usan la caché.

### Base de datos histórica (pestaña HISTÓRICO)

```bash
.venv/bin/python ingest.py --cached                       # ingiere todo lo ya descargado
.venv/bin/python ingest.py 2026 "British Grand Prix" "Race"   # una sesión concreta
```

Crea/actualiza `data.nosync/f1.duckdb` (~1 s por sesión). La pestaña HISTÓRICO consulta esa base para análisis multi-GP instantáneos. Además, **cada sesión que cargas en el dashboard se registra sola** en la base (auto-sincronización idempotente).

### Tests

```bash
.venv/bin/pip install -r requirements-dev.txt   # una sola vez
.venv/bin/python -m pytest tests/
```

## Estructura

- `app_f12025.py` — orquestador Streamlit (~600 líneas): sidebar, contexto y despacho a las vistas
- `f1core/` — lógica pura, **sin Streamlit** (reutilizable desde cualquier UI o script):
  - `config.py` pilotos/equipos/colores/constantes · `colors.py` colores por selección
  - `timeutils.py` tiempos y sectores · `laps.py` selección/filtrado de vueltas
  - `racecontrol.py` SC/VSC/banderas/pits · `physics.py` fuerzas G, DTW, mini-sectores
  - `charts.py` constructores de figuras Plotly
- `app/` — capa de UI Streamlit:
  - `theme.py` CSS global · `components.py` tarjetas/tablas/guías · `data.py` caché de datos
  - `views/` una vista por pestaña: `panorama` `telemetria` `vs_vueltas` `carrera` `fisica` `replay`
- `requirements.txt` — versiones congeladas
- `legacy/` — versiones anteriores (no versionado)
- `colab/` — cuadernos de exploración
