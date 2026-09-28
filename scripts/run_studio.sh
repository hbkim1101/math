#!/usr/bin/env bash
# Explainer Studio 를 내 PC 브라우저에서 연다.
# 사용:  repo 루트에서  ./scripts/run_studio.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "[setup] Python venv 생성…"
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -U pip
  pip install -e ".[dev]"
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

PORT="${PORT:-8765}"
HOST="${HOST:-0.0.0.0}"
echo ""
echo "  Explainer Studio → http://localhost:${PORT}/"
echo "  (종료: Ctrl+C)"
echo ""
exec python -m explainer studio --host "$HOST" --port "$PORT" --root "$ROOT"
