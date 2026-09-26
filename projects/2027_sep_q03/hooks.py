"""2027학년도 9월 모평 3번 전용 커스텀 애니메이션 (`custom` 액션에서 호출).

- term_line : 등차수열의 항 a_1 … a_n 을 한 줄로 늘어놓은 '항 번호 줄'을 판서 커서 위치에 그린다.
- term_hops : 항 사이를 공차만큼 뛰어넘는 화살표(호)를 하나씩 그리며 '몇 번 더했는지'를 눈으로 세게 한다.
"""

from __future__ import annotations

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, PI, ArcBetweenPoints, Create, Dot, FadeIn, FadeOut, Line, MathTex, VGroup, Write,
)

from explainer.render.chalk import handwrite


def term_line(scene, n: int = 10, known: dict | None = None, id: str = "terms", color: str | None = None,
              known_color: str | None = None, height: float = 2.4, **_):
    """a_1 … a_n 점과 라벨. known = {번호: "값"} 이면 그 항 아래에 값을 함께 적는다."""
    cv = scene.chalk
    sec = cv.section()
    col = scene.color(color, scene.theme.text)
    kcol = scene.color(known_color, scene.theme.highlight)
    width = sec.notes_width - 0.4
    xs = np.linspace(0, width, n)
    base = Line(LEFT * 0.3, RIGHT * (width + 0.3), color=scene.theme.axis, stroke_width=2)
    dots, labels, values = VGroup(), VGroup(), VGroup()
    for k, x in enumerate(xs, start=1):
        p = np.array([x, 0.0, 0.0])
        d = Dot(p, radius=0.07, color=col).set_z_index(5)
        lab = scene.mtex(f"a_{{{k}}}", scale=0.75, plain=True).next_to(p, DOWN, buff=0.18)
        dots.add(d)
        labels.add(lab)
        if known and (k in known or str(k) in known):
            v = known.get(k, known.get(str(k)))
            vm = scene.mtex(str(v), scale=0.8, plain=True, color=known_color).next_to(lab, DOWN, buff=0.12)
            vm.set_color(kcol)
            vm._term_index = k
            values.add(vm)
    g = VGroup(base, dots, labels, values)
    # 호(hop)가 들어갈 자리를 위에 남겨 둔다
    cv.advance(max(0.0, height - g.height), sec)
    cv.place_line(g, indent=0.2, sec=sec)
    cv.advance(0.25, sec)
    scene.register(id, g)
    scene._term_pts = [np.array([base.get_left()[0] + 0.3 + x, base.get_center()[1], 0.0]) for x in xs]
    scene._term_dots = dots
    scene._term_labels = labels
    scene._term_values = values
    scene.play(Create(base), run_time=0.5)
    scene.play(FadeIn(dots, lag_ratio=0.08), Write(labels, lag_ratio=0.08), run_time=1.2)
    if len(values):
        scene.play(handwrite(values, run_time=0.6))


def term_hops(scene, start: int, end: int, label: str = "+d", color: str | None = None, id: str = "hops",
              total: str | None = None, total_color: str | None = None, run_time: float = 0.55, arc_height: float = 0.55,
              **_):
    """a_start → a_end 까지 한 항씩 뛰어넘는 호 + 라벨. total 을 주면 전체를 감싸는 큰 호와 함께 적는다."""
    pts = scene._term_pts
    col = scene.color(color, scene.theme.highlight)
    tcol = scene.color(total_color, scene.theme.palette.get("ok", col))
    hops = VGroup()
    for k in range(start, end):
        a, b = pts[k - 1] + UP * 0.12, pts[k] + UP * 0.12
        arc = ArcBetweenPoints(a, b, angle=-PI * 0.9, color=col, stroke_width=3).set_z_index(6)
        arc.add_tip(tip_length=0.16, tip_width=0.14)
        lab = scene.mtex(label, scale=0.62, plain=True).set_color(col).next_to(arc, UP, buff=0.05)
        hops.add(VGroup(arc, lab))
        scene.play(Create(arc), FadeIn(lab, shift=UP * 0.1), run_time=run_time)
    scene.register(id, hops)
    for k in range(start, end + 1):
        scene._term_dots[k - 1].set_color(col)
    if total:
        a, b = pts[start - 1] + UP * (0.12 + arc_height + 0.25), pts[end - 1] + UP * (0.12 + arc_height + 0.25)
        chord = float(np.linalg.norm(b - a))
        big = ArcBetweenPoints(a, b, angle=-min(PI * 0.3, 3.6 / max(chord, 1e-6)), color=tcol, stroke_width=3.2).set_z_index(6)
        tl = scene.mtex(total, scale=0.8, plain=True).set_color(tcol).next_to(big, UP, buff=0.08)
        scene.register(f"{id}_total", VGroup(big, tl))
        scene.play(Create(big), run_time=0.6)
        scene.play(handwrite(tl, run_time=0.6))


def term_value(scene, index: int, value: str, color: str | None = None, run_time: float = 0.8, **_):
    """항 아래의 값(예: '?')을 새 값으로 바꾼다 — 구한 답을 그림에 되돌려 놓는다."""
    from manim import ReplacementTransform, Circumscribe
    col = scene.color(color, scene.theme.highlight)
    old = next((v for v in scene._term_values if getattr(v, "_term_index", None) == index), None)
    new = scene.mtex(str(value), scale=0.8, plain=True).set_color(col)
    if old is not None:
        new.move_to(old)
        scene.play(ReplacementTransform(old, new), run_time=run_time)
        scene._term_values.remove(old)
    else:
        new.next_to(scene._term_labels[index - 1], DOWN, buff=0.12)
        scene.play(handwrite(new, run_time=run_time))
    scene._term_values.add(new)
    scene.play(Circumscribe(new, color=col, buff=0.1), run_time=0.7)
