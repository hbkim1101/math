from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from manim import *

from src.config import ANSWER_COLOR, HIGHLIGHT_COLOR, KOREAN_FONT, TITLE_COLOR
from src.renderer.layout import caption_bar, fit_text_width, place_equation


@dataclass
class Segment:
    kind: str
    duration: float
    index: int = -1


def load_lecture_timing(path: Path | None) -> list[Segment]:
    if path is None or not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    segments: list[Segment] = []
    for seg in data.get("segments", []):
        segments.append(Segment(kind=seg["kind"], duration=float(seg["duration"]), index=seg.get("index", -1)))
    # legacy fallback
    if not segments:
        for item in data.get("steps", []):
            segments.append(Segment(kind="step", duration=float(item.get("duration", 2.5)), index=int(item["index"])))
    return segments


def env_lecture_timing() -> Path | None:
    raw = os.environ.get("MATH_VIZ_TIMING")
    return Path(raw) if raw else None


class LectureMixin:
    """TTS 길이에 맞춰 대기하는 강의 Scene mixin."""

    _segments: list[Segment]
    _seg_ptr: int = 0

    def init_lecture_timing(self) -> None:
        self._segments = load_lecture_timing(env_lecture_timing())
        self._seg_ptr = 0

    def wait_segment(self, kind: str, index: int = -1, *, min_wait: float = 0.5, anim_time: float = 0.0) -> None:
        dur = self._find_duration(kind, index)
        remaining = max(dur - anim_time, min_wait)
        self.wait(remaining)
        self._seg_ptr += 1

    def _find_duration(self, kind: str, index: int) -> float:
        for i, seg in enumerate(self._segments[self._seg_ptr :], self._seg_ptr):
            if seg.kind == kind and (index < 0 or seg.index == index):
                return seg.duration
        return 3.0

    def show_header(self, brand: str, title: str) -> VGroup:
        header = VGroup(
            Text(brand, font=KOREAN_FONT, font_size=20, color=GRAY_B),
            Text(title, font=KOREAN_FONT, font_size=26, color=TITLE_COLOR),
        ).arrange(DOWN, buff=0.06).to_edge(UP, buff=0.22)
        self.play(FadeIn(header), run_time=0.4)
        return header

    def show_caption(self, cap: Text | None, text: str) -> Text:
        new_cap = caption_bar(text)
        if cap is None:
            self.play(FadeIn(new_cap), run_time=0.35)
        else:
            self.play(cap.animate.become(new_cap), run_time=0.35)
        return new_cap

    def show_equations(
        self,
        lines: list[str],
        *,
        color: ManimColor = WHITE,
        font_size: int = 28,
        stagger: float = 0.55,
    ) -> VGroup:
        """우측 패널에 수식을 순차적으로 표시."""
        group = VGroup()
        for i, line in enumerate(lines):
            eq = place_equation(MathTex(line, font_size=font_size, color=color))
            if i > 0:
                eq.shift(DOWN * (0.55 * i))
            if group:
                self.play(FadeOut(group), run_time=0.15)
            group = VGroup(eq)
            self.play(Write(eq), run_time=stagger)
        return group

    def show_answer_box(self, answer: str) -> None:
        box = RoundedRectangle(
            width=6.5, height=1.1, corner_radius=0.15,
            color=ANSWER_COLOR, fill_color=ANSWER_COLOR, fill_opacity=0.12, stroke_width=2,
        )
        label = Text("정답", font=KOREAN_FONT, font_size=32, color=ANSWER_COLOR)
        ans = Text(str(answer), font=KOREAN_FONT, font_size=36, color=ANSWER_COLOR)
        g = VGroup(box, VGroup(label, ans).arrange(RIGHT, buff=0.35)).move_to(ORIGIN)
        self.play(FadeIn(g, scale=0.95), run_time=0.6)
