#!/usr/bin/env bash

set -euo pipefail

echo "==> Starting Eschen Chess Club services"

if [[ ! -d ".venv" ]]; then
  echo ".venv not found. Run ./bootstrap_codespace.sh first."
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

export STOCKFISH_PATH="${STOCKFISH_PATH:-/usr/games/stockfish}"
export CELERY_BROKER_URL="${CELERY_BROKER_URL:-redis://localhost:6379/0}"
export CELERY_RESULT_BACKEND="${CELERY_RESULT_BACKEND:-redis://localhost:6379/0}"

if [[ ! -x "$STOCKFISH_PATH" ]]; then
  echo "Stockfish binary not found at $STOCKFISH_PATH"
  exit 1
fi

mkdir -p .logs

echo "==> Applying database migrations"
python manage.py migrate --noinput

echo "==> Ensuring Redis is running"
sudo service redis-server start >/dev/null

echo "==> Starting Celery worker (background)"
nohup celery -A chess_club worker -l info > .logs/celery.log 2>&1 &
CELERY_PID=$!
echo "$CELERY_PID" > .logs/celery.pid

echo "==> Starting Celery Beat (scheduled Lichess sync, background)"
nohup celery -A chess_club beat -l info > .logs/celery_beat.log 2>&1 &
CELERY_BEAT_PID=$!
echo "$CELERY_BEAT_PID" > .logs/celery_beat.pid

cleanup() {
  if [[ -f .logs/celery.pid ]]; then
    PID="$(cat .logs/celery.pid)"
    if ps -p "$PID" >/dev/null 2>&1; then
      echo "==> Stopping Celery worker ($PID)"
      kill "$PID" >/dev/null 2>&1 || true
    fi
    rm -f .logs/celery.pid
  fi
  if [[ -f .logs/celery_beat.pid ]]; then
    BPID="$(cat .logs/celery_beat.pid)"
    if ps -p "$BPID" >/dev/null 2>&1; then
      echo "==> Stopping Celery Beat ($BPID)"
      kill "$BPID" >/dev/null 2>&1 || true
    fi
    rm -f .logs/celery_beat.pid
  fi
}

trap cleanup EXIT INT TERM

echo "==> Starting Django server on 0.0.0.0:8000"
python manage.py runserver 0.0.0.0:8000
