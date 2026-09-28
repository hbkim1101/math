"""2026학년도 수능 미적분 30번 전용 커스텀 애니메이션 (`custom` 액션에서 호출).

- inverse_curve : 이미 plot 한 (증가)함수 h 의 역함수 y = h^{-1}(x) 를 그린다. (t, h(t)) → (h(t), t) 매개곡선.
                  scene.funcs[id] 에 수치 역함수(이분법)를 등록하므로 이후 plot/line 식이나 slope_sweep 에서 쓸 수 있다.
- slope_sweep   : 한 점을 지나는 직선의 기울기 k 를 움직이며 곡선과의 교점 개수를 실시간으로 센다 (교점 ●, 개수 판독).
                  개수는 화면 밖까지 넓은 구간에서 부호 변화로 계산하고, 화면 안의 교점만 점으로 그린다.
- sweep_to      : slope_sweep 이후 기울기를 다른 값으로 이어서 움직인다 (내레이션 `at` 동기화용).
"""

from __future__ import annotations

import math

from manim import (
    DOWN, LEFT, RIGHT, UP, UL, UR, DL, DR, Create, DashedLine, DecimalNumber, Dot, FadeIn, FadeOut, VGroup,
    ValueTracker, always_redraw, rate_functions,
)

from explainer.render.actions import _plot_pieces, caption as caption_action


def _bisect_inverse(h, lo: float = -60.0, hi: float = 60.0):
    """증가함수 h 의 수치 역함수. y 가 [h(lo), h(hi)] 를 벗어나면 끝값으로 잠근다."""
    def inv(y: float) -> float:
        a, b = lo, hi
        fa = h(a)
        if y <= fa:
            return a
        if y >= h(b):
            return b
        for _ in range(60):
            m = 0.5 * (a + b)
            if h(m) < y:
                a = m
            else:
                b = m
        return 0.5 * (a + b)
    return inv


def inverse_curve(scene, source: str, id: str, color: str | None = None, label: str | None = None, label_at=None,
                  label_dir="UR", label_scale: float = 0.7, stroke_width: float = 4.0, run_time: float = 1.4,
                  diag: bool = True, diag_color: str | None = None, **_):
    """source(증가함수) 의 역함수 그래프를 그리고 scene.funcs[id] 에 수치 역함수를 등록한다."""
    h = scene.funcs[source]
    axes = scene.axes
    xr, yr = scene.axes_ranges
    col = scene.color(color, scene.theme.palette.get("exp", scene.theme.accent))
    inv = _bisect_inverse(h)
    scene.funcs[id] = inv
    # (h(t), t) 가 화면 안에 있는 t 구간만 그린다 (h 는 증가하므로 구간 하나)
    ts = [yr[0] + (yr[1] - yr[0]) * i / 600 for i in range(601)]
    ok = [t for t in ts if xr[0] <= h(t) <= xr[1]]
    t0, t1 = (min(ok), max(ok)) if ok else (yr[0], yr[1])
    curve = axes.plot_parametric_curve(lambda t: (h(t), t), t_range=[t0, t1], color=col, stroke_width=stroke_width).set_z_index(3)
    scene.register(id, curve)
    anims = []
    if diag:
        lo, hi = max(xr[0], yr[0]), min(xr[1], yr[1])
        d = DashedLine(axes.c2p(lo, lo), axes.c2p(hi, hi), color=scene.color(diag_color, scene.theme.palette.get("axis_sym", scene.theme.muted)),
                       stroke_width=2.0, dash_length=0.12).set_z_index(1)
        scene.register(f"{id}_diag", d)
        anims.append(Create(d))
    anims.append(Create(curve))
    scene.play(*anims, run_time=run_time)
    if label:
        lab = scene.mtex(label, color=color, scale=label_scale, plain=True)
        if label_at is not None:
            x = scene.eval(label_at)
            lab.next_to(axes.c2p(x, inv(x)), scene.direction(label_dir), buff=0.12)
        else:
            lab.next_to(curve, scene.direction(label_dir), buff=0.1)
        lab.set_z_index(9)
        scene.register(f"{id}_label", lab)
        scene.play(FadeIn(lab), run_time=0.4)


