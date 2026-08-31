from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from manim import *

from src.config import ANSWER_COLOR, KOREAN_FONT, TITLE_COLOR
from src.dsl.models import ExamSet, Problem, get_problem, load_exam
from src.pipeline.planner import (
    enrich_problem,
    env_problem_id,
    env_problem_path,
    env_timing_path,
    read_timing_manifest,
    step_duration,
)
from src.renderer.action_engine import ActionEngine
from src.renderer.layout import caption_bar, place_equation


@dataclass
class HansuSceneContext:
    scene: Scene
    problem: Problem
    exam: ExamSet
    manifest: dict = field(default_factory=dict)


GRAPH_ACTIONS = frozenset({
    "plot", "tangent_at", "plot_piecewise", "highlight_point", "vertical_line", "brace_y",
})


class HansuAutoScene(Scene):
    """YAML 기반 수학 한수 스타일 자동 Scene."""

    def construct(self) -> None:
        exam_path = env_problem_path()
        problem_id = env_problem_id()
        if exam_path is None or problem_id is None:
            self._demo_construct()
            return

        exam = load_exam(exam_path)
        problem = enrich_problem(get_problem(exam, problem_id))
        timing_path = env_timing_path()
        manifest = read_timing_manifest(timing_path) if timing_path else {}

        ctx = HansuSceneContext(scene=self, problem=problem, exam=exam, manifest=manifest)
        self._render(ctx)

    def _demo_construct(self) -> None:
        label = Text(
            "MATH_VIZ_EXAM_PATH / MATH_VIZ_PROBLEM_ID 환경변수 필요",
            font=KOREAN_FONT,
            font_size=28,
        )
        self.play(FadeIn(label))

    def _render(self, ctx: HansuSceneContext) -> None:
        problem = ctx.problem
        exam = ctx.exam
        config = problem.visual

        header = VGroup(
            Text(exam.brand, font=KOREAN_FONT, font_size=20, color=GRAY_B),
            Text(
                f"{exam.section} · {problem.id}번 · {problem.topic}",
                font=KOREAN_FONT,
                font_size=26,
                color=TITLE_COLOR,
            ),
        ).arrange(DOWN, buff=0.06).to_edge(UP, buff=0.22)
        self.play(FadeIn(header, shift=DOWN * 0.1), run_time=0.45)

        engine = ActionEngine(ctx)
        eq_mob: Mobject | None = None

        for i, step in enumerate(problem.steps):
            dur = step_duration(ctx.manifest, i)
            cap_text = step.caption or step.narration

            # 이전 step 요소 제거 (그래프·수식 겹침 방지)
            if i > 0:
                engine.clear_step_visuals()
            if eq_mob is not None:
                self.play(FadeOut(eq_mob), run_time=0.2)
                eq_mob = None

            engine.set_caption(cap_text)

            has_graph = any(a.action in GRAPH_ACTIONS for a in step.visual)
            has_eq_action = any(a.action == "show_equation" for a in step.visual)

            if step.visual and config:
                for action in step.visual:
                    if action.action == "show_equation":
                        continue
                    engine.execute(action, config)

            if not has_eq_action and step.latex.strip():
                latex = place_equation(MathTex(step.latex, font_size=30 if has_graph else 34, color=WHITE))
                eq_mob = latex
                self.play(Write(latex), run_time=min(0.85, dur * 0.35))
            elif not has_graph and step.latex.strip():
                latex = place_equation(MathTex(step.latex, font_size=34, color=WHITE))
                latex.move_to(ORIGIN).shift(DOWN * 0.2)
                eq_mob = latex
                self.play(Write(latex), run_time=min(0.85, dur * 0.35))

            self.wait(max(dur - 1.0, 0.6))

        if eq_mob is not None:
            self.play(FadeOut(eq_mob), run_time=0.2)
        engine.clear_step_visuals()
        if engine.caption:
            self.play(FadeOut(engine.caption), run_time=0.2)

        self._show_answer(problem)
        self.wait(1.2)

    def _show_answer(self, problem: Problem) -> None:
        box = RoundedRectangle(
            width=6.0,
            height=1.1,
            corner_radius=0.15,
            color=ANSWER_COLOR,
            fill_color=ANSWER_COLOR,
            fill_opacity=0.12,
            stroke_width=2,
        )
        label = Text("정답", font=KOREAN_FONT, font_size=32, color=ANSWER_COLOR)
        ans = Text(str(problem.answer), font=KOREAN_FONT, font_size=36, color=ANSWER_COLOR)
        group = VGroup(box, VGroup(label, ans).arrange(RIGHT, buff=0.35)).move_to(ORIGIN)
        self.play(FadeIn(group, scale=0.95), run_time=0.65)
