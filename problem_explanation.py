"""문제(좌상단) + 해설(나머지) 레이아웃 데모 씬."""

from manim import *
from layout_config import (
    make_chalkboard_background,
    make_region_guides,
    place_in_problem,
    place_in_explain_right,
    place_in_explain_bottom,
)

# 렌더:
#   manim -ql problem_explanation.py LayoutPreviewScene
# 실시간 미리보기:
#   ./scripts/live_preview.sh


class LayoutPreviewScene(Scene):
    """영역 구분만 보여주는 레이아웃 미리보기 씬."""

    def construct(self):
        # ---------- 배경 ----------
        bg = make_chalkboard_background(self)
        self.add(bg)

        # ---------- 영역 가이드 (문제 / 해설 구분선) ----------
        guides = make_region_guides(show_labels=True)
        self.play(FadeIn(guides), run_time=0.8)

        # ---------- 문제 영역: placeholder ----------
        problem_text = VGroup(
            Text("문제 영역", font_size=24, color=WHITE, weight=BOLD),
            MathTex(r"\frac{f(x)-f(1)}{x-1} = f'(g(x))", color=WHITE).scale(0.9),
            Text("(x ≠ 1)", font_size=20, color=GREY_B),
        ).arrange(DOWN, buff=0.25)
        place_in_problem(problem_text)

        # ---------- 해설 영역: placeholder ----------
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

        self.play(
            FadeIn(problem_text),
            FadeIn(explain_right),
            FadeIn(explain_bottom),
            run_time=0.8,
        )

        self.wait(2.0)
