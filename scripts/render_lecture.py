#!/usr/bin/env python3
"""Render lecture video from YAML DSL — no per-problem Scene needed."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIM = ROOT / ".venv" / "bin" / "manim"


def render(yaml_path: Path, problem_id: int, quality: str = "m", force_tts: bool = False) -> Path:
    exam_slug = yaml_path.stem
    out_slug = f"lecture_q{problem_id:02d}_{exam_slug}"
    out_dir = ROOT / "output" / "lectures"
    out_dir.mkdir(parents=True, exist_ok=True)

    tts_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "generate_lecture_tts.py"),
        str(yaml_path),
        "--id",
        str(problem_id),
    ]
    if force_tts:
        tts_cmd.append("--force")
    subprocess.run(tts_cmd, cwd=str(ROOT), env={**os.environ, "PYTHONPATH": str(ROOT)}, check=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["LECTURE_YAML"] = str(yaml_path.resolve())
    env["LECTURE_PROBLEM_ID"] = str(problem_id)

    cmd = [
        str(MANIM),
        f"-q{quality}",
        "--media_dir",
        str(out_dir),
        "-o",
        out_slug,
        str(ROOT / "src/scenes/generic_lecture.py"),
        "GenericLectureScene",
    ]
    print(f"\n>>> GenericLectureScene  problem={problem_id}  yaml={yaml_path.name}")
    rc = subprocess.run(cmd, cwd=str(ROOT), env=env).returncode
    if rc != 0:
        sys.exit(rc)

    mp4 = out_dir / "videos" / "generic_lecture" / "720p30" / f"{out_slug}.mp4"
    docs = ROOT / "docs" / "videos" / f"{out_slug}.mp4"
    if mp4.exists():
        docs.parent.mkdir(parents=True, exist_ok=True)
        docs.write_bytes(mp4.read_bytes())
        print(f"\nDone: {mp4}\nCopied: {docs}")
    return mp4


def main() -> None:
    parser = argparse.ArgumentParser(description="YAML → 강의 영상 자동 렌더")
    parser.add_argument("yaml", type=Path, nargs="?", default=ROOT / "problems/2026_suneung/calc_q28_june.yaml")
    parser.add_argument("--id", type=int, default=28)
    parser.add_argument("-q", "--quality", default="m")
    parser.add_argument("--force-tts", action="store_true")
    args = parser.parse_args()
    render(args.yaml, args.id, args.quality, args.force_tts)


if __name__ == "__main__":
    main()
