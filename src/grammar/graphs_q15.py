"""Q15 graph panels — f', f, g piecewise."""

from __future__ import annotations

from manim import *

from src.renderer.graph_helpers import make_graph_axes
from src.renderer.layout import place_graph_group


def f_prime(x: float) -> float:
    return -6 * (x + 1) * (x - 1)


def f_cubic(x: float, k: float = 10.0) -> float:
    return -2 * (x + 2) * (x - 1) ** 2 - k / 2


def g_piecewise(x: float, k: float = 10.0) -> float:
    if abs(x) > 1:
        return f_cubic(x, k) + k
    return -f_cubic(x, k)


def build_f_prime_graph() -> VGroup:
    axes = make_graph_axes(x_range=(-2.5, 2.5, 1), y_range=(-2, 8, 2), x_len=5.5, y_len=3.2)
    curve = axes.plot(f_prime, x_range=[-2.2, 2.2], color=BLUE, stroke_width=3)
    dots = VGroup(
        Dot(axes.coords_to_point(-1, 0), color=YELLOW, radius=0.07),
        Dot(axes.coords_to_point(1, 0), color=YELLOW, radius=0.07),
        Dot(axes.coords_to_point(0, 6), color=RED, radius=0.07),
    )
    lbl = MathTex(r"y=f'(x)", font_size=22, color=BLUE).next_to(axes, UP, buff=0.08)
    return place_graph_group(VGroup(axes, curve, dots, lbl))


def build_f_cubic_graph(k: float = 10.0) -> VGroup:
    axes = make_graph_axes(x_range=(-3, 2, 1), y_range=(-8, 4, 2), x_len=5.5, y_len=3.2)
    curve = axes.plot(lambda x: f_cubic(x, k), x_range=[-2.8, 1.5], color=TEAL, stroke_width=3)
    hline = DashedLine(
        axes.coords_to_point(-2.8, -k / 2),
        axes.coords_to_point(1.5, -k / 2),
        color=RED,
        stroke_width=2,
    )
    lbl = MathTex(r"y=f(x)", font_size=22, color=TEAL).next_to(axes, UP, buff=0.08)
    return place_graph_group(VGroup(axes, curve, hline, lbl))


def build_g_graph(k: float = 10.0, t_line: float = 13.0) -> VGroup:
    axes = make_graph_axes(x_range=(-3, 2, 1), y_range=(-6, 16, 4), x_len=5.5, y_len=3.2)
    left = axes.plot(lambda x: -f_cubic(x, k), x_range=[-1, 1], color=ORANGE, stroke_width=3)
    right1 = axes.plot(lambda x: f_cubic(x, k) + k, x_range=[1.001, 1.8], color=ORANGE, stroke_width=3)
    right2 = axes.plot(lambda x: f_cubic(x, k) + k, x_range=[-2.8, -1.001], color=ORANGE, stroke_width=3)
    t_h = Line(
        axes.coords_to_point(-2.8, t_line),
        axes.coords_to_point(1.8, t_line),
        color=RED,
        stroke_width=2.5,
    )
    t_lbl = MathTex(r"y=13", font_size=22, color=RED).next_to(axes.coords_to_point(1.5, t_line), UP, buff=0.05)
    lbl = MathTex(r"y=g(x)", font_size=22, color=ORANGE).next_to(axes, UP, buff=0.08)
    return place_graph_group(VGroup(axes, left, right1, right2, t_h, t_lbl, lbl))


GRAPH_BUILDERS = {
    "f_prime": build_f_prime_graph,
    "f_cubic": build_f_cubic_graph,
    "g_piecewise": build_g_graph,
}
