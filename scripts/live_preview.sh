#!/usr/bin/env bash
# 실시간 미리보기: PNG 자동 재렌더 + 재생 버튼(애니메이션 MP4)
#
# 사용법:
#   ./scripts/live_preview.sh

set -euo pipefail
cd "$(dirname "$0")/.."

SCENE_FILE="${1:-problem_explanation.py}"
SCENE_NAME="${2:-LayoutStaticScene}"
PORT="${PREVIEW_PORT:-8765}"
QUALITY="${PREVIEW_QUALITY:-l}"

export PREVIEW_PORT="$PORT"
export PREVIEW_SCENE_FILE="$SCENE_FILE"
export PREVIEW_ANIM_SCENE="${PREVIEW_ANIM_SCENE:-LayoutPreviewScene}"
export PREVIEW_QUALITY="$QUALITY"

VENV=".venv/bin/activate"
if [[ -f "$VENV" ]]; then
  # shellcheck disable=SC1090
  source "$VENV"
fi

OUTPUT_DIR="preview"
OUTPUT_PNG="$OUTPUT_DIR/latest.png"
VERSION_FILE="$OUTPUT_DIR/version.txt"
mkdir -p "$OUTPUT_DIR"

write_version() {
  date +%s > "$VERSION_FILE"
}

render_png() {
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  PNG 렌더: $SCENE_FILE → $SCENE_NAME  (-q$QUALITY -s)"
  echo "  $(date '+%H:%M:%S')"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  manim -q"$QUALITY" -s --format png --media_dir "$OUTPUT_DIR/media" \
    "$SCENE_FILE" "$SCENE_NAME" 2>&1 | tail -5

  LATEST=$(find "$OUTPUT_DIR/media/images" -name "${SCENE_NAME}*.png" -printf '%T@ %p\n' 2>/dev/null \
    | sort -rn | head -1 | cut -d' ' -f2-)
  if [[ -n "${LATEST:-}" && -f "$LATEST" ]]; then
    cp -f "$LATEST" "$OUTPUT_PNG"
    write_version
    echo "  → $OUTPUT_PNG 갱신 ($(cat "$VERSION_FILE"))"
  else
    echo "  ✗ PNG를 찾지 못했습니다"
  fi
}

# 기존 서버 종료
pkill -f "preview_server.py" 2>/dev/null || true
pkill -f "python.*http.server.*${PORT}" 2>/dev/null || true
sleep 0.5

render_png

python3 scripts/preview_server.py > /dev/null 2>&1 &
echo ""
echo "  ▶ 재생 버튼: http://localhost:$PORT"
echo ""

WATCH_FILES=("$SCENE_FILE" "layout_config.py" "suneung_problems.py" "calculus_visualization.py")
echo "  감시 중: ${WATCH_FILES[*]}"
echo "  Ctrl+C 로 종료"
echo ""

LAST_HASH=""
while true; do
  CURRENT_HASH=$(md5sum "${WATCH_FILES[@]}" 2>/dev/null | md5sum | awk '{print $1}')
  if [ "$CURRENT_HASH" != "$LAST_HASH" ]; then
    if [ -n "$LAST_HASH" ]; then
      render_png
    fi
    LAST_HASH="$CURRENT_HASH"
  fi
  sleep 2
done
