"""그래프 + 접선 빌드·애니메이션."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from manim import *
from layout_config import explain_right_box


@dataclass
class GraphSpec:
    """그래프 설정.

    LaTeX는 라벨 표시용, 곡선 그리기는 Python 함수 f(x) 필요.
    """

    f: Callable[[float], float]
    x_range: tuple[float, float, float] = (-2, 3.5, 1)
    y_range: tuple[float, float, float] = (-6, 14, 4)
    plot_x_range: tuple[float, float] = (-1.8, 3.2)

    tangent_at: float | None = None
    slope_fn: Callable[[float], float] | None = None
    tangent_x_range: tuple[float, float] | None = None

    point_label_latex: str | None = None
    x_label_latex: str | None = None
    tangent_label_text: str = "접선 기울기"
    tangent_label_pending_latex: str | None = None
    tangent_label_final_latex: str | None = None

    graph_color=RED_C
    tangent_color=GREEN_C
    stroke_width: float = 2.5


def build_graph_parts(spec: GraphSpec, region: dict | None = None) -> dict:
    """좌표축·곡선·접선·어노테이션을 dict로 반환."""
    box = region or explain_right_box()

    axes = Axes(
        x_range=list(spec.x_range),
        y_range=list(spec.y_range),
        x_length=box["width"] - 1.8,
        y_length=box["height"] - 2.4,
        tips=False,
        axis_config={"color": GREY_B, "stroke_width": 1.5},
    )
    axes.move_to(box["center"] + DOWN * 0.15)

    graph = axes.plot(
        spec.f,
        x_range=list(spec.plot_x_range),
        color=spec.graph_color,
        stroke_width=spec.stroke_width,
    )

    result: dict = {"axes": axes, "graph": graph}

    if spec.tangent_at is None or spec.slope_fn is None:
        result["tangent"] = VGroup()
        result["annotations"] = VGroup()
        return result

    a = spec.tangent_at
    fa = spec.f(a)
    slope = spec.slope_fn(a)
    t_range = spec.tangent_x_range or (a - 1.5, a + 1.0)

    tangent = axes.plot(
        lambda x, fa=fa, slope=slope, a=a: fa + slope * (x - a),
        x_range=list(t_range),
        color=spec.tangent_color,
        stroke_width=spec.stroke_width,
    )

    point = Dot(axes.c2p(a, fa), radius=0.055, color=YELLOW)
    x_dash = DashedLine(
        axes.c2p(a, 0),
        axes.c2p(a, fa),
        color=YELLOW_E,
        dash_length=0.06,
        dashed_ratio=0.55,
        stroke_width=1.5,
    )

    extras = VGroup(x_dash, point)

    if spec.x_label_latex is not None:
        x_label = MathTex(spec.x_label_latex, color=YELLOW_E).scale(0.48)
        x_label.next_to(axes.c2p(a, 0), DOWN, buff=0.06)
        extras.add(x_label)

    if spec.point_label_latex is not None:
        pt_label = MathTex(spec.point_label_latex, color=YELLOW_E).scale(0.45)
        pt_label.next_to(point, UR, buff=0.08)
        extras.add(pt_label)

    tangent_label = None
    tangent_label_final = None

    if spec.tangent_label_pending_latex or spec.tangent_label_final_latex:
        pending = MathTex(
            spec.tangent_label_pending_latex or "?",
            color=spec.tangent_color,
        ).scale(0.55)
        tangent_label = VGroup(
            Text(spec.tangent_label_text, font_size=14, color=spec.tangent_color),
            pending,
        ).arrange(RIGHT, buff=0.08)
        tangent_label.next_to(axes.c2p(a + 0.8, fa + slope * 0.8), UP, buff=0.05)
        extras.add(tangent_label)

        if spec.tangent_label_final_latex:
            final_tex = MathTex(
                spec.tangent_label_final_latex,
                color=spec.tangent_color,
            ).scale(0.55)
            tangent_label_final = VGroup(
                Text(spec.tangent_label_text, font_size=14, color=spec.tangent_color),
                final_tex,
            ).arrange(RIGHT, buff=0.08)
            tangent_label_final.move_to(tangent_label)

    result.update({
        "tangent": tangent,
        "annotations": extras,
        "tangent_label": tangent_label,
        "tangent_label_final": tangent_label_final,
    })
    return result


def animate_graph(
    scene,
    parts: dict,
    *,
    axes_run: float = 1.0,
    graph_run: float = 1.8,
    tangent_run: float = 1.2,
):
    """좌표평면 → 함수 → 접선 순서로 그린다."""
    scene.play(Create(parts["axes"]), run_time=axes_run)
    scene.play(Create(parts["graph"]), run_time=graph_run)

    if parts.get("tangent_label") is not None or (
        parts.get("tangent") and not isinstance(parts["tangent"], VGroup)
    ):
        scene.play(
            Create(parts["tangent"]),
            FadeIn(parts["annotations"]),
            run_time=tangent_run,
        )
    elif parts.get("tangent") and len(parts["tangent"].submobjects) > 0:
        scene.play(
            Create(parts["tangent"]),
            FadeIn(parts["annotations"]),
            run_time=tangent_run,
        )


def graph_group(parts: dict, *, use_final_label: bool = False) -> VGroup:
    """정적 PNG용 — 그래프 요소를 VGroup으로 묶는다."""
    ann = parts["annotations"]
    if use_final_label and parts.get("tangent_label_final"):
        ann = VGroup(*[
            m for m in ann.submobjects
            if m is not parts.get("tangent_label")
        ])
        ann.add(parts["tangent_label_final"])

    items = [parts["axes"], parts["graph"]]
    if parts.get("tangent_label") is not None:
        items.extend([parts["tangent"], ann])
    elif parts.get("tangent") and not isinstance(parts["tangent"], VGroup):
        items.extend([parts["tangent"], ann])
    return VGroup(*items)
