#!/usr/bin/env python3
"""Generate TTS from Lecture DSL narrate steps."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import edge_tts

from src.dsl.lecture_models import get_lecture_problem, iter_narrations, load_lecture_exam

ROOT = Path(__file__).resolve().parents[1]


async def generate(problem_id: int, yaml_path: Path, force: bool = False) -> Path:
    exam = load_lecture_exam(yaml_path)
    problem = get_lecture_problem(exam, problem_id)
    out = ROOT / "assets" / "narration" / problem.lecture.slug
    out.mkdir(parents=True, exist_ok=True)
    voice = problem.lecture.voice
    texts = iter_narrations(problem)
    for i, text in enumerate(texts):
        path = out / f"{i:02d}.mp3"
        if path.exists() and not force:
            continue
        print(f"  TTS [{i:02d}] {text[:60]}…")
        await edge_tts.Communicate(text, voice).save(str(path))
    print(f"TTS ready: {out} ({len(texts)} files)")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate lecture TTS from YAML")
    parser.add_argument("yaml", type=Path, nargs="?", default=ROOT / "problems/2026_suneung/calc_q28_june.yaml")
    parser.add_argument("--id", type=int, default=28)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    asyncio.run(generate(args.id, args.yaml, args.force))


if __name__ == "__main__":
    main()
