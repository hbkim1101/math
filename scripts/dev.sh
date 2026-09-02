#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Math Studio Dev Server ==="

# Backend venv
if [ ! -d "$ROOT/backend/.venv" ]; then
  echo "Creating Python venv..."
  python3 -m venv "$ROOT/backend/.venv"
  "$ROOT/backend/.venv/bin/pip" install -r "$ROOT/backend/requirements.txt"
fi

# Frontend deps
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "Installing frontend dependencies..."
  (cd "$ROOT/frontend" && npm install)
fi

echo ""
echo "Starting backend  → http://127.0.0.1:8000"
echo "Starting frontend → http://127.0.0.1:5173"
echo ""
echo "Press Ctrl+C to stop both servers."
echo ""

SESSION_NAME="math-studio-dev"
tmux -f /exec-daemon/tmux.portal.conf has-session -t "=$SESSION_NAME" 2>/dev/null && tmux -f /exec-daemon/tmux.portal.conf kill-session -t "$SESSION_NAME" || true

tmux -f /exec-daemon/tmux.portal.conf new-session -d -s "$SESSION_NAME" -c "$ROOT" -- "${SHELL:-bash}" -l -c "
  cd '$ROOT/backend' && .venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000
"

tmux -f /exec-daemon/tmux.portal.conf split-window -h -t "$SESSION_NAME:0.0" -c "$ROOT/frontend" -- "${SHELL:-bash}" -l -c "
  npm run dev
"

echo "Servers running in tmux session: $SESSION_NAME"
echo "Attach with: tmux -f /exec-daemon/tmux.portal.conf attach -t $SESSION_NAME"
