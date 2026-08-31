from __future__ import annotations

import json
import os
from pathlib import Path

from manim import *

from src.config import ANSWER_COLOR, HIGHLIGHT_COLOR, KOREAN_FONT, TITLE_COLOR
from src.grammar.graphs_q15 import GRAPH_BUILDERS
from src.grammar.models import FlowNode, SolutionScript, load_solution
from src.renderer.layout import caption_bar, place_equation


ARROW_WHEN = MathTex(r"\rightarrow", font_size=36, color=HIGHLIGHT_COLOR)
ARROW_THEREFORE = MathTex(r"\Rightarrow", font_size=36, color=YELLOW)


class GrammarLectureScene(Scene):
    """풀이 문법(→/⇒) 기반 강의 Scene."""

    def construct(self) -> None:
        path = os.environ.get("MATH_VIZ_SCRIPT")
        if not path:
            self.add(Text("MATH_VIZ_SCRIPT 필요", font=KOREAN_FONT))
            return

        script = load_solution(path)
        timing = self._load_timing()
        t_idx = 0

        header = VGroup(
            Text(script.brand, font=KOREAN_FONT, font_size=20, color=GRAY_B),
            Text(f"{script.section} {script.id}번 · {script.topic}", font=KOREAN_FONT, font_size=26, color=TITLE_COLOR),
        ).arrange(DOWN, buff=0.06).to_edge(UP, buff=0.2)
        self.play(FadeIn(header), run_time=0.4)

        cap: Text | None = None
        graph_mob: Mobject | None = None
        eq_mob: Mobject | None = None

        def wait_t() -> None:
            nonlocal t_idx
            dur = timing[t_idx] if t_idx < len(timing) else 3.0
            t_idx += 1
            self.wait(max(dur - 0.5, 0.8))

        # intro
        cap = self._caption(cap, "강의 시작")
        wait_t()

        # question
        q_text = Text("조건 (가) 우미분계수 ≤ 0  ·  (나) g(x)=t 두 실근, max t=13", font=KOREAN_FONT, font_size=22)
        q_text.to_edge(UP, buff=1.0)
        q_lines = VGroup(*[MathTex(line, font_size=24) for line in script.question_lines[:3]])
        q_lines.arrange(DOWN, buff=0.2).move_to(ORIGIN).shift(UP * 0.1)
        self.play(FadeIn(q_text), LaggedStart(*[Write(l) for l in q_lines], lag_ratio=0.3), run_time=1.2)
        self.wait(0.8)
        self.play(FadeOut(q_text), FadeOut(q_lines), run_time=0.3)

        def render_node(node: FlowNode, case_prefix: str = "") -> None:
            nonlocal cap, graph_mob, eq_mob

            arrow = ARROW_WHEN if node.link == "when" else ARROW_THEREFORE
            cap_text = node.caption or node.say[:40]
            cap = self._caption(cap, cap_text)

            # arrow badge left
            badge = arrow.copy().to_edge(LEFT, buff=0.5).shift(UP * 0.5)
            self.play(FadeIn(badge, shift=RIGHT * 0.2), run_time=0.25)

            if node.math:
                if eq_mob:
                    self.play(FadeOut(eq_mob), run_time=0.15)
                eq = place_equation(MathTex(node.math, font_size=26))
                self.play(Write(eq), run_time=0.65)
                eq_mob = eq

            if node.visual and node.visual.type == "graph" and node.visual.graph:
                builder = GRAPH_BUILDERS.get(node.visual.graph)
                if builder:
                    if graph_mob:
                        self.play(FadeOut(graph_mob), run_time=0.25)
                    g = builder()
                    self.play(Create(g[0]), run_time=0.4)
                    self.play(*[Create(m) for m in g[1:]], run_time=0.8)
                    graph_mob = g

            wait_t()
            self.play(FadeOut(badge), run_time=0.15)

            if node.link == "when" and node.cases:
                for case in node.cases:
                    case_cap = self._caption(cap, f"→ {case.name}")
                    case_lbl = Text(case.name, font=KOREAN_FONT, font_size=24, color=HIGHLIGHT_COLOR)
                    case_lbl.next_to(case_cap, UP, buff=0.15)
                    self.play(FadeIn(case_lbl), run_time=0.3)
                    for sub in case.flow:
                        render_node(sub, case.name)
                    self.play(FadeOut(case_lbl), run_time=0.2)
                    cap = case_cap

        for node in script.flow:
            render_node(node)

        # answer
        if eq_mob:
            self.play(FadeOut(eq_mob), FadeOut(graph_mob) if graph_mob else Wait(0.01), run_time=0.3)
        ans = VGroup(
            Text("정답", font=KOREAN_FONT, font_size=32, color=ANSWER_COLOR),
            Text(script.answer, font=KOREAN_FONT, font_size=36, color=ANSWER_COLOR),
        ).arrange(RIGHT, buff=0.3)
        box = SurroundingRectangle(ans, color=ANSWER_COLOR, buff=0.2)
        self.play(FadeIn(VGroup(box, ans)), run_time=0.6)
        wait_t()

    def _caption(self, cap: Text | None, text: str) -> Text:
        new = caption_bar(text)
        if cap is None:
            self.play(FadeIn(new), run_time=0.3)
        else:
            self.play(cap.animate.become(new), run_time=0.3)
        return new

    def _load_timing(self) -> list[float]:
        raw = os.environ.get("MATH_VIZ_TIMING")
        if not raw or not Path(raw).exists():
            return []
        data = json.loads(Path(raw).read_text())
        return [float(s["duration"]) for s in data.get("segments", [])]
