"""칠판(chalkboard) 스타일 엔진: 캔버스 배치, 판서 커서, 질감 생성, 테마."""

import numpy as np
import pytest
from manim import Square

from explainer.render.actions import REGISTRY
from explainer.render.chalk import Canvas, Section, chalk_theme, chalkboard_texture, chalkify, handwrite_time
from explainer.script.models import ChalkLayout, Project


class _FakeScene:
    """카메라 프레임만 있는 최소 씬. play 는 애니메이션을 끝 상태로 바로 적용한다."""

    def __init__(self):
        from manim import Rectangle
        self.camera = type("Cam", (), {})()
        self.camera.frame = Rectangle(width=14.2, height=8.0)
        self.plays = 0

    def play(self, *anims, **k):
        self.plays += 1
        for a in anims:
            a.begin()
            a.interpolate(1.0)
            a.finish()


def _layout(**kw):
    return ChalkLayout(sections=[
        {"id": "title", "layout": "full"},
        {"id": "p", "title": "문제", "layout": "full"},
        {"id": "s1", "title": "풀이 1", "layout": "split"},
    ], **kw)


def test_sections_are_laid_out_left_to_right_without_overlap():
    cv = Canvas(_FakeScene(), _layout())
    xs = [s.center_x for s in cv.sections]
    assert xs == sorted(xs)
    for a, b in zip(cv.sections, cv.sections[1:]):
        assert b.left - a.right == pytest.approx(cv.gap)
    assert cv.total_width == pytest.approx(3 * (cv.width + cv.gap))


def test_split_section_has_graph_area_left_of_notes():
    cv = Canvas(_FakeScene(), _layout())
    s1 = cv.section("s1")
    gx, _ = s1.graph_center
    assert s1.left < gx < s1.notes_left < s1.right
    assert s1.notes_left - (s1.left + cv.margin) >= s1.graph_width
    # 제목이 있는 섹션은 제목 높이만큼 커서가 내려가 있다
    assert s1.cursor_y == pytest.approx(s1.top - cv.margin - cv.title_height)
    assert cv.section("title").cursor_y == pytest.approx(cv.height / 2 - cv.margin)


def test_place_line_moves_cursor_down_and_aligns_left():
    cv = Canvas(_FakeScene(), _layout())
    sec = cv.section("p")
    y0 = sec.cursor_y
    sq = Square(side_length=0.5)
    cv.place_line(sq, indent=0.3, sec=sec)
    assert sq.get_left()[0] == pytest.approx(sec.notes_left + 0.3)
    assert sq.get_top()[1] == pytest.approx(y0)
    assert sec.cursor_y == pytest.approx(y0 - 0.5 - cv.line_gap)
    # 판서 폭보다 넓은 줄은 폭에 맞춰 줄어든다
    wide = Square(side_length=40)
    cv.place_line(wide, sec=sec)
    assert wide.width <= sec.notes_width + 1e-6


def test_goto_snaps_first_then_flies():
    sc = _FakeScene()
    cv = Canvas(sc, _layout())
    cv.goto("title", write_title=False)
    assert sc.plays == 0  # 첫 방문은 애니메이션 없이 카메라를 바로 놓는다
    assert cv.frame.width == pytest.approx(cv.width)
    cv.goto("s1", write_title=False)
    assert sc.plays == 1
    assert cv.current.id == "s1"
    # 비행이 끝나면 카메라는 목표 섹션을 꽉 차게 본다
    assert cv.frame.width == pytest.approx(cv.width, rel=1e-3)
    assert cv.frame.get_center()[0] == pytest.approx(cv.section("s1").center_x, abs=1e-3)


def test_unknown_section_raises():
    cv = Canvas(_FakeScene(), _layout())
    with pytest.raises(KeyError):
        cv.section("nope")


def test_chalkboard_texture_is_cached_and_board_colored(tmp_path):
    p1 = chalkboard_texture(tmp_path, 320, 120, "#24493a")
    p2 = chalkboard_texture(tmp_path, 320, 120, "#24493a")
    assert p1 == p2 and p1.exists()
    from PIL import Image
    im = np.asarray(Image.open(p1).convert("RGB"), dtype=float)
    assert im.shape == (120, 320, 3)
    mean = im.reshape(-1, 3).mean(axis=0)
    # 평균색은 칠판 바탕색(0x24,0x49,0x3a) 근처, 초록이 가장 강하다
    assert abs(mean[1] - 0x49) < 18 and mean[1] > mean[0] and mean[1] > mean[2]
    assert im.std() > 2.0  # 완전히 균일한 색이 아니다 (질감)


def test_chalk_theme_uses_handwriting_fonts():
    th = chalk_theme()
    assert th.chalk is True
    assert th.font == "NanumBarunpen" and th.title_font == "Nanum Pen Script"
    assert "NanumBarunpen" in th.ko_template.preamble
    assert th.color("chalk") == th.palette["chalk"]


def test_chalkify_adds_thin_stroke_to_filled_glyphs():
    sq = Square(fill_opacity=1, stroke_width=0)
    chalkify(sq)
    assert sq.get_stroke_width() > 0
    assert 0.6 <= handwrite_time(sq) <= 3.4


def test_project_meta_style_and_chalk_layout_parse():
    proj = Project.model_validate({
        "meta": {"id": "x", "title": "t", "style": "chalkboard"},
        "layout": {"chalk": {"sections": [{"id": "a", "layout": "full"}]}},
        "segments": [{"id": "s", "narration": "안녕", "actions": [{"do": "goto", "section": "a"}]}],
    })
    assert proj.meta.style == "chalkboard"
    assert proj.layout.chalk.sections[0]["id"] == "a"
    assert Project.model_validate({"meta": {"id": "x", "title": "t"}, "segments": [{"id": "s"}]}).meta.style == "panel"


def test_chalk_actions_registered_and_reject_panel_style():
    for name in ["goto", "write", "camera", "space"]:
        assert name in REGISTRY

    class PanelScene:
        chalk = None

    with pytest.raises(RuntimeError):
        REGISTRY["goto"](PanelScene(), section="a")
