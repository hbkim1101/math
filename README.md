# Explainer Studio — 고품질 수학 해설 영상 제작 파이프라인

YAML 시나리오 한 장으로 **3Blue1Brown / 수학도장 스타일의 해설 영상**(애니메이션 시각화 + 한국어 내레이션 + 단계별 수식 보드 + 자막)을 만들고, 산출물을 **자동 검증**하는 프로그램입니다.

```
YAML 시나리오 ──▶ TTS(문장 타이밍) ──▶ Manim 렌더(내레이션과 동기화) ──▶ ffmpeg 합성(자막·라우드니스) ──▶ 자동 검증 리포트
```

데모: `projects/2027_sep_q22/` — 2027학년도 9월 모의평가(2026.9 시행) 수학 공통 22번 (지수·로그함수와 직사각형 ABCD, 정답 97).

---

## 1. 설치

```bash
# 시스템 의존성 (Ubuntu)
sudo apt-get install -y ffmpeg libcairo2-dev libpango1.0-dev pkg-config python3-dev \
  texlive-latex-base texlive-latex-extra texlive-fonts-recommended texlive-science \
  texlive-xetex texlive-lang-korean dvisvgm cm-super fonts-noto-cjk fonts-nanum

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

- 수식: `pdflatex` (MathTex) / 한글+수식 혼합 문장: `xelatex + kotex + Noto Sans CJK KR`
- 내레이션: `edge-tts` (Microsoft 신경망 음성, 기본 `ko-KR-InJoonNeural`; 네트워크 필요, 결과는 캐시됨)

## 2. 사용법

```bash
python -m explainer validate projects/2027_sep_q22/project.yaml --tex   # YAML 구조 + 모든 LaTeX 사전 컴파일
python -m explainer timing   projects/2027_sep_q22/project.yaml         # 문장별 내레이션 타이밍표 (at 값 정할 때)
python -m explainer build    projects/2027_sep_q22/project.yaml --preview   # 480p/15fps 빠른 확인
python -m explainer build    projects/2027_sep_q22/project.yaml             # 1080p/30fps 최종 + 자동 검증
python -m explainer verify   output/2027_sep_q22                            # 산출물 재검증
python -m explainer actions                                                 # 액션 목록
pytest                                                                      # 단위 테스트 + 수학 증명 테스트
```

산출물 (`output/<id>/`): `<id>.mp4`(최종), `subtitles.srt/.ass`, `timeline.json`(세그먼트 실제 시각), `manifest.json`, `verify_report.json`.

## 3. 시나리오 DSL

```yaml
meta:      { id, title, subtitle, voice, rate, resolution: 1080p, fps: 30, subtitles: burn|soft|none }
params:    { a: "(81/16)**(1/3)" }        # 수식/좌표에서 쓰는 상수 (서로 참조 가능)
t2c:       { "\\mathrm{A}": point }        # MathTex 토큰 색상
layout:    { graph: {x_range, y_range, ...}, board: {title, line_scale, ...} }
segments:
  - id: setup
    narration: "a가 1보다 크므로 ... 점 A와 점 B입니다."     # 이 문장이 TTS 로 합성됨
    actions:
      - {do: plot, id: exp, expr: "a**x", color: exp, label: "y=a^x"}
      - {do: points, at: s2, items: [{id: A, at: ["3/4", "3/2"], label: "\\mathrm{A}"}]}
```

- **세그먼트** = 내레이션 한 덩어리. 오디오 길이를 측정해 애니메이션이 끝나도 내레이션이 끝날 때까지 기다리고, 반대로 애니메이션이 길면 그만큼 자연히 늘어납니다 → 잘림 없음.
- **`at`** = 세그먼트 시작 기준 실행 시각. 숫자(초) 또는 `s2`(TTS 가 인식한 2번째 문장의 시작). 문장 경계는 edge-tts 의 `SentenceBoundary` 이벤트로 얻습니다.
- 좌표는 숫자/표현식(`"3/4"`)/점 id(`A`)/`{on: q1, x: "0.5"}` 모두 가능. 표현식은 AST 화이트리스트 기반 안전 평가기(`safe_eval`)로만 계산됩니다.

### 액션 (일부)

| 분류 | 액션 |
|---|---|
| 카드/전환 | `title_card`, `end_card`, `section`, `clear`, `wait`, `caption` |
| 문제/보드 | `problem`(한글+수식 전문), `problem_dock`(보드 헤더로 축소), `board`, `board_write`, `board_replace`, `board_highlight`, `board_clear`, `board_title` |
| 그래프 | `axes`(등축 자동), `plot`(y 범위 밖 자동 클리핑), `line`, `vline`, `point`, `points`, `polygon`, `segment`, `arrow`, `guides`, `label` |
| 기하 연출 | `translate_copy`(평행이동 복사), `reflect`(직선 대칭이동 + 수선/직각 표시) |
| 강조 | `highlight`(indicate/flash/circumscribe/pulse), `dim`/`undim`(stroke·fill 원본 비율 유지), `fade`, `answer` |
| 확장 | `custom` → 프로젝트 폴더의 `hooks.py` 함수 호출 (예: 데모의 `sliding_chord`, `ghost_translate`) |

## 4. 자동 검증 (`explainer verify`)

| 항목 | 내용 |
|---|---|
| 컨테이너 | 해상도/fps/코덱, yuv420p, 오디오 트랙, **오디오·비디오 길이 일치** |
| 동기화 | 세그먼트 시각 단조 증가, **각 세그먼트 길이 ≥ 내레이션 길이(잘림 없음)**, 발화 비율 |
| 자막 | 겹침 없음, 시간 범위, 줄 길이(≤34자), 모든 문장 포함 |
| 프레임 | 검은/빈 프레임 없음, 화면 변화 존재, 선명도(라플라시안 분산), 콘텐츠 존재 |
| 오디오 | 통합 라우드니스(-16 LUFS 목표), 트루피크(클리핑 없음), 긴 무음 없음 |

수학적 내용은 `tests/test_math_q22.py` 에서 sympy 로 증명합니다(포물선 평행이동 (1,−1), 현 기울기 일차식, 대칭축 y=x−1/4 에 대한 A↔D·B↔C 대칭, 직선 y=x+3/4 와의 교점, a³=81/16, p+q=97).

## 5. 구조

```
explainer/
  script/    models.py(pydantic DSL) · loader.py(YAML, safe_eval)
  narration/ tts.py(edge-tts, 문장 타이밍, 캐시) · timeline.py
  render/    theme.py(색·폰트·xelatex 템플릿) · board.py(풀이 보드) · scene.py(세그먼트 실행 루프) · actions.py(액션 라이브러리)
  compose/   subtitles.py(SRT/ASS, 긴 문장 분할) · mux.py(ffmpeg: 자막 번인, loudnorm, apad)
  verify/    checks.py(자동 검증)
  lint.py · pipeline.py · cli.py
projects/2027_sep_q22/  project.yaml · hooks.py
tests/
```

### 구현 메모
- Manim 캐시 재사용 시 `Scene.add_sound` 가 소리를 버리는 문제(`skip_animations`)를 피하기 위해 파일 라이터에 직접 오디오를 삽입합니다.
- 오디오는 마지막 내레이션에서 끝나므로 `apad` + `-shortest` 로 영상 길이에 맞춥니다.
