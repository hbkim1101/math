#!/usr/bin/env python3
"""Generate Lecture DSL YAML from problem text + solution notes via OpenAI."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from textwrap import dedent

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]

SYSTEM_PROMPT = dedent("""
    You are a Korean high-school math teacher writing a Manim lecture script.
    Output ONLY valid JSON (no markdown fences) with this shape:

    {
      "slug": "exam_qNN",
      "header": {"title": "...", "subtitle": "..."},
      "steps": [ ... ]
    }

    Each step is one of:
    - narrate: {"type":"narrate", "text":"short on-screen subtitle", "speech":"long natural Korean TTS script"}
    - problem: {"type":"problem"}
    - latex: {"type":"latex", "content":"LaTeX only, no Korean", "stack": false}
    - latex_block: {"type":"latex_block", "items":["..."], "colors":["purple","yellow","white"]}
    - graph: {"type":"graph", "axes":{"x_range":[-3,3,1],"y_range":[-2,2,1]}, "curves":[{"preset":"g_y5_y3","x_plot":[-1.4,1.4],"color":"purple","label_latex":"..."}], "dots":[...], "tangents":[...]}
    - number_line: {"type":"number_line", "x_range":[-3.5,3.5,1], "markers":[{"x":0,"label_latex":"f(c)=0","color":"yellow"}]}
    - clear: {"type":"clear"}
    - fade_out: {"type":"fade_out", "target":"board"}
    - answer: {"type":"answer", "latex":"...", "label":"정답"}
    - wait: {"type":"wait", "seconds": 1.0}
    - section: {"type":"section", "title":"...", "subtitle":""}

    Rules:
    - Target audience: 고2. Explain WHY, not just answers. Pacing: graph/idea first, then algebra.
    - narrate.text = short subtitle; narrate.speech = longer spoken Korean (no LaTeX in speech).
    - LaTeX strings use single quotes in YAML later; escape backslashes properly in JSON.
    - graph preset names: g_y5_y3, june28_ln, june28_k (or describe curves if unknown).
    - Do not skip key visual steps (problem card, graphs, number_line when applicable).
    - 15–25 narrate steps for a 4-point calculus problem.
    - Korean in narrate; math only in latex/graph fields.
    """).strip()


def build_user_prompt(
    *,
    exam: str,
    problem_id: int,
    topic: str,
    question: str,
    conditions: str,
    choices: str,
    answer: str,
    notes: str,
) -> str:
    parts = [
        f"exam: {exam}",
        f"problem_id: {problem_id}",
        f"topic: {topic}",
        f"question_latex: {question}",
    ]
    if conditions:
        parts.append(f"conditions: {conditions}")
    if choices:
        parts.append(f"choices: {choices}")
    if answer:
        parts.append(f"answer: {answer}")
    if notes:
        parts.append(f"solution_notes:\n{notes}")
    parts.append("\nGenerate the lecture.steps JSON for this problem.")
    return "\n".join(parts)


def call_openai(system: str, user: str, *, model: str, api_key: str) -> dict:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return json.loads(content)


def assemble_exam_yaml(
    *,
    exam_meta: dict,
    problem_id: int,
    topic: str,
    question_latex: str,
    question_note: str,
    choices: list[str],
    answer: str,
    lecture: dict,
    tts: dict | None,
) -> dict:
    problem: dict = {
        "id": problem_id,
        "topic": topic,
        "question_latex": question_latex,
        "answer": answer,
        "lecture": {
            "slug": lecture.get("slug", f"q{problem_id}"),
            "header": lecture.get("header", {"title": f"{exam_meta.get('exam', '')} {problem_id}번", "subtitle": ""}),
            "steps": lecture["steps"],
        },
    }
    if question_note:
        problem["question_note"] = question_note
    if choices:
        problem["choices"] = choices
    if tts:
        problem["lecture"]["tts"] = tts

    return {
        "exam": exam_meta.get("exam", ""),
        "section": exam_meta.get("section", ""),
        "source": exam_meta.get("source", ""),
        "problems": [problem],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-generate Lecture DSL YAML")
    parser.add_argument("--exam", default="2026학년도 수능")
    parser.add_argument("--section", default="")
    parser.add_argument("--source", default="")
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--question", required=True, help="Main question LaTeX")
    parser.add_argument("--conditions", default="", help="Extra conditions (LaTeX/text)")
    parser.add_argument("--choices", default="", help="Comma-separated choice strings")
    parser.add_argument("--answer", default="")
    parser.add_argument("--notes", default="", help="Solution outline or full solution")
    parser.add_argument("--notes-file", type=Path, help="Read solution notes from file")
    parser.add_argument("-o", "--output", type=Path, required=True)
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-4o"))
    parser.add_argument("--dry-run", action="store_true", help="Print prompt only, no API call")
    args = parser.parse_args()

    notes = args.notes
    if args.notes_file:
        notes = args.notes_file.read_text(encoding="utf-8")

    user_prompt = build_user_prompt(
        exam=args.exam,
        problem_id=args.id,
        topic=args.topic,
        question=args.question,
        conditions=args.conditions,
        choices=args.choices,
        answer=args.answer,
        notes=notes,
    )

    if args.dry_run:
        print("=== SYSTEM ===")
        print(SYSTEM_PROMPT)
        print("\n=== USER ===")
        print(user_prompt)
        return

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is not set.", file=sys.stderr)
        print("Set the key and retry, or use --dry-run to inspect the prompt.", file=sys.stderr)
        sys.exit(1)

    print(f"Calling OpenAI ({args.model}) for problem {args.id}…")
    lecture = call_openai(SYSTEM_PROMPT, user_prompt, model=args.model, api_key=api_key)

    choices_list = [c.strip() for c in args.choices.split(",") if c.strip()] if args.choices else []
    doc = assemble_exam_yaml(
        exam_meta={"exam": args.exam, "section": args.section, "source": args.source},
        problem_id=args.id,
        topic=args.topic,
        question_latex=args.question,
        question_note=args.conditions,
        choices=choices_list,
        answer=args.answer,
        lecture=lecture,
        tts={"provider": "edge", "voice": "ko-KR-SunHiNeural", "rate": "-16%", "pause_ms": 480},
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    header = "# Auto-generated lecture YAML — review before render\n"
    body = yaml.dump(
        doc,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=100,
    )
    args.output.write_text(header + body, encoding="utf-8")
    print(f"Wrote {args.output} ({len(lecture.get('steps', []))} steps)")


if __name__ == "__main__":
    main()
