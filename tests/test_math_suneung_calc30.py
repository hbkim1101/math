"""2026학년도 수능 미적분 30번 시나리오(projects/2026_suneung_calc30)의 수학적 주장들을 sympy 로 검증한다.

문제: 실수 전체에서 증가하는 연속함수 f 의 역함수가
      (가) |x|≤1: 4(f⁻¹(x))² = x²(x²−5)²,   (나) |x|>1: |f⁻¹(x)| = e^{|x|−1}+1
      을 만족. 기울기 m, 점 (1,0) 을 지나는 직선과 y=f(x) 의 교점 개수 g(m) 이 m=a, m=b (a<b) 에서 불연속일 때
      g(a)·lim_{m→a+} g(m) + g(b)·(ln b / b)² = ?   (정답 11)
"""

import math

import pytest
import sympy as sp

x, t, k = sp.symbols("x t k", real=True)

h_left = -sp.exp(-x - 1) - 1          # x < -1
h_mid = -sp.Rational(1, 2) * x * (x**2 - 5)   # -1 <= x <= 1
h_right = sp.exp(x - 1) + 1           # x > 1


def h_num(v: float) -> float:
    if v < -1:
        return -math.exp(-v - 1) - 1
    if v <= 1:
        return -0.5 * v * (v * v - 5)
    return math.exp(v - 1) + 1


def test_candidates_from_conditions():
    # (가) 4h² = x²(x²-5)²  ⇔  2h = ±x(x²-5)  — 선택한 가지가 조건을 만족
    assert sp.simplify(4 * h_mid**2 - x**2 * (x**2 - 5) ** 2) == 0
    # (나) |h| = e^{|x|-1}+1 — x>1 은 +, x<-1 은 - 가지
    assert sp.simplify(sp.Abs(h_right).subs(x, 2) - (sp.exp(2 - 1) + 1)) == 0
    assert sp.simplify(sp.Abs(h_left).subs(x, -2) - (sp.exp(2 - 1) + 1)) == 0


def test_only_increasing_branch_survives():
    # 가운데 구간: x(x²-5) 는 [-1,1] 에서 감소 → -½x(x²-5) 가 증가, +½x(x²-5) 는 감소
    d_plus = sp.diff(sp.Rational(1, 2) * x * (x**2 - 5), x)
    d_minus = sp.diff(h_mid, x)
    for v in (-1, -0.5, 0, 0.5, 1):
        assert d_plus.subs(x, v) < 0 and d_minus.subs(x, v) > 0
    # 바깥 구간의 도함수도 양수
    assert sp.diff(h_left, x).subs(x, -3) > 0 and sp.diff(h_right, x).subs(x, 3) > 0


def test_pieces_join_continuously_and_smoothly():
    assert h_mid.subs(x, -1) == -2 and h_left.subs(x, -1) == -2
    assert h_mid.subs(x, 1) == 2 and h_right.subs(x, 1) == 2
    # 기울기 1 로 매끄럽게 연결 (그래서 (1,2) 근방에서 직선 y=x+1 은 곡선을 '뚫고' 지나간다)
    assert sp.diff(h_mid, x).subs(x, -1) == 1 == sp.diff(h_left, x).subs(x, -1)
    assert sp.diff(h_mid, x).subs(x, 1) == 1 == sp.diff(h_right, x).subs(x, 1)
    # h(0)=0 → f(0)=0 : m=0 일 때 교점은 x=0 하나
    assert h_mid.subs(x, 0) == 0


def test_reflected_line():
    # y = m(x-1) 를 y=x 에 대칭이동하면 y = x/m + 1  (점 (1,0) ↔ (0,1))
    m = sp.symbols("m", nonzero=True)
    X, Y = sp.symbols("X Y")
    # (X, Y) 가 원래 직선 위 ⇔ (Y, X) 가 대칭 직선 위
    orig = sp.Eq(Y, m * (X - 1))
    refl = sp.Eq(X, Y / m + 1)
    assert sp.simplify(sp.solve(orig, Y)[0] - sp.solve(refl, Y)[0]) == 0


def count_intersections(kk: float, lo=-40.0, hi=40.0, n=200000) -> int:
    """직선 y = kk·x + 1 과 y = h(x) 의 교점 개수 (부호 변화 + 접점)."""
    g = lambda v: h_num(v) - (kk * v + 1)
    xs = [lo + (hi - lo) * i / n for i in range(n + 1)]
    vals = [g(v) for v in xs]
    cnt = 0
    for i in range(n):
        if vals[i] == 0 or vals[i] * vals[i + 1] < 0:
            cnt += 1
    return cnt


@pytest.fixture(scope="module")
def k_b():
    return float(sp.nsolve(k * sp.log(k) - 2, k, 2.3))


def test_k_b_solves_k_ln_k_equals_2(k_b):
    assert abs(k_b * math.log(k_b) - 2) < 1e-10
    assert abs(k_b - 2.34575) < 2e-5           # project.yaml 의 params.k_b
    # 접점: t = -1 - ln k_b (<-1) 에서 (0,1) 과 잇는 기울기 = 접선의 기울기
    tt = -1 - math.log(k_b)
    assert tt < -1
    slope_chord = (h_num(tt) - 1) / (tt - 0)
    slope_tan = math.exp(-tt - 1)
    assert abs(slope_chord - slope_tan) < 1e-9 and abs(slope_tan - k_b) < 1e-9


def test_intersection_counts_by_slope(k_b):
    # 역함수 쪽 기울기 k 에 따른 교점 개수 (원함수 쪽 m = 1/k)
    assert count_intersections(-1.5) == 1        # k<0  (m<0)      → 1
    assert count_intersections(0.6) == 1         # 0<k<1 (m>1)     → 1
    assert count_intersections(1.0) == 1         # k=1: (1,2) 변곡점에서 접하지만 뚫고 지나감 → 1
    assert count_intersections(1.8) == 1         # 1<k<k_b (b<m<1) → 1
    assert count_intersections(3.4) == 3         # k>k_b (0<m<b)   → 3
    assert count_intersections(30.0) == 3        # k→∞ (m→0+)      → 3
    # k = k_b 근처: 접점을 사이에 두고 1 ↔ 3 으로 바뀐다 (접하는 순간 자체는 2)
    assert count_intersections(k_b - 1e-3) == 1 and count_intersections(k_b + 1e-3) == 3


def test_g_of_m_and_answer(k_b):
    b = 1 / k_b
    g_a, lim_a_plus, g_b = 1, 3, 2               # a = 0
    assert abs((math.log(b) / b) ** 2 - 4) < 1e-9   # (ln b / b)² = (k_b ln k_b)² = 4
    assert g_a * lim_a_plus + g_b * 4 == 11
    assert 0 < b < 1 and abs(b - 0.4263) < 1e-3
