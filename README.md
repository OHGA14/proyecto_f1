# F1 Data Dashboard

Dashboard de telemetría y estrategia de Fórmula 1 construido con **Streamlit + FastF1 + Plotly**. Análisis de vuelta rápida, comparativas entre pilotos, física del coche (fuerzas G, fases de conducción), estrategia de carrera y replay animado — con resúmenes calculados y guías de lectura en cada gráfica.

## Vistas

| Pestaña | Contenido |
|---|---|
| **PANORAMA** | Veredicto de la sesión: más rápido, ventaja, consistencia, speed trap, distribución de ritmo, clasificación Q1/Q2/Q3, mejores sectores y vuelta ideal |
| **TELEMETRÍA** | Delta, velocidad, acelerador, freno y marchas por distancia; similitud DTW; micro-sectores estilo MultiViewer |
| **VS VUELTAS** | Comparador de 2 vueltas del mismo piloto |
| **CARRERA** | Lap chart, gap al líder, estrategia de neumáticos (Gantt), degradación por stint, parrilla→meta, ritmo corregido por combustible |
| **FÍSICA** | G-G plot, fuerza G longitudinal, despliegue de energía (ERS/clipping), fases de conducción |
| **REPLAY** | Replay animado N pilotos con close-up sincronizado y dominancia por mini-sector |
| **HISTÓRICO** | Comparación multi-GP desde base DuckDB local: ritmo puro por carrera, récords de speed trap (responde en milisegundos, sin cargar FastF1) |

## Ejecutar

```bash
python3 -m venv .venv.nosync                                # una sola vez
.venv.nosync/bin/pip install -r requirements.txt            # una sola vez
.venv.nosync/bin/streamlit run app_f12025.py
```

> El venv se llama `.venv.nosync` para que iCloud no lo sincronice (iCloud además elimina symlinks, así que no se usa alias `.venv`).

La primera carga de una sesión descarga los datos de FastF1 (~1–2 min) y los cachea en `cache.nosync/` (excluida de git y de iCloud). Las cargas siguientes usan la caché.

### Base de datos histórica (pestaña HISTÓRICO)

```bash
.venv.nosync/bin/python ingest.py --cached                       # ingiere todo lo ya descargado
.venv.nosync/bin/python ingest.py 2026 "British Grand Prix" "Race"   # una sesión concreta
```

Crea/actualiza `data.nosync/f1.duckdb` (~1 s por sesión). La pestaña HISTÓRICO consulta esa base para análisis multi-GP instantáneos.

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
