"""액션 라이브러리: YAML 의 `do:` 이름을 Manim 애니메이션으로 변환한다.

각 핸들러는 `handler(scene, **params)` 형태이며 스스로 scene.play(...) 를 호출한다.
"""

from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, UL, UR, DL, DR, ORIGIN, PI,
    Angle, Arrow, Circumscribe, Create, DashedLine, DashedVMobject, Dot, FadeIn, FadeOut, Flash,
    GrowArrow, GrowFromCenter, Indicate, Line, MathTex, Mobject, MoveAlongPath, NumberPlane,
    Polygon, Rectangle, ReplacementTransform, RoundedRectangle, SurroundingRectangle, Transform,
    TransformFromCopy, TransformMatchingTex, VGroup, VMobject, Write, Axes, AnimationGroup,
    LaggedStart, Wiggle, ShowPassingFlash, Uncreate, Text, BackgroundRectangle, always_redraw,
    ManimColor, Elbow, RightAngle, smooth, linear, there_and_back, TracedPath, ValueTracker, config,
)

from ..script.models import Action
from .board import Board
from .chalk import handwrite, handwrite_time, pin_to_frame

Handler = Callable[..., None]
REGISTRY: dict[str, Handler] = {}


def action(name: str):
    def deco(fn: Handler) -> Handler:
        REGISTRY[name] = fn
        return fn
    return deco


def run_action(scene, act: Action) -> None:
    fn = REGISTRY.get(act.do)
    if fn is None:
        raise KeyError(f"알 수 없는 액션: {act.do!r} (사용 가능: {sorted(REGISTRY)})")
    params = act.params
    if act.run_time is not None:
        params["run_time"] = act.run_time
    fn(scene, **params)


def _rt(params_rt: float | None, default: float) -> float:
    return default if params_rt is None else float(params_rt)


# ====================================================================== 카드/전환
@action("title_card")
def title_card(scene, title: str, subtitle: str = "", run_time: float | None = None, tag: str = "",
               id: str = "title_card", **_):
    rt = _rt(run_time, 1.6)
    chalk = scene.theme.chalk
    t = scene.ktext(title, size=58 if not chalk else 66, weight="BOLD" if not chalk else "NORMAL",
                    font=scene.theme.title_font)
    parts = [t]
    if subtitle:
        s = scene.ktext(subtitle, size=32 if not chalk else 38, color=scene.theme.muted, font=scene.theme.title_font)
        parts.append(s)
    if tag:
        g = scene.ktext(tag, size=22 if not chalk else 30, color=scene.theme.accent, font=scene.theme.title_font)
        parts.append(g)
    group = VGroup(*parts).arrange(DOWN, buff=0.4).move_to(scene.view_center)
    underline = Line(LEFT * 2.2, RIGHT * 2.2, stroke_width=3, color=scene.theme.accent)
    underline.next_to(t, DOWN, buff=0.25)
    if subtitle:
        group[1].next_to(underline, DOWN, buff=0.35)
        if tag:
            group[2].next_to(group[1], DOWN, buff=0.35)
    full = VGroup(group, underline)
    scene.register(id, full)
    if chalk:
        # 칠판에 직접 손으로 써 내려가는 타이틀
        scene.play(handwrite(t, run_time=max(rt * 0.6, 1.2)))
        scene.play(Create(underline, run_time=0.35))
        for p in parts[1:]:
            scene.play(handwrite(p, run_time=min(1.4, handwrite_time(p))))
        return
    scene.play(FadeIn(t, shift=UP * 0.3), run_time=rt * 0.5)
    scene.play(Create(underline), *(FadeIn(p, shift=UP * 0.2) for p in parts[1:]), run_time=rt * 0.5)


@action("end_card")
def end_card(scene, title: str, subtitle: str = "", run_time: float | None = None, id: str = "end_card",
             lines: list[str] | None = None, **_):
    """마무리 카드. chalkboard 스타일에서는 현재 섹션에 손글씨로 정리 문장(lines)을 써 내려간다."""
    rt = _rt(run_time, 1.4)
    chalk = scene.theme.chalk
    t = scene.ktext(title, size=54 if not chalk else 50, weight="BOLD" if not chalk else "NORMAL",
                    font=scene.theme.title_font)
    items = [t]
    if subtitle:
        s = scene.ktext(subtitle, size=30 if not chalk else 32, color=scene.theme.muted, font=scene.theme.title_font)
        if s.width > 12.5:
            s.scale_to_fit_width(12.5)
        items.append(s)
    for ln in lines or []:
        items.append(scene.ktext(ln, size=30 if not chalk else 32, color=scene.theme.muted,
                                 font=scene.theme.title_font))
    g = VGroup(*items).arrange(DOWN, buff=0.4).move_to(scene.view_center)
    if g.width > 12.5:
        g.scale_to_fit_width(12.5)
    scene.register(id, g)
    if chalk:
        if scene.chalk is not None:
            # 칠판: 현재 섹션의 판서 커서 아래에 왼쪽 정렬로 이어 쓴다
            _drop_caption(scene)
            g.arrange(DOWN, buff=0.3, aligned_edge=LEFT)
            scene.chalk.place_line(g, space=0.4)
        scene.play(handwrite(t, run_time=max(1.0, rt * 0.7)))
        for m in items[1:]:
            scene.play(handwrite(m, run_time=min(1.6, handwrite_time(m))))
        return
    scene.play(FadeIn(g, shift=UP * 0.2), run_time=rt)


@action("clear")
def clear(scene, ids: list[str] | None = None, keep: list[str] | None = None, run_time: float | None = None,
          board: bool = False, **_):
    """ids 가 없으면 화면 전체(보드 프레임 제외)를 페이드아웃."""
    rt = _rt(run_time, 0.7)
    keep = set(keep or [])
    if ids:
        targets = [scene.get(i) for i in ids if i in scene.objs]
        for i in ids:
            scene.objs.pop(i, None)
            scene.coords.pop(i, None)
    else:
        protected = set()
        if scene.board is not None and not board:
            protected.update(id(m) for m in scene.board.all_mobjects())
        if scene.chalk is not None:
            # 칠판 자체(질감·테두리)와 섹션 제목은 지우지 않는다
            protected.update(id(m) for m in getattr(scene.chalk, "background_parts", []))
            protected.update(id(s.title_mob) for s in scene.chalk.sections if s.title_mob is not None)
        for k in keep:
            if k in scene.objs:
                protected.add(id(scene.objs[k]))
        targets = [m for m in list(scene.mobjects) if id(m) not in protected]
        for k in list(scene.objs):
            if k not in keep:
                scene.objs.pop(k, None)
                scene.coords.pop(k, None)
        if board and scene.board is not None:
            scene.board.lines.clear()
            scene.board.header = None
        scene.caption = None
        if not board:
            # 보드 줄은 남기되 그래프 영역만 지우는 경우, 보드 줄 객체는 보호되어야 함
            pass
    if targets:
        scene.play(*(FadeOut(m) for m in targets), run_time=rt)


