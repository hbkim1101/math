"""그래프 위 주석 — 손풀이 스타일 (점·선·화살표·brace)."""

from __future__ import annotations

from manim import *

from src.config import HIGHLIGHT_COLOR, KOREAN_FONT
from src.grammar.models import AnnotateAction

COLOR_MAP: dict[str, ManimColor] = {
    "YELLOW": YELLOW,
    "RED": RED,
    "BLUE": BLUE,
    "TEAL": TEAL,
    "ORANGE": ORANGE,
    "GREEN": GREEN,
    "WHITE": WHITE,
    "HIGHLIGHT": HIGHLIGHT_COLOR,
}


def _c(name: str) -> ManimColor:
    return COLOR_MAP.get(name.upper(), YELLOW)


def _find_axes(graph: VGroup) -> Axes:
    for m in graph:
        if isinstance(m, Axes):
            return m
    raise ValueError("Axes not found in graph group")


class GraphAnnotator:
    def __init__(self, scene: Scene, graph: VGroup) -> None:
        self.scene = scene
        self.graph = graph
        self.axes = _find_axes(graph)
        self.layer = VGroup()

    def play_all(self, actions: list[AnnotateAction]) -> float:
        """주석 순차 재생, 총 animation 시간 반환."""
        total = 0.0
        for act in actions:
            total += self._play_one(act)
        return total

    def _play_one(self, act: AnnotateAction) -> float:
        mob: Mobject | None = None
        t = 0.45

        if act.action in ("dot", "pulse_dot"):
            assert act.at and len(act.at) >= 2
            x, y = act.at[0], act.at[1]
            dot = Dot(self.axes.coords_to_point(x, y), color=_c(act.color), radius=0.07)
            parts: list[Mobject] = [dot]
            if act.label:
                lbl = MathTex(act.label, font_size=18, color=_c(act.color))
                lbl.next_to(dot, UR, buff=0.05)
                parts.append(lbl)
            mob = VGroup(*parts)
            if act.action == "pulse_dot":
                self.scene.play(GrowFromCenter(dot), run_time=0.35)
                self.scene.play(dot.animate.scale(1.4), dot.animate.scale(1 / 1.4), run_time=0.35)
                t = 0.75
            else:
                self.scene.play(GrowFromCenter(dot), *[Write(p) for p in parts[1:]], run_time=0.45)

        elif act.action == "hline":
            y = act.y if act.y is not None else (act.at[1] if act.at else 0)
            xr = self.axes.x_range[:2]
            line = DashedLine(
                self.axes.coords_to_point(xr[0], y),
                self.axes.coords_to_point(xr[1], y),
                color=_c(act.color),
                stroke_width=2.5,
            )
            parts = [line]
            if act.label:
                lbl = MathTex(act.label, font_size=18, color=_c(act.color))
                lbl.next_to(self.axes.coords_to_point(xr[1] * 0.7, y), UP, buff=0.05)
                parts.append(lbl)
            mob = VGroup(*parts)
            self.scene.play(Create(line), *[Write(p) for p in parts[1:]], run_time=0.55)
            t = 0.6

        elif act.action == "vline":
            x = act.x if act.x is not None else (act.at[0] if act.at else 0)
            yr = self.axes.y_range[:2]
            line = DashedLine(
                self.axes.coords_to_point(x, yr[0]),
                self.axes.coords_to_point(x, yr[1]),
                color=_c(act.color),
                stroke_width=1.8,
            )
            mob = line
            self.scene.play(Create(line), run_time=0.4)

        elif act.action == "arrow":
            assert act.from_pt and act.to
            p0 = self.axes.coords_to_point(act.from_pt[0], act.from_pt[1])
            p1 = self.axes.coords_to_point(act.to[0], act.to[1])
            arr = Arrow(p0, p1, color=_c(act.color), buff=0.05, stroke_width=2.5, max_tip_length_to_length_ratio=0.15)
            mob = arr
            self.scene.play(GrowArrow(arr), run_time=0.45)

        elif act.action == "brace_y":
            x = act.x if act.x is not None else 0
            y0 = act.y0 if act.y0 is not None else 0
            y1 = act.y1 if act.y1 is not None else 1
            p0 = self.axes.coords_to_point(x, y0)
            p1 = self.axes.coords_to_point(x, y1)
            brace = BraceBetweenPoints(p0, p1, direction=RIGHT, color=_c(act.color))
            parts: list[Mobject] = [brace]
            if act.label:
                lbl = MathTex(act.label, font_size=20, color=_c(act.color))
                lbl.next_to(brace, RIGHT, buff=0.08)
                parts.append(lbl)
            mob = VGroup(*parts)
            self.scene.play(GrowFromCenter(brace), *[Write(p) for p in parts[1:]], run_time=0.55)
            t = 0.6

        elif act.action == "label":
            assert act.at
            txt = act.label or ""
            if any(ord(c) > 127 for c in txt):
                lbl: Mobject = Text(txt, font=KOREAN_FONT, font_size=18, color=_c(act.color))
            else:
                lbl = MathTex(txt, font_size=18, color=_c(act.color))
            lbl.move_to(self.axes.coords_to_point(act.at[0], act.at[1]))
            mob = lbl
            self.scene.play(FadeIn(lbl, shift=UP * 0.08), run_time=0.35)

        if mob is not None:
            self.layer.add(mob)
            self.graph.add(mob)
        return t
