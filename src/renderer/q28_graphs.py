"""Graph helpers for 2026 Sept mock Calculus Q28."""

from __future__ import annotations

import math

import numpy as np
from manim import *

PI = math.pi


def h_composite(t: float) -> float:
    """h(t) = t - tan(t). Defined away from asymptotes."""
    return t - math.tan(t)


def h_composite_derivative(t: float) -> float:
    return 1 - 1 / (math.cos(t) ** 2)


def asymptote_positions(x_min: float, x_max: float) -> list[float]:
    positions: list[float] = []
    n = int(x_min / PI) - 1
    while True:
        pos = PI / 2 + n * PI
        if pos > x_max:
            break
        if pos >= x_min:
            positions.append(pos)
        n += 1
    return positions


def plot_h_composite_branches(
    axes: Axes,
    x_range: tuple[float, float] = (-PI, 3 * PI),
    color: ManimColor = BLUE,
) -> VGroup:
    """Plot t - tan(t) on intervals between vertical asymptotes."""
    graphs = VGroup()
    asymptotes = asymptote_positions(x_range[0], x_range[1])
    bounds = [x_range[0], *asymptotes, x_range[1]]
    for i in range(len(bounds) - 1):
        left = bounds[i] + 0.12
        right = bounds[i + 1] - 0.12
        if right <= left:
            continue
        graphs.add(
            axes.plot(
                lambda x, lo=left, hi=right: h_composite(
                    max(lo + 0.01, min(hi - 0.01, x))
                ),
                x_range=[left, right],
                color=color,
                stroke_width=2.5,
            )
        )
    return graphs


def plot_asymptote_lines(axes: Axes, x_range: tuple[float, float], color=RED) -> VGroup:
    y_min, y_max = axes.y_range[0], axes.y_range[1]
    lines = VGroup()
    for x in asymptote_positions(x_range[0], x_range[1]):
        lines.add(
            DashedLine(
                axes.coords_to_point(x, y_min),
                axes.coords_to_point(x, y_max),
                color=color,
                stroke_width=1.2,
                stroke_opacity=0.55,
            )
        )
    return lines


def f_cubic_increasing(x: float, k: float = 3 / (PI**2)) -> float:
    """f(x) = k·x·(x-π)·(x-2π) from graph analysis."""
    return k * x * (x - PI) * (x - 2 * PI)


def f_cubic_derivative_at_zero(k: float = 3 / (PI**2)) -> float:
    return 2 * k * PI**2  # = 6


def schematic_g_increasing(axes: Axes) -> VGroup:
    """Schematic y=g(x): (0,0)→(π,π)→ approaches 3π/2."""
    # piecewise linear/schematic curve for visualization
    pts = [
        (-0.3, -0.2),
        (0, 0),
        (0.8, 0.6),
        (PI, PI),
        (1.8, 1.9),
        (2.5, 2.3),
        (3.2, 2.55),
        (4.0, 2.65),
    ]
    points = [axes.coords_to_point(x, y) for x, y in pts]
    curve = VMobject(color=TEAL, stroke_width=3)
    curve.set_points_as_corners(points)
    # asymptote y = 3π/2
    asym = DashedLine(
        axes.coords_to_point(-0.5, 3 * PI / 2),
        axes.coords_to_point(4.5, 3 * PI / 2),
        color=GRAY,
        stroke_width=1.5,
    )
    label = MathTex(r"y=\frac{3\pi}{2}", font_size=22, color=GRAY).next_to(
        axes.coords_to_point(4.2, 3 * PI / 2), UP, buff=0.08
    )
    return VGroup(curve, asym, label)


def schematic_g_decreasing(axes: Axes) -> VGroup:
    """Decreasing case — passes (π,π) but can't pass (0,0) with f(0)=0."""
    pts = [(0, 1.5), (0.5, 1.2), (PI, PI), (2.5, 0.5), (3.5, -0.5)]
    points = [axes.coords_to_point(x, y) for x, y in pts]
    curve = VMobject(color=RED, stroke_width=3)
    curve.set_points_as_corners(points)
    cross = Text("✕", font_size=48, color=RED).move_to(axes.coords_to_point(0, 0.8))
    return VGroup(curve, cross)
