"""Q04 piecewise continuity graph visualization."""

from __future__ import annotations

from manim import *

from src.config import ANSWER_COLOR, KOREAN_FONT, TITLE_COLOR
from src.renderer.graph_helpers import caption_bar, korean_label, make_graph_axes


def f_piecewise(x: float, a: float) -> float:
    if x >= 1:
        return 3 * x - 2
    return x**2 - 3 * x + a


class Q04ContinuityVizScene(Scene):
    """4번 — 조각함수 연속: 좌·우극한 시각화."""

    def construct(self) -> None:
        header = Text("2026 수능 공통 4번 · 함수의 연속", font=KOREAN_FONT, font_size=26, color=TITLE_COLOR)
        header.to_edge(UP, buff=0.3)
        self.play(FadeIn(header), run_time=0.4)

        cap = caption_bar("x=1에서 좌극한 = 우극한 = f(1) 이어야 연속")
        self.play(FadeIn(cap), run_time=0.4)

        axes = make_graph_axes(x_range=(-1, 3, 1), y_range=(-3, 5, 1)).shift(DOWN * 0.1)
        x1_line = DashedLine(
            axes.coords_to_point(1, -3),
            axes.coords_to_point(1, 5),
            color=GRAY,
            stroke_width=1.5,
        )
        x1_label = MathTex("x=1", font_size=24).next_to(axes.coords_to_point(1, -2.8), DOWN, buff=0.15)

        a_tracker = ValueTracker(0.0)

        def right_graph():
            return axes.plot(lambda x: 3 * x - 2, x_range=[1, 2.5], color=BLUE, stroke_width=3)

        def left_graph():
            a = a_tracker.get_value()
            return axes.plot(lambda x: x**2 - 3 * x + a, x_range=[-0.5, 0.999], color=TEAL, stroke_width=3)

        left_plot = always_redraw(left_graph)
        right_plot = right_graph()

        self.play(Create(axes), Create(x1_line), Write(x1_label), run_time=0.7)
        self.play(Create(right_plot), run_time=0.8)
        self.add(left_plot)

        # a=0: gap at x=1
        gap_dot_l = Dot(axes.coords_to_point(1, -2), color=RED, radius=0.08)
        gap_dot_r = Dot(axes.coords_to_point(1, 1), color=BLUE, radius=0.08)
        gap_brace = BraceBetweenPoints(axes.coords_to_point(1, -2), axes.coords_to_point(1, 1), direction=RIGHT, color=RED)
        self.play(a_tracker.animate.set_value(0), run_time=0.8)
        self.play(FadeIn(gap_dot_l), FadeIn(gap_dot_r), GrowFromCenter(gap_brace), run_time=0.7)
        self.play(cap.animate.become(caption_bar("a=0: 좌극한 -2 ≠ f(1)=1 → 불연속")))
        self.wait(0.6)

        # animate a → 3
        self.play(
            FadeOut(gap_brace),
            cap.animate.become(caption_bar("a를 키우면 x=1에서 좌극한이 올라감")),
            run_time=0.4,
        )
        connect_dot = always_redraw(
            lambda: Dot(axes.coords_to_point(1, f_piecewise(1, a_tracker.get_value())), color=YELLOW, radius=0.1)
        )
        self.add(connect_dot)
        self.play(a_tracker.animate.set_value(3), run_time=2.0, rate_func=smooth)
        self.play(cap.animate.become(caption_bar("a=3: 좌극한=우극한=f(1)=1 → 연속!")))
        self.wait(0.8)

        ans = VGroup(
            MathTex(r"a-2=1", font_size=36),
            MathTex(r"a=3", font_size=40, color=ANSWER_COLOR),
        ).arrange(DOWN, buff=0.25).to_edge(RIGHT, buff=0.5).shift(DOWN * 0.5)
        box = SurroundingRectangle(ans, color=ANSWER_COLOR, buff=0.15)
        self.play(Write(ans), Create(box), run_time=1.0)
        self.wait(1.2)
