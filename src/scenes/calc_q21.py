from __future__ import annotations

import math

from manim import *

from src.config import ANSWER_COLOR, KOREAN_FONT, HIGHLIGHT_COLOR, TITLE_COLOR
from src.renderer.graph_helpers import caption_bar, korean_label, make_graph_axes
from src.renderer.q21_graphs import (
    lower_bound,
    plot_lower_bound,
    plot_middle_line,
    plot_upper_bound,
    upper_bound,
)

CONTENT_WIDTH = 12.0


class Q21CubicInequalityScene(Scene):
    """삼차함수 부등식 21번 — 손풀이 전체 (대수 전개 + 그래프)."""

    def construct(self) -> None:
        header = VGroup(
            Text("삼차함수 부등식 21번", font=KOREAN_FONT, font_size=26, color=TITLE_COLOR),
            VGroup(
                MathTex(r"f(x)=x^3+ax^2+bx+c", font_size=22, color=GRAY_B),
                Text("최고차항 계수 1", font=KOREAN_FONT, font_size=20, color=GRAY_B),
            ).arrange(RIGHT, buff=0.2),
        ).arrange(DOWN, buff=0.08).to_edge(UP, buff=0.22)
        self.play(FadeIn(header), run_time=0.4)

        cap = caption_bar("0이 아닌 모든 실수 x에 대해 성립")
        self.play(FadeIn(cap), run_time=0.3)

        algebra: Mobject | None = None

        def show_algebra(lines: VGroup, new_cap: str | None = None) -> None:
            nonlocal algebra
            if new_cap:
                self.play(cap.animate.become(caption_bar(new_cap)), run_time=0.3)
            if algebra is not None:
                self.play(FadeOut(algebra), run_time=0.25)
            algebra = lines
            self.play(FadeIn(algebra), run_time=0.45)

        def fit(mob: Mobject) -> Mobject:
            if mob.width > CONTENT_WIDTH:
                mob.scale(CONTENT_WIDTH / mob.width)
            return mob

        # ── 1) 문제 조건 ──
        problem = fit(
            VGroup(
                MathTex(
                    r"\frac{f'(x)}{2}+x^2-2",
                    r"\leq",
                    r"\frac{f(2x)-f(0)}{2x}",
                    r"\leq",
                    r"x^4",
                    font_size=30,
                ),
                Text("구함:  f'(10)", font=KOREAN_FONT, font_size=24, color=HIGHLIGHT_COLOR),
            ).arrange(DOWN, buff=0.35)
        ).shift(DOWN * 0.15)
        show_algebra(problem)
        self.wait(0.8)

        # ── 2) f(x) 설정 ──
        step_f = fit(
            VGroup(
                MathTex(r"f(x)=x^3+ax^2+bx+c", font_size=28),
                MathTex(r"f'(x)=3x^2+2ax+b", font_size=28, color=YELLOW),
                MathTex(r"f(0)=c", font_size=26, color=GRAY_A),
            ).arrange(DOWN, buff=0.28, aligned_edge=LEFT)
        ).shift(DOWN * 0.1)
        show_algebra(step_f, "삼차함수 f(x)를 미정계수로 둔다")
        self.wait(0.7)

        # ── 3) 좌변 전개 ──
        step_left = fit(
            VGroup(
                MathTex(
                    r"\frac{f'(x)}{2}+x^2-2",
                    r"=",
                    r"\frac{3x^2+2ax+b}{2}+x^2-2",
                    font_size=26,
                ),
                MathTex(
                    r"=",
                    r"\frac{3}{2}x^2+ax+\frac{b}{2}+x^2-2",
                    font_size=26,
                ),
                MathTex(
                    r"=",
                    r"\frac{5}{2}x^2+ax+\frac{b}{2}-2",
                    font_size=28,
                    color=YELLOW,
                ),
            ).arrange(DOWN, buff=0.22, aligned_edge=LEFT)
        ).shift(DOWN * 0.05)
        show_algebra(step_left, "좌변  f'(x)/2 + x² − 2  전개")
        self.wait(0.9)

        # ── 4) 가운데 항 전개 ──
        step_mid = fit(
            VGroup(
                MathTex(
                    r"\frac{f(2x)-f(0)}{2x}",
                    r"=",
                    r"\frac{8x^3+4ax^2+2bx+c-c}{2x}",
                    font_size=26,
                ),
                MathTex(
                    r"=",
                    r"\frac{8x^3+4ax^2+2bx}{2x}",
                    font_size=26,
                ),
                MathTex(
                    r"=",
                    r"4x^2+2ax+b",
                    font_size=28,
                    color=YELLOW,
                ),
            ).arrange(DOWN, buff=0.22, aligned_edge=LEFT)
        ).shift(DOWN * 0.05)
        show_algebra(step_mid, "가운데 항  (f(2x)−f(0))/(2x)  전개")
        self.wait(0.9)

        # ── 5) 부등식 대입 ──
        step_ineq = fit(
            VGroup(
                MathTex(
                    r"\frac{5}{2}x^2+ax+\frac{b}{2}-2",
                    r"\leq",
                    r"4x^2+2ax+b",
                    r"\leq",
                    r"x^4",
                    font_size=26,
                ),
            )
        ).shift(DOWN * 0.15)
        show_algebra(step_ineq, "세 식을 부등식에 대입")
        self.wait(0.8)

        # ── 6) 좌측 부등식 정리 ──
        step_left_ineq = fit(
            VGroup(
                MathTex(
                    r"\frac{5}{2}x^2+ax+\frac{b}{2}-2",
                    r"\leq",
                    r"4x^2+2ax+b",
                    font_size=24,
                ),
                MathTex(r"\Downarrow", font_size=28),
                MathTex(
                    r"-\frac{3}{2}x^2-ax-\frac{b}{2}-2",
                    r"\leq",
                    r"0",
                    font_size=24,
                ),
                MathTex(r"\Downarrow", font_size=28),
                MathTex(
                    r"2ax+b",
                    r"\geq",
                    r"-3x^2-4",
                    font_size=28,
                    color=YELLOW,
                ),
            ).arrange(DOWN, buff=0.18)
        ).shift(DOWN * 0.05)
        show_algebra(step_left_ineq, "왼쪽 부등식 정리 (양변에 −4x², −2ax, −b/2)")
        self.wait(1.0)

        # ── 7) 우측 부등식 정리 ──
        step_right_ineq = fit(
            VGroup(
                MathTex(
                    r"4x^2+2ax+b",
                    r"\leq",
                    r"x^4",
                    font_size=26,
                ),
                MathTex(r"\Downarrow", font_size=28),
                MathTex(
                    r"2ax+b",
                    r"\leq",
                    r"x^4-4x^2",
                    font_size=28,
                    color=YELLOW,
                ),
            ).arrange(DOWN, buff=0.22)
        ).shift(DOWN * 0.15)
        show_algebra(step_right_ineq, "오른쪽 부등식 정리")
        self.wait(0.8)

        # ── 8) 최종 부등식 ──
        step_final = fit(
            VGroup(
                MathTex(
                    r"-3x^2-4",
                    r"\leq",
                    r"2ax+b",
                    r"\leq",
                    r"x^4-4x^2",
                    font_size=32,
                    color=YELLOW,
                ),
                Text(
                    "→  직선 y=2ax+b 가 두 곡선 사이에 갇힌다",
                    font=KOREAN_FONT,
                    font_size=22,
                    color=GRAY_A,
                ),
            ).arrange(DOWN, buff=0.35)
        ).shift(DOWN * 0.1)
        show_algebra(step_final, "모든 x에서 성립하려면…")
        self.wait(1.0)

        # ── 9) 그래프 파트 ──
        if algebra is not None:
            self.play(FadeOut(algebra), run_time=0.3)
            algebra = None

        self.play(
            cap.animate.become(caption_bar("아래: y=−3x²−4  ·  위: y=x⁴−4x²")),
            run_time=0.35,
        )

        axes = make_graph_axes(
            x_range=(-2.6, 2.6, 1),
            y_range=(-6, 4, 2),
            x_len=7.5,
            y_len=3.6,
        ).shift(DOWN * 0.45)
        axes_labels = VGroup(
            MathTex("x", font_size=24).next_to(axes.x_axis, RIGHT, buff=0.1),
            MathTex("y", font_size=24).next_to(axes.y_axis, UP, buff=0.1),
        )

        upper = plot_upper_bound(axes, color=BLUE)
        lower = plot_lower_bound(axes, color=TEAL)
        upper_lbl = MathTex(r"y=x^4-4x^2", font_size=22, color=BLUE).to_corner(UR).shift(
            DOWN * 0.85 + LEFT * 0.2
        )
        lower_lbl = MathTex(r"y=-3x^2-4", font_size=22, color=TEAL).to_corner(UL).shift(
            DOWN * 0.85 + RIGHT * 0.2
        )

        graph_group = VGroup(axes, axes_labels, upper, lower, upper_lbl, lower_lbl)
        self.play(Create(axes), Write(axes_labels), run_time=0.7)
        self.play(Create(lower), Create(upper), Write(lower_lbl), Write(upper_lbl), run_time=1.2)

        sqrt2 = math.sqrt(2)
        min_pts = VGroup(
            Dot(axes.coords_to_point(sqrt2, upper_bound(sqrt2)), color=RED, radius=0.07),
            Dot(axes.coords_to_point(-sqrt2, upper_bound(-sqrt2)), color=RED, radius=0.07),
            Dot(axes.coords_to_point(0, lower_bound(0)), color=RED, radius=0.07),
        )
        min_note = korean_label("공통 값 y = −4", 18, RED).next_to(axes, DOWN, buff=0.08)
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
        self.wait(0.6)

        # 기울기 있는 직선 ✕
        self.play(
            cap.animate.become(caption_bar("기울기 있는 직선은 곡선을 벗어남 → ✕")),
            run_time=0.35,
        )
        bad_line = plot_middle_line(axes, a=1.5, b=-4, color=RED)
        bad_x = korean_label("✕", 36, RED).next_to(axes.coords_to_point(1.8, 0.5), UP, buff=0.05)
        self.play(Create(bad_line), FadeIn(bad_x), run_time=0.7)
        self.wait(0.5)
        self.play(FadeOut(bad_line), FadeOut(bad_x), run_time=0.3)

        # y = −4
        self.play(
            cap.animate.become(caption_bar("y = −4 수평선만 모든 x에서 성립")),
            run_time=0.35,
        )
        good_line = plot_middle_line(axes, a=0, b=-4, color=YELLOW)
        good_lbl = MathTex(r"2ax+b=-4 \Rightarrow a=0,\ b=-4", font_size=24, color=YELLOW)
        good_lbl.to_edge(RIGHT, buff=0.35).shift(UP * 0.35)
        self.play(Create(good_line), Write(good_lbl), run_time=0.9)
        self.wait(0.7)

        # ── 10) f'(10) ──
        self.play(
            cap.animate.become(caption_bar("f'(x)=3x²+2ax+b=3x²−4")),
            run_time=0.35,
        )
        answer = VGroup(
            MathTex(r"f'(x)=3x^2+2ax+b=3x^2-4", font_size=26),
            MathTex(r"f'(10)=3\cdot 10^2-4=296", font_size=30, color=ANSWER_COLOR),
            Text("정답  296", font=KOREAN_FONT, font_size=28, color=ANSWER_COLOR),
        ).arrange(DOWN, buff=0.2).to_edge(RIGHT, buff=0.3).shift(DOWN * 1.0)
        box = SurroundingRectangle(answer[-1], color=ANSWER_COLOR, buff=0.1)
        self.play(Write(answer[0]), run_time=0.55)
        self.play(Write(answer[1]), Write(answer[2]), Create(box), run_time=0.85)
        self.wait(2.0)
