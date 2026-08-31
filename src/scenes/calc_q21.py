from __future__ import annotations

import math

from manim import *

from src.config import ANSWER_COLOR, KOREAN_FONT, HIGHLIGHT_COLOR, TITLE_COLOR
from src.renderer.graph_helpers import korean_label, make_graph_axes
from src.renderer.lecture_helpers import (
    PAUSE_LONG,
    PAUSE_MED,
    PAUSE_SHORT,
    WRITE_MED,
    WRITE_SLOW,
    LectureBoard,
)
from src.renderer.q21_graphs import (
    lower_bound,
    plot_lower_bound,
    plot_middle_line,
    plot_upper_bound,
    upper_bound,
)


class Q21CubicInequalityScene(Scene):
    """삼차함수 부등식 21번 — 고2 강의형 (느린 pacing + why 해설)."""

    def construct(self) -> None:
        board = LectureBoard(self)

        header = VGroup(
            Text("21번 · 삼차함수와 부등식", font=KOREAN_FONT, font_size=26, color=TITLE_COLOR),
            Text("대상: 고2", font=KOREAN_FONT, font_size=18, color=GRAY_B),
        ).arrange(DOWN, buff=0.06).to_edge(UP, buff=0.18)
        self.play(FadeIn(header), run_time=0.6)
        self.wait(PAUSE_SHORT)

        # ══════════════════════════════════════════
        # 도입
        # ══════════════════════════════════════════
        board.section("도입", "문제 읽기")
        board.say(
            [
                "f(x)는 삼차함수이고",
                "최고차항의 계수가 1이에요.",
                "0이 아닌 모든 x에서",
                "아래 부등식이 성립한다고 합니다.",
            ],
            pause=PAUSE_LONG,
        )

        problem = MathTex(
            r"\frac{f'(x)}{2}+x^2-2",
            r"\leq",
            r"\frac{f(2x)-f(0)}{2x}",
            r"\leq",
            r"x^4",
            font_size=30,
        ).shift(RIGHT * 1.2)
        ask = Text("구하는 값:  f'(10)", font=KOREAN_FONT, font_size=24, color=HIGHLIGHT_COLOR)
        ask.next_to(problem, DOWN, buff=0.45)
        prob_grp = VGroup(problem, ask)
        self.play(Write(problem), run_time=WRITE_SLOW)
        self.wait(PAUSE_SHORT)
        self.play(FadeIn(ask), run_time=0.7)
        self.wait(PAUSE_MED)

        board.say(
            [
                "처음 보면 복잡해 보이지만,",
                "a, b를 구하면 f'(10)은",
                "바로 계산할 수 있어요.",
            ],
            pause=PAUSE_MED,
        )
        board.tip("전략: f(x)를 미정계수로 두고 부등식을 정리한 뒤, 그래프로 a·b를 확정!")
        self.play(FadeOut(prob_grp), run_time=0.5)

        # ══════════════════════════════════════════
        # 1단계: f(x) 설정
        # ══════════════════════════════════════════
        board.section("1단계", "f(x) 설정")
        board.clear_math()
        board.say(
            [
                "최고차항 계수가 1이므로",
                "미정계수 a, b, c를 두고",
                "이렇게 놓을 수 있어요.",
            ],
            pause=PAUSE_MED,
        )

        board.append_math(r"f(x)=x^3+ax^2+bx+c", font_size=30, pause=PAUSE_SHORT)
        board.say(
            ["미분하면 f'(x)는 이렇게 됩니다.", "(고2에서 배운 다항함수 미분)"],
            pause=PAUSE_MED,
        )
        board.append_math(r"f'(x)=3x^2+2ax+b", font_size=28, color=YELLOW, pause=PAUSE_SHORT)
        board.say(
            [
                "f(0)은 상수항 c예요.",
                "가운데 항에 f(0)이 있죠?",
                "→ 나중에 c가 약분돼서 사라집니다.",
            ],
            highlight="사라집",
            pause=PAUSE_LONG,
        )
        board.append_math(r"f(0)=c", font_size=26, color=GRAY_A, pause=PAUSE_MED)

        # ══════════════════════════════════════════
        # 2단계: 좌변
        # ══════════════════════════════════════════
        board.section("2단계", "왼쪽 식 계산")
        board.clear_math()
        board.say(
            [
                "부등식 왼쪽:",
                "f'(x)/2 + x² − 2",
                "f'(x)를 대입해 볼게요.",
            ],
            pause=PAUSE_MED,
        )

        board.append_math(
            r"\frac{f'(x)}{2}+x^2-2=\frac{3x^2+2ax+b}{2}+x^2-2",
            font_size=24,
            pause=PAUSE_MED,
        )
        board.say(
            ["분수를 풀고, x²끼리 모으면", "최종적으로 이렇게 정리돼요."],
            pause=PAUSE_MED,
        )
        board.append_math(
            r"=\frac{5}{2}x^2+ax+\frac{b}{2}-2",
            font_size=28,
            color=YELLOW,
            pause=PAUSE_LONG,
        )

        # ══════════════════════════════════════════
        # 3단계: 가운데 항
        # ══════════════════════════════════════════
        board.section("3단계", "가운데 항 계산")
        board.clear_math()
        board.say(
            [
                "가운데 (f(2x)−f(0))/(2x)는",
                "평균변화율 형태예요.",
                "f(2x)에 x→2x를 대입합니다.",
            ],
            pause=PAUSE_MED,
        )

        board.append_math(
            r"\frac{f(2x)-f(0)}{2x}=\frac{8x^3+4ax^2+2bx+c-c}{2x}",
            font_size=22,
            pause=PAUSE_MED,
        )
        board.say(
            [
                "분자에서 c−c=0 !",
                "그래서 c는 여기서 사라져요.",
                "x로 나누면 2차식이 남습니다.",
            ],
            highlight="사라져",
            pause=PAUSE_LONG,
        )
        board.append_math(r"=4x^2+2ax+b", font_size=28, color=YELLOW, pause=PAUSE_LONG)

        # ══════════════════════════════════════════
        # 4단계: 부등식 정리
        # ══════════════════════════════════════════
        board.section("4단계", "부등식 정리")
        board.clear_math()
        board.say(
            [
                "세 식을 한 줄로 적으면",
                "이 부등식이 됩니다.",
            ],
            pause=PAUSE_MED,
        )
        board.append_math(
            r"\frac{5}{2}x^2+ax+\frac{b}{2}-2\leq 4x^2+2ax+b\leq x^4",
            font_size=22,
            pause=PAUSE_LONG,
        )

        board.say(
            [
                "왼쪽 부등식: 양변에서",
                "4x², 2ax, b/2를 빼면",
                "2ax+b에 대한 하한이 나와요.",
            ],
            pause=PAUSE_MED,
        )
        board.append_math(r"2ax+b\geq -3x^2-4", font_size=28, color=YELLOW, pause=PAUSE_MED)

        board.say(
            [
                "오른쪽도 마찬가지로",
                "4x²를 넘겨 정리하면",
                "2ax+b의 상한이 나옵니다.",
            ],
            pause=PAUSE_MED,
        )
        board.append_math(r"2ax+b\leq x^4-4x^2", font_size=28, color=YELLOW, pause=PAUSE_MED)

        board.say(
            [
                "정리하면 모든 x에서",
                "아래 두 식 사이에",
                "2ax+b가 갇혀 있어야 해요.",
            ],
            pause=PAUSE_MED,
        )
        board.clear_math()
        final_ineq = MathTex(
            r"-3x^2-4",
            r"\leq",
            r"2ax+b",
            r"\leq",
            r"x^4-4x^2",
            font_size=32,
            color=YELLOW,
        ).shift(RIGHT * 1.2)
        self.play(Write(final_ineq), run_time=WRITE_SLOW)
        self.wait(PAUSE_LONG)

        board.tip("2ax+b는 x에 대한 일차함수 → 그래프는 직선 y=2ax+b")

        # ══════════════════════════════════════════
        # 5단계: 그래프
        # ══════════════════════════════════════════
        board.section("5단계", "그래프로 a, b 확정")
        self.play(FadeOut(final_ineq), run_time=0.5)
        board.clear_math()

        board.say(
            [
                "y = −3x² − 4 는",
                "아래쪽 포물선이에요.",
                "꼭짓점 (0, −4).",
            ],
            pause=PAUSE_MED,
        )

        axes = make_graph_axes(
            x_range=(-2.6, 2.6, 1),
            y_range=(-6, 4, 2),
            x_len=6.8,
            y_len=3.4,
        ).shift(RIGHT * 1.5 + DOWN * 0.55)

        lower = plot_lower_bound(axes, color=TEAL)
        lower_lbl = MathTex(r"y=-3x^2-4", font_size=20, color=TEAL).next_to(
            axes.coords_to_point(-2.2, -3), UP, buff=0.05
        )
        self.play(Create(axes), run_time=WRITE_MED)
        self.play(Create(lower), Write(lower_lbl), run_time=WRITE_SLOW)
        self.wait(PAUSE_MED)

        board.say(
            [
                "y = x⁴ − 4x² 는",
                "W 모양 4차 곡선이에요.",
                "x=±√2 에서 최솟값 −4.",
            ],
            pause=PAUSE_MED,
        )
        upper = plot_upper_bound(axes, color=BLUE)
        upper_lbl = MathTex(r"y=x^4-4x^2", font_size=20, color=BLUE).next_to(
            axes.coords_to_point(2.0, 2), DOWN, buff=0.05
        )
        self.play(Create(upper), Write(upper_lbl), run_time=WRITE_SLOW)
        self.wait(PAUSE_MED)

        sqrt2 = math.sqrt(2)
        h_line = DashedLine(
            axes.coords_to_point(-2.5, -4),
            axes.coords_to_point(2.5, -4),
            color=RED,
            stroke_width=2,
        )
        min_pts = VGroup(
            Dot(axes.coords_to_point(0, -4), color=RED, radius=0.07),
            Dot(axes.coords_to_point(sqrt2, -4), color=RED, radius=0.07),
            Dot(axes.coords_to_point(-sqrt2, -4), color=RED, radius=0.07),
        )
        board.say(
            [
                "두 곡선 모두",
                "y = −4 에서 닿아요.",
                "직선도 여기를 지나야",
                "모든 x에서 성립합니다.",
            ],
            pause=PAUSE_LONG,
        )
        self.play(Create(h_line), LaggedStart(*[GrowFromCenter(d) for d in min_pts], lag_ratio=0.2), run_time=1.2)
        self.wait(PAUSE_MED)

        board.say(
            [
                "기울기가 있으면?",
                "한쪽에서 곡선 밖으로",
                "나가게 돼요. ✕",
            ],
            pause=PAUSE_MED,
        )
        bad = plot_middle_line(axes, a=1.5, b=-4, color=RED)
        self.play(Create(bad), run_time=WRITE_MED)
        cross = Text("✕", font=KOREAN_FONT, font_size=40, color=RED).move_to(
            axes.coords_to_point(1.6, 0.3)
        )
        self.play(FadeIn(cross), run_time=0.5)
        self.wait(PAUSE_MED)
        self.play(FadeOut(bad), FadeOut(cross), run_time=0.5)

        board.say(
            [
                "그래서 유일한 답은",
                "수평선 y = −4.",
                "2ax + b = −4 → a=0, b=−4",
            ],
            pause=PAUSE_LONG,
        )
        good = plot_middle_line(axes, a=0, b=-4, color=YELLOW)
        self.play(Create(good), run_time=WRITE_MED)
        self.wait(PAUSE_LONG)

        graph_stuff = VGroup(axes, lower, upper, lower_lbl, upper_lbl, h_line, min_pts, good)
        self.play(FadeOut(graph_stuff), run_time=0.6)

        # ══════════════════════════════════════════
        # 6단계: 정답
        # ══════════════════════════════════════════
        board.section("6단계", "f'(10) 계산")
        board.clear_math()
        board.say(
            [
                "a=0, b=−4 이므로",
                "f'(x) = 3x² + 2ax + b",
                "= 3x² − 4",
            ],
            pause=PAUSE_MED,
        )
        board.append_math(r"f'(x)=3x^2-4", font_size=30, color=YELLOW, pause=PAUSE_MED)

        board.say(
            [
                "x=10을 대입하면",
                "3×100 − 4 = 296",
                "이 문제의 정답입니다.",
            ],
            pause=PAUSE_MED,
        )
        math_block = board.append_math(
            r"f'(10)=3\cdot 10^2-4=296", font_size=32, color=ANSWER_COLOR, pause=PAUSE_MED
        )

        ans_box = Text("정답  296", font=KOREAN_FONT, font_size=32, color=ANSWER_COLOR)
        ans_box.next_to(math_block, DOWN, buff=0.45)
        rect = SurroundingRectangle(ans_box, color=ANSWER_COLOR, buff=0.15, corner_radius=0.1)
        self.play(Write(ans_box), Create(rect), run_time=WRITE_MED)
        self.wait(PAUSE_LONG)

        board.say(
            [
                "오늘 핵심 정리:",
                "① 미정계수 → 부등식 정리",
                "② 2ax+b를 직선으로 해석",
                "③ 그래프로 계수 확정",
            ],
            pause=PAUSE_LONG + 1.0,
        )
