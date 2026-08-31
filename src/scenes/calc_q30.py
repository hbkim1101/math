from __future__ import annotations

from pathlib import Path

from manim import *

from src.config import KOREAN_FONT, STEP_COLOR, TITLE_COLOR
from src.dsl.models import get_problem, load_exam
from src.renderer.base import SuneungBaseScene

EXAM_PATH = Path(__file__).resolve().parents[2] / "problems" / "2026_suneung" / "calc_q30.yaml"
EXAM = load_exam(EXAM_PATH)


class Q30CalculusScene(SuneungBaseScene):
    """2026 수능 미적분 30번 — 역함수와 교점 개수."""

    problem = get_problem(EXAM, 30)
    exam_title = "2026학년도 수능 미적분"

    def show_header(self) -> VGroup:
        badge = Text(
            f"제 {self.problem.id}문 (단답형 · {self.problem.points}점)",
            font=KOREAN_FONT,
            font_size=28,
            color=TITLE_COLOR,
        )
        topic = Text(
            self.problem.topic,
            font=KOREAN_FONT,
            font_size=22,
            color=GRAY_A,
        )
        header = VGroup(badge, topic).arrange(DOWN, buff=0.12)
        header.to_edge(UP, buff=0.3)
        self.play(FadeIn(header, shift=DOWN * 0.15), run_time=0.5)
        return header

    def show_question(self) -> VGroup:
        q_label = Text("문제", font=KOREAN_FONT, font_size=26, color=STEP_COLOR)
        lines = [
            Text("f: 실수 전체에서 증가·연속,  h = f⁻¹(x)", font=KOREAN_FONT, font_size=22),
            Text("(가) |x|≤1  →  4·h(x)² = x²(x²−5)²", font=KOREAN_FONT, font_size=20, color=GRAY_A),
            Text("(나) |x|>1  →  |h(x)| = e^{|x|−1} + 1", font=KOREAN_FONT, font_size=20, color=GRAY_A),
            Text(
                "기울기 m, 점 (1,0) 지나 y=m(x−1) 과 y=f(x) 교점 수 = g(m)",
                font=KOREAN_FONT,
                font_size=20,
            ),
            Text(
                "g(m)이 m=a, m=b (a<b)에서 불연속일 때 아래 값을 구하시오.",
                font=KOREAN_FONT,
                font_size=20,
            ),
            self._fit_width(
                MathTex(
                    r"g(a)\cdot\lim_{m\to a+}g(m)+g(b)\cdot\left(\frac{\ln b}{b}\right)^2",
                    font_size=32,
                ),
                11.0,
            ),
        ]
        group = VGroup(q_label, *lines).arrange(DOWN, buff=0.22)
        group.move_to(self._content_anchor())
        self.play(FadeIn(q_label), run_time=0.3)
        for line in lines:
            self.play(FadeIn(line, shift=DOWN * 0.08), run_time=0.35)
        self.wait(0.8)
        return group

    def run_solution(self, header: Mobject, question: Mobject) -> None:
        self.play(FadeOut(question, shift=DOWN * 0.2), run_time=0.45)
        last_step: Mobject | None = None
        for i, step in enumerate(self.problem.steps):
            if last_step is not None:
                self.play(FadeOut(last_step, shift=DOWN * 0.15), run_time=0.28)
            eq_size = 32 if len(step.latex) > 60 else 36
            last_step = self.show_step(i, step.narration, step.latex, eq_size=eq_size)
        if last_step is not None:
            self.play(FadeOut(last_step, shift=DOWN * 0.15), run_time=0.28)
        self.show_answer()

    def construct(self) -> None:
        header = self.show_header()
        question = self.show_question()
        self.run_solution(header, question)
