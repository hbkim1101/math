# 한수 Studio — 모바일 칠판 강의 제작

스마트폰에서 **beat 단위로** 칠판 강의 영상을 수동 제작하는 PWA입니다.

## 기능

- **⇒ 말하기 / 수식 / 그래프 / 점 / 쉬기** beat 추가·편집·순서 변경
- **칠판 미리보기** — Write 느낌의 캡션·수식·그래프 그리기
- **▶ 재생** — beat 순서대로 애니메이션
- **⏺ 녹화** — Canvas → WebM/MP4 저장 (Chrome, Safari iOS 17+)
- **내보내기** — JSON/YAML (PC Manim 파이프라인 연동용)
- **오프라인** — PWA 설치 가능

## 사용법

### 1. 로컬 서버 (PC에서 테스트)

```bash
cd apps/mobile-studio
python3 -m http.server 8765
```

폰과 같은 Wi‑Fi에서 `http://<PC-IP>:8765` 접속

### 2. GitHub Pages

저장소 Pages 루트를 `/docs`로 두면  
`https://<user>.github.io/math/mobile-studio/` 경로에 배포할 수 있습니다.

### 3. 홈 화면에 추가

- **iPhone**: Safari → 공유 → "홈 화면에 추가"
- **Android**: Chrome → 메뉴 → "앱 설치" / "홈 화면에 추가"

## Beat 타입

| 타입 | 설명 |
|------|------|
| `say` | ⇒/→ 한 줄 설명 (타이핑 애니메이션) |
| `math` | LaTeX 수식 (KaTeX 렌더) |
| `graph` | f'(x) / parabola / cubic 그래프 그리기 |
| `dot` | 그래프 위 점 + 라벨 |
| `wait` | N초 대기 |

## 제작 흐름 (권장)

1. 손풀이 → beat sheet
2. 앱에서 beat 순서대로 입력
3. **재생**으로 타이밍 확인
4. **녹화** → 영상 저장
5. (선택) YAML 내보내기 → PC 고화질 Manim 렌더

## 파일

```
apps/mobile-studio/
  index.html      # 앱 UI
  manifest.json   # PWA
  sw.js           # 오프라인 캐시
  css/app.css
  js/
    app.js        # 메인
    board.js      # 칠판 Canvas
    editor.js     # beat 편집
    player.js     # 재생
    recorder.js   # 녹화
    store.js      # localStorage + YAML
```
