"""edge-tts 기반 내레이션 합성 + 문장 단위 타이밍 추출.

- 텍스트/보이스/속도 해시로 캐시하여 재렌더 시 네트워크 호출을 생략한다.
- WordBoundary 이벤트를 저장해 문장별 시작/끝 시각을 계산한다 (자막 큐, `at: "s2"` 동기화에 사용).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。？！])\s+")


@dataclass
class Sentence:
    text: str
    start: float
    end: float


@dataclass
class NarrationClip:
    text: str
    audio_path: str
    duration: float
    sentences: list[Sentence] = field(default_factory=list)
    words: list[dict] = field(default_factory=list)

    def sentence_start(self, index_1based: int) -> float:
        if not self.sentences:
            return 0.0
        idx = max(1, min(index_1based, len(self.sentences))) - 1
        return self.sentences[idx].start

    def to_json(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_json(cls, d: dict) -> "NarrationClip":
        d = dict(d)
        d["sentences"] = [Sentence(**s) for s in d.get("sentences", [])]
        return cls(**d)


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_SPLIT.split(text.strip()) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def probe_duration(path: str | Path) -> float:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def _cache_key(text: str, voice: str, rate: str, pitch: str) -> str:
    return hashlib.sha1(f"{voice}|{rate}|{pitch}|{text}".encode("utf-8")).hexdigest()[:20]


async def _synthesize_async(text: str, voice: str, rate: str, pitch: str, mp3_path: Path) -> list[dict]:
    """오디오를 저장하고 SentenceBoundary 이벤트(문장 시작/끝)를 돌려준다."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch, boundary="SentenceBoundary")
    marks: list[dict] = []
    with open(mp3_path, "wb") as fh:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])
            elif chunk["type"] in ("SentenceBoundary", "WordBoundary"):
                marks.append(
                    {
                        "text": chunk["text"],
                        "start": chunk["offset"] / 1e7,
                        "end": (chunk["offset"] + chunk["duration"]) / 1e7,
                    }
                )
    return marks


def _sentences_from_marks(text: str, marks: list[dict], total: float) -> list[Sentence]:
    """SentenceBoundary 이벤트를 문장 타이밍으로 변환한다. 개수가 맞지 않으면 단어 기반 폴백."""
    if marks:
        # TTS 엔진이 실제로 끊어 읽은 문장 경계를 그대로 사용한다 (자막/동기화의 기준)
        result = [Sentence(m["text"].strip(), m["start"], m["end"]) for m in marks if m["text"].strip()]
    else:
        return _sentences_from_words(text, [], total)
    result[0].start = 0.0
    result[-1].end = total
    for i in range(len(result) - 1):
        result[i].end = result[i + 1].start
    return result


def _sentences_from_words(text: str, words: list[dict], total: float) -> list[Sentence]:
    """단어 경계 정보를 문장 텍스트에 순서대로 배분하여 문장 타이밍을 만든다."""
    sents = split_sentences(text)
    if not sents:
        return []
    if not words:
        # 균등 분배 (폴백)
        n = len(sents)
        return [Sentence(s, total * i / n, total * (i + 1) / n) for i, s in enumerate(sents)]

    # 단어 텍스트를 순차 매칭: 각 문장에서 공백 제거한 글자 수를 기준으로 단어를 소비한다
    result: list[Sentence] = []
    wi = 0
    for si, s in enumerate(sents):
        target = len(re.sub(r"\s+", "", s))
        consumed = 0
        start_idx = wi
        while wi < len(words) and consumed < target:
            consumed += len(re.sub(r"\s+", "", words[wi]["text"]))
            wi += 1
        end_idx = max(wi - 1, start_idx)
        if start_idx >= len(words):
            start = result[-1].end if result else 0.0
            end = total
        else:
            start = words[start_idx]["start"]
            end = words[end_idx]["end"]
        result.append(Sentence(s, start, end))
    # 마지막 문장의 끝은 오디오 끝으로, 첫 문장의 시작은 0으로 정리
    if result:
        result[0].start = 0.0
        result[-1].end = total
        # 문장 사이 공백을 없애서 자막이 끊기지 않게 함
        for i in range(len(result) - 1):
            result[i].end = result[i + 1].start
    return result


def cached_clip(text: str, voice: str, rate: str = "+0%", pitch: str = "+0Hz",
                cache_dir: str | Path = "cache/tts") -> Optional[NarrationClip]:
    """이미 합성된 적이 있으면 캐시의 NarrationClip 을, 없으면 None (네트워크를 쓰지 않는다)."""
    text = " ".join(text.split())
    if not text:
        return None
    cache_dir = Path(cache_dir)
    key = _cache_key(text, voice, rate, pitch)
    mp3, meta = cache_dir / f"{key}.mp3", cache_dir / f"{key}.json"
    if not (mp3.exists() and meta.exists()):
        return None
    try:
        return NarrationClip.from_json(json.loads(meta.read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        return None


def synthesize_segment(
    text: str,
    voice: str,
    rate: str = "+0%",
    pitch: str = "+0Hz",
    cache_dir: str | Path = "cache/tts",
    force: bool = False,
) -> Optional[NarrationClip]:
    """문장을 mp3로 합성하고 NarrationClip을 돌려준다. 빈 텍스트면 None."""
    text = " ".join(text.split())
    if not text:
        return None
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _cache_key(text, voice, rate, pitch)
    mp3 = cache_dir / f"{key}.mp3"
    meta = cache_dir / f"{key}.json"

    if not force:
        hit = cached_clip(text, voice, rate, pitch, cache_dir)
        if hit is not None:
            return hit

    marks = asyncio.run(_synthesize_async(text, voice, rate, pitch, mp3))
    if not mp3.exists() or mp3.stat().st_size < 1000:
        raise RuntimeError(f"TTS 합성 실패: {text[:40]!r}")
    duration = probe_duration(mp3)
    clip = NarrationClip(
        text=text,
        audio_path=str(mp3.resolve()),
        duration=duration,
        sentences=_sentences_from_marks(text, marks, duration),
        words=marks,
    )
    meta.write_text(json.dumps(clip.to_json(), ensure_ascii=False, indent=1), encoding="utf-8")
    return clip
