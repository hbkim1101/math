"""Basic pipeline tests."""

from __future__ import annotations

from src.dsl.models import load_exam
from src.pipeline.planner import enrich_problem, infer_visual_config
from src.renderer.expression import derivative_at, eval_expr, make_function


def test_infer_derivative_template() -> None:
    exam = load_exam("problems/2026_suneung/common.yaml")
    problem = exam.problems[1]  # id=2
    config = infer_visual_config(problem)
    assert config.template == "derivative_tangent"
    assert config.expr is not None


def test_enrich_adds_visuals() -> None:
    exam = load_exam("problems/2026_suneung/common.yaml")
    problem = enrich_problem(exam.problems[1])
    assert all(len(s.visual) > 0 for s in problem.steps)
    assert problem.visual is not None


def test_expression_eval() -> None:
    fn = make_function("3*x**3 + 7*x + 1")
    assert fn(1) == 11
    assert derivative_at("3*x**3 + 7*x + 1", 1.0) == 16
