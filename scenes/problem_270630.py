"""
2027학년도 6월 모의평가 · 미적분 30번 — 강의형 해설

레이아웃: 왼쪽 문제 이미지 고정 + 오른쪽 해설

렌더:
  manim -pql scenes/problem_270630.py Problem270630
  manim -pqh scenes/problem_270630.py Problem270630
"""

from manim import *

from common import LectureScene, ktext


class Problem270630(LectureScene):
    """270630m — 삼차함수와 세제곱근 합성함수 (강의형)"""

    def construct(self) -> None:
        self.show_intro("2027학년도 6월 모의평가", "미적분 30번 해설", "270630m")
        self.setup_lecture("problem_270630.png", title="미적분 30번")
        self.play(FadeIn(self.problem_panel), Create(self.divider), run_time=1)
        self.wait(0.8)

        self.step1_f_zero()
        self.step2_p_structure()
        self.step3_g_cubed()
        self.step4_solve_p()
        self.step5_answer()

    def step1_f_zero(self) -> None:
        key = MathTex(r"g(x)^3 = x(f(x))^2", font_size=40)
        note1 = ktext("x=0에서 미분가능하려면", font_size=24)
        note2 = ktext("x·(f(x))² 가 x=0에서\n3차 이상으로 0이어야", font_size=22, color=YELLOW)
        cond = MathTex(r"\therefore\; f(0)=0", font_size=38, color=GREEN)
        factor = MathTex(r"f(x)=x\cdot p(x)", font_size=36)
        sub = ktext("(p: 이차식, 최고차항 1)", font_size=20, color=GRAY)

        content = VGroup(key, note1, note2, cond, factor, sub).arrange(DOWN, buff=0.28, aligned_edge=LEFT)
        self.show_lecture(1, "세제곱근 안의 영점", content, wait=2.5)

    def step2_p_structure(self) -> None:
        cases = VGroup(
            ktext("① p의 단근 → |x−a|^{2/3} → 미분불가", font_size=20, color=RED),
            ktext("② p=(x−k)² → 극값 k, 3k/7\n     → 19/7, 3과 불일치", font_size=20, color=ORANGE),
            ktext("③ p(x) > 0 (실근 없음) ✓", font_size=22, color=GREEN),
        ).arrange(DOWN, buff=0.25, aligned_edge=LEFT)

        result = MathTex(
            r"p(x)=x^2+ax+b,\; p(x)>0\;\forall x",
            font_size=32,
        )

        content = VGroup(cases, result).arrange(DOWN, buff=0.5, aligned_edge=LEFT)
        self.show_lecture(2, "p(x) 구조 결정", content, wait=2.5)

    def step3_g_cubed(self) -> None:
        lines = VGroup(
            MathTex(r"g(x)=x\,(p(x))^{2/3}", font_size=34),
            MathTex(r"G(x)=g(x)^3=x^3(p(x))^2", font_size=32),
            MathTex(r"G'(x)=x^2 p(x)[3p+2xp']", font_size=30),
            MathTex(r"\Rightarrow\; 3p+2xp'=0", font_size=34, color=YELLOW),
            MathTex(r"x=\frac{19}{7},\; 3", font_size=34, color=GREEN),
        ).arrange(DOWN, buff=0.3, aligned_edge=LEFT)

        self.show_lecture(3, "극값 조건 (g³ 미분)", lines, wait=2.5)

    def step4_solve_p(self) -> None:
        lines = VGroup(
            MathTex(r"p(x)=x^2+ax+b,\; p'=2x+a", font_size=30),
            MathTex(r"3p+2xp'=7x^2+5ax+3b", font_size=30),
            MathTex(
                r"=7\!\left(x-\frac{19}{7}\right)(x-3)",
                font_size=28,
            ),
            MathTex(r"=7x^2-40x+57", font_size=30),
            MathTex(r"a=-8,\; b=19", font_size=32, color=YELLOW),
            MathTex(r"p(x)=x^2-8x+19=(x-4)^2+3", font_size=28, color=GREEN),
        ).arrange(DOWN, buff=0.22, aligned_edge=LEFT)

        self.show_lecture(4, "계수 결정", lines, wait=2.5)

    def step5_answer(self) -> None:
        lines = VGroup(
            MathTex(r"f(x)=x(x^2-8x+19)", font_size=38),
            MathTex(r"f(5)=5(25-40+19)", font_size=36),
            MathTex(r"=5 \times 4 = 20", font_size=40, color=YELLOW),
        ).arrange(DOWN, buff=0.35, aligned_edge=LEFT)

        answer = MathTex(r"\boxed{20}", font_size=56, color=YELLOW)
        answer.next_to(lines, DOWN, buff=0.4)

        self.show_lecture(5, "답 구하기", VGroup(lines, answer), wait=3)

        self.clear_lecture()
        end = ktext("수고하셨습니다!", font_size=36, color=BLUE)
        end = self.place_lecture(end)
        self.play(FadeIn(end), run_time=0.8)
        self.wait(1.5)