@action("wait")
def wait(scene, seconds: float = 1.0, **_):
    scene.wait(float(seconds))


@action("section")
def section(scene, text: str, run_time: float | None = None, id: str = "section", **_):
    """화면 상단 중앙의 섹션 배너(작은 타이틀). 기존 배너는 교체."""
    rt = _rt(run_time, 0.7)
    label = scene.ktext(text, size=26, weight="BOLD", color=scene.theme.accent)
    bg = RoundedRectangle(corner_radius=0.12, width=label.width + 0.6, height=label.height + 0.3,
                          fill_color=scene.theme.panel, fill_opacity=0.9,
                          stroke_color=scene.theme.panel_border, stroke_width=1)
    g = VGroup(bg, label).to_edge(UP, buff=0.18)
    if scene.axes is not None:
        g.set_x(scene.axes.get_center()[0])
    old = scene.objs.get(id)
    scene.register(id, g)
    if old is not None:
        scene.play(FadeOut(old, shift=UP * 0.2), FadeIn(g, shift=UP * 0.2), run_time=rt)
    else:
        scene.play(FadeIn(g, shift=DOWN * 0.2), run_time=rt)


# ====================================================================== 문제 패널 / 보드
@action("problem")
def problem(scene, tex: str | None = None, lines: list[str] | None = None, width: float = 12.0,
            scale: float = 0.85, run_time: float | None = None, id: str = "problem", title: str = "",
            line_buff: float = 0.32, **_):
    """문제 전문을 화면 중앙에 크게 보여준다 (한글+수식, xelatex). width: 표시 폭(Manim 단위).

    `lines` 로 주면 줄(문장)별로 따로 렌더되어 `problem_focus` 로 읽는 위치를 따라갈 수 있다.
    """
    rt = _rt(run_time, 1.8)
    chalk = scene.theme.chalk and scene.chalk is not None
    if chalk:
        # 칠판: 현재 섹션 판서 폭에 맞춰 줄마다 손글씨로 써 내려간다
        sec = scene.chalk.section()
        width = min(width, sec.notes_width)
    line_mobs: list[Mobject] = []
    if lines:
        line_mobs = [scene.ktex(s, width=width, scale=scale) for s in lines]
        body = VGroup(*line_mobs).arrange(DOWN, buff=line_buff, aligned_edge=LEFT)
    else:
        assert tex is not None, "problem 액션에는 tex 또는 lines 가 필요합니다"
        body = scene.ktex(tex, width=width, scale=scale)
    items = []
    if title:
        items.append(scene.ktext(title, size=30 if not chalk else 36, weight="BOLD" if not chalk else "NORMAL",
                                 color=scene.theme.accent, font=scene.theme.title_font))
    items.append(body)
    g = VGroup(*items).arrange(DOWN, buff=0.35, aligned_edge=LEFT)
    if not chalk:
        if g.width > 12.8:
            g.scale_to_fit_width(12.8)
        if g.height > 5.9:
            g.scale_to_fit_height(5.9)
        g.move_to([0, 0.55, 0])  # 하단 자막 영역을 피해 약간 위에 배치
    else:
        avail_h = sec.cursor_y - (sec.bottom + scene.chalk.margin)
        if g.height > avail_h:
            g.scale_to_fit_height(avail_h)
        g.move_to([sec.notes_left, sec.cursor_y, 0], aligned_edge=UL)
        sec.cursor_y = g.get_bottom()[1] - scene.chalk.line_gap
    scene.register(id, g)
    scene.problem_lines = line_mobs
    for i, m in enumerate(line_mobs):
        scene.register(f"{id}_line_{i}", m)
    if chalk:
        pieces = ([items[0]] if title else []) + (line_mobs or [body])
        for m in pieces:
            scene.play(handwrite(m, run_time=min(2.4, handwrite_time(m, per_glyph=0.03))))
        return
    scene.play(FadeIn(g, shift=UP * 0.2), run_time=rt)


@action("problem_focus")
def problem_focus(scene, index: int, id: str = "problem", run_time: float | None = None,
                  dim_opacity: float = 0.32, color: str | None = None, **_):
    """`problem` 을 lines 로 그렸을 때, 내레이션이 읽고 있는 줄만 밝게 하고 왼쪽에 포인터 바를 둔다."""
    lines = list(getattr(scene, "problem_lines", None) or [])
    if not lines:
        return
    rt = _rt(run_time, 0.6)
    index = max(0, min(int(index), len(lines) - 1))
    accent = scene.color(color, scene.theme.accent)
    target = lines[index]
    anims = [Transform(m, _opacity_target(m, 1.0 if i == index else dim_opacity)) for i, m in enumerate(lines)]
    bar = Rectangle(width=0.09, height=target.height + 0.22, fill_color=accent, fill_opacity=1, stroke_width=0)
    bar.next_to(target, LEFT, buff=0.28).set_z_index(3)
    old = scene.objs.get(f"{id}_focus")
    scene.register(f"{id}_focus", bar)
    if old is not None:
        anims.append(ReplacementTransform(old, bar))
    else:
        anims.append(FadeIn(bar, shift=RIGHT * 0.15))
    scene.play(*anims, run_time=rt)


@action("board")
def board_init(scene, run_time: float | None = None, **_):
    """오른쪽 보드 패널 생성."""
    rt = _rt(run_time, 0.8)
    scene.board = Board(scene.project.layout.board, scene.theme)
    scene.play(FadeIn(scene.board.frame), FadeIn(scene.board.title), run_time=rt)


@action("problem_dock")
def problem_dock(scene, id: str = "problem", run_time: float | None = None, tex: str | None = None,
                 width: float | None = None, scale: float = 0.62, **_):
    """중앙의 문제를 보드 헤더로 축소 이동. tex 를 주면 요약본으로 교체한다."""
    rt = _rt(run_time, 1.2)
    assert scene.board is not None, "board 액션이 먼저 필요합니다"
    src = scene.objs.get(id)
    if tex is not None:
        w = width if width is not None else scene.board.content_width
        target = scene.ktex(tex, width=w, scale=scale)
    else:
        target = src.copy()
    scene.board.header_target_position(target)
    # ReplacementTransform 은 대상이 원본(문제 패널)의 그리기 순서를 물려받아 보드 프레임 뒤로 숨을 수 있다
    target.set_z_index(3)
    shift_anims = scene.board.make_room_for_header(target)
    focus = scene.objs.pop(f"{id}_focus", None)
    if focus is not None:
        shift_anims.append(FadeOut(focus))
    for i in range(len(getattr(scene, "problem_lines", None) or [])):
        scene.objs.pop(f"{id}_line_{i}", None)
    scene.problem_lines = []
    if src is not None:
        scene.play(ReplacementTransform(src, target), *shift_anims, run_time=rt)
        scene.objs.pop(id, None)
    else:
        scene.play(FadeIn(target), *shift_anims, run_time=rt)
    scene.board.header = target
    scene.register("problem_header", target)


