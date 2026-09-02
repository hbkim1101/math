# Manim 수학 해설 영상 (코드 기반)

2027학년도 6월 모의평가 등 수능/모평 문제를 **Manim Python 코드**로 해설 영상화합니다.

## 설치

```bash
# Ubuntu/Debian
sudo apt install python3.12-venv python3-dev ffmpeg \
  libpango1.0-dev libcairo2-dev pkg-config \
  texlive-latex-extra texlive-fonts-extra fonts-noto-cjk

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 렌더

```bash
source .venv/bin/activate

# 미리보기 (480p, 빠름)
manim -pql scenes/problem_270630.py Problem270630

# 최종 (1080p)
manim -pqh scenes/problem_270630.py Problem270630
```

또는:

```bash
chmod +x scripts/render.sh
./scripts/render.sh              # 480p 미리보기
./scripts/render.sh high         # 1080p
```

## 프로젝트 구조

```
scenes/
  common.py           # 한글 Text, step 라벨 등 공통 유틸
  problem_270630.py   # 2027.6 모의평가 미적분 30번
scripts/
  render.sh
requirements.txt
```

## 문제 코드 규칙

| 코드 | 의미 |
|------|------|
| `270630m` | 2027학년도 6월 모의평가 미적분 30번 |
| `270630p` | 같은 시험 확률과통계 30번 |

새 문제 추가 시 `scenes/problem_XXXXXX.py` 파일을 만들고 Scene 클래스를 추가하면 됩니다.

## Cursor 활용

- `scenes/problem_270630.py` 를 열고 "2단계 설명 더 자세히", "그래프 추가" 등으로 수정
- 새 문제: "270615 미적분 15번 풀이 Scene 만들어줘"
- Manim API 검색·LaTeX 수정을 Cursor에 맡기기

## 현재 영상

**270630m** — 삼차함수 `f(x)`와 `g(x)=∛(x(f(x))²)`의 미분가능성  
→ `f(x)=x(x²-8x+19)`, **정답 20**
