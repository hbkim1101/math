# 풀이 문법 (Solution Grammar)

수학 한수 강의 영상의 **핵심 설계 문서**.

## 철학

영상은 “슬라이드”가 아니라 **손풀이의 논리 흐름**을 그대로 따라간다.
사용자가 종이에 쓰는 것처럼, 각 줄은 **화살표 종류**로 논리 관계가 정해진다.

## 화살표 문법

| 기호 | YAML `link` | 의미 | 나레이션 예 |
|------|-------------|------|-------------|
| → | `when` | **만약**, **예를 들어**, 경우 나눔 | “만약 a가 1이 아니라면…” |
| ⇒ | `therefore` | **~~이므로**, 따라서 | “우미분계수가 존재하므로…” |

## 노드 종류

```yaml
flow:
  - link: therefore          # ⇒ 한 줄
    say: "나레이션"
    math: 'LaTeX'
    caption: "화면 하단 요약"

  - link: when               # → 조건/분기
    say: "경우를 나눕니다"
    cases:
      - name: "a ≠ 1"
        flow: [...]
      - name: "a = 1"
        flow: [...]

  - link: therefore
    say: "..."
    visual: graph            # 그래프 등장
    graph: f_prime
```

## 영상 레이아웃

```
┌─────────────────────────────────────┐
│  헤더 (문항 · 주제)                    │
├──────────────────┬──────────────────┤
│  그래프 / 기하     │  ⇒ 수식 흐름       │
│  (좌 55%)         │  (우 45%)         │
├──────────────────┴──────────────────┤
│  ⇒/→ 캡션 + say 나레이션 (TTS)        │
└─────────────────────────────────────┘
```

## 파이프라인

```
solution.yaml → TTS(say[]) → timing.json → GrammarLectureScene → ffmpeg → MP4
```

## 실행

```bash
PYTHONPATH=. python scripts/render_grammar.py problems/examples/q15_derivative.yaml -q l
```
