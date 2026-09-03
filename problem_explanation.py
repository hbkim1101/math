"""문제(좌상단) + 해설(나머지) 레이아웃 데모 씬."""

from manim import *
from layout_config import (
    make_chalkboard_background,
    make_chalkboard_bg_texts,
    make_region_guides,
)
from suneung_problems import build_suneung_2_problem, build_suneung_2_explanation

# 렌더 (이미지):
#   manim -ql -s problem_explanation.py LayoutStaticScene
# 실시간 미리보기:
#   ./scripts/live_preview.sh


def _build_layout_content():
    """레이아웃 데모: 2025 수능 2번 + 해설."""
    bg = make_chalkboard_bg_texts()
    guides = make_region_guides(show_labels=True)

    problem_text = build_suneung_2_problem()
    explain_right, explain_bottom = build_suneung_2_explanation()

    return VGroup(bg, guides, problem_text, explain_right, explain_bottom)


class LayoutStaticScene(Scene):
    """애니메이션 없이 즉시 PNG로 뽑는 정적 레이아웃 씬 (미리보기용)."""

    def construct(self):
        self.camera.background_color = "#0A1630"
        self.add(_build_layout_content())


class LayoutPreviewScene(Scene):
    """영역 구분만 보여주는 레이아웃 미리보기 씬."""

    def construct(self):
        bg = make_chalkboard_background(self)
        content = _build_layout_content()
        _, guides, problem_text, explain_right, explain_bottom = content

        self.add(bg)

        self.play(FadeIn(guides), run_time=0.8)
        self.play(
            FadeIn(problem_text),
            FadeIn(explain_right),
            FadeIn(explain_bottom),
            run_time=0.8,
        )
        self.wait(2.0)
