from __future__ import annotations

from manim import *

from src.config import ANSWER_COLOR, KOREAN_FONT, HIGHLIGHT_COLOR, TITLE_COLOR
from src.renderer.graph_helpers import make_graph_axes
from src.renderer.hansu_board import HansuPresenter
from src.renderer.q28_june_graphs import (
    ln_Q,
    plot_g_outer,
    plot_ln_Q,
    plot_tangent_at_c,
)


class Q28JuneHansuScene(Scene):
    """2026 6월 모평 28번 — 수학한수 스타일 v2 (그래프 중심 + TTS)."""

    def construct(self) -> None:
        self.camera.background_color = "#0f0f1a"
        voice = HansuPresenter(self)

        # ── 0. 도입 ──
        title = voice.section_title("2026학년도 6월 모평 · 미적분 28번", "수학한수 스타일")
        voice.speak(
            "26학년도 6월 미적분 28번, 같이 풀어볼게요. "
            "겉으로는 복잡해 보이지만, 핵심은 합성함수입니다.",
            segment=0,
        )

        prob = MathTex(
            r"(f(x))^5+(f(x))^3+ax+b",
            r"=",
            r"\ln\left(x^2+x+\frac{5}{2}\right)",
            font_size=34,
        ).shift(UP * 0.3)
        cond = MathTex(r"f(-3)f(3)<0,\quad f'(2)>0", font_size=26, color=HIGHLIGHT_COLOR)
        cond.next_to(prob, DOWN, buff=0.4)
        ask = Text("구함:  a×e^b", font=KOREAN_FONT, font_size=24, color=GRAY_A)
        ask.next_to(cond, DOWN, buff=0.3)
        self.play(Write(prob), run_time=1.5)
        self.play(FadeIn(cond), FadeIn(ask), run_time=0.8)
        self.wait(1.0)
        self.play(FadeOut(prob), FadeOut(cond), FadeOut(ask), run_time=0.5)

        # ── 1. g(f(x))=h(x) ──
        voice.speak(
            "조건 (가)를 이항하면, g(f(x))는 h(x)와 같아요. "
            "g(y)는 y 다섯제곱 더하기 y 세제곱, "
            "h(x)는 로그 빼기 ax 더하기 b 입니다.",
            segment=1,
        )

        decomp = VGroup(
            MathTex(r"g(y)=y^5+y^3", font_size=30, color=PURPLE),
            MathTex(r"\Downarrow", font_size=28),
            MathTex(r"g(f(x))=h(x)", font_size=32, color=YELLOW),
            MathTex(r"h(x)=\ln\left(x^2+x+\frac{5}{2}\right)-ax-b", font_size=26),
        ).arrange(DOWN, buff=0.35)
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.15) for m in decomp], lag_ratio=0.25), run_time=2.0)
        self.wait(1.0)
        self.play(FadeOut(decomp), run_time=0.5)

        # ── 2. g(y) 그래프 ──
        voice.speak(
            "먼저 겉함수 g(y) equals y 다섯제곱 더하기 y 세제곱 그래프를 그려볼게요. "
            "영점에서만 삼차처럼 움직이는, 기울기가 항상 양수인 함수예요.",
            segment=2,
        )

        g_axes = make_graph_axes(
            x_range=(-1.6, 1.6, 0.5),
            y_range=(-1.2, 1.2, 0.5),
            x_len=7,
            y_len=4.5,
        ).shift(UP * 0.2)
        g_lbl = MathTex(r"y=g(t)=t^5+t^3", font_size=28, color=PURPLE).next_to(g_axes, UP, buff=0.15)
        g_graph = plot_g_outer(g_axes, color=PURPLE)
        origin = Dot(g_axes.coords_to_point(0, 0), color=YELLOW, radius=0.08)
        origin_note = Text("t=0에서 3차 접촉", font=KOREAN_FONT, font_size=20, color=GRAY_A)
        origin_note.next_to(origin, UR, buff=0.1)

        self.play(Create(g_axes), Write(g_lbl), run_time=1.0)
        self.play(Create(g_graph), run_time=2.0)
        self.play(GrowFromCenter(origin), FadeIn(origin_note), run_time=0.8)
        self.wait(1.5)
        self.play(
            FadeOut(g_axes), FadeOut(g_graph), FadeOut(g_lbl),
            FadeOut(origin), FadeOut(origin_note),
            run_time=0.5,
        )

        # ── 3. f(c)=0 ──
        voice.speak(
            "조건 (나) f(-3) f(3)이 음수이므로, 사잇값 정리로 "
            "열린구간 (-3, 3) 안에 f(c) equals 0인 c가 반드시 존재합니다.",
            segment=3,
        )

        ivt_axes = NumberLine(x_range=[-3.5, 3.5, 1], length=10, include_numbers=True).shift(UP * 0.5)
        d_neg = Dot(ivt_axes.n2p(-3), color=RED)
        d_pos = Dot(ivt_axes.n2p(3), color=BLUE)
        lbl_neg = MathTex(r"f(-3)<0", font_size=22, color=RED).next_to(d_neg, UP)
        lbl_pos = MathTex(r"f(3)>0", font_size=22, color=BLUE).next_to(d_pos, UP)
        c_mark = Dot(ivt_axes.n2p(-2), color=YELLOW, radius=0.1)
        c_lbl = MathTex(r"f(c)=0", font_size=24, color=YELLOW).next_to(c_mark, DOWN, buff=0.2)

        self.play(Create(ivt_axes), run_time=0.8)
        self.play(GrowFromCenter(d_neg), GrowFromCenter(d_pos), Write(lbl_neg), Write(lbl_pos), run_time=1.0)
        self.play(GrowFromCenter(c_mark), Write(c_lbl), run_time=0.8)
        self.wait(1.0)
        self.play(FadeOut(ivt_axes), FadeOut(d_neg), FadeOut(d_pos), FadeOut(lbl_neg),
                  FadeOut(lbl_pos), FadeOut(c_mark), FadeOut(c_lbl), run_time=0.5)

        # ── 4. h(c)=0 ──
        voice.speak(
            "f(c)가 0이면 g(f(c))도 0이므로, h(c) equals 0 입니다. "
            "로그 그래프에서 직선 y equals ax 더하기 b 가 x equals c 를 지나야 해요.",
            segment=4,
        )

        hint = MathTex(r"g(0)=0 \Rightarrow h(c)=0", font_size=36, color=YELLOW).shift(UP * 0.3)
        self.play(Write(hint), run_time=1.2)
        self.wait(1.0)
        self.play(FadeOut(hint), run_time=0.4)

        # ── 5. 3차 접근 ──
        voice.speak(
            "f가 이계도함수이려면, h(x)는 c 근처에서 최소 삼차식으로 0에 접근해야 합니다. "
            "그래서 h(c), h 프라임 c, h 더블프라임 c 가 모두 0이 됩니다.",
            segment=5,
        )

        triple = MathTex(
            r"h(c)=0,\quad h'(c)=0,\quad h''(c)=0",
            font_size=34,
            color=HIGHLIGHT_COLOR,
        )
        cubic = Text("→ 변곡점에서의 접선!", font=KOREAN_FONT, font_size=24, color=GRAY_A)
        cubic.next_to(triple, DOWN, buff=0.4)
        self.play(Write(triple), run_time=1.5)
        self.play(FadeIn(cubic), run_time=0.6)
        self.wait(1.5)
        self.play(FadeOut(triple), FadeOut(cubic), run_time=0.4)

        # ── 6. c 후보 ──
        voice.speak(
            "h(x)의 이계도함수를 계산하면, c equals -2 또는 c equals 1 입니다. "
            "둘 다 로그 함수의 변곡점이에요.",
            segment=6,
        )

        candidates = VGroup(
            MathTex(r"h''(x)=\frac{-2(x+2)(x-1)}{Q(x)^2}", font_size=28),
            MathTex(r"c=-2 \quad \text{or} \quad c=1", font_size=32, color=YELLOW),
        ).arrange(DOWN, buff=0.5)
        self.play(Write(candidates[0]), run_time=1.2)
        self.play(Write(candidates[1]), run_time=1.0)
        self.wait(1.0)
        self.play(FadeOut(candidates), run_time=0.4)

        # ── 7. ln 그래프 + 변곡점 ──
        voice.speak(
            "이제 y equals ln(x 제곱 더하기 x 더하기 5/2) 그래프를 그립니다. "
            "x equals -2 와 x equals 1 에서 오목·볼록이 바뀌죠.",
            segment=7,
        )

        axes = make_graph_axes(
            x_range=(-3.5, 3.0, 1),
            y_range=(-1.5, 3.0, 1),
            x_len=8,
            y_len=4.2,
        ).shift(UP * 0.15)
        ln_g = plot_ln_Q(axes, x_range=(-3.0, 2.5), color=BLUE)
        ln_lbl = MathTex(r"y=\ln\left(x^2+x+\frac{5}{2}\right)", font_size=24, color=BLUE)
        ln_lbl.to_corner(UR).shift(DOWN * 0.7 + LEFT * 0.3)

        inf_pts = VGroup(
            Dot(axes.coords_to_point(-2, ln_Q(-2)), color=RED, radius=0.08),
            Dot(axes.coords_to_point(1, ln_Q(1)), color=RED, radius=0.08),
        )
        inf_lbl = VGroup(
            MathTex(r"x=-2", font_size=20, color=RED).next_to(inf_pts[0], UL, buff=0.05),
            MathTex(r"x=1", font_size=20, color=RED).next_to(inf_pts[1], UR, buff=0.05),
        )

        self.play(Create(axes), Write(ln_lbl), run_time=0.8)
        self.play(Create(ln_g), run_time=2.0)
        self.play(LaggedStart(*[GrowFromCenter(d) for d in inf_pts], lag_ratio=0.2), run_time=0.8)
        self.play(Write(inf_lbl), run_time=0.6)
        self.wait(1.0)

        # ── 8. 접선 2후보 ──
        voice.speak(
            "변곡점에서의 접선이 두 개 후보입니다. "
            "왼쪽 접선은 기울기 a가 음수, 오른쪽은 a가 양수예요.",
            segment=8,
        )

        tan_left, a_l, b_l = plot_tangent_at_c(axes, -2, color=YELLOW)
        tan_right, a_r, b_r = plot_tangent_at_c(axes, 1, color=ORANGE)
        self.play(Create(tan_left), run_time=1.0)
        self.play(Create(tan_right), run_time=1.0)
        self.wait(1.0)

        # ── 9. f'(2)>0 선택 ──
        voice.speak(
            "f 프라임 2가 0보다 크므로, h(x)는 x equals 2 에서 증가해야 합니다. "
            "따라서 왼쪽 변곡점 접선, x equals -2 가 정답입니다.",
            segment=9,
        )

        self.play(FadeOut(tan_right), FadeOut(inf_lbl[1]), FadeOut(inf_pts[1]), run_time=0.5)
        highlight = SurroundingRectangle(tan_left, color=YELLOW, buff=0.05)
        self.play(Create(highlight), run_time=0.5)
        sel = MathTex(r"c=-2,\ a=-\frac{2}{3}", font_size=28, color=YELLOW)
        sel.to_corner(UL).shift(DOWN * 0.8 + RIGHT * 0.2)
        self.play(Write(sel), run_time=1.0)
        self.wait(1.0)

        # ── 10. a, b ──
        voice.speak(
            "x equals -2 에서 접선의 기울기 a는 -2/3, "
            "b는 ln 9/2 빼기 4/3 입니다.",
            segment=10,
        )

        ab = VGroup(
            MathTex(r"a=-\frac{2}{3}", font_size=30, color=YELLOW),
            MathTex(r"b=\ln\frac{9}{2}-\frac{4}{3}", font_size=28),
        ).arrange(DOWN, buff=0.3).to_edge(RIGHT, buff=0.5).shift(UP * 0.5)
        self.play(Write(ab), run_time=1.2)
        self.wait(1.0)

        # ── 11. 정답 ──
        voice.speak(
            "구하는 값 a times e to the b 는 "
            "-3 times e to the minus 4/3. 정답은 1번입니다.",
            segment=11,
        )

        ans = MathTex(r"a\times e^b=-3e^{-\frac{4}{3}}", font_size=36, color=ANSWER_COLOR)
        ans_box = SurroundingRectangle(ans, color=ANSWER_COLOR, buff=0.15, corner_radius=0.08)
        ans_grp = VGroup(ans, ans_box).move_to(UP * 0.5)
        self.play(
            FadeOut(axes), FadeOut(ln_g), FadeOut(ln_lbl), FadeOut(tan_left),
            FadeOut(highlight), FadeOut(sel), FadeOut(ab), FadeOut(inf_pts[0]),
            run_time=0.5,
        )
        self.play(Write(ans), Create(ans_box), run_time=1.5)
        badge = Text("정답  ①", font=KOREAN_FONT, font_size=32, color=ANSWER_COLOR)
        badge.next_to(ans_grp, DOWN, buff=0.4)
        self.play(FadeIn(badge), run_time=0.6)
        self.wait(2.5)

        self.play(FadeOut(title), FadeOut(ans_grp), FadeOut(badge), run_time=0.6)
        voice.clear_subtitle()