@action("board_write")
def board_write(scene, lines: list[str] | None = None, tex: str | None = None, color: str | None = None,
                ko: bool = False, scale: float | None = None, run_time: float | None = None,
                indent: float = 0.0, t2c: dict | None = None, plain: bool = False, id: str | None = None,
                animation: str = "write", **_):
    """보드에 수식 줄을 추가한다. lines 또는 tex 사용."""
    assert scene.board is not None, "board 액션이 먼저 필요합니다"
    items = list(lines or [])
    if tex is not None:
        items.append(tex)
    sc = scale if scale is not None else scene.project.layout.board.line_scale
    per = _rt(run_time, 0.9) / max(1, len(items))
    for i, s in enumerate(items):
        if ko:
            # 한글 문장은 축소 대신 보드 폭에 맞춰 자동 줄바꿈
            mob = scene.ktex(s, scale=sc, color=color, width=scene.board.content_width - indent)
        else:
            mob = scene.mtex(s, color=color, scale=sc, t2c=t2c, plain=plain)
        scene.board.add_line(mob, scene, run_time=per, indent=indent, animation=animation)
        if id and i == len(items) - 1:
            scene.register(id, mob)
        if id and len(items) > 1:
            scene.register(f"{id}_{i}", mob)


@action("board_replace")
def board_replace(scene, tex: str, index: int = -1, color: str | None = None, ko: bool = False,
                  scale: float | None = None, run_time: float | None = None, t2c: dict | None = None,
                  plain: bool = False, **_):
    assert scene.board is not None
    sc = scale if scale is not None else scene.project.layout.board.line_scale
    mob = scene.ktex(tex, scale=sc, color=color) if ko else scene.mtex(tex, color=color, scale=sc, t2c=t2c, plain=plain)
    scene.board.replace_line(index, mob, scene, run_time=_rt(run_time, 0.9))


@action("board_highlight")
def board_highlight(scene, index: int = -1, color: str | None = None, run_time: float | None = None,
                    box: bool = False, **_):
    assert scene.board is not None
    scene.board.highlight_line(index, scene, scene.color(color, scene.theme.highlight), _rt(run_time, 0.9), box=box)


@action("board_clear")
def board_clear(scene, run_time: float | None = None, keep_header: bool = True, **_):
    assert scene.board is not None
    scene.board.clear(scene, run_time=_rt(run_time, 0.6), keep_header=keep_header)


@action("board_title")
def board_title(scene, text: str, run_time: float | None = None, **_):
    assert scene.board is not None
    new = scene.ktext(text, size=26, weight="BOLD", color=scene.theme.muted)
    if new.width > scene.board.content_width:
        new.scale_to_fit_width(scene.board.content_width)
    new.move_to(scene.board.title, aligned_edge=LEFT)
    new.set_z_index(3)
    scene.play(Transform(scene.board.title, new), run_time=_rt(run_time, 0.5))


# ====================================================================== 좌표평면 / 그래프
@action("axes")
def axes(scene, id: str = "axes", x_range: list | None = None, y_range: list | None = None,
         width: float | None = None, height: float | None = None, center: list | None = None,
         grid: bool | None = None, numbers: bool | None = None, run_time: float | None = None,
         equal_aspect: bool = True, labels: bool = True, **_):
    rt = _rt(run_time, 1.2)
    lay = scene.project.layout.graph
    xr = [scene.eval(v) for v in (x_range or lay.x_range)]
    yr = [scene.eval(v) for v in (y_range or lay.y_range)]
    if len(xr) == 2:
        xr.append(1)
    if len(yr) == 2:
        yr.append(1)
    w = width or lay.width
    h = height or lay.height
    sec = None
    if scene.chalk is not None:
        # 칠판: 현재 섹션의 그림 영역에 맞춘다 (YAML 에서 width/height/center 를 주면 그 값이 우선)
        sec = scene.chalk.section()
        if width is None:
            w = sec.graph_width - 0.5
        if height is None:
            h = sec.graph_height - 0.6
    if equal_aspect:
        unit = min(w / (xr[1] - xr[0]), h / (yr[1] - yr[0]))
        w = unit * (xr[1] - xr[0])
        h = unit * (yr[1] - yr[0])
    use_grid = lay.grid if grid is None else grid
    use_numbers = lay.numbers if numbers is None else numbers
    axis_cfg = {
        "color": scene.theme.axis,
        "stroke_width": 2.2,
        "include_numbers": use_numbers,
        "font_size": 22,
        "decimal_number_config": {"num_decimal_places": 0, "color": scene.theme.muted},
        "numbers_to_exclude": [0],
        "include_tip": True,
        "tip_width": 0.18,
        "tip_height": 0.18,
    }
    if use_grid:
        ax = NumberPlane(
            x_range=xr, y_range=yr, x_length=w, y_length=h,
            axis_config=axis_cfg,
            background_line_style={"stroke_color": scene.theme.grid, "stroke_width": 1.0, "stroke_opacity": 0.9},
            faded_line_ratio=2,
            faded_line_style={"stroke_color": scene.theme.grid_faded, "stroke_width": 0.6, "stroke_opacity": 0.8},
        )
    else:
        ax = Axes(x_range=xr, y_range=yr, x_length=w, y_length=h, axis_config=axis_cfg, tips=True)
    if center is not None:
        c = center
    elif sec is not None:
        c = sec.graph_center
    else:
        c = lay.center
    ax.move_to([float(c[0]), float(c[1]), 0])
    scene.axes = ax
    scene.axes_ranges = (xr, yr)
    scene.register(id, ax)
    anims = [Create(ax)]
    if labels:
        lab = ax.get_axis_labels(MathTex("x").scale(0.8), MathTex("y").scale(0.8)).set_color(scene.theme.muted)
        scene.finish_text(lab)
        scene.register(f"{id}_labels", lab)
        anims.append(FadeIn(lab))
    if scene.theme.chalk:
        scene.finish_text(ax)  # 축 눈금 숫자도 분필 질감
    scene.play(*anims, run_time=rt)


def _plot_pieces(scene, f, x_range, color, stroke_width, dashed=False, samples=600, smooth=True, steps=400):
    xr, yr = scene.axes_ranges
    x0 = xr[0] if x_range is None else scene.eval(x_range[0])
    x1 = xr[1] if x_range is None else scene.eval(x_range[1])
    pieces = scene.clipped_pieces(f, (x0, x1), (yr[0], yr[1]), samples=samples)
    group = VGroup()
    for a, b in pieces:
        step = (b - a) / steps
        # smooth=False: 절댓값·조각 함수처럼 뾰족점이 있는 그래프를 둥글리지 않고 그린다
        g = scene.axes.plot(f, x_range=[a, b, step], color=color, stroke_width=stroke_width, use_smoothing=smooth)
        if dashed:
            g = DashedVMobject(g, num_dashes=int(max(12, (b - a) * 14)), dashed_ratio=0.55)
        group.add(g)
    return group


