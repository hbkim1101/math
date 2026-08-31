"""TTS natural speech helpers — edge-tts SSML, pacing."""

from __future__ import annotations

import re


def normalize_math_speech(text: str) -> str:
    """읽기 좋은 한국어로 수식·기호 치환."""
    t = text
    replacements = [
        (r"f\s*\(\s*x\s*\)", "에프 엑스"),
        (r"f\s*\(\s*c\s*\)", "에프 씨"),
        (r"f\s*\(\s*-3\s*\)", "에프 마이너스 삼"),
        (r"f\s*\(\s*3\s*\)", "에프 삼"),
        (r"f\s*\(\s*2\s*\)", "에프 이"),
        (r"f\s*\(\s*-2\s*\)", "에프 마이너스 이"),
        (r"f\s*\(\s*0\s*\)", "에프 영"),
        (r"f\s*'\s*\(\s*2\s*\)", "에프 프라임 이"),
        (r"f\s*'\s*\(\s*2\s*\)\s*>\s*0", "에프 프라임 이가 영보다 크다"),
        (r"g\s*\(\s*y\s*\)", "지 와이"),
        (r"g\s*\(\s*f\s*\(\s*x\s*\)\s*\)", "지 에프 엑스"),
        (r"g\s*\(\s*0\s*\)", "지 영"),
        (r"h\s*\(\s*x\s*\)", "에이치 엑스"),
        (r"h\s*\(\s*c\s*\)", "에이치 씨"),
        (r"h\s*'\s*\(\s*c\s*\)", "에이치 프라임 씨"),
        (r"h\s*''\s*\(\s*c\s*\)", "에이치 더블 프라임 씨"),
        (r"x\s*=\s*-2", "엑스는 마이너스 이"),
        (r"x\s*=\s*1", "엑스는 일"),
        (r"x\s*=\s*2", "엑스는 이"),
        (r"c\s*=\s*-2", "씨는 마이너스 이"),
        (r"c\s*=\s*1", "씨는 일"),
        (r"a\s*=\s*-2/3", "에이는 마이너스 이분의 삼"),
        (r"a\s×\s*e\s*\^\s*b", "에이 곱하기 e의 b제곱"),
        (r"a×e\^b", "에이 곱하기 e의 b제곱"),
        (r"y\s*=\s*-3x²-4", "와이는 마이너스 삼엑스제곱 빼기 사"),
        (r"ln\s*\(\s*9/2\s*\)", "로그 이분의 구"),
        (r"ln\s*\(9/2\)", "로그 이분의 구"),
        (r"3/2", "이분의 삼"),
        (r"-4/3", "마이너스 삼분의 사"),
        (r"-2/3", "마이너스 이분의 삼"),
        (r"5/2", "이분의 오"),
        (r"Q\(x\)", "큐 엑스"),
        (r"→", ","),
        (r"⇒", ","),
        (r"≤", "이하"),
        (r"≥", "이상"),
        (r"≠", "같지 않"),
        (r"∈", "속하는"),
        (r"π", "파이"),
        (r"α", "알파"),
        (r"β", "베타"),
        (r"θ", "세타"),
        (r"∞", "무한"),
        (r"±", "플러스 마이너스"),
        (r"√", "루트"),
        (r"²", "제곱"),
        (r"³", "세제곱"),
        (r"⁴", "네제곱"),
        (r"⁵", "다섯제곱"),
        (r"\^", "의"),
        (r"_", " "),
    ]
    for pat, rep in replacements:
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)
    # 영어 잔여 equals/times 제거
    t = re.sub(r"\bequals\b", "는", t, flags=re.IGNORECASE)
    t = re.sub(r"\btimes\b", "곱하기", t, flags=re.IGNORECASE)
    t = re.sub(r"\bto the\b", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\bminus\b", "마이너스", t, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?…])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def build_ssml(
    text: str,
    voice: str,
    *,
    rate: str = "-14%",
    pitch: str = "-2Hz",
    pause_ms: int = 420,
) -> str:
    """문장 단위 쉼 + 느린 속도 SSML."""
    spoken = normalize_math_speech(text)
    sentences = split_sentences(spoken)
    if not sentences:
        sentences = [spoken]

    chunks: list[str] = []
    for i, sent in enumerate(sentences):
        chunks.append(sent)
        if i < len(sentences) - 1:
            chunks.append(f'<break time="{pause_ms}ms"/>')

    body = " ".join(chunks)
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ko-KR">'
        f'<voice name="{voice}">'
        f'<prosody rate="{rate}" pitch="{pitch}">{body}</prosody>'
        f"</voice></speak>"
    )
