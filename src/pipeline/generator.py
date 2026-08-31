from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from src.dsl.models import ExamSet, Problem, Step, save_exam
from src.pipeline.planner import enrich_problem


SYSTEM_PROMPT = """당신은 '수학 한수' 스타일 수능 수학 해설 작가입니다.
- 텍스트 슬라이드가 아닌, 그래프·기하 직관 중심으로 설명합니다.
- 각 step은 narration(한국어 구어체, 1~2문장)과 latex(핵심 수식)를 포함합니다.
- 마지막 step에서 정답을 명확히 제시합니다.
JSON만 출력하세요."""


def generate_solution_yaml(problem_text: str, *, topic: str = "수학", points: int = 3) -> Problem:
    """LLM 또는 규칙 기반으로 Problem steps 생성."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            return _generate_with_openai(problem_text, topic=topic, points=points)
        except Exception:
            pass
    return _generate_rule_based(problem_text, topic=topic, points=points)


def _generate_with_openai(problem_text: str, *, topic: str, points: int) -> Problem:
    from openai import OpenAI

    client = OpenAI()
    user = f"""다음 수학 문제를 풀어 steps를 JSON으로 작성하세요.

문제:
{problem_text}

형식:
{{
  "topic": "{topic}",
  "question_latex": "...",
  "answer": "...",
  "answer_value": 0,
  "steps": [{{"narration": "...", "latex": "..."}}]
}}
"""
    resp = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    data = json.loads(resp.choices[0].message.content or "{}")
    return Problem(
        id=0,
        topic=data.get("topic", topic),
        points=points,
        question_latex=data.get("question_latex", problem_text),
        answer=str(data.get("answer", "?")),
        answer_value=data.get("answer_value", 0),
        steps=[Step(**s) for s in data.get("steps", [])],
    )


def _generate_rule_based(problem_text: str, *, topic: str, points: int) -> Problem:
    """API 키 없을 때 기본 step 템플릿."""
    steps = [
        Step(narration="문제 조건을 정리합니다.", latex=_guess_latex(problem_text)),
        Step(narration="핵심 아이디어를 적용합니다.", latex=r"\Rightarrow \cdots"),
        Step(narration="계산을 마무리합니다.", latex=r"=\,?"),
        Step(narration="따라서 정답을 확인합니다.", latex=r"\text{정답}"),
    ]
    return Problem(
        id=0,
        topic=topic,
        points=points,
        question_latex=_guess_latex(problem_text),
        answer="?",
        answer_value=0,
        steps=steps,
    )


def _guess_latex(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if "=" in cleaned:
        return cleaned.replace("*", r" \cdot ")
    return cleaned


def problem_from_image(image_path: str, *, topic: str = "수학") -> Problem:
    """OCR placeholder — pytesseract/easyocr 확장 지점."""
    raw = os.environ.get("MATH_VIZ_OCR_TEXT")
    if not raw and os.path.isfile(image_path):
        raw = f"[이미지 문제: {Path(image_path).name}]"
    if not raw:
        raw = "f(x) = 3x^3 + 7x + 1"
    return generate_solution_yaml(raw, topic=topic)


def build_exam_from_problem(problem: Problem, exam_meta: dict[str, Any] | None = None) -> ExamSet:
    meta = exam_meta or {}
    enriched = enrich_problem(problem)
    return ExamSet(
        exam=meta.get("exam", "자동 생성"),
        section=meta.get("section", "수학"),
        source=meta.get("source", "math-viz pipeline"),
        problems=[enriched],
    )


def export_problem_yaml(problem: Problem, path: str, exam_meta: dict[str, Any] | None = None) -> None:
    exam = build_exam_from_problem(problem, exam_meta)
    save_exam(exam, path)