@action("plot")
def plot(scene, id: str, expr: str, color: str | None = None, x_range: list | None = None,
         label: str | None = None, label_at: Any = None, label_dir: Any = "UR", label_scale: float = 0.75,
         stroke_width: float = 4.0, run_time: float | None = None, dashed: bool = False,
         smooth: bool = True, **_):
    """y = expr(x) 그래프. y 범위를 벗어나는 부분은 자동으로 잘라낸다. smooth=false 면 뾰족점을 보존."""
    rt = _rt(run_time, 1.4)
    f = scene.func(expr)
    scene.funcs[id] = f
    col = scene.color(color, scene.theme.accent)
    group = _plot_pieces(scene, f, x_range, col, stroke_width, dashed, smooth=smooth, steps=400 if smooth else 800)
    scene.register(id, group)
    anims = [Create(group)]
    if label:
        lab = scene.mtex(label, color=color, scale=label_scale, plain=True)
        if label_at is not None:
            x = scene.eval(label_at)
            lab.next_to(scene.c2p(x, f(x)), scene.direction(label_dir), buff=0.12)
        else:
            lab.next_to(group, scene.direction(label_dir), buff=0.1)
        scene.bg_rect(lab, opacity=0.7, buff=0.05)
        lab.set_z_index(6)
        scene.register(f"{id}_label", lab)
        anims.append(FadeIn(lab, shift=UP * 0.1))
    scene.play(*anims, run_time=rt)


@action("line")
def line(scene, id: str, slope: Any = None, intercept: Any = None, expr: str | None = None,
         color: str | None = None, dashed: bool = True, stroke_width: float = 2.6, label: str | None = None,
         label_at: Any = None, label_dir: Any = "UR", label_scale: float = 0.7, x_range: list | None = None,
         through: list | None = None, run_time: float | None = None, **_):
    """직선 y = slope*x + intercept (또는 expr). through=[p1,p2]로 두 점을 지나는 직선도 가능."""
    rt = _rt(run_time, 1.0)
    if through is not None:
        (x1, y1), (x2, y2) = scene.resolve_coord(through[0]), scene.resolve_coord(through[1])
        if abs(x2 - x1) < 1e-12:
            raise ValueError("수직선은 vline 을 사용하세요")
        m = (y2 - y1) / (x2 - x1)
        c = y1 - m * x1
        f = lambda x, m=m, c=c: m * x + c
    elif expr is not None:
        f = scene.func(expr)
    else:
        m, c = scene.eval(slope), scene.eval(intercept if intercept is not None else 0)
        f = lambda x, m=m, c=c: m * x + c
    scene.funcs[id] = f
    col = scene.color(color, scene.theme.palette["guide"])
    group = _plot_pieces(scene, f, x_range, col, stroke_width, dashed, samples=200)
    scene.register(id, group)
    anims = [Create(group)]
    if label:
        lab = scene.mtex(label, color=color, scale=label_scale, plain=True)
        xr, _ = scene.axes_ranges
        x = scene.eval(label_at) if label_at is not None else xr[1] - 0.6
        lab.next_to(scene.c2p(x, f(x)), scene.direction(label_dir), buff=0.1)
        scene.bg_rect(lab, opacity=0.7, buff=0.05)
        lab.set_z_index(6)
        scene.register(f"{id}_label", lab)
        anims.append(FadeIn(lab))
    scene.play(*anims, run_time=rt)


@action("vline")
def vline(scene, id: str, x: Any, color: str | None = None, dashed: bool = True, stroke_width: float = 2.4,
          label: str | None = None, run_time: float | None = None, **_):
    """수직 점근선 등."""
    rt = _rt(run_time, 0.8)
    xr, yr = scene.axes_ranges
    xv = scene.eval(x)
    col = scene.color(color, scene.theme.palette["guide"])
    ln = Line(scene.c2p(xv, yr[0]), scene.c2p(xv, yr[1]), color=col, stroke_width=stroke_width)
    if dashed:
        ln = DashedLine(scene.c2p(xv, yr[0]), scene.c2p(xv, yr[1]), color=col, stroke_width=stroke_width,
                        dash_length=0.12)
    scene.register(id, ln)
    anims = [Create(ln)]
    if label:
        lab = scene.mtex(label, color=color, scale=0.65, plain=True).next_to(ln.get_top(), DR, buff=0.08)
        scene.register(f"{id}_label", lab)
        anims.append(FadeIn(lab))
    scene.play(*anims, run_time=rt)


@action("point")
def point(scene, id: str, pos: Any = None, at: Any = None, color: str | None = None, label: str | None = None,
          label_dir: Any = "UR", label_scale: float = 0.8, radius: float = 0.08, run_time: float | None = None,
          flash: bool = True, coords_label: bool = False, **_):
    """점 하나. 좌표는 `pos` 로 준다 (`at` 은 액션 실행 시각과 이름이 겹치므로 YAML 에서는 pos 사용)."""
    rt = _rt(run_time, 0.7)
    if pos is None:
        raise ValueError(f"point {id!r}: 좌표 pos 가 필요합니다")
    x, y = scene.resolve_coord(pos)
    col = scene.color(color, scene.theme.palette["point"])
    dot = Dot(scene.c2p(x, y), radius=radius, color=col, z_index=5)
    dot.set_stroke(scene.theme.background, width=2)
    scene.register(id, dot, (x, y))
    anims = [GrowFromCenter(dot)]
    if label:
        lab = scene.mtex(label, color=color, scale=label_scale, plain=True)
        lab.next_to(dot, scene.direction(label_dir), buff=0.1).set_z_index(6)
        scene.register(f"{id}_label", lab)
        anims.append(FadeIn(lab, shift=scene.direction(label_dir) * 0.1))
    scene.play(*anims, run_time=rt)
    if flash:
        scene.play(Flash(dot, color=col, flash_radius=0.3, line_length=0.15, run_time=0.5))


@action("points")
def points(scene, items: list[dict], run_time: float | None = None, lag: float = 0.25, **_):
    """여러 점을 순차적으로(LaggedStart) 표시. items: [{id, at, label, ...}]"""
    rt = _rt(run_time, 1.4)
    anims = []
    for it in items:
        x, y = scene.resolve_coord(it["at"])
        col = scene.color(it.get("color"), scene.theme.palette["point"])
        dot = Dot(scene.c2p(x, y), radius=it.get("radius", 0.08), color=col, z_index=5)
        dot.set_stroke(scene.theme.background, width=2)
        scene.register(it["id"], dot, (x, y))
        sub = [GrowFromCenter(dot)]
        if it.get("label"):
            lab = scene.mtex(it["label"], color=it.get("color"), scale=it.get("label_scale", 0.8), plain=True)
            lab.next_to(dot, scene.direction(it.get("label_dir", "UR")), buff=0.1).set_z_index(6)
            scene.register(f"{it['id']}_label", lab)
            sub.append(FadeIn(lab))
        anims.append(AnimationGroup(*sub))
    scene.play(LaggedStart(*anims, lag_ratio=lag), run_time=rt)


