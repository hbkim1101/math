"""Graph helpers for 2026 June mock Calculus Q28."""

from __future__ import annotations

import math

from manim import *

PI = math.pi


def Q(x: float) -> float:
    """x² + x + 5/2"""
    return x**2 + x + 2.5


def ln_Q(x: float) -> float:
    return math.log(Q(x))


def k_slope(x: float) -> float:
    """(2x+1)/Q(x) — derivative of ln(Q(x))."""
    return (2 * x + 1) / Q(x)


def plot_ln_Q(axes: Axes, x_range: tuple[float, float] = (-3.2, 2.8), color=BLUE) -> ParametricFunction:
    return axes.plot(ln_Q, x_range=[x_range[0], x_range[1]], color=color, stroke_width=3)


def plot_tangent_line(
    axes: Axes,
    a: float,
    b: float,
    x_range: tuple[float, float] = (-3.2, 2.8),
    color=YELLOW,
) -> ParametricFunction:
    return axes.plot(
        lambda x, aa=a, bb=b: aa * x + bb,
        x_range=[x_range[0], x_range[1]],
        color=color,
        stroke_width=2.5,
    )


def plot_k_slope(axes: Axes, x_range: tuple[float, float] = (-3.5, 2.5), color=TEAL) -> ParametricFunction:
    return axes.plot(k_slope, x_range=[x_range[0], x_range[1]], color=color, stroke_width=2.5)


def june28_a() -> float:
    return -2 / 3


def june28_b() -> float:
    return math.log(9 / 2) - 4 / 3


def june28_c() -> float:
    return -2.0


def g_outer(y: float) -> float:
    """g(y) = y^5 + y^3"""
    return y**5 + y**3


def plot_g_outer(axes: Axes, x_range: tuple[float, float] = (-1.4, 1.4), color=PURPLE) -> ParametricFunction:
    return axes.plot(g_outer, x_range=[x_range[0], x_range[1]], color=color, stroke_width=3)


def tangent_at_c(c: float) -> tuple[float, float]:
    """Tangent y=ax+b to ln(Q(x)) at inflection x=c."""
    a = (2 * c + 1) / Q(c)
    b = ln_Q(c) - a * c
    return a, b


def plot_tangent_at_c(
    axes: Axes,
    c: float,
    x_range: tuple[float, float] = (-3.2, 2.8),
    color=YELLOW,
) -> tuple[ParametricFunction, float, float]:
    a, b = tangent_at_c(c)
    line = plot_tangent_line(axes, a, b, x_range=x_range, color=color)
    return line, a, b

