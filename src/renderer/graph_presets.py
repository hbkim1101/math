"""Named graph functions for Lecture DSL presets."""

from __future__ import annotations

import math
from typing import Callable

from manim import *

PRESET_REGISTRY: dict[str, Callable[[float], float]] = {}


def register(name: str):
    def deco(fn: Callable[[float], float]):
        PRESET_REGISTRY[name] = fn
        return fn
    return deco


def Q(x: float) -> float:
    return x**2 + x + 2.5


@register("g_y5_y3")
def g_y5_y3(y: float) -> float:
    return y**5 + y**3


@register("june28_ln")
def june28_ln(x: float) -> float:
    return math.log(Q(x))


@register("june28_k")
def june28_k(x: float) -> float:
    return (2 * x + 1) / Q(x)


def get_preset(name: str) -> Callable[[float], float]:
    if name not in PRESET_REGISTRY:
        raise KeyError(f"Unknown graph preset: {name}. Available: {list(PRESET_REGISTRY)}")
    return PRESET_REGISTRY[name]


def tangent_at(preset: str, x0: float) -> tuple[float, float]:
    """Return (a, b) for tangent y=ax+b to preset at x0."""
    fn = get_preset(preset)
    h = 1e-5
    y0 = fn(x0)
    slope = (fn(x0 + h) - fn(x0 - h)) / (2 * h)
    b = y0 - slope * x0
    return slope, b


COLOR_MAP: dict[str, ManimColor] = {
    "white": WHITE,
    "yellow": YELLOW,
    "blue": BLUE,
    "purple": PURPLE,
    "teal": TEAL,
    "red": RED,
    "green": GREEN,
    "orange": ORANGE,
    "gray": GRAY,
    "gray_a": GRAY_A,
    "highlight": "#58C4DD",
    "answer": "#83C167",
    "title": "#FFD700",
}


def resolve_color(name: str) -> ManimColor:
    return COLOR_MAP.get(name.lower(), WHITE)
