"""세그먼트별 내레이션을 합성하고 타임라인(각 세그먼트의 오디오/문장 타이밍)을 구성한다."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from ..script.models import Project, Segment
from .tts import NarrationClip, synthesize_segment


@dataclass
class SegmentTiming:
    id: str
    narration: str
    clip: Optional[NarrationClip]
    pad: float
    # 렌더 후 채워지는 실제 시각(초)
    start: float = 0.0
    end: float = 0.0

    @property
    def audio_duration(self) -> float:
        return self.clip.duration if self.clip else 0.0

    def resolve_at(self, at) -> float:
        """액션의 `at` 값을 초 단위로 변환. 숫자 또는 "s<N>" (N번째 문장 시작, 1-based)."""
        if at is None:
            return 0.0
        if isinstance(at, (int, float)):
            return float(at)
        s = str(at).strip().lower()
        if s.startswith("s") and s[1:].isdigit():
            if self.clip is None:
                return 0.0
            return self.clip.sentence_start(int(s[1:]))
        if s.startswith("+") or s.replace(".", "", 1).isdigit():
            return float(s)
        raise ValueError(f"해석할 수 없는 at 값: {at!r}")


@dataclass
class Timeline:
    segments: list[SegmentTiming] = field(default_factory=list)

    def by_id(self, seg_id: str) -> SegmentTiming:
        for s in self.segments:
            if s.id == seg_id:
                return s
        raise KeyError(seg_id)

    @property
    def total_audio(self) -> float:
        return sum(s.audio_duration + s.pad for s in self.segments)

    def to_json(self) -> dict:
        return {
            "segments": [
                {
                    "id": s.id,
                    "narration": s.narration,
                    "pad": s.pad,
                    "start": s.start,
                    "end": s.end,
                    "audio_duration": s.audio_duration,
                    "audio_path": s.clip.audio_path if s.clip else None,
                    "sentences": [asdict(x) for x in (s.clip.sentences if s.clip else [])],
                }
                for s in self.segments
            ]
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_json(), ensure_ascii=False, indent=1), encoding="utf-8")


def build_timeline(project: Project, cache_dir: str | Path = "cache/tts", force: bool = False,
                   log=print) -> Timeline:
    tl = Timeline()
    for seg in project.segments:
        clip = None
        if seg.narration:
            clip = synthesize_segment(
                seg.narration,
                voice=seg.voice or project.meta.voice,
                rate=seg.rate or project.meta.rate,
                pitch=project.meta.pitch,
                cache_dir=cache_dir,
                force=force,
            )
            if log:
                log(f"  [tts] {seg.id:<18} {clip.duration:6.2f}s  ({len(clip.sentences)} 문장)")
        tl.segments.append(
            SegmentTiming(
                id=seg.id,
                narration=seg.narration,
                clip=clip,
                pad=project.meta.segment_pad if seg.pad is None else seg.pad,
            )
        )
    return tl
