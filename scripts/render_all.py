#!/usr/bin/env python3
"""Render 2026 수능 수학 1~4번 시각화 영상."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENES = [
    ("Q01ExponentScene", "q01_exponent"),
    ("Q02DerivativeScene", "q02_derivative"),
    ("Q03SigmaScene", "q03_sigma"),
    ("Q04ContinuityScene", "q04_continuity"),
]


def render_all(quality: str = "m") -> None:
    output_dir = ROOT / "output" / "2026_suneung"
    output_dir.mkdir(parents=True, exist_ok=True)
    scene_file = ROOT / "src" / "scenes" / "suneung_2026.py"

    for scene_name, slug in SCENES:
        print(f"\n{'='*50}")
        print(f"Rendering {scene_name} -> {slug}.mp4")
        print(f"{'='*50}")
        cmd = [
            str(ROOT / ".venv" / "bin" / "manim"),
            f"-q{quality}",
            "--media_dir",
            str(output_dir),
            "-o",
            slug,
            str(scene_file),
            scene_name,
        ]
        result = subprocess.run(cmd, cwd=str(ROOT), check=False)
        if result.returncode != 0:
            print(f"ERROR: Failed to render {scene_name}", file=sys.stderr)
            sys.exit(result.returncode)

    print(f"\nAll renders complete. Output: {output_dir}")


if __name__ == "__main__":
    quality = sys.argv[1] if len(sys.argv) > 1 else "m"
    render_all(quality)
