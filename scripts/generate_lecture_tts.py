#!/usr/bin/env python3
"""Generate natural TTS from Lecture DSL narrate steps."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from src.dsl.lecture_models import get_lecture_problem, iter_narrations, load_lecture_exam
from src.renderer.tts_providers import synthesize_batch

ROOT = Path(__file__).resolve().parents[1]


async def generate(problem_id: int, yaml_path: Path, force: bool = False) -> Path:
    exam = load_lecture_exam(yaml_path)
    problem = get_lecture_problem(exam, problem_id)
    spec = problem.lecture
    tts_cfg = spec.tts
    voice = tts_cfg.voice or spec.voice
    tts_cfg = tts_cfg.model_copy(update={"voice": voice})
    out = ROOT / "assets" / "narration" / spec.slug
    pairs = iter_narrations(problem)
    written = await synthesize_batch(pairs, out, tts_cfg, force=force)
    provider = tts_cfg.provider
    print(
        f"TTS ready: {out} ({len(pairs)} clips, provider={provider}, "
        f"written={written}, voice={tts_cfg.voice})"
    )
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
