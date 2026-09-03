"""수능 문제 데이터 — manim_kit + DSL 입력 사용 예시."""

from manim import *
from layout_config import LayoutRegions, place_in_problem
from manim_kit import (
    GraphSpec,
    build_graph_parts,
    animate_graph,
    graph_group,
    build_substitution_steps,
    animate_substitution,
    tex,
)
from manim_kit.input_parser import (
    parse_input,
    substitution_spec_from_input,
    SUNEUNG_2_INPUT,
)

A = 2


def suneung2_f(x):
    return x**3 - 8 * x + 7


def suneung2_df(x):
    return 3 * x**2 - 8


def _explain_bottom_anchor():
    box = RoundedRectangle(
        width=LayoutRegions.PROBLEM_W,
        height=LayoutRegions.EXPLAIN_BOTTOM_H,
        corner_radius=0.12,
    ).move_to(LayoutRegions.explain_bottom_center)
    return box.get_center() + UP * 0.05


def build_suneung_2_problem():
    parsed = parse_input(SUNEUNG_2_INPUT)
    problem = VGroup(
        Text("2025 수능 2번", font_size=20, color=TEAL_A, weight=BOLD),
        tex(r"f(x) = x^3 - 8x + 7", scale=0.78),
        tex(parsed.problem_latex, scale=0.72),
        Text("의 값을 구하시오.  [2점]", font_size=15, color=GREY_B),
    ).arrange(DOWN, buff=0.16, aligned_edge=LEFT)
    place_in_problem(problem)
    return problem


def suneung_2_graph_spec() -> GraphSpec:
    return GraphSpec(
        f=suneung2_f,
        x_range=(-2, 3.5, 1),
        y_range=(-6, 14, 4),
        plot_x_range=(-1.8, 3.2),
        tangent_at=A,
        slope_fn=suneung2_df,
        tangent_x_range=(-0.5, 3.0),
        x_label_latex="2",
        point_label_latex=r"(2,\,-1)",
        tangent_label_pending_latex=r"f'(2)=?",
        tangent_label_final_latex=r"f'(2)=4",
    )


def suneung_2_substitution_spec():
    return substitution_spec_from_input(
        SUNEUNG_2_INPUT,
        _explain_bottom_anchor() + DOWN * 0.15,
    )


def build_suneung_2_graph_parts():
    return build_graph_parts(suneung_2_graph_spec())


def build_suneung_2_tangent_graph():
    return graph_group(build_suneung_2_graph_parts(), use_final_label=True)


def build_suneung_2_explain_header():
    parsed = parse_input(SUNEUNG_2_INPUT)
    anchor = _explain_bottom_anchor()
    header = VGroup(
        Text("해설", font_size=18, color=WHITE, weight=BOLD),
        tex(parsed.problem_latex, scale=0.58),
    ).arrange(DOWN, buff=0.1, aligned_edge=LEFT)
    header.move_to(anchor + UP * 1.05)
    header.set_max_width(LayoutRegions.PROBLEM_W - 0.9)
    return header


def build_suneung_2_explain_definition():
    anchor = _explain_bottom_anchor()
    definition = tex(
        r"f'(a) = \lim_{h \to 0} \frac{f(a+h) - f(a)}{h}",
        scale=0.52,
        color=GREY_B,
    )
    definition.move_to(anchor + DOWN * 1.05)
    definition.set_max_width(LayoutRegions.PROBLEM_W - 0.9)
    return definition


def build_suneung_2_deriv_substitution_steps():
    spec = suneung_2_substitution_spec()
    steps = build_substitution_steps(spec)
    steps["_highlight"] = spec.highlight
    return steps


def build_suneung_2_explain_bottom():
    parsed = parse_input(SUNEUNG_2_INPUT)
    header = build_suneung_2_explain_header()
    final_step = parsed.substitution_steps[-1] if parsed.substitution_steps else "f'(2)=4"
    final = tex(final_step, scale=0.55, color=YELLOW_E)
    final.move_to(_explain_bottom_anchor() + DOWN * 0.15)
    return VGroup(header, final, build_suneung_2_explain_definition())


def animate_suneung_2_graph(scene, parts, **kwargs):
    animate_graph(scene, parts, **kwargs)


def animate_suneung_2_deriv_substitution(scene, steps, graph_parts=None):
    animate_substitution(scene, steps, graph_parts=graph_parts)
