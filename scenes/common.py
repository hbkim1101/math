"""Shared helpers for math lecture Manim scenes (split-screen layout)."""

from __future__ import annotations

from pathlib import Path

from manim import *

KOREAN_FONT = "Noto Sans CJK KR"
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

# Layout constants (16:9 frame ≈ 14.22 × 8)
PROBLEM_PANEL_WIDTH = 5.2
LECTURE_PANEL_CENTER = RIGHT * 2.8
DIVIDER_X = -0.6


def ktext(content: str, font_size: int = 36, **kwargs) -> Text:
    return Text(content, font=KOREAN_FONT, font_size=font_size, **kwargs)


class LectureScene(Scene):
    """Left: problem image (fixed) · Right: lecture notes (animated)."""

    problem_panel: VGroup
    lecture_slot: VGroup
    divider: Line
    step_badge: VGroup | None = None

    def setup_lecture(self, problem_image: str | Path, title: str = "") -> None:
        img_path = Path(problem_image)
        if not img_path.is_absolute():
            img_path = ASSETS_DIR / img_path.name

        # ── left: problem card ──
        header = ktext(title or "문제", font_size=22, color=BLUE)
        header.to_corner(UL, buff=0.25).shift(RIGHT * 0.15)

        if img_path.exists():
            problem_img = ImageMobject(str(img_path))
            problem_img.scale_to_fit_height(6.8)
        else:
            problem_img = Rectangle(
                width=4.5, height=6.5, color=GRAY, fill_color=WHITE, fill_opacity=1
            )
            placeholder = ktext("문제 이미지\nassets/ 에 추가", font_size=20, color=GRAY)
            problem_img = VGroup(problem_img, placeholder)

        problem_img.move_to(LEFT * 3.35 + DOWN * 0.15)

        panel_bg = RoundedRectangle(
            width=PROBLEM_PANEL_WIDTH,
            height=7.4,
            corner_radius=0.12,
            fill_color="#F5F7FA",
            fill_opacity=1,
            stroke_color="#D0D7E2",
            stroke_width=1.5,
        ).move_to(LEFT * 3.35 + DOWN * 0.1)

        self.problem_panel = Group(panel_bg, problem_img, header)

        # ── divider ──
        self.divider = Line(UP * 3.6, DOWN * 3.6, color="#CCCCCC", stroke_width=2)
        self.divider.move_to(RIGHT * DIVIDER_X)

        # ── right: lecture area placeholder ──
        self.lecture_slot = VGroup()

        # NOTE: caller animates FadeIn of problem_panel + divider

    def lecture_step_header(self, number: int, title: str) -> VGroup:
        badge = Circle(radius=0.22, color=BLUE, fill_opacity=1)
        num = Text(str(number), font_size=22, color=WHITE).move_to(badge)
        label = ktext(title, font_size=26)
        header = VGroup(badge, num, label).arrange(RIGHT, buff=0.2)
        header.to_edge(UP, buff=0.35).align_to(LECTURE_PANEL_CENTER, LEFT).shift(LEFT * 2.8)
        return header

    def place_lecture(self, *mobjects: Mobject) -> VGroup:
        """Position mobjects in the right lecture panel."""
        group = VGroup(*mobjects)
        group.move_to(LECTURE_PANEL_CENTER + DOWN * 0.2)
        return group

    def clear_lecture(self, *extra) -> None:
        to_remove = [m for m in self.lecture_slot.submobjects]
        if self.step_badge:
            to_remove.append(self.step_badge)
        to_remove.extend(extra)
        if to_remove:
            self.play(*[FadeOut(m) for m in to_remove], run_time=0.5)
        self.lecture_slot = VGroup()
        self.step_badge = None

    def show_lecture(self, step_num: int, step_title: str, *content, wait: float = 2.0) -> None:
        self.clear_lecture()
        self.step_badge = self.lecture_step_header(step_num, step_title)
        body = self.place_lecture(*content)
        self.lecture_slot = body

        self.play(FadeIn(self.step_badge), run_time=0.4)
        for item in content:
            if isinstance(item, MathTex):
                self.play(Write(item), run_time=0.9)
            else:
                self.play(FadeIn(item, shift=UP * 0.1), run_time=0.6)
        self.wait(wait)

    def show_intro(self, line1: str, line2: str, tag: str = "") -> None:
        overlay = VGroup(
            ktext(line1, font_size=38),
            ktext(line2, font_size=48, color=YELLOW),
        ).arrange(DOWN, buff=0.3)
        if tag:
            t = Text(tag, font=KOREAN_FONT, font_size=22, color=GRAY)
            t.next_to(overlay, DOWN, buff=0.25)
            overlay.add(t)
        overlay.move_to(ORIGIN)
        self.play(FadeIn(overlay), run_time=1)
        self.wait(1.5)
        self.play(FadeOut(overlay), run_time=0.6)
