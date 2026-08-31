from __future__ import annotations

from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


def clean_latex(value: str) -> str:
    text = value.strip()
    if len(text) >= 3 and text.startswith('r"') and text.endswith('"'):
        return text[2:-1]
    if len(text) >= 3 and text.startswith("r'") and text.endswith("'"):
        return text[2:-1]
    return text


class VisualSpec(BaseModel):
    type: str = "none"
    graph: str | None = None
    params: dict[str, float | str] = Field(default_factory=dict)


class CaseBranch(BaseModel):
    name: str
    flow: list[FlowNode] = Field(default_factory=list)


class FlowNode(BaseModel):
    link: str = "therefore"
    say: str = ""
    math: str | None = None
    caption: str | None = None
    visual: VisualSpec | None = None
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


def flatten_narrations(script: SolutionScript) -> list[tuple[str, str, str]]:
    """TTS: (say, link, caption)."""
    lines: list[tuple[str, str, str]] = []

    if script.intro:
        lines.append((script.intro, "therefore", "시작"))

    def walk(nodes: list[FlowNode], case_name: str = "") -> None:
        for node in nodes:
            cap = node.caption or (node.say[:36] + "…" if len(node.say) > 36 else node.say)
            say = node.say
            if case_name:
                say = f"{case_name}에서, {say}"

            if node.link == "when" and node.cases:
                lines.append((f"만약, {say}", "when", cap))
                for case in node.cases:
                    walk(case.flow, case.name)
            else:
                prefix = "만약, " if node.link == "when" else ""
                lines.append((prefix + say, node.link, cap))

    walk(script.flow)

    if script.outro:
        lines.append((script.outro, "therefore", "마무리"))
    return lines
