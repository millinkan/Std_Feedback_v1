#!/usr/bin/env bash

set -euo pipefail

echo "==> Bootstrapping chess_full for Codespaces"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but not installed."
  exit 1
fi

if ! command -v pip >/dev/null 2>&1; then
  echo "pip is required but not installed."
  exit 1
fi

if [[ ! -d ".venv" ]]; then
  echo "==> Creating virtual environment (.venv)"
  python3 -m venv .venv
fi

echo "==> Activating virtual environment"
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> Installing Python dependencies"
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "==> Installing system dependencies (redis, stockfish)"
sudo apt-get update
sudo apt-get install -y redis-server stockfish

echo "==> Starting Redis"
sudo service redis-server start

STOCKFISH_BIN="${STOCKFISH_PATH:-/usr/games/stockfish}"
if [[ ! -x "$STOCKFISH_BIN" ]]; then
  echo "Stockfish binary not found at $STOCKFISH_BIN"
  echo "Set STOCKFISH_PATH and rerun."
  exit 1
fi

export STOCKFISH_PATH="$STOCKFISH_BIN"
export CELERY_BROKER_URL="${CELERY_BROKER_URL:-redis://localhost:6379/0}"
export CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-redis://localhost:6379/0}"

echo "==> Running migrations"
python manage.py migrate

cat <<EOF

Bootstrap complete.

Run app server:
  source .venv/bin/activate
  export STOCKFISH_PATH="$STOCKFISH_PATH"
  export CELERY_BROKER_URL="$CELERY_BROKER_URL"
  export CELERY_RESULT_BACKEND="$CELERY_RESULT_BACKEND"
  python manage.py runserver 0.0.0.0:8000

Run Celery worker in another terminal:
  source .venv/bin/activate
  export STOCKFISH_PATH="$STOCKFISH_PATH"
  export CELERY_BROKER_URL="$CELERY_BROKER_URL"
  export CELERY_RESULT_BACKEND="$CELERY_RESULT_BACKEND"
  celery -A chess_club worker -l info

EOF
