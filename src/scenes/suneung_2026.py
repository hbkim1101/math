from __future__ import annotations

from pathlib import Path

from src.dsl.models import get_problem, load_exam
from src.renderer.base import SuneungBaseScene

EXAM_PATH = Path(__file__).resolve().parents[2] / "problems" / "2026_suneung" / "common.yaml"
EXAM = load_exam(EXAM_PATH)


class Q01ExponentScene(SuneungBaseScene):
    problem = get_problem(EXAM, 1)

    def construct(self) -> None:
        header = self.show_header()
        question = self.show_question()
        self.run_solution(header, question)


class Q02DerivativeScene(SuneungBaseScene):
    problem = get_problem(EXAM, 2)

    def construct(self) -> None:
        header = self.show_header()
        question = self.show_question()
        self.run_solution(header, question)


class Q03SigmaScene(SuneungBaseScene):
    problem = get_problem(EXAM, 3)

    def construct(self) -> None:
        header = self.show_header()
        question = self.show_question()
        self.run_solution(header, question)


class Q04ContinuityScene(SuneungBaseScene):
    problem = get_problem(EXAM, 4)

    def construct(self) -> None:
        header = self.show_header()
        question = self.show_question()
        self.run_solution(header, question)