@action("polygon")
def polygon(scene, id: str, points: list, color: str | None = None, fill_opacity: float = 0.08,
            stroke_width: float = 3.0, run_time: float | None = None, dashed: bool = False, closed: bool = True, **_):
    rt = _rt(run_time, 1.4)
    pts = [scene.c2p(*scene.resolve_coord(p)) for p in points]
    col = scene.color(color, scene.theme.palette["rect"])
    if closed:
        poly = Polygon(*pts, color=col, stroke_width=stroke_width, fill_color=col, fill_opacity=fill_opacity)
    else:
        poly = VMobject(color=col, stroke_width=stroke_width).set_points_as_corners(pts)
    if dashed:
        poly = DashedVMobject(poly, num_dashes=60, dashed_ratio=0.6)
    poly.set_z_index(2)
    scene.register(id, poly)
    scene.play(Create(poly), run_time=rt)


@action("segment")
def segment(scene, id: str, a: Any, b: Any, color: str | None = None, stroke_width: float = 3.5,
            dashed: bool = False, label: str | None = None, label_dir: Any = "UP", label_scale: float = 0.7,
            run_time: float | None = None, **_):
    rt = _rt(run_time, 0.9)
    p1 = scene.c2p(*scene.resolve_coord(a))
    p2 = scene.c2p(*scene.resolve_coord(b))
    col = scene.color(color, scene.theme.palette["rect"])
    ln = (DashedLine if dashed else Line)(p1, p2, color=col, stroke_width=stroke_width)
    ln.set_z_index(2)
    scene.register(id, ln)
    anims = [Create(ln)]
    if label:
        lab = scene.mtex(label, color=color, scale=label_scale, plain=True)
        lab.next_to(ln.get_center(), scene.direction(label_dir), buff=0.12)
        scene.register(f"{id}_label", lab)
        anims.append(FadeIn(lab))
    scene.play(*anims, run_time=rt)


@action("arrow")
def arrow(scene, id: str, a: Any, b: Any, color: str | None = None, label: str | None = None,
          label_dir: Any = "UP", label_scale: float = 0.7, stroke_width: float = 4.0, run_time: float | None = None,
          buff: float = 0.12, **_):
    rt = _rt(run_time, 0.9)
    p1 = scene.c2p(*scene.resolve_coord(a))
    p2 = scene.c2p(*scene.resolve_coord(b))
    col = scene.color(color, scene.theme.accent)
    ar = Arrow(p1, p2, color=col, stroke_width=stroke_width, buff=buff, max_tip_length_to_length_ratio=0.18)
    ar.set_z_index(3)
    scene.register(id, ar)
    anims = [GrowArrow(ar)]
    if label:
        lab = scene.mtex(label, color=color, scale=label_scale, plain=True)
        lab.next_to(ar.get_center(), scene.direction(label_dir), buff=0.1).set_z_index(6)
        scene.bg_rect(lab, opacity=0.75, buff=0.05)
        scene.register(f"{id}_label", lab)
        anims.append(FadeIn(lab))
    scene.play(*anims, run_time=rt)


@action("guides")
def guides(scene, point: str, color: str | None = None, x_label: str | None = None, y_label: str | None = None,
           run_time: float | None = None, id: str | None = None, label_scale: float = 0.65, **_):
    """점에서 두 축으로 내린 점선 + 좌표값 라벨."""
    rt = _rt(run_time, 0.9)
    x, y = scene.resolve_coord(point)
    col = scene.color(color, scene.theme.palette["guide"])
    p = scene.c2p(x, y)
    v = DashedLine(scene.c2p(x, 0), p, color=col, stroke_width=2, dash_length=0.1)
    h = DashedLine(scene.c2p(0, y), p, color=col, stroke_width=2, dash_length=0.1)
    g = VGroup(v, h)
    anims = [Create(v), Create(h)]
    if x_label:
        xl = scene.mtex(x_label, color=color, scale=label_scale, plain=True).next_to(scene.c2p(x, 0), DOWN, buff=0.12)
        scene.bg_rect(xl, opacity=0.8, buff=0.04)
        g.add(xl)
        anims.append(FadeIn(xl))
    if y_label:
        yl = scene.mtex(y_label, color=color, scale=label_scale, plain=True).next_to(scene.c2p(0, y), LEFT, buff=0.12)
        scene.bg_rect(yl, opacity=0.8, buff=0.04)
        g.add(yl)
        anims.append(FadeIn(yl))
    scene.register(id or f"guides_{point}", g)
    scene.play(*anims, run_time=rt)


@action("translate_copy")
def translate_copy(scene, source: str, dx: Any, dy: Any, id: str, color: str | None = None,
                   label: str | None = None, label_dir: Any = "UR", arrow: bool = True,
                   arrow_label: str | None = None, run_time: float | None = None, keep_source: bool = True,
                   label_scale: float = 0.8, **_):
    """점(또는 그래프)을 (dx, dy) 만큼 평행이동한 복사본을 만든다. 점이면 좌표도 등록."""
    rt = _rt(run_time, 1.4)
    src = scene.get(source)
    ddx, ddy = scene.eval(dx), scene.eval(dy)
    shift_vec = scene.c2p(ddx, ddy) - scene.c2p(0, 0)
    copy = src.copy()
    if color:
        copy.set_color(scene.color(color))
    anims = []
    if source in scene.coords:
        x, y = scene.coords[source]
        scene.register(id, copy, (x + ddx, y + ddy))
    else:
        scene.register(id, copy)
    if arrow and source in scene.coords:
        x, y = scene.coords[source]
        ar = Arrow(scene.c2p(x, y), scene.c2p(x + ddx, y + ddy), color=scene.color(color, scene.theme.accent),
                   stroke_width=3.5, buff=0.1, max_tip_length_to_length_ratio=0.2).set_z_index(3)
        scene.register(f"{id}_arrow", ar)
        anims.append(GrowArrow(ar))
        if arrow_label:
            al = scene.mtex(arrow_label, scale=0.65, plain=True, color=color).next_to(ar.get_center(), UR, buff=0.08)
            scene.bg_rect(al, opacity=0.75, buff=0.04)
            scene.register(f"{id}_arrow_label", al)
            anims.append(FadeIn(al))
    scene.play(copy.animate.shift(shift_vec), *anims, run_time=rt)
    if label and source in scene.coords:
        lab = scene.mtex(label, color=color, scale=label_scale, plain=True)
        lab.next_to(copy, scene.direction(label_dir), buff=0.1).set_z_index(6)
        scene.register(f"{id}_label", lab)
        scene.play(FadeIn(lab, shift=scene.direction(label_dir) * 0.1), run_time=0.4)
    if not keep_source:
        scene.play(FadeOut(src), run_time=0.3)


