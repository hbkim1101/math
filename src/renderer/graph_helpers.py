"""Manim graph utilities for math visualization."""

from __future__ import annotations

import math
from typing import Callable

import numpy as np
from manim import *

from src.config import HIGHLIGHT_COLOR, KOREAN_FONT

# --- Q30: h(x) = f^{-1}(x) ---------------------------------------------------

def h_inverse(x: float) -> float:
    if x < -1:
        return -math.exp(-x - 1) - 1
    if x <= 1:
        return -0.5 * x * (x**2 - 5)
    return math.exp(x - 1) + 1


def h_derivative(x: float) -> float:
    if x < -1:
        return math.exp(-x - 1)
    if x <= 1:
        return -1.5 * x**2 + 2.5
    return math.exp(x - 1)


def tangent_t_parameter() -> float:
    """t < -1 s.t. (-t-1)*exp(-t-1) = 2."""
    lo, hi = -3.0, -1.01
    for _ in range(80):
        mid = (lo + hi) / 2
        val = (-mid - 1) * math.exp(-mid - 1)
        if val > 2:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def critical_slope_b() -> float:
    t = tangent_t_parameter()
    return math.exp(t + 1)


def line_through_origin_one(m: float, x: float) -> float:
    """y = x/m + 1, slope 1/m through (0,1). m≠0."""
    return x / m + 1


def count_h_line_intersections(m: float, samples: int = 2000) -> int:
    if m == 0:
        return 1
    xs = np.linspace(-2.8, 2.8, samples)
    ys_h = np.array([h_inverse(float(x)) for x in xs])
    ys_l = np.array([line_through_origin_one(m, float(x)) for x in xs])
    diff = ys_h - ys_l
    count = 0
    for i in range(len(diff) - 1):
        if diff[i] == 0:
            continue
        if diff[i] * diff[i + 1] < 0:
            count += 1
        elif abs(diff[i]) < 0.02 and (i == 0 or diff[i - 1] * diff[i + 1] < 0):
            count += 1
    return max(count, 0)


def intersection_x_values(m: float) -> list[float]:
    if abs(m) < 1e-6:
        return [0.0] if abs(h_inverse(0) - 1) < 0.05 else []
    xs = np.linspace(-2.8, 2.8, 4000)
    roots: list[float] = []
    prev = h_inverse(float(xs[0])) - line_through_origin_one(m, float(xs[0]))
    for x in xs[1:]:
        cur = h_inverse(float(x)) - line_through_origin_one(m, float(x))
        if prev == 0 or cur == 0 or prev * cur < 0:
            roots.append(float(x))
        prev = cur
    # dedupe close roots
    merged: list[float] = []
    for r in roots:
        if not merged or abs(r - merged[-1]) > 0.08:
            merged.append(r)
    return merged


def make_graph_axes(
    x_range: tuple[float, float, float] = (-3, 3, 1),
    y_range: tuple[float, float, float] = (-3, 4, 1),
    x_len: float = 6.5,
    y_len: float = 4.2,
) -> Axes:
    return Axes(
        x_range=x_range,
        y_range=y_range,
        x_length=x_len,
        y_length=y_len,
        axis_config={"include_tip": True, "font_size": 24},
        tips=False,
    ).set_color(GRAY_B)


def plot_h_inverse(axes: Axes, color: ManimColor = BLUE) -> VGroup:
    left = axes.plot(lambda x: h_inverse(x), x_range=[-2.6, -1.001], color=color, stroke_width=3)
    mid = axes.plot(lambda x: h_inverse(x), x_range=[-1, 1], color=color, stroke_width=3)
    right = axes.plot(lambda x: h_inverse(x), x_range=[1.001, 2.4], color=color, stroke_width=3)
    return VGroup(left, mid, right)


def plot_moving_line(axes: Axes, m_tracker: ValueTracker, color: ManimColor = YELLOW) -> always_redraw:
    def _line() -> Line:
        m = m_tracker.get_value()
        if abs(m) < 0.05:
            m = 0.05 if m >= 0 else -0.05
        x0, x1 = -2.6, 2.6
        p0 = axes.coords_to_point(x0, line_through_origin_one(m, x0))
        p1 = axes.coords_to_point(x1, line_through_origin_one(m, x1))
        return Line(p0, p1, color=color, stroke_width=2.5)

    return always_redraw(_line)


def intersection_dots(axes: Axes, m: float, color: ManimColor = RED) -> VGroup:
    dots = VGroup()
    for x in intersection_x_values(m):
        y = h_inverse(x)
        dots.add(Dot(axes.coords_to_point(x, y), color=color, radius=0.07))
    return dots


def g_m_value(m: float, b: float | None = None) -> int:
    if b is None:
        b = critical_slope_b()
    if m < 0:
        return 0
    if abs(m) < 1e-6:
        return 1
    if m < b - 1e-4:
        return 3 if m > 1e-4 else 1
    if abs(m - b) < 1e-3:
        return 2
    return 1


def plot_gm_step(axes: Axes, b: float | None = None) -> VGroup:
    if b is None:
        b = critical_slope_b()
    segs = VGroup()
    specs = [
        (-0.5, 0, 0, 0),
        (0, 0, 0, 1),
        (0, b, 1, 3),
        (b, b, 3, 2),
        (b, 3.2, 2, 1),
    ]
    for x0, x1, y0, y1 in specs:
        p0 = axes.coords_to_point(x0, y0)
        p1 = axes.coords_to_point(x1, y0)
        p2 = axes.coords_to_point(x1, y1)
        segs.add(Line(p0, p1, color=GREEN, stroke_width=3))
        if y0 != y1:
            segs.add(Line(p1, p2, color=GREEN, stroke_width=2, stroke_opacity=0.5))
    return segs


def korean_label(text: str, font_size: int = 22, color: ManimColor = WHITE) -> Text:
    return Text(text, font=KOREAN_FONT, font_size=font_size, color=color)


def caption_bar(text: str) -> Text:
    from src.renderer.layout import caption_bar as _caption

    return _caption(text)
