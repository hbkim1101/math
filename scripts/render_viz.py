#!/usr/bin/env python3
"""Render graph-centric visualization videos."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIM = ROOT / ".venv" / "bin" / "manim"
OUT = ROOT / "output" / "2026_suneung"

SCENES = [
    ("src/scenes/q02_viz.py", "Q02DerivativeVizScene", "q02_derivative"),
    ("src/scenes/suneung_2026.py", "Q01ExponentScene", "q01_exponent"),
    ("src/scenes/suneung_2026.py", "Q03SigmaScene", "q03_sigma"),
    ("src/scenes/q04_viz.py", "Q04ContinuityVizScene", "q04_continuity"),
    ("src/scenes/calc_q30.py", "Q30CalculusScene", "q30_calculus"),
    ("src/scenes/calc_q28.py", "Q28SeptMockScene", "q28_calculus"),
    ("src/scenes/calc_q21.py", "Q21CubicInequalityScene", "q21_cubic"),
]


def render_all(quality: str = "m") -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for scene_file, scene_name, slug in SCENES:
        print(f"\n>>> {scene_name} -> {slug}.mp4")
        cmd = [
            str(MANIM),
            f"-q{quality}",
            "--media_dir",
            str(OUT),
            "-o",
            slug,
            str(ROOT / scene_file),
            scene_name,
        ]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT)
        rc = subprocess.run(cmd, cwd=str(ROOT), env=env).returncode
        if rc != 0:
            sys.exit(rc)
    print(f"\nDone: {OUT}")


if __name__ == "__main__":
    render_all(sys.argv[1][1:] if len(sys.argv) > 1 else "m")
