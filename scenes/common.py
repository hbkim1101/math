"""Shared helpers for math lecture Manim scenes."""

from manim import *

KOREAN_FONT = "Noto Sans CJK KR"


def ktext(content: str, font_size: int = 36, **kwargs) -> Text:
    return Text(content, font=KOREAN_FONT, font_size=font_size, **kwargs)


def step_label(number: int, title: str) -> VGroup:
    badge = Circle(radius=0.28, color=BLUE, fill_opacity=1)
    num = Text(str(number), font_size=28, color=WHITE).move_to(badge)
    label = ktext(title, font_size=32).next_to(badge, RIGHT, buff=0.3)
    return VGroup(badge, num, label).to_edge(UP, buff=0.4).to_edge(LEFT, buff=0.5)


def clear_scene(scene: Scene, *mobjects) -> None:
    if mobjects:
        scene.play(*[FadeOut(m) for m in mobjects], run_time=0.6)
