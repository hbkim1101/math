from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from src.dsl.visual import VisualAction, VisualConfig


def clean_latex(value: str) -> str:
    """YAML에 실수로 넣은 Python r\"...\" 접두사를 제거합니다."""
    text = value.strip()
    if len(text) >= 3 and text.startswith('r"') and text.endswith('"'):
        return text[2:-1]
    if len(text) >= 3 and text.startswith("r'") and text.endswith("'"):
        return text[2:-1]
    return text


class Step(BaseModel):
    narration: str
    latex: str
    caption: str | None = None
    visual: list[VisualAction] = Field(default_factory=list)

    @field_validator("latex", mode="before")
    @classmethod
    def normalize_latex(cls, value: str) -> str:
        return clean_latex(value)


class Problem(BaseModel):
    id: int
    topic: str
    points: int
    question_latex: str
    question_latex_2: str | None = None
    question_note: str | None = None
    question_note_2: str | None = None
    choices: list[str] = Field(default_factory=list)
    answer: str
    answer_value: int | float
    steps: list[Step]
    visual: VisualConfig | None = None

    @field_validator("question_latex", "question_latex_2", mode="before")
    @classmethod
    def normalize_question_latex(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return clean_latex(value)


class ExamSet(BaseModel):
    exam: str
    section: str
    source: str
    brand: str = "수학 한수"
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


def save_exam(exam: ExamSet, path: str | Path) -> None:
    data = exam.model_dump(mode="json", by_alias=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
