from __future__ import annotations

from pathlib import Path

from manim import *

from src.config import ANSWER_COLOR, HIGHLIGHT_COLOR, KOREAN_FONT, TITLE_COLOR
from src.renderer.graph_helpers import (
    caption_bar,
    count_h_line_intersections,
    critical_slope_b,
    h_derivative,
    h_inverse,
    intersection_dots,
    korean_label,
    make_graph_axes,
    plot_gm_step,
    plot_h_inverse,
    plot_moving_line,
    tangent_t_parameter,
)
from src.dsl.models import get_problem, load_exam

EXAM_PATH = Path(__file__).resolve().parents[2] / "problems" / "2026_suneung" / "calc_q30.yaml"
EXAM = load_exam(EXAM_PATH)


class Q30CalculusScene(Scene):
    """2026 수능 미적분 30번 — 그래프 중심 시각화."""

    def construct(self) -> None:
        problem = get_problem(EXAM, 30)
        b_crit = critical_slope_b()
        t_val = tangent_t_parameter()

        header = VGroup(
            Text(
                f"2026 수능 미적분 {problem.id}번",
                font=KOREAN_FONT,
                font_size=26,
                color=TITLE_COLOR,
            ),
            Text(problem.topic, font=KOREAN_FONT, font_size=20, color=GRAY_B),
        ).arrange(DOWN, buff=0.08).to_edge(UP, buff=0.25)
        self.play(FadeIn(header), run_time=0.5)

        cap = caption_bar("증가함수 f ↔ 역함수 h=f⁻¹ (y=x 대칭)")
        self.play(FadeIn(cap), run_time=0.4)

        # --- 1) y=x 대칭 직관 ---
        sym_axes = Axes(x_range=[-2, 2, 1], y_range=[-2, 2, 1], x_length=3.2, y_length=3.2).shift(LEFT * 3.2 + DOWN * 0.2)
        diag = sym_axes.plot(lambda x: x, x_range=[-2, 2], color=GRAY, stroke_width=2)
        f_curve = sym_axes.plot(lambda x: 0.4 * x**3 + 0.6 * x + 0.2, x_range=[-1.5, 1.5], color=BLUE)
        h_curve = sym_axes.plot(lambda x: 0.4 * x**3 + 0.6 * x - 0.2, x_range=[-1.5, 1.5], color=TEAL)
        sym_group = VGroup(sym_axes, diag, f_curve, h_curve)
        labels = VGroup(
            korean_label("y=f(x)", 18, BLUE).next_to(sym_axes, UP, buff=0.05),
            korean_label("y=h(x)", 18, TEAL).next_to(sym_axes, RIGHT, buff=0.05),
            korean_label("y=x", 16, GRAY).move_to(sym_axes.coords_to_point(1.3, 0.9)),
        )
        self.play(Create(sym_axes), Create(diag), run_time=0.8)
        self.play(Create(f_curve), Create(h_curve), FadeIn(labels), run_time=1.0)
        self.wait(0.6)
        self.play(FadeOut(sym_group), FadeOut(labels), run_time=0.5)

        # --- 2) h(x) 그래프 그리기 ---
        self.play(cap.animate.become(caption_bar("조건(가)(나)에서 증가하는 h(x) 확정")))
        axes = make_graph_axes().shift(DOWN * 0.15)
        h_graph = plot_h_inverse(axes, BLUE)
        h_label = MathTex("h(x)=f^{-1}(x)", font_size=28, color=BLUE).next_to(axes, UP, buff=0.15)

        key_points = {
            "(-1,-2)": (-1, -2),
            "(0,0)": (0, 0),
            "(1,2)": (1, 2),
        }
        dots = VGroup()
        labels_k = VGroup()
        for name, (x, y) in key_points.items():
            dots.add(Dot(axes.coords_to_point(x, y), color=YELLOW, radius=0.08))
            labels_k.add(MathTex(name, font_size=22, color=YELLOW).next_to(axes.coords_to_point(x, y), UR, buff=0.08))

        self.play(Create(axes), Write(h_label), run_time=0.8)
        self.play(Create(h_graph), run_time=1.8)
        self.play(LaggedStart(*[GrowFromCenter(d) for d in dots], lag_ratio=0.2), run_time=0.8)
        self.play(FadeIn(labels_k), run_time=0.6)
        self.wait(0.8)

        # --- 3) 기울기 변화 → 교점 개수 ---
        self.play(
            cap.animate.become(caption_bar("점 (0,1) 지나는 직선 y=x/m+1 과 h(x) 교점 → g(m)")),
            FadeOut(labels_k),
            run_time=0.5,
        )
        origin_dot = Dot(axes.coords_to_point(0, 1), color=ORANGE, radius=0.09)
        origin_lbl = MathTex("(0,1)", font_size=24, color=ORANGE).next_to(origin_dot, UL, buff=0.06)
        self.play(FadeIn(origin_dot), Write(origin_lbl), run_time=0.5)

        m_tracker = ValueTracker(2.5)
        moving_line = plot_moving_line(axes, m_tracker, YELLOW)
        self.add(moving_line)

        count_label = always_redraw(
            lambda: korean_label(
                f"기울기 1/m ≈ {1/m_tracker.get_value():.2f}  →  교점 {count_h_line_intersections(m_tracker.get_value())}개",
                20,
                HIGHLIGHT_COLOR,
            ).to_edge(RIGHT, buff=0.4).shift(DOWN * 2.8)
        )
        self.add(count_label)

        def show_m(m_val: float, wait: float = 1.0) -> None:
            inter = intersection_dots(axes, m_val, RED)
            self.play(m_tracker.animate.set_value(m_val), run_time=1.2)
            if len(inter) > 0:
                self.play(LaggedStart(*[GrowFromCenter(d) for d in inter], lag_ratio=0.15), run_time=0.6)
            self.wait(wait)
            if len(inter) > 0:
                self.play(FadeOut(inter), run_time=0.3)

        show_m(2.5, 0.7)
        show_m(0.8, 0.7)
        show_m(b_crit, 0.9)
        show_m(0.01, 0.7)

        self.play(FadeOut(moving_line), FadeOut(count_label), FadeOut(origin_dot), FadeOut(origin_lbl), run_time=0.4)

        # --- 4) g(m) 계단 그래프 ---
        self.play(
            cap.animate.become(caption_bar("g(m) 불연속: a=0, b≈1/m 접선기울기")),
            FadeOut(h_graph),
            FadeOut(dots),
            FadeOut(h_label),
            axes.animate.scale(0.85).shift(DOWN * 0.3 + LEFT * 2.8),
            run_time=0.6,
        )

        gm_axes = make_graph_axes(
            x_range=(-0.5, 3, 1),
            y_range=(0, 4, 1),
            x_len=5.5,
            y_len=3.5,
        ).shift(RIGHT * 2.2 + DOWN * 0.1)
        gm_axes_labels = VGroup(
            MathTex("m", font_size=26).next_to(gm_axes.x_axis, RIGHT, buff=0.15),
            MathTex("g(m)", font_size=26).next_to(gm_axes.y_axis, UP, buff=0.15),
        )
        gm_plot = plot_gm_step(gm_axes, b_crit)

        a_dot = Dot(gm_axes.coords_to_point(0, 1), color=RED, radius=0.08)
        b_dot = Dot(gm_axes.coords_to_point(b_crit, 2), color=RED, radius=0.08)
        a_lbl = MathTex("a=0", font_size=22, color=RED).next_to(a_dot, DOWN, buff=0.1)
        b_lbl = MathTex(r"b \approx {:.2f}".format(b_crit), font_size=22, color=RED).next_to(b_dot, UR, buff=0.08)

        self.play(Create(gm_axes), Write(gm_axes_labels), run_time=0.7)
        self.play(Create(gm_plot), run_time=1.2)
        self.play(FadeIn(a_dot), FadeIn(b_dot), Write(a_lbl), Write(b_lbl), run_time=0.7)
        self.wait(0.6)

        # --- 5) 접선 조건 시각화 (x<-1) ---
        self.play(
            cap.animate.become(caption_bar("x<-1 접점 t에서 (-t-1)e^{-t-1}=2")),
            FadeOut(gm_axes),
            FadeOut(gm_axes_labels),
            FadeOut(gm_plot),
            FadeOut(a_dot),
            FadeOut(b_dot),
            FadeOut(a_lbl),
            FadeOut(b_lbl),
            axes.animate.scale(1 / 0.85).move_to(DOWN * 0.15),
            run_time=0.5,
        )
        h_graph2 = plot_h_inverse(axes, BLUE)
        self.play(Create(h_graph2), run_time=0.8)

        tx = t_val
        ty = h_inverse(tx)
        t_dot = Dot(axes.coords_to_point(tx, ty), color=RED, radius=0.09)
        tangent = axes.plot(
            lambda x: h_derivative(tx) * (x - tx) + ty,
            x_range=[tx - 1.2, tx + 0.8],
            color=RED,
            stroke_width=2.5,
        )
        p01 = Dot(axes.coords_to_point(0, 1), color=ORANGE, radius=0.08)
        secant = Line(axes.coords_to_point(0, 1), axes.coords_to_point(tx, ty), color=ORANGE, stroke_width=2)
        self.play(FadeIn(t_dot), Create(tangent), FadeIn(p01), Create(secant), run_time=1.0)
        self.wait(0.8)

        # --- 6) 정답 ---
        self.play(*[FadeOut(m) for m in self.mobjects if m != header], run_time=0.5)
        result = VGroup(
            MathTex(r"g(0)=1,\;", r"\lim_{m\to0+}g(m)=3", font_size=34),
            MathTex(r"g(b)=2,\;", r"\left(\frac{\ln b}{b}\right)^2=4", font_size=34),
            MathTex(r"1\times3 + 2\times4 = \mathbf{11}", font_size=40, color=ANSWER_COLOR),
        ).arrange(DOWN, buff=0.35).move_to(ORIGIN)
        ans_box = SurroundingRectangle(result[-1], color=ANSWER_COLOR, buff=0.2)
        self.play(Write(result[0]), run_time=0.7)
        self.play(Write(result[1]), run_time=0.7)
        self.play(Write(result[2]), Create(ans_box), run_time=1.0)
        self.wait(1.5)
