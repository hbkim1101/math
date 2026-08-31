"""Q15 graph panels — axes+curve only, 주석은 YAML annotate."""

from __future__ import annotations

from manim import *

from src.renderer.graph_helpers import make_graph_axes


def f_prime(x: float) -> float:
    return -6 * (x + 1) * (x - 1)


def f_cubic(x: float, k: float = 10.0) -> float:
    return -2 * (x + 2) * (x - 1) ** 2 - k / 2


def g_piecewise(x: float, k: float = 10.0) -> float:
    if abs(x) > 1:
        return f_cubic(x, k) + k
    return -f_cubic(x, k)


def build_f_prime_graph() -> VGroup:
    axes = make_graph_axes(x_range=(-2.5, 2.5, 1), y_range=(-2, 8, 2), x_len=5.0, y_len=2.8)
    curve = axes.plot(f_prime, x_range=[-2.2, 2.2], color=BLUE, stroke_width=3)
    title = MathTex(r"y=f'(x)", font_size=18, color=BLUE).next_to(axes, UP, buff=0.04)
    return VGroup(axes, curve, title)


def build_f_cubic_graph(k: float = 10.0) -> VGroup:
    axes = make_graph_axes(x_range=(-3, 2, 1), y_range=(-8, 4, 2), x_len=5.0, y_len=2.8)
    curve = axes.plot(lambda x: f_cubic(x, k), x_range=[-2.8, 1.5], color=TEAL, stroke_width=3)
    title = MathTex(r"y=f(x)", font_size=18, color=TEAL).next_to(axes, UP, buff=0.04)
    return VGroup(axes, curve, title)


def build_g_graph(k: float = 10.0) -> VGroup:
    axes = make_graph_axes(x_range=(-3, 2, 1), y_range=(-6, 16, 4), x_len=5.0, y_len=2.8)
    left = axes.plot(lambda x: -f_cubic(x, k), x_range=[-1, 1], color=ORANGE, stroke_width=3)
    right1 = axes.plot(lambda x: f_cubic(x, k) + k, x_range=[1.001, 1.8], color=ORANGE, stroke_width=3)
    right2 = axes.plot(lambda x: f_cubic(x, k) + k, x_range=[-2.8, -1.001], color=ORANGE, stroke_width=3)
    title = MathTex(r"y=g(x)", font_size=18, color=ORANGE).next_to(axes, UP, buff=0.04)
    return VGroup(axes, left, right1, right2, title)


GRAPH_BUILDERS = {
    "f_prime": build_f_prime_graph,
    "f_cubic": build_f_cubic_graph,
    "g_piecewise": build_g_graph,
}
