"""2027학년도 9월 모평 2번 전용 커스텀 애니메이션 (`custom` 액션에서 호출).

- secant_to_tangent : 점 Q 를 점 P 쪽으로 보내며 할선이 접선으로 수렴하는 모습과 기울기 값을 실시간으로 보여준다.
"""

from __future__ import annotations

from manim import (
    DOWN, LEFT, RIGHT, UP, UL, UR, DL, DR, Create, DashedLine, DecimalNumber, Dot, FadeIn, FadeOut, Line, VGroup,
    ValueTracker, always_redraw, rate_functions,
)

from explainer.render.actions import caption as caption_action


def secant_to_tangent(scene, func: str, x0, x_from, x_to, color: str | None = None, tangent_color: str | None = None,
                      run_time: float = 4.0, id: str = "secant", readout: str = "기울기 =", readout_at: list | None = None,
                      span: float = 1.1, label_p: str = "\\mathrm{P}", label_q: str = "\\mathrm{Q}",
                      final_caption: str = "", keep: bool = True, stroke_width: float = 3.2,
                      sweep_at=None, **_):
    """P(x0, f(x0)) 는 고정, Q(x, f(x)) 의 x 를 x_from → x_to 로 움직인다. 할선의 기울기 = 평균변화율.

    sweep_at: 할선을 먼저 그려 놓고, 이 내레이션 표식(예: s3)까지 기다린 뒤 Q 를 움직인다."""
    f = scene.funcs[func]
    x0 = scene.eval(x0)
    x_from, x_to = scene.eval(x_from), scene.eval(x_to)
    col = scene.color(color, scene.theme.highlight)
    tcol = scene.color(tangent_color, scene.theme.palette.get("ok", col))
    t = ValueTracker(x_from)
    p0 = scene.c2p(x0, f(x0))

    def slope():
        x = t.get_value()
        if abs(x - x0) < 1e-6:
            h = 1e-5
            return (f(x0 + h) - f(x0 - h)) / (2 * h)
        return (f(x) - f(x0)) / (x - x0)

    yr_lo, yr_hi = scene.axes_ranges[1][0], scene.axes_ranges[1][1]

    def clipped(m, xa, xb):
        """기울기 m 으로 P 를 지나는 직선의 [xa, xb] 구간을 y 범위 안으로 잘라낸다."""
        y0 = f(x0)
        for lim in (yr_lo, yr_hi):
            if abs(m) > 1e-9:
                xc = x0 + (lim - y0) / m
                if xa < xc < x0:
                    xa = xc
                if x0 < xc < xb:
                    xb = xc
        return xa, xb

    def make_secant():
        m = slope()
        xa, xb = clipped(m, x0 - span * 0.55, x0 + span)
        return Line(scene.c2p(xa, f(x0) + m * (xa - x0)), scene.c2p(xb, f(x0) + m * (xb - x0)),
                    color=col, stroke_width=stroke_width).set_z_index(6)

    def make_q():
        x = t.get_value()
        return Dot(scene.c2p(x, f(x)), radius=0.075, color=col).set_z_index(8)

    def make_guides():
        x = t.get_value()
        q = scene.c2p(x, f(x))
        corner = scene.c2p(x, f(x0))
        g = VGroup(DashedLine(p0, corner, color=scene.theme.muted, stroke_width=1.6, dash_length=0.08),
                   DashedLine(corner, q, color=scene.theme.muted, stroke_width=1.6, dash_length=0.08))
        return g.set_z_index(4)

    P = Dot(p0, radius=0.075, color=scene.theme.palette.get("point", col)).set_z_index(8)
    lp = scene.mtex(label_p, scale=0.7, plain=True).next_to(P, DL, buff=0.08).set_z_index(9)
    secant = always_redraw(make_secant)
    Q = always_redraw(make_q)
    lq = always_redraw(lambda: scene.mtex(label_q, scale=0.7, plain=True, color=color).next_to(Q, UR if t.get_value() > x0 else UL, buff=0.08).set_z_index(9))
    guides = always_redraw(make_guides)

    xr, yr = scene.axes_ranges
    anchor = readout_at or [xr[0] + 0.3, yr[1] - (yr[1] - yr[0]) * 0.08]
    label = scene.ktext(readout, size=26, color=col)
    value = DecimalNumber(slope(), num_decimal_places=2, color=col).scale(0.8)
    scene.finish_text(value)
    value.add_updater(lambda m: m.set_value(slope()).next_to(label, RIGHT, buff=0.12))
    label.move_to(scene.c2p(*[scene.eval(v) for v in anchor]), aligned_edge=LEFT)
    value.next_to(label, RIGHT, buff=0.12)
    box = VGroup(label, value).set_z_index(9)

    scene.play(FadeIn(P), FadeIn(lp), run_time=0.4)
    scene.add(guides, secant, Q, lq, box)
    scene.play(FadeIn(guides), Create(secant), FadeIn(Q), FadeIn(lq), FadeIn(box), run_time=0.8)
    if sweep_at is not None and scene.current_segment is not None:
        scene.wait_until(scene.current_segment.resolve_at(sweep_at))
    scene.play(t.animate.set_value(x_to), run_time=run_time, rate_func=rate_functions.ease_in_out_sine)
    for m in (secant, Q, lq, guides, value):
        m.clear_updaters()
    # 마지막: 접선으로 굳히고 기울기를 f'(x0) 값으로 표시
    h = 1e-5
    m_t = (f(x0 + h) - f(x0 - h)) / (2 * h)
    xa, xb = clipped(m_t, x0 - span * 0.8, x0 + span)
    tangent = Line(scene.c2p(xa, f(x0) + m_t * (xa - x0)), scene.c2p(xb, f(x0) + m_t * (xb - x0)),
                   color=tcol, stroke_width=stroke_width + 0.6).set_z_index(7)
    scene.play(FadeOut(guides), FadeOut(Q), FadeOut(lq), secant.animate.set_color(tcol), run_time=0.5)
    scene.play(Create(tangent), FadeOut(secant), value.animate.set_value(m_t).set_color(tcol), label.animate.set_color(tcol), run_time=0.8)
    if final_caption:
        caption_action(scene, text=final_caption, run_time=0.4)
    if keep:
        scene.register(id, tangent)
        scene.register(f"{id}_P", VGroup(P, lp))
        scene.register(f"{id}_readout", box)
    else:
        scene.play(FadeOut(tangent), FadeOut(box), FadeOut(P), FadeOut(lp), run_time=0.4)
