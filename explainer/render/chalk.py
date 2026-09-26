"""칠판(강의) 스타일: 큰 칠판 캔버스 + 판서(Write) + 움직이는 카메라.

- 캔버스는 '섹션'들이 가로로 이어진 하나의 큰 칠판이다. 지우지 않고 계속 써 나가며 카메라가 따라간다.
- 각 섹션은 (선택) 왼쪽 그림 영역 + 오른쪽 판서 영역으로 나뉜다. 판서는 커서 위치에 손글씨 애니메이션으로 적힌다.
- 캡션처럼 화면에 고정되어야 하는 요소는 카메라 프레임에 핀(pin)한다.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, UL, ImageMobject, Line, Mobject, MovingCamera, Rectangle, TexTemplate,
    UpdateFromAlphaFunc, VGroup, VMobject, Write, config, rate_functions, smooth,
)
from PIL import Image

from .theme import Theme

CHALK_FONT = "NanumBarunpen"          # 한글 손글씨(펜) 폰트 — Pango Text 용
CHALK_TITLE_FONT = "Nanum Pen Script"  # 제목/캡션용 더 자유로운 손글씨

CHALK_KO_TEX_TEMPLATE = TexTemplate(
    tex_compiler="xelatex",
    output_format=".xdv",
    documentclass=r"\documentclass[preview]{standalone}",
    preamble=r"""
