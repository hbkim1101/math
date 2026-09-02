#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
QUALITY="${1:-low}"
SCENE="${2:-Problem270630}"
FILE="${3:-scenes/problem_270630.py}"

cd "$ROOT"
source .venv/bin/activate 2>/dev/null || {
  echo "Run: python3 -m venv .venv && pip install -r requirements.txt"
  exit 1
}

case "$QUALITY" in
  low)    FLAG="-ql" ;;
  medium) FLAG="-qm" ;;
  high)   FLAG="-qh" ;;
  *)      FLAG="-ql" ;;
esac

manim -p"$FLAG" "$FILE" "$SCENE"
