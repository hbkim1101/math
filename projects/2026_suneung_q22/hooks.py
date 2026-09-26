"""2026학년도 수능 수학 22번 전용 커스텀 애니메이션 (`custom` 액션에서 호출).

- swap_then_scale : 곡선(과 그 위의 점)을 직선 y=x 에 대칭이동한 뒤 원점 중심으로 factor 배 확대해
                    다른 곡선으로 옮겨 가는 과정을 보여준다. (x, y) → (y, x) → (factor·y, factor·x)
"""

from __future__ import annotations

from manim import (
    DL, DOWN, DR, LEFT, RIGHT, UL, UP, UR, Create, DashedLine, Dot, FadeIn, FadeOut, Line, ReplacementTransform,
    Transform, VGroup, rate_functions,
)

from explainer.render.actions import caption as caption_action


def swap_then_scale(scene, source: str, factor: float = 2.0, id: str = "img", color: str | None = None,
                    mid_color: str | None = None, t_range: list | None = None, run_time: float = 2.0,
                    points: list[dict] | None = None, swap_at=None, scale_at=None,
                    mid_label: str | None = None, label: str | None = None, label_at=None, label_dir="RIGHT",
                    label_scale: float = 0.7, caption_swap: str = "", caption_scale: str = "",
                    keep_mid: bool = False, show_diag: bool = True, **_):
    """source 곡선(plot id)을 y=x 대칭 → 원점 중심 factor 배 확대. points 는 곡선 위의 점(id, label) 목록."""
    f = scene.funcs[source]
    axes = scene.axes
    col = scene.color(color, scene.theme.palette.get("exp", scene.theme.highlight))
    mcol = scene.color(mid_color, scene.theme.muted)
    fac = float(scene.eval(factor))
    xr, yr = scene.axes_ranges
    t0, t1 = (scene.eval(t_range[0]), scene.eval(t_range[1])) if t_range else (xr[0], xr[1])

    def inside(x, y):
        return xr[0] <= x <= xr[1] and yr[0] <= y <= yr[1]

    # 대칭 곡선 (x,y)→(y,x), 확대 곡선 → (fac·y, fac·x). 화면 밖은 t 범위로 잘라낸다.
    def clip_range(fn):
        ts = [t0 + (t1 - t0) * i / 400 for i in range(401)]
        ok = [t for t in ts if inside(*fn(t))]
        return (min(ok), max(ok)) if ok else (t0, t1)

    swap_fn = lambda t: (f(t), t)
    scale_fn = lambda t: (fac * f(t), fac * t)
    s_lo, s_hi = clip_range(swap_fn)
    c_lo, c_hi = clip_range(scale_fn)
    src_mob = scene.get(source)
    # Axes.plot_parametric_curve 는 축 좌표 (x, y) 를 돌려주는 함수를 받아 스스로 c2p 를 적용한다
    swapped = axes.plot_parametric_curve(swap_fn, t_range=[s_lo, s_hi], color=mcol, stroke_width=3.2).set_z_index(3)
    scaled = axes.plot_parametric_curve(scale_fn, t_range=[c_lo, c_hi], color=col, stroke_width=3.6).set_z_index(3)
    diag = DashedLine(axes.c2p(max(xr[0], yr[0]), max(xr[0], yr[0])), axes.c2p(min(xr[1], yr[1]), min(xr[1], yr[1])),
                      color=scene.theme.palette.get("guide", mcol), stroke_width=2.0, dash_length=0.12).set_z_index(1)
    scene.register(f"{id}_diag", diag)

    # 점들: 원본 → 대칭점 → 확대점
    pts = points or []
    dots0, dots1, dots2, labs1, labs2, links = [], [], [], [], [], []
    pcol = scene.color(None, scene.theme.palette.get("point", col))
    for it in pts:
        x, y = scene.coords[it["id"]]
        d1 = Dot(axes.c2p(y, x), radius=0.075, color=mcol).set_z_index(8)
        d2 = Dot(axes.c2p(fac * y, fac * x), radius=0.08, color=col).set_z_index(8)
        dots0.append(scene.get(it["id"]))
        dots1.append(d1)
        dots2.append(d2)
        if it.get("mid_label"):
            labs1.append(scene.mtex(it["mid_label"], scale=0.7, plain=True, color=mid_color).next_to(d1, scene.direction(it.get("mid_dir", "DR")), buff=0.1).set_z_index(9))
        if it.get("label"):
            labs2.append(scene.mtex(it["label"], scale=0.7, plain=True, color=color).next_to(d2, scene.direction(it.get("label_dir", "UR")), buff=0.1).set_z_index(9))
        links.append(DashedLine(axes.c2p(x, y), axes.c2p(y, x), color=mcol, stroke_width=1.8, dash_length=0.08).set_z_index(1))
        links.append(DashedLine(axes.c2p(0, 0), axes.c2p(fac * y, fac * x), color=col, stroke_width=1.8, dash_length=0.08).set_z_index(1))

    # 1) y=x 와 대칭
    if swap_at is not None and scene.current_segment is not None:
        scene.wait_until(scene.current_segment.resolve_at(swap_at))
    if show_diag:
        scene.play(Create(diag), run_time=0.6)
    moving = src_mob.copy().set_color(mcol).set_z_index(3)
    scene.add(moving)
    anims = [Transform(moving, swapped, run_time=run_time * 0.55, rate_func=rate_functions.ease_in_out_sine)]
    for d0, d1 in zip(dots0, dots1):
        mv = d0.copy().set_color(mcol).set_z_index(8)
        scene.add(mv)
        anims.append(mv.animate(run_time=run_time * 0.55).move_to(d1.get_center()))
        d1._mv = mv
    if links:
        anims.append(Create(VGroup(*links[0::2]), run_time=run_time * 0.4))
    scene.play(*anims)
    for d1 in dots1:
        scene.remove(d1._mv)
        scene.add(d1)
    extra = [FadeIn(l) for l in labs1]
    if mid_label:
        ml = scene.mtex(mid_label, scale=label_scale, plain=True, color=mid_color)
        lx = scene.eval(label_at) if label_at is not None else (s_lo + s_hi) / 2
        ml.next_to(axes.c2p(*swap_fn(lx)), scene.direction(label_dir), buff=0.1).set_z_index(9)
        extra.append(FadeIn(ml))
        scene.register(f"{id}_mid_label", ml)
    if extra:
        scene.play(*extra, run_time=0.4)
    if caption_swap:
        caption_action(scene, text=caption_swap, run_time=0.4)
    scene.register(f"{id}_mid", moving)

    # 2) 원점 중심 factor 배 확대
    if scale_at is not None and scene.current_segment is not None:
        scene.wait_until(scene.current_segment.resolve_at(scale_at))
    grow = moving.copy()
    scene.add(grow)
    anims = [Transform(grow, scaled, run_time=run_time * 0.7, rate_func=rate_functions.ease_in_out_sine)]
    for d1, d2 in zip(dots1, dots2):
        mv = d1.copy().set_color(col).set_z_index(8)
        scene.add(mv)
        anims.append(mv.animate(run_time=run_time * 0.7).move_to(d2.get_center()))
        d2._mv = mv
    if links:
        anims.append(Create(VGroup(*links[1::2]), run_time=run_time * 0.6))
    if not keep_mid:
        anims.append(moving.animate(run_time=run_time * 0.7).set_stroke(opacity=0.35))
        for d1 in dots1:
            anims.append(d1.animate(run_time=run_time * 0.7).set_opacity(0.45))
    scene.play(*anims)
    for d2 in dots2:
        scene.remove(d2._mv)
        scene.add(d2)
    extra = [FadeIn(l) for l in labs2]
    if label:
        lb = scene.mtex(label, scale=label_scale, plain=True, color=color)
        lx = scene.eval(label_at) if label_at is not None else (c_lo + c_hi) / 2
        lb.next_to(axes.c2p(*scale_fn(lx)), scene.direction(label_dir), buff=0.1).set_z_index(9)
        extra.append(FadeIn(lb))
        scene.register(f"{id}_label", lb)
    if extra:
        scene.play(*extra, run_time=0.4)
    if caption_scale:
        caption_action(scene, text=caption_scale, run_time=0.4)
    scene.register(id, grow)
    for it, d2 in zip(pts, dots2):
        if it.get("out_id"):
            x, y = scene.coords[it["id"]]
            scene.register(it["out_id"], d2, (fac * y, fac * x))
    scene.register(f"{id}_links", VGroup(*links))
