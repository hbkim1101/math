from __future__ import annotations

from dataclasses import dataclass

from manim import *

from src.config import ANSWER_COLOR, CAPTION_BUFF, HIGHLIGHT_COLOR, KOREAN_FONT, TITLE_COLOR


@dataclass(frozen=True)
class Zone:
    """화면 구역 — 겹침 방지용 고정 박스."""

    center: np.ndarray
    width: float
    height: float

    def fit(self, mob: Mobject, max_scale: float = 1.0) -> Mobject:
        mob.move_to(self.center)
        if mob.width > self.width:
            mob.scale(self.width / mob.width)
        if mob.height > self.height:
            mob.scale(self.height / mob.height)
        if mob.width > self.width:  # re-check after height scale
            mob.scale(self.width / mob.width)
        return mob

    def place(self, mob: Mobject) -> Mobject:
        return self.fit(mob)


# Manim frame ≈ 14.22 × 8.0
HEADER = Zone(UP * 3.35, width=13.0, height=0.75)
GRAPH = Zone(LEFT * 3.35 + DOWN * 0.15, width=6.2, height=4.6)
MATH = Zone(RIGHT * 3.2 + DOWN * 0.05, width=5.8, height=4.8)
CAPTION = Zone(DOWN * 3.05, width=12.5, height=0.55)
BADGE = Zone(LEFT * 6.55 + UP * 0.3, width=0.6, height=0.5)
CASE_TAG = Zone(LEFT * 3.35 + UP * 2.05, width=6.0, height=0.45)


def fit_text_width(mob: Mobject, max_width: float) -> Mobject:
    if mob.width > max_width:
        mob.scale(max_width / mob.width)
    return mob


def caption_bar(text: str) -> Text:
    short = text.strip()
    if len(short) > 38:
        short = short[:35] + "…"
    t = Text(short, font=KOREAN_FONT, font_size=19, color=WHITE)
    return CAPTION.place(t)


def split_math_lines(math: str | None) -> list[str]:
    if not math:
        return []
    parts = math.replace("\n", " ").split(r"\;\Rightarrow\;")
    return [p.strip() for p in parts if p.strip()]


class LectureBoard:
    """강의 보드 — 한 구역에 하나만, 교체 시 fade."""

    def __init__(self, scene: Scene) -> None:
        self.scene = scene
        self.caption_mob: Text | None = None
        self.math_mob: VGroup | None = None
        self.graph_mob: VGroup | None = None
        self.badge_mob: Mobject | None = None
        self.case_mob: Text | None = None

    def show_header(self, brand: str, title: str) -> VGroup:
        h = VGroup(
            Text(brand, font=KOREAN_FONT, font_size=18, color=GRAY_B),
            Text(title, font=KOREAN_FONT, font_size=24, color=TITLE_COLOR),
        ).arrange(DOWN, buff=0.05)
        HEADER.place(h)
        self.scene.play(FadeIn(h), run_time=0.35)
        return h

    def set_caption(self, text: str) -> None:
        new = caption_bar(text)
        if self.caption_mob is None:
            self.scene.play(FadeIn(new), run_time=0.25)
        else:
            self.scene.play(self.caption_mob.animate.become(new), run_time=0.25)
        self.caption_mob = new

    def show_badge(self, link: str) -> None:
        self.hide_badge()
        color = HIGHLIGHT_COLOR if link == "when" else YELLOW
        sym = MathTex(r"\rightarrow" if link == "when" else r"\Rightarrow", font_size=40, color=color)
        BADGE.place(sym)
        self.scene.play(FadeIn(sym, scale=0.8), run_time=0.2)
        self.badge_mob = sym

    def hide_badge(self) -> None:
        if self.badge_mob:
            self.scene.play(FadeOut(self.badge_mob), run_time=0.12)
            self.badge_mob = None

    def set_case_tag(self, name: str | None) -> None:
        if self.case_mob:
            self.scene.play(FadeOut(self.case_mob), run_time=0.12)
            self.case_mob = None
        if name:
            tag = Text(f"→ {name}", font=KOREAN_FONT, font_size=20, color=HIGHLIGHT_COLOR)
            CASE_TAG.place(tag)
            self.scene.play(FadeIn(tag), run_time=0.2)
            self.case_mob = tag

    def clear_math(self) -> None:
        if self.math_mob:
            self.scene.play(FadeOut(self.math_mob), run_time=0.15)
            self.math_mob = None

    def write_math_progressive(self, lines: list[str]) -> None:
        """수식을 한 줄씩 쌓아가며 강의 (⇓ 화살표)."""
        self.clear_math()
        if not lines:
            return
        stack = VGroup()
        for i, line in enumerate(lines):
            if i > 0:
                stack.add(MathTex(r"\Downarrow", font_size=18, color=GRAY_B))
            eq = MathTex(line, font_size=24)
            stack.add(eq)
            stack.arrange(DOWN, buff=0.08, aligned_edge=LEFT)
            MATH.fit(stack)
            self.scene.play(Write(eq), run_time=0.45)
        self.math_mob = stack

    def set_graph(self, graph: VGroup) -> None:
        if self.graph_mob:
            self.scene.play(FadeOut(self.graph_mob), run_time=0.2)
        g = GRAPH.place(graph.copy())
        self.scene.play(
            LaggedStart(*[Create(m) if hasattr(m, "points") else FadeIn(m) for m in g], lag_ratio=0.12),
            run_time=1.0,
        )
        self.graph_mob = g

    def highlight_graph_point(self, dot: Dot) -> None:
        self.scene.play(GrowFromCenter(dot), run_time=0.35)

    def wait_lesson(self, duration: float, anim_done: float = 0.0) -> None:
        self.scene.wait(max(duration - anim_done, 0.4))
