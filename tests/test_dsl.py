import math
from pathlib import Path

import pytest

from explainer.script.loader import ExpressionError, load_project, make_function, resolve_params, safe_eval
from explainer.script.models import Action, Project

ROOT = Path(__file__).resolve().parents[1]


def test_safe_eval_arithmetic_and_functions():
    assert safe_eval("3/4") == 0.75
    assert safe_eval("(81/16)**(1/3)") == pytest.approx(1.71713, rel=1e-4)
    assert safe_eval("log(8)/log(2)") == pytest.approx(3.0)
    assert safe_eval("sqrt(16) + abs(-2)") == 6.0
    assert safe_eval("x*2", {"x": 5}) == 10


@pytest.mark.parametrize("bad", ["__import__('os')", "open('x')", "x.y", "lambda: 1", "[1][0]", "'s'"])
def test_safe_eval_rejects_unsafe(bad):
    with pytest.raises(ExpressionError):
        safe_eval(bad, {"x": 1})


def test_make_function_and_params_chain():
    params = resolve_params({"a": "(81/16)**(1/3)", "b": "a*2"})
    assert params["b"] == pytest.approx(params["a"] * 2)
    f = make_function("a**x", params)
    assert f(0.75) == pytest.approx(1.5, rel=1e-6)
    assert f(1.5) == pytest.approx(2.25, rel=1e-6)


def test_action_params_and_extra_fields():
    act = Action(do="plot", id="f", expr="x**2", color="q1", at="s2", run_time=1.5)
    p = act.params
    assert p["id"] == "f" and p["expr"] == "x**2" and p["color"] == "q1"
    assert "do" not in p and "at" not in p and "run_time" not in p


def test_project_requires_unique_segment_ids():
    data = {
        "meta": {"id": "t", "title": "t"},
        "segments": [{"id": "a", "narration": "x"}, {"id": "a", "narration": "y"}],
    }
    with pytest.raises(ValueError):
        Project.model_validate(data)


def test_demo_project_loads_and_actions_known():
    from explainer.render.actions import REGISTRY

    proj = load_project(ROOT / "projects/2027_sep_q22/project.yaml")
    assert proj.meta.id == "2027_sep_q22"
    assert len(proj.segments) >= 10
    used = {a.do for s in proj.segments for a in s.actions}
    assert used <= set(REGISTRY), used - set(REGISTRY)
    # 모든 세그먼트에 내레이션이 있어야 한다
    assert all(s.narration for s in proj.segments)
