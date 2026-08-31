# math-viz

**수학 한수** 스타일 — 손풀이 **문법(→/⇒)** · 칠판 강의 · 그래프 중심

## 📱 모바일 Studio (수동 제작, 권장)

스마트폰 PWA — beat 편집 · 칠판 재생 · 영상 녹화

→ **https://hbkim1101.github.io/math/mobile-studio/** (저장소 Public + Pages 배포 후)

→ [apps/mobile-studio/README.md](apps/mobile-studio/README.md)

```bash
cd apps/mobile-studio && python3 -m http.server 8765
# 폰에서 http://<PC-IP>:8765
```

## PC Manim — 칠판 필기

```bash
PYTHONPATH=. .venv/bin/manim -ql src/scenes/chalk_q15_demo.py ChalkQ15DemoScene
PYTHONPATH=. python scripts/render_grammar.py problems/examples/q15_derivative.yaml -q l
```

## PC Manim — YAML 자동 강의

```bash
PYTHONPATH=. python scripts/render_lecture.py problems/2026_suneung/calc_q28_june.yaml --id 28
```

| 기호 | YAML | 의미 |
|------|------|------|
| → | `link: when` | **만약**, **예를 들어** |
| ⇒ | `link: therefore` | **~~이므로**, 따라서 |

자세한 설계: [docs/GRAMMAR.md](docs/GRAMMAR.md)

## Lecture DSL (step types)

| type | 설명 |
|------|------|
| `narrate` | TTS + 하단 자막 |
| `graph` | preset 곡선 + 접선 + 점 |
| `latex` | 수식 |
| `answer` | 정답 |

## GitHub Pages 배포

저장소가 **Private**이면 Pages URL이 404입니다.

1. GitHub → **Settings → General → Danger zone → Change visibility → Public**
2. **Settings → Pages → Source: GitHub Actions**
3. `main` 브랜치 push 시 `.github/workflows/pages.yml` 자동 배포

## 구조

```
apps/mobile-studio/     # 모바일 PWA
docs/mobile-studio/     # Pages 배포
src/renderer/chalk_board.py
src/scenes/chalk_q15_demo.py
src/scenes/generic_lecture.py
scripts/render_grammar.py
scripts/render_lecture.py
```
