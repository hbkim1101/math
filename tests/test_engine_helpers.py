import math

import pytest

from explainer.compose.subtitles import split_long_sentence
from explainer.render.actions import REGISTRY, _reflect_point
from explainer.render.theme import Theme


def test_reflect_point_across_y_eq_x_minus_quarter():
    # A(3/4, 3/2) ↔ D(7/4, 1/2), B(3/2, 9/4) ↔ C(5/2, 5/4)
    assert _reflect_point(0.75, 1.5, 1, -0.25) == pytest.approx((1.75, 0.5))
    assert _reflect_point(1.5, 2.25, 1, -0.25) == pytest.approx((2.5, 1.25))
    # 대칭은 두 번 적용하면 원래대로
    x, y = _reflect_point(*_reflect_point(0.3, -1.2, -2, 0.7), -2, 0.7)
    assert (x, y) == pytest.approx((0.3, -1.2))
    # 직선 위의 점은 고정
    assert _reflect_point(2.0, 1.75, 1, -0.25) == pytest.approx((2.0, 1.75))


def test_theme_color_resolution():
    th = Theme()
    assert th.color("exp") == th.palette["exp"]
    assert th.color("accent") == th.accent
    assert th.color("#123456") == "#123456"
    assert th.color(None, "fallback") == "fallback"


def test_registry_has_core_actions():
    for name in ["axes", "plot", "point", "points", "polygon", "reflect", "translate_copy",
                 "board", "board_write", "problem", "problem_dock", "problem_focus", "dim", "undim",
                 "caption", "answer", "custom"]:
        assert name in REGISTRY


def test_problem_focus_is_noop_without_lines():
    """problem 을 tex 한 덩어리로 그린 경우 problem_focus 는 아무 것도 재생하지 않아야 한다."""
    class FakeScene:
        problem_lines = []
        objs = {}
        played = 0

        def play(self, *a, **k):
            self.played += 1

    sc = FakeScene()
    REGISTRY["problem_focus"](sc, index=2)
    assert sc.played == 0 and sc.objs == {}


def test_split_long_sentence_prefers_commas():
    text = "첫 번째 구절은 여기까지이고, 두 번째 구절은 조금 더 길게 이어지며, 세 번째 구절로 마무리합니다."
    pieces = split_long_sentence(text, max_chars=30)
    assert len(pieces) >= 2
    assert all(len(p) <= 30 for p in pieces)
    assert " ".join(pieces) == text
    assert split_long_sentence("짧다.", 30) == ["짧다."]


def test_clipped_pieces_splits_out_of_range_parts():
    from explainer.render.scene import ExplainerScene

    f = lambda x: 1.0 / x if x != 0 else float("inf")
    pieces = ExplainerScene.clipped_pieces(None, f, (-2.0, 2.0), (-3.0, 3.0), samples=801)
    # 1/x 는 y∈[-3,3] 범위에서 x≤-1/3, x≥1/3 두 조각으로 나뉜다
    assert len(pieces) == 2
    (a0, a1), (b0, b1) = pieces
    assert a0 == pytest.approx(-2.0) and a1 == pytest.approx(-1 / 3, abs=0.02)
    assert b0 == pytest.approx(1 / 3, abs=0.02) and b1 == pytest.approx(2.0)
