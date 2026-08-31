# math-viz

**수학 한수** 스타일 — 수능 수학 **그래프·핵심 아이디어 중심** 자동 해설 영상 생성

## 설계 원칙

- 텍스트 슬라이드 ❌ → **그래프·애니메이션·기하 직관** ✅
- 하단 **캡션 바** + 우측 **핵심 수식** (수학 한수 레이아웃)
- Manim `Axes`, `plot`, `ValueTracker`로 **개념이 보이게**
- **TTS 나레이션** (edge-tts 한국어) + **자막(SRT)** 자동 생성

## 파이프라인

```
[문제 YAML] → [시각화 플랜 자동 추론] → [TTS 나레이션] → [Manim 렌더] → [ffmpeg 합성] → MP4
     ↑
[텍스트/LLM 생성]  (OPENAI_API_KEY 설정 시)
```

## 빠른 시작

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 시스템 의존성 (Manim + LaTeX + ffmpeg)
# Ubuntu: apt install ffmpeg texlive-latex-extra texlive-fonts-recommended dvisvgm cm-super

# 단일 문항 영상 (TTS 포함)
PYTHONPATH=. python scripts/generate_video.py render \
  problems/2026_suneung/common.yaml --id 2 -q l

# TTS 없이 빠른 미리보기
PYTHONPATH=. python scripts/generate_video.py render \
  problems/2026_suneung/common.yaml --id 2 -q l --no-tts

# exam 전체 일괄 렌더
PYTHONPATH=. python scripts/generate_video.py batch \
  problems/2026_suneung/common.yaml -q l

# YAML에 시각화 플랜 추가
PYTHONPATH=. python scripts/generate_video.py enrich \
  problems/2026_suneung/common.yaml -o problems/2026_suneung/common_enriched.yaml

# 텍스트 문제 → 자동 풀이 + 영상 (OPENAI_API_KEY 선택)
PYTHONPATH=. python scripts/generate_video.py generate \
  "f(x)=3x^3+7x+1, x=1에서 미분계수" --topic "미분계수" --id 1
```

## 출력 위치

```
output/pipeline/q02_미분계수/
  ├── q02_미분계수_final.mp4   # 나레이션 합성 최종본
  ├── q02_미분계수.srt         # 자막
  ├── audio/                   # step별 TTS
  └── problem_enriched.yaml    # 시각화 플랜 포함
```

## YAML 형식

```yaml
exam: "2026학년도 대학수학능력시험"
section: "수학 공통"
source: "한국교육과정평가원"
brand: "수학 한수"

problems:
  - id: 2
    topic: "미분계수"
    question_latex: 'f(x) = 3x^3 + 7x + 1'
    answer: "④ 16"
    answer_value: 16
    steps:
      - narration: "이 극한은 x=1에서의 미분계수 f'(1)입니다."
        latex: '\lim_{h \to 0} \frac{f(1+h)-f(1)}{h} = f''(1)'
        caption: "극한 = 미분계수 = 접선 기울기"
        visual:
          - action: plot
            expr: "3*x**3 + 7*x + 1"
            color: BLUE
          - action: tangent_at
            expr: "3*x**3 + 7*x + 1"
            x: 1
    visual:
      template: derivative_tangent
      expr: "3*x**3 + 7*x + 1"
      tangent_at: 1
```

### 시각화 템플릿

| template | 용도 |
|----------|------|
| `derivative_tangent` | 미분계수 · 접선 기울기 |
| `piecewise_continuity` | 조각함수 연속성 |
| `equation_flow` | 대수/지수 등 수식 중심 |
| `custom` | `visual.actions` 수동 지정 |

### Visual Actions

| action | 설명 |
|--------|------|
| `plot` | 함수 그래프 |
| `tangent_at` | 접선 + 점 |
| `plot_piecewise` | 조각함수 + 매개변수 애니메이션 |
| `highlight_point` | 특정 점 강조 |
| `vertical_line` | 수직선 (x=1 등) |
| `show_equation` | 우측 수식 패널 |
| `caption` | 하단 캡션 변경 |

## 프로젝트 구조

```
src/
  dsl/models.py          # Problem / Step YAML 모델
  dsl/visual.py          # 시각화 DSL
  renderer/action_engine.py  # Manim action 실행기
  renderer/expression.py     # sympy 수식 파싱
  scenes/hansu_scene.py      # 자동 Scene (수학 한수 스타일)
  tts/synthesizer.py         # edge-tts 나레이션
  pipeline/
    planner.py           # topic → 시각화 플랜 추론
    generator.py         # LLM/규칙 기반 풀이 생성
    runner.py            # 전체 파이프라인
    assembler.py         # ffmpeg 합성
scripts/
  generate_video.py      # CLI
  render_viz.py          # (레거시) 수동 Scene 일괄 렌더
problems/                # exam YAML
```

## 환경 변수

| 변수 | 설명 |
|------|------|
| `OPENAI_API_KEY` | LLM 풀이 생성 (선택) |
| `OPENAI_MODEL` | 기본 `gpt-4o-mini` |
| `MATH_VIZ_TTS_VOICE` | TTS 음성 (기본 `ko-KR-SunHiNeural`) |
| `MATH_VIZ_EXAM_PATH` | Manim 직접 실행 시 exam YAML |
| `MATH_VIZ_PROBLEM_ID` | Manim 직접 실행 시 문항 ID |
| `MATH_VIZ_TIMING` | step별 오디오 타이밍 JSON |

## 기존 수동 Scene

고난도 문항(21, 28, 30번)은 **전용 Manim Scene**으로 더 풍부한 시각화 제공:

```bash
PYTHONPATH=. python scripts/render_viz.py
```

자동 파이프라인(`generate_video.py`)과 병행 사용 가능.
