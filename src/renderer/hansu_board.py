"""Math Hansu-style narration + TTS sync helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from manim import *

from src.config import HIGHLIGHT_COLOR, KOREAN_FONT, TITLE_COLOR

ROOT = Path(__file__).resolve().parents[2]
NARRATION_DIR = ROOT / "assets" / "narration" / "q28_june"


def audio_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


class HansuPresenter:
    """하단 자막 + TTS 음성 동기화."""

    def __init__(self, scene: Scene, narration_dir: Path = NARRATION_DIR) -> None:
        self.scene = scene
        self.narration_dir = narration_dir
        self._subtitle: Mobject | None = None
        self._segment = 0

    def speak(self, text: str, segment: int | None = None) -> None:
        """자막 표시 + 해당 segment mp3 재생."""
        if segment is None:
            segment = self._segment
            self._segment += 1

        audio = self.narration_dir / f"{segment:02d}.mp3"
        sub = Text(text, font=KOREAN_FONT, font_size=22, color=WHITE, line_spacing=1.2)
        if sub.width > 13.5:
            sub.scale(13.5 / sub.width)
        sub.to_edge(DOWN, buff=0.45)

        if self._subtitle is not None:
            self.scene.play(
                FadeOut(self._subtitle, shift=DOWN * 0.08),
                FadeIn(sub, shift=UP * 0.08),
                run_time=0.35,
            )
        else:
            self.scene.play(FadeIn(sub, shift=UP * 0.08), run_time=0.35)
        self._subtitle = sub

        if audio.exists():
            dur = audio_duration(audio)
            self.scene.add_sound(str(audio))
            self.scene.wait(max(dur - 0.35, 0.5))
        else:
            # fallback: 읽기 속도 추정
            self.scene.wait(max(len(text) * 0.08, 2.0))

    def section_title(self, title: str, subtitle: str = "") -> VGroup:
        parts = [Text(title, font=KOREAN_FONT, font_size=28, color=TITLE_COLOR)]
        if subtitle:
            parts.append(Text(subtitle, font=KOREAN_FONT, font_size=20, color=GRAY_B))
        grp = VGroup(*parts).arrange(DOWN, buff=0.08).to_edge(UP, buff=0.25)
        self.scene.play(FadeIn(grp), run_time=0.5)
        return grp

    def clear_subtitle(self) -> None:
        if self._subtitle:
            self.scene.play(FadeOut(self._subtitle), run_time=0.3)
            self._subtitle = None

    def write_eq(self, latex: str, pos: np.ndarray = ORIGIN, fs: int = 32, color=WHITE) -> MathTex:
        eq = MathTex(latex, font_size=fs, color=color).move_to(pos)
        self.scene.play(Write(eq), run_time=1.2)
        return eq
