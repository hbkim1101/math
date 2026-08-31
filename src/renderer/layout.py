from __future__ import annotations

from manim import *

from src.config import CAPTION_BUFF, EQUATION_PANEL_WIDTH, KOREAN_FONT


# Screen zones (Manim default frame ≈ 14.2 × 8)
GRAPH_CENTER = LEFT * 2.0 + DOWN * 0.05
GRAPH_SCALE = 0.88
EQUATION_ANCHOR = RIGHT * 3.15 + UP * 0.15
CAPTION_MAX_WIDTH = 12.8
CAPTION_FONT_SIZE = 20
EQUATION_FONT_SIZE = 30


def fit_text_width(mob: Mobject, max_width: float) -> Mobject:
    if mob.width > max_width:
        mob.scale(max_width / mob.width)
    return mob


def caption_bar(text: str, *, max_width: float = CAPTION_MAX_WIDTH) -> Text:
    """하단 캡션 — 긴 문장은 자동 축소."""
    short = text if len(text) <= 42 else text[:39] + "…"
    bar = Text(short, font=KOREAN_FONT, font_size=CAPTION_FONT_SIZE, color=WHITE)
    return fit_text_width(bar, max_width).to_edge(DOWN, buff=CAPTION_BUFF)


def place_equation(mob: Mobject, *, max_width: float = EQUATION_PANEL_WIDTH) -> Mobject:
    """우측 수식 패널 고정 위치."""
    fit_text_width(mob, max_width)
    mob.move_to(EQUATION_ANCHOR)
    return mob


def place_graph_group(group: Mobject) -> Mobject:
    """그래프 영역 — 좌측, 헤더·캡션과 분리."""
    group.scale(GRAPH_SCALE)
    group.move_to(GRAPH_CENTER)
    return group
