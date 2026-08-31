from __future__ import annotations

import math
from pathlib import Path

from manim import *

from src.config import ANSWER_COLOR, HIGHLIGHT_COLOR, KOREAN_FONT, TITLE_COLOR
from src.dsl.models import get_problem, load_exam
from src.pipeline.planner import env_problem_id, env_problem_path
from src.renderer.graph_helpers import make_graph_axes
from src.renderer.layout import caption_bar, place_equation, place_graph_group
from src.scenes.lecture_base import LectureMixin


def curve1(x: float, k: float = 8.0) -> float:
    return 2**x + k / 2


def curve2(x: float, k: float = 8.0) -> float:
    return k / (2**x) + k - 2


def curve3(x: float) -> float:
    return 2 ** (x - 2) - 3


def point_a(k: float = 8.0) -> tuple[float, float]:
    return math.log2(k) - 1, k


def point_b(k: float = 8.0) -> tuple[float, float]:
    ax, _ = point_a(k)
    return ax + 3, k - 3


DEFAULT_EXAM = (
    Path(__file__).resolve().parents[2] / "problems" / "2026_suneung" / "q22.yaml"
)


class Q22LectureScene(LectureMixin, Scene):
    """2026 수능 22번 — TTS 동기화 풀 풀이 강의."""

    def construct(self) -> None:
        self.init_lecture_timing()
        exam_path = env_problem_path() or DEFAULT_EXAM
        pid = env_problem_id() or 22
        exam = load_exam(exam_path)
        problem = get_problem(exam, pid)
        steps = problem.steps
        k = 8.0
        ax, ay = point_a(k)
        bx, by = point_b(k)

        header = self.show_header(exam.brand, f"{exam.section} {problem.id}번 · {problem.topic}")
        cap: Text | None = None
        eq: Mobject | None = None
        graph_layer = VGroup()

        # ── INTRO ──
        cap = self.show_caption(cap, "강의를 시작합니다")
        self.wait_segment("intro", anim_time=0.75)

        # ── STEP 0: 문제 소개 + 그래프 ──
        cap = self.show_caption(cap, steps[0].caption or "")
        axes = make_graph_axes(x_range=(-1, 6, 1), y_range=(-2, 12, 2), x_len=6.0, y_len=3.6)
        g1 = axes.plot(lambda x: curve1(x, k), x_range=[-0.5, 4.5], color=BLUE, stroke_width=3)
        g2 = axes.plot(lambda x: curve2(x, k), x_range=[-0.5, 4.5], color=TEAL, stroke_width=3)
        graph_layer = place_graph_group(VGroup(axes, g1, g2))
        self.play(Create(axes), run_time=0.5)
        self.play(Create(g1), Create(g2), run_time=0.9)
        if eq:
            self.play(FadeOut(eq), run_time=0.15)
        eq = place_equation(MathTex(steps[0].latex, font_size=26))
        self.play(Write(eq), run_time=0.7)
        self.wait_segment("step", 0, anim_time=2.1)

        # ── STEP 1: t=2^x 치환 ──
        cap = self.show_caption(cap, steps[1].caption or "")
        self.play(FadeOut(eq), run_time=0.15)
        eq = self.show_equations([steps[1].latex], font_size=26)
        self.wait_segment("step", 1, anim_time=1.0)

        # ── STEP 2: 2t 곱 ──
        cap = self.show_caption(cap, steps[2].caption or "")
        self.play(FadeOut(eq), run_time=0.15)
        eq = self.show_equations(
            [r"t+\frac{k}{2}=\frac{k}{t}+k-2", r"\times 2t", steps[2].latex],
            font_size=24,
            stagger=0.45,
        )
        self.wait_segment("step", 2, anim_time=1.5)

        # ── STEP 3: 인수분해 ──
        cap = self.show_caption(cap, steps[3].caption or "")
        self.play(FadeOut(eq), run_time=0.15)
        eq = self.show_equations([steps[3].latex, r"2^x=\frac{k}{2}"], font_size=26)
        self.wait_segment("step", 3, anim_time=1.0)

        # ── STEP 4: A 좌표 ──
        cap = self.show_caption(cap, steps[4].caption or "")
        dot_a = Dot(axes.coords_to_point(ax, ay), color=YELLOW, radius=0.09)
        la = MathTex("A", font_size=24, color=YELLOW).next_to(dot_a, UL, buff=0.06)
        self.play(GrowFromCenter(dot_a), Write(la), run_time=0.6)
        graph_layer.add(dot_a, la)
        self.play(FadeOut(eq), run_time=0.15)
        eq = place_equation(MathTex(steps[4].latex, font_size=28, color=HIGHLIGHT_COLOR))
        self.play(Write(eq), run_time=0.6)
        self.wait_segment("step", 4, anim_time=1.3)

        # ── STEP 5: 직선 ──
        cap = self.show_caption(cap, steps[5].caption or "")
        line = axes.plot(lambda x: (k + math.log2(k) - 1) - x, x_range=[ax - 0.5, bx + 0.5], color=YELLOW, stroke_width=2.5)
        self.play(Create(line), run_time=0.7)
        graph_layer.add(line)
        self.play(FadeOut(eq), run_time=0.15)
        eq = place_equation(MathTex(steps[5].latex, font_size=24))
        self.play(Write(eq), run_time=0.6)
        self.wait_segment("step", 5, anim_time=1.4)

        # ── STEP 6: B 좌표 ──
        cap = self.show_caption(cap, steps[6].caption or "")
        g3 = axes.plot(curve3, x_range=[-0.5, 5.5], color=ORANGE, stroke_width=2.5)
        dot_b = Dot(axes.coords_to_point(bx, by), color=RED, radius=0.09)
        lb = MathTex("B", font_size=24, color=RED).next_to(dot_b, UR, buff=0.06)
        self.play(Create(g3), GrowFromCenter(dot_b), Write(lb), run_time=0.8)
        graph_layer.add(g3, dot_b, lb)
        self.play(FadeOut(eq), run_time=0.15)
        eq = place_equation(MathTex(steps[6].latex, font_size=24))
        self.play(Write(eq), run_time=0.6)
        self.wait_segment("step", 6, anim_time=1.5)

        # ── STEP 7: AB 거리 ──
        cap = self.show_caption(cap, steps[7].caption or "")
        seg = Line(axes.coords_to_point(ax, ay), axes.coords_to_point(bx, by), color=GREEN, stroke_width=3)
        self.play(Create(seg), run_time=0.6)
        graph_layer.add(seg)
        self.play(FadeOut(eq), run_time=0.15)
        eq = place_equation(MathTex(steps[7].latex, font_size=28, color=GREEN))
        self.play(Write(eq), run_time=0.6)
        self.wait_segment("step", 7, anim_time=1.3)

        # ── STEP 8: 넓이 → h ──
        cap = self.show_caption(cap, steps[8].caption or "")
        tri = Polygon(
            axes.coords_to_point(0, 0),
            axes.coords_to_point(ax, ay),
            axes.coords_to_point(bx, by),
            color=HIGHLIGHT_COLOR,
            fill_opacity=0.12,
            stroke_width=2,
        )
        o_dot = Dot(axes.coords_to_point(0, 0), color=WHITE, radius=0.07)
        lo = MathTex("O", font_size=22).next_to(o_dot, DL, buff=0.05)
        self.play(FadeIn(tri), FadeIn(o_dot), Write(lo), run_time=0.7)
        graph_layer.add(tri, o_dot, lo)
        self.play(FadeOut(eq), run_time=0.15)
        eq = place_equation(MathTex(steps[8].latex, font_size=24))
        self.play(Write(eq), run_time=0.6)
        self.wait_segment("step", 8, anim_time=1.4)

        # ── STEP 9: 거리 공식 ──
        cap = self.show_caption(cap, steps[9].caption or "")
        self.play(FadeOut(eq), run_time=0.15)
        eq = self.show_equations(
            [r"x+y-(k+\log_2 k-1)=0", steps[9].latex],
            font_size=24,
        )
        self.wait_segment("step", 9, anim_time=1.0)

        # ── STEP 10: 정답 ──
        cap = self.show_caption(cap, steps[10].caption or "")
        self.play(FadeOut(eq), FadeOut(graph_layer), run_time=0.4)
        result = place_equation(MathTex(steps[10].latex, font_size=30, color=ANSWER_COLOR))
        box = SurroundingRectangle(result, color=ANSWER_COLOR, buff=0.15)
        self.play(Write(result), Create(box), run_time=0.8)
        self.wait_segment("step", 10, anim_time=1.0)

        # ── OUTRO ──
        cap = self.show_caption(cap, f"정답 {problem.answer}")
        self.show_answer_box(problem.answer)
        self.wait_segment("outro", anim_time=0.7)