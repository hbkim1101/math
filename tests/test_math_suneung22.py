"""2026학년도 수능 수학 22번 시나리오(projects/2026_suneung_q22)의 수학적 주장들을 sympy 로 검증한다.

문제: 곡선 y=log16(8x+2) 위의 점 A(a,b), 곡선 y=4^(x-1)-1/2 위의 점 B 가 제1사분면에 있다.
      A 를 y=x 에 대칭이동한 점이 직선 OB 위에 있고 AB 의 중점이 (77/8, 133/8) 일 때 ab = q/p, p+q = ?  (정답 457)
"""

import pytest
import sympy as sp
from sympy import Rational as R

x, y, k, t = sp.symbols("x y k t", real=True)
a, b = sp.symbols("a b", positive=True)

curve1 = sp.log(8 * x + 2, 16)          # y = log16(8x+2)
curve2 = 4 ** (x - 1) - R(1, 2)         # y = 4^(x-1) - 1/2

A_VAL = (R(63, 4), R(7, 4))
B_VAL = (R(7, 2), R(63, 2))


def test_log_condition_becomes_exponential():
    # b = log16(8a+2)  ⇔  2^(4b-1) = 4a+1
    lhs = 2 ** (4 * b - 1)
    # b 를 로그식으로 치환하면 항등식
    assert sp.simplify(lhs.subs(b, sp.log(8 * a + 2, 16)) - (4 * a + 1)) == 0
    # 실제 값 대입: 8·63/4+2 = 128 = 16^(7/4)
    assert sp.simplify(sp.log(8 * A_VAL[0] + 2, 16) - A_VAL[1]) == 0


def test_curve2_point_condition():
    # (x, y) 가 y=4^(x-1)-1/2 위  ⇔  2y+1 = 2^(2x-1)
    assert sp.simplify((2 * curve2 + 1) - 2 ** (2 * x - 1)) == 0


def test_swapped_and_doubled_point_lies_on_curve2():
    # A(a,b) 가 curve1 위이면 (2b, 2a) 는 curve2 위: curve2(2b) = 2a
    bb = sp.log(8 * a + 2, 16)
    assert sp.simplify(curve2.subs(x, 2 * bb) - 2 * a) == 0
    # 곡선 전체로도 성립: (t, f(t)) → (2f(t), 2t) 가 curve2 위 (hooks.swap_then_scale 이 그리는 그림)
    assert sp.simplify(curve2.subs(x, 2 * sp.log(8 * t + 2, 16)) - 2 * t) == 0


def test_k_equals_2_is_the_only_positive_solution():
    # B = (kb, ka) 가 curve2 위: g(k) = 2^(2bk-1) - 2ak - 1 = 0
    av, bv = A_VAL
    g = 2 ** (2 * bv * k - 1) - 2 * av * k - 1
    assert sp.simplify(g.subs(k, 2)) == 0
    assert g.subs(k, 0) == R(-1, 2)                     # k=0 에서 직선(1) > 지수(1/2)
    assert sp.simplify(sp.diff(g, k, 2)).is_positive    # 아래로 볼록
    # 볼록 + g(0)<0 → 양의 근은 하나(음의 근은 k<0 쪽에 하나 있을 수 있다)
    # (0, 10] 을 촘촘히 훑어 부호가 바뀌는 구간이 k=2 근방 하나뿐인지 확인
    grid = [i / 100 + 0.005 for i in range(0, 1000)]   # 격자점이 근 k=2 에 정확히 걸리지 않게 어긋나게 잡는다
    vals = [float(g.subs(k, v)) for v in grid]
    changes = [grid[i] for i in range(1, len(vals)) if vals[i - 1] * vals[i] < 0]
    assert len(changes) == 1 and abs(changes[0] - 2) <= 0.01
    assert float(sp.nsolve(g, k, 1.8)) == pytest.approx(2.0, abs=1e-9)
    # 일반 a, b 에 대한 볼록성 (b>0)
    gg = 2 ** (2 * b * k - 1) - 2 * a * k - 1
    assert sp.simplify(sp.diff(gg, k, 2) / (2 ** (2 * b * k - 1) * sp.log(2) ** 2)) == 4 * b ** 2


def test_midpoint_system_gives_a_and_b():
    sol = sp.solve([sp.Eq((a + 2 * b) / 2, R(77, 8)), sp.Eq((b + 2 * a) / 2, R(133, 8))], [a, b], dict=True)
    assert sol == [{a: R(63, 4), b: R(7, 4)}]


def test_points_are_on_curves_and_collinear():
    av, bv = A_VAL
    assert sp.simplify(curve1.subs(x, av) - bv) == 0
    assert sp.simplify(curve2.subs(x, B_VAL[0]) - B_VAL[1]) == 0
    # A' = (b, a) 가 직선 OB 위: B = 2·A'
    assert (2 * bv, 2 * av) == B_VAL
    assert all(v > 0 for v in (*A_VAL, *B_VAL))          # 제1사분면
    # 중점
    assert ((av + B_VAL[0]) / 2, (bv + B_VAL[1]) / 2) == (R(77, 8), R(133, 8))


def test_answer_457():
    ab = A_VAL[0] * A_VAL[1]
    assert ab == R(441, 16)
    p, q = sp.fraction(ab)[1], sp.fraction(ab)[0]
    assert sp.gcd(p, q) == 1
    assert p + q == 457


def test_concept_picture_parameters():
    # project.yaml 의 개념도: A(1, log16 10) → A'(log16 10, 1) → B=(2 log16 10, 2) 가 실제로 curve2 위
    ay = sp.log(10, 16)
    assert sp.simplify(curve1.subs(x, 1) - ay) == 0
    assert sp.simplify(curve2.subs(x, 2 * ay) - 2) == 0
