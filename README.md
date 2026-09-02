# Math Studio

Manim 기반 **수학 해설 영상**을 웹 UI에서 쉽게 만드는 도구입니다.

코드 없이 장면(수식, 그래프, 텍스트)을 추가하고, 클릭 한 번으로 Manim 애니메이션 MP4를 생성합니다.

## 기능

- **장면 편집**: 수식 / 그래프 / 텍스트 / 단계별 풀이
- **효과 프리셋**: 등장, 페이드인, 그리기, 강조
- **타임라인**: 장면별 대기 시간 조절
- **미리보기 렌더**: Manim으로 MP4 생성
- **다운로드**: 완성된 영상 저장

## 빠른 시작

### 1. 시스템 의존성 + 설치 (Linux)

```bash
chmod +x scripts/setup.sh scripts/dev.sh
./scripts/setup.sh
```

또는 수동:

```bash
sudo apt install python3.12-venv python3-dev ffmpeg \
  libpango1.0-dev libcairo2-dev pkg-config \
  texlive-latex-extra texlive-fonts-extra fonts-noto-cjk
```

### 2. 개발 서버 실행

```bash
chmod +x scripts/dev.sh
./scripts/dev.sh
```

브라우저에서 **http://127.0.0.1:5173** 접속

### 3. 수동 실행

**백엔드:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**프론트엔드:**
```bash
cd frontend
npm install
npm run dev
```

## 사용법

1. 왼쪽 **+ 수식 / + 그래프** 등으로 장면 추가
2. 오른쪽 패널에서 LaTeX, 함수, 효과, 대기 시간 설정
3. 상단 **미리보기 렌더** 클릭
4. 가운데 미리보기 확인 → **MP4 다운로드**

## 장면 타입

| 타입 | 설명 | 예시 |
|------|------|------|
| `equation` | LaTeX 수식 | `y = x^2 - 4x + 3` |
| `graph` | 함수 그래프 | `x**2 - 4*x + 3` |
| `text` | 설명 텍스트 | `꼭짓점 (2, -1)` |
| `steps` | 단계별 풀이 | 여러 줄 LaTeX |

## 아키텍처

```
[React UI] → JSON → [FastAPI] → [Manim 코드 생성] → MP4
```

## Cursor와 함께 쓰기

- 장면 JSON / Manim 생성 로직(`backend/generator.py`) 수정을 Cursor에 맡기기
- "포물선 + 접선 애니메이션 장면 추가해줘" 같이 자연어로 확장
- `.cursor/rules`에 Manim Community 규칙 추가하면 일관된 코드 생성 가능

## 로드맵

- [ ] 실시간 저화질 프리뷰 (렌더 없이)
- [ ] AI 채팅으로 장면 자동 생성
- [ ] 템플릿 저장 / 불러오기
- [ ] Manim Voiceover 나레이션 연동
