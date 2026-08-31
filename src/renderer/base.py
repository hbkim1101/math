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


class SuneungBaseScene(Scene):
    """Shared helpers for 수능 problem visualization scenes."""

    problem: Problem
    exam_title: str = "2026학년도 수능 수학"

    def construct(self) -> None:
        raise NotImplementedError

    def show_header(self) -> VGroup:
        badge = Text(
            f"제 {self.problem.id}문",
            font=KOREAN_FONT,
            font_size=36,
            color=TITLE_COLOR,
        )
        topic = Text(
            self.problem.topic,
            font=KOREAN_FONT,
            font_size=24,
            color=GRAY_B,
        )
        header = VGroup(badge, topic).arrange(DOWN, buff=0.15).to_edge(UP, buff=0.4)
        self.play(FadeIn(header, shift=DOWN * 0.2), run_time=0.6)
        return header

    def show_question(self) -> VGroup:
        q_label = Text("문제", font=KOREAN_FONT, font_size=28, color=STEP_COLOR)
        q_math = MathTex(
            self.problem.question_latex.strip(),
            font_size=40,
            color=WHITE,
        )
        parts: list[Mobject] = [q_label, q_math]

        if self.problem.question_note and not self.problem.question_latex_2:
            note = Text(
                self.problem.question_note,
                font=KOREAN_FONT,
                font_size=26,
                color=GRAY_A,
            )
            parts.append(note)
        elif self.problem.question_latex_2:
            if self.problem.question_note:
                note = Text(
                    self.problem.question_note,
                    font=KOREAN_FONT,
                    font_size=26,
                    color=GRAY_A,
                )
                parts.append(note)
            q_math_2 = MathTex(
                self.problem.question_latex_2.strip(),
                font_size=40,
                color=WHITE,
            )
            parts.append(q_math_2)
        elif self.problem.question_note:
            note = Text(
                self.problem.question_note,
                font=KOREAN_FONT,
                font_size=26,
                color=GRAY_A,
            )
            parts.append(note)

        choices = Text(
            "   ".join(self.problem.choices),
            font=KOREAN_FONT,
            font_size=22,
            color=GRAY_B,
        )
        parts.append(choices)
        group = VGroup(*parts).arrange(DOWN, buff=0.35).move_to(ORIGIN)
        self.play(Write(q_label), run_time=0.4)
        self.play(Write(q_math), run_time=1.0)
        for part in parts[2:-1]:
            self.play(FadeIn(part) if isinstance(part, Text) else Write(part), run_time=0.5)
        self.play(FadeIn(choices), run_time=0.5)
        self.wait(0.8)
        return group

    def show_step(self, step_index: int, narration: str, latex: str) -> VGroup:
        step_num = Text(
            f"Step {step_index + 1}",
            font=KOREAN_FONT,
            font_size=24,
            color=HIGHLIGHT_COLOR,
        )
        narr = Text(narration, font=KOREAN_FONT, font_size=26, color=STEP_COLOR)
        eq = MathTex(latex, font_size=44, color=WHITE)
        group = VGroup(step_num, narr, eq).arrange(DOWN, buff=0.3)
        group.move_to(ORIGIN)
        self.play(FadeIn(step_num, shift=RIGHT * 0.2), run_time=0.3)
        self.play(Write(narr), run_time=0.8)
        self.play(Write(eq), run_time=1.0)
        self.wait(1.0)
        return group

    def show_answer(self) -> None:
        box = RoundedRectangle(
            width=5.5,
            height=1.2,
            corner_radius=0.15,
            color=ANSWER_COLOR,
            fill_color=ANSWER_COLOR,
            fill_opacity=0.15,
            stroke_width=2,
        )
        label = Text("정답", font=KOREAN_FONT, font_size=32, color=ANSWER_COLOR)
        ans = Text(self.problem.answer, font=KOREAN_FONT, font_size=36, color=ANSWER_COLOR)
        group = VGroup(box, VGroup(label, ans).arrange(RIGHT, buff=0.4)).move_to(DOWN * 2.5)
        self.play(Create(box), FadeIn(VGroup(label, ans)), run_time=0.8)
        self.wait(1.5)

    def run_solution(self, header: Mobject) -> None:
        for i, step in enumerate(self.problem.steps):
            self.play(
                FadeOut(header, shift=UP * 0.3),
                run_time=0.4,
            )
            step_group = self.show_step(i, step.narration, step.latex)
            self.play(FadeOut(step_group), run_time=0.4)
            header = self.show_header()
        self.show_answer()
