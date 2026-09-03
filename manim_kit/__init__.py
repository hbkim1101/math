"""
Manim 재사용 도구 모음.

LaTeX 문자열 → MathTex 표시, Python 함수 → 곡선 그리기.
"""

from manim_kit.graph import GraphSpec, build_graph_parts, animate_graph, graph_group
from manim_kit.substitution import (
    SubstitutionSpec,
    build_substitution_steps,
    animate_substitution,
    build_and_animate_substitution,
)
from manim_kit.latex import tex, tex_block
from manim_kit.input_parser import (
    parse_dsl,
    dsl_to_latex,
    substitution_spec_from_dsl,
    ParsedProblem,
    SUNEUNG_2_DSL,
)

__all__ = [
    "GraphSpec",
    "build_graph_parts",
    "animate_graph",
    "graph_group",
    "SubstitutionSpec",
    "build_substitution_steps",
    "animate_substitution",
    "build_and_animate_substitution",
    "tex",
    "tex_block",
    "parse_dsl",
    "dsl_to_latex",
    "substitution_spec_from_dsl",
    "ParsedProblem",
    "SUNEUNG_2_DSL",
]
