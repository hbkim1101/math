"""
2027학년도 6월 모의평가 · 미적분 30번 해설

렌더:
  manim -pql scenes/problem_270630.py Problem270630
  manim -pqh scenes/problem_270630.py Problem270630
"""

from manim import *

from common import KOREAN_FONT, clear_scene, ktext, step_label


class Problem270630(Scene):
    """270630m — 삼차함수와 세제곱근 합성함수의 미분가능성"""

    def construct(self) -> None:
        self.show_title()
        self.show_problem()
        self.step1_f_zero()
        self.step2_p_structure()
        self.step3_g_cubed()
        self.step4_solve_p()
        self.step5_answer()

    # ── intro ──────────────────────────────────────────────

    def show_title(self) -> None:
        title = ktext("2027학년도 6월 모의평가", font_size=40)
        subtitle = ktext("미적분 30번 해설", font_size=52, color=YELLOW)
        subtitle.next_to(title, DOWN, buff=0.35)
        tag = Text("270630m", font=KOREAN_FONT, font_size=24, color=GRAY)
        tag.next_to(subtitle, DOWN, buff=0.3)
        self.play(FadeIn(title), FadeIn(subtitle), run_time=1)
        self.play(FadeIn(tag), run_time=0.5)
        self.wait(1.2)
        self.play(FadeOut(title), FadeOut(subtitle), FadeOut(tag), run_time=0.7)

    def show_problem(self) -> None:
        header = ktext("문제", font_size=36, color=BLUE).to_edge(UP, buff=0.5)
        lines = VGroup(
            ktext("최고차항의 계수가 1인 삼차함수 f(x)에 대하여", font_size=28),
            MathTex(r"g(x)=\sqrt[3]{x(f(x))^2}", font_size=44),
            ktext("g(x)가 실수 전체에서 미분가능하고,", font_size=28),
            VGroup(
                MathTex(r"x=\frac{19}{7},\; x=3", font_size=36),
                ktext("에서 극값을 가질 때,", font_size=28),
                MathTex(r"f(5)=?", font_size=36),
            ).arrange(RIGHT, buff=0.2),
        ).arrange(DOWN, buff=0.35).move_to(ORIGIN)
        self.play(FadeIn(header), run_time=0.5)
        for line in lines:
            self.play(FadeIn(line, shift=UP * 0.15), run_time=0.7)
        self.wait(2)
        self.play(FadeOut(header), FadeOut(lines), run_time=0.7)

    # ── step 1 ─────────────────────────────────────────────

    def step1_f_zero(self) -> None:
        label = step_label(1, "세제곱근 안의 영점 — f(0)=0")
        key = MathTex(r"g(x)^3 = x(f(x))^2", font_size=48).shift(UP * 0.5)
        note1 = ktext("x=0에서 미분가능하려면", font_size=30).next_to(key, DOWN, buff=0.6)
        note2 = ktext("x·(f(x))² 가 x=0에서 3차 이상으로 0이어야 함", font_size=28, color=YELLOW)
        note2.next_to(note1, DOWN, buff=0.25)
        cond = MathTex(r"\therefore\; f(0)=0", font_size=44, color=GREEN).next_to(note2, DOWN, buff=0.5)
        factor = VGroup(
            MathTex(r"f(x)=x\cdot p(x)", font_size=40),
            ktext("(p(x): 이차식, 최고차항 1)", font_size=28, color=GRAY),
        ).arrange(RIGHT, buff=0.25).next_to(cond, DOWN, buff=0.45)

        self.play(FadeIn(label), run_time=0.5)
        self.play(Write(key), run_time=1)
        self.play(FadeIn(note1), FadeIn(note2), run_time=0.8)
        self.play(Write(cond), run_time=0.8)
        self.play(Write(factor), run_time=1)
        self.wait(2)
        clear_scene(self, label, key, note1, note2, cond, factor)

    # ── step 2 ─────────────────────────────────────────────

    def step2_p_structure(self) -> None:
        label = step_label(2, "이차식 p(x)의 구조 결정")
        cases = VGroup(
            ktext("① p의 단근 a  →  |x−a|^{2/3} 꼴  →  미분불가", font_size=26, color=RED),
            ktext("② p=(x−k)² 중근  →  극값 k, 3k/7  →  19/7, 3과 불일치", font_size=26, color=ORANGE),
            ktext("③ p(x)>0 (실근 없음)  ✓", font_size=30, color=GREEN),
        ).arrange(DOWN, buff=0.35, aligned_edge=LEFT).shift(DOWN * 0.2)

        result = MathTex(r"p(x)=x^2+ax+b,\quad p(x)>0\ \forall x\in\mathbb{R}", font_size=38)
        result.next_to(cases, DOWN, buff=0.6)

        self.play(FadeIn(label), run_time=0.5)
        for c in cases:
            self.play(FadeIn(c, shift=RIGHT * 0.2), run_time=0.7)
        self.play(Write(result), run_time=1)
        self.wait(2)
        clear_scene(self, label, cases, result)

    # ── step 3 ─────────────────────────────────────────────

    def step3_g_cubed(self) -> None:
        label = step_label(3, "극값 조건 — g³ 미분")
        g_form = MathTex(r"g(x)=x\,(p(x))^{2/3}", font_size=44).shift(UP * 1.0)
        g3 = MathTex(r"G(x)=g(x)^3=x^3(p(x))^2", font_size=42).next_to(g_form, DOWN, buff=0.5)
        deriv = MathTex(
            r"G'(x)=x^2 p(x)\,\bigl[3p(x)+2x\,p'(x)\bigr]",
            font_size=38,
        ).next_to(g3, DOWN, buff=0.5)
        critical = MathTex(
            r"g'(x)=0 \;\Rightarrow\; 3p(x)+2x\,p'(x)=0",
            font_size=42,
            color=YELLOW,
        ).next_to(deriv, DOWN, buff=0.5)
        roots = MathTex(r"x=\frac{19}{7},\; 3", font_size=40, color=GREEN).next_to(critical, DOWN, buff=0.4)

        self.play(FadeIn(label), run_time=0.5)
        self.play(Write(g_form), run_time=0.8)
        self.play(Write(g3), run_time=1)
        self.play(Write(deriv), run_time=1.2)
        self.play(Write(critical), run_time=1)
        self.play(FadeIn(roots), run_time=0.7)
        self.wait(2)
        clear_scene(self, label, g_form, g3, deriv, critical, roots)

    # ── step 4 ─────────────────────────────────────────────

    def step4_solve_p(self) -> None:
        label = step_label(4, "계수 결정")
        eq1 = MathTex(r"p(x)=x^2+ax+b,\quad p'(x)=2x+a", font_size=38).shift(UP * 1.2)
        eq2 = MathTex(r"3p(x)+2x\,p'(x)=7x^2+5ax+3b", font_size=38).next_to(eq1, DOWN, buff=0.45)
        eq3 = MathTex(
            r"7x^2+5ax+3b=7\!\left(x-\frac{19}{7}\right)(x-3)=7x^2-40x+57",
            font_size=34,
        ).next_to(eq2, DOWN, buff=0.45)
        coeff = MathTex(r"5a=-40,\; 3b=57 \;\Rightarrow\; a=-8,\; b=19", font_size=38, color=YELLOW)
        coeff.next_to(eq3, DOWN, buff=0.45)
        p_final = VGroup(
            MathTex(r"p(x)=x^2-8x+19=(x-4)^2+3>0", font_size=38, color=GREEN),
            ktext("✓", font_size=36, color=GREEN),
        ).arrange(RIGHT, buff=0.15).next_to(coeff, DOWN, buff=0.45)

        self.play(FadeIn(label), run_time=0.5)
        self.play(Write(eq1), run_time=0.8)
        self.play(Write(eq2), run_time=0.8)
        self.play(Write(eq3), run_time=1.2)
        self.play(Write(coeff), run_time=1)
        self.play(Write(p_final), run_time=1)
        self.wait(2)
        clear_scene(self, label, eq1, eq2, eq3, coeff, p_final)

    # ── step 5 ─────────────────────────────────────────────

    def step5_answer(self) -> None:
        label = step_label(5, "답 구하기")
        f_def = MathTex(r"f(x)=x(x^2-8x+19)", font_size=48).shift(UP * 0.5)
        calc = MathTex(
            r"f(5)=5(25-40+19)=5\times 4=20",
            font_size=48,
        ).next_to(f_def, DOWN, buff=0.6)
        answer_box = SurroundingRectangle(calc, color=YELLOW, buff=0.25)
        answer = MathTex(r"\boxed{20}", font_size=64, color=YELLOW).next_to(calc, DOWN, buff=0.7)

        self.play(FadeIn(label), run_time=0.5)
        self.play(Write(f_def), run_time=1)
        self.play(Write(calc), run_time=1.2)
        self.play(Create(answer_box), run_time=0.6)
        self.play(Write(answer), run_time=0.8)
        self.wait(3)
        self.play(
            FadeOut(label), FadeOut(f_def), FadeOut(calc), FadeOut(answer_box), FadeOut(answer),
            run_time=1,
        )

        end = ktext("수고하셨습니다!", font_size=44, color=BLUE)
        self.play(FadeIn(end), run_time=0.8)
        self.wait(1.5)
