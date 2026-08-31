from __future__ import annotations

import json
from pathlib import Path

from src.tts.synthesizer import synthesize_intro_outro, synthesize_narrations_sync


def write_lecture_timing(
    path: Path,
    *,
    intro_duration: float,
    step_durations: list[float],
    outro_duration: float,
    audio_files: dict[str, Path],
) -> None:
    segments: list[dict] = [
        {"kind": "intro", "duration": intro_duration, "audio": str(audio_files.get("intro", ""))},
    ]
    for i, dur in enumerate(step_durations):
        segments.append({
            "kind": "step",
            "index": i,
            "duration": dur,
            "audio": str(audio_files.get(f"step_{i:02d}", "")),
        })
    segments.append({
        "kind": "outro",
        "duration": outro_duration,
        "audio": str(audio_files.get("outro", "")),
    })
    path.write_text(json.dumps({"segments": segments}, ensure_ascii=False, indent=2), encoding="utf-8")


def prepare_lecture_audio(
    intro: str,
    narrations: list[str],
    outro: str,
    audio_dir: Path,
) -> tuple[list[float], dict[str, Path]]:
    """TTS 생성 후 segment별 duration과 파일 경로 반환."""
    audio_dir.mkdir(parents=True, exist_ok=True)
    intro_p, outro_p, d_intro, d_outro = synthesize_intro_outro(intro, outro, audio_dir)
    step_paths, step_durs = synthesize_narrations_sync(narrations, audio_dir)

    files: dict[str, Path] = {"intro": intro_p, "outro": outro_p}
    for i, p in enumerate(step_paths):
        files[f"step_{i:02d}"] = p

    durations = [d_intro + 0.4, *step_durs, d_outro + 0.5]
    return durations, files
