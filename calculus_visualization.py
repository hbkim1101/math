
from manim import *  # Scene, Axes, MathTex, Dot, Line 등 Manim 도구 전부 가져오기
import numpy as np   # 난수 배치, 수치 근 찾기 등에 사용

# 렌더링 명령:
#   manim -pqh calculus_visualization.py MeanValueCandidateScene
#
# 16:9 해상도로 렌더:
#   manim -p -r 1920,1080 calculus_visualization.py MeanValueCandidateScene


class MeanValueCandidateScene(Scene):
    # 평균값 정리 후보 g(x)를 시각화하는 Manim 씬

    def construct(self):
        # construct(): 이 씬에 무엇을 그릴지 정의하는 메인 함수

        # ---------- 배경 ----------
        self.camera.background_color = "#0A1630"
        # 화면 전체 배경색을 짙은 남색으로 설정 (칠판 느낌)

        bg_texts = VGroup()
        # 배경 수식들을 담을 빈 그룹 (여러 객체를 하나로 묶음)

        snippets = [
            r"\int_a^b f(x)\,dx", r"\sum_{n=1}^{\infty}", r"\frac{a}{b}",
            r"\Delta x", r"\sin x", r"\cos x", r"f'(x)", r"x^2+y^2",
            r"\lim_{x\to a}", r"\sqrt{x}", r"\nabla f", r"\log x"
        ]
        # 배경에 흩뿌릴 LaTeX 수식 조각 목록

        rng = np.random.default_rng(4)
        # 난수 생성기 (seed=4 → 렌더할 때마다 같은 배치)

        for _ in range(34):
            # 수식 34개를 반복해서 화면에 배치

            tex = MathTex(rng.choice(snippets), color=BLUE_E)
            # snippets에서 하나 골라 LaTeX 수식으로 렌더, 어두운 파란색

            tex.set_opacity(0.09)
            # 9% 불투명도 → 거의 안 보이는 워터마크

            tex.scale(rng.uniform(0.55, 1.05))
            # 크기를 0.55~1.05배 사이에서 랜덤

            tex.rotate(rng.uniform(-0.35, 0.35))
            # -0.35~0.35 라디안만큼 기울임

            tex.move_to([
                rng.uniform(-6.8, 6.8),   # x 좌표 랜덤
                rng.uniform(-3.7, 3.7),   # y 좌표 랜덤
                0                         # z=0 (2D 평면)
            ])

            bg_texts.add(tex)
            # 그룹에 수식 하나 추가

        self.add(bg_texts)
        # 애니메이션 없이 처음부터 배경에 고정 표시

        # ---------- 왼쪽 수식 ----------
        eq = MathTex(
            r"\frac{f(x)-f(1)}{x-1}",  # 할선 기울기 분자/분mo
            r"=",                      # 등호
            r"f'(g(x))",               # f의 도함수를 g(x)에서
            r"\quad (x\neq 1)",         # x≠1 조건
            color=WHITE
        ).scale(1.08)
        # LaTeX 수식 4조각을 흰색으로, 1.08배 크게

        eq.arrange(RIGHT, buff=0.20)
        # 조각들을 가로로 나열, 간격 0.20

        eq.move_to(LEFT * 3.55 + UP * 1.15)
        # 화면 왼쪽 위쪽으로 이동

        self.play(Write(eq), run_time=1.2)
        # 1.2초 동안 글씨 쓰듯 등장

        # ---------- 위쪽 그래프 (f(x)) ----------
        axes = Axes(
            x_range=[0, 4.2, 1],      # x축 범위 0~4.2, 눈금 간격 1
            y_range=[-0.6, 4.2, 1],   # y축 범위 -0.6~4.2
            x_length=3.5,             # 화면상 x축 길이
            y_length=3.05,            # 화면상 y축 길이
            tips=False,               # 축 끝 화살표 없음
            axis_config={"color": GREY_B, "stroke_width": 2},
            # 축 색상과 선 두께
        )
        axes.move_to(RIGHT * 3.25 + UP * 0.95)
        # 오른쪽 위로 배치

        x1_label = MathTex("1", color=YELLOW_E).scale(0.55)
        # x=1 위치 라벨 "1"

        x1_label.next_to(axes.c2p(1, 0), DOWN, buff=0.08)
        # axes.c2p(1,0) = 좌표 (1,0)의 화면 위치, 그 아래에 배치

        x_label = MathTex("x", color=YELLOW_E).scale(0.65)
        # 움직이는 점 x 위치 라벨

        x_label.next_to(axes.c2p(3.0, 0), DOWN, buff=0.08)
        # x=3 (초기 tracker 값) 아래에 "x" 라벨

        def f(t):
            return 0.70 * (t - 1.15) * (t - 2.55) * (t - 3.35) + 2.85
        # 3차 함수 f(t). 모양만 예쁘게 잡은 함수

        graph = axes.plot(
            f,
            x_range=[0.55, 3.65],  # 그릴 x 구간
            color=RED_C,           # 빨간 곡선
            stroke_width=4         # 선 두께
        )

        self.play(Create(axes), FadeIn(x1_label), Create(graph), run_time=1.1)
        # 축, "1" 라벨, f(x) 곡선을 1.1초에 등장

        # ---------- x 추적 (움직이는 점·할선) ----------
        tracker = ValueTracker(3.0)
        # x의 현재 값을 3.0으로 추적. 애니메이션으로 이 값을 바꿈

        p1 = axes.c2p(1.0, f(1.0))
        # 고정점 (1, f(1))의 화면 좌표

        moving_point = always_redraw(
            lambda: Dot(
                axes.c2p(tracker.get_value(), f(tracker.get_value())),
                # tracker 값 = x → (x, f(x)) 위치
                radius=0.07,
                color=YELLOW
            )
        )
        # tracker가 바뀔 때마다 (x, f(x))에 노란 점을 다시 그림

        fixed_point = Dot(p1, radius=0.07, color=YELLOW)
        # (1, f(1)) 고정 노란 점

        secant = always_redraw(
            lambda: Line(
                p1,  # 시작: (1, f(1))
                axes.c2p(tracker.get_value(), f(tracker.get_value())),
                # 끝: (x, f(x))
                color=GREEN_C,
                stroke_width=4
            ).scale(1.35)
            # 선을 1.35배 늘려서 화면 밖으로 살짝 나가게
        )
        # (1,f(1))과 (x,f(x))를 잇는 초록 할선

        x_dash = always_redraw(
            lambda: DashedLine(
                axes.c2p(tracker.get_value(), 0),  # x축 위 (x, 0)
                axes.c2p(tracker.get_value(), f(tracker.get_value())),
                # 곡선 위 (x, f(x))
                color=YELLOW_E,
                dash_length=0.08,    # 점선 한 칸 길이
                dashed_ratio=0.55,   # 점선 비율
                stroke_width=2
            )
        )
        # x축에서 (x, f(x))까지 세로 점선

        fixed_dash = DashedLine(
            axes.c2p(1.0, 0),  # x=1 위 x축 점
            p1,                # (1, f(1))
            color=YELLOW_E,
            dash_length=0.08,
            dashed_ratio=0.55,
            stroke_width=2
        )
        # x=1에서 (1, f(1))까지 세로 점선 (고정)

        self.play(
            FadeIn(fixed_point),   # 고정점 등장
            FadeIn(moving_point),  # 움직이는 점 등장
            Create(fixed_dash),    # x=1 점선
            Create(x_dash),        # x 점선
            Create(secant),        # 할선
            FadeIn(x_label),       # "x" 라벨
            run_time=1.0
        )

        # ---------- 아래쪽 그래프 (f'(x)) ----------
        d_axes = Axes(
            x_range=[0, 4.2, 1],
            y_range=[-2.4, 2.4, 1],
            x_length=3.5,
            y_length=2.15,
            tips=False,
            axis_config={"color": GREY_B, "stroke_width": 2},
        )
        d_axes.move_to(RIGHT * 3.25 + DOWN * 2.15)
        # 위 그래프 아래에 도함수용 축 배치

        def df(t):
            h = 1e-4
            return (f(t+h) - f(t-h)) / (2*h)
        # 중앙차분으로 f'(t) 수치 근사

        deriv_graph = d_axes.plot(
            df,
            x_range=[0.55, 3.65],
            color=PURPLE_B,    # 보라색 곡선
            stroke_width=3
        )

        self.play(Create(d_axes), Create(deriv_graph), run_time=1.0)
        # 도함수 축과 f'(x) 곡선 등장

        def secant_slope(x):
            if abs(x - 1.0) < 1e-6:
                return df(1.0)
            # x≈1이면 0으로 나누기 방지 → f'(1) 사용
            return (f(x) - f(1.0)) / (x - 1.0)
        # 할선 기울기 m(x) = [f(x)-f(1)] / (x-1)

        def candidates(x):
            target = secant_slope(x)
            # 찾을 값: f'(t) = target (= 할선 기울기)이 되는 t

            grid = np.linspace(0.65, 3.55, 500)
            # 0.65~3.55 구간을 500등분

            vals = np.array([df(t) - target for t in grid])
            # 각 격자점에서 df(t) - target 계산

            roots = []
            for i in range(len(grid)-1):
                if vals[i] == 0 or vals[i] * vals[i+1] < 0:
                    # 부호가 바뀌면 → 그 구간에 근(root) 존재

                    a, b = grid[i], grid[i+1]
                    va, vb = vals[i], vals[i+1]
                    for _ in range(24):
                        m = (a+b)/2
                        vm = df(m) - target
                        if va * vm <= 0:
                            b, vb = m, vm
                        else:
                            a, va = m, vm
                    # 이분법 24번 반복 → 근사해 r

                    r = (a+b)/2
                    if not roots or abs(r - roots[-1]) > 0.03:
                        roots.append(r)
                    # 너무 가까운 중복 근은 제외 (0.03 이상 차이)

            if len(roots) == 0:
                return [1.0, 2.7]
            # 근이 없으면 기본값 반환

            if len(roots) == 1:
                return [roots[0], roots[0]]
            # 근이 하나면 두 점이 같은 위치

            return [roots[0], roots[-1]]
            # 첫 근과 마지막 근 = g(x)의 두 후보

        cand1 = always_redraw(
            lambda: Dot(
                d_axes.c2p(
                    candidates(tracker.get_value())[0],
                    df(candidates(tracker.get_value())[0])
                ),
                radius=0.065,
                color=YELLOW
            )
        )
        # 아래 그래프에 첫 번째 g(x) 후보 점 (노란 점)

        cand2 = always_redraw(
            lambda: Dot(
                d_axes.c2p(
                    candidates(tracker.get_value())[1],
                    df(candidates(tracker.get_value())[1])
                ),
                radius=0.065,
                color=YELLOW
            )
        )
        # 아래 그래프에 두 번째 g(x) 후보 점

        bridge1 = always_redraw(
            lambda: DashedLine(
                axes.c2p(tracker.get_value(), f(tracker.get_value())),
                # 위 그래프 (x, f(x))
                d_axes.c2p(
                    candidates(tracker.get_value())[0],
                    df(candidates(tracker.get_value())[0])
                ),
                # 아래 첫 번째 후보
                color=TEAL_C,
                dash_length=0.08,
                dashed_ratio=0.55,
                stroke_width=2
            )
        )
        # 위 (x,f(x)) ↔ 아래 첫 후보를 잇는 청록 점선

        bridge2 = always_redraw(
            lambda: DashedLine(
                axes.c2p(tracker.get_value(), f(tracker.get_value())),
                d_axes.c2p(
                    candidates(tracker.get_value())[1],
                    df(candidates(tracker.get_value())[1])
                ),
                color=YELLOW_E,
                dash_length=0.08,
                dashed_ratio=0.55,
                stroke_width=2
            )
        )
        # 위 (x,f(x)) ↔ 아래 두 번째 후보를 잇는 노란 점선

        def tangent_marker(root_index):
            # 후보 점 옆에 접선 느낌의 작은 사선을 그리는 함수

            def _mk():
                x = candidates(tracker.get_value())[root_index]
                y = df(x)
                p = d_axes.c2p(x, y)
                return Line(
                    p + LEFT * 0.32 + DOWN * 0.11,   # 왼쪽 아래 끝
                    p + RIGHT * 0.32 + UP * 0.11,    # 오른쪽 위 끝
                    color=TEAL_A,
                    stroke_width=4
                )

            return always_redraw(_mk)
            # tracker 바뀔 때마다 사선 위치 갱신

        marker1 = tangent_marker(0)
        # 첫 번째 후보 옆 사선

        marker2 = tangent_marker(1)
        # 두 번째 후보 옆 사선

        label = Text("g(x)의 후보", font_size=30, color=TEAL_A)
        label.move_to(RIGHT * 5.15 + DOWN * 2.0)
        # "g(x)의 후보" 텍스트 라벨

        brace_top = Line(
            label.get_left() + LEFT*0.25 + UP*0.36,
            label.get_left() + LEFT*0.48 + UP*0.68,
            color=TEAL_A,
            stroke_width=3
        )
        # 라벨 왼쪽 위 작은 꺾은선 (괄호 느낌)

        brace_bottom = Line(
            label.get_left() + LEFT*0.25 + DOWN*0.36,
            label.get_left() + LEFT*0.48 + DOWN*0.68,
            color=TEAL_A,
            stroke_width=3
        )
        # 라벨 왼쪽 아래 작은 꺾은선

        self.play(
            Create(bridge1),
            Create(bridge2),
            FadeIn(cand1),
            FadeIn(cand2),
            Create(marker1),
            Create(marker2),
            FadeIn(label),
            Create(brace_top),
            Create(brace_bottom),
            run_time=1.0
        )
        # 후보 점, 연결선, 마커, 라벨 등장

        # ---------- x 움직이는 애니메이션 ----------
        self.wait(0.5)
        # 0.5초 정지

        self.play(
            tracker.animate.set_value(1.22),
            # x를 3.0 → 1.22로 변경
            run_time=4.0,
            rate_func=smooth
            # 4초 동안 부드럽게 이동 (always_redraw 덕분에 점·할선·후보도 같이 움직임)
        )

        self.wait(0.7)
        # 0.7초 정지

        self.play(
            tracker.animate.set_value(3.0),
            # x를 다시 3.0으로 변경 → 후보들이 다시 갈라짐
            run_time=4.0,
            rate_func=smooth
        )

        self.wait(1.0)
        # 마지막 1초 정지 후 씬 종료
