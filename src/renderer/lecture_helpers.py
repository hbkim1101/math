"""강의형 Manim Scene 공통 UI — 고2 수준 해설용."""

from __future__ import annotations

from manim import *

from src.config import ANSWER_COLOR, HIGHLIGHT_COLOR, KOREAN_FONT, TITLE_COLOR

# 강의 기본 타이밍 (초)
PAUSE_SHORT = 1.2
PAUSE_MED = 2.0
PAUSE_LONG = 3.0
WRITE_SLOW = 1.4
WRITE_MED = 1.0
FADE = 0.5

NARRATION_WIDTH = 4.8
MATH_MAX_WIDTH = 7.2


class LectureBoard:
    """왼쪽 해설 + 가운데 수식 보드."""

    def __init__(self, scene: Scene) -> None:
        self.scene = scene
        self._narration: Mobject | None = None
        self._math_block: Mobject | None = None
        self._section_label: Mobject | None = None

    def _fit_narration(self, mob: Mobject) -> Mobject:
        if mob.width > NARRATION_WIDTH:
            mob.scale(NARRATION_WIDTH / mob.width)
        return mob

    def _fit_math(self, mob: Mobject) -> Mobject:
        if mob.width > MATH_MAX_WIDTH:
            mob.scale(MATH_MAX_WIDTH / mob.width)
        return mob

    def section(self, title: str, subtitle: str = "") -> None:
        """단원 구분 (예: '1단계 · 좌변 계산')."""
        parts: list[Mobject] = [
            Text(title, font=KOREAN_FONT, font_size=22, color=TITLE_COLOR),
        ]
        if subtitle:
            parts.append(Text(subtitle, font=KOREAN_FONT, font_size=18, color=GRAY_B))
        label = VGroup(*parts).arrange(DOWN, buff=0.06, aligned_edge=LEFT)
        label.to_corner(UL, buff=0.15).shift(DOWN * 0.55 + RIGHT * 0.05)
        if self._section_label is not None:
            self.scene.play(
                FadeOut(self._section_label, shift=LEFT * 0.1),
                FadeIn(label, shift=LEFT * 0.1),
                run_time=FADE,
            )
        else:
            self.scene.play(FadeIn(label, shift=LEFT * 0.1), run_time=FADE)
        self._section_label = label

    def say(
        self,
        lines: list[str],
        *,
        highlight: str | None = None,
        pause: float = PAUSE_MED,
    ) -> Text:
        """왼쪽에 선생님 해설 (2~4줄)."""
        texts = VGroup(
            *[
                Text(line, font=KOREAN_FONT, font_size=20, color=WHITE, line_spacing=1.15)
                for line in lines
            ]
        ).arrange(DOWN, buff=0.14, aligned_edge=LEFT)
        if highlight:
            for t in texts:
                if highlight in t.text:
                    t.set_color(HIGHLIGHT_COLOR)
        texts = self._fit_narration(texts)
        texts.to_edge(LEFT, buff=0.35).shift(UP * 0.15)

        if self._narration is not None:
            self.scene.play(
                FadeOut(self._narration, shift=LEFT * 0.08),
                FadeIn(texts, shift=LEFT * 0.08),
                run_time=FADE,
            )
        else:
            self.scene.play(FadeIn(texts, shift=LEFT * 0.08), run_time=FADE)
        self._narration = texts
        self.scene.wait(pause)
        return texts

    def tip(self, text: str, pause: float = PAUSE_MED) -> None:
        """핵심 포인트 강조."""
        box_text = Text(f"💡 {text}", font=KOREAN_FONT, font_size=19, color=HIGHLIGHT_COLOR)
        box_text = self._fit_narration(box_text)
        box = SurroundingRectangle(box_text, color=HIGHLIGHT_COLOR, buff=0.1, corner_radius=0.08)
        tip = VGroup(box, box_text).next_to(self._narration, DOWN, buff=0.25, aligned_edge=LEFT)
        self.scene.play(FadeIn(tip, shift=UP * 0.05), run_time=FADE)
        self.scene.wait(pause)
        self.scene.play(FadeOut(tip), run_time=FADE)

    def clear_math(self) -> None:
        if self._math_block is not None:
            self.scene.play(FadeOut(self._math_block), run_time=FADE)
            self._math_block = None

    def write_math(
        self,
        latex: str,
        *,
        font_size: int = 28,
        color: ManimColor = WHITE,
        pause: float = PAUSE_MED,
        shift_from: Mobject | None = None,
    ) -> MathTex:
        """수식 한 줄 Write."""
        eq = self._fit_math(MathTex(latex, font_size=font_size, color=color))
        eq.shift(RIGHT * 1.8 + UP * 0.1)
        if shift_from is not None:
            eq.next_to(shift_from, DOWN, buff=0.35, aligned_edge=LEFT)
        self.scene.play(Write(eq), run_time=WRITE_SLOW)
        self.scene.wait(pause)
        return eq

    def append_math(
        self,
        latex: str,
        *,
        font_size: int = 26,
        color: ManimColor = WHITE,
        pause: float = PAUSE_MED,
    ) -> VGroup:
        """기존 수식 아래에 줄 추가."""
        eq = MathTex(latex, font_size=font_size, color=color)
        if self._math_block is None:
            block = self._fit_math(eq)
            block.shift(RIGHT * 1.8 + UP * 0.2)
            self.scene.play(Write(block), run_time=WRITE_SLOW)
            self._math_block = block
        else:
            eq.next_to(self._math_block, DOWN, buff=0.32, aligned_edge=LEFT)
            new_block = VGroup(self._math_block, eq)
            self._fit_math(new_block)
            self.scene.play(Write(eq), run_time=WRITE_MED)
            self._math_block = new_block
        self.scene.wait(pause)
        return self._math_block  # type: ignore[return-value]

    def show_math_group(self, group: VGroup, pause: float = PAUSE_MED) -> None:
        """미리 만든 수식 그룹 표시."""
        group = self._fit_math(group)
        group.shift(RIGHT * 1.6 + UP * 0.05)
        if self._math_block is not None:
            self.scene.play(FadeOut(self._math_block), run_time=FADE)
        self._math_block = group
        self.scene.play(FadeIn(group), run_time=FADE + 0.15)
        self.scene.wait(pause)

    def transform_math(self, new_block: VGroup, pause: float = PAUSE_MED) -> None:
        new_block = self._fit_math(new_block)
        new_block.move_to(self._math_block).align_to(self._math_block, LEFT) if self._math_block else new_block.shift(RIGHT * 1.6)
        if self._math_block is None:
            self.scene.play(FadeIn(new_block), run_time=FADE)
        else:
            self.scene.play(ReplacementTransform(self._math_block, new_block), run_time=WRITE_MED)
        self._math_block = new_block
        self.scene.wait(pause)

    def clear_all(self) -> None:
        to_fade = [m for m in (self._narration, self._math_block) if m is not None]
        if to_fade:
            self.scene.play(*[FadeOut(m) for m in to_fade], run_time=FADE)
        self._narration = None
        self._math_block = None
