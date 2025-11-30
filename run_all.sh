#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

VENV_PATH=".venv"
BACKEND="backend/app.py"
FRONTEND="front/st.py"
STREAMLIT_PORT=8501

if [ ! -f "$VENV_PATH/bin/activate" ]; then
  echo " Virtualenv não encontrado em '$VENV_PATH'. Ajuste VENV_PATH no script ou crie o venv."
  exit 1
fi

source "$VENV_PATH/bin/activate"

_cleanup() {
  echo
  echo "!!!! Parando serviços..."
  if [ -n "${FLASK_PID-}" ] && kill -0 "$FLASK_PID" 2>/dev/null; then
    echo "Matando Flask (PID $FLASK_PID)"
    kill "$FLASK_PID" 2>/dev/null || true
  fi
  exit 0
}
trap _cleanup INT TERM EXIT

echo "Iniciando Flask (backend/$BACKEND)..."
python -m backend.app &
FLASK_PID=$!
echo "   Flask PID = $FLASK_PID"
sleep 1

echo "Iniciando Streamlit (front/$FRONTEND) na porta $STREAMLIT_PORT..."
python -m streamlit run "$FRONTEND" --server.port "$STREAMLIT_PORT"
