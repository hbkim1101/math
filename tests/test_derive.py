"""식 전개(derive) 엔진의 조각 매칭 규칙 테스트 — 렌더 없이 순수 함수 `plan_match` 만 검사한다."""

from explainer.render.derive import DerivLine, _eq_index, is_operator, plan_match


def _line(parts):
    class _M:  # MathTex 대용 (plan_match 는 parts 와 eq_index 만 쓴다)
        submobjects = []
    return DerivLine(parts=parts, mob=_M(), eq_index=_eq_index(parts))


def test_first_line_everything_is_new():
    p = plan_match(None, ["2^{3}", "\\times", "4"])
    assert p.new == [0, 2] and p.ops == [1]
    assert not p.slide and not p.morph and not p.move


def test_unchanged_parts_slide_and_changed_part_morphs_from_source():
    prev = _line(["=", "2^{3/2}", "\\times", "(2^2)^{-1/2}"])
    p = plan_match(prev, ["=", "2^{3/2}", "\\times", "2^{-1}"])
    assert set(p.slide) == {(0, 0), (1, 1), (2, 2)}
    assert p.morph == [(3, 3)]
    assert p.new == [] and p.sources == []


def test_two_sources_merge_into_one_target():
    prev = _line(["=", "2^{3/2}", "\\times", "2^{-1}"])
    p = plan_match(prev, ["=", "2^{3/2-1}"])
    assert (1, 1) in p.morph and (3, 1) in p.morph
    assert p.new == []


def test_transposition_is_detected_as_move_with_new_signs():
    prev = _line(["14", "+", "a", "=", "4", "+", "2a"])
    p = plan_match(prev, ["14", "-", "4", "=", "2a", "-", "a"])
    # 4 는 우변→좌변, a 는 좌변→우변으로 등호를 건너간다
    assert (4, 2) in p.move and (2, 6) in p.move
    assert (0, 0) in p.slide and (3, 3) in p.slide and (6, 4) in p.slide
    # 새 부호(-) 두 개는 연산자로 새로 쓴다
    assert sorted(p.ops) == [1, 5]
    assert p.new == []


def test_explicit_from_map_for_substitution_reuses_single_source():
    prev = _line(["f'(x)", "=", "6", "x^{2}", "-", "1"])
    p = plan_match(prev, ["f'(2)", "=", "6", "\\cdot", "2^{2}", "-", "1"], from_map={"f'(2)": "f'(x)", "2^{2}": "x^{2}"})
    assert (0, 0) in p.morph and (3, 4) in p.morph
    assert (2, 2) in p.slide and (5, 6) in p.slide
    assert 3 in p.ops  # 새 \cdot


def test_from_map_with_list_merges_many_sources_explicitly():
    prev = _line(["14", "-", "4", "=", "2a", "-", "a"])
    p = plan_match(prev, ["10", "=", "a"], from_map={"10": ["14", "4"], "a": ["2a", "a"]})
    assert (0, 0) in p.morph and (2, 0) in p.morph
    assert (4, 2) in p.morph and (6, 2) in p.morph
    assert p.slide == [(3, 1)]
    assert p.new == [] and p.sources == []


def test_focus_restricts_sources_and_new_marks_fresh_targets():
    prev = _line(["f'(x)", "=", "2\\cdot3x^{2}", "-", "1", "-", "0"])
    p = plan_match(prev, ["f'(x)", "=", "6", "x^{2}", "-", "1"], focus=["2\\cdot3x^{2}"], new=["6", "x^{2}"])
    assert p.morph == [(2, 2)]
    assert p.new == [3]
    assert (0, 0) in p.slide and (4, 5) in p.slide


def test_same_string_twice_uses_nearest_unused_source():
    prev = _line(["a_{10}", "-", "a_{7}", "=", "9"])
    p = plan_match(prev, ["a_7", "+", "3d", "-", "a_{7}", "=", "9"], from_map={"a_7": "a_{10}"})
    assert (0, 0) in p.morph
    assert (2, 4) in p.slide and (1, 3) in p.slide and (3, 5) in p.slide and (4, 6) in p.slide
    assert sorted(p.new) == [2] and p.ops == [1]


def test_chained_equality_does_not_use_left_side_as_source():
    # a_7 = a_2 + 5d  →  = 2 + 5·3 : 좌변 a_7 은 그대로이므로 출처(상자)가 되지 않아야 한다
    prev = _line(["a_{7}", "=", "a_{2}", "+", "5d"])
    p = plan_match(prev, ["=", "2", "+", "5\\cdot3"], from_map={"2": "a_{2}", "5\\cdot3": "5d"})
    assert sorted(p.morph) == [(2, 1), (4, 3)]
    assert all(j != 0 for j, _ in p.morph) and p.sources == []
    # from 없이 자동 짝짓기를 해도 마찬가지
    p2 = plan_match(prev, ["=", "2", "+", "15"])
    assert all(j != 0 for j, _ in p2.morph)


def test_operator_set():
    assert is_operator("=") and is_operator("\\times") and is_operator(" + ")
    assert not is_operator("x") and not is_operator("2^{-1}")
