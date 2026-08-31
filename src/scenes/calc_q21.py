from __future__ import annotations

import math

from manim import *

from src.config import ANSWER_COLOR, KOREAN_FONT, TITLE_COLOR
from src.renderer.graph_helpers import caption_bar, korean_label, make_graph_axes
from src.renderer.q21_graphs import (
    lower_bound,
    plot_lower_bound,
    plot_middle_line,
    plot_upper_bound,
    upper_bound,
)


class Q21CubicInequalityScene(Scene):
    """삼차함수 부등식 — 2ax+b 가 두 곡선 사이에 끼는 그래프 해설."""

    def construct(self) -> None:
        header = VGroup(
            Text("삼차함수 부등식 21번", font=KOREAN_FONT, font_size=26, color=TITLE_COLOR),
            VGroup(
                MathTex(r"f(x)=x^3+ax^2+bx+c", font_size=22, color=GRAY_B),
                Text("최고차항 계수 1", font=KOREAN_FONT, font_size=20, color=GRAY_B),
            ).arrange(RIGHT, buff=0.2),
        ).arrange(DOWN, buff=0.08).to_edge(UP, buff=0.22)
        self.play(FadeIn(header), run_time=0.4)

        # ── 1) 부등식 세팅 ──
        cap = caption_bar("조건을 정리하면 2ax+b 가 두 곡선 사이에 갇힌다")
        self.play(FadeIn(cap), run_time=0.35)

        cond = VGroup(
            MathTex(
                r"\frac{f'(x)}{2}+x^2-2",
                r"\leq",
                r"\frac{f(2x)-f(0)}{2x}",
                r"\leq",
                r"x^4",
                font_size=28,
            ),
            MathTex(
                r"\Downarrow",
                font_size=32,
            ),
            MathTex(
                r"-3x^2-4",
                r"\leq",
                r"2ax+b",
                r"\leq",
                r"x^4-4x^2",
                font_size=32,
                color=YELLOW,
            ),
        ).arrange(DOWN, buff=0.35).shift(DOWN * 0.2)
        self.play(Write(cond[0]), run_time=0.9)
        self.play(FadeIn(cond[1]), Write(cond[2]), run_time=1.0)
        self.wait(0.6)
        self.play(FadeOut(cond), run_time=0.4)

        # ── 2) 두 경계 곡선 그리기 ──
        self.play(
            cap.animate.become(caption_bar("아래: y=−3x²−4  ·  위: y=x⁴−4x²")),
            run_time=0.35,
        )
        axes = make_graph_axes(
            x_range=(-2.6, 2.6, 1),
            y_range=(-6, 4, 2),
            x_len=7.5,
            y_len=4.0,
        ).shift(DOWN * 0.35)
        axes_labels = VGroup(
            MathTex("x", font_size=24).next_to(axes.x_axis, RIGHT, buff=0.1),
            MathTex("y", font_size=24).next_to(axes.y_axis, UP, buff=0.1),
        )

        upper = plot_upper_bound(axes, color=BLUE)
        lower = plot_lower_bound(axes, color=TEAL)
        upper_lbl = MathTex(r"y=x^4-4x^2", font_size=24, color=BLUE).to_corner(UR).shift(
            DOWN * 0.85 + LEFT * 0.2
        )
        lower_lbl = MathTex(r"y=-3x^2-4", font_size=24, color=TEAL).to_corner(UL).shift(
            DOWN * 0.85 + RIGHT * 0.2
        )

        self.play(Create(axes), Write(axes_labels), run_time=0.7)
        self.play(Create(lower), Create(upper), Write(lower_lbl), Write(upper_lbl), run_time=1.4)

        # 최솟값·최댓값 포인트
        sqrt2 = math.sqrt(2)
        min_pts = VGroup(
            Dot(axes.coords_to_point(sqrt2, upper_bound(sqrt2)), color=RED, radius=0.07),
            Dot(axes.coords_to_point(-sqrt2, upper_bound(-sqrt2)), color=RED, radius=0.07),
            Dot(axes.coords_to_point(0, lower_bound(0)), color=RED, radius=0.07),
        )
        min_note = korean_label("공통 최솟값 y = −4", 18, RED).next_to(axes, DOWN, buff=0.12)
        h_line = DashedLine(
            axes.coords_to_point(-2.5, -4),
            axes.coords_to_point(2.5, -4),
            color=RED,
            stroke_width=2,
        )
        self.play(
            LaggedStart(*[GrowFromCenter(d) for d in min_pts], lag_ratio=0.15),
            Create(h_line),
            FadeIn(min_note),
            run_time=0.9,
        )
        self.wait(0.7)

        # ── 3) 직선 2ax+b — 기울기 있는 경우는 안 됨 ──
        self.play(
            cap.animate.become(caption_bar("기울기 있는 직선?  →  ✕  (곡선을 벗어남)")),
            run_time=0.35,
        )
        bad_line = plot_middle_line(axes, a=1.5, b=-4, color=RED)
        bad_x = korean_label("✕", 36, RED).next_to(axes.coords_to_point(1.8, 0.5), UP, buff=0.05)
        self.play(Create(bad_line), FadeIn(bad_x), run_time=0.8)
        self.wait(0.6)
        self.play(FadeOut(bad_line), FadeOut(bad_x), run_time=0.35)

        # ── 4) y = −4 수평선만 가능 ──
        self.play(
            cap.animate.become(caption_bar("y = −4 수평선만 모든 x에서 성립")),
            run_time=0.35,
        )
        good_line = plot_middle_line(axes, a=0, b=-4, color=YELLOW)
        good_lbl = MathTex(r"2ax+b=-4 \Rightarrow a=0,\ b=-4", font_size=26, color=YELLOW)
        good_lbl.to_edge(RIGHT, buff=0.4).shift(UP * 0.5)
        self.play(Create(good_line), Write(good_lbl), run_time=1.0)
        self.wait(0.8)

        # ── 5) f'(10) 계산 ──
        self.play(
            cap.animate.become(caption_bar("f'(x)=3x²−4  →  f'(10)=296")),
            run_time=0.35,
        )
        answer = VGroup(
            MathTex(r"f'(x)=3x^2+2ax+b=3x^2-4", font_size=28),
            MathTex(r"f'(10)=3\cdot 10^2-4=296", font_size=32, color=ANSWER_COLOR),
            Text("정답  296", font=KOREAN_FONT, font_size=30, color=ANSWER_COLOR),
        ).arrange(DOWN, buff=0.22).to_edge(RIGHT, buff=0.35).shift(DOWN * 1.2)
        box = SurroundingRectangle(answer[-1], color=ANSWER_COLOR, buff=0.12)
        self.play(Write(answer[0]), run_time=0.6)
        self.play(Write(answer[1]), Write(answer[2]), Create(box), run_time=0.9)
        self.wait(1.5)