def _count_roots(g, lo: float, hi: float, n: int = 4000):
    """g 의 부호 변화(또는 0) 개수와 근의 위치들. 접점(부호 변화 없는 근)은 국소 최소 |g| 가 매우 작을 때로 잡는다."""
    xs = [lo + (hi - lo) * i / n for i in range(n + 1)]
    vals = []
    for x in xs:
        try:
            vals.append(g(x))
        except (ValueError, OverflowError, ZeroDivisionError):
            vals.append(float("nan"))
    roots = []
    for i in range(n):
        a, b = vals[i], vals[i + 1]
        if math.isnan(a) or math.isnan(b):
            continue
        if a == 0.0:
            roots.append(xs[i])
        elif a * b < 0:
            # 선형 보간
            roots.append(xs[i] - a * (xs[i + 1] - xs[i]) / (b - a))
    # 접점: 부호가 바뀌지 않지만 |g| 가 0 에 매우 가까운 국소 최소
    for i in range(1, n):
        a, b, c = vals[i - 1], vals[i], vals[i + 1]
        if any(math.isnan(v) for v in (a, b, c)):
            continue
        if abs(b) <= abs(a) and abs(b) <= abs(c) and abs(b) < 2e-3 and a * c > 0:
            if not any(abs(r - xs[i]) < (hi - lo) / n * 3 for r in roots):
                roots.append(xs[i])
    roots.sort()
    return roots


def slope_sweep(scene, func: str, point: list, k_from, k_to, id: str = "sw", color: str | None = None,
                dot_color: str | None = None, run_time: float = 4.0, readout: str = "k =", count_label: str = "교점",
                readout_at: list | None = None, decimals: int = 2, domain: list | None = None,
                stroke_width: float = 3.0, pause: float = 0.4, caption: str | None = None, at=None,
                highlight_counts: list | None = None, **_):
    """점 point 를 지나고 기울기 k 인 직선을 k_from → k_to 로 움직이며 y = func(x) 와의 교점 개수를 센다."""
    if at is not None and scene.current_segment is not None:
        scene.wait_until(scene.current_segment.resolve_at(at))
    f = scene.funcs[func]
    axes = scene.axes
    xr, yr = scene.axes_ranges
    px, py = (scene.eval(point[0]), scene.eval(point[1]))
    k0, k1 = scene.eval(k_from), scene.eval(k_to)
    lo, hi = (scene.eval(domain[0]), scene.eval(domain[1])) if domain else (-40.0, 40.0)
    col = scene.color(color, scene.theme.palette.get("point", scene.theme.accent))
    dcol = scene.color(dot_color, scene.theme.palette.get("warn", col))
    tracker = ValueTracker(k0)

    def line_fn(k):
        return lambda x: k * (x - px) + py

    def make_line():
        k = tracker.get_value()
        return _plot_pieces(scene, line_fn(k), None, col, stroke_width, samples=200).set_z_index(4)

    cache = {}

    def roots_now():
        k = round(tracker.get_value(), 6)
        if k not in cache:
            g = lambda x: f(x) - (k * (x - px) + py)
            cache.clear()
            cache[k] = _count_roots(g, lo, hi, n=1600)
        return cache[k]

    def make_dots():
        vg = VGroup()
        for r in roots_now():
            y = f(r)
            if xr[0] <= r <= xr[1] and yr[0] <= y <= yr[1]:
                vg.add(Dot(axes.c2p(r, y), radius=0.085, color=dcol).set_z_index(8))
        return vg

    anchor = readout_at or [xr[0] + 0.25, yr[1] - (yr[1] - yr[0]) * 0.07]
    lab = scene.ktext(readout, size=24, color=scene.theme.highlight)
    lab.move_to(axes.c2p(*[scene.eval(v) for v in anchor]), aligned_edge=LEFT).set_z_index(9)
    val = DecimalNumber(k0, num_decimal_places=decimals, color=scene.theme.highlight).scale(0.75)
    scene.finish_text(val)
    val.add_updater(lambda m: m.set_value(tracker.get_value()).next_to(lab, RIGHT, buff=0.12))
    val.set_z_index(9)
    cnt_lab = scene.ktext(count_label, size=24, color=dcol).set_z_index(9)
    cnt_lab.next_to(lab, DOWN, buff=0.12, aligned_edge=LEFT)
    cnt = DecimalNumber(0, num_decimal_places=0, color=dcol).scale(0.8)
    scene.finish_text(cnt)
    cnt.add_updater(lambda m: m.set_value(len(roots_now())).next_to(cnt_lab, RIGHT, buff=0.12))
    cnt.set_z_index(9)
    unit = scene.ktext("개", size=22, color=dcol).set_z_index(9)
    unit.add_updater(lambda m: m.next_to(cnt, RIGHT, buff=0.06))

    fixed = Dot(axes.c2p(px, py), radius=0.09, color=col).set_z_index(9)
    line = always_redraw(make_line)
    dots = always_redraw(make_dots)
    scene.play(FadeIn(fixed), run_time=0.3)
    scene.add(line, dots, lab, val, cnt_lab, cnt, unit)
    scene.play(Create(line), FadeIn(lab), FadeIn(val), FadeIn(cnt_lab), FadeIn(cnt), FadeIn(unit), run_time=0.7)
    scene._sweep = {"tracker": tracker, "dyn": (line, dots, val, cnt, unit), "id": id,
                    "mobs": {id: line, f"{id}_dots": dots, f"{id}_point": fixed,
                             f"{id}_readout": VGroup(lab, val, cnt_lab, cnt, unit)}}
    if abs(k1 - k0) > 1e-9:
        scene.play(tracker.animate.set_value(k1), run_time=run_time, rate_func=rate_functions.ease_in_out_sine)
    if caption:
        caption_action(scene, text=caption, run_time=0.4)
    if pause > 0:
        scene.wait(pause)


