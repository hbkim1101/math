"""Generic lecture scene — YAML + env vars only, no per-problem code."""

from __future__ import annotations

import os
from pathlib import Path

from manim import Scene

from src.dsl.lecture_models import get_lecture_problem, load_lecture_exam
from src.renderer.lecture_engine import LectureEngine

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_YAML = ROOT / "problems" / "2026_suneung" / "calc_q28_june.yaml"


class GenericLectureScene(Scene):
    """LECTURE_YAML + LECTURE_PROBLEM_ID 환경변수로 문제 지정."""

    def construct(self) -> None:
        yaml_path = Path(os.environ.get("LECTURE_YAML", str(DEFAULT_YAML)))
        problem_id = int(os.environ.get("LECTURE_PROBLEM_ID", "28"))
        exam = load_lecture_exam(yaml_path)
        problem = get_lecture_problem(exam, problem_id)
        LectureEngine(self, problem).run()
