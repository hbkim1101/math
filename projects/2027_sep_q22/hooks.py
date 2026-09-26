"""2027학년도 9월 모평 22번 전용 커스텀 애니메이션 (`custom` 액션에서 호출)."""

from __future__ import annotations

from manim import (
    DOWN, LEFT, RIGHT, UP, UR, DecimalNumber, Dot, FadeIn, FadeOut, Line, MathTex, VGroup,
    ValueTracker, always_redraw, linear, rate_functions,
)


def sliding_chord(scene, func: str = "q1", gap: float = 0.75, t_from: float = -0.15, t_to: float = 1.1,
                  t_final: float = 0.75, color: str | None = None, run_time: float = 4.0, id: str = "chord",
                  label: str = "기울기 =", **_):
    """포물선 위에서 x좌표 차가 gap 으로 고정된 현을 미끄러뜨리며 기울기 값을 실시간으로 보여준다.

    기울기 = 2(x1 + x2) - 7/2 가 x1 에 대한 일차식이므로 값이 선형으로 변하는 것을 시각화한다.
    """
    f = scene.funcs[func]
    col = scene.color(color, scene.theme.highlight)
    t = ValueTracker(t_from)

    def make_chord():
        x1 = t.get_value()
        x2 = x1 + gap
        p1, p2 = scene.c2p(x1, f(x1)), scene.c2p(x2, f(x2))
        ln = Line(p1, p2, color=col, stroke_width=4).set_z_index(4)
        d1 = Dot(p1, radius=0.06, color=col).set_z_index(5)
        d2 = Dot(p2, radius=0.06, color=col).set_z_index(5)
        return VGroup(ln, d1, d2)

    chord = always_redraw(make_chord)

    slope_val = DecimalNumber(0, num_decimal_places=2, color=col).scale(0.7)
    slope_lab = scene.ktext(label, size=24, color=col)

    def update_slope(m):
        x1 = t.get_value()
        x2 = x1 + gap
        m.set_value((f(x2) - f(x1)) / (x2 - x1))
        m.next_to(slope_lab, RIGHT, buff=0.08)

    slope_val.add_updater(update_slope)
    readout = VGroup(slope_lab, slope_val)

    def place_readout(g):
        x1 = t.get_value()
        mid = scene.c2p(x1 + gap / 2, f(x1 + gap / 2))
        slope_lab.next_to(mid, UR, buff=0.35)
        update_slope(slope_val)

    readout.add_updater(place_readout)
    place_readout(readout)
    scene.bg_rect(slope_lab, opacity=0.8, buff=0.04)

    scene.add(chord, readout)
    scene.play(FadeIn(chord), FadeIn(readout), run_time=0.4)
    scene.play(t.animate.set_value(t_to), run_time=run_time * 0.55, rate_func=rate_functions.ease_in_out_sine)
    scene.play(t.animate.set_value(t_final), run_time=run_time * 0.45, rate_func=rate_functions.ease_in_out_sine)
    readout.clear_updaters()
    slope_val.clear_updaters()
    chord.clear_updaters()
    scene.register(id, chord)
    scene.register(f"{id}_readout", readout)


def ghost_translate(scene, source: str, dx: float, dy: float, run_time: float = 1.8, color: str | None = None,
                    id: str = "ghost", keep: bool = False, **_):
    """그래프(곡선)의 반투명 복사본이 (dx, dy)만큼 미끄러져 다른 곡선 위에 겹쳐지는 연출."""
    src = scene.get(source)
    ghost = src.copy().set_stroke(opacity=0.55)
    if color:
        ghost.set_color(scene.color(color))
    vec = scene.c2p(dx, dy) - scene.c2p(0, 0)
    scene.add(ghost)
    scene.play(ghost.animate.shift(vec), run_time=run_time, rate_func=rate_functions.ease_in_out_cubic)
    if keep:
        scene.register(id, ghost)
    else:
        scene.play(FadeOut(ghost), run_time=0.4)
