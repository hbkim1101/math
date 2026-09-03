#!/usr/bin/env bash
# 한 번만 PNG 이미지로 렌더
#
# 사용법:
#   ./scripts/render_once.sh
#   ./scripts/render_once.sh problem_explanation.py LayoutStaticScene

set -euo pipefail
cd "$(dirname "$0")/.."

SCENE_FILE="${1:-problem_explanation.py}"
SCENE_NAME="${2:-LayoutStaticScene}"
PORT="${PREVIEW_PORT:-8765}"

if [[ -f ".venv/bin/activate" ]]; then
  source .venv/bin/activate
fi

mkdir -p preview
manim -ql -s --format png --media_dir preview/media "$SCENE_FILE" "$SCENE_NAME"

LATEST=$(find preview/media/images -name "${SCENE_NAME}*.png" -printf '%T@ %p\n' \
  | sort -rn | head -1 | cut -d' ' -f2-)
cp -f "$LATEST" preview/latest.png
date +%s > preview/version.txt

echo ""
echo "  이미지: preview/latest.png"
echo "  미리보기: http://localhost:$PORT"
