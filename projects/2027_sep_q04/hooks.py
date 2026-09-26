"""2027학년도 9월 모평 4번 전용 커스텀 애니메이션 (`custom` 액션에서 호출).

- piecewise_gap : 상수 a 를 움직이며 x = 2 에서 두 조각의 끝점(●, ○) 사이 '틈'이 닫히는 순간을 보여준다.
"""

from __future__ import annotations

from manim import (
    DOWN, LEFT, RIGHT, UP, UL, UR, DL, DR, Circle, Create, DashedLine, DecimalNumber, Dot, FadeIn, FadeOut, Line,
    MathTex, VGroup, ValueTracker, always_redraw, rate_functions,
)

from explainer.render.actions import _plot_pieces, caption as caption_action
from explainer.script.loader import make_function


def piecewise_gap(scene, left_expr: str, right_expr: str, split, param: str, values: list, id: str = "pw",
                  left_color: str | None = None, right_color: str | None = None, gap_color: str | None = None,
                  readout: str = "a =", readout_at: list | None = None, left_label: str | None = None,
                  right_label: str | None = None, stop_captions: list | None = None, pause: float = 0.6,
                  run_time: float = 5.0, stroke_width: float = 4.0, gap_label: str = "틈", **_):
    """x ≤ split 는 left_expr, x > split 는 right_expr. param 의 값을 values 순서로 바꾸며 다시 그린다."""
    x_s = scene.eval(split)
    values = [scene.eval(v) for v in values]
    tracker = ValueTracker(values[0])
    lcol = scene.color(left_color, scene.theme.palette.get("q1"))
    rcol = scene.color(right_color, scene.theme.palette.get("exp"))
    gcol = scene.color(gap_color, scene.theme.palette.get("warn"))
    xr, yr = scene.axes_ranges

    def env():
        p = dict(scene.params)
        p[param] = tracker.get_value()
        return p

    def fl():
        return make_function(left_expr, {**scene.funcs, **env()})

    def fr():
        return make_function(right_expr, {**scene.funcs, **env()})

    def make_left():
        return _plot_pieces(scene, fl(), [xr[0], x_s], lcol, stroke_width, smooth=True, samples=200, steps=200)

    def make_right():
        return _plot_pieces(scene, fr(), [x_s, xr[1]], rcol, stroke_width, smooth=True, samples=200, steps=200)

    def make_ends():
        yl, yr_ = fl()(x_s), fr()(x_s)
        closed = Dot(scene.c2p(x_s, yl), radius=0.085, color=lcol).set_z_index(8)
        open_ = Circle(radius=0.085, color=rcol, stroke_width=3).move_to(scene.c2p(x_s, yr_)).set_z_index(8)
        open_.set_fill(scene.theme.background, opacity=1.0)
        return VGroup(closed, open_)

    def make_gap():
        yl, yr_ = fl()(x_s), fr()(x_s)
        if abs(yl - yr_) < 1e-3:
            return VGroup()
        a, b = scene.c2p(x_s, yl), scene.c2p(x_s, yr_)
        x_off = RIGHT * 0.45
        br = VGroup(Line(a + x_off * 0.6, a + x_off, color=gcol, stroke_width=2.4),
                    Line(a + x_off, b + x_off, color=gcol, stroke_width=2.4),
                    Line(b + x_off * 0.6, b + x_off, color=gcol, stroke_width=2.4)).set_z_index(7)
        lab = scene.ktext(gap_label, size=22, color=gap_color or "warn").next_to(br, RIGHT, buff=0.08)
        return VGroup(br, lab)

    left = always_redraw(make_left)
    right = always_redraw(make_right)
    ends = always_redraw(make_ends)
    gap = always_redraw(make_gap)

    anchor = readout_at or [xr[0] + 0.3, yr[1] - (yr[1] - yr[0]) * 0.08]
    label = scene.ktext(readout, size=26, color=scene.theme.highlight)
    value = DecimalNumber(values[0], num_decimal_places=1, color=scene.theme.highlight).scale(0.8)
    scene.finish_text(value)
    value.add_updater(lambda m: m.set_value(tracker.get_value()).next_to(label, RIGHT, buff=0.12))
    label.move_to(scene.c2p(*[scene.eval(v) for v in anchor]), aligned_edge=LEFT)
    value.next_to(label, RIGHT, buff=0.12)
    box = VGroup(label, value).set_z_index(9)

    labels = VGroup()
    if left_label:
        lm = scene.mtex(left_label, scale=0.7, plain=True).set_color(lcol)
        lm.next_to(scene.c2p(xr[0] + 0.6, fl()(xr[0] + 0.6)), UL, buff=0.12)
        labels.add(lm)
    if right_label:
        rm = scene.mtex(right_label, scale=0.7, plain=True).set_color(rcol)
        rm.next_to(scene.c2p(x_s + 0.9, fr()(x_s + 0.9)), DR, buff=0.12)
        labels.add(rm)
    for m in labels:
        m.set_z_index(9)

    vline = DashedLine(scene.c2p(x_s, yr[0]), scene.c2p(x_s, yr[1]), color=scene.theme.muted, stroke_width=1.6,
                       dash_length=0.1).set_z_index(3)
    scene.play(Create(vline), run_time=0.4)
    scene.add(left, right, ends, gap, box, labels)
    scene.play(Create(left), Create(right), run_time=1.2)
    scene.play(FadeIn(ends), FadeIn(gap), FadeIn(box), FadeIn(labels), run_time=0.6)
    if stop_captions and stop_captions[0]:
        caption_action(scene, text=stop_captions[0], run_time=0.4)
    total = sum(abs(b - a) for a, b in zip(values, values[1:])) or 1.0
    for i, (a, b) in enumerate(zip(values, values[1:]), start=1):
        scene.play(tracker.animate.set_value(b), run_time=max(0.6, run_time * abs(b - a) / total),
                   rate_func=rate_functions.ease_in_out_sine)
        if stop_captions and i < len(stop_captions) and stop_captions[i]:
            caption_action(scene, text=stop_captions[i], run_time=0.4)
        if pause > 0:
            scene.wait(pause)
    for m in (left, right, ends, gap, value):
        m.clear_updaters()
    scene.register(id, VGroup(left, right))
    scene.register(f"{id}_ends", ends)
    scene.register(f"{id}_readout", box)
    scene.register(f"{id}_vline", vline)
    scene.register(f"{id}_labels", labels)
