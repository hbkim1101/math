"""문제(좌상단) + 해설(나머지) 레이아웃 데모 씬."""

from manim import *
from layout_config import (
    make_chalkboard_background,
    make_chalkboard_bg_texts,
    make_region_guides,
)
from suneung_problems import (
    build_suneung_2_problem,
    build_suneung_2_explain_bottom,
    build_suneung_2_tangent_graph,
    build_suneung_2_graph_parts,
    animate_suneung_2_graph,
)

# 렌더 (이미지):
#   manim -ql -s problem_explanation.py LayoutStaticScene
# 애니메이션 (재생 버튼):
#   manim -ql problem_explanation.py LayoutPreviewScene


def _build_layout_content():
    """레이아웃 데모: 2025 수능 2번 + 해설 (정적 PNG용)."""
    bg = make_chalkboard_bg_texts()
    guides = make_region_guides(show_labels=True)
    problem_text = build_suneung_2_problem()
    explain_graph = build_suneung_2_tangent_graph()
    explain_bottom = build_suneung_2_explain_bottom()
    return VGroup(bg, guides, problem_text, explain_graph, explain_bottom)


class LayoutStaticScene(Scene):
    """애니메이션 없이 즉시 PNG로 뽑는 정적 레이아웃 씬 (미리보기용)."""

    def construct(self):
        self.camera.background_color = "#0A1630"
        self.add(_build_layout_content())


class LayoutPreviewScene(Scene):
    """레이아웃 + 그래프 단계별 애니메이션 씬."""

    def construct(self):
        bg = make_chalkboard_background(self)
        guides = make_region_guides(show_labels=True)
        problem_text = build_suneung_2_problem()
        graph_parts = build_suneung_2_graph_parts()
        explain_bottom = build_suneung_2_explain_bottom()

        self.add(bg)

        # 1) 영역·문제·해설 수식
        self.play(FadeIn(guides), run_time=0.6)
        self.play(FadeIn(problem_text), run_time=0.6)
        self.play(Write(explain_bottom[0]), run_time=0.3)
        self.play(
            Write(explain_bottom[1]),
            Write(explain_bottom[2]),
            run_time=0.8,
        )

        # 2) 그래프: 좌표평면 → 함수 → 접선
        animate_suneung_2_graph(self, graph_parts)

        # 3) 미분계수 정의
        self.play(Write(explain_bottom[3]), run_time=0.6)
        self.wait(1.5)
