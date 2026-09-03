#!/usr/bin/env bash
# 실시간 미리보기: 파일 저장 시 자동 재렌더 + 브라우저에서 확인
#
# 사용법:
#   ./scripts/live_preview.sh                          # 기본 씬
#   ./scripts/live_preview.sh problem_explanation.py LayoutPreviewScene

set -euo pipefail
cd "$(dirname "$0")/.."

SCENE_FILE="${1:-problem_explanation.py}"
SCENE_NAME="${2:-LayoutPreviewScene}"
PORT="${PREVIEW_PORT:-8765}"
QUALITY="${PREVIEW_QUALITY:-l}"   # l=저화질(빠름), m=중, h=고

VENV=".venv/bin/activate"
if [[ -f "$VENV" ]]; then
  # shellcheck disable=SC1090
  source "$VENV"
fi

OUTPUT_DIR="preview"
OUTPUT_MP4="$OUTPUT_DIR/latest.mp4"
mkdir -p "$OUTPUT_DIR"

render() {
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  렌더 중: $SCENE_FILE → $SCENE_NAME  (-q$QUALITY)"
  echo "  $(date '+%H:%M:%S')"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  manim -q"$QUALITY" --format mp4 --media_dir "$OUTPUT_DIR/media" \
    "$SCENE_FILE" "$SCENE_NAME" 2>&1 | tail -5

  # 최신 mp4를 preview/latest.mp4로 복사
  LATEST=$(find "$OUTPUT_DIR/media" -name "${SCENE_NAME}.mp4" -printf '%T@ %p\n' 2>/dev/null \
    | sort -rn | head -1 | cut -d' ' -f2-)
  if [[ -n "${LATEST:-}" && -f "$LATEST" ]]; then
    cp -f "$LATEST" "$OUTPUT_MP4"
    echo "  → $OUTPUT_MP4 갱신 완료"
  fi
}

# HTML 미리보기 페이지 생성
cat > "$OUTPUT_DIR/index.html" << 'HTML'
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="3">
  <title>Manim 실시간 미리보기</title>
  <style>
    * { margin: 0; box-sizing: border-box; }
    body {
      background: #0A1630;
      color: #e0e0e0;
      font-family: system-ui, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      min-height: 100vh;
      padding: 24px;
    }
    h1 { font-size: 1.25rem; margin-bottom: 8px; color: #5eead4; }
    p { font-size: 0.85rem; color: #94a3b8; margin-bottom: 16px; }
    video {
      max-width: 100%;
      border: 2px solid #334155;
      border-radius: 8px;
      background: #000;
    }
    .status { margin-top: 12px; font-size: 0.8rem; color: #64748b; }
  </style>
</head>
<body>
  <h1>Manim 실시간 미리보기</h1>
  <p>코드를 저장하면 자동 재렌더됩니다. 이 페이지는 3초마다 새로고침됩니다.</p>
  <video controls autoplay loop muted playsinline>
    <source src="latest.mp4?t=REFRESH" type="video/mp4">
  </video>
  <p class="status">REFRESH_TIME</p>
</body>
</html>
HTML

# 첫 렌더
render

# HTTP 서버 백그라운드 시작
if ! pgrep -f "python.*http.server.*$PORT" > /dev/null 2>&1; then
  python3 -m http.server "$PORT" --directory "$OUTPUT_DIR" > /dev/null 2>&1 &
  echo ""
  echo "  미리보기 주소: http://localhost:$PORT"
  echo "  (Cloud Agent VM에서는 포트 포워딩으로 접속)"
  echo ""
fi

# 파일 변경 감지 루프
WATCH_FILES=("$SCENE_FILE" "layout_config.py" "calculus_visualization.py")
echo "  감시 중: ${WATCH_FILES[*]}"
echo "  Ctrl+C 로 종료"
echo ""

LAST_HASH=""
while true; do
  CURRENT_HASH=$(md5sum "${WATCH_FILES[@]}" 2>/dev/null | md5sum | awk '{print $1}')
  if [ "$CURRENT_HASH" != "$LAST_HASH" ]; then
    if [ -n "$LAST_HASH" ]; then
      render
      TS=$(date '+%H:%M:%S')
      sed -i "s|REFRESH_TIME|마지막 렌더: ${TS}|" "$OUTPUT_DIR/index.html"
      sed -i "s|t=REFRESH|t=$(date +%s)|" "$OUTPUT_DIR/index.html"
    fi
    LAST_HASH="$CURRENT_HASH"
  fi
  sleep 2
done
