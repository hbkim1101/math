from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path

import edge_tts

DEFAULT_VOICE = "ko-KR-SunHiNeural"


async def _synthesize_one(text: str, output: Path, voice: str) -> float:
    output.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output))
    return _probe_duration(output)


def _probe_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode == 0 and result.stdout.strip():
        return max(float(result.stdout.strip()), 0.5)
    return max(len(path.read_bytes()) / 16000, 2.0)


async def synthesize_narrations(
    narrations: list[str],
    output_dir: Path,
    voice: str | None = None,
) -> tuple[list[Path], list[float]]:
    voice = voice or os.environ.get("MATH_VIZ_TTS_VOICE", DEFAULT_VOICE)
    paths: list[Path] = []
    durations: list[float] = []

    for i, text in enumerate(narrations):
        out = output_dir / f"step_{i:02d}.mp3"
        duration = await _synthesize_one(text, out, voice)
        paths.append(out)
        durations.append(duration + 0.35)  # pause padding

    return paths, durations


def synthesize_narrations_sync(
    narrations: list[str],
    output_dir: Path,
    voice: str | None = None,
) -> tuple[list[Path], list[float]]:
    return asyncio.run(synthesize_narrations(narrations, output_dir, voice))


def synthesize_intro_outro(
    intro: str,
    outro: str,
    output_dir: Path,
    voice: str | None = None,
) -> tuple[Path, Path, float, float]:
    voice = voice or os.environ.get("MATH_VIZ_TTS_VOICE", DEFAULT_VOICE)

    async def _run() -> tuple[Path, Path, float, float]:
        intro_path = output_dir / "intro.mp3"
        outro_path = output_dir / "outro.mp3"
        d0 = await _synthesize_one(intro, intro_path, voice)
        d1 = await _synthesize_one(outro, outro_path, voice)
        return intro_path, outro_path, d0, d1

    return asyncio.run(_run())
