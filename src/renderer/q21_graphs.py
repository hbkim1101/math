"""Graph helpers for cubic inequality Q21 (2ax+b sandwiched between bounds)."""

from __future__ import annotations

import math

from manim import *


def upper_bound(x: float) -> float:
    """y = x^4 - 4x^2"""
    return x**4 - 4 * x**2


def lower_bound(x: float) -> float:
    """y = -3x^2 - 4"""
    return -3 * x**2 - 4


def middle_line(x: float, a: float, b: float) -> float:
    """y = 2ax + b"""
    return 2 * a * x + b


def plot_upper_bound(axes: Axes, x_range: tuple[float, float] = (-2.5, 2.5), color=BLUE) -> ParametricFunction:
    return axes.plot(
        upper_bound,
        x_range=[x_range[0], x_range[1]],
        color=color,
        stroke_width=3,
    )


def plot_lower_bound(axes: Axes, x_range: tuple[float, float] = (-2.5, 2.5), color=TEAL) -> ParametricFunction:
    return axes.plot(
        lower_bound,
        x_range=[x_range[0], x_range[1]],
        color=color,
        stroke_width=3,
    )


def plot_middle_line(
    axes: Axes,
    a: float,
    b: float,
    x_range: tuple[float, float] = (-2.5, 2.5),
    color=YELLOW,
) -> ParametricFunction:
    return axes.plot(
        lambda x, aa=a, bb=b: middle_line(x, aa, bb),
        x_range=[x_range[0], x_range[1]],
        color=color,
        stroke_width=3,
    )


def min_upper_bound() -> tuple[float, float]:
    """Minimum of x^4 - 4x^2 at x = ±sqrt(2)."""
    x = math.sqrt(2)
    return x, upper_bound(x)


def max_lower_bound() -> tuple[float, float]:
    """Maximum of -3x^2 - 4 at x = 0."""
    return 0.0, lower_bound(0.0)


def f_prime(x: float, a: float = 0.0, b: float = -4.0) -> float:
    return 3 * x**2 + 2 * a * x + b
