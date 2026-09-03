"""수능 문제 데이터 (Manim 레이아웃용)."""

from manim import *
from layout_config import place_in_problem, place_in_explain_right, place_in_explain_bottom


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


def build_suneung_2_explanation():
    """2025 수능 2번 해설 — 미분계수의 정의 활용."""
    explain_right = VGroup(
        Text("해설", font_size=22, color=WHITE, weight=BOLD),
        MathTex(
            r"\lim_{h \to 0} \frac{f(2+h) - f(2)}{h} = f'(2)",
            color=WHITE,
        ).scale(0.72),
        MathTex(r"f'(x) = 3x^2 - 8", color=WHITE).scale(0.78),
        MathTex(r"f'(2) = 3 \cdot 2^2 - 8 = 4", color=YELLOW_E).scale(0.82),
    ).arrange(DOWN, buff=0.18, aligned_edge=LEFT)
    place_in_explain_right(explain_right)

    explain_bottom = VGroup(
        Text("핵심", font_size=18, color=WHITE, weight=BOLD),
        MathTex(
            r"f'(a) = \lim_{h \to 0} \frac{f(a+h) - f(a)}{h}",
            color=GREY_B,
        ).scale(0.62),
        Text("극한식이 미분계수의 정의와 같다", font_size=14, color=GREY_B),
    ).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
    place_in_explain_bottom(explain_bottom)

    return explain_right, explain_bottom
