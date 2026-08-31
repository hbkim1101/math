from __future__ import annotations

from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator


def clean_latex(value: str) -> str:
    text = value.strip()
    if len(text) >= 3 and text.startswith('r"') and text.endswith('"'):
        return text[2:-1]
    if len(text) >= 3 and text.startswith("r'") and text.endswith("'"):
        return text[2:-1]
    return text


AnnotateKind = Literal["dot", "hline", "vline", "arrow", "brace_y", "label", "pulse_dot"]


class AnnotateAction(BaseModel):
    """그래프 위 손풀이式 주석."""

    action: AnnotateKind
    at: list[float] | None = None
    x: float | None = None
    y: float | None = None
    y0: float | None = None
    y1: float | None = None
    from_pt: list[float] | None = Field(default=None, alias="from")
    to: list[float] | None = None
    color: str = "YELLOW"
    label: str | None = None
    say: str | None = None  # 이 주석 TTS

    model_config = {"populate_by_name": True}


class VisualSpec(BaseModel):
    type: str = "none"
    graph: str | None = None
    params: dict[str, float | str] = Field(default_factory=dict)
    annotate: list[AnnotateAction] = Field(default_factory=list)


class CaseBranch(BaseModel):
    name: str
    flow: list[FlowNode] = Field(default_factory=list)


class FlowNode(BaseModel):
    link: str = "therefore"
    say: str = ""
    math: str | None = None
    caption: str | None = None
    visual: VisualSpec | None = None
    annotate: list[AnnotateAction] = Field(default_factory=list)
    cases: list[CaseBranch] = Field(default_factory=list)

    @field_validator("math", mode="before")
    @classmethod
    def normalize_math(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return clean_latex(value)


CaseBranch.model_rebuild()
FlowNode.model_rebuild()


class SolutionScript(BaseModel):
    id: int
    exam: str = "2026학년도 수능"
    section: str = "수학"
    topic: str
    brand: str = "수학 한수"
    question_lines: list[str] = Field(default_factory=list)
    answer: str
    intro: str | None = None
    outro: str | None = None
    flow: list[FlowNode]


def load_solution(path: str) -> SolutionScript:
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    return SolutionScript.model_validate(data)