def sweep_to(scene, k, run_time: float = 2.0, pause: float = 0.4, caption: str | None = None, at=None,
             finish: bool = False, **_):
    """`slope_sweep` 의 기울기를 k 로 이어서 움직인다. finish=true 면 업데이터를 멈추고 객체들을 id 로 등록."""
    if at is not None and scene.current_segment is not None:
        scene.wait_until(scene.current_segment.resolve_at(at))
    st = scene._sweep
    scene.play(st["tracker"].animate.set_value(scene.eval(k)), run_time=run_time,
               rate_func=rate_functions.ease_in_out_sine)
    if caption:
        caption_action(scene, text=caption, run_time=0.4)
    if pause > 0:
        scene.wait(pause)
    if finish:
        for m in st["dyn"]:
            m.clear_updaters()
        for key, m in st["mobs"].items():
            scene.register(key, m)


def step_graph(scene, id: str, pieces: list, color: str | None = None, dot_color: str | None = None,
               stroke_width: float = 4.0, run_time: float = 1.6, **_):
    """계단형 그래프. pieces: [{x: [a, b], y: v, open: [true, false]}] 또는 {x: a, y: v} (한 점).
    구간 끝의 열린 점은 ○, 닫힌 점은 ● 로 표시한다."""
    axes = scene.axes
    col = scene.color(color, scene.theme.palette.get("q1", scene.theme.accent))
    dcol = scene.color(dot_color, scene.theme.palette.get("point", col))
    xr, yr = scene.axes_ranges
    group = VGroup()
    dots = VGroup()
    for p in pieces:
        y = scene.eval(p["y"])
        if isinstance(p["x"], (list, tuple)):
            a, b = scene.eval(p["x"][0]), scene.eval(p["x"][1])
            a, b = max(a, xr[0]), min(b, xr[1])
            seg = _plot_pieces(scene, lambda x, y=y: y, [a, b], col, stroke_width, samples=20, smooth=False, steps=20)
            group.add(seg)
            opens = p.get("open", [True, True])
            for end, is_open, inside in ((a, opens[0], scene.eval(p["x"][0]) > xr[0]), (b, opens[1], scene.eval(p["x"][1]) < xr[1])):
                if not inside:
                    continue
                d = Dot(axes.c2p(end, y), radius=0.08, color=dcol).set_z_index(8)
                if is_open:
                    d.set_fill(scene.theme.background, opacity=1.0).set_stroke(dcol, width=3)
                dots.add(d)
        else:
            x = scene.eval(p["x"])
            dots.add(Dot(axes.c2p(x, y), radius=0.085, color=dcol).set_z_index(9))
    scene.register(id, group)
    scene.register(f"{id}_dots", dots)
    scene.play(Create(group), run_time=run_time)
    scene.play(FadeIn(dots), run_time=0.5)