\usepackage{amsmath,amssymb,mathtools}
\usepackage{fontspec}
\usepackage{kotex}
\setmainhangulfont{NanumBarunpen}
\setsanshangulfont{NanumBarunpen}
\setlength{\parindent}{0pt}
% 한글 어절 중간에서 줄이 바뀌지 않게 (xetexko 기본은 글자 단위 줄바꿈 허용)
\XeTeXlinebreakpenalty=10000
\emergencystretch=3em
""",
)

BOARD_FRAME_COLOR = "#8a6a48"   # 칠판 테두리(나무)
BOARD_FRAME_INNER = "#c9b08a"


def chalk_theme(board_color: str = "#24493a") -> Theme:
    """분필 팔레트. 곡선/점 색은 실제 색분필(흰·노랑·하늘·분홍·연두·주황)에 맞춘다."""
    return Theme(
        background=board_color,
        text="#f3efe4",
        muted="#cfd8cf",
        axis="#d9e2d6",
        grid="#37634f",
        grid_faded="#2d5544",
        panel="#1d3b2f",
        panel_border="#6f8f7f",
        accent="#ffe38a",
        highlight="#ffe38a",
        palette={
            "exp": "#ffb98a",
            "log": "#9fd6ff",
            "q1": "#c6f79a",
            "q2": "#e2b8ff",
            "point": "#ffe38a",
            "rect": "#f3efe4",
            "axis_sym": "#ffa3d1",
            "guide": "#b9c7bd",
            "ok": "#b6f0c2",
            "warn": "#ffb3b3",
            "chalk": "#f3efe4",
        },
        font=CHALK_FONT,
        title_font=CHALK_TITLE_FONT,
        ko_template=CHALK_KO_TEX_TEMPLATE,
        chalk=True,
    )


# ---------------------------------------------------------------------- 질감 배경
def chalkboard_texture(cache_dir: Path, width_px: int, height_px: int, base_hex: str = "#24493a",
                       seed: int = 7) -> Path:
    """잡티·얼룩(분필 먼지)·비네팅이 있는 칠판 질감 PNG 를 만들어 캐시한다."""
    from PIL import ImageFilter

    key = hashlib.sha1(f"v2:{width_px}x{height_px}{base_hex}{seed}".encode()).hexdigest()[:10]
    path = cache_dir / f"chalkboard_{key}.png"
    if path.exists():
        return path
    cache_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    base = np.array([int(base_hex[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32)
    h, w = height_px, width_px

    def noise(cell: int, blur: float) -> np.ndarray:
        small = rng.normal(0, 1, (h // cell + 2, w // cell + 2)).astype(np.float32)
        small = (small - small.min()) / (np.ptp(small) + 1e-6)
        img = Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
        if blur > 0:
            img = img.filter(ImageFilter.GaussianBlur(blur))
        return np.asarray(img, dtype=np.float32) / 255.0

    blotch = noise(28, 8)          # 넓은 얼룩(지운 자국)
    smear = noise(9, 2)            # 중간 크기 분필 먼지
    grain = rng.normal(0, 1, (h, w)).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2, h / 2
    vign = 1.0 - 0.18 * (((xx - cx) / cx) ** 2 * 0.35 + ((yy - cy) / cy) ** 2) ** 1.1
    lum = (1.0 + 0.14 * (blotch - 0.5) + 0.07 * (smear - 0.5) + 0.03 * grain) * vign
    dust = np.clip(smear - 0.62, 0, 1) * 34.0     # 밝은 분필 먼지
    img = np.clip(base[None, None, :] * lum[:, :, None] + dust[:, :, None] + 5 * (blotch[:, :, None] - 0.5),
                  0, 255).astype(np.uint8)
    Image.fromarray(img, "RGB").save(path, optimize=True)
    return path


class ChalkCamera(MovingCamera):
    """축에 나란한 이미지(칠판 질감 타일)는 보이는 부분만 잘라 그린다.

    기본 구현은 이미지를 화면 좌표계 크기로 통째로 변환해 붙이므로, 카메라가 줌인해 타일이 화면보다 커지면
    프레임마다 수천 픽셀 크기의 변환을 수행하게 된다. 보이는 사각형만 잘라 리사이즈하면 항상 화면 크기 이하다.
    """

    def display_image_mobject(self, image_mobject, pixel_array):
        pts = self.points_to_subpixel_coords(image_mobject, image_mobject.points)
        if len(pts) != 4:
            return super().display_image_mobject(image_mobject, pixel_array)
        xs, ys = pts[:, 0], pts[:, 1]
        x0, x1, y0, y1 = float(xs.min()), float(xs.max()), float(ys.min()), float(ys.max())
        axis_aligned = (abs(pts[0][0] - x0) < 0.5 and abs(pts[0][1] - y0) < 0.5 and abs(pts[1][0] - x1) < 0.5
                        and abs(pts[2][1] - y1) < 0.5)
        if not axis_aligned or x1 - x0 < 1 or y1 - y0 < 1:
            return super().display_image_mobject(image_mobject, pixel_array)
        W, H = self.pixel_width, self.pixel_height
        vx0, vy0 = max(0.0, x0), max(0.0, y0)
        vx1, vy1 = min(float(W), x1), min(float(H), y1)
        if vx1 - vx0 < 1 or vy1 - vy0 < 1:
            return
        arr = image_mobject.get_pixel_array()
        ih, iw = arr.shape[:2]
        sx, sy = iw / (x1 - x0), ih / (y1 - y0)
        px0, py0, px1, py1 = int(vx0), int(vy0), int(math.ceil(vx1)), int(math.ceil(vy1))
        px1, py1 = min(px1, W), min(py1, H)
        crop = (
            int((px0 - x0) * sx), int((py0 - y0) * sy),
            min(iw, int(math.ceil((px1 - x0) * sx))), min(ih, int(math.ceil((py1 - y0) * sy))),
        )
        if crop[2] <= crop[0] or crop[3] <= crop[1]:
            return
        sub = Image.fromarray(arr, mode="RGBA").crop(crop).resize(
            (px1 - px0, py1 - py0), resample=image_mobject.resampling_algorithm)
        full = Image.new("RGBA", (W, H))
        full.paste(sub, (px0, py0))
        self.overlay_PIL_image(pixel_array, full)


# ---------------------------------------------------------------------- 캔버스 / 섹션
@dataclass
class Section:
    id: str
    title: str = ""
    layout: str = "split"     # split(그림+판서) | full(판서만)
    center_x: float = 0.0
    width: float = 14.2
    height: float = 8.0
    graph_width: float = 7.2
    notes_left: float = 0.0
    notes_width: float = 6.0
    notes_top: float = 3.0
    cursor_y: float = 3.0
    graph_center: tuple[float, float] = (0.0, 0.0)
    graph_height: float = 6.0
    lines: list[Mobject] = field(default_factory=list)
    title_mob: Optional[Mobject] = None
    visited: bool = False

    @property
    def left(self) -> float:
        return self.center_x - self.width / 2

    @property
    def right(self) -> float:
        return self.center_x + self.width / 2

    @property
    def top(self) -> float:
        return self.height / 2

    @property
    def bottom(self) -> float:
        return -self.height / 2

    @property
    def center(self) -> np.ndarray:
        return np.array([self.center_x, 0.0, 0.0])

    @property
    def notes_center_x(self) -> float:
        return self.notes_left + self.notes_width / 2


class Canvas:
    """섹션이 가로로 이어진 큰 칠판. 커서(판서 위치)와 카메라 목표를 관리한다."""

    PX_PER_UNIT = 100
    BOARD_OVERHANG = 0.3   # 섹션 뷰에서 칠판 가장자리가 보이지 않게 위아래로 조금 더 크게

    def __init__(self, scene, layout, title_height: float = 1.0):
        self.scene = scene
        self.layout = layout
        self.width = float(layout.section_width)
        self.height = float(layout.section_height)
        self.gap = float(layout.gap)
        self.margin = float(layout.margin)
        self.title_height = title_height
        self.line_gap = float(layout.line_gap)
        self.sections: list[Section] = []
        self.by_id: dict[str, Section] = {}
        self.current: Optional[Section] = None
        specs = layout.sections or [{"id": "main", "layout": "split"}]
        for i, spec in enumerate(specs):
            sec = Section(id=spec["id"], title=spec.get("title", ""), layout=spec.get("layout", "split"),
                          center_x=i * (self.width + self.gap), width=self.width, height=self.height,
                          graph_width=float(spec.get("graph_width", layout.graph_width)))
            top = self.height / 2 - self.margin - (title_height if sec.title else 0.0)
            sec.notes_top = top
            sec.cursor_y = top
            sec.graph_height = top - (sec.bottom + self.margin + 0.2)
            if sec.layout == "split":
                sec.graph_center = (sec.left + self.margin + sec.graph_width / 2, (top + sec.bottom + self.margin) / 2 - 0.1)
                sec.notes_left = sec.left + self.margin + sec.graph_width + 0.55
                sec.notes_width = sec.right - self.margin - sec.notes_left
            else:
                sec.graph_center = (sec.center_x, (top + sec.bottom + self.margin) / 2 - 0.1)
                sec.notes_left = sec.left + self.margin
                sec.notes_width = self.width - 2 * self.margin
            self.sections.append(sec)
            self.by_id[sec.id] = sec
        self.background = VGroup()

    # ------------------------------------------------------------------ 전체 칠판 범위
    @property
    def total_left(self) -> float:
        return self.sections[0].left - self.gap / 2

    @property
    def total_right(self) -> float:
        return self.sections[-1].right + self.gap / 2

    @property
    def total_center(self) -> np.ndarray:
        return np.array([(self.total_left + self.total_right) / 2, 0.0, 0.0])

    @property
    def total_width(self) -> float:
        return self.total_right - self.total_left

    @property
    def board_height(self) -> float:
        return self.height + 2 * self.BOARD_OVERHANG

    def section(self, sid: Optional[str] = None) -> Section:
        if sid is None:
            assert self.current is not None, "goto 액션으로 섹션을 먼저 선택해야 합니다"
            return self.current
        if sid not in self.by_id:
            raise KeyError(f"알 수 없는 섹션: {sid} (사용 가능: {list(self.by_id)})")
        return self.by_id[sid]

    # ------------------------------------------------------------------ 배경(칠판)
    def build_background(self, cache_dir: Path, texture: bool = True) -> None:
        """칠판 바탕색 + (선택) 질감 타일 + 나무 테두리를 씬에 추가한다."""
        base = Rectangle(width=self.total_width, height=self.board_height, fill_color=self.layout.board_color,
                         fill_opacity=1.0, stroke_width=0).move_to(self.total_center).set_z_index(-12)
        parts: list[Mobject] = [base]
        if texture:
            tile_units = self.width + self.gap
            px_w = int(round(self.total_width * self.PX_PER_UNIT))
            px_h = int(round(self.board_height * self.PX_PER_UNIT))
            big = chalkboard_texture(cache_dir, px_w, px_h, self.layout.board_color)
            img = Image.open(big)
            for i, sec in enumerate(self.sections):
                x_a = int(round(i * tile_units * self.PX_PER_UNIT))
                x_b = int(round((i + 1) * tile_units * self.PX_PER_UNIT)) if i < len(self.sections) - 1 else px_w
                tile_path = cache_dir / f"{big.stem}_tile{i}.png"
                if not tile_path.exists():
                    img.crop((x_a, 0, x_b, px_h)).save(tile_path, optimize=True)
                tile = ImageMobject(str(tile_path))
                tile.height = self.board_height
                tile.stretch_to_fit_width((x_b - x_a) / self.PX_PER_UNIT)
                tile.move_to(np.array([self.total_left + (x_a + x_b) / 2 / self.PX_PER_UNIT, 0.0, 0.0]))
                tile.set_z_index(-11)
                parts.append(tile)
        frame_outer = Rectangle(width=self.total_width + 0.36, height=self.board_height + 0.36,
                                stroke_color=BOARD_FRAME_COLOR, stroke_width=14, fill_opacity=0)
        frame_inner = Rectangle(width=self.total_width + 0.06, height=self.board_height + 0.06,
                                stroke_color=BOARD_FRAME_INNER, stroke_width=2, fill_opacity=0)
        for fr in (frame_outer, frame_inner):
            fr.move_to(self.total_center).set_z_index(-10)
            parts.append(fr)
        self.background = VGroup()  # ImageMobject 는 VGroup 에 못 넣으므로 목록만 유지
        self.background_parts = parts
        self.scene.add(*parts)

    # ------------------------------------------------------------------ 판서 커서
    def place_line(self, mob: Mobject, indent: float = 0.0, sec: Optional[Section] = None,
                   space: float = 0.0) -> Section:
        """판서 커서 위치에 mob 의 왼쪽 위를 맞추고 커서를 내린다."""
        sec = sec or self.section()
        if space:
            sec.cursor_y -= space
        max_w = sec.notes_width - indent
        if mob.width > max_w:
            mob.scale_to_fit_width(max_w)
        mob.move_to(np.array([sec.notes_left + indent, sec.cursor_y, 0.0]), aligned_edge=UL)
        if mob.get_bottom()[1] < sec.bottom + self.margin * 0.5:
            print(f"  [chalk] 경고: 섹션 '{sec.id}' 판서가 아래로 넘칩니다 (cursor_y={sec.cursor_y:.2f})")
        sec.cursor_y -= mob.height + self.line_gap
        sec.lines.append(mob)
        return sec

    def advance(self, dy: float, sec: Optional[Section] = None) -> None:
        sec = sec or self.section()
        sec.cursor_y -= dy

    # ------------------------------------------------------------------ 카메라
    @property
    def frame(self):
        return self.scene.camera.frame

    def view_of(self, sec: Section) -> tuple[np.ndarray, float]:
        return sec.center, sec.width

    def snap_to(self, sec: Section) -> None:
        c, w = self.view_of(sec)
        self.frame.set(width=w).move_to(c)
        self.current = sec

    def fly_to(self, center, width: float, run_time: float = 1.6, overview: bool = True,
               overview_width: Optional[float] = None) -> None:
        """현재 뷰 → (center, width) 로 카메라를 날린다. overview 면 중간에 살짝 줌아웃해 전체 흐름을 보여준다."""
        frame = self.frame
        c0, w0 = frame.get_center().copy(), float(frame.width)
        c1 = np.array([float(center[0]), float(center[1]), 0.0])
        w1 = float(width)
        if np.allclose(c0, c1, atol=1e-3) and abs(w0 - w1) < 1e-3:
            return
        dist = float(np.linalg.norm(c1 - c0))
        if overview and dist > 0.5 * max(w0, w1):
            # 두 뷰를 모두 담는 폭(여백 포함)까지 줌아웃 — 단, 너무 넓어지지 않게 제한
            span = abs(c1[0] - c0[0]) + (w0 + w1) / 2 + 1.0
            peak_w = min(overview_width or span, self.total_width + 1.2)
        else:
            peak_w = max(w0, w1)
        bump = max(0.0, peak_w - max(w0, w1))

        def upd(m, a):
            s = smooth(a)
            w = w0 + (w1 - w0) * s + bump * 4 * s * (1 - s)
            m.set(width=w)
            m.move_to(c0 + (c1 - c0) * s)

        self.scene.play(UpdateFromAlphaFunc(frame, upd), run_time=run_time)

    def goto(self, sid: str, run_time: float = 1.8, overview: bool = True, write_title: bool = True,
             title_run_time: float = 0.9) -> Section:
        sec = self.section(sid)
        if self.current is None:
            self.snap_to(sec)
        else:
            c, w = self.view_of(sec)
            self.fly_to(c, w, run_time=run_time, overview=overview)
            self.current = sec
        if write_title and sec.title and sec.title_mob is None:
            self.write_title(sec, run_time=title_run_time)
        sec.visited = True
        return sec

    def write_title(self, sec: Section, run_time: float = 0.9) -> None:
        scene = self.scene
        title = scene.ktext(sec.title, size=40, color=scene.theme.accent, font=scene.theme.title_font)
        title.move_to(np.array([sec.left + self.margin, sec.top - self.margin, 0.0]), aligned_edge=UL)
        under = Line(title.get_corner(DOWN + LEFT) + DOWN * 0.08, title.get_corner(DOWN + RIGHT) + DOWN * 0.08,
                     stroke_color=scene.theme.accent, stroke_width=2.5)
        sec.title_mob = VGroup(title, under)
        scene.register(f"{sec.id}_title", sec.title_mob)
        scene.play(handwrite(title, run_time=run_time * 0.75))
        scene.play(handwrite(under, run_time=run_time * 0.25))

    def focus(self, center, width: float, run_time: float = 1.2) -> None:
        self.fly_to(center, width, run_time=run_time, overview=False)

    def reset_view(self, run_time: float = 1.2) -> None:
        sec = self.section()
        c, w = self.view_of(sec)
        self.fly_to(c, w, run_time=run_time, overview=False)


# ---------------------------------------------------------------------- 판서 애니메이션
def chalkify(mob: Mobject, stroke_width: float = 0.9, opacity: float = 0.96) -> Mobject:
    """글자에 얇은 외곽선을 더해 분필로 쓴 듯한 질감을 준다."""
    for sm in mob.family_members_with_points():
        if isinstance(sm, VMobject) and sm.get_fill_opacity() > 0 and sm.get_stroke_width() == 0:
            sm.set_stroke(color=sm.get_fill_color(), width=stroke_width, opacity=0.75)
            sm.set_fill(opacity=opacity)
    return mob


def handwrite_time(mob: Mobject, per_glyph: float = 0.05, lo: float = 0.6, hi: float = 3.4) -> float:
    n = len(list(mob.family_members_with_points()))
    return float(min(hi, max(lo, n * per_glyph)))


def handwrite(mob: Mobject, run_time: Optional[float] = None) -> Write:
    """손으로 쓰는 속도로 Write. run_time 이 없으면 글자 수에 비례."""
    rt = run_time if run_time is not None else handwrite_time(mob)
    return Write(mob, run_time=rt, rate_func=rate_functions.linear)


# ---------------------------------------------------------------------- 프레임 고정 요소
def pin_to_frame(scene, mob: Mobject, anchor=DOWN, buff: float = 1.4, x_offset: float = 0.0) -> Mobject:
    """카메라가 움직여도 mob 이 화면의 같은 자리·같은 크기로 보이도록 업데이터를 붙인다."""
    frame = scene.camera.frame
    ref_w = float(config.frame_width)
    mob._pin_scale = 1.0

    def _upd(m):
        w, h = frame.width, frame.height
        c = frame.get_center()
        scale = w / ref_w
        # 폭을 직접 재지 않고 적용된 배율만 추적한다 (Write 도중 폭이 변해도 크기가 흔들리지 않게)
        if abs(scale - m._pin_scale) > 1e-4:
            m.scale(scale / m._pin_scale)
            m._pin_scale = scale
        if np.allclose(anchor, DOWN):
            m.move_to(c + DOWN * (h / 2 - buff * scale - m.height / 2) + RIGHT * x_offset * scale)
        elif np.allclose(anchor, UP):
            m.move_to(c + UP * (h / 2 - buff * scale - m.height / 2) + RIGHT * x_offset * scale)
        else:
            m.move_to(c)

    mob.add_updater(_upd)
    _upd(mob)
    return mob
