"""Q15 칠판 데모 — 손풀이 beat 4개, 필기·그리기 느낌."""

from __future__ import annotations

from manim import *

from src.config import ANSWER_COLOR, CHALK_PINK, CHALK_YELLOW, KOREAN_FONT
from src.grammar.graphs_q15 import f_prime
from src.renderer.chalk_board import ChalkBoard, chalk_math, chalk_text
from src.renderer.graph_helpers import make_graph_axes


class ChalkQ15DemoScene(Scene):
    """15번 앞부분 — 칠판에 써지는 강의 (자동화 없이 beat 수동)."""

    def construct(self) -> None:
        self.camera.background_color = "#0a0a0a"
        board = ChalkBoard(self)
        board.mount()
        board.show_title("수학 한수", "2026 수능 15번 · 미분·조각함수")

        # beat 1 — (가) ⇒
        board.say("우미분계수가 실수이려면 분자→0", link="therefore")
        board.write_math(r"\lim_{x\to a^+}\frac{g(x)-g(a)}{x-a}\in\mathbb{R}")
        board.pause(0.7)

        # beat 2 — 연속
        board.say("그래서 x=a에서 우연속", link="therefore")
        board.write_math(r"\lim_{x\to a^+}g(x)=g(a)")
        board.pause(0.7)

        # beat 3 — a=1 ⇒ f(1)
        board.say("a=1이면 f(1)=−k/2", link="therefore")
        board.write_math(r"f(1)+k=-f(1)\;\Rightarrow\;f(1)=-\frac{k}{2}", color=CHALK_YELLOW)
        board.pause(0.8)

        # beat 4 — f' 그래프 + 주석
        board.say("f'(x) 그래프부터 그립니다", link="therefore")
        board.write_math(r"f'(x)=-6(x+1)(x-1)", color=CHALK_YELLOW)

        axes = make_graph_axes(x_range=(-2.5, 2.5, 1), y_range=(-2, 8, 2), x_len=5.0, y_len=2.8)
        curve = axes.plot(f_prime, x_range=[-2.2, 2.2], color=CHALK_YELLOW, stroke_width=3)
        title = chalk_text("y = f'(x)", font_size=16, color=CHALK_YELLOW)
        title.next_to(axes, UP, buff=0.06)
        board.draw_graph(VGroup(axes, curve, title), run_time=1.6)

        board.say("x=±1에서 0", link="therefore")
        board.chalk_dot(axes, -1, 0)
        board.chalk_dot(axes, 1, 0)
        board.pause(0.4)

        board.say("꼭짓점 (0, 6)", link="therefore")
        peak = board.chalk_dot(axes, 0, 6, color=CHALK_PINK)
        lbl = chalk_math(r"(0,6)", font_size=18, color=CHALK_PINK).next_to(peak, UR, buff=0.06)
        self.play(Write(lbl), run_time=0.45)
        board.pause(1.0)

        # 정답 힌트
        ans = VGroup(
            chalk_text("정답 ①", font_size=26, color=ANSWER_COLOR),
            chalk_math(r"k+f\!\left(\tfrac12\right)=\tfrac{15}{4}", font_size=28, color=ANSWER_COLOR),
        ).arrange(RIGHT, buff=0.3)
        ans.move_to(DOWN * 2.2)
        box = SurroundingRectangle(ans, color=ANSWER_COLOR, buff=0.15, stroke_width=2)
        self.play(Write(ans[1]), AddTextLetterByLetter(ans[0], time_per_char=0.05), Create(box), run_time=1.2)
        board.pause(1.5)
