"""LaTeX 단계별 대입 애니메이션."""

from __future__ import annotations

from dataclasses import dataclass

from manim import *


@dataclass
class SubstitutionSpec:
    """대입 애니메이션 설정.

    steps: LaTeX 문자열 리스트 — 순서대로 Transform
    highlight: 첫 단계에서 강조할 조각 (예 "x")
    key_map: 첫 TransformMatchingTex 치환 맵 (예 {"x": "2"})
    """

    steps: list[str]
    anchor: np.ndarray
    scale: float = 0.58
    highlight: str | None = None
    key_map: dict[str, str] | None = None
    final_color=YELLOW_E
    color=WHITE


def build_substitution_steps(spec: SubstitutionSpec) -> dict:
    """같은 위치에 겹칠 단계별 MathTex dict 반환."""
    if len(spec.steps) < 2:
        raise ValueError("steps는 최소 2개 필요")

    result = {}
    for i, latex in enumerate(spec.steps):
        kwargs: dict = {"color": spec.color}
        if i == 0 and spec.highlight:
            kwargs["substrings_to_isolate"] = [spec.highlight]
        mob = MathTex(latex, **kwargs).scale(spec.scale)
        mob.move_to(spec.anchor)
        if i == len(spec.steps) - 1:
            mob.set_color(spec.final_color)
        result[f"step_{i}"] = mob

    if spec.key_map:
        result["_key_map"] = spec.key_map
    return result


def animate_substitution(
    scene,
    steps: dict,
    *,
    graph_parts: dict | None = None,
    write_run: float = 0.8,
    highlight_run: float = 0.6,
    transform_run: float = 0.9,
):
    """LaTeX 단계를 순서대로 Write → Indicate → Transform."""
    keys = sorted(
        (k for k in steps if k.startswith("step_")),
        key=lambda k: int(k.split("_")[1]),
    )
    current = steps[keys[0]]

    scene.play(Write(current), run_time=write_run)

    if steps.get("_highlight"):
        try:
            part = current.get_part_by_tex(steps["_highlight"])
            scene.play(Indicate(part, color=YELLOW, scale_factor=1.8), run_time=highlight_run)
        except Exception:
            pass

    key_map = steps.get("_key_map")

    for i in range(1, len(keys)):
        nxt = steps[keys[i]]
        if i == 1 and key_map:
            scene.play(
                TransformMatchingTex(current, nxt, key_map=key_map),
                run_time=transform_run,
            )
        else:
            scene.play(TransformMatchingTex(current, nxt), run_time=transform_run)
        current = nxt

    if graph_parts and graph_parts.get("tangent_label") and graph_parts.get("tangent_label_final"):
        scene.play(
            Transform(graph_parts["tangent_label"], graph_parts["tangent_label_final"]),
            run_time=0.5,
        )
        graph_parts["tangent_label"] = graph_parts["tangent_label_final"]


def build_and_animate_substitution(
    scene,
    spec: SubstitutionSpec,
    graph_parts=None,
    **kwargs,
):
    """spec 빌드 + 애니메이션 한 번에."""
    steps = build_substitution_steps(spec)
    if spec.highlight:
        steps["_highlight"] = spec.highlight
    animate_substitution(scene, steps, graph_parts=graph_parts, **kwargs)
    return steps
