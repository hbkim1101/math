"""전체 파이프라인: 로드 → TTS/타임라인 → 렌더 → 합성 → 검증."""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path
from typing import Callable, Optional

from .compose.mux import finalize_video
from .narration.timeline import Timeline, build_timeline
from .render.scene import RESOLUTIONS, render_project
from .script.loader import load_project
from .script.models import Project
from .verify.checks import VerifyReport, verify_output


def load_hooks(project: Project) -> dict[str, Callable]:
    """프로젝트 YAML 옆의 hooks.py 에 정의된 함수들을 `custom` 액션에서 쓸 수 있게 로드."""
    if not project.source_path:
        return {}
    hooks_path = Path(project.source_path).parent / "hooks.py"
    if not hooks_path.exists():
        return {}
    spec = importlib.util.spec_from_file_location(f"hooks_{project.meta.id}", hooks_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return {k: v for k, v in vars(mod).items() if callable(v) and not k.startswith("_")}


def build(project_path: str | Path, out_root: str | Path = "output", preview: bool = False,
          force_tts: bool = False, verify: bool = True, segments: list[str] | None = None,
          log=print) -> tuple[Path, Optional[VerifyReport]]:
    """segments 를 주면 그 세그먼트들만 렌더한다 (편집 중 빠른 확인용; 산출물은 `<id>__part/`)."""
    t0 = time.time()
    project = load_project(project_path)
    if segments:
        chosen = [s for s in project.segments if s.id in set(segments)]
        missing = sorted(set(segments) - {s.id for s in chosen})
        if missing:
            raise ValueError(f"없는 세그먼트: {missing}")
        project = project.model_copy(update={
            "segments": chosen,
            "meta": project.meta.model_copy(update={"id": project.meta.id + "__part"}),
        })
        log(f"부분 렌더: {[s.id for s in chosen]}")
    out_dir = Path(out_root) / project.meta.id
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = Path(out_root) / "_cache" / "tts"

    log(f"[1/4] 내레이션 합성 ({project.meta.voice})")
    timeline = build_timeline(project, cache_dir=cache_dir, force=force_tts, log=log)
    log(f"      총 내레이션 {sum(s.audio_duration for s in timeline.segments):.1f}s, 세그먼트 {len(timeline.segments)}개")

    log(f"[2/4] 렌더링 ({'preview 480p15' if preview else project.meta.resolution + ' ' + str(project.meta.fps) + 'fps'})")
    movie = render_project(project, timeline, out_dir, preview=preview, hooks=load_hooks(project), log=log)
    timeline.save(out_dir / "timeline.json")

    log("[3/4] 합성 (자막/라우드니스)")
    manifest = finalize_video(project, timeline, movie, out_dir, preview=preview, log=log)
    final = Path(manifest["final_video"])

    report = None
    if verify:
        log("[4/4] 검증")
        w, h = RESOLUTIONS["480p"] if preview else RESOLUTIONS[project.meta.resolution]
        report = verify_output(out_dir, expect_resolution=(w, h), expect_fps=15 if preview else project.meta.fps)
        log(report.render_text())
        from .verify.storyboard import build_storyboard
        build_storyboard(out_dir, log=log)
    log(f"완료: {final}  (소요 {time.time() - t0:.0f}s)")
    return final, report


def timing_table(project_path: str | Path, out_root: str | Path = "output", log=print) -> Timeline:
    """세그먼트/문장별 오디오 타이밍을 출력 (액션 `at` 값을 정할 때 참고)."""
    project = load_project(project_path)
    timeline = build_timeline(project, cache_dir=Path(out_root) / "_cache" / "tts", log=None)
    t = 0.0
    for seg in timeline.segments:
        log(f"\n■ {seg.id}  (시작≈{t:6.1f}s, 길이 {seg.audio_duration:.2f}s + pad {seg.pad})")
        if seg.clip:
            for i, s in enumerate(seg.clip.sentences, 1):
                log(f"   s{i}  {s.start:6.2f} → {s.end:6.2f}   {s.text}")
        t += seg.audio_duration + seg.pad
    log(f"\n총 예상 길이 ≈ {t:.1f}s ({t/60:.1f}분)")
    return timeline
