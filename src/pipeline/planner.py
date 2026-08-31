from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path

from src.dsl.models import ExamSet, Problem, Step
from src.dsl.visual import VisualAction, VisualConfig


def infer_visual_config(problem: Problem) -> VisualConfig:
    """Topic/steps 기반 시각화 템플릿 자동 추론."""
    topic = problem.topic.lower()
    q = problem.question_latex

    if "미분계수" in topic or "미분" in topic:
        expr = _extract_polynomial(q) or "3*x**3 + 7*x + 1"
        return VisualConfig(
            template="derivative_tangent",
            expr=expr,
            tangent_at=1.0,
            x_range=[-1.5, 1.5],
            y_range=[-5, 15],
        )

    if "연속" in topic:
        return VisualConfig(
            template="piecewise_continuity",
            expr="x**2 - 3*x + a",
            expr_right="3*x - 2",
            breakpoint=1.0,
            param_name="a",
            param_from=0.0,
            param_to=3.0,
            x_range=[-0.5, 2.5],
            y_range=[-3, 5],
        )

    if "역함수" in topic or "교점" in topic:
        return VisualConfig(template="custom", x_range=[-3, 3], y_range=[-3, 4])

    return VisualConfig(template="equation_flow", x_range=[-2, 2], y_range=[-2, 2])


def build_step_visuals(problem: Problem, config: VisualConfig) -> list[Step]:
    """각 step에 caption + visual actions 부여."""
    steps = copy.deepcopy(problem.steps)
    template = config.template

    for i, step in enumerate(steps):
        step.caption = step.caption or step.narration
        if step.visual:
            continue

        if template == "derivative_tangent":
            step.visual = _derivative_step_actions(i, config)
        elif template == "piecewise_continuity":
            step.visual = _continuity_step_actions(i, config)
        elif template == "equation_flow":
            step.visual = _equation_step_actions(i, step)
        else:
            step.visual = [
                VisualAction(action="caption", label=step.caption),
                VisualAction(action="show_equation", label=step.latex, color="HIGHLIGHT"),
            ]

    return steps


def enrich_problem(problem: Problem) -> Problem:
    config = problem.visual or infer_visual_config(problem)
    steps = build_step_visuals(problem, config)
    return problem.model_copy(update={"visual": config, "steps": steps})


def enrich_exam(exam: ExamSet) -> ExamSet:
    return exam.model_copy(
        update={"problems": [enrich_problem(p) for p in exam.problems]}
    )


def _derivative_step_actions(index: int, config: VisualConfig) -> list[VisualAction]:
    expr = config.expr or "3*x**3 + 7*x + 1"
    x0 = config.tangent_at or 1.0
    actions: list[VisualAction] = []

    if index == 0:
        actions = [
            VisualAction(action="caption", label="f'(x) = x에서 접선 기울기"),
            VisualAction(action="plot", expr=expr, color="BLUE", x_range=config.x_range),
        ]
    elif index == 1:
        actions = [
            VisualAction(action="caption", label="미분하면 기울기 함수가 나옵니다"),
            VisualAction(action="show_equation", label=r"f'(x)=9x^2+7", color="HIGHLIGHT"),
        ]
    elif index == 2:
        actions = [
            VisualAction(action="caption", label=f"x={x0:g}에서 접선 기울기"),
            VisualAction(action="tangent_at", expr=expr, x=x0, color="YELLOW"),
            VisualAction(action="show_equation", label=rf"f'({x0:g})=16", color="ANSWER"),
        ]
    else:
        actions = [
            VisualAction(action="caption", label="정답 확인"),
            VisualAction(action="show_equation", label=rf"f'({x0:g})=16", color="ANSWER"),
        ]
    return actions


def _continuity_step_actions(index: int, config: VisualConfig) -> list[VisualAction]:
    bp = config.breakpoint
    if index == 0:
        return [
            VisualAction(action="caption", label=f"x={bp:g}에서 좌·우극한 = 함수값"),
            VisualAction(
                action="plot_piecewise",
                param=config.param_name,
                from_value=config.param_from,
                to_value=config.param_from,
            ),
        ]
    if index == 1:
        return [
            VisualAction(action="caption", label="좌극한 계산"),
            VisualAction(action="show_equation", label=rf"\lim_{{x\to {bp:g}^-}} f(x)=a-2", color="HIGHLIGHT"),
        ]
    if index == 2:
        return [
            VisualAction(action="caption", label="우극한 = f(1)"),
            VisualAction(action="show_equation", label=rf"f({bp:g})=1", color="HIGHLIGHT"),
        ]
    if index == 3:
        return [
            VisualAction(action="caption", label="a=3이면 x=1에서 연속!"),
            VisualAction(
                action="plot_piecewise",
                param=config.param_name,
                from_value=config.param_from,
                to_value=config.param_to,
            ),
            VisualAction(action="show_equation", label=r"a=3", color="ANSWER"),
        ]
    return [VisualAction(action="caption", label="정답")]


def _equation_step_actions(index: int, step: Step) -> list[VisualAction]:
    return [
        VisualAction(action="caption", label=step.caption or step.narration),
        VisualAction(action="show_equation", label=step.latex, color="HIGHLIGHT" if index < 3 else "ANSWER"),
    ]


def _extract_polynomial(text: str) -> str | None:
    m = re.search(r"f\s*\(\s*x\s*\)\s*=\s*(.+)", text, re.IGNORECASE)
    if not m:
        return None
    raw = m.group(1).strip()
    raw = raw.replace("^", "**")
    raw = re.sub(r"(\d)(x)", r"\1*\2", raw)
    raw = re.sub(r"\)(x)", r")*\1", raw)
    return raw


def write_timing_manifest(path: Path, durations: list[float], audio_files: list[Path]) -> None:
    payload = {
        "steps": [
            {"index": i, "duration": d, "audio": str(p)}
            for i, (d, p) in enumerate(zip(durations, audio_files))
        ]
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_timing_manifest(path: Path) -> dict:
    if not path.exists():
        return {"steps": []}
    return json.loads(path.read_text(encoding="utf-8"))


def step_duration(manifest: dict, index: int, default: float = 2.5) -> float:
    for item in manifest.get("steps", []):
        if item.get("index") == index:
            return float(item.get("duration", default))
    return default


def env_problem_path() -> Path | None:
    raw = os.environ.get("MATH_VIZ_EXAM_PATH")
    return Path(raw) if raw else None


def env_problem_id() -> int | None:
    raw = os.environ.get("MATH_VIZ_PROBLEM_ID")
    return int(raw) if raw else None


def env_timing_path() -> Path | None:
    raw = os.environ.get("MATH_VIZ_TIMING")
    return Path(raw) if raw else None
