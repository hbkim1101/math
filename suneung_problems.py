"""수능 문제 데이터 (Manim 레이아웃용)."""

from manim import *
from layout_config import (
    LayoutRegions,
    explain_right_box,
    place_in_problem,
    place_in_explain_bottom,
)


def suneung2_f(x):
    """2025 수능 2번: f(x) = x³ - 8x + 7"""
    return x**3 - 8 * x + 7


def suneung2_df(x):
    """f'(x) = 3x² - 8"""
    return 3 * x**2 - 8


A = 2  # 미분점 x = 2


def build_suneung_2_problem():
    """2025학년도 수능 수학 공통 2번 — 미분계수의 정의."""
    problem = VGroup(
        Text("2025 수능 2번", font_size=20, color=TEAL_A, weight=BOLD),
        MathTex(r"f(x) = x^3 - 8x + 7", color=WHITE).scale(0.78),
        MathTex(
            r"\lim_{h \to 0} \frac{f(2+h) - f(2)}{h}",
            color=WHITE,
        ).scale(0.72),
        Text("의 값을 구하시오.  [2점]", font_size=15, color=GREY_B),
    ).arrange(DOWN, buff=0.16, aligned_edge=LEFT)
    place_in_problem(problem)
    return problem


def build_suneung_2_graph_parts():
    """그래프 요소를 애니메이션 단계별로 분리해서 반환."""
    box = explain_right_box()
    fa = suneung2_f(A)
    slope = suneung2_df(A)

    axes = Axes(
        x_range=[-2, 3.5, 1],
        y_range=[-6, 14, 4],
        x_length=box["width"] - 1.8,
        y_length=box["height"] - 2.4,
        tips=False,
        axis_config={"color": GREY_B, "stroke_width": 1.5},
    )
    axes.move_to(box["center"] + DOWN * 0.15)

    graph = axes.plot(
        suneung2_f,
        x_range=[-1.8, 3.2],
        color=RED_C,
        stroke_width=2.5,
    )

    tangent = axes.plot(
        lambda x: fa + slope * (x - A),
        x_range=[-0.5, 3.0],
        color=GREEN_C,
        stroke_width=2.5,
    )

    point = Dot(axes.c2p(A, fa), radius=0.055, color=YELLOW)
    x_dash = DashedLine(
        axes.c2p(A, 0),
        axes.c2p(A, fa),
        color=YELLOW_E,
        dash_length=0.06,
        dashed_ratio=0.55,
        stroke_width=1.5,
    )

    x_label = MathTex("2", color=YELLOW_E).scale(0.48)
    x_label.next_to(axes.c2p(A, 0), DOWN, buff=0.06)

    point_label = MathTex(r"(2,\,-1)", color=YELLOW_E).scale(0.45)
    point_label.next_to(point, UR, buff=0.08)

    tangent_label = VGroup(
        Text("접선 기울기", font_size=14, color=GREEN_C),
        MathTex(r"f'(2)=?", color=GREEN_C).scale(0.55),
    ).arrange(RIGHT, buff=0.08)
    tangent_label.next_to(axes.c2p(2.8, fa + slope * 0.8), UP, buff=0.05)

    tangent_label_final = VGroup(
        Text("접선 기울기", font_size=14, color=GREEN_C),
        MathTex(r"f'(2)=4", color=GREEN_C).scale(0.55),
    ).arrange(RIGHT, buff=0.08)
    tangent_label_final.move_to(tangent_label)

    annotations = VGroup(
        x_dash, point, x_label, point_label, tangent_label
    )

    return {
        "axes": axes,
        "graph": graph,
        "tangent": tangent,
        "annotations": annotations,
        "tangent_label": tangent_label,
        "tangent_label_final": tangent_label_final,
    }


def build_suneung_2_tangent_graph():
    """f(x) 그래프 + 접선 (정적 PNG용 — 전체 묶음)."""
    parts = build_suneung_2_graph_parts()
    static_annotations = VGroup(
        parts["annotations"][0],  # x_dash
        parts["annotations"][1],  # point
        parts["annotations"][2],  # x_label
        parts["annotations"][3],  # point_label
        parts["tangent_label_final"],
    )
    return VGroup(
        parts["axes"],
        parts["graph"],
        parts["tangent"],
        static_annotations,
    )


def _explain_bottom_anchor():
    """좌하단 해설 영역 중심."""
    box = RoundedRectangle(
        width=LayoutRegions.PROBLEM_W,
        height=LayoutRegions.EXPLAIN_BOTTOM_H,
        corner_radius=0.12,
    ).move_to(LayoutRegions.explain_bottom_center)
    return box.get_center() + UP * 0.05


