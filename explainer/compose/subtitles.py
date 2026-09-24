"""타임라인 → 자막(SRT / ASS). 문장 단위 큐, 긴 문장은 두 줄로 줄바꿈."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..narration.timeline import Timeline

MAX_CHARS_PER_LINE = 26


@dataclass
class Cue:
    index: int
    start: float
    end: float
    text: str


def wrap_korean(text: str, max_chars: int = MAX_CHARS_PER_LINE) -> str:
    """어절 단위로 최대 두 줄 줄바꿈. 균형 잡힌 두 줄이 되도록 중앙 근처에서 끊는다."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    words = text.split()
    best, best_score = None, None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        score = abs(len(a) - len(b)) + (50 if max(len(a), len(b)) > max_chars + 6 else 0)
        if best_score is None or score < best_score:
            best, best_score = (a, b), score
    if best is None:
        return text
    return best[0] + "\n" + best[1]


def build_cues(timeline: Timeline, min_gap: float = 0.05) -> list[Cue]:
    cues: list[Cue] = []
    idx = 1
    for seg in timeline.segments:
        if seg.clip is None:
            continue
        for s in seg.clip.sentences:
            start = seg.start + s.start
            end = seg.start + s.end
            if cues and start < cues[-1].end + min_gap:
                cues[-1].end = max(cues[-1].start + 0.3, start - min_gap)
            cues.append(Cue(idx, start, max(end, start + 0.6), wrap_korean(s.text)))
            idx += 1
    return cues


def _ts_srt(t: float) -> str:
    ms = int(round(t * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(cues: list[Cue], path: str | Path) -> Path:
    path = Path(path)
    lines = []
    for c in cues:
        lines += [str(c.index), f"{_ts_srt(c.start)} --> {_ts_srt(c.end)}", c.text, ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _ts_ass(t: float) -> str:
    cs = int(round(t * 100))
    h, rem = divmod(cs, 360_000)
    m, rem = divmod(rem, 6_000)
    s, cs = divmod(rem, 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def write_ass(cues: list[Cue], path: str | Path, width: int = 1920, height: int = 1080,
              font: str = "Noto Sans CJK KR", font_size: int | None = None) -> Path:
    """번인용 ASS 자막. 반투명 박스 배경 + 흰 글자, 하단 중앙."""
    path = Path(path)
    fs = font_size or max(28, int(height * 0.042))
    margin_v = int(height * 0.035)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},{fs},&H00F5F7FA,&H000000FF,&H00000000,&H8C0A0E17,-1,0,0,0,100,100,0.5,0,3,{max(6, fs // 5)},0,2,80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for c in cues:
        text = c.text.replace("\n", r"\N")
        events.append(f"Dialogue: 0,{_ts_ass(c.start)},{_ts_ass(c.end)},Default,,0,0,0,,{text}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return path
