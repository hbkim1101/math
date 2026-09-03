"""수능 문제 데이터 (Manim 레이아웃용)."""

from manim import *
from layout_config import (
    LayoutRegions,
    explain_right_box,
    place_in_problem,
    place_in_explain_bottom,
)


def suneung2_f(x):
    """2025 수능 2번: f(x) = x³ - 8x + 7"""
    return x**3 - 8 * x + 7


def suneung2_df(x):
    """f'(x) = 3x² - 8"""
    return 3 * x**2 - 8


A = 2  # 미분점 x = 2


def build_suneung_2_problem():
    """2025학년도 수능 수학 공통 2번 — 미분계수의 정의."""
    problem = VGroup(
        Text("2025 수능 2번", font_size=20, color=TEAL_A, weight=BOLD),
        MathTex(r"f(x) = x^3 - 8x + 7", color=WHITE).scale(0.78),
        MathTex(
            r"\lim_{h \to 0} \frac{f(2+h) - f(2)}{h}",
            color=WHITE,
        ).scale(0.72),
        Text("의 값을 구하시오.  [2점]", font_size=15, color=GREY_B),
    ).arrange(DOWN, buff=0.16, aligned_edge=LEFT)
    place_in_problem(problem)
    return problem


def build_suneung_2_tangent_graph():
    """f(x) 그래프 + x=2에서의 접선 시각화 (우측 해설 영역)."""
    box = explain_right_box()
    fa = suneung2_f(A)
    slope = suneung2_df(A)

    axes = Axes(
        x_range=[-2, 3.5, 1],
        y_range=[-6, 14, 4],
        x_length=box["width"] - 1.8,
        y_length=box["height"] - 2.4,
        tips=False,
        axis_config={"color": GREY_B, "stroke_width": 1.5},
    )
    axes.move_to(box["center"] + DOWN * 0.15)

    graph = axes.plot(
        suneung2_f,
        x_range=[-1.8, 3.2],
        color=RED_C,
        stroke_width=2.5,
    )

    # 접선: y - f(2) = f'(2)(x - 2)
    tangent = axes.plot(
        lambda x: fa + slope * (x - A),
        x_range=[-0.5, 3.0],
        color=GREEN_C,
        stroke_width=2.5,
    )

    point = Dot(axes.c2p(A, fa), radius=0.055, color=YELLOW)
    x_dash = DashedLine(
        axes.c2p(A, 0),
        axes.c2p(A, fa),
        color=YELLOW_E,
        dash_length=0.06,
        dashed_ratio=0.55,
        stroke_width=1.5,
    )

    x_label = MathTex("2", color=YELLOW_E).scale(0.48)
    x_label.next_to(axes.c2p(A, 0), DOWN, buff=0.06)

    point_label = MathTex(r"(2,\,-1)", color=YELLOW_E).scale(0.45)
    point_label.next_to(point, UR, buff=0.08)

    tangent_label = VGroup(
        Text("접선 기울기", font_size=14, color=GREEN_C),
        MathTex(r"f'(2)=4", color=GREEN_C).scale(0.55),
    ).arrange(RIGHT, buff=0.08)
    tangent_label.next_to(axes.c2p(2.8, fa + slope * 0.8), UP, buff=0.05)

    return VGroup(
        axes,
        graph,
        tangent,
        x_dash,
        point,
        x_label,
        point_label,
        tangent_label,
    )


def build_suneung_2_explanation():
    """2025 수능 2번 해설 — 그래프(우측) + 수식(좌하단)."""
    graph = build_suneung_2_tangent_graph()

    explain_bottom = VGroup(
        Text("해설", font_size=18, color=WHITE, weight=BOLD),
        MathTex(
            r"\lim_{h \to 0} \frac{f(2+h) - f(2)}{h} = f'(2)",
            color=WHITE,
        ).scale(0.58),
        MathTex(r"f'(x) = 3x^2 - 8 \;\;\Rightarrow\;\; f'(2) = 4", color=YELLOW_E).scale(0.6),
        MathTex(
            r"f'(a) = \lim_{h \to 0} \frac{f(a+h) - f(a)}{h}",
            color=GREY_B,
        ).scale(0.52),
    ).arrange(DOWN, buff=0.1, aligned_edge=LEFT)

    box = RoundedRectangle(
        width=LayoutRegions.PROBLEM_W,
        height=LayoutRegions.EXPLAIN_BOTTOM_H,
        corner_radius=0.12,
    ).move_to(LayoutRegions.explain_bottom_center)
    explain_bottom.move_to(box.get_center() + UP * 0.1)
    explain_bottom.set_max_width(box.width - 0.9)
    explain_bottom.set_max_height(box.height - 0.5)

    return graph, explain_bottom
