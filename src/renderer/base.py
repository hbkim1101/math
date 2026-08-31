from __future__ import annotations

from manim import *
from src.config import (
    ANSWER_COLOR,
    HIGHLIGHT_COLOR,
    KOREAN_FONT,
    STEP_COLOR,
    TITLE_COLOR,
)
from src.dsl.models import Problem

CONTENT_MAX_WIDTH = 12.5
NARRATION_MAX_WIDTH = 11.5


class SuneungBaseScene(Scene):
    """Shared helpers for 수능 problem visualization scenes."""

    problem: Problem
    exam_title: str = "2026학년도 수능 수학"

    def construct(self) -> None:
        raise NotImplementedError

    def _fit_width(self, mob: Mobject, max_width: float = CONTENT_MAX_WIDTH) -> Mobject:
        if mob.width > max_width:
            mob.scale(max_width / mob.width)
        return mob

    def _content_anchor(self) -> np.ndarray:
        return UP * 0.6

    def show_header(self) -> VGroup:
        badge = Text(
            f"제 {self.problem.id}문",
            font=KOREAN_FONT,
            font_size=34,
            color=TITLE_COLOR,
        )
        topic = Text(
            self.problem.topic,
            font=KOREAN_FONT,
            font_size=22,
            color=GRAY_B,
        )
        header = VGroup(badge, topic).arrange(DOWN, buff=0.12)
        header.to_edge(UP, buff=0.35)
        self.play(FadeIn(header, shift=DOWN * 0.15), run_time=0.5)
        return header

    def show_question(self) -> VGroup:
        q_label = Text("문제", font=KOREAN_FONT, font_size=28, color=STEP_COLOR)
        q_math = self._fit_width(MathTex(self.problem.question_latex.strip(), font_size=36))
        parts: list[Mobject] = [q_label, q_math]

        if self.problem.question_latex_2:
            if self.problem.question_note:
                note = Text(
                    self.problem.question_note,
                    font=KOREAN_FONT,
                    font_size=24,
                    color=GRAY_A,
                )
                self._fit_width(note, NARRATION_MAX_WIDTH)
                parts.append(note)
            q_math_2 = self._fit_width(
                MathTex(self.problem.question_latex_2.strip(), font_size=36)
            )
            parts.append(q_math_2)
        elif self.problem.question_note:
            note = Text(
                self.problem.question_note,
                font=KOREAN_FONT,
                font_size=24,
                color=GRAY_A,
            )
            self._fit_width(note, NARRATION_MAX_WIDTH)
            parts.append(note)

        choices = Text(
            "   ".join(self.problem.choices),
            font=KOREAN_FONT,
            font_size=20,
            color=GRAY_B,
        )
        self._fit_width(choices, NARRATION_MAX_WIDTH)
        parts.append(choices)

        group = VGroup(*parts).arrange(DOWN, buff=0.28)
        group.move_to(self._content_anchor())

        self.play(FadeIn(q_label, shift=DOWN * 0.15), run_time=0.35)
        self.play(Write(q_math), run_time=0.9)
        for part in parts[2:]:
            anim = FadeIn(part, shift=DOWN * 0.1) if isinstance(part, Text) else Write(part)
            self.play(anim, run_time=0.45)
        self.wait(0.7)
        return group

    def show_step(self, step_index: int, narration: str, latex: str) -> VGroup:
        step_num = Text(
            f"Step {step_index + 1}",
            font=KOREAN_FONT,
            font_size=22,
            color=HIGHLIGHT_COLOR,
        )
        narr = Text(narration, font=KOREAN_FONT, font_size=24, color=STEP_COLOR)
        self._fit_width(narr, NARRATION_MAX_WIDTH)
        eq = self._fit_width(MathTex(latex, font_size=38))
        group = VGroup(step_num, narr, eq).arrange(DOWN, buff=0.25)
        group.move_to(self._content_anchor())
        self.play(FadeIn(step_num, shift=RIGHT * 0.15), run_time=0.25)
        self.play(FadeIn(narr, shift=DOWN * 0.1), run_time=0.6)
        self.play(Write(eq), run_time=0.9)
        self.wait(0.8)
        return group

    def show_answer(self) -> None:
        box = RoundedRectangle(
            width=5.2,
            height=1.0,
            corner_radius=0.15,
            color=ANSWER_COLOR,
            fill_color=ANSWER_COLOR,
            fill_opacity=0.15,
            stroke_width=2,
        )
        label = Text("정답", font=KOREAN_FONT, font_size=30, color=ANSWER_COLOR)
        ans = Text(self.problem.answer, font=KOREAN_FONT, font_size=34, color=ANSWER_COLOR)
        answer_text = VGroup(label, ans).arrange(RIGHT, buff=0.35)
        answer_text.move_to(box.get_center())
        group = VGroup(box, answer_text).move_to(DOWN * 2.6)
        self.play(FadeIn(group, shift=UP * 0.15), run_time=0.7)
        self.wait(1.2)

    def run_solution(self, header: Mobject, question: Mobject) -> None:
        self.play(FadeOut(question, shift=DOWN * 0.2), run_time=0.45)

        last_step: Mobject | None = None
        for i, step in enumerate(self.problem.steps):
            if last_step is not None:
                self.play(FadeOut(last_step, shift=DOWN * 0.15), run_time=0.3)
            last_step = self.show_step(i, step.narration, step.latex)

        if last_step is not None:
            self.play(FadeOut(last_step, shift=DOWN * 0.15), run_time=0.3)
        self.show_answer()
