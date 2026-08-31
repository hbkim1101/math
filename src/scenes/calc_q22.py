from __future__ import annotations

import math

from manim import *

from src.config import ANSWER_COLOR, HIGHLIGHT_COLOR, KOREAN_FONT, TITLE_COLOR
from src.renderer.graph_helpers import make_graph_axes
from src.renderer.layout import caption_bar, place_equation, place_graph_group


def curve1(x: float, k: float = 8.0) -> float:
    return 2**x + k / 2


def curve2(x: float, k: float = 8.0) -> float:
    return k / (2**x) + k - 2


def curve3(x: float) -> float:
    return 2 ** (x - 2) - 3


def point_a(k: float = 8.0) -> tuple[float, float]:
    x = math.log2(k) - 1
    return x, k


def point_b(k: float = 8.0) -> tuple[float, float]:
    ax, _ = point_a(k)
    return ax + 3, k - 3


class Q22ExponentialScene(Scene):
    """2026 수능 22번 — 지수·로그함수 그래프 해설."""

    def construct(self) -> None:
        k = 8.0
        ax, ay = point_a(k)
        bx, by = point_b(k)

        header = VGroup(
            Text("수학 한수", font=KOREAN_FONT, font_size=20, color=GRAY_B),
            Text("2026 수능 공통 22번 · 지수·로그함수", font=KOREAN_FONT, font_size=26, color=TITLE_COLOR),
        ).arrange(DOWN, buff=0.06).to_edge(UP, buff=0.22)
        self.play(FadeIn(header), run_time=0.4)

        cap = caption_bar("두 지수함수 그래프의 교점 A를 먼저 잡습니다")
        self.play(FadeIn(cap), run_time=0.35)

        axes = make_graph_axes(x_range=(-1, 6, 1), y_range=(-2, 12, 2), x_len=6.2, y_len=3.8)
        g1 = axes.plot(lambda x: curve1(x, k), x_range=[-0.5, 4.5], color=BLUE, stroke_width=3)
        g2 = axes.plot(lambda x: curve2(x, k), x_range=[-0.5, 4.5], color=TEAL, stroke_width=3)
        g3 = axes.plot(curve3, x_range=[-0.5, 5.5], color=ORANGE, stroke_width=2.5)
        graph = place_graph_group(VGroup(axes, g1, g2, g3))

        lbl = VGroup(
            MathTex(r"y=2^x+\frac{k}{2}", font_size=20, color=BLUE).next_to(axes, UP, buff=0.05).shift(LEFT * 1.2),
            MathTex(r"y=\frac{k}{2^x}+k-2", font_size=20, color=TEAL).next_to(axes, UP, buff=0.05).shift(RIGHT * 0.3),
        )

        self.play(Create(axes), run_time=0.6)
        self.play(Create(g1), Create(g2), FadeIn(lbl), run_time=1.0)

        dot_a = Dot(axes.coords_to_point(ax, ay), color=YELLOW, radius=0.09)
        la = MathTex(r"A", font_size=24, color=YELLOW).next_to(dot_a, UL, buff=0.06)
        eq_a = place_equation(MathTex(r"A=(\log_2 k-1,\,k)", font_size=28, color=HIGHLIGHT_COLOR))
        self.play(
            cap.animate.become(caption_bar("t=2^x로 치환 → A=(log₂k−1, k)")),
            GrowFromCenter(dot_a),
            Write(la),
            Write(eq_a),
            run_time=0.9,
        )
        self.wait(0.7)

        # line AB: x+y = k+log_2 k - 1
        self.play(FadeOut(eq_a), run_time=0.2)
        line_ab = axes.plot(lambda x: (k + math.log2(k) - 1) - x, x_range=[ax - 0.5, bx + 0.5], color=YELLOW, stroke_width=2)
        eq_line = place_equation(MathTex(r"x+y=k+\log_2 k-1", font_size=28))
        self.play(
            cap.animate.become(caption_bar("A를 지나 기울기 −1 직선 → B")),
            Create(line_ab),
            Write(eq_line),
            run_time=0.8,
        )

        dot_b = Dot(axes.coords_to_point(bx, by), color=RED, radius=0.09)
        lb = MathTex(r"B", font_size=24, color=RED).next_to(dot_b, UR, buff=0.06)
        self.play(Create(g3), GrowFromCenter(dot_b), Write(lb), run_time=0.7)
        self.play(FadeOut(eq_line), run_time=0.2)

        # AB distance
        seg = Line(axes.coords_to_point(ax, ay), axes.coords_to_point(bx, by), color=GREEN, stroke_width=3)
        eq_ab = place_equation(MathTex(r"AB=3\sqrt{2}", font_size=32, color=GREEN))
        self.play(
            cap.animate.become(caption_bar("A→B: x+3, y−3 → AB=3√2")),
            Create(seg),
            Write(eq_ab),
            run_time=0.8,
        )
        self.wait(0.6)
        self.play(FadeOut(eq_ab), run_time=0.2)

        # area → height
        tri = Polygon(
            axes.coords_to_point(0, 0),
            axes.coords_to_point(ax, ay),
            axes.coords_to_point(bx, by),
            color=HIGHLIGHT_COLOR,
            fill_opacity=0.15,
            stroke_width=2,
        )
        eq_h = place_equation(
            MathTex(
                r"\frac{1}{2}\cdot3\sqrt{2}\cdot h=16",
                r"\;\Rightarrow\;",
                r"h=\frac{16\sqrt{2}}{3}",
                font_size=26,
            )
        )
        self.play(
            cap.animate.become(caption_bar("△AOB 넓이 16 → 원점-직선 거리 h")),
            FadeIn(tri),
            Write(eq_h),
            run_time=0.9,
        )
        self.wait(0.6)
        self.play(FadeOut(eq_h), FadeOut(tri), run_time=0.25)

        # final
        result = place_equation(
            MathTex(
                r"k+\log_2 k=\frac{35}{3}",
                r"\;\Rightarrow\;",
                r"p+q=38",
                font_size=30,
                color=ANSWER_COLOR,
            )
        )
        box = SurroundingRectangle(result, color=ANSWER_COLOR, buff=0.15)
        self.play(
            cap.animate.become(caption_bar("거리 공식 → k+log₂k=35/3, 정답 38")),
            Write(result),
            Create(box),
            run_time=1.0,
        )
        self.wait(1.5)
