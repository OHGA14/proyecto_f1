#!/bin/bash
# Doble clic para encender TODO el proyecto F1 con el código MÁS RECIENTE:
#   · Web data center  → http://localhost:8600
#   · Laboratorio (Streamlit) → http://localhost:8511
cd "$(dirname "$0")"

echo "🏁 HABIB CONTROL · encendiendo (versión más reciente)..."

# apaga instancias anteriores para no servir código viejo
pkill -f "uvicorn api.main:app" 2>/dev/null
pkill -f "streamlit run app_f12025.py" 2>/dev/null
sleep 1

nohup .venv/bin/uvicorn api.main:app --port 8600 >/tmp/f1_web.log 2>&1 &
echo "  · Web data center: arrancando en el puerto 8600"
nohup .venv/bin/streamlit run app_f12025.py --server.headless true --server.port 8511 >/tmp/f1_lab.log 2>&1 &
echo "  · Laboratorio: arrancando en el puerto 8511"

sleep 5
open "http://localhost:8600"
open "http://localhost:8511"
echo ""
echo "Listo. Puedes cerrar esta ventana."
