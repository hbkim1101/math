"""문제(좌상단) / 해설(나머지) 영역 레이아웃 설정."""

from manim import *
import numpy as np

# Manim 기본 프레임: 가로 14.22, 세로 8 (16:9)
FRAME_W = config.frame_width
FRAME_H = config.frame_height
MARGIN = 0.35  # 화면 가장자리 여백


class LayoutRegions:
    """화면을 '문제' / '해설' 두 영역으로 나눈 좌표 정보."""

    # ---------- 문제 영역 (왼쪽 위) ----------
    PROBLEM_W = 5.8
    PROBLEM_H = 3.4

    # 좌상단(UL) 기준으로 문제 박스 중심 좌표 계산
    problem_center = (
        -FRAME_W / 2 + MARGIN + PROBLEM_W / 2,
        FRAME_H / 2 - MARGIN - PROBLEM_H / 2,
        0,
    )

    # ---------- 해설 영역 (나머지 = 우측 + 좌하단) ----------
    # 우측 패널: 문제 오른쪽 ~ 화면 끝, 전체 높이
    EXPLAIN_RIGHT_W = FRAME_W - MARGIN * 2 - PROBLEM_W - 0.15
    EXPLAIN_RIGHT_H = FRAME_H - MARGIN * 2

    explain_right_center = (
        problem_center[0] + PROBLEM_W / 2 + 0.15 + EXPLAIN_RIGHT_W / 2,
        0,
        0,
    )

    # 좌하단 패널: 문제 아래 ~ 화면 아래, 문제와 같은 너비
    EXPLAIN_BOTTOM_H = FRAME_H - MARGIN * 2 - PROBLEM_H - 0.15

    explain_bottom_center = (
        problem_center[0],
        problem_center[1] - PROBLEM_H / 2 - 0.15 - EXPLAIN_BOTTOM_H / 2,
        0,
    )


def make_chalkboard_background(scene, seed=4, count=34, opacity=0.09):
    """칠판 느낌 배경: 짙은 남색 + 희미한 수식 텍스처."""
    scene.camera.background_color = "#0A1630"

    bg_texts = VGroup()
    snippets = [
        r"\int_a^b f(x)\,dx", r"\sum_{n=1}^{\infty}", r"\frac{a}{b}",
        r"\Delta x", r"\sin x", r"\cos x", r"f'(x)", r"x^2+y^2",
        r"\lim_{x\to a}", r"\sqrt{x}", r"\nabla f", r"\log x",
    ]
    rng = np.random.default_rng(seed)

    for _ in range(count):
        tex = MathTex(rng.choice(snippets), color=BLUE_E)
        tex.set_opacity(opacity)
        tex.scale(rng.uniform(0.55, 1.05))
        tex.rotate(rng.uniform(-0.35, 0.35))
        tex.move_to([
            rng.uniform(-6.8, 6.8),
            rng.uniform(-3.7, 3.7),
            0,
        ])
        bg_texts.add(tex)

    return bg_texts


def make_region_guides(show_labels=True):
    """문제/해설 영역 구분선과 라벨을 그려서 레이아웃을 눈으로 확인."""
    r = LayoutRegions

    problem_box = RoundedRectangle(
        width=r.PROBLEM_W,
        height=r.PROBLEM_H,
        corner_radius=0.12,
        color=TEAL_A,
        stroke_width=2,
        fill_color=TEAL_E,
        fill_opacity=0.08,
    ).move_to(r.problem_center)

    explain_right_box = RoundedRectangle(
        width=r.EXPLAIN_RIGHT_W,
        height=r.EXPLAIN_RIGHT_H,
        corner_radius=0.12,
        color=YELLOW_E,
        stroke_width=2,
        fill_color=YELLOW_E,
        fill_opacity=0.05,
    ).move_to(r.explain_right_center)

    explain_bottom_box = RoundedRectangle(
        width=r.PROBLEM_W,
        height=r.EXPLAIN_BOTTOM_H,
        corner_radius=0.12,
        color=YELLOW_E,
        stroke_width=2,
        fill_color=YELLOW_E,
        fill_opacity=0.05,
    ).move_to(r.explain_bottom_center)

    guides = VGroup(problem_box, explain_right_box, explain_bottom_box)

    if show_labels:
        problem_label = Text("문제", font_size=28, color=TEAL_A, weight=BOLD)
        problem_label.move_to(problem_box.get_top() + DOWN * 0.35)

        explain_label = Text("해설", font_size=28, color=YELLOW_E, weight=BOLD)
        explain_label.move_to(explain_right_box.get_top() + DOWN * 0.35)

        guides.add(problem_label, explain_label)

    return guides


def place_in_problem(mobject, buff=0.45):
    """객체를 문제 영역 안에 배치."""
    box = RoundedRectangle(
        width=LayoutRegions.PROBLEM_W,
        height=LayoutRegions.PROBLEM_H,
        corner_radius=0.12,
    ).move_to(LayoutRegions.problem_center)
    mobject.move_to(box.get_center())
    mobject.set_max_width(box.width - buff * 2)
    mobject.set_max_height(box.height - buff * 2)
    return mobject


def place_in_explain_right(mobject, buff=0.45):
    """객체를 우측 해설 영역 안에 배치."""
    box = RoundedRectangle(
        width=LayoutRegions.EXPLAIN_RIGHT_W,
        height=LayoutRegions.EXPLAIN_RIGHT_H,
        corner_radius=0.12,
    ).move_to(LayoutRegions.explain_right_center)
    mobject.move_to(box.get_center())
    mobject.set_max_width(box.width - buff * 2)
    mobject.set_max_height(box.height - buff * 2)
    return mobject


def place_in_explain_bottom(mobject, buff=0.45):
    """객체를 좌하단 해설 영역 안에 배치."""
    box = RoundedRectangle(
        width=LayoutRegions.PROBLEM_W,
        height=LayoutRegions.EXPLAIN_BOTTOM_H,
        corner_radius=0.12,
    ).move_to(LayoutRegions.explain_bottom_center)
    mobject.move_to(box.get_center())
    mobject.set_max_width(box.width - buff * 2)
    mobject.set_max_height(box.height - buff * 2)
    return mobject
