#!/usr/bin/env python3
"""Generate TTS narration for 2026 June Q28 Math Hansu-style video."""

from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

VOICE = "ko-KR-InJoonNeural"
OUT = Path(__file__).resolve().parents[1] / "assets" / "narration" / "q28_june"

# 수학한수 흐름: g → h → ln 변곡 → 접선 선택
SEGMENTS = [
    "26학년도 6월 미적분 28번, 같이 풀어볼게요. "
    "겉으로는 복잡해 보이지만, 핵심은 합성함수입니다.",
    "조건 (가)를 이항하면, g(f(x))는 h(x)와 같아요. "
    "g(y)는 y 다섯제곱 더하기 y 세제곱, "
    "h(x)는 로그 빼기 ax 더하기 b 입니다.",
    "먼저 겉함수 g(y) equals y 다섯제곱 더하기 y 세제곱 그래프를 그려볼게요. "
    "영점에서만 삼차처럼 움직이는, 기울기가 항상 양수인 함수예요.",
    "조건 (나) f(-3) f(3)이 음수이므로, 사잇값 정리로 "
    "열린구간 (-3, 3) 안에 f(c) equals 0인 c가 반드시 존재합니다.",
    "f(c)가 0이면 g(f(c))도 0이므로, h(c) equals 0 입니다. "
    "로그 그래프에서 직선 y equals ax 더하기 b 가 x equals c 를 지나야 해요.",
    "f가 이계도함수이려면, h(x)는 c 근처에서 최소 삼차식으로 0에 접근해야 합니다. "
    "그래서 h(c), h 프라임 c, h 더블프라임 c 가 모두 0이 됩니다.",
    "h(x)의 이계도함수를 계산하면, c equals -2 또는 c equals 1 입니다. "
    "둘 다 로그 함수의 변곡점이에요.",
    "이제 y equals ln(x 제곱 더하기 x 더하기 5/2) 그래프를 그립니다. "
    "x equals -2 와 x equals 1 에서 오목·볼록이 바뀌죠.",
    "변곡점에서의 접선이 두 개 후보입니다. "
    "왼쪽 접선은 기울기 a가 음수, 오른쪽은 a가 양수예요.",
    "f 프라임 2가 0보다 크므로, h(x)는 x equals 2 에서 증가해야 합니다. "
    "따라서 왼쪽 변곡점 접선, x equals -2 가 정답입니다.",
    "x equals -2 에서 접선의 기울기 a는 -2/3, "
    "b는 ln 9/2 빼기 4/3 입니다.",
    "구하는 값 a times e to the b 는 "
    "-3 times e to the minus 4/3. 정답은 1번입니다.",
]


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for i, text in enumerate(SEGMENTS):
        path = OUT / f"{i:02d}.mp3"
        print(f"  [{i:02d}] {text[:50]}…")
        comm = edge_tts.Communicate(text, VOICE)
        await comm.save(str(path))
    print(f"\nDone: {OUT} ({len(SEGMENTS)} files)")


if __name__ == "__main__":
    asyncio.run(main())
