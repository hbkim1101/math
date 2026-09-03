#!/usr/bin/env bash
# 실시간 미리보기: 파일 저장 시 PNG 자동 재렌더 + 브라우저에서 확인
#
# 사용법:
#   ./scripts/live_preview.sh
#   ./scripts/live_preview.sh problem_explanation.py LayoutStaticScene

set -euo pipefail
cd "$(dirname "$0")/.."

SCENE_FILE="${1:-problem_explanation.py}"
SCENE_NAME="${2:-LayoutStaticScene}"
PORT="${PREVIEW_PORT:-8765}"
QUALITY="${PREVIEW_QUALITY:-l}"

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

render() {
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

cat > "$OUTPUT_DIR/index.html" << 'HTML'
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
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
    img {
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
  <p>코드를 저장하면 PNG가 자동 재렌더됩니다.</p>
  <img id="preview" src="latest.png" alt="레이아웃 미리보기">
  <p class="status" id="status">로딩 중...</p>
  <script>
    let lastVersion = null;
    const img = document.getElementById("preview");
    const status = document.getElementById("status");

    async function poll() {
      try {
        const res = await fetch("version.txt?" + Date.now(), { cache: "no-store" });
        const ver = (await res.text()).trim();
        if (ver !== lastVersion) {
          lastVersion = ver;
          img.src = "latest.png?v=" + ver;
          const d = new Date(Number(ver) * 1000);
          status.textContent = "마지막 렌더: " + d.toLocaleTimeString("ko-KR");
        }
      } catch (e) {
        status.textContent = "version.txt 대기 중...";
      }
    }
    poll();
    setInterval(poll, 1500);
  </script>
</body>
</html>
HTML

# 기존 서버 종료 후 재시작 (오래된 캐시 방지)
pkill -f "python.*http.server.*${PORT}" 2>/dev/null || true
sleep 0.5

render

python3 -m http.server "$PORT" --bind 0.0.0.0 --directory "$OUTPUT_DIR" > /dev/null 2>&1 &
echo ""
echo "  미리보기: http://localhost:$PORT"
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
      render
    fi
    LAST_HASH="$CURRENT_HASH"
  fi
  sleep 2
done
