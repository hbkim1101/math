from __future__ import annotations

import math

from manim import *

from src.config import ANSWER_COLOR, KOREAN_FONT, HIGHLIGHT_COLOR, TITLE_COLOR
from src.renderer.graph_helpers import make_graph_axes
from src.renderer.lecture_helpers import (
    PAUSE_LONG,
    PAUSE_MED,
    PAUSE_SHORT,
    WRITE_MED,
    WRITE_SLOW,
    LectureBoard,
)
from src.renderer.q28_june_graphs import (
    Q,
    june28_a,
    june28_b,
    june28_c,
    ln_Q,
    plot_ln_Q,
    plot_tangent_line,
)


class Q28JuneMockScene(Scene):
    """2026학년도 6월 모평 미적분 28번 — 고2 강의형 풀 해설."""

    def construct(self) -> None:
        board = LectureBoard(self)
        a_val = june28_a()
        b_val = june28_b()
        c_val = june28_c()

        header = VGroup(
            Text("28번 · 2026학년도 6월 모평", font=KOREAN_FONT, font_size=26, color=TITLE_COLOR),
            Text("미적분 · 합성함수와 변곡점 접선", font=KOREAN_FONT, font_size=18, color=GRAY_B),
        ).arrange(DOWN, buff=0.06).to_edge(UP, buff=0.18)
        self.play(FadeIn(header), run_time=0.6)
        self.wait(PAUSE_SHORT)

        # ── 도입 ──
        board.section("도입", "문제 읽기")
        board.say(
            [
                "f(x)는 이계도함수를 갖고,",
                "아래 항등식이 모든 x에서 성립해요.",
                "구하는 값은 a×e^b 입니다.",
            ],
            pause=PAUSE_MED,
        )

        prob = MathTex(
            r"(f(x))^5+(f(x))^3+ax+b",
            r"=",
            r"\ln\left(x^2+x+\frac{5}{2}\right)",
            font_size=26,
        ).shift(RIGHT * 0.8)
        cond = VGroup(
            MathTex(r"f(-3)f(3)<0", font_size=24, color=HIGHLIGHT_COLOR),
            MathTex(r"f'(2)>0", font_size=24, color=HIGHLIGHT_COLOR),
        ).arrange(DOWN, buff=0.2).next_to(prob, DOWN, buff=0.45)
        prob_grp = VGroup(prob, cond)
        self.play(Write(prob), run_time=WRITE_SLOW)
        self.play(FadeIn(cond), run_time=0.8)
        self.wait(PAUSE_MED)

        board.tip("f를 직접 구하지 말고 H(f(x))=r(x) 합성함수로 바꿔요!")
        self.play(FadeOut(prob_grp), run_time=0.5)

        # ── 1단계: H(f(x))=r(x) ──
        board.section("1단계", "합성함수로 묶기")
        board.clear_math()
        board.say(
            [
                "y⁵+y³ 은 y=0에서만 0이 되는",
                "증가하는(홀수차) 함수예요.",
                "이걸 H(y)라 두면…",
            ],
            pause=PAUSE_MED,
        )
        board.append_math(r"H(y)=y^5+y^3=y^3(y^2+1)", font_size=26, pause=PAUSE_SHORT)
        board.append_math(
            r"r(x)=\ln\left(x^2+x+\frac{5}{2}\right)-ax-b",
            font_size=24,
            pause=PAUSE_MED,
        )
        board.say(
            [
                "원래 식은",
                "H(f(x)) = r(x) 한 줄로 정리됩니다.",
            ],
            pause=PAUSE_MED,
        )
        board.append_math(r"H(f(x))=r(x)", font_size=30, color=YELLOW, pause=PAUSE_MED)

        board.say(
            [
                "미분해 보면 H'(0)=0, H''(0)=0.",
                "이게 나중에 r'(c)=r''(c)=0의",
                "핵심 이유가 됩니다.",
            ],
            highlight="핵심",
            pause=PAUSE_LONG,
        )
        board.append_math(r"H'(y)=5y^4+3y^2\ge 0", font_size=26, color=GRAY_A, pause=PAUSE_MED)

        # ── 2단계: f(c)=0 ──
        board.section("2단계", "f(c)=0 존재")
        board.clear_math()
        board.say(
            [
                "조건 f(-3)f(3)<0 은",
                "고2 사잇값 정리 그대로예요.",
                "연속함수 f가 x축을 건너뛴다 →",
                "(-3,3) 안에 f(c)=0인 c가 있어요.",
            ],
            pause=PAUSE_LONG,
        )
        board.append_math(r"\exists\, c\in(-3,3)\ \text{s.t.}\ f(c)=0", font_size=28, color=YELLOW, pause=PAUSE_MED)
        board.say(
            [
                "f(c)=0이면 H(f(c))=H(0)=0",
                "즉 r(c)=0 입니다.",
            ],
            pause=PAUSE_MED,
        )
        board.append_math(r"r(c)=0", font_size=28, color=YELLOW, pause=PAUSE_MED)

        # ── 3단계: r'(c)=r''(c)=0 ──
        board.section("3단계", "변곡점 접선 조건")
        board.clear_math()
        board.say(
            [
                "r(x)=H(f(x))를 미분하면",
                "r'(x)=H'(f(x))·f'(x)",
                "r''(x)도 f, f', f''로 표현돼요.",
            ],
            pause=PAUSE_MED,
        )
        board.append_math(r"r'(x)=H'(f(x))\,f'(x)", font_size=26, pause=PAUSE_SHORT)
        board.append_math(
            r"r''(x)=H''(f(x))(f'(x))^2+H'(f(x))\,f''(x)",
            font_size=22,
            pause=PAUSE_MED,
        )
        board.say(
            [
                "x=c에서 f(c)=0 → H'(0)=H''(0)=0",
                "따라서 r'(c)=0, r''(c)=0 까지!",
            ],
            highlight="r''(c)=0",
            pause=PAUSE_LONG,
        )
        board.append_math(r"r(c)=r'(c)=r''(c)=0", font_size=28, color=YELLOW, pause=PAUSE_MED)

        board.tip("기하: y=ln(Q(x))와 직선 y=ax+b가 x=c에서 접하고, c는 변곡점")

        # ── 4단계: r''로 c 후보 ──
        board.section("4단계", "c = −2 또는 1")
        board.clear_math()
        board.say(
            [
                "Q(x)=x²+x+5/2 (>0)라 두고",
                "r(x)를 두 번 미분해 볼게요.",
            ],
            pause=PAUSE_MED,
        )
        board.append_math(r"r'(x)=\frac{2x+1}{Q(x)}-a", font_size=26, pause=PAUSE_SHORT)
        board.append_math(
            r"r''(x)=\frac{-2(x+2)(x-1)}{Q(x)^2}",
            font_size=26,
            color=YELLOW,
            pause=PAUSE_MED,
        )
        board.say(
            [
                "r''(c)=0 → (c+2)(c−1)=0",
                "후보: c=−2, c=1",
            ],
            pause=PAUSE_MED,
        )
        board.append_math(r"c=-2 \quad \text{or} \quad c=1", font_size=28, color=YELLOW, pause=PAUSE_MED)

        # ── 5단계: a와 f'(2)>0 ──
        board.section("5단계", "f'(2)>0으로 후보 선택")
        board.clear_math()
        board.say(
            [
                "r'(c)=0에서 a를 c로 표현:",
            ],
            pause=PAUSE_SHORT,
        )
        board.append_math(
            r"a=\frac{2c+1}{c^2+c+\frac{5}{2}}",
            font_size=28,
            color=YELLOW,
            pause=PAUSE_MED,
        )
        board.say(
            [
                "c=−2 → a=−2/3,  r'(2)>0 ✓",
                "c=1 → a=2/3,   r'(2)<0 ✗",
            ],
            pause=PAUSE_MED,
        )
        board.append_math(r"c=-2,\quad a=-\frac{2}{3}", font_size=28, color=YELLOW, pause=PAUSE_SHORT)

        board.say(
            [
                "왜 r'(2) 부호로 고를까?",
                "r'(2)=H'(f(2))·f'(2)",
                "H'≥0 이고 f'(2)>0 이므로 r'(2)>0 필요!",
            ],
            highlight="r'(2)>0",
            pause=PAUSE_LONG,
        )

        # ── 6단계: 그래프 ──
        board.section("6단계", "그래프 확인")
        board.clear_math()
        board.say(
            [
                "y=ln(x²+x+5/2) 곡선과",
                "직선 y=ax+b (a=−2/3)",
                "x=−2에서 접하는 모습이에요.",
            ],
            pause=PAUSE_MED,
        )

        axes = make_graph_axes(
            x_range=(-3.5, 3.0, 1),
            y_range=(-1, 3, 1),
            x_len=6.5,
            y_len=3.2,
        ).shift(RIGHT * 1.4 + DOWN * 0.5)

        ln_graph = plot_ln_Q(axes, x_range=(-3.0, 2.5), color=BLUE)
        tangent = plot_tangent_line(axes, a_val, b_val, x_range=(-3.0, 2.5), color=YELLOW)

        self.play(Create(axes), run_time=WRITE_MED)
        self.play(Create(ln_graph), run_time=WRITE_SLOW)
        self.play(Create(tangent), run_time=WRITE_MED)

        c_dot = Dot(axes.coords_to_point(c_val, ln_Q(c_val)), color=RED, radius=0.08)
        c_lbl = MathTex(r"c=-2", font_size=22, color=RED).next_to(c_dot, UP, buff=0.1)
        self.play(GrowFromCenter(c_dot), Write(c_lbl), run_time=0.8)
        self.wait(PAUSE_LONG)

        graph_grp = VGroup(axes, ln_graph, tangent, c_dot, c_lbl)
        self.play(FadeOut(graph_grp), run_time=0.5)

        # ── 7단계: b와 정답 ──
        board.section("7단계", "b와 ae^b")
        board.clear_math()
        board.say(
            [
                "r(−2)=0에 a=−2/3 대입:",
                "ln(9/2) + 4/3 − b = 0",
            ],
            pause=PAUSE_MED,
        )
        board.append_math(r"b=\ln\frac{9}{2}-\frac{4}{3}", font_size=28, pause=PAUSE_MED)

        board.say(
            [
                "a×e^b 를 계산하면",
                "e^b = (9/2)·e^{−4/3}",
            ],
            pause=PAUSE_MED,
        )
        board.append_math(
            r"a\times e^b=-\frac{2}{3}\cdot\frac{9}{2}\cdot e^{-\frac{4}{3}}",
            font_size=24,
            pause=PAUSE_MED,
        )
        board.append_math(
            r"=-3e^{-\frac{4}{3}}",
            font_size=32,
            color=ANSWER_COLOR,
            pause=PAUSE_MED,
        )

        ans = Text("정답  ①  −3e^{−4/3}", font=KOREAN_FONT, font_size=28, color=ANSWER_COLOR)
        ans.shift(RIGHT * 1.8 + DOWN * 1.5)
        box = SurroundingRectangle(ans, color=ANSWER_COLOR, buff=0.12, corner_radius=0.08)
        self.play(Write(ans), Create(box), run_time=WRITE_MED)
        self.wait(PAUSE_LONG)

        board.say(
            [
                "오늘 핵심 정리:",
                "① H(f(x))=r(x)로 관점 전환",
                "② f(c)=0 → r(c)=r'(c)=r''(c)=0",
                "③ 변곡점 접선 + f'(2)>0",
            ],
            pause=PAUSE_LONG + 1.0,
        )
