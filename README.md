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

| provider | 설정 | 비고 |
|----------|------|------|
| `edge` (기본) | `lecture.tts.voice`, `rate`, `pitch`, `pause_ms` | 무료, SSML |
| `elevenlabs` | `ELEVENLABS_API_KEY` + `elevenlabs_voice_id` | 유료, 자연스러움 ↑ |

```yaml
lecture:
  tts:
    provider: elevenlabs
    elevenlabs_voice_id: "YOUR_VOICE_ID"
    elevenlabs_model: eleven_multilingual_v2
```

```bash
export ELEVENLABS_API_KEY=sk-...
PYTHONPATH=. python scripts/generate_lecture_tts.py problems/foo.yaml --id 28 --force
```

- YAML `narrate.speech`: 화면 자막(`text`)과 별도로 **자연스러운 내레이션** 작성
- edge-tts는 무료 대안으로 “로봇 느낌” 한계가 있습니다. 수학한수급은 **사람 녹음** 또는 ElevenLabs 권장.

## AI YAML 생성 (OpenAI)

풀이 메모만 넣으면 Lecture DSL 초안을 생성합니다 (검수 후 렌더).

```bash
export OPENAI_API_KEY=sk-...

# 프롬프트만 확인
PYTHONPATH=. python scripts/generate_lecture_yaml.py \
  --id 28 --topic "합성함수" \
  --question 'g(f(x))=h(x)' \
  --notes-file solution.txt \
  --output problems/draft_q28.yaml --dry-run

# 생성
PYTHONPATH=. python scripts/generate_lecture_yaml.py \
  --exam "2026 6월 모평" --id 28 --topic "합성함수" \
  --question '(f(x))^5+...' --answer "① $-3e^{-4/3}$" \
  --notes "g(y)=y^5+y^3, f(c)=0, 접선..." \
  -o problems/draft_q28.yaml
```

생성 YAML은 graph preset·LaTeX·speech를 **반드시 사람이 검수**한 뒤 `render_lecture.py`로 렌더하세요.

`calc_q21.py`, `calc_q28_june_v2.py` 등은 **프로토타입**. 새 문항은 YAML 우선.

## 모바일

https://github.com/hbkim1101/math/raw/main/docs/videos/lecture_q28_calc_q28_june.mp4
