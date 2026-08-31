# math

수능 수학 **그래프·핵심 아이디어 중심** 자동 강의 영상

## 목표 (자동화)

**문항별 Python Scene 없이** YAML만으로 강의 영상 생성:

```
problems/*.yaml  →  GenericLectureScene  →  TTS  →  MP4
```

```bash
# 6월 28번 자동 렌더 (TTS + Manim)
PYTHONPATH=. python scripts/render_lecture.py problems/2026_suneung/calc_q28_june.yaml --id 28

# TTS만 재생성
PYTHONPATH=. python scripts/generate_lecture_tts.py problems/2026_suneung/calc_q28_june.yaml --id 28
```

## Lecture DSL (step types)

| type | 설명 |
|------|------|
| `narrate` | TTS + 하단 자막 |
| `problem` | 문제식 표시 |
| `latex` / `latex_block` | 수식 |
| `graph` | preset 곡선 + 접선 + 점 |
| `number_line` | 사잇값 정리 등 |
| `answer` | 정답 |
| `clear` | 보드 지우기 |

그래프 preset: `g_y5_y3`, `june28_ln`, `june28_k` (`src/renderer/graph_presets.py`)

## 구조

```
src/dsl/lecture_models.py      # Lecture DSL (Pydantic)
src/renderer/lecture_engine.py # YAML step 실행 엔진
src/renderer/graph_presets.py
src/scenes/generic_lecture.py  # Scene 1개 (공통)
scripts/render_lecture.py      # YAML → MP4
problems/2026_suneung/calc_q28_june.yaml
```

## TTS 품질

- 기본: **edge-tts** + SSML (느린 속도, 문장 간 pause)
- YAML `narrate.speech`: 화면 자막(`text`)과 별도로 **자연스러운 내레이션** 작성
- `lecture.tts`: voice, rate, pitch, pause_ms 조절

수학한수급 목소리는 **사람 녹음** 또는 ElevenLabs 등 고품질 TTS API 연동이 필요합니다.
edge-tts는 무료 대안으로 “로봇 느낌” 한계가 있습니다.

`calc_q21.py`, `calc_q28_june_v2.py` 등은 **프로토타입**. 새 문항은 YAML 우선.

## 모바일

https://github.com/hbkim1101/math/raw/main/docs/videos/lecture_q28_calc_q28_june.mp4
