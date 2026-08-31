# math-viz

**수학 한수** 스타일 — 손풀이 **문법(→/⇒)** 그대로 강의 영상 생성

## 핵심 아이디어

영상 = 슬라이드 ❌ · **손풀이 논리 흐름** ✅

| 기호 | YAML | 의미 |
|------|------|------|
| → | `link: when` | **만약**, **예를 들어**, 경우 나눔 |
| ⇒ | `link: therefore` | **~~이므로**, 따라서 |

자세한 설계: [docs/GRAMMAR.md](docs/GRAMMAR.md)

## 모바일 Studio (수동 제작)

스마트폰 PWA — beat 편집 · 칠판 재생 · 영상 녹화

→ [apps/mobile-studio/README.md](apps/mobile-studio/README.md)

```bash
cd apps/mobile-studio && python3 -m http.server 8765
# 폰에서 http://<PC-IP>:8765
```

## 강의 영상 만들기 (PC Manim)

```bash
# 15번 예시 — 사용자 손풀이 문법 그대로
PYTHONPATH=. python scripts/render_grammar.py problems/examples/q15_derivative.yaml -q l
# → docs/videos/q15_grammar.mp4 (TTS 포함)
```

## YAML 예시

```yaml
flow:
  - link: therefore
    say: "우미분계수가 실수이려면 분자 극한이 0이어야 합니다."
    math: '\lim_{x\to a^+}\frac{g(x)-g(a)}{x-a}\in\mathbb{R}'
    caption: "(가) ⇒ 분자→0"

  - link: when
    say: "a가 1인지 아닌지 나눕니다."
    cases:
      - name: "a ≠ 1"
        flow: [...]
      - name: "a = 1"
        flow:
          - link: therefore
            say: "f(1)+k=-f(1)이므로 f(1)=-k/2"
            math: 'f(1)=-\frac{k}{2}'
```

## 프로젝트 구조

```
src/grammar/          # 풀이 문법 DSL (→/⇒)
src/scenes/grammar_lecture.py
scripts/render_grammar.py   ← 메인 진입점
problems/examples/    # 문항별 solution YAML
```

## 레거시

- `render_grammar.py` — **풀이 문법** 기반 (신규, 권장)
- `render_lecture.py` — step 기반 강의
- `generate_video.py` — 자동 템플릿 파이프라인
- `render_viz.py` — 수동 Manim Scene
