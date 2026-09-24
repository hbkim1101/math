"""렌더 없이 시나리오의 모든 LaTeX 문자열을 미리 컴파일해 오류를 찾는다."""

from __future__ import annotations

from pathlib import Path

from manim import tempconfig

from .script.models import Project

# 액션 파라미터 중 LaTeX 로 컴파일되는 것들: (파라미터명, 기본 모드)
TEX_PARAMS = {
    "tex": "auto",
    "lines": "auto",
    "label": "math",
    "x_label": "math",
    "y_label": "math",
    "arrow_label": "math",
}


def iter_tex_strings(project: Project):
    """(segment_id, action, param, text, mode) 를 순회한다. mode 는 'ko' | 'math'."""
    for seg in project.segments:
        for act in seg.actions:
            p = act.params
            ko = bool(p.get("ko"))
            for key, default_mode in TEX_PARAMS.items():
                if key not in p or p[key] is None:
                    continue
                values = p[key] if isinstance(p[key], list) else [p[key]]
                if key == "label" and act.do in ("title_card", "end_card", "caption", "section"):
                    continue
                if act.do in ("problem", "problem_dock") or (act.do == "label" and ko) or (act.do == "caption"):
                    mode = "ko"
                elif default_mode == "auto":
                    mode = "ko" if ko else "math"
                else:
                    mode = default_mode
                for v in values:
                    if isinstance(v, str) and v.strip():
                        yield seg.id, act.do, key, v, mode
            if act.do == "points":
                for it in p.get("items", []):
                    if it.get("label"):
                        yield seg.id, act.do, "items.label", it["label"], "math"


def lint_tex(project: Project, media_dir: str | Path = "output/_cache/lint", log=print) -> list[str]:
    """컴파일 실패한 항목의 설명 목록을 돌려준다 (비어 있으면 통과)."""
    from .narration.timeline import Timeline
    from .render.scene import ExplainerScene

    errors: list[str] = []
    seen: set[tuple[str, str]] = set()
    with tempconfig({"media_dir": str(media_dir), "verbosity": "ERROR", "progress_bar": "none"}):
        scene = ExplainerScene(project, Timeline())
        for seg_id, do, key, text, mode in iter_tex_strings(project):
            if (text, mode) in seen:
                continue
            seen.add((text, mode))
            try:
                if mode == "ko":
                    scene.ktex(text, width=8)
                else:
                    scene.mtex(text, plain=True)
                    if project.t2c and do.startswith("board"):
                        scene.mtex(text)  # t2c 분할이 LaTeX 를 깨뜨리는지도 확인
            except Exception as exc:  # noqa: BLE001
                msg = f"[{seg_id}] {do}.{key} ({mode}): {text[:70]!r}"
                errors.append(msg)
                if log:
                    log("  FAIL " + msg)
    if log:
        log(f"  LaTeX 검사: {len(seen)}개 문자열, 실패 {len(errors)}개")
    return errors
