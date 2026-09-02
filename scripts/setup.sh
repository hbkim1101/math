#!/usr/bin/env bash
# Math Studio — first-time system + Python + Node setup (Ubuntu/Debian)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Installing system dependencies ==="
sudo apt-get update -qq
sudo apt-get install -y -qq \
  python3.12-venv python3-dev \
  ffmpeg \
  pkg-config libpango1.0-dev libcairo2-dev \
  texlive-latex-extra texlive-fonts-extra texlive-science cm-super dvipng \
  fonts-noto-cjk

echo "=== Python backend ==="
cd "$ROOT/backend"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

echo "=== Frontend ==="
cd "$ROOT/frontend"
npm install

echo ""
echo "Done! Run: ./scripts/dev.sh"
echo "Then open: http://localhost:5173"
