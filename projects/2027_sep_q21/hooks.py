"""2027학년도 9월 모평 21번 전용 커스텀 애니메이션 (`custom` 액션에서 호출).

- corner_tangents : 함수의 한 점에서 좌·우 접선을 따로 그려 '뾰족점(미분 불가능)'을 보여준다.
- sweep_param     : 매개변수(a)를 움직이며 그래프와 근의 위치가 변하는 모습을 실시간으로 보여준다.
"""

from __future__ import annotations

from manim import (
    DOWN, LEFT, RIGHT, UP, UL, UR, DL, DR, Create, DecimalNumber, Dot, FadeIn, FadeOut, Line, VGroup,
    ValueTracker, always_redraw, rate_functions,
)

from explainer.render.actions import _plot_pieces, caption as caption_action
from explainer.script.loader import make_function


def _one_sided_slopes(f, x0: float, h: float = 1e-5) -> tuple[float, float]:
    return (f(x0) - f(x0 - h)) / h, (f(x0 + h) - f(x0)) / h


def corner_tangents(scene, func: str, x0, length: float = 0.7, color: str | None = None,
                    left_label: str | None = None, right_label: str | None = None,
                    left_dir: str = "UL", right_dir: str = "UR", id: str = "corner", run_time: float = 1.2,
                    label_scale: float = 0.62, marker: bool = True, stroke_width: float = 3.2, **_):
    """x = x0 에서 좌·우 미분계수를 수치로 구해 두 반접선을 그린다. 기울기가 다르면 뾰족점이 드러난다."""
    f = scene.funcs[func]
    x0 = scene.eval(x0)
    y0 = f(x0)
    m_left, m_right = _one_sided_slopes(f, x0)
    col = scene.color(color, scene.theme.highlight)
    p0 = scene.c2p(x0, y0)
    left = Line(scene.c2p(x0 - length, y0 - m_left * length), p0, color=col, stroke_width=stroke_width)
    right = Line(p0, scene.c2p(x0 + length, y0 + m_right * length), color=col, stroke_width=stroke_width)
    left.set_z_index(7)
    right.set_z_index(7)
    parts = [left, right]
    anims = [Create(left), Create(right)]
    if marker:
        dot = Dot(p0, radius=0.07, color=col).set_z_index(8)
        dot.set_stroke(scene.theme.background, width=2)
        parts.append(dot)
        anims.append(FadeIn(dot, scale=0.5))
    for text, ln, d in ((left_label, left, left_dir), (right_label, right, right_dir)):
        if not text:
            continue
        lab = scene.mtex(text, color=color, scale=label_scale, plain=True)
        lab.next_to(ln.get_center(), scene.direction(d), buff=0.12)
        lab.add_background_rectangle(color=scene.theme.background, opacity=0.8, buff=0.05)
        lab.set_z_index(8)
        parts.append(lab)
        anims.append(FadeIn(lab, shift=scene.direction(d) * 0.1))
    group = VGroup(*parts)
    scene.register(id, group, (x0, y0))
    scene.register(f"{id}_left", left)
    scene.register(f"{id}_right", right)
    scene.play(*anims, run_time=run_time)


def sweep_param(scene, expr: str, param: str, values: list, id: str = "sweep", color: str | None = None,
                roots: list | None = None, roots_color: str | None = None, readout: str = "a =",
                readout_at: list | None = None, stop_captions: list | None = None, pause: float = 0.7,
                run_time: float = 6.0, stroke_width: float = 4.0, smooth: bool = False, keep: bool = True,
                abs_of: str | None = None, **_):
    """param 의 값을 values 순서로 바꾸며 y = expr 그래프를 다시 그린다.

    roots      : param 에 의존하는 x 좌표 식들(예: ["1", "a", "4-a"]) → x축 위 점으로 표시
    stop_captions : 각 values[i] 에 도착했을 때 보여줄 캡션 문장(빈 문자열이면 유지)
    abs_of     : 주면 expr 대신 |abs_of| 를 점선(원본)으로 함께 그린다
    """
    values = [scene.eval(v) for v in values]
    tracker = ValueTracker(values[0])
    col = scene.color(color, scene.theme.accent)
    rcol = scene.color(roots_color, scene.theme.palette["point"])

    def env():
        p = dict(scene.params)
        p[param] = tracker.get_value()
        return p

    def make_curve():
        f = make_function(expr, {**scene.funcs, **env()})
        return _plot_pieces(scene, f, None, col, stroke_width, smooth=smooth, samples=300, steps=300)

    def make_roots():
        g = VGroup()
        for rx in roots or []:
            xv = float(make_function(str(rx), env(), var="__unused")(0.0))
            d = Dot(scene.c2p(xv, 0), radius=0.075, color=rcol).set_z_index(6)
            d.set_stroke(scene.theme.background, width=2)
            g.add(d)
        return g

    curve = always_redraw(make_curve)
    root_dots = always_redraw(make_roots)

    xr, yr = scene.axes_ranges
    anchor = readout_at or [xr[1] - 1.7, yr[1] - 0.55]
    label = scene.ktext(readout, size=26, color=col)
    value = DecimalNumber(values[0], num_decimal_places=2, color=col).scale(0.75)
    value.add_updater(lambda m: m.set_value(tracker.get_value()).next_to(label, RIGHT, buff=0.12))
    box = VGroup(label, value)
    label.move_to(scene.c2p(*[scene.eval(v) for v in anchor]))
    value.next_to(label, RIGHT, buff=0.12)
    label.add_background_rectangle(color=scene.theme.background, opacity=0.85, buff=0.06)
    box.set_z_index(9)

    scene.add(curve, root_dots, box)
    scene.play(FadeIn(curve), FadeIn(root_dots), FadeIn(box), run_time=0.5)
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
    curve.clear_updaters()
    root_dots.clear_updaters()
    value.clear_updaters()
    scene.funcs[id] = make_function(expr, {**scene.funcs, **env()})
    if keep:
        scene.register(id, curve)
        scene.register(f"{id}_roots", root_dots)
        scene.register(f"{id}_readout", box)
    else:
        scene.play(FadeOut(curve), FadeOut(root_dots), FadeOut(box), run_time=0.4)
