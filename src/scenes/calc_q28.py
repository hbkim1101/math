from __future__ import annotations

from manim import *

from src.config import ANSWER_COLOR, KOREAN_FONT, TITLE_COLOR
from src.renderer.graph_helpers import caption_bar, korean_label, make_graph_axes
from src.renderer.q28_graphs import (
    PI,
    f_cubic_derivative_at_zero,
    f_cubic_increasing,
    plot_asymptote_lines,
    plot_h_composite_branches,
    schematic_g_decreasing,
    schematic_g_increasing,
)


class Q28SeptMockScene(Scene):
    """2026 9월 평가원 미적분 28번 — 수학 한수 스타일 그래프 해설."""

    def construct(self) -> None:
        header = VGroup(
            Text("2026 9월 평가원 · 미적분 28번", font=KOREAN_FONT, font_size=26, color=TITLE_COLOR),
            Text("f(x) = g(x) − tan g(x)", font=KOREAN_FONT, font_size=20, color=GRAY_B),
        ).arrange(DOWN, buff=0.08).to_edge(UP, buff=0.22)
        self.play(FadeIn(header), run_time=0.4)

        # ── 1) 합성함수 직관: h(t)=t−tan t ──
        cap = caption_bar("겉함수 h(t)=t−tan t 를 먼저 그립니다")
        self.play(FadeIn(cap), run_time=0.35)

        axes = make_graph_axes(
            x_range=(-PI, 3 * PI, PI / 2),
            y_range=(-4, 4, 2),
            x_len=7.5,
            y_len=3.8,
        ).shift(DOWN * 0.35)
        axes_labels = VGroup(
            MathTex("t", font_size=24).next_to(axes.x_axis, RIGHT, buff=0.12),
            MathTex("h(t)", font_size=24).next_to(axes.y_axis, UP, buff=0.12),
        )
        h_label = MathTex(r"h(t)=t-\tan t", font_size=28, color=BLUE).next_to(axes, UP, buff=0.12)

        asym_lines = plot_asymptote_lines(axes, (-PI, 3 * PI))
        h_graph = plot_h_composite_branches(axes, (-PI, 3 * PI), BLUE)

        deriv_note = korean_label("h′(t)=−tan²t ≤ 0  →  구간마다 감소", 18, GRAY_A)
        deriv_note.next_to(axes, DOWN, buff=0.15)

        self.play(Create(axes), Write(axes_labels), Write(h_label), run_time=0.7)
        self.play(Create(asym_lines), run_time=0.5)
        self.play(LaggedStart(*[Create(g) for g in h_graph], lag_ratio=0.15), run_time=1.8)
        self.play(FadeIn(deriv_note), run_time=0.4)

        origin = Dot(axes.coords_to_point(0, 0), color=YELLOW, radius=0.07)
        pi_point = Dot(axes.coords_to_point(PI, PI), color=YELLOW, radius=0.07)
        self.play(GrowFromCenter(origin), GrowFromCenter(pi_point), run_time=0.5)
        self.wait(0.6)

        # ── 2) 항등식 = 합성 ──
        self.play(
            FadeOut(h_graph),
            FadeOut(asym_lines),
            FadeOut(origin),
            FadeOut(pi_point),
            FadeOut(deriv_note),
            cap.animate.become(caption_bar("f(x)=h(g(x))  —  g의 그래프 모양이 f를 결정")),
            run_time=0.5,
        )
        composite = VGroup(
            MathTex(r"f(x)", font_size=32),
            MathTex(r"=", font_size=32),
            MathTex(r"g(x)", font_size=32, color=TEAL),
            MathTex(r"-", font_size=32),
            MathTex(r"\tan g(x)", font_size=32, color=TEAL),
            MathTex(r"=", font_size=32),
            MathTex(r"h\bigl(g(x)\bigr)", font_size=32, color=BLUE),
        ).arrange(RIGHT, buff=0.15).move_to(axes.get_center())
        self.play(Write(composite), run_time=1.0)
        self.wait(0.7)
        self.play(FadeOut(composite), run_time=0.35)

        # ── 3) g(x) 감소 개형 → 모순 ──
        self.play(
            cap.animate.become(caption_bar("감소 개형?  f(0)=0 과 모순 → ✕")),
            run_time=0.35,
        )
        g_dec = schematic_g_decreasing(axes)
        g_dec_label = korean_label("y=g(x) 감소", 20, RED).to_corner(UL).shift(DOWN * 0.8 + RIGHT * 0.3)
        self.play(Create(g_dec[0]), FadeIn(g_dec_label), run_time=1.0)
        self.play(GrowFromCenter(g_dec[1]), run_time=0.5)
        self.wait(0.7)
        self.play(FadeOut(g_dec), FadeOut(g_dec_label), run_time=0.4)

        # ── 4) g(x) 증가 개형 + 조건 (가)(나) ──
        self.play(cap.animate.become(caption_bar("증가 개형 + (가)(나) → π, 2π, 3π/2")), run_time=0.35)
        g_inc = schematic_g_increasing(axes)
        marks = VGroup(
            Dot(axes.coords_to_point(0, 0), color=YELLOW, radius=0.07),
            Dot(axes.coords_to_point(PI, PI), color=YELLOW, radius=0.07),
            MathTex("(0,0)", font_size=20, color=YELLOW).next_to(axes.coords_to_point(0, 0), DL, buff=0.06),
            MathTex(r"(\pi,\pi)", font_size=20, color=YELLOW).next_to(axes.coords_to_point(PI, PI), UR, buff=0.06),
        )
        self.play(Create(g_inc), run_time=1.2)
        self.play(LaggedStart(*[GrowFromCenter(m) for m in marks], lag_ratio=0.12), run_time=0.7)
        cond = korean_label("sin g(π)=0,  lim g(x)=3π/2", 18, GRAY_A).next_to(axes, DOWN, buff=0.12)
        self.play(FadeIn(cond), run_time=0.4)
        self.wait(0.8)
        self.play(FadeOut(g_inc), FadeOut(marks), FadeOut(cond), run_time=0.4)

        # ── 5) f(x) 개형 확정 ──
        self.play(cap.animate.become(caption_bar("f(x)=kx(x−π)(x−2π)  (양수 k)")), run_time=0.35)
        f_graph = axes.plot(
            lambda x: f_cubic_increasing(x),
            x_range=[-0.3, 2.8],
            color=GREEN,
            stroke_width=3,
        )
        f_formula = MathTex(r"f(x)=kx(x-\pi)(x-2\pi)", font_size=30, color=GREEN).next_to(axes, UP, buff=0.1)
        roots = VGroup(
            Dot(axes.coords_to_point(0, 0), color=GREEN, radius=0.07),
            Dot(axes.coords_to_point(PI, 0), color=GREEN, radius=0.07),
            Dot(axes.coords_to_point(2 * PI, 0), color=GREEN, radius=0.07),
        )
        self.play(Write(f_formula), Create(f_graph), run_time=1.2)
        self.play(LaggedStart(*[GrowFromCenter(d) for d in roots], lag_ratio=0.1), run_time=0.6)
        self.wait(0.6)

        # ── 6) 미분 → 정답 ──
        self.play(
            cap.animate.become(caption_bar("항등식 미분 → g′(0)·(g(0))² = −f′(0) = −6")),
            run_time=0.4,
        )
        fp0 = f_cubic_derivative_at_zero()
        calc = VGroup(
            MathTex(r"f'(0)=2k\pi^2=6", font_size=28),
            MathTex(r"g'(0)\times(g(0))^2 = -f'(0) = -6", font_size=32, color=ANSWER_COLOR),
            Text("정답  ②  −6", font=KOREAN_FONT, font_size=30, color=ANSWER_COLOR),
        ).arrange(DOWN, buff=0.25).to_edge(RIGHT, buff=0.45).shift(DOWN * 0.3)
        box = SurroundingRectangle(calc[-1], color=ANSWER_COLOR, buff=0.12)
        self.play(Write(calc[0]), run_time=0.6)
        self.play(Write(calc[1]), Write(calc[2]), Create(box), run_time=0.9)
        self.wait(1.5)
