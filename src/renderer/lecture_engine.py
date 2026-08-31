"""YAML Lecture DSL → Manim 실행 엔진."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
from manim import *

from src.config import ANSWER_COLOR, KOREAN_FONT, HIGHLIGHT_COLOR, TITLE_COLOR
from src.dsl.lecture_models import (
    AnswerStep,
    ClearStep,
    FadeOutStep,
    GraphStep,
    HighlightStep,
    LatexBlockStep,
    LatexStep,
    LectureProblem,
    NarrateStep,
    NumberLineStep,
    ProblemCardStep,
    SectionStep,
    WaitStep,
)
from src.renderer.graph_helpers import make_graph_axes
from src.renderer.graph_presets import get_preset, resolve_color, tangent_at
from src.renderer.hansu_board import HansuPresenter, audio_duration


class LectureEngine:
    """공통 강의 Scene — YAML steps 순차 실행."""

    def __init__(self, scene: Scene, problem: LectureProblem, narration_dir: Path | None = None) -> None:
        self.scene = scene
        self.problem = problem
        self.narration_dir = narration_dir or (
            Path(__file__).resolve().parents[2] / "assets" / "narration" / problem.lecture.slug
        )
        self.presenter = HansuPresenter(scene, self.narration_dir)
        self._board: VGroup = VGroup()
        self._latex_stack: VGroup | None = None
        self._narration_index = 0
        self._header: Mobject | None = None
        self._graph_group: VGroup | None = None

    def run(self) -> None:
        spec = self.problem.lecture
        self.scene.camera.background_color = spec.background
        h = spec.header
        self._header = self.presenter.section_title(h.title, h.subtitle)

        for step in spec.steps:
            self._execute(step)

        self.presenter.clear_subtitle()

    def _execute(self, step) -> None:  # noqa: ANN001
        if isinstance(step, NarrateStep):
            self.presenter.speak(step.text, segment=self._narration_index)
            self._narration_index += 1
        elif isinstance(step, SectionStep):
            self.presenter.section_title(step.title, step.subtitle)
        elif isinstance(step, ProblemCardStep):
            self._show_problem()
        elif isinstance(step, LatexStep):
            self._show_latex(step)
        elif isinstance(step, LatexBlockStep):
            self._show_latex_block(step)
        elif isinstance(step, GraphStep):
            self._show_graph(step)
        elif isinstance(step, NumberLineStep):
            self._show_number_line(step)
        elif isinstance(step, AnswerStep):
            self._show_answer(step)
        elif isinstance(step, ClearStep):
            self._clear_board()
        elif isinstance(step, FadeOutStep):
            self._fade_out(step.target)
        elif isinstance(step, WaitStep):
            self.scene.wait(step.seconds)
        elif isinstance(step, HighlightStep):
            self._highlight_last(step.color)

    def _set_board(self, mob: Mobject) -> None:
        self._board = mob

    def _show_problem(self) -> None:
        p = self.problem
        prob = MathTex(
            p.question_latex,
            font_size=32,
        ).shift(UP * 0.3 + RIGHT * 0.5)
        parts: list[Mobject] = [prob]
        if p.question_note:
            note = MathTex(p.question_note, font_size=24, color=HIGHLIGHT_COLOR)
            note.next_to(prob, DOWN, buff=0.4)
            parts.append(note)
        if p.question_latex_2:
            q2 = MathTex(p.question_latex_2, font_size=28)
            q2.next_to(parts[-1], DOWN, buff=0.3)
            parts.append(q2)
        ask = Text("구함:  a×e^b", font=KOREAN_FONT, font_size=22, color=GRAY_A)
        ask.next_to(parts[-1], DOWN, buff=0.35)
        parts.append(ask)
        grp = VGroup(*parts)
        self.scene.play(Write(prob), run_time=1.2)
        for m in parts[1:]:
            self.scene.play(FadeIn(m), run_time=0.5)
        self.scene.wait(1.0)
        self._set_board(grp)

    def _show_latex(self, step: LatexStep) -> None:
        eq = MathTex(step.content, font_size=step.font_size, color=resolve_color(step.color))
        if step.stack and self._latex_stack is not None:
            eq.next_to(self._latex_stack, DOWN, buff=0.35, aligned_edge=LEFT)
            new_stack = VGroup(self._latex_stack, eq)
            self.scene.play(Write(eq), run_time=1.0)
            self._latex_stack = new_stack
            self._set_board(new_stack)
        else:
            eq.shift(RIGHT * 0.6)
            self.scene.play(Write(eq), run_time=1.2)
            self._latex_stack = eq
            self._set_board(eq)
        self.scene.wait(0.8)

    def _show_latex_block(self, step: LatexBlockStep) -> None:
        items = VGroup()
        for i, tex in enumerate(step.items):
            color = resolve_color(step.colors[i]) if i < len(step.colors) else WHITE
            items.add(MathTex(tex, font_size=step.font_size, color=color))
        items.arrange(DOWN, buff=0.35).shift(RIGHT * 0.5)
        self.scene.play(LaggedStart(*[FadeIn(m, shift=UP * 0.1) for m in items], lag_ratio=0.2), run_time=1.5)
        self.scene.wait(0.8)
        self._latex_stack = items
        self._set_board(items)

    def _show_graph(self, step: GraphStep) -> None:
        ax = step.axes
        axes = make_graph_axes(
            x_range=(ax.x_range[0], ax.x_range[1], ax.x_range[2] if len(ax.x_range) > 2 else 1),
            y_range=(ax.y_range[0], ax.y_range[1], ax.y_range[2] if len(ax.y_range) > 2 else 1),
            x_len=ax.x_len,
            y_len=ax.y_len,
        ).shift(RIGHT * step.shift[0] + UP * step.shift[1] + RIGHT * 0.8)

        grp: list[Mobject] = [axes]

        self.scene.play(Create(axes), run_time=0.7)

        for curve in step.curves:
            fn = get_preset(curve.preset)
            x0, x1 = (curve.x_plot or [ax.x_range[0], ax.x_range[1]])
            graph = axes.plot(fn, x_range=[x0, x1], color=resolve_color(curve.color), stroke_width=3)
            self.scene.play(Create(graph), run_time=1.5)
            grp.append(graph)
            if curve.label_latex:
                lbl = MathTex(curve.label_latex, font_size=22, color=resolve_color(curve.color))
                lbl.to_corner(UR).shift(DOWN * 0.75 + LEFT * 0.2)
                self.scene.play(FadeIn(lbl), run_time=0.4)
                grp.append(lbl)

        for dot in step.dots:
            if dot.preset_y:
                y = get_preset(dot.preset_y)(dot.x)
            elif dot.y is not None:
                y = dot.y
            else:
                y = 0.0
            d = Dot(axes.coords_to_point(dot.x, y), color=resolve_color(dot.color), radius=0.08)
            self.scene.play(GrowFromCenter(d), run_time=0.4)
            grp.append(d)
            if dot.label_latex:
                dl = MathTex(dot.label_latex, font_size=20, color=resolve_color(dot.color))
                dl.next_to(d, UP, buff=0.08)
                self.scene.play(FadeIn(dl), run_time=0.3)
                grp.append(dl)

        for tan in step.tangents:
            a, b = tangent_at(tan.preset_base, tan.at_x)
            x0, x1 = ax.x_range[0], ax.x_range[1]
            line = axes.plot(
                lambda x, aa=a, bb=b: aa * x + bb,
                x_range=[x0, x1],
                color=resolve_color(tan.color),
                stroke_width=2.5,
            )
            self.scene.play(Create(line), run_time=0.9)
            grp.append(line)

        self._graph_group = VGroup(*grp)
        self._set_board(self._graph_group)
        self.scene.wait(0.8)

    def _show_number_line(self, step: NumberLineStep) -> None:
        xr = step.x_range
        nl = NumberLine(
            x_range=[xr[0], xr[1], xr[2] if len(xr) > 2 else 1],
            length=9,
            include_numbers=True,
        ).shift(UP * 0.5 + RIGHT * 0.5)
        self.scene.play(Create(nl), run_time=0.7)
        marks: list[Mobject] = [nl]
        for m in step.markers:
            d = Dot(nl.n2p(m.x), color=resolve_color(m.color))
            self.scene.play(GrowFromCenter(d), run_time=0.35)
            marks.append(d)
            if m.label_latex:
                lbl = MathTex(m.label_latex, font_size=22, color=resolve_color(m.color))
                lbl.next_to(d, UP, buff=0.15)
                self.scene.play(FadeIn(lbl), run_time=0.3)
                marks.append(lbl)
        grp = VGroup(*marks)
        self._set_board(grp)
        self.scene.wait(0.8)

    def _show_answer(self, step: AnswerStep) -> None:
        ans = MathTex(step.latex, font_size=36, color=ANSWER_COLOR)
        box = SurroundingRectangle(ans, color=ANSWER_COLOR, buff=0.15, corner_radius=0.08)
        badge = Text(step.label, font=KOREAN_FONT, font_size=28, color=ANSWER_COLOR)
        grp = VGroup(VGroup(ans, box), badge).arrange(DOWN, buff=0.4).shift(RIGHT * 0.5)
        self.scene.play(Write(ans), Create(box), run_time=1.2)
        self.scene.play(FadeIn(badge), run_time=0.5)
        self.scene.wait(2.0)
        self._set_board(grp)

    def _clear_board(self) -> None:
        if len(self._board) > 0:
            self.scene.play(FadeOut(self._board), run_time=0.4)
        self._board = VGroup()
        self._latex_stack = None
        self._graph_group = None

    def _fade_out(self, target: str) -> None:
        if target == "all" and self._header:
            self.scene.play(FadeOut(self._board), FadeOut(self._header), run_time=0.4)
            self._header = None
        elif len(self._board) > 0:
            self.scene.play(FadeOut(self._board), run_time=0.4)
        self._board = VGroup()
        self._latex_stack = None

    def _highlight_last(self, color: str) -> None:
        if len(self._board) == 0:
            return
        rect = SurroundingRectangle(self._board, color=resolve_color(color), buff=0.08)
        self.scene.play(Create(rect), run_time=0.4)
        self._board = VGroup(self._board, rect)
