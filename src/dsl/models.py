from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class Step(BaseModel):
    narration: str
    latex: str


class Problem(BaseModel):
    id: int
    topic: str
    points: int
    question_latex: str
    question_latex_2: str | None = None
    question_note: str | None = None
    choices: list[str]
    answer: str
    answer_value: int | float
    steps: list[Step]


class ExamSet(BaseModel):
    exam: str
    section: str
    source: str
    problems: list[Problem]


def load_exam(path: str | Path) -> ExamSet:
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    return ExamSet.model_validate(data)


def get_problem(exam: ExamSet, problem_id: int) -> Problem:
    for problem in exam.problems:
        if problem.id == problem_id:
            return problem
    raise ValueError(f"Problem {problem_id} not found")
