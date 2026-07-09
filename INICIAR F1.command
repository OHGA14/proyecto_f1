#!/bin/bash
# Doble clic para encender TODO el proyecto F1:
#   · Web data center  → http://localhost:8600
#   · Laboratorio (28 gráficas originales) → http://localhost:8511
cd "$(dirname "$0")"

echo "🏁 HABIB CONTROL · encendiendo..."

if ! curl -s --max-time 2 http://localhost:8600 >/dev/null 2>&1; then
  nohup .venv/bin/uvicorn api.main:app --port 8600 >/tmp/f1_web.log 2>&1 &
  echo "  · Web data center: arrancando en el puerto 8600"
else
  echo "  · Web data center: ya estaba encendida"
fi

if ! curl -s --max-time 2 http://localhost:8511 >/dev/null 2>&1; then
  nohup .venv/bin/streamlit run app_f12025.py --server.headless true --server.port 8511 >/tmp/f1_lab.log 2>&1 &
  echo "  · Laboratorio: arrancando en el puerto 8511"
else
  echo "  · Laboratorio: ya estaba encendido"
fi

sleep 5
open "http://localhost:8600"
open "http://localhost:8511"
echo ""
echo "Listo. Puedes cerrar esta ventana."
