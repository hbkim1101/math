"""문제(좌상단) + 해설(나머지) 레이아웃 데모 씬."""

from manim import *
from layout_config import (
    make_chalkboard_background,
    make_chalkboard_bg_texts,
    make_region_guides,
    place_in_problem,
    place_in_explain_right,
    place_in_explain_bottom,
)

# 렌더 (이미지):
#   manim -ql -s problem_explanation.py LayoutStaticScene
# 실시간 미리보기:
#   ./scripts/live_preview.sh


def _build_layout_content():
    """레이아웃 데모에 들어갈 배경·가이드·placeholder 묶음."""
    bg = make_chalkboard_bg_texts()

    guides = make_region_guides(show_labels=True)

    problem_text = VGroup(
        Text("문제 영역", font_size=24, color=WHITE, weight=BOLD),
        MathTex(r"\frac{f(x)-f(1)}{x-1} = f'(g(x))", color=WHITE).scale(0.9),
        Text("(x ≠ 1)", font_size=20, color=GREY_B),
    ).arrange(DOWN, buff=0.25)
    place_in_problem(problem_text)

    explain_right = VGroup(
        Text("해설 영역 (우측)", font_size=22, color=WHITE, weight=BOLD),
        Text("그래프 · 도형 · 애니메이션", font_size=18, color=GREY_B),
        Text("여기에 시각 자료를 배치", font_size=18, color=GREY_B),
    ).arrange(DOWN, buff=0.2)
    place_in_explain_right(explain_right)

    explain_bottom = VGroup(
        Text("해설 영역 (좌하단)", font_size=20, color=WHITE, weight=BOLD),
        Text("추가 설명 · 수식 · 단계", font_size=16, color=GREY_B),
    ).arrange(DOWN, buff=0.15)
    place_in_explain_bottom(explain_bottom)

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
