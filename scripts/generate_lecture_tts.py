#!/usr/bin/env python3
"""Generate natural TTS from Lecture DSL narrate steps (SSML + pacing)."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import edge_tts

from src.dsl.lecture_models import get_lecture_problem, iter_narrations, load_lecture_exam
from src.renderer.tts_utils import build_ssml

ROOT = Path(__file__).resolve().parents[1]


async def generate(problem_id: int, yaml_path: Path, force: bool = False) -> Path:
    exam = load_lecture_exam(yaml_path)
    problem = get_lecture_problem(exam, problem_id)
    spec = problem.lecture
    tts_cfg = spec.tts
    voice = tts_cfg.voice or spec.voice
    out = ROOT / "assets" / "narration" / spec.slug
    out.mkdir(parents=True, exist_ok=True)

    pairs = iter_narrations(problem)
    for i, (subtitle, speech) in enumerate(pairs):
        path = out / f"{i:02d}.mp3"
        if path.exists() and not force:
            continue
        ssml = build_ssml(
            speech,
            voice,
            rate=tts_cfg.rate,
            pitch=tts_cfg.pitch,
            pause_ms=tts_cfg.pause_ms,
        )
        print(f"  TTS [{i:02d}] {subtitle[:50]}…")
        comm = edge_tts.Communicate(ssml, voice)
        await comm.save(str(path))
    print(f"TTS ready: {out} ({len(pairs)} files, voice={voice}, rate={tts_cfg.rate})")
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
