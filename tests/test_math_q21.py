"""21번 데모 시나리오의 수학적 주장들을 sympy 로 검증한다.

문제: 2027학년도 9월 모의평가 수학 공통 21번
  최고차항의 계수가 1인 삼차함수 f 가
  (가) f(x)=0 의 서로 다른 실근의 개수는 2
  (나) g(x) = -f(x) (f≥0), 7f(x) (f<0) 일 때, 어떤 실수 a 에 대하여
       h(x) = g(x) + |(x-1)(x-a)(x-4+a)| 가 실수 전체에서 미분가능
  일 때 f(0) 의 최댓값과 최솟값의 곱은?  (정답 12)
"""

import itertools

import sympy as sp
from sympy import Rational as R

x = sp.symbols("x", real=True)
r, s, a = sp.symbols("r s a", real=True)

f = (x - r) ** 2 * (x - s)
w = (x - 1) * (x - a) * (x - 4 + a)


def one_sided_slopes(expr, x0, h=R(1, 10**7)):
    """좌·우 미분계수. 유리수로 정확히 계산한 차분몫을 소수 4자리에서 반올림해 단순 분수로 복원한다
    (문제의 모든 기울기는 분모가 작은 유리수)."""
    left = (expr.subs(x, x0) - expr.subs(x, x0 - h)) / h
    right = (expr.subs(x, x0 + h) - expr.subs(x, x0)) / h
    return sp.nsimplify(round(float(left), 4)), sp.nsimplify(round(float(right), 4))


def g_of(fx):
    return sp.Piecewise((-fx, fx >= 0), (7 * fx, True))


def test_derivative_of_f_at_simple_root():
    # f'(s) = (s-r)^2, f'(r) = 0
    fp = sp.diff(f, x)
    assert sp.simplify(fp.subs(x, s) - (s - r) ** 2) == 0
    assert sp.simplify(fp.subs(x, r)) == 0


def test_g_has_single_corner_at_s_with_jump_minus_8():
    # 구체적 값으로 좌우 기울기 확인: r=1/2, s=1 → g'(1-)=7/4, g'(1+)=-1/4
    fx = f.subs({r: R(1, 2), s: 1})
    gx = g_of(fx)
    left, right = one_sided_slopes(gx, 1)
    assert left == R(7, 4) and right == -R(1, 4)
    assert right - left == -8 * (1 - R(1, 2)) ** 2
    # 중근 r=1/2 에서는 좌우 기울기 모두 0 (매끄럽다)
    left, right = one_sided_slopes(gx, R(1, 2))
    assert left == 0 and right == 0


def test_abs_w_corner_jump_is_twice_abs_derivative():
    # a=1/2 : 단순근 1 에서 |w| 의 기울기 변화 = 2|w'(1)|
    wx = w.subs(a, R(1, 2))
    wp = sp.diff(wx, x).subs(x, 1)
    left, right = one_sided_slopes(sp.Abs(wx), 1)
    assert right - left == 2 * abs(wp)
    # a=2 : 중근 2 에서는 매끄럽다
    wx2 = w.subs(a, 2)
    left, right = one_sided_slopes(sp.Abs(wx2), 2)
    assert left == 0 and right == 0


def test_roots_must_coincide_a_in_1_2_3():
    roots = [sp.Integer(1), a, 4 - a]
    sols = set()
    for p, q in itertools.combinations(roots, 2):
        for sol in sp.solve(sp.Eq(p, q), a):
            sols.add(sol)
    assert sols == {1, 2, 3}
    # 삼중근은 불가능
    assert sp.solve([sp.Eq(1, a), sp.Eq(a, 4 - a)], a) == []


def _f0_values_for(a_val):
    """a 가 정해졌을 때 조건 2|w'(s)| = 8(s-r)^2 에서 나오는 f(0) 값들."""
    wx = sp.expand(w.subs(a, a_val))
    root_mult = sp.roots(sp.Poly(wx, x))
    simple = [rt for rt, m in root_mult.items() if m == 1]
    assert len(simple) == 1
    s_val = simple[0]
    wp = abs(sp.diff(wx, x).subs(x, s_val))
    r_sols = sp.solve(sp.Eq(2 * wp, 8 * (s_val - r) ** 2), r)
    return {f.subs({s: s_val, r: rv, x: 0}) for rv in r_sols}, s_val, r_sols


def test_case_a1_gives_minus12_minus48():
    vals, s_val, r_sols = _f0_values_for(1)
    assert s_val == 3 and set(r_sols) == {2, 4}
    assert vals == {-12, -48}
    assert _f0_values_for(3)[0] == vals  # a=3 은 a=1 과 같은 w


def test_case_a2_gives_minus_quarter_minus_9_over_4():
    vals, s_val, r_sols = _f0_values_for(2)
    assert s_val == 1 and set(r_sols) == {R(1, 2), R(3, 2)}
    assert vals == {-R(1, 4), -R(9, 4)}


def test_h_is_differentiable_in_found_cases():
    for a_val, r_val, s_val in [(1, 2, 3), (1, 4, 3), (2, R(1, 2), 1), (2, R(3, 2), 1)]:
        fx = f.subs({r: r_val, s: s_val})
        hx = g_of(fx) + sp.Abs(w.subs(a, a_val))
        for x0 in {1, a_val, 4 - a_val, r_val, s_val}:
            left, right = one_sided_slopes(hx, x0)
            assert left == right, (a_val, r_val, x0, left, right)


def test_final_answer_is_12():
    all_vals = set().union(_f0_values_for(1)[0], _f0_values_for(2)[0], _f0_values_for(3)[0])
    assert all_vals == {-48, -12, -R(9, 4), -R(1, 4)}
    assert max(all_vals) * min(all_vals) == 12
