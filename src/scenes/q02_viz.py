"""Q02 derivative as tangent slope visualization."""

from __future__ import annotations

from manim import *

from src.config import ANSWER_COLOR, KOREAN_FONT, TITLE_COLOR
from src.renderer.graph_helpers import caption_bar, make_graph_axes


class Q02DerivativeVizScene(Scene):
    def construct(self) -> None:
        header = Text("2026 수능 공통 2번 · 미분계수", font=KOREAN_FONT, font_size=26, color=TITLE_COLOR)
        header.to_edge(UP, buff=0.3)
        self.play(FadeIn(header))

        cap = caption_bar("f'(1) = x=1에서 접선 기울기")
        self.play(FadeIn(cap))

        axes = make_graph_axes(x_range=(-2, 2, 1), y_range=(-5, 15, 5)).shift(DOWN * 0.1)
        graph = axes.plot(lambda x: 3 * x**3 + 7 * x + 1, x_range=[-1.5, 1.5], color=BLUE, stroke_width=3)
        self.play(Create(axes), Create(graph), run_time=1.2)

        x0 = 1
        y0 = 3 * x0**3 + 7 * x0 + 1
        slope = 9 * x0**2 + 7
        point = Dot(axes.coords_to_point(x0, y0), color=YELLOW, radius=0.09)
        tangent = axes.plot(
            lambda x: slope * (x - x0) + y0,
            x_range=[-0.5, 1.5],
            color=YELLOW,
            stroke_width=2.5,
        )
        lbl = MathTex(r"(1,\,11)", font_size=24, color=YELLOW).next_to(point, UR, buff=0.1)
        self.play(FadeIn(point), Create(tangent), Write(lbl), run_time=1.0)

        slope_label = MathTex(r"f'(1)=9\cdot1+7=16", font_size=34, color=ANSWER_COLOR)
        slope_label.to_edge(RIGHT, buff=0.5).shift(DOWN * 0.5)
        box = SurroundingRectangle(slope_label, color=ANSWER_COLOR, buff=0.15)
        self.play(
            cap.animate.become(caption_bar("극한 = 미분계수 = 접선 기울기")),
            Write(slope_label),
            Create(box),
            run_time=1.0,
        )
        self.wait(1.2)
