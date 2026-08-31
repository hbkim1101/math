#!/usr/bin/env python3
"""강의형 영상 렌더 — TTS 선생성 → Manim → ffmpeg 합성."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dsl.models import get_problem, load_exam  # noqa: E402
from src.pipeline.assembler import concat_audio, merge_audio_video, write_srt  # noqa: E402
from src.pipeline.lecture_timing import prepare_lecture_audio, write_lecture_timing  # noqa: E402

SCENE_MAP: dict[int, tuple[str, str]] = {
    22: ("src/scenes/calc_q22.py", "Q22LectureScene"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="강의형 TTS 동기화 영상 생성")
    parser.add_argument("exam", type=Path)
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("-q", "--quality", default="l", choices=["l", "m", "h"])
    parser.add_argument("--scene", type=str, help="scene_file:ClassName override")
    args = parser.parse_args()

    exam = load_exam(args.exam.resolve())
    problem = get_problem(exam, args.id)
    slug = f"q{problem.id:02d}_lecture"

    if args.scene:
        scene_file, scene_class = args.scene.split(":", 1)
    elif args.id in SCENE_MAP:
        scene_file, scene_class = SCENE_MAP[args.id]
    else:
        scene_file, scene_class = "src/scenes/hansu_scene.py", "HansuAutoScene"

    work = ROOT / "output" / "lectures" / slug
    work.mkdir(parents=True, exist_ok=True)
    audio_dir = work / "audio"

    intro = (
        f"안녕하세요, 수학 한수입니다. "
        f"오늘은 {exam.section} {problem.id}번, {problem.topic} 문제를 풀어 보겠습니다."
    )
    outro = (
        f"정리하면, {problem.id}번의 정답은 {problem.answer}입니다. "
        f"오늘도 수학 한수와 함께 완전한 이해, 다음 영상에서 만나요."
    )
    narrations = [s.narration.strip() for s in problem.steps]

    _, audio_files = prepare_lecture_audio(intro, narrations, outro, audio_dir)

    # durations from ffprobe via re-read
    from src.tts.synthesizer import _probe_duration

    intro_d = _probe_duration(audio_files["intro"]) + 0.4
    step_ds = [_probe_duration(audio_files[f"step_{i:02d}"]) + 0.35 for i in range(len(narrations))]
    outro_d = _probe_duration(audio_files["outro"]) + 0.5

    timing_path = work / "timing.json"
    write_lecture_timing(
        timing_path,
        intro_duration=intro_d,
        step_durations=step_ds,
        outro_duration=outro_d,
        audio_files=audio_files,
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["MATH_VIZ_EXAM_PATH"] = str(args.exam.resolve())
    env["MATH_VIZ_PROBLEM_ID"] = str(problem.id)
    env["MATH_VIZ_TIMING"] = str(timing_path)

    manim = ROOT / ".venv" / "bin" / "manim"
    cmd = [
        str(manim), f"-q{args.quality}",
        "--media_dir", str(work / "manim"),
        "-o", slug,
        str(ROOT / scene_file), scene_class,
    ]
    rc = subprocess.run(cmd, cwd=str(ROOT), env=env).returncode
    if rc != 0:
        sys.exit(rc)

    candidates = list(work.rglob(f"{slug}.mp4"))
    video = sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]

    # audio concat: intro + steps + outro
    ordered = [audio_files["intro"]]
    ordered += [audio_files[f"step_{i:02d}"] for i in range(len(narrations))]
    ordered.append(audio_files["outro"])
    merged = work / f"{slug}_audio.mp3"
    concat_audio(ordered, merged)

    final = work / f"{slug}_final.mp4"
    merge_audio_video(video, merged, final, short_video=False)

    # SRT
    t = intro_d
    caps: list[tuple[float, float, str]] = [(0, intro_d, intro)]
    for i, (cap, dur) in enumerate(zip(narrations, step_ds)):
        caps.append((t, t + dur, cap))
        t += dur
    caps.append((t, t + outro_d, outro))
    write_srt(caps, work / f"{slug}.srt")

    # docs copy
    docs = ROOT / "docs" / "videos" / f"{slug}.mp4"
    docs.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy(final, docs)

    print(f"✓ Lecture: {final}")
    print(f"  Docs:    {docs}")
    print(f"  SRT:     {work / f'{slug}.srt'}")


if __name__ == "__main__":
    main()
