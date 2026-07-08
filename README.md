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

## Ejecutar

```bash
python3 -m venv .venv.nosync && ln -s .venv.nosync .venv   # una sola vez
.venv/bin/pip install -r requirements.txt                   # una sola vez
.venv/bin/streamlit run app_f12025.py
```

La primera carga de una sesión descarga los datos de FastF1 (~1–2 min) y los cachea en `cache.nosync/` (excluida de git y de iCloud). Las cargas siguientes usan la caché.

## Estructura

- `app_f12025.py` — aplicación completa (en proceso de modularización a `f1core/` + `app/`)
- `requirements.txt` — versiones congeladas
- `legacy/` — versiones anteriores (no versionado)
- `colab/` — cuadernos de exploración
