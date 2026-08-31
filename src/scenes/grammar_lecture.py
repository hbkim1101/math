from __future__ import annotations

import json
import os
import re
from pathlib import Path

from manim import *

from src.config import ANSWER_COLOR, KOREAN_FONT
from src.grammar.graphs_q15 import GRAPH_BUILDERS
from src.grammar.models import AnnotateAction, FlowNode, SolutionScript, load_solution
from src.renderer.graph_annotator import GraphAnnotator
from src.renderer.lecture_board import LectureBoard, split_math_lines


class GrammarLectureScene(Scene):
    """풀이 문법 강의 — 시각(그래프·수식) 중심, TTS는 짧은 캡션."""

    def construct(self) -> None:
        path = os.environ.get("MATH_VIZ_SCRIPT")
        if not path:
            self.add(Text("MATH_VIZ_SCRIPT 필요", font=KOREAN_FONT))
            return

        script = load_solution(path)
        board = LectureBoard(self)
        timings = self._load_segments()

        board.show_header(script.brand, f"{script.section} {script.id}번 · {script.topic}")

        ti = 0

        def seg_dur() -> float:
            nonlocal ti
            d = timings[ti]["duration"] if ti < len(timings) else 2.5
            ti += 1
            return d

        # intro — 문제만 잠깐
        board.set_caption("문제 확인")
        self._show_problem(script, board)
        board.wait_lesson(seg_dur(), 1.5)

        def teach(node: FlowNode) -> None:
            cap = node.caption or _short(node.say)
            board.show_badge(node.link)
            board.set_caption(cap)

            lines = split_math_lines(node.math)
            if lines:
                board.write_math_progressive(lines)

            annotations = _all_annotations(node)
            has_graph = bool(node.visual and node.visual.type == "graph" and node.visual.graph)

            if has_graph:
                builder = GRAPH_BUILDERS.get(node.visual.graph)
                if builder:
                    board.set_graph(builder())

            board.wait_lesson(seg_dur(), anim_done=1.0 if has_graph else 0.6)

            if has_graph and annotations and board.graph_mob:
                ann = GraphAnnotator(self, board.graph_mob)
                for act in annotations:
                    if act.say:
                        board.set_caption(act.say)
                    t = ann._play_one(act)
                    if act.say:
                        board.wait_lesson(seg_dur(), anim_done=t)
                    else:
                        self.wait(0.25)

            board.hide_badge()

            if node.link == "when" and node.cases:
                for case in node.cases:
                    board.set_case_tag(case.name)
                    board.set_caption(f"→ {case.name}")
                    board.wait_lesson(seg_dur(), 0.2)
                    for sub in case.flow:
                        teach(sub)
                    board.set_case_tag(None)

        for node in script.flow:
            teach(node)

        board.clear_math()
        if board.graph_mob:
            self.play(FadeOut(board.graph_mob), run_time=0.25)
        ans = VGroup(
            Text("정답", font=KOREAN_FONT, font_size=30, color=ANSWER_COLOR),
            Text(script.answer, font=KOREAN_FONT, font_size=34, color=ANSWER_COLOR),
        ).arrange(RIGHT, buff=0.28)
        box = SurroundingRectangle(ans, color=ANSWER_COLOR, buff=0.18)
        g = VGroup(box, ans).move_to(ORIGIN)
        board.set_caption("정답")
        self.play(FadeIn(g), run_time=0.5)
        board.wait_lesson(seg_dur(), 0.5)

    def _show_problem(self, script: SolutionScript, board: LectureBoard) -> None:
        note = Text(
            "(가) 우미분계수 ≤ 0   (나) g(x)=t 두 실근, t_max=13",
            font=KOREAN_FONT,
            font_size=18,
            color=GRAY_B,
        )
        lines = VGroup(*[MathTex(x, font_size=22) for x in script.question_lines[:2]])
        lines.arrange(DOWN, buff=0.15)
        prob = VGroup(note, lines).arrange(DOWN, buff=0.2)
        from src.renderer.lecture_board import MATH
        MATH.place(prob)
        self.play(FadeIn(note), LaggedStart(*[Write(l) for l in lines], lag_ratio=0.25), run_time=1.0)
        self.play(FadeOut(prob), run_time=0.25)

    def _load_segments(self) -> list[dict]:
        raw = os.environ.get("MATH_VIZ_TIMING")
        if not raw or not Path(raw).exists():
            return []
        return json.loads(Path(raw).read_text()).get("segments", [])


def _short(text: str, n: int = 36) -> str:
    t = re.sub(r"\s+", " ", text.strip())
    return t if len(t) <= n else t[: n - 1] + "…"


def _all_annotations(node: FlowNode) -> list[AnnotateAction]:
    items = list(node.annotate)
    if node.visual:
        items.extend(node.visual.annotate)
    return items
