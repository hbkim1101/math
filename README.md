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

## 내용

`MeanValueCandidateScene`은 다음 등식을 그래프로 보여줍니다.

$$\frac{f(x)-f(1)}{x-1} = f'(g(x)) \quad (x \neq 1)$$

- 위쪽: 함수 $f(x)$와 점 $(1, f(1))$, $(x, f(x))$를 잇는 할선
- 아래쪽: 도함수 $f'(x)$와 $g(x)$ 후보 지점
- $x$가 1에 가까워지면 후보들이 수렴하고, 멀어지면 다시 갈라집니다