def _reflect_point(x: float, y: float, m: float, c: float) -> tuple[float, float]:
    """점 (x, y) 를 직선 y = m x + c 에 대해 대칭이동."""
    # 직선 위의 점 P0=(0,c), 방향 d=(1,m)
    d = np.array([1.0, m])
    d /= np.linalg.norm(d)
    v = np.array([x, y - c])
    proj = d * float(np.dot(v, d))
    r = 2 * proj - v
    return float(r[0]), float(r[1] + c)


@action("reflect")
def reflect(scene, source: str, slope: Any, intercept: Any, id: str, color: str | None = None,
            label: str | None = None, label_dir: Any = "DR", run_time: float | None = None,
            show_perpendicular: bool = True, guide_color: str | None = None, keep_guide: bool = True,
            label_scale: float = 0.8, right_angle: bool = True, **_):
    """점 source 를 직선 y = slope x + intercept 에 대해 대칭이동한 점을 애니메이션으로 만든다."""
    rt = _rt(run_time, 1.6)
    m, c = scene.eval(slope), scene.eval(intercept)
    x, y = scene.coords[source]
    rx, ry = _reflect_point(x, y, m, c)
    mx, my = (x + rx) / 2, (y + ry) / 2
    col = scene.color(color, scene.theme.palette["point"])
    gcol = scene.color(guide_color, scene.theme.palette["guide"])
    p, q = scene.c2p(x, y), scene.c2p(rx, ry)
    perp = DashedLine(p, q, color=gcol, stroke_width=2.2, dash_length=0.1).set_z_index(1)
    foot = Dot(scene.c2p(mx, my), radius=0.045, color=gcol).set_z_index(4)
    anims = []
    if show_perpendicular:
        anims.append(Create(perp))
        anims.append(FadeIn(foot))
    src = scene.get(source)
    moving = src.copy().set_color(col).set_z_index(5)
    scene.play(*anims, run_time=rt * 0.45)
    scene.play(moving.animate.move_to(q), run_time=rt * 0.55)
    scene.register(id, moving, (rx, ry))
    extra = []
    if right_angle and show_perpendicular:
        # 축 위 직선 방향 벡터와 수선의 발 사이 직각 표시
        base = Line(scene.c2p(mx - 0.4, my - 0.4 * m), scene.c2p(mx + 0.4, my + 0.4 * m))
        ra = RightAngle(base, Line(foot.get_center(), p), length=0.18, color=gcol, stroke_width=2)
        extra.append(FadeIn(ra))
        scene.register(f"{id}_rightangle", ra)
    if label:
        lab = scene.mtex(label, color=color, scale=label_scale, plain=True)
        lab.next_to(moving, scene.direction(label_dir), buff=0.1).set_z_index(6)
        scene.register(f"{id}_label", lab)
        extra.append(FadeIn(lab, shift=scene.direction(label_dir) * 0.1))
    if extra:
        scene.play(*extra, run_time=0.5)
    if show_perpendicular:
        g = VGroup(perp, foot)
        scene.register(f"{id}_guide", g)
        if not keep_guide:
            scene.play(FadeOut(g), run_time=0.3)


@action("highlight")
def highlight(scene, ids: list[str] | str, color: str | None = None, mode: str = "indicate",
              run_time: float | None = None, **_):
    """indicate | flash | circumscribe | wiggle | pulse"""
    rt = _rt(run_time, 0.9)
    if isinstance(ids, str):
        ids = [ids]
    col = scene.color(color, scene.theme.highlight)
    mobs = [scene.get(i) for i in ids]
    if mode == "flash":
        scene.play(*(Flash(m, color=col, flash_radius=0.35) for m in mobs), run_time=rt)
    elif mode == "circumscribe":
        scene.play(*(Circumscribe(m, color=col, buff=0.12, time_width=0.6) for m in mobs), run_time=rt)
    elif mode == "wiggle":
        scene.play(*(Wiggle(m) for m in mobs), run_time=rt)
    elif mode == "pulse":
        scene.play(*(ShowPassingFlash(m.copy().set_color(col).set_stroke(width=8), time_width=0.5) for m in mobs),
                   run_time=rt)
    else:
        scene.play(*(Indicate(m, color=col, scale_factor=1.12) for m in mobs), run_time=rt)


@action("label")
def label(scene, id: str, tex: str, near: str | None = None, pos: Any = None, dir: Any = "UR",
          color: str | None = None, scale: float = 0.75, run_time: float | None = None, ko: bool = False,
          bg: bool = True, buff: float = 0.12, **_):
    """수식 라벨을 객체 근처(near) 또는 좌표(pos)에 배치."""
    rt = _rt(run_time, 0.6)
    lab = scene.ktex(tex, scale=scale, color=color) if ko else scene.mtex(tex, color=color, scale=scale, plain=True)
    if near is not None:
        lab.next_to(scene.get(near), scene.direction(dir), buff=buff)
    elif pos is not None:
        lab.move_to(scene.c2p(*scene.resolve_coord(pos))).shift(scene.direction(dir) * buff)
    if bg:
        scene.bg_rect(lab, opacity=0.75, buff=0.05)
    lab.set_z_index(7)
    scene.register(id, lab)
    scene.play(FadeIn(lab, shift=scene.direction(dir) * 0.1), run_time=rt)


@action("caption")
def caption(scene, text: str = "", tex: str | None = None, color: str | None = None,
            run_time: float | None = None, id: str = "caption", position: str = "bottom", **_):
    """그래프 영역 아래쪽의 한 줄 설명 말풍선. 기존 캡션은 교체. text 가 비면 제거."""
    rt = _rt(run_time, 0.6)
    old = scene.caption
    if not text and tex is None:
        if old is not None:
            scene.play(FadeOut(old), run_time=rt)
            scene.caption = None
            scene.objs.pop(id, None)
        return
    if scene.theme.chalk:
        _chalk_caption(scene, text, tex, color, rt, id, position, old)
        return
    if tex is not None:
        body = scene.ktex(tex, scale=0.78, color=color)
    else:
        body = scene.ktext(text, size=27, color=color or scene.theme.text)
    accent = scene.color(color, scene.theme.accent)
    bar = Rectangle(width=0.08, height=body.height + 0.28, fill_color=accent, fill_opacity=1, stroke_width=0)
    bg = RoundedRectangle(corner_radius=0.1, width=body.width + 0.7, height=body.height + 0.34,
                          fill_color=scene.theme.panel, fill_opacity=0.94, stroke_color=scene.theme.panel_border,
                          stroke_width=1)
    bar.align_to(bg, LEFT).shift(RIGHT * 0.08)
    body.move_to(bg).shift(RIGHT * 0.08)
    g = VGroup(bg, bar, body).set_z_index(9)
    # 그래프 영역(보드 왼쪽) 안에 들어오도록 폭을 제한하고 좌우를 클램프한다
    frame_left = -config.frame_width / 2 + 0.25
    frame_right = (scene.board.frame.get_left()[0] - 0.2) if scene.board is not None else config.frame_width / 2 - 0.25
    max_w = frame_right - frame_left
    if g.width > max_w:
        g.scale_to_fit_width(max_w)
    anchor_x = scene.axes.get_center()[0] if scene.axes is not None else (frame_left + frame_right) / 2
    if position == "top":
        g.to_edge(UP, buff=0.22)
    else:
        # 하단 자막 영역(2줄 기준 약 1.3 유닛)을 비워 둔다
        g.to_edge(DOWN, buff=1.4)
    g.set_x(anchor_x)
    if g.get_left()[0] < frame_left:
        g.shift(RIGHT * (frame_left - g.get_left()[0]))
    if g.get_right()[0] > frame_right:
        g.shift(LEFT * (g.get_right()[0] - frame_right))
    scene.caption = g
    scene.register(id, g)
    if old is not None:
        scene.play(FadeOut(old, shift=DOWN * 0.15), FadeIn(g, shift=UP * 0.15), run_time=rt)
    else:
        scene.play(FadeIn(g, shift=UP * 0.15), run_time=rt)


