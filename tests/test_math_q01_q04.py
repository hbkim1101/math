"""2027학년도 9월 모평 공통 1~4번 — 시나리오에 적힌 풀이 단계가 수학적으로 참인지 sympy 로 확인한다."""

import sympy as sp

x, a, d, n, m = sp.symbols("x a d n m")


# ---------------------------------------------------------------- 1번: 2^{3/2} × 4^{-1/2} = 2^{1/2}
def test_q01_each_step_is_equal():
    e0 = sp.Integer(2) ** sp.Rational(3, 2) * sp.Integer(4) ** sp.Rational(-1, 2)
    e1 = sp.Integer(2) ** sp.Rational(3, 2) * (sp.Integer(2) ** 2) ** sp.Rational(-1, 2)   # 4 = 2^2
    e2 = sp.Integer(2) ** sp.Rational(3, 2) * sp.Integer(2) ** (2 * sp.Rational(-1, 2))    # (a^m)^n = a^{mn}
    e3 = sp.Integer(2) ** sp.Rational(3, 2) * sp.Integer(2) ** (-1)
    e4 = sp.Integer(2) ** (sp.Rational(3, 2) - 1)                                          # a^m a^n = a^{m+n}
    e5 = sp.Integer(2) ** sp.Rational(1, 2)
    for u, v in zip([e0, e1, e2, e3, e4], [e1, e2, e3, e4, e5]):
        assert sp.simplify(u - v) == 0
    assert sp.simplify(e5 - sp.sqrt(2)) == 0
    assert 1 < float(e5) < 2
    # 보기 ④ 가 2^{1/2}
    choices = [sp.Integer(2) ** -1, sp.Integer(2) ** sp.Rational(-1, 2), sp.Integer(1), sp.Integer(2) ** sp.Rational(1, 2), sp.Integer(2)]
    assert [sp.simplify(c - e0) == 0 for c in choices].index(True) + 1 == 4


def test_q01_common_mistake_is_wrong():
    assert sp.Integer(4) ** sp.Rational(-1, 2) == sp.Rational(1, 2) != -2


# ---------------------------------------------------------------- 2번: lim (f(x)-f(2))/(x-2) = f'(2) = 23
def test_q02_limit_equals_derivative_and_value_is_23():
    f = 2 * x**3 - x - 4
    lim = sp.limit((f - f.subs(x, 2)) / (x - 2), x, 2)
    fp = sp.diff(f, x)
    assert sp.expand(fp) == 6 * x**2 - 1
    assert fp.subs(x, 2) == 6 * 4 - 1 == 24 - 1 == 23
    assert lim == 23
    assert [19, 21, 23, 25, 27].index(23) + 1 == 3


def test_q02_secant_slope_approaches_23():
    f = sp.Lambda(x, 2 * x**3 - x - 4)
    slope = lambda t: float((f(t) - f(2)) / (t - 2))
    s = [slope(2.42), slope(2.2), slope(2.05), slope(2.003)]
    assert all(s[i] > s[i + 1] for i in range(len(s) - 1))
    assert abs(s[-1] - 23) < 0.1
    # 시각화에 쓴 평균변화율의 닫힌 식: 2(x^2 + 2x + 4) - 1
    assert sp.simplify(sp.cancel((f(x) - f(2)) / (x - 2)) - (2 * (x**2 + 2 * x + 4) - 1)) == 0


# ---------------------------------------------------------------- 3번: a_2 = 2, a_10 - a_7 = 9 → a_7 = 17
def test_q03_arithmetic_sequence():
    a1 = sp.Symbol("a1")
    an = lambda k: a1 + (k - 1) * d
    sol = sp.solve([sp.Eq(an(2), 2), sp.Eq(an(10) - an(7), 9)], [a1, d], dict=True)[0]
    assert sol[d] == 3
    assert an(7).subs(sol) == 17
    # 시나리오의 단계: a_10 - a_7 = 3d, a_7 = a_2 + 5d
    assert sp.simplify(an(10) - an(7) - 3 * d) == 0
    assert sp.simplify(an(7) - (an(2) + 5 * d)) == 0
    assert 2 + 5 * 3 == 2 + 15 == 17
    assert [16, 17, 18, 19, 20].index(17) + 1 == 2


def test_q03_general_identity_in_end_caption():
    a1 = sp.Symbol("a1")
    an = lambda k: a1 + (k - 1) * d
    assert sp.simplify(an(n) - (an(m) + (n - m) * d)) == 0


# ---------------------------------------------------------------- 4번: 연속 ⇔ 14 + a = 4 + 2a → a = 10
def test_q04_continuity_at_2():
    left = 7 * x + a
    right = x**2 + a * x
    l_val = left.subs(x, 2)
    r_lim = sp.limit(right, x, 2, dir="+")
    assert sp.expand(l_val) == 14 + a
    assert sp.expand(r_lim) == 4 + 2 * a
    sol = sp.solve(sp.Eq(l_val, r_lim), a)
    assert sol == [10]
    # 이항 단계: 14 - 4 = 2a - a  ⇔  10 = a
    assert sp.simplify((14 - 4) - (2 * a - a)).subs(a, 10) == 0
    assert sp.solve(sp.Eq(14 - 4, 2 * a - a), a) == [10]
    assert [9, 10, 11, 12, 13].index(10) + 1 == 2


def test_q04_gap_closes_only_at_10():
    gap = (4 + 2 * a) - (14 + a)   # 오른쪽 끝 - 왼쪽 끝
    assert sp.expand(gap) == a - 10
    assert gap.subs(a, 4) == -6      # a = 4: 왼쪽 18, 오른쪽 12 → 틈 6
    assert gap.subs(a, 10) == 0
    f_piece = sp.Piecewise((7 * x + 10, x <= 2), (x**2 + 10 * x, True))
    assert sp.limit(f_piece, x, 2, dir="-") == sp.limit(f_piece, x, 2, dir="+") == f_piece.subs(x, 2) == 24
