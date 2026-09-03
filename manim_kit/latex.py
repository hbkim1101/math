"""LaTeX → MathTex 헬퍼."""

from manim import *


def tex(latex: str, scale: float = 1.0, color=WHITE, **kwargs) -> MathTex:
    """LaTeX 문자열 하나를 MathTex로 만든다."""
    m = MathTex(latex, color=color, **kwargs)
    if scale != 1.0:
        m.scale(scale)
    return m


def tex_block(
    lines: list[str],
    scale: float = 1.0,
    color=WHITE,
    buff: float = 0.2,
    aligned_edge=LEFT,
) -> VGroup:
    """LaTeX 문자열 리스트를 세로로 나열."""
    group = VGroup(*[tex(line, color=color) for line in lines])
    group.arrange(DOWN, buff=buff, aligned_edge=aligned_edge)
    if scale != 1.0:
        group.scale(scale)
    return group
