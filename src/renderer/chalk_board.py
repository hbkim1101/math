"""칠판 강의 스타일 — 글씨·수식·그래프가 써지는 느낌."""

from __future__ import annotations

from dataclasses import dataclass

from manim import *

from src.config import (
    CHALK_BG,
    CHALK_CYAN,
    CHALK_FAINT,
    CHALK_PINK,
    CHALK_WHITE,
    CHALK_YELLOW,
    KOREAN_FONT,
    TITLE_COLOR,
)


@dataclass(frozen=True)
class ChalkZone:
    center: np.ndarray
    width: float
    height: float

    def fit(self, mob: Mobject) -> Mobject:
        mob.move_to(self.center)
        if mob.width > self.width:
            mob.scale(self.width / mob.width)
        if mob.height > self.height:
            mob.scale(self.height / mob.height)
        if mob.width > self.width:
            mob.scale(self.width / mob.width)
        return mob


# Layout tuned for chalk lecture (graph left, writing right)
CHALK_HEADER = ChalkZone(UP * 3.35, 13.0, 0.7)
CHALK_GRAPH = ChalkZone(LEFT * 3.4 + DOWN * 0.1, 6.0, 4.8)
CHALK_WRITE = ChalkZone(RIGHT * 3.15 + DOWN * 0.05, 5.6, 5.0)
CHALK_FOOT = ChalkZone(DOWN * 3.05, 12.0, 0.55)


def chalk_text(text: str, *, font_size: int = 22, color: str = CHALK_WHITE) -> Text:
    return Text(text, font=KOREAN_FONT, font_size=font_size, color=color)


def chalk_math(latex: str, *, font_size: int = 26, color: str = CHALK_WHITE) -> MathTex:
    return MathTex(latex, font_size=font_size, color=color)


class ChalkBoard:
    """강의 칠판 — 이전 줄은 희미하게 남기고, 새 줄은 Write로 추가."""

    def __init__(self, scene: Scene) -> None:
        self.scene = scene
        self.bg: VGroup | None = None
        self.header: VGroup | None = None
        self.stack = VGroup()
        self.stack.move_to(CHALK_WRITE.center)
        self.foot: Text | None = None
        self.graph: VGroup | None = None

    def mount(self) -> None:
        """칠판 배경 + 미세 질감."""
        board = Rectangle(
            width=14.2,
            height=8.0,
            fill_color=CHALK_BG,
            fill_opacity=1,
            stroke_width=0,
        )
        dots = VGroup()
        rng = np.random.default_rng(7)
        for _ in range(120):
            x = rng.uniform(-6.8, 6.8)
            y = rng.uniform(-3.8, 3.8)
            d = Dot([x, y, 0], radius=0.008, color=CHALK_FAINT, fill_opacity=0.25)
            dots.add(d)
        frame = Rectangle(
            width=13.6,
            height=7.4,
            stroke_color=CHALK_FAINT,
            stroke_width=2,
            fill_opacity=0,
        )
        self.bg = VGroup(board, dots, frame)
        self.scene.add(self.bg)

    def show_title(self, brand: str, title: str) -> None:
        h = VGroup(
            chalk_text(brand, font_size=16, color=CHALK_FAINT),
            chalk_text(title, font_size=24, color=TITLE_COLOR),
        ).arrange(DOWN, buff=0.06)
        CHALK_HEADER.fit(h)
        self.scene.play(AddTextLetterByLetter(h[1], time_per_char=0.04), FadeIn(h[0]), run_time=0.8)
        self.header = h

    def say(self, line: str, *, link: str | None = None) -> None:
        """하단 한 줄 — 칠판 아래 메모처럼 타이핑."""
        prefix = ""
        if link == "when":
            prefix = "→ "
        elif link == "therefore":
            prefix = "⇒ "
        txt = chalk_text(f"{prefix}{line}", font_size=19, color=CHALK_CYAN)
        CHALK_FOOT.fit(txt)
        if self.foot:
            self.scene.play(FadeOut(self.foot, shift=DOWN * 0.05), run_time=0.15)
        self.scene.play(AddTextLetterByLetter(txt, time_per_char=0.035), run_time=max(len(txt.text) * 0.035, 0.5))
        self.foot = txt

    def write_math(self, latex: str, *, color: str = CHALK_WHITE) -> MathTex:
        """오른쪽 풀이 칸에 수식 한 줄 추가 (위 줄은 희미해짐)."""
        for mob in self.stack:
            mob.set_color(CHALK_FAINT)
        eq = chalk_math(latex, color=color)
        if len(self.stack) > 0:
            arrow = chalk_math(r"\Downarrow", font_size=16, color=CHALK_FAINT)
            self.stack.add(arrow)
        self.stack.add(eq)
        self.stack.arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        CHALK_WRITE.fit(self.stack)
        self.scene.add(self.stack)
        self.scene.play(Write(eq), run_time=0.9)
        return eq

    def write_korean(self, text: str) -> Text:
        for mob in self.stack:
            mob.set_color(CHALK_FAINT)
        t = chalk_text(text, font_size=20)
        if len(self.stack) > 0:
            self.stack.add(chalk_math(r"\Downarrow", font_size=16, color=CHALK_FAINT))
        self.stack.add(t)
        self.stack.arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        CHALK_WRITE.fit(self.stack)
        self.scene.add(self.stack)
        self.scene.play(AddTextLetterByLetter(t, time_per_char=0.04), run_time=max(len(text) * 0.04, 0.6))
        return t

    def draw_graph(self, graph: VGroup, *, run_time: float = 1.4) -> VGroup:
        """그래프 — 선은 Create, 축/라벨은 Write."""
        if self.graph:
            self.scene.play(FadeOut(self.graph), run_time=0.25)
        g = graph.copy()
        CHALK_GRAPH.fit(g)
        for m in g:
            if isinstance(m, (VMobject, Axes)) and not isinstance(m, Text):
                m.set_stroke(color=CHALK_WHITE, width=2.8)
                if hasattr(m, "set_color"):
                    try:
                        m.set_color(CHALK_YELLOW)
                    except Exception:
                        pass
        anims: list[Animation] = []
        for m in g:
            if isinstance(m, Text):
                anims.append(AddTextLetterByLetter(m, time_per_char=0.03))
            elif hasattr(m, "points") and len(getattr(m, "points", [])) > 0:
                anims.append(Create(m))
            else:
                anims.append(Write(m))
        self.scene.play(LaggedStart(*anims, lag_ratio=0.15), run_time=run_time)
        self.graph = g
        return g

    def chalk_dot(self, axes: Axes, x: float, y: float, *, color: str = CHALK_YELLOW) -> Dot:
        dot = Dot(axes.coords_to_point(x, y), color=color, radius=0.08)
        self.scene.play(GrowFromCenter(dot), run_time=0.35)
        if self.graph:
            self.graph.add(dot)
        return dot

    def chalk_line(
        self,
        axes: Axes,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        *,
        dashed: bool = False,
        color: str = CHALK_PINK,
    ) -> VMobject:
        p0, p1 = axes.coords_to_point(x0, y0), axes.coords_to_point(x1, y1)
        line: VMobject = DashedLine(p0, p1, color=color, stroke_width=2.2) if dashed else Line(p0, p1, color=color, stroke_width=2.2)
        self.scene.play(Create(line), run_time=0.55)
        if self.graph:
            self.graph.add(line)
        return line

    def pause(self, t: float = 0.8) -> None:
        self.scene.wait(t)
