"""Math Studio API — JSON scenes → Manim render."""

from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from generator import default_project, generate_manim_code

APP_DIR = Path(__file__).resolve().parent
RENDERS_DIR = APP_DIR / "renders"
SCRIPTS_DIR = APP_DIR / "scripts"
RENDERS_DIR.mkdir(exist_ok=True)
SCRIPTS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Math Studio", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Scene(BaseModel):
    type: Literal["equation", "graph", "text", "steps"] = "equation"
    latex: str | None = None
    function: str | None = None
    x_range: list[float] | None = None
    y_range: list[float] | None = None
    color: str | None = "BLUE"
    highlight: str | None = None
    content: str | None = None
    items: list[str] | None = None
    effect: Literal["write", "fade_in", "draw", "indicate"] = "write"
    wait: float = Field(default=2.0, ge=0, le=30)


class Project(BaseModel):
    title: str = "Math Studio"
    scenes: list[Scene] = Field(default_factory=list)


class RenderRequest(BaseModel):
    project: Project
    quality: Literal["low", "medium", "high"] = "low"


QUALITY_FLAGS = {
    "low": ["-ql"],
    "medium": ["-qm"],
    "high": ["-qh"],
}


def _find_output_video(job_dir: Path) -> Path | None:
    media = job_dir / "media" / "videos"
    if not media.exists():
        return None
    mp4s = sorted(media.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    return mp4s[0] if mp4s else None


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/template")
def template() -> dict[str, Any]:
    return default_project()


@app.post("/api/preview-code")
def preview_code(body: RenderRequest) -> dict[str, str]:
    code = generate_manim_code(body.project.model_dump())
    return {"code": code}


@app.post("/api/render")
def render_video(body: RenderRequest) -> dict[str, str]:
    job_id = uuid.uuid4().hex[:12]
    job_dir = RENDERS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    script_path = SCRIPTS_DIR / f"scene_{job_id}.py"
    code = generate_manim_code(body.project.model_dump())
    script_path.write_text(code, encoding="utf-8")

    quality_args = QUALITY_FLAGS.get(body.quality, ["-ql"])
    cmd = [
        sys.executable,
        "-m",
        "manim",
        *quality_args,
        "--media_dir",
        str(job_dir / "media"),
        str(script_path),
        "GeneratedScene",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(APP_DIR),
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Render timed out") from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail="Manim not installed. Run: pip install manim",
        ) from exc

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Manim render failed",
                "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-2000:],
            },
        )

    video = _find_output_video(job_dir)
    if not video:
        raise HTTPException(status_code=500, detail="No output video found")

    final_path = job_dir / "output.mp4"
    final_path.write_bytes(video.read_bytes())

    return {
        "job_id": job_id,
        "video_url": f"/api/video/{job_id}",
        "code": code,
    }


@app.get("/api/video/{job_id}")
def get_video(job_id: str) -> FileResponse:
    video_path = RENDERS_DIR / job_id / "output.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(video_path, media_type="video/mp4", filename=f"math-studio-{job_id}.mp4")
