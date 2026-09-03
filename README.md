# math — 미적분 시각화

Manim으로 평균값 정리 후보 함수 `g(x)`를 시각화하는 애니메이션입니다.

## 요구 사항

- Python 3.12+
- LaTeX (MathTex 렌더링용)
- ffmpeg

## 설치

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ubuntu/Debian에서 LaTeX가 없다면:

```bash
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-fonts-recommended texlive-science cm-super dvisvgm
```

## 렌더링

```bash
source .venv/bin/activate
manim -qh calculus_visualization.py MeanValueCandidateScene
```

16:9 해상도:

```bash
manim -qh -r 1920,1080 calculus_visualization.py MeanValueCandidateScene
```

출력: `media/videos/calculus_visualization/1080p60/MeanValueCandidateScene.mp4`

## 레이아웃 (문제 / 해설)

화면을 **왼쪽 위 = 문제**, **나머지 = 해설**로 나눕니다.

| 파일 | 역할 |
|------|------|
| `layout_config.py` | 영역 좌표, 배경, 가이드선, 배치 헬퍼 |
| `problem_explanation.py` | 레이아웃 미리보기 씬 (`LayoutPreviewScene`) |

```
┌──────────┬─────────────────┐
│  문제     │                 │
│ (좌상단)  │   해설 (우측)    │
│          │                 │
├──────────┤                 │
│ 해설(좌하)│                 │
└──────────┴─────────────────┘
```

## 실시간 미리보기

코드를 저장하면 자동 재렌더 + 브라우저에서 확인:

```bash
source .venv/bin/activate
./scripts/live_preview.sh
# → http://localhost:8765
```

한 번만 빠르게 렌더:

```bash
./scripts/render_once.sh
# → preview/latest.mp4
```

다른 씬 지정:

```bash
./scripts/live_preview.sh calculus_visualization.py MeanValueCandidateScene
```

## 내용

`MeanValueCandidateScene`은 다음 등식을 그래프로 보여줍니다.

$$\frac{f(x)-f(1)}{x-1} = f'(g(x)) \quad (x \neq 1)$$

- 위쪽: 함수 $f(x)$와 점 $(1, f(1))$, $(x, f(x))$를 잇는 할선
- 아래쪽: 도함수 $f'(x)$와 $g(x)$ 후보 지점
- $x$가 1에 가까워지면 후보들이 수렴하고, 멀어지면 다시 갈라집니다
