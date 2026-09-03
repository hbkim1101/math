#!/usr/bin/env python3
"""미리보기 HTTP 서버: PNG 정적 제공 + 재생 버튼용 MP4 렌더 API."""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREVIEW = ROOT / "preview"
PORT = int(os.environ.get("PREVIEW_PORT", "8765"))
SCENE_FILE = os.environ.get("PREVIEW_SCENE_FILE", "problem_explanation.py")
ANIM_SCENE = os.environ.get("PREVIEW_ANIM_SCENE", "LayoutPreviewScene")
QUALITY = os.environ.get("PREVIEW_QUALITY", "l")
VENV_MANIM = ROOT / ".venv" / "bin" / "manim"

render_lock = threading.Lock()
video_state = {"status": "idle", "version": None, "error": None}


def render_video() -> None:
    """LayoutPreviewScene을 MP4로 렌더하고 preview/latest.mp4에 복사."""
    global video_state

    with render_lock:
        video_state = {"status": "rendering", "version": None, "error": None}

    manim = str(VENV_MANIM) if VENV_MANIM.exists() else "manim"
    cmd = [
        manim,
        f"-q{QUALITY}",
        "--format",
        "mp4",
        "--media_dir",
        str(PREVIEW / "media"),
        SCENE_FILE,
        ANIM_SCENE,
    ]

    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr[-800:] or "manim failed")

        videos = list((PREVIEW / "media" / "videos").rglob(f"{ANIM_SCENE}.mp4"))
        if not videos:
            raise RuntimeError("MP4 파일을 찾지 못했습니다")

        latest = max(videos, key=lambda p: p.stat().st_mtime)
        dest = PREVIEW / "latest.mp4"
        dest.write_bytes(latest.read_bytes())

        ver = str(int(time.time()))
        (PREVIEW / "video_version.txt").write_text(ver, encoding="utf-8")

        with render_lock:
            video_state = {"status": "ready", "version": ver, "error": None}
    except Exception as exc:
        with render_lock:
            video_state = {"status": "error", "version": None, "error": str(exc)}


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PREVIEW), **kwargs)

    def log_message(self, fmt, *args):
        if self.path.startswith("/api/"):
            super().log_message(fmt, *args)

    def do_POST(self):
        if self.path == "/api/render-video":
            with render_lock:
                if video_state["status"] == "rendering":
                    self._json(409, {"error": "이미 렌더 중입니다"})
                    return

            threading.Thread(target=render_video, daemon=True).start()
            self._json(202, {"ok": True})
            return

        self.send_error(404)

    def do_GET(self):
        if self.path.startswith("/api/video-status"):
            with render_lock:
                self._json(200, dict(video_state))
            return

        return super().do_GET()

    def _json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main():
    PREVIEW.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), PreviewHandler)
    print(f"  미리보기: http://localhost:{PORT}")
    print(f"  재생 씬: {SCENE_FILE} → {ANIM_SCENE}")
    server.serve_forever()


if __name__ == "__main__":
    main()
