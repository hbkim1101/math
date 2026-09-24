"""데모 시나리오가 담고 있는 수학적 주장들을 sympy 로 엄밀하게 검증한다.

문제: 2027학년도 9월 모의평가 수학 22번
  (가) y=a^x, y=2x²-(7/2)x+3 이 A, B 를 지난다.
  (나) y=log_a(x-1/4)-1/4, y=2x²-(15/2)x+15/2 이 C, D 를 지난다.
  ABCD 는 직사각형. a³ = q/p 일 때 p+q = ?  (정답 97)
"""

import sympy as sp
from sympy import Rational as R

x = sp.symbols("x", real=True)
a = sp.symbols("a", positive=True)

q1 = 2 * x**2 - R(7, 2) * x + 3
q2 = 2 * x**2 - R(15, 2) * x + R(15, 2)

A = (R(3, 4), R(3, 2))
B = (R(3, 2), R(9, 4))
C = (R(5, 2), R(5, 4))
D = (R(7, 4), R(1, 2))
A_VAL = (R(81, 16)) ** R(1, 3)


def test_parabolas_are_translation_by_1_minus_1():
    # q2(x) = q1(x-1) - 1  ⇔  첫 포물선을 (1, -1) 평행이동
    assert sp.simplify(q2 - (q1.subs(x, x - 1) - 1)) == 0
    # 꼭짓점 확인
    v1 = sp.solve(sp.diff(q1, x), x)[0]
    v2 = sp.solve(sp.diff(q2, x), x)[0]
    assert (v1, q1.subs(x, v1)) == (R(7, 8), R(47, 32))
    assert (v2, q2.subs(x, v2)) == (R(15, 8), R(15, 32))


def test_chord_slope_is_linear_in_x1_plus_x2():
    x1, x2 = sp.symbols("x1 x2")
    slope = sp.simplify((q1.subs(x, x2) - q1.subs(x, x1)) / (x2 - x1))
    assert sp.simplify(slope - (2 * (x1 + x2) - R(7, 2))) == 0


def test_line_AB_intersections_with_q1():
    sols = sp.solve(sp.Eq(q1, x + R(3, 4)), x)
    assert sorted(sols) == [R(3, 4), R(3, 2)]
    assert sp.expand(4 * (q1 - (x + R(3, 4))) - (8 * x**2 - 18 * x + 9)) == 0  # 양변 ×4 → 8x²-18x+9=0
    assert sp.factor(8 * x**2 - 18 * x + 9) == (4 * x - 3) * (2 * x - 3)


def test_points_lie_on_their_curves():
    for px, py in (A, B):
        assert q1.subs(x, px) == py
    for px, py in (C, D):
        assert q2.subs(x, px) == py
    # C, D 는 A, B 의 (1, -1) 평행이동
    assert D == (A[0] + 1, A[1] - 1)
    assert C == (B[0] + 1, B[1] - 1)
    # 지수/로그 곡선 위의 점 (a³ = 81/16)
    assert sp.simplify(A_VAL ** A[0] - A[1]) == 0
    assert sp.simplify(A_VAL ** B[0] - B[1]) == 0
    log_curve = lambda t: sp.log(t - R(1, 4), A_VAL) - R(1, 4)
    assert sp.nsimplify(sp.simplify(log_curve(D[0]))) == D[1]
    assert sp.nsimplify(sp.simplify(log_curve(C[0]))) == C[1]


def test_ABCD_is_a_rectangle_with_slopes_1_and_minus_1():
    vec = lambda p, q: (q[0] - p[0], q[1] - p[1])
    AB, BC, CD, DA = vec(A, B), vec(B, C), vec(C, D), vec(D, A)
    assert AB == (-CD[0], -CD[1]) and BC == (-DA[0], -DA[1])  # 평행사변형
    assert AB[0] * BC[0] + AB[1] * BC[1] == 0  # 직각
    assert AB[1] / AB[0] == 1 and BC[1] / BC[0] == -1


def test_symmetry_axis_and_reflections():
    # y=log_a(x-1/4)-1/4 는 y=a^x 를 y=x 대칭 후 (1/4,-1/4) 평행이동 → 대칭축 y = x - 1/4
    def reflect(p, m=1, c=R(-1, 4)):
        px, py = p
        d = sp.Matrix([1, m]) / sp.sqrt(1 + m**2)
        v = sp.Matrix([px, py - c])
        r = 2 * d * (d.dot(v)) - v
        return (sp.nsimplify(r[0]), sp.nsimplify(r[1] + c))

    assert reflect(A) == D
    assert reflect(B) == C
    # 직선 AB: y=x+3/4, CD: y=x-5/4, 대칭축은 둘의 한가운데
    assert A[1] - A[0] == R(3, 4) and B[1] - B[0] == R(3, 4)
    assert C[1] - C[0] == R(-5, 4) and D[1] - D[0] == R(-5, 4)
    assert (R(3, 4) + R(-5, 4)) / 2 == R(-1, 4)


def test_final_answer_97():
    (sol_A,) = sp.solve(sp.Eq(a ** A[0], A[1]), a)  # a^(3/4) = 3/2
    (sol_B,) = sp.solve(sp.Eq(a ** B[0], B[1]), a)  # a^(3/2) = 9/4
    assert sp.simplify(sol_A**3 - R(81, 16)) == 0
    assert sp.simplify(sol_B**3 - R(81, 16)) == 0
    assert R(3, 2) ** 4 == R(81, 16) and R(9, 4) ** 2 == R(81, 16)
    p, q = 16, 81
    assert sp.gcd(p, q) == 1
    assert p + q == 97
