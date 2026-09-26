"""Manim 씬: 타임라인의 세그먼트를 순서대로 실행하며 내레이션 오디오를 삽입한다."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, UL, UR, DL, DR, ORIGIN,
    Axes, Dot, MathTex, Mobject, MovingCameraScene, NumberPlane, Tex, Text, VGroup, config, tempconfig,
)

from ..narration.timeline import SegmentTiming, Timeline
from ..script.loader import make_function, resolve_params, safe_eval
from ..script.models import Project
from .board import Board
from .chalk import Canvas, ChalkCamera, chalk_theme, chalkify
from .theme import MATH_TEX_TEMPLATE, Theme

DIRECTIONS = {
    "UP": UP, "DOWN": DOWN, "LEFT": LEFT, "RIGHT": RIGHT,
    "UL": UL, "UR": UR, "DL": DL, "DR": DR,
    "U": UP, "D": DOWN, "L": LEFT, "R": RIGHT,
}

RESOLUTIONS = {
    "480p": (854, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "2160p": (3840, 2160),
}


class ExplainerScene(MovingCameraScene):
    """프로젝트 + 타임라인을 받아 영상을 구성하는 범용 씬.

    style=panel 이면 카메라는 고정되어 있고, style=chalkboard 면 큰 칠판 캔버스 위를 카메라가 옮겨 다닌다.
    """

    project: Project
    timeline: Timeline

    def __init__(self, project: Project, timeline: Timeline, theme: Optional[Theme] = None,
                 hooks: Optional[dict[str, Callable]] = None, cache_dir: Optional[Path] = None, **kwargs):
        self.project = project
        self.timeline = timeline
        self.is_chalk = project.meta.style == "chalkboard"
        if theme is not None:
            self.theme = theme
        elif self.is_chalk:
            self.theme = chalk_theme(project.layout.chalk.board_color)
        else:
            self.theme = Theme(background=project.meta.background)
        self.hooks = hooks or {}
        self.cache_dir = Path(cache_dir) if cache_dir else Path(".cache")
        self.params: dict[str, float] = resolve_params(project.params)
        self.objs: dict[str, Mobject] = {}
        self.coords: dict[str, tuple[float, float]] = {}
        self.funcs: dict[str, Callable[[float], float]] = {}
        self.axes: Optional[Axes] = None
        self.board: Optional[Board] = None
        self.chalk: Optional[Canvas] = None
        self.caption: Optional[Mobject] = None
        self.derivations: dict[str, Any] = {}
        self.current_segment: Optional[SegmentTiming] = None
        self._segment_start = 0.0
        self.log: list[dict[str, Any]] = []
        kwargs.setdefault("camera_class", ChalkCamera)
        super().__init__(**kwargs)

    # ------------------------------------------------------------------ 시간
    @property
    def now(self) -> float:
        return float(self.renderer.time)

    def wait_until(self, t_rel: float) -> None:
        """세그먼트 시작 기준 t_rel 초가 될 때까지 대기."""
        target = self._segment_start + t_rel
        dt = target - self.now
        if dt > 1.0 / config.frame_rate:
            self.wait(dt)

    # ------------------------------------------------------------------ 실행 루프
    def construct(self) -> None:
        from .actions import run_action

        meta = self.project.meta
        self.camera.background_color = meta.background
        if self.is_chalk:
            lay = self.project.layout.chalk
            self.chalk = Canvas(self, lay)
            self.chalk.build_background(self.cache_dir / "chalk", texture=lay.texture)
            # 첫 섹션을 바로 보여준다 (goto 액션이 나오기 전이라도 카메라가 칠판 위에 있어야 한다)
            self.chalk.goto(self.chalk.sections[0].id, write_title=False)
        if meta.intro_silence > 0:
            self.wait(meta.intro_silence)

        for seg_model, seg in zip(self.project.segments, self.timeline.segments):
            self.current_segment = seg
            self._segment_start = self.now
            seg.start = self.now
            if seg.clip is not None:
                # Scene.add_sound 는 직전 애니메이션이 캐시에서 재사용되면(skip_animations=True) 소리를 버린다.
                # 파일 라이터에 직접 넣어 캐시 여부와 무관하게 항상 삽입되도록 한다.
                self.renderer.file_writer.add_sound(seg.clip.audio_path, self.now)

            for action in seg_model.actions:
                if action.at is not None:
                    self.wait_until(seg.resolve_at(action.at))
                t0 = self.now
                run_action(self, action)
                self.log.append({"segment": seg.id, "action": action.do, "start": t0, "end": self.now})

            # 내레이션이 끝날 때까지(+여백) 대기
            end_rel = seg.audio_duration + seg.pad
            self.wait_until(end_rel)
            seg.end = self.now

        if meta.outro_silence > 0:
            self.wait(meta.outro_silence)

    # ------------------------------------------------------------------ 헬퍼
    def color(self, name: str | None, default: str | None = None) -> str | None:
        c = self.project.resolve_color(name)
        return self.theme.color(c, default)

    def eval(self, expr) -> float:
        return float(safe_eval(expr, self.params))

    def func(self, expr: str) -> Callable[[float], float]:
        # 앞서 plot/line 으로 등록된 함수 id 를 식 안에서 호출할 수 있다 (예: "7*f(x)"); params 가 우선
        return make_function(expr, {**self.funcs, **self.params})

    def resolve_coord(self, spec) -> tuple[float, float]:
        """좌표 스펙 → (x, y). 숫자 쌍, 표현식 쌍, 점 id, {on: f, x: ...} 를 지원."""
        if isinstance(spec, str):
            if spec in self.coords:
                return self.coords[spec]
            raise KeyError(f"알 수 없는 점 id: {spec}")
        if isinstance(spec, dict):
            fid = spec["on"]
            x = self.eval(spec["x"])
            f = self.funcs[fid]
            return (x, f(x))
        x, y = spec
        return (self.eval(x), self.eval(y))

    def c2p(self, x: float, y: float) -> np.ndarray:
        assert self.axes is not None, "axes 액션이 먼저 실행되어야 합니다"
        return self.axes.c2p(x, y)

    def direction(self, name) -> np.ndarray:
        if name is None:
            return UR
        if isinstance(name, (list, tuple)):
            return np.array([float(name[0]), float(name[1]), 0.0])
        return DIRECTIONS[str(name).upper()]

    def t2c_map(self, extra: dict | None = None) -> dict[str, str]:
        out = {k: self.color(v) for k, v in self.project.t2c.items()}
        if extra:
            out.update({k: self.color(v) for k, v in extra.items()})
        return out

    def mtex(self, tex: str, color: str | None = None, scale: float = 1.0,
             t2c: dict | None = None, plain: bool = False) -> MathTex:
        kwargs: dict[str, Any] = {"tex_template": MATH_TEX_TEMPLATE}
        if not plain:
            kwargs["tex_to_color_map"] = self.t2c_map(t2c)
        m = MathTex(tex, **kwargs)
        if color:
            m.set_color(self.color(color))
        return self.finish_text(m.scale(scale))

    # 실측: \parbox{10cm} → 약 14.1 Manim 단위 (scale 1 기준)
    CM_PER_UNIT = 10.0 / 14.1

    def ktex(self, tex: str, color: str | None = None, scale: float = 1.0, width: float | None = None) -> Tex:
        """한글+수식 혼합 문장(xelatex). width 는 최종 표시 폭(Manim 단위)이며 자동 줄바꿈된다."""
        if width is not None:
            cm = width / scale * self.CM_PER_UNIT
            # raggedright: 줄이 바뀌어도 단어 사이가 늘어나지 않는다 (판서 느낌, 가독성)
            body = rf"\parbox{{{cm:.2f}cm}}{{\raggedright\setlength{{\baselineskip}}{{1.35\baselineskip}}{tex}}}"
        else:
            body = tex
        m = Tex(body, tex_template=self.theme.ko_template)
        m.set_color(self.color(color, self.theme.text))
        return self.finish_text(m.scale(scale))

    def ktext(self, text: str, size: int = 30, color: str | None = None, weight: str = "NORMAL",
              font: str | None = None) -> Text:
        m = Text(text, font=font or self.theme.font, font_size=size, weight=weight,
                 color=self.color(color, self.theme.text))
        return self.finish_text(m)

    def finish_text(self, mob: Mobject) -> Mobject:
        """테마별 후처리: 칠판 테마는 글자에 분필 질감(얇은 외곽선)을 준다."""
        if self.theme.chalk:
            chalkify(mob)
        return mob

    def bg_rect(self, mob: Mobject, opacity: float = 0.75, buff: float = 0.05) -> Mobject:
        """라벨 뒤의 가림 사각형. 칠판 테마에서는 질감 위에 평면 사각형이 보이므로 넣지 않는다."""
        if not self.theme.chalk:
            mob.add_background_rectangle(color=self.theme.background, opacity=opacity, buff=buff)
        return mob

    @property
    def view_center(self) -> np.ndarray:
        """현재 카메라가 보는 중심 (panel 스타일은 원점)."""
        return self.camera.frame.get_center().copy()

    def register(self, oid: str | None, mob: Mobject, coord: tuple[float, float] | None = None) -> None:
        if oid:
            self.objs[oid] = mob
            if coord is not None:
                self.coords[oid] = coord

    def get(self, oid: str) -> Mobject:
        if oid not in self.objs:
            raise KeyError(f"알 수 없는 객체 id: {oid}")
        return self.objs[oid]

    def clipped_pieces(self, f: Callable[[float], float], x_range: tuple[float, float],
                       y_range: tuple[float, float], samples: int = 600, margin: float = 0.02
                       ) -> list[tuple[float, float]]:
        """f 의 그래프 중 y 범위 안에 들어오는 연속 구간들의 x 구간을 돌려준다."""
        xs = np.linspace(x_range[0], x_range[1], samples)
        ylo, yhi = y_range[0] - margin, y_range[1] + margin
        pieces: list[tuple[float, float]] = []
        start = None
        for i, x in enumerate(xs):
            try:
                y = f(float(x))
                ok = math.isfinite(y) and ylo <= y <= yhi
            except (ValueError, ZeroDivisionError, OverflowError):
                ok = False
            if ok and start is None:
                start = float(x)
            if (not ok or i == len(xs) - 1) and start is not None:
                end = float(x) if ok else float(xs[i - 1])
                if end > start:
                    pieces.append((start, end))
                start = None
        return pieces


def render_project(project: Project, timeline: Timeline, out_dir: str | Path, preview: bool = False,
                   hooks: Optional[dict[str, Callable]] = None, log=print) -> Path:
    """Manim 으로 렌더링하고 결과 mp4 경로를 돌려준다. 타임라인에 실제 세그먼트 시각을 기록한다."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    media_dir = out_dir / "media"
    w, h = RESOLUTIONS["480p"] if preview else RESOLUTIONS[project.meta.resolution]
    fps = 15 if preview else project.meta.fps
    scene_name = f"{project.meta.id}{'_preview' if preview else ''}"

    with tempconfig(
        {
            "pixel_width": w,
            "pixel_height": h,
            "frame_rate": fps,
            "media_dir": str(media_dir),
            "output_file": scene_name,
            "background_color": project.meta.background,
            "disable_caching": False,
            "verbosity": "WARNING",
            "progress_bar": "none",
            "write_to_movie": True,
        }
    ):
        scene = ExplainerScene(project, timeline, hooks=hooks, cache_dir=media_dir / "cache")
        scene.render()
        movie = Path(scene.renderer.file_writer.movie_file_path)

    (out_dir / "actions_log.json").write_text(json.dumps(scene.log, ensure_ascii=False, indent=1), encoding="utf-8")
    if log:
        log(f"  [render] {movie}  ({movie.stat().st_size / 1e6:.1f} MB)")
    return movie
