"""오른쪽 '풀이 보드' 패널: 수식 줄을 순서대로 쌓고, 넘치면 위로 스크롤한다."""

from __future__ import annotations

from typing import Optional

from manim import (
    DOWN, LEFT, UP, RIGHT, ORIGIN,
    AnimationGroup, FadeIn, FadeOut, Mobject, RoundedRectangle, SurroundingRectangle,
    Text, VGroup, Write, Transform, Animation, Indicate,
)

from ..script.models import BoardLayout
from .theme import KOREAN_FONT, Theme


class Board:
    PAD_X = 0.32
    PAD_Y = 0.28
    LINE_BUFF = 0.24

    def __init__(self, layout: BoardLayout, theme: Theme):
        self.layout = layout
        self.theme = theme
        w, h = layout.width, layout.height
        cx, cy = layout.center
        self.frame = RoundedRectangle(
            corner_radius=0.18, width=w, height=h,
            fill_color=layout.background, fill_opacity=0.92,
            stroke_color=layout.border, stroke_width=1.5,
        ).move_to([cx, cy, 0])
        self.title = Text(layout.title, font=KOREAN_FONT, font_size=26, weight="BOLD", color=theme.muted)
        self.title.next_to(self.frame.get_corner(UP + LEFT), DOWN + RIGHT, buff=0.22)
        self.title.set_z_index(3)
        self.header: Optional[Mobject] = None
        self.lines: list[Mobject] = []
        self.group = VGroup(self.frame, self.title)

    # ------------------------------------------------------------------ 영역 계산
    @property
    def left_x(self) -> float:
        return self.frame.get_left()[0] + self.PAD_X

    @property
    def right_x(self) -> float:
        return self.frame.get_right()[0] - self.PAD_X

    @property
    def content_width(self) -> float:
        return self.right_x - self.left_x

    @property
    def content_top(self) -> float:
        base = self.title.get_bottom()[1] - 0.2
        if self.header is not None:
            base = self.header.get_bottom()[1] - 0.26
        return base

    @property
    def content_bottom(self) -> float:
        return self.frame.get_bottom()[1] + self.PAD_Y

    def fit_width(self, mob: Mobject, max_scale: float | None = None) -> Mobject:
        if mob.width > self.content_width:
            mob.scale_to_fit_width(self.content_width)
        return mob

    # ------------------------------------------------------------------ 헤더(문제 요약 등)
    def set_header(self, mob: Mobject) -> None:
        self.header = mob
        mob.next_to(self.title, DOWN, buff=0.18, aligned_edge=LEFT)
        mob.align_to([self.left_x, 0, 0], LEFT)

    def header_target_position(self, mob: Mobject) -> Mobject:
        """헤더로 도킹될 때의 목표 위치/크기를 mob에 적용해서 돌려준다."""
        self.fit_width(mob)
        mob.next_to(self.title, DOWN, buff=0.18, aligned_edge=LEFT)
        mob.align_to([self.left_x, 0, 0], LEFT)
        return mob

    def make_room_for_header(self, header: Mobject) -> list[Animation]:
        """이미 줄이 있을 때 헤더가 들어갈 자리만큼 줄들을 아래로 밀어내는 애니메이션."""
        if not self.lines:
            return []
        needed = (header.get_bottom()[1] - 0.26)
        first_top = self.lines[0].get_top()[1]
        dy = first_top - needed
        if dy <= 0:
            return []
        return [m.animate.shift(DOWN * dy) for m in self.lines]

    # ------------------------------------------------------------------ 줄 추가/교체
    def _place_below(self, mob: Mobject, prev: Optional[Mobject]) -> None:
        if prev is None:
            mob.next_to([self.left_x, self.content_top, 0], DOWN, buff=0, aligned_edge=LEFT)
            mob.align_to([self.left_x, 0, 0], LEFT)
        else:
            mob.next_to(prev, DOWN, buff=self.LINE_BUFF, aligned_edge=LEFT)
            mob.align_to([self.left_x, 0, 0], LEFT)

    def add_line(self, mob: Mobject, scene, run_time: float = 0.9, indent: float = 0.0,
                 animation: str = "write") -> None:
        """새 줄을 추가한다. 공간이 부족하면 오래된 줄을 스크롤아웃한다."""
        self.fit_width(mob)
        mob.set_z_index(3)
        prev = self.lines[-1] if self.lines else None
        self._place_below(mob, prev)
        if indent:
            mob.shift(RIGHT * indent)

        if mob.get_bottom()[1] < self.content_bottom and self.lines:
            # 필요한 만큼 위쪽 줄을 제거
            overflow = self.content_bottom - mob.get_bottom()[1]
            removed: list[Mobject] = []
            freed = 0.0
            while self.lines and freed < overflow:
                top = self.lines.pop(0)
                removed.append(top)
                freed += top.height + self.LINE_BUFF
            shift_anims = [m.animate.shift(UP * freed) for m in self.lines]
            scene.play(
                AnimationGroup(*(FadeOut(m, shift=UP * 0.3) for m in removed)),
                *shift_anims,
                run_time=0.6,
            )
            mob.shift(UP * freed)
        self.lines.append(mob)
        if animation == "fade":
            scene.play(FadeIn(mob, shift=DOWN * 0.15), run_time=run_time)
        else:
            scene.play(Write(mob), run_time=run_time)

    def replace_line(self, index: int, mob: Mobject, scene, run_time: float = 0.9) -> None:
        old = self.lines[index]
        self.fit_width(mob)
        mob.move_to(old, aligned_edge=LEFT)
        mob.align_to(old, UP)
        self.lines[index] = mob
        scene.play(Transform(old, mob), run_time=run_time)
        # Transform 은 old 를 유지하므로 실제 표시 객체는 old. 목록엔 old 를 남겨 둔다.
        self.lines[index] = old

    def highlight_line(self, index: int, scene, color: str, run_time: float = 0.9, box: bool = False) -> None:
        mob = self.lines[index]
        if box:
            rect = SurroundingRectangle(mob, color=color, buff=0.1, corner_radius=0.08, stroke_width=2.5)
            scene.play(FadeIn(rect), run_time=0.35)
            scene.play(FadeOut(rect), run_time=0.35)
        else:
            scene.play(Indicate(mob, color=color, scale_factor=1.06), run_time=run_time)

    def clear(self, scene, run_time: float = 0.6, keep_header: bool = True) -> None:
        anims: list[Animation] = [FadeOut(m, shift=UP * 0.2) for m in self.lines]
        if not keep_header and self.header is not None:
            anims.append(FadeOut(self.header))
            self.header = None
        if anims:
            scene.play(*anims, run_time=run_time)
        self.lines.clear()

    def all_mobjects(self) -> list[Mobject]:
        out = [self.frame, self.title]
        if self.header is not None:
            out.append(self.header)
        out.extend(self.lines)
        return out
