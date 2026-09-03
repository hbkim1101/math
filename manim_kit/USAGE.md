# manim_kit 사용법

LaTeX로 수식을 입력하고, Manim으로 **그래프·대입 애니메이션**을 만드는 도구입니다.

---

## 입력 형식 — 일반 LaTeX + shortcut 3가지

극한·분수 등은 **표준 LaTeX** 그대로 씁니다 (`\lim_{h \to 0}`, `\frac{...}{...}`).
LaTeX 문법을 몰라도 되는 **shortcut**은 아래 3가지만 있습니다.

```
\lim_{h \to 0} \frac{f(2+h)-f(2)}{h} = f`(2)
[f`(x)=3x^2-8]_{x=2}
f`(2)=3 2^2-8 =4
```

| 기호 | 의미 | 변환 |
|------|------|------|
| `` f`(x) `` | f'(x) | 백틱 `` ` `` = 프라임 |
| `[식]_{x=2}` | x=2 대입 | 대입 애니메이션 2단계 |
| `3 2^2` | 곱셈 | `3 \cdot 2^2` |

```python
from manim_kit import parse_input, substitution_spec_from_input, SUNEUNG_2_INPUT

parsed = parse_input(SUNEUNG_2_INPUT)
print(parsed.problem_latex)
# \lim_{h \to 0} \frac{f(2+h)-f(2)}{h} = f'(2)

print(parsed.substitution_steps)
# ["f'(x) = 3x^2-8", "f'(2) = 3 \\cdot 2^2-8", "f'(2) = 4"]

spec = substitution_spec_from_input(SUNEUNG_2_INPUT, anchor=ORIGIN)
```

> `parse_dsl`, `SUNEUNG_2_DSL` 등은 하위 호환 alias입니다.

예시 파일: `examples/suneung2.dsl.txt`

---

> **곡선 그리기:** Python 함수 `f(x)` 필요 (LaTeX → 곡선 파싱은 추후)

---

## 빠른 시작

```python
from manim import *
from manim_kit import GraphSpec, SubstitutionSpec, build_graph_parts, animate_graph
from manim_kit import build_substitution_steps, animate_substitution, tex

class MyScene(Scene):
    def construct(self):
        # 1) LaTeX 수식 표시
        eq = tex(r"f'(x) = 3x^2 - 8")
        self.play(Write(eq))

        # 2) 그래프 (축 → 곡선 → 접선)
        spec = GraphSpec(
            f=lambda x: x**3 - 8*x + 7,
            tangent_at=2,
            slope_fn=lambda x: 3*x**2 - 8,
            point_label_latex=r"(2,\,-1)",
            tangent_label_pending_latex=r"f'(2)=?",
            tangent_label_final_latex=r"f'(2)=4",
        )
        parts = build_graph_parts(spec)
        animate_graph(self, parts)

        # 3) 대입 애니메이션
        sub = SubstitutionSpec(
            steps=[
                r"f'(x) = 3x^2 - 8",
                r"f'(2) = 3 \cdot 2^2 - 8",
                r"f'(2) = 12 - 8",
                r"f'(2) = 4",
            ],
            anchor=ORIGIN + DOWN * 2,
            highlight="x",
            key_map={"x": "2"},
        )
        steps = build_substitution_steps(sub)
        steps["_highlight"] = sub.highlight
        animate_substitution(self, steps, graph_parts=parts)
```

---

## API 요약

### `tex(latex, scale=1.0, color=WHITE)`

LaTeX 문자열 → `MathTex`

```python
tex(r"\lim_{h \to 0} \frac{f(2+h)-f(2)}{h}")
```

### `tex_block(lines, scale=1.0, buff=0.2)`

LaTeX 리스트 → 세로 나열

```python
tex_block([
    r"f(x) = x^3 - 8x + 7",
    r"f'(x) = 3x^2 - 8",
])
```

---

### `GraphSpec` — 그래프 설정

| 필드 | 설명 | 예시 |
|------|------|------|
| `f` | Python 함수 (필수) | `lambda x: x**3 - 8*x + 7` |
| `x_range` | 축 x 범위 (min, max, step) | `(-2, 3.5, 1)` |
| `y_range` | 축 y 범위 | `(-6, 14, 4)` |
| `plot_x_range` | 곡선 그릴 x 구간 | `(-1.8, 3.2)` |
| `tangent_at` | 접선 x좌표 | `2` |
| `slope_fn` | 기울기 함수 f'(x) | `lambda x: 3*x**2 - 8` |
| `point_label_latex` | 점 라벨 LaTeX | `r"(2,\,-1)"` |
| `x_label_latex` | x축 라벨 | `"2"` |
| `tangent_label_pending_latex` | 접선 라벨 (계산 전) | `r"f'(2)=?"` |
| `tangent_label_final_latex` | 접선 라벨 (계산 후) | `r"f'(2)=4"` |

```python
parts = build_graph_parts(spec)   # dict: axes, graph, tangent, annotations, ...
animate_graph(scene, parts)       # 축 → 곡선 → 접선 순서 Create
graph_group(parts)                # 정적 PNG용 VGroup
```

---

### `SubstitutionSpec` — 대입 애니메이션

| 필드 | 설명 | 예시 |
|------|------|------|
| `steps` | LaTeX 단계 리스트 (2개 이상) | 아래 참고 |
| `anchor` | 수식 위치 (화면 좌표) | `ORIGIN + DOWN` |
| `highlight` | 강조할 조각 | `"x"` |
| `key_map` | 첫 Transform 치환 | `{"x": "2"}` |
| `scale` | 크기 | `0.58` |
| `final_color` | 마지막 답 색 | `YELLOW_E` |

**steps 작성법:**

```python
steps=[
    r"f'(x) = 3x^2 - 8",           # 1. 일반식
    r"f'(2) = 3 \cdot 2^2 - 8",    # 2. x=2 대입
    r"f'(2) = 12 - 8",              # 3. 중간 계산
    r"f'(2) = 4",                   # 4. 최종 답
]
```

```python
steps = build_substitution_steps(spec)
steps["_highlight"] = spec.highlight
animate_substitution(scene, steps, graph_parts=parts)
# graph_parts 넘기면 답 나올 때 접선 라벨도 f'(2)=4 로 갱신
```

---

## 실전 예시: 2025 수능 2번

` suneung_problems.py` 참고:

```python
from suneung_problems import (
    suneung_2_graph_spec,
    suneung_2_substitution_spec,
    build_suneung_2_graph_parts,
    build_suneung_2_deriv_substitution_steps,
    animate_suneung_2_graph,
    animate_suneung_2_deriv_substitution,
)
```

---

## LaTeX 입력 규칙

1. **raw string** 사용: `r"f'(x) = 3x^2 - 8"`
2. 곱셈 기호: `\cdot` (예 `3 \cdot 2^2`)
3. 쉼표 좌표: `(2,\,-1)` (쉼표 앞 `\` )
4. 한글은 `Text("접선 기울기")` — MathTex `\text{}` 는 한글 불가
5. `\lim`, `\frac`, `\to` 등 표준 LaTeX 사용

---

## 앞으로 만들 프로그램 (로드맵)

```
[사용자 LaTeX 입력]
       ↓
  (파싱 · 문제 JSON)
       ↓
  GraphSpec + SubstitutionSpec 자동 생성
       ↓
  LayoutPreviewScene 렌더
```

**지금 입력 형식 (수동):**

```yaml
problem_latex:
  - "f(x) = x^3 - 8x + 7"
  - "\\lim_{h \\to 0} \\frac{f(2+h)-f(2)}{h}"

graph:
  f: "x**3 - 8*x + 7"      # Python expr (추후 sympy)
  tangent_at: 2
  slope: "3*x**2 - 8"

substitution:
  steps:
    - "f'(x) = 3x^2 - 8"
    - "f'(2) = 3 \\cdot 2^2 - 8"
    - "f'(2) = 4"
  highlight: "x"
  key_map: {x: "2"}
```

---

## 미리보기

```bash
./scripts/live_preview.sh
# http://localhost:8765  →  ▶ 재생
```