def _chalk_caption(scene, text, tex, color, rt, id, position, old):
    """칠판 스타일 캡션: 화면(카메라 프레임)에 고정된 손글씨 메모. 반투명 띠 위에 얹어 어떤 배경에서도 읽힌다."""
    accent = scene.color(color, scene.theme.accent)
    if tex is not None:
        body = scene.ktex(tex, scale=0.8, color=color or scene.theme.accent)
    else:
        body = scene.ktext(text, size=34, color=accent, font=scene.theme.title_font)
    if body.width > 12.0:
        body.scale_to_fit_width(12.0)
    band = RoundedRectangle(corner_radius=0.12, width=body.width + 0.7, height=body.height + 0.34,
                            fill_color="#0d1a14", fill_opacity=0.55, stroke_width=0)
    body.move_to(band)
    g = VGroup(band, body).set_z_index(40)
    pin_to_frame(scene, g, anchor=UP if position == "top" else DOWN, buff=0.25 if position == "top" else 1.35)
    scene.caption = g
    scene.register(id, g)
    anims = [FadeIn(band, run_time=rt), handwrite(body, run_time=max(rt, min(1.4, handwrite_time(body, per_glyph=0.035))))]
    if old is not None:
        old.clear_updaters()
        anims.append(FadeOut(old, shift=DOWN * 0.15, run_time=rt))
    scene.play(*anims)
    # 애니메이션은 band/body 를 개별로 씬에 넣는다. 업데이터(프레임 고정)는 그룹에 있으므로 그룹으로 다시 묶는다.
    scene.remove(band, body)
    scene.add(g)


@action("fade")
def fade(scene, ids: list[str] | str, out: bool = True, run_time: float | None = None, opacity: float | None = None, **_):
    rt = _rt(run_time, 0.6)
    if isinstance(ids, str):
        ids = [ids]
    mobs = [scene.get(i) for i in ids if i in scene.objs]
    if not mobs:
        return
    if opacity is not None:
        scene.play(*(Transform(m, _opacity_target(m, opacity)) for m in mobs), run_time=rt)
        return
    if out:
        scene.play(*(FadeOut(m) for m in mobs), run_time=rt)
        for i in ids:
            if scene.caption is not None and scene.objs.get(i) is scene.caption:
                scene.caption = None
            scene.objs.pop(i, None)
    else:
        scene.play(*(FadeIn(m) for m in mobs), run_time=rt)


def _remember_opacity(mob: Mobject) -> None:
    """stroke/fill 원본 불투명도를 서브모브젼트별로 기억한다 (최초 1회)."""
    if getattr(mob, "_orig_opacity", None) is not None:
        return
    rec = {}
    for sm in mob.family_members_with_points():
        if isinstance(sm, VMobject):
            rec[id(sm)] = (float(sm.get_stroke_opacity()), float(sm.get_fill_opacity()))
    mob._orig_opacity = rec


def _opacity_target(mob: Mobject, factor: float) -> Mobject:
    """원본 대비 factor 배의 불투명도를 가진 복사본(Transform 목표)을 만든다. fill 이 0 이던 곡선은 0 을 유지."""
    _remember_opacity(mob)
    target = mob.copy()
    for src, dst in zip(mob.family_members_with_points(), target.family_members_with_points()):
        if isinstance(dst, VMobject):
            so, fo = mob._orig_opacity.get(id(src), (1.0, 0.0))
            dst.set_stroke(opacity=so * factor)
            dst.set_fill(opacity=fo * factor)
    target._orig_opacity = mob._orig_opacity
    return target


@action("dim")
def dim(scene, ids: list[str] | str, opacity: float = 0.25, run_time: float | None = None, **_):
    """객체를 흐리게. stroke/fill 을 원본 비율로 함께 낮춘다 (곡선이 채워지는 부작용 없음)."""
    rt = _rt(run_time, 0.5)
    if isinstance(ids, str):
        ids = [ids]
    mobs = [scene.get(i) for i in ids if i in scene.objs]
    if mobs:
        scene.play(*(Transform(m, _opacity_target(m, opacity)) for m in mobs), run_time=rt)


@action("undim")
def undim(scene, ids: list[str] | str, run_time: float | None = None, **_):
    """dim 으로 흐려진 객체를 원래 불투명도로 복원."""
    rt = _rt(run_time, 0.5)
    if isinstance(ids, str):
        ids = [ids]
    mobs = [scene.get(i) for i in ids if i in scene.objs]
    if mobs:
        scene.play(*(Transform(m, _opacity_target(m, 1.0)) for m in mobs), run_time=rt)


@action("answer")
def answer(scene, tex: str, run_time: float | None = None, id: str = "answer", color: str | None = None,
           caption_text: str = "", **_):
    """그래프 영역 중앙에 정답 박스를 강조 표시."""
    rt = _rt(run_time, 1.2)
    col = scene.color(color, scene.theme.highlight)
    m = scene.mtex(tex, scale=1.4, plain=True).set_color(scene.theme.text)
    items = [m]
    if caption_text:
        items.insert(0, scene.ktext(caption_text, size=28 if not scene.theme.chalk else 40, color=scene.theme.muted,
                                    font=scene.theme.title_font))
    g = VGroup(*items).arrange(DOWN, buff=0.3)
    if scene.theme.chalk and scene.chalk is not None:
        # 칠판: 판서 커서 위치에 크게 쓰고 분필로 상자를 두른다 (채우기 없음)
        g.arrange(RIGHT if caption_text else DOWN, buff=0.5)
        scene.chalk.place_line(g, indent=0.3, space=0.35)
        scene.chalk.advance(0.3)
        box = RoundedRectangle(corner_radius=0.12, width=g.width + 0.7, height=g.height + 0.5,
                               fill_opacity=0, stroke_color=col, stroke_width=4).move_to(g)
        full = VGroup(g, box).set_z_index(20)
        scene.register(id, full)
        scene.play(handwrite(g, run_time=rt))
        scene.play(Create(box, run_time=0.7))
        scene.play(Circumscribe(box, color=col, buff=0.08), run_time=0.8)
        return
    box = RoundedRectangle(corner_radius=0.16, width=g.width + 0.9, height=g.height + 0.7,
                           fill_color=scene.theme.panel, fill_opacity=0.96, stroke_color=col, stroke_width=3)
    full = VGroup(box, g).set_z_index(20)
    if scene.axes is not None:
        full.move_to(scene.axes.get_center())
    scene.register(id, full)
    scene.play(FadeIn(box, scale=0.9), Write(g), run_time=rt)
    scene.play(Circumscribe(box, color=col, buff=0.05), run_time=0.8)


