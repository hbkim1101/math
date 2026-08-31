"""Lecture DSL — YAML만으로 강의 영상 자동 생성."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, Literal, Union

import yaml
from pydantic import BaseModel, Field, field_validator

from src.dsl.models import clean_latex


class LectureHeader(BaseModel):
    title: str
    subtitle: str = ""


class AxesSpec(BaseModel):
    x_range: list[float] = Field(default_factory=lambda: [-3, 3, 1])
    y_range: list[float] = Field(default_factory=lambda: [-2, 2, 1])
    x_len: float = 7.0
    y_len: float = 4.0


class CurveSpec(BaseModel):
    preset: str
    x_plot: list[float] | None = None
    color: str = "blue"
    label_latex: str = ""


class DotSpec(BaseModel):
    x: float
    y: float | None = None  # None → preset eval at x
    preset_y: str | None = None
    color: str = "yellow"
    label_latex: str = ""


class TangentSpec(BaseModel):
    at_x: float
    preset_base: str = "june28_ln"
    color: str = "yellow"


class NarrateStep(BaseModel):
    type: Literal["narrate"] = "narrate"
    text: str
    speech: str | None = None


class TtsConfig(BaseModel):
    voice: str = "ko-KR-SunHiNeural"
    rate: str = "-14%"
    pitch: str = "-2Hz"
    pause_ms: int = 420


class SectionStep(BaseModel):
    type: Literal["section"] = "section"
    title: str
    subtitle: str = ""


class LatexStep(BaseModel):
    type: Literal["latex"] = "latex"
    content: str
    font_size: int = 28
    color: str = "white"
    stack: bool = False  # True: 이전 latex 아래에 누적

    @field_validator("content", mode="before")
    @classmethod
    def normalize(cls, value: str) -> str:
        return clean_latex(value)


class LatexBlockStep(BaseModel):
    type: Literal["latex_block"] = "latex_block"
    items: list[str]
    font_size: int = 28
    colors: list[str] = Field(default_factory=list)

    @field_validator("items", mode="before")
    @classmethod
    def normalize_items(cls, value: list[str]) -> list[str]:
        return [clean_latex(v) for v in value]


class GraphStep(BaseModel):
    type: Literal["graph"] = "graph"
    axes: AxesSpec = Field(default_factory=AxesSpec)
    curves: list[CurveSpec] = Field(default_factory=list)
    dots: list[DotSpec] = Field(default_factory=list)
    tangents: list[TangentSpec] = Field(default_factory=list)
    shift: list[float] = Field(default_factory=lambda: [0.0, 0.15])


class NumberLineMarker(BaseModel):
    x: float
    label_latex: str = ""
    color: str = "yellow"


class NumberLineStep(BaseModel):
    type: Literal["number_line"] = "number_line"
    x_range: list[float] = Field(default_factory=lambda: [-3.5, 3.5, 1])
    markers: list[NumberLineMarker] = Field(default_factory=list)


class ProblemCardStep(BaseModel):
    type: Literal["problem"] = "problem"


class AnswerStep(BaseModel):
    type: Literal["answer"] = "answer"
    latex: str
    label: str = "정답"

    @field_validator("latex", mode="before")
    @classmethod
    def normalize(cls, value: str) -> str:
        return clean_latex(value)


class ClearStep(BaseModel):
    type: Literal["clear"] = "clear"


class WaitStep(BaseModel):
    type: Literal["wait"] = "wait"
    seconds: float = 1.0


class HighlightStep(BaseModel):
    type: Literal["highlight"] = "highlight"
    target: Literal["last"] = "last"
    color: str = "yellow"


class FadeOutStep(BaseModel):
    type: Literal["fade_out"] = "fade_out"
    target: Literal["board", "all"] = "board"


LectureStep = Annotated[
    Union[
        NarrateStep,
        SectionStep,
        LatexStep,
        LatexBlockStep,
        GraphStep,
        NumberLineStep,
        ProblemCardStep,
        AnswerStep,
        ClearStep,
        WaitStep,
        HighlightStep,
        FadeOutStep,
    ],
    Field(discriminator="type"),
]


class LectureSpec(BaseModel):
    slug: str
    voice: str = "ko-KR-SunHiNeural"
    tts: TtsConfig = Field(default_factory=TtsConfig)
    background: str = "#0f0f1a"
    header: LectureHeader
    steps: list[LectureStep]


class LectureProblem(BaseModel):
    id: int
    topic: str
    points: int = 4
    question_latex: str
    question_note: str = ""
    question_latex_2: str = ""
    choices: list[str] = Field(default_factory=list)
    answer: str = ""
    answer_value: float = 0
    lecture: LectureSpec

    @field_validator("question_latex", "question_latex_2", mode="before")
    @classmethod
    def normalize_q(cls, value: str | None) -> str:
        if not value:
            return ""
        return clean_latex(value)


class LectureExam(BaseModel):
    exam: str
    section: str = ""
    source: str = ""
    problems: list[LectureProblem]


def load_lecture_exam(path: str | Path) -> LectureExam:
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    return LectureExam.model_validate(data)


def get_lecture_problem(exam: LectureExam, problem_id: int) -> LectureProblem:
    for p in exam.problems:
        if p.id == problem_id:
            return p
    raise ValueError(f"Lecture problem {problem_id} not found in {exam.exam}")


def iter_narrations(problem: LectureProblem) -> list[tuple[str, str]]:
    """(subtitle, speech) pairs for narrate steps."""
    out: list[tuple[str, str]] = []
    for s in problem.lecture.steps:
        if isinstance(s, NarrateStep):
            speech = s.speech or s.text
            out.append((s.text, speech))
    return out