def build_suneung_2_explain_header():
    """해설 제목 + 극한식 = f'(2)."""
    anchor = _explain_bottom_anchor()
    title = Text("해설", font_size=18, color=WHITE, weight=BOLD)
    limit_eq = MathTex(
        r"\lim_{h \to 0} \frac{f(2+h) - f(2)}{h} = f'(2)",
        color=WHITE,
    ).scale(0.58)
    header = VGroup(title, limit_eq).arrange(DOWN, buff=0.1, aligned_edge=LEFT)
    header.move_to(anchor + UP * 1.05)
    header.set_max_width(LayoutRegions.PROBLEM_W - 0.9)
    return header


def build_suneung_2_deriv_substitution_steps():
    """f'(x) → x=2 대입 → f'(2)=4 단계별 수식 (같은 위치에 겹침)."""
    anchor = _explain_bottom_anchor()
    line_y = anchor + DOWN * 0.15

    # x를 isolate해서 대입 전후 Transform
    step_x = MathTex(
        r"f'(x)", r"=", r"3", r"x", r"^2", r"-", r"8",
        substrings_to_isolate=[r"x"],
        color=WHITE,
    ).scale(0.58).move_to(line_y)

    step_sub = MathTex(
        r"f'(2)", r"=", r"3", r"\cdot", r"2", r"^2", r"-", r"8",
        color=WHITE,
    ).scale(0.58).move_to(line_y)

    step_calc = MathTex(
        r"f'(2)", r"=", r"12", r"-", r"8",
        color=WHITE,
    ).scale(0.58).move_to(line_y)

    step_final = MathTex(
        r"f'(2)", r"=", r"4",
        color=YELLOW_E,
    ).scale(0.62).move_to(line_y)

    return {
        "step_x": step_x,
        "step_sub": step_sub,
        "step_calc": step_calc,
        "step_final": step_final,
    }


def build_suneung_2_explain_definition():
    """미분계수 정의 (마지막에 등장)."""
    anchor = _explain_bottom_anchor()
    definition = MathTex(
        r"f'(a) = \lim_{h \to 0} \frac{f(a+h) - f(a)}{h}",
        color=GREY_B,
    ).scale(0.52)
    definition.move_to(anchor + DOWN * 1.05)
    definition.set_max_width(LayoutRegions.PROBLEM_W - 0.9)
    return definition


def build_suneung_2_explain_bottom():
    """좌하단 해설 수식 (정적 PNG용 — 최종 상태)."""
    header = build_suneung_2_explain_header()
    final_line = build_suneung_2_deriv_substitution_steps()["step_final"]
    final_line.set_color(WHITE)
    final_deriv = MathTex(
        r"f'(x)=3x^2-8 \;\Rightarrow\; f'(2)=4",
        color=YELLOW_E,
    ).scale(0.55).move_to(final_line.get_center())
    definition = build_suneung_2_explain_definition()
    return VGroup(header, final_deriv, definition)


def animate_suneung_2_deriv_substitution(scene, steps, graph_parts=None):
    """f'(x)에 x=2를 대입하는 애니메이션."""
    step_x = steps["step_x"]
    step_sub = steps["step_sub"]
    step_calc = steps["step_calc"]
    step_final = steps["step_final"]

    scene.play(Write(step_x), run_time=0.8)

    x_part = step_x.get_part_by_tex("x")
    scene.play(Indicate(x_part, color=YELLOW, scale_factor=1.8), run_time=0.6)

    scene.play(
        TransformMatchingTex(step_x, step_sub, key_map={r"x": r"2"}),
        run_time=1.0,
    )

    scene.play(
        TransformMatchingTex(step_sub, step_calc),
        run_time=0.9,
    )

    scene.play(
        TransformMatchingTex(step_calc, step_final),
        run_time=0.7,
    )

    if graph_parts is not None:
        scene.play(
            Transform(
                graph_parts["tangent_label"],
                graph_parts["tangent_label_final"],
            ),
            run_time=0.5,
        )
        graph_parts["tangent_label"] = graph_parts["tangent_label_final"]


def build_suneung_2_explanation():
    """2025 수능 2번 해설 — 그래프(우측) + 수식(좌하단)."""
    return build_suneung_2_tangent_graph(), build_suneung_2_explain_bottom()


def animate_suneung_2_graph(scene, parts, axes_run=1.0, graph_run=1.8, tangent_run=1.2):
    """좌표평면 → 함수 → 접선 순서로 그래프 애니메이션."""
    scene.play(Create(parts["axes"]), run_time=axes_run)
    scene.play(Create(parts["graph"]), run_time=graph_run)
    scene.play(
        Create(parts["tangent"]),
        FadeIn(parts["annotations"]),
        run_time=tangent_run,
    )
