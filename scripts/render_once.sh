#!/usr/bin/env bash
# 한 번만 빠르게 렌더 + 미리보기 페이지 열기
#
# 사용법:
#   ./scripts/render_once.sh
#   ./scripts/render_once.sh problem_explanation.py LayoutPreviewScene

set -euo pipefail
cd "$(dirname "$0")/.."

SCENE_FILE="${1:-problem_explanation.py}"
SCENE_NAME="${2:-LayoutPreviewScene}"
PORT="${PREVIEW_PORT:-8765}"

if [[ -f ".venv/bin/activate" ]]; then
  source .venv/bin/activate
fi

mkdir -p preview
manim -ql --format mp4 --media_dir preview/media "$SCENE_FILE" "$SCENE_NAME"

LATEST=$(find preview/media -name "${SCENE_NAME}.mp4" -printf '%T@ %p\n' \
  | sort -rn | head -1 | cut -d' ' -f2-)
cp -f "$LATEST" preview/latest.mp4

echo ""
echo "  영상: preview/latest.mp4"
echo "  미리보기: http://localhost:$PORT (./scripts/live_preview.sh 실행 중일 때)"