# ====================================================================== 칠판(chalkboard) 전용
def _need_chalk(scene, name: str):
    if scene.chalk is None:
        raise RuntimeError(f"{name} 액션은 meta.style: chalkboard 에서만 사용할 수 있습니다")
    return scene.chalk


def _drop_caption(scene, run_time: float = 0.3) -> None:
    """화면에 고정된 메모(캡션)를 지운다 — 섹션 이동·전체 훑어보기 전에."""
    if scene.caption is None:
        return
    scene.caption.clear_updaters()
    scene.play(FadeOut(scene.caption), run_time=run_time)
    scene.objs.pop("caption", None)
    scene.caption = None


@action("goto")
def goto(scene, section: str, run_time: float | None = None, overview: bool = True, title: bool = True, **_):
    """카메라를 다른 섹션으로 옮긴다. 도중에 살짝 줌아웃해 칠판 전체 흐름이 보이고, 처음 방문이면 제목을 판서한다."""
    cv = _need_chalk(scene, "goto")
    _drop_caption(scene)
    cv.goto(section, run_time=_rt(run_time, 1.8), overview=overview, write_title=title)


@action("write")
def write(scene, lines: list[str] | None = None, tex: str | None = None, text: str | None = None,
          color: str | None = None, ko: bool = False, scale: float | None = None, run_time: float | None = None,
          indent: float = 0.0, t2c: dict | None = None, plain: bool = False, id: str | None = None,
          box: bool = False, underline: bool = False, space: float = 0.0, section: str | None = None,
          width: float | None = None, **_):
    """칠판 판서: 현재(또는 지정) 섹션의 커서 위치에 한 줄씩 손글씨로 적는다.

    - tex/lines: 수식(pdflatex). ko: true 면 한글+수식 혼합(xelatex, 판서 폭에 맞춰 자동 줄바꿈)
    - text: Pango 손글씨 폰트로 쓴 한글 메모
    - box/underline: 마지막 줄을 분필 상자/밑줄로 강조 (지우지 않고 남는다)
    """
    cv = _need_chalk(scene, "write")
    sec = cv.section(section)
    items: list[tuple[str, str]] = [("tex", s) for s in (lines or [])]
    if tex is not None:
        items.append(("tex", tex))
    if text is not None:
        items.append(("text", text))
    sc = scale if scale is not None else scene.project.layout.chalk.line_scale
    col = scene.color(color, scene.theme.text)
    last = None
    for i, (kind, s) in enumerate(items):
        if kind == "text":
            mob = scene.ktext(s, size=int(44 * sc), color=col)
        elif ko:
            w = width if width is not None else sec.notes_width - indent
            mob = scene.ktex(s, scale=sc, color=color, width=w)
        else:
            mob = scene.mtex(s, color=color, scale=sc, t2c=t2c, plain=plain)
        cv.place_line(mob, indent=indent, sec=sec, space=space if i == 0 else 0.0)
        rt = run_time if run_time is not None and len(items) == 1 else None
        if run_time is not None and len(items) > 1:
            rt = float(run_time) / len(items)
        scene.play(handwrite(mob, run_time=rt))
        if id:
            scene.register(f"{id}_{i}" if len(items) > 1 else id, mob)
        last = mob
    if last is not None and id and len(items) > 1:
        scene.register(id, last)
    if last is not None and (box or underline):
        hl = scene.color(None, scene.theme.highlight) if color is None else col
        if box:
            mark = RoundedRectangle(corner_radius=0.1, width=last.width + 0.4, height=last.height + 0.3,
                                    fill_opacity=0, stroke_color=hl, stroke_width=3).move_to(last)
            cv.advance(0.18, sec)
        else:
            mark = Line(last.get_corner(DL) + DOWN * 0.08, last.get_corner(DR) + DOWN * 0.08,
                        stroke_color=hl, stroke_width=3)
            cv.advance(0.1, sec)
        mark.set_z_index(3)
        if id:
            scene.register(f"{id}_mark", mark)
        scene.play(Create(mark), run_time=0.5)


@action("space")
def space(scene, dy: float = 0.3, section: str | None = None, **_):
    """판서 커서를 dy 만큼 아래로 내린다 (문단 사이 여백)."""
    cv = _need_chalk(scene, "space")
    cv.advance(float(dy), cv.section(section))


@action("camera")
def camera(scene, focus: Any = None, pos: Any = None, width: float = 6.0, run_time: float | None = None,
           reset: bool = False, ids: list[str] | None = None, pad: float = 1.2, sections: list[str] | None = None,
           **_):
    """카메라 줌.

    - pos: 그래프 좌표로 줌인 / focus: 객체 id(또는 섹션 id) / ids: 여러 객체가 모두 보이게
    - sections: [첫 섹션, 끝 섹션] 범위가 모두 보이게 줌아웃 (칠판 전체를 훑어보는 마무리 등)
    - reset: 현재 섹션 뷰로 복귀
    """
    cv = _need_chalk(scene, "camera")
    rt = _rt(run_time, 1.2)
    if reset:
        cv.reset_view(run_time=rt)
        return
    if sections:
        _drop_caption(scene)
        a, b = cv.section(sections[0]), cv.section(sections[-1])
        left, right = min(a.left, b.left) - 0.4, max(a.right, b.right) + 0.4
        cv.focus([(left + right) / 2, 0.0], right - left, run_time=rt)
        return
    if ids:
        g = VGroup(*(scene.get(i) for i in ids))
        c = g.get_center()
        w = max(float(width), g.width + pad, (g.height + pad) * 16 / 9)
        cv.focus(c, w, run_time=rt)
        return
    if pos is not None:
        c = scene.c2p(*scene.resolve_coord(pos))
    elif isinstance(focus, str) and scene.chalk is not None and focus in cv.by_id:
        cv.goto(focus, run_time=rt, overview=False)
        return
    elif focus is not None:
        c = scene.get(focus).get_center()
    else:
        raise ValueError("camera 액션에는 focus, pos, ids 또는 reset 이 필요합니다")
    cv.focus(c, float(width), run_time=rt)


@action("custom")
def custom(scene, fn: str, **params):
    """프로젝트의 hooks.py 에 정의된 함수 호출: fn(scene, **params)"""
    hook = scene.hooks.get(fn)
    if hook is None:
        raise KeyError(f"hooks 에 {fn!r} 가 없습니다. 사용 가능: {sorted(scene.hooks)}")
    params.pop("run_time", None)
    hook(scene, **params)
