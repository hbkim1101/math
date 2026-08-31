from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from src.dsl.models import ExamSet, Problem, get_problem, load_exam, save_exam
from src.pipeline.assembler import concat_audio, merge_audio_video, write_srt
from src.pipeline.generator import build_exam_from_problem, export_problem_yaml, generate_solution_yaml
from src.pipeline.planner import enrich_exam, enrich_problem, write_timing_manifest
from src.tts.synthesizer import synthesize_intro_outro, synthesize_narrations_sync


@dataclass
class RenderResult:
    video: Path
    audio: Path
    final: Path
    srt: Path
    work_dir: Path


class VideoPipeline:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[2]
        self.manim = self.root / ".venv" / "bin" / "manim"
        self.scene_file = self.root / "src" / "scenes" / "hansu_scene.py"
        self.scene_class = "HansuAutoScene"

    def run(
        self,
        exam_path: Path,
        problem_id: int,
        *,
        quality: str = "m",
        with_tts: bool = True,
        output_slug: str | None = None,
    ) -> RenderResult:
        exam = load_exam(exam_path)
        problem = enrich_problem(get_problem(exam, problem_id))
        slug = output_slug or f"q{problem_id:02d}_{problem.topic.replace(' ', '_')[:20]}"
        work = self.root / "output" / "pipeline" / slug
        work.mkdir(parents=True, exist_ok=True)

        enriched_path = work / "problem_enriched.yaml"
        enriched_exam = exam.model_copy(
            update={"problems": [p if p.id != problem_id else problem for p in exam.problems]}
        )
        save_exam(enriched_exam, enriched_path)

        audio_dir = work / "audio"
        narrations = [s.narration for s in problem.steps]
        intro = f"{exam.section} {problem.id}번, {problem.topic} 문제입니다."
        outro = f"정답은 {problem.answer} 입니다."

        audio_files: list[Path] = []
        durations: list[float] = []
        t_start = 0.0
        captions: list[tuple[float, float, str]] = []

        if with_tts:
            intro_p, outro_p, d_intro, d_outro = synthesize_intro_outro(intro, outro, audio_dir)
            step_paths, step_durs = synthesize_narrations_sync(narrations, audio_dir)
            audio_files = [intro_p, *step_paths, outro_p]
            durations = [d_intro + 0.3, *step_durs, d_outro + 0.5]

            t_start += durations[0]
            for i, (cap, dur) in enumerate(zip(narrations, step_durs)):
                captions.append((t_start, t_start + dur, cap))
                t_start += dur
        else:
            durations = [2.0] * len(narrations)
            for cap in narrations:
                captions.append((t_start, t_start + 2.0, cap))
                t_start += 2.0

        timing_path = work / "timing.json"
        if with_tts:
            write_timing_manifest(timing_path, step_durs, step_paths)
        else:
            write_timing_manifest(timing_path, durations, [])

        video_path = self._render_manim(
            enriched_path,
            problem_id,
            timing_path,
            work,
            slug,
            quality,
        )

        srt_path = work / f"{slug}.srt"
        write_srt(captions, srt_path)

        final = work / f"{slug}_final.mp4"
        if with_tts and audio_files:
            merged_audio = work / f"{slug}_narration.mp3"
            concat_audio(audio_files, merged_audio)
            merge_audio_video(video_path, merged_audio, final, short_video=True)
        else:
            final = video_path

        return RenderResult(
            video=video_path,
            audio=work / f"{slug}_narration.mp3" if with_tts else Path(),
            final=final,
            srt=srt_path,
            work_dir=work,
        )

    def _render_manim(
        self,
        exam_path: Path,
        problem_id: int,
        timing_path: Path,
        work_dir: Path,
        slug: str,
        quality: str,
    ) -> Path:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.root)
        env["MATH_VIZ_EXAM_PATH"] = str(exam_path)
        env["MATH_VIZ_PROBLEM_ID"] = str(problem_id)
        env["MATH_VIZ_TIMING"] = str(timing_path)

        cmd = [
            str(self.manim),
            f"-q{quality}",
            "--media_dir",
            str(work_dir / "manim"),
            "-o",
            slug,
            str(self.scene_file),
            self.scene_class,
        ]
        rc = subprocess.run(cmd, cwd=str(self.root), env=env).returncode
        if rc != 0:
            raise RuntimeError(f"Manim render failed (exit {rc})")

        candidates = list((work_dir / "manim" / "videos" / self.scene_file.stem).rglob(f"{slug}.mp4"))
        if not candidates:
            candidates = list(work_dir.rglob(f"{slug}.mp4"))
        if not candidates:
            raise FileNotFoundError(f"Rendered video not found for {slug}")
        return sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]

    def from_text(
        self,
        problem_text: str,
        *,
        topic: str = "수학",
        problem_id: int = 1,
        quality: str = "m",
    ) -> RenderResult:
        problem = generate_solution_yaml(problem_text, topic=topic)
        problem = problem.model_copy(update={"id": problem_id})
        exam = build_exam_from_problem(problem)
        tmp = self.root / "output" / "pipeline" / "_generated.yaml"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        save_exam(exam, tmp)
        return self.run(tmp, problem_id, quality=quality)


def enrich_exam_file(path: Path, out_path: Path | None = None) -> Path:
    exam = enrich_exam(load_exam(path))
    dest = out_path or path.with_stem(path.stem + "_enriched")
    save_exam(exam, dest)
    return dest
