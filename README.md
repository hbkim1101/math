# math

수능 수학 자동 시각화 해설

## 2026 수능 수학 1~4번 시각화 테스트

2026학년도 대학수학능력시험 수학 공통 1~4번 문제를 Manim으로 시각화합니다.

| 문항 | 주제 | 정답 |
|------|------|------|
| 1번 | 지수법칙 | ① 1 |
| 2번 | 미분계수 | ④ 16 |
| 3번 | 시그마 (수열의 합) | ⑤ 14 |
| 4번 | 함수의 연속 | ③ 3 |

### 실행 방법

```bash
# 가상환경 설정 (최초 1회)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# LaTeX (MathTex 렌더링용, Ubuntu)
sudo apt install texlive-latex-base texlive-latex-extra dvisvgm cm-super

# 1~4번 전체 렌더
PYTHONPATH=. python scripts/render_all.py

# 개별 렌더 예시
PYTHONPATH=. manim -qm --media_dir output/2026_suneung -o q01_exponent \
  src/scenes/suneung_2026.py Q01ExponentScene
```

### 출력 위치

```
output/2026_suneung/videos/suneung_2026/720p30/
├── q01_exponent.mp4
├── q02_derivative.mp4
├── q03_sigma.mp4
└── q04_continuity.mp4
```

### 프로젝트 구조

```
problems/2026_suneung/common.yaml   # 문제·풀이 Scene DSL
src/dsl/models.py                   # DSL Pydantic 모델
src/renderer/base.py                # Manim 공통 Scene
src/scenes/suneung_2026.py          # 1~4번 Scene 클래스
scripts/render_all.py               # 일괄 렌더 스크립트
```
