"""ffmpeg 후처리: 라우드니스 정규화, 자막(번인/소프트), 최종 인코딩."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from ..narration.timeline import Timeline
from ..script.models import Project
from .subtitles import build_cues, write_ass, write_srt


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 실패:\n{' '.join(cmd)}\n{proc.stderr[-3000:]}")


def probe(path: str | Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def finalize_video(project: Project, timeline: Timeline, movie: Path, out_dir: Path, preview: bool = False,
                   log=print) -> dict:
    """Manim 결과물 → 자막/라우드니스 처리된 최종 mp4. 산출물 경로를 dict 로 돌려준다."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    info = probe(movie)
    vstream = next(s for s in info["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    w, h = int(vstream["width"]), int(vstream["height"])

    cues = build_cues(timeline)
    srt = write_srt(cues, out_dir / "subtitles.srt")
    ass = write_ass(cues, out_dir / "subtitles.ass", width=w, height=h)

    stem = f"{project.meta.id}{'_preview' if preview else ''}"
    final = out_dir / f"{stem}.mp4"
    mode = project.meta.subtitles

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(movie)]
    if mode == "soft":
        cmd += ["-i", str(srt)]
    vf = []
    if mode == "burn" and cues:
        vf.append(f"ass={ass.as_posix()}")
    if vf:
        cmd += ["-vf", ",".join(vf)]
    crf = "23" if preview else "17"
    cmd += ["-c:v", "libx264", "-preset", "medium" if not preview else "veryfast", "-crf", crf,
            "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if has_audio:
        af = []
        if project.meta.loudnorm:
            af.append("loudnorm=I=-16:TP=-1.5:LRA=11")
        # 오디오가 마지막 내레이션에서 끝나므로 영상 길이만큼 무음을 채운다
        af += ["aresample=48000", "apad"]
        cmd += ["-af", ",".join(af), "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    if mode == "soft":
        cmd += ["-c:s", "mov_text", "-metadata:s:s:0", "language=kor"]
        cmd += ["-map", "0:v", "-map", "0:a?", "-map", "1:0"]
    cmd += ["-metadata", f"title={project.meta.title}", str(final)]
    _run(cmd)

    manifest = {
        "project": project.meta.model_dump(),
        "final_video": str(final),
        "manim_video": str(movie),
        "subtitles_srt": str(srt),
        "subtitles_ass": str(ass),
        "cues": [c.__dict__ for c in cues],
        "timeline": timeline.to_json(),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    if log:
        log(f"  [final] {final}  ({final.stat().st_size / 1e6:.1f} MB, {len(cues)} 자막 큐)")
    return manifest
