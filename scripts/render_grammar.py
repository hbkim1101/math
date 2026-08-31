#!/usr/bin/env python3
"""풀이 문법 강의 — 짧은 TTS + 시각 beat 동기화."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.grammar.models import FlowNode, SolutionScript, load_solution  # noqa: E402
from src.pipeline.assembler import concat_audio, merge_audio_video, write_srt  # noqa: E402
from src.tts.synthesizer import synthesize_narrations_sync  # noqa: E402


def _short_say(node: FlowNode) -> str:
    return (node.caption or node.say[:40]).strip()


def collect_beats(script: SolutionScript) -> list[tuple[str, str]]:
    """(tts_text, link) — 시각 beat마다 짧은 멘트."""
    beats: list[tuple[str, str]] = [("문제를 확인합니다.", "therefore")]

    def walk(nodes: list[FlowNode]) -> None:
        for node in nodes:
            beats.append((_short_say(node), node.link))
            if node.link == "when" and node.cases:
                for case in node.cases:
                    beats.append((f"{case.name}의 경우", "when"))
                    walk(case.flow)
    walk(script.flow)
    beats.append((f"정답은 {script.answer}입니다.", "therefore"))
    return beats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("script", type=Path)
    parser.add_argument("-q", "--quality", default="l", choices=["l", "m", "h"])
    args = parser.parse_args()

    script_path = args.script.resolve()
    sol = load_solution(str(script_path))
    slug = f"q{sol.id:02d}_grammar"
    work = ROOT / "output" / "grammar" / slug
    audio_dir = work / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    beats = collect_beats(sol)
    texts = [b[0] for b in beats]
    paths, durs = synthesize_narrations_sync(texts, audio_dir)

    segments = [{"kind": b[1], "duration": d, "caption": b[0]} for b, d in zip(beats, durs)]
    timing_path = work / "timing.json"
    timing_path.write_text(json.dumps({"segments": segments}, ensure_ascii=False, indent=2))

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["MATH_VIZ_SCRIPT"] = str(script_path)
    env["MATH_VIZ_TIMING"] = str(timing_path)

    manim = ROOT / ".venv" / "bin" / "manim"
    cmd = [
        str(manim), f"-q{args.quality}", "--media_dir", str(work / "manim"),
        "-o", slug, str(ROOT / "src/scenes/grammar_lecture.py"), "GrammarLectureScene",
    ]
    if subprocess.run(cmd, cwd=str(ROOT), env=env).returncode != 0:
        sys.exit(1)

    video = sorted(work.rglob(f"{slug}.mp4"), key=lambda p: p.stat().st_mtime)[-1]
    merged = work / f"{slug}_audio.mp3"
    concat_audio(paths, merged)
    final = work / f"{slug}_final.mp4"
    merge_audio_video(video, merged, final, short_video=False)

    t = 0.0
    caps = []
    for (_, cap), d in zip(beats, durs):
        caps.append((t, t + d, cap))
        t += d
    write_srt(caps, work / f"{slug}.srt")

    docs = ROOT / "docs" / "videos" / f"{slug}.mp4"
    import shutil
    shutil.copy(final, docs)
    print(f"✓ {final}\n  {docs}")


if __name__ == "__main__":
    main()
