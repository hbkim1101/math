# Explainer Studio — 고품질 수학 해설 영상 제작 파이프라인

YAML 시나리오 한 장으로 **3Blue1Brown / 수학도장 스타일의 해설 영상**(애니메이션 시각화 + 한국어 내레이션 + 단계별 수식 보드 + 자막)을 만들고, 산출물을 **자동 검증**하는 프로그램입니다.

```
YAML 시나리오 ──▶ TTS(문장 타이밍) ──▶ Manim 렌더(내레이션과 동기화) ──▶ ffmpeg 합성(자막·라우드니스) ──▶ 자동 검증 리포트
```

데모 (2027학년도 9월 모의평가, 2026.9 시행, 수학 공통) — 모두 **칠판 강의 스타일**:
- `projects/2027_sep_q01/` — 1번: 지수법칙 (정답 ④ 2^{1/2}) — **식 전개(derive) 데모**: 밑 통일 → 지수 곱 → 지수 합
- `projects/2027_sep_q02/` — 2번: 미분계수의 정의 (정답 ③ 23) — 할선→접선 애니메이션 + 항별 미분 + 대입
- `projects/2027_sep_q03/` — 3번: 등차수열 (정답 ② 17) — 항 번호 줄에서 공차를 '몇 번' 더하는지 세는 애니메이션
- `projects/2027_sep_q04/` — 4번: 함수의 연속 (정답 ② 10) — a 를 움직여 틈이 닫히는 순간 + **이항 애니메이션**
- `projects/2027_sep_q21/` — 21번: 절댓값 함수의 미분가능성, 뾰족점의 상쇄 (정답 12) (`project_panel.yaml` 은 패널 스타일 버전)
- `projects/2027_sep_q22/` — 22번: 지수·로그함수와 직사각형 ABCD (정답 97) (`project_panel.yaml` 은 패널 스타일 버전)

실전 데모 (2026학년도 대학수학능력시험, 2025.11 시행):
- `projects/2026_suneung_q22/` — 22번: 로그함수·지수함수와 대칭이동, 중점 (정답 457) — **Explainer Studio(아래 §3) 로 제작**. 로그 조건을 지수식으로 바꿔 (2b, 2a) 가 지수함수 위에 있음을 보이고, 곡선 전체가 `y=x` 대칭 → 원점 중심 2배 확대로 옮겨 가는 애니메이션(`hooks.py: swap_then_scale`), 볼록성으로 교점의 유일성, 중점 조건 연립.

- `projects/2026_suneung_calc30/` — 미적분 30번: 역함수의 그래프에서 교점의 개수 g(m) (정답 11) — **처음부터 끝까지 제작 과정을 따라가는 가이드: [`docs/guide_suneung_calc30.md`](docs/guide_suneung_calc30.md)**. 후보 곡선 4개에서 증가하는 가지 고르기, 직선도 y=x 에 뒤집기(`inverse_curve`), 기울기를 움직이며 교점을 실시간으로 세는 스윕(`slope_sweep`), g(m) 계단 그래프(`step_graph`).

두 가지 연출 스타일을 지원합니다 (`meta.style`):

| 스타일 | 설명 |
|---|---|
| `panel` | 왼쪽 그래프 + 오른쪽 풀이 보드 패널. 보드는 지우고 다시 쓴다. 카메라 고정. |
| `chalkboard` | **하나의 큰 칠판**에 지우지 않고 계속 써 나가고, 카메라가 **줌인/아웃**으로 따라간다. 질감 있는 초록 칠판, 색분필 팔레트, 손글씨 폰트(나눔바른펜/나눔손글씨 펜)로 **판서(Write) 애니메이션**. 핵심 메모(캡션)는 화면에 고정. 실제 강의 영상의 판서 흐름 + 영상만의 애니메이션(그래프 생성, 매개변수 슬라이더, 확대 뷰)을 함께 유지. |

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
python -m explainer build    projects/2027_sep_q22/project.yaml --segments setup_exp,setup_log   # 일부 세그먼트만 (output/<id>__part/)
python -m explainer verify   output/2027_sep_q22                            # 산출물 재검증
python -m explainer actions                                                 # 액션 목록
python -m explainer studio                                                  # 브라우저 편집기 (아래 §3)
pytest                                                                      # 단위 테스트 + 수학 증명 테스트
```

산출물 (`output/<id>/`): `<id>.mp4`(최종), `subtitles.srt/.ass`, `timeline.json`(세그먼트 실제 시각), `manifest.json`, `verify_report.json`.

## 3. Explainer Studio — 브라우저 편집기

```bash
python -m explainer studio                 # http://localhost:8765 를 브라우저로 연다 (bind 0.0.0.0)
python -m explainer studio --host 127.0.0.1   # 본인 PC에서만 들을 때
python -m explainer studio --port 9000 --root /path/to/repo --no-browser
```

YAML 을 직접 쓰지 않고도 위 파이프라인으로 영상을 **만들고 고치는** 로컬 프로그램입니다 (FastAPI + 순수 JS, 외부 CDN 없음).

### 내 PC에서 열기

**A. Cursor Cloud Agent 가 이미 Studio 를 띄운 경우 (가장 빠름)**  
Cursor Desktop → Agents Window에서 이 에이전트 탭을 연 뒤, 에디터 패널 **오른쪽 위 플러그(Forwarded Ports)** 아이콘을 누르세요. 포트 `8765` 가 Detected 되면 포워딩(또는 Auto-Forward)하고 **Open in internal browser** / 내 PC 브라우저에서 `http://localhost:8765/` 를 엽니다. (모바일 웹만 쓰면 포트 포워딩이 안 되니 Desktop 을 쓰거나 B를 따르세요.)

**B. 내 PC에 받아서 직접 실행**

```bash
git clone https://github.com/hbkim1101/math.git
cd math
git checkout cursor/explainer-video-studio-6877

# macOS / Linux
./scripts/run_studio.sh

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File .\scripts\run_studio.ps1
```

첫 실행 때 venv 생성 + `pip install -e .` 가 자동으로 돌아갑니다. 끝나면 브라우저에서 `http://localhost:8765/` → 프로젝트 `2026_suneung_q22` 선택.  
시스템 의존성(ffmpeg, TeX, 한글 폰트)은 [§1 설치](#1-설치)를 한 번 맞춰 두면 렌더까지 됩니다. 편집·검사·YAML만 보려면 Studio 기동만으로도 충분합니다.

**C. 완성된 영상만 보기**  
PR [#10](https://github.com/hbkim1101/math/pull/10) 의 아티팩트, 또는 clone 후 `output/2026_suneung_q22/2026_suneung_q22.mp4` 를 로컬 플레이어로 여세요.

| 영역 | 기능 |
|---|---|
| 프로젝트 | 목록 / **새 프로젝트**(칠판 템플릿: 제목·문제·풀이·정답 4개 세그먼트) / 저장(`Ctrl+S`, 저장 전 `.history/` 에 스냅샷 → **되돌리기**) |
| 세그먼트 편집 | 왼쪽 목록에서 선택·드래그로 순서 변경·추가/삭제. 내레이션 textarea 아래에 **문장 칩(s1, s2, …)** 과 `▶ 듣기 · 문장 타이밍`(TTS 를 미리 합성해 각 문장의 시작 시각 표시) |
| 액션 카드 | 액션 카탈로그(분류·설명·파라미터 기본값 자동 추출)에서 골라 추가. 카드마다 `at`/`run_time`, 파라미터 표(값은 숫자/불/목록/객체를 자동 해석), **식 전개(derive/step) 전용 편집기**(조각은 `|` 로 구분, why/from/cancel/box/pulse/hold), 고급 사용자는 카드별 JSON 직접 편집 |
| 설정 | meta(제목·음성·해상도·자막), 칠판 섹션(id/제목/full·split), params, 원본 YAML 보기·적용(정렬된 형식으로 다시 저장) |
| 검사 | **검사**(pydantic 검증 + 알 수 없는 액션/`at: s9` 가 문장 수를 넘는지/`goto` 대상 섹션 존재/derive 조각 누락 등을 세그먼트·액션 위치와 함께 표시), **LaTeX 검사**(모든 수식을 미리 컴파일) |
| 렌더 | **선택 세그먼트 렌더**(그 부분만 480p 로 빠르게) / **프리뷰 렌더** / **최종 렌더**(1080p + 21항목 자동 검증). 진행 로그를 실시간으로 보여 주고 중지 가능. 프로젝트당 한 작업만 실행 |
| 결과 | 오른쪽 패널에서 **영상 재생**, **스토리보드**, **검증 리포트**(PASS/FAIL 표), **타임라인**(세그먼트·문장별 실제 시각), 빌드 **로그** |

REST API (`explainer/studio/server.py`)는 그대로 스크립트에서도 쓸 수 있습니다: `GET/POST /api/projects`, `GET/PUT /api/projects/{id}`, `POST …/validate`, `GET …/timing`, `POST …/build`, `GET /api/jobs/{id}?offset=`, `POST /api/tts`, `GET /api/actions`, `POST /api/yaml/format|parse`. 26학년도 수능 22번 데모는 이 API 로 저장(`PUT`)→검증→프리뷰 빌드→문장 타이밍(`/timing`)을 보고 `at` 재조정→최종 빌드 순서로 만들었습니다. 테스트: `tests/test_studio.py`(API 라운드트립·검사·빌드 작업·YAML 포맷).

## 4. 시나리오 DSL

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
- 표현식 안에서 앞서 `plot` 한 그래프 id 를 함수로 부를 수 있고(`"7*f(x)"`), 조건식으로 조각 함수를 만들 수 있습니다(`"-f(x) if f(x) >= 0 else 7*f(x)"`). 뾰족점이 있는 그래프는 `smooth: false` 로 그립니다.

### 액션 (일부)

| 분류 | 액션 |
|---|---|
| 카드/전환 | `title_card`, `end_card`, `section`, `clear`, `wait`, `caption` |
| 문제/보드 | `problem`(한글+수식 전문, `lines:` 로 줄별 렌더), `problem_focus`(읽는 줄만 밝게 + 포인터 바), `problem_dock`(보드 헤더로 축소), `board`, `board_write`, `board_replace`, `board_highlight`, `board_clear`, `board_title` |
| 그래프 | `axes`(등축 자동, `equal_aspect: false` 가능), `plot`(y 범위 밖 자동 클리핑, `smooth`), `line`, `vline`, `point`(좌표는 `pos`), `points`, `polygon`, `segment`, `arrow`, `guides`, `label` |
| 기하 연출 | `translate_copy`(평행이동 복사), `reflect`(직선 대칭이동 + 수선/직각 표시) |
| 강조 | `highlight`(indicate/flash/circumscribe/pulse), `dim`/`undim`(stroke·fill 원본 비율 유지), `fade`, `answer` |
| 확장 | `custom` → 프로젝트 폴더의 `hooks.py` 함수 호출 (26 수능 22번: `swap_then_scale`(곡선과 점을 y=x 대칭 → 원점 중심 확대) / 22번: `sliding_chord`, `ghost_translate` / 21번: `corner_tangents`, `sweep_param` / 2번: `secant_to_tangent`(할선→접선, 기울기 판독) / 3번: `term_line`, `term_hops`, `term_value`(항 번호 줄과 공차 호) / 4번: `piecewise_gap`(a 슬라이더로 틈이 닫히는 순간)) |
| 칠판 전용 | `goto`(섹션으로 카메라 이동 — 도중 살짝 줌아웃, 첫 방문이면 제목 판서), `write`(커서 위치에 손글씨로 한 줄씩; `ko`, `text`, `box`/`underline`, `space`), `camera`(`pos`/`focus`/`ids` 줌인, `sections` 범위 줌아웃, `reset`), `space`, **`derive` / `step`**(식 전개, 아래) |
| 5지선다 | `problem` 의 `choices: [...]` 로 ①~⑤ 보기 줄을 쓰고, `answer` 의 `choice: n` 으로 카메라가 문제로 돌아가 보기에 분필 동그라미를 친다 |

### 식 전개 애니메이션 (`derive` / `step`)

학생이 "어느 항이 어디서 왔는지"를 눈으로 따라갈 수 있도록, 식의 각 줄을 **조각(parts)** 으로 쓰고 이전 줄과 조각을 자동으로 짝지어 애니메이션합니다.

```yaml
- do: derive
  id: d
  steps:
    - {parts: ["2^{\\frac32}", "\\times", "4^{-\\frac12}"]}                          # 첫 줄: 그대로 판서
    - {parts: ["=", "2^{\\frac32}", "\\times", "\\left(2^{2}\\right)^{-\\frac12}"],  # 같은 줄에 이어 쓰고
       why: "$4=2^{2}$ 으로 밑을 통일"}                                              # (∵ 이유) 메모
    - {parts: ["=", "2^{\\frac32}", "\\times", "2^{-1}"], why: "$(a^m)^n=a^{mn}$"}     # 등호를 세로로 맞춰 다음 줄
    - {parts: ["=", "2^{\\frac12}"], box: true, pulse: true}                           # 결과 상자 + 펄스
- do: step                                                                        # 나중 세그먼트에서 단계를 더할 때 (내레이션 at 동기화)
  of: d
  at: s2
  parts: ["=", "\\sqrt2"]
```

| 조각의 운명 | 애니메이션 |
|---|---|
| 이전 줄과 **같은 문자열** | 그 자리에서 새 자리로 미끄러져 내려온다 (TransformFromCopy) |
| 같은 문자열인데 **등호 반대편**으로 갔다 (이항) | 호를 그리며 등호를 건너가고, 새로 생긴 부호(`+`/`-`)는 강조색 |
| **바뀐 조각** | 이전 줄의 출처가 분필 상자로 강조된 뒤, 그 자리에서 날아와 변형된다 (강조색). 출처가 여럿이면 하나로 합쳐진다 |
| **완전히 새 조각** | 강조색 손글씨로 쓴다 |
| `from: {"2^{2}": "x^{2}"}` | 대입처럼 문자열이 다른 조각을 명시적으로 짝짓는다 (한 출처를 여러 자리에 재사용). 값이 목록이면 여러 출처가 한 조각으로 합쳐진다 (`{"10": ["14", "4"]}`) |
| `focus` / `new` | 자동 매칭을 덮어써 출처/새 조각을 지정 |
| `cancel: ["a_7", 5]` | 문자열 또는 인덱스로 조각에 취소선 (소거) |
| `why` | 식 오른쪽의 '이유 칸'에 `(∵ …)` 로 정렬해 적는다 (한글+수식, 자리가 없으면 아래 오른쪽) |
| `same_line` | `auto`(첫 줄에 `=` 가 없으면 이어 쓰기) / `true` / `false` |
| `at` / `hold` / `cancel_at` | 내레이션 문장 표식(`s3`)에 맞춰 단계 시작 / 출처 상자만 먼저 짚어 두고 이 문장부터 움직이기 / 취소선을 이 문장에서 |

한 단계는 **두 박자**로 움직입니다: (A) 출처에 분필 상자가 그려지고 그대로인 조각이 먼저 미끄러져 내려와 뼈대(`= … × …`)를 만든 뒤, (B) 바뀐 조각이 상자에서 날아와 빈자리에 들어갑니다. 이전 단계의 강조색은 다음 단계에서 기본색으로 돌아가므로 **지금 바뀐 조각만** 색이 있습니다. `= …` 로 이어지는 연쇄 등식에서는 앞줄의 좌변은 출처로 잡지 않습니다. 단계별 `run_time`(기본 2.0)으로 속도를 조절하고, `at: s3` 로 내레이션 문장에 맞춥니다. 매칭 규칙은 순수 함수 `plan_match` 로 분리되어 `tests/test_derive.py` 에서 검사합니다.

### 칠판 스타일 레이아웃

```yaml
meta:   { style: chalkboard, background: "#101614" }
layout:
  chalk:
    board_color: "#24493a"
    line_scale: 0.7
    sections:                                  # 왼쪽→오른쪽으로 이어지는 칠판 칸
      - {id: title,   layout: full}
      - {id: problem, layout: full,  title: "문제"}
      - {id: sol1,    layout: split, title: "풀이 1 · 조건 (가)"}   # split = 왼쪽 그림 + 오른쪽 판서
```

- 섹션 한 칸이 카메라 뷰 하나(폭 14.2 ≒ 16:9 프레임). `axes` 는 현재 섹션의 그림 영역에 자동 배치되고, `write`/`problem`/`answer`/`end_card` 는 판서 커서를 따라 아래로 이어 쓴다.
- `caption` 은 카메라 프레임에 고정된 손글씨 메모(줌인 중에도 같은 자리), `goto` 시 자동으로 지워진다.
- 칠판 질감은 PIL 로 생성해 캐시하고 섹션별 타일로 얹는다. 카메라 줌 시 타일의 보이는 부분만 리샘플링하도록 `ChalkCamera` 가 이미지 렌더링을 최적화한다.

## 5. 자동 검증 (`explainer verify`)

| 항목 | 내용 |
|---|---|
| 컨테이너 | 해상도/fps/코덱, yuv420p, 오디오 트랙, **오디오·비디오 길이 일치** |
| 동기화 | 세그먼트 시각 단조 증가, **각 세그먼트 길이 ≥ 내레이션 길이(잘림 없음)**, 발화 비율 |
| 자막 | 겹침 없음, 시간 범위, 줄 길이(≤34자), 모든 문장 포함 |
| 프레임 | 검은/빈 프레임 없음, 화면 변화 존재, 선명도(라플라시안 분산), 콘텐츠 존재 |
| 스토리보드 | 세그먼트별 대표 프레임 + 내레이션 콘택트 시트 `storyboard.png` (`explainer storyboard out_dir`) |
| 오디오 | 통합 라우드니스(-16 LUFS 목표), 트루피크(클리핑 없음), 긴 무음 없음 |

수학적 내용은 sympy 로 증명합니다: `tests/test_math_q01_q04.py`(1~4번의 모든 전개 단계가 서로 같은 값인지, 이항·대입 단계, 보기 번호), `tests/test_math_q22.py`(포물선 평행이동 (1,−1), 현 기울기 일차식, 대칭축 y=x−1/4 에 대한 A↔D·B↔C 대칭, 직선 y=x+3/4 와의 교점, a³=81/16, p+q=97), `tests/test_math_suneung_calc30.py`(26 수능 미적분 30번: 조건에서 후보 가지, 증가 조건으로 선택, x=±1 에서 C¹ 연결, 직선 대칭이동, 기울기별 교점 개수 1/1/1/3, k_b ln k_b=2 와 접점, 정답 11), `tests/test_math_suneung22.py`(26 수능 22번: log 조건 ⇔ 2^{4b−1}=4a+1, (2b,2a)∈지수함수, k=2 의 유일성(볼록), 연립 → a=63/4, b=7/4, ab=441/16, p+q=457), `tests/test_math_q21.py`(f'(s)=(s−r)², g 의 뾰족점은 s 하나·기울기 변화 −8(s−r)², |w| 의 뾰족점 +2|w'(t)|, a∈{1,2,3}, 각 경우의 f(0), h 의 미분가능성, 최댓값×최솟값 = 12).

## 6. 구조

```
explainer/
  script/    models.py(pydantic DSL) · loader.py(YAML, safe_eval)
  narration/ tts.py(edge-tts, 문장 타이밍, 캐시) · timeline.py
  render/    theme.py(색·폰트·xelatex 템플릿) · board.py(풀이 보드) · chalk.py(칠판 캔버스·판서·카메라) · derive.py(식 전개: 조각 매칭·이동·변형·이유 메모) · scene.py(세그먼트 실행 루프, MovingCamera) · actions.py(액션 라이브러리)
  compose/   subtitles.py(SRT/ASS, 긴 문장 분할) · mux.py(ffmpeg: 자막 번인, loudnorm, apad)
  verify/    checks.py(자동 검증)
  studio/    server.py(FastAPI REST) · jobs.py(빌드 작업·로그) · yamlio.py(정렬된 YAML 저장·히스토리·새 프로젝트 템플릿) · catalog.py(액션 카탈로그) · static/(편집기 UI)
  lint.py · pipeline.py · cli.py
projects/2027_sep_q01..q04/  project.yaml (· hooks.py)   — 식 전개 중심의 짧은 강의
projects/2027_sep_q22/  project.yaml · hooks.py
projects/2027_sep_q21/  project.yaml(칠판) · project_panel.yaml(패널) · hooks.py
projects/2026_suneung_q22/  project.yaml · hooks.py(swap_then_scale)   — Studio 로 제작한 실전 데모
tests/
```

### 구현 메모
- Manim 캐시 재사용 시 `Scene.add_sound` 가 소리를 버리는 문제(`skip_animations`)를 피하기 위해 파일 라이터에 직접 오디오를 삽입합니다.
- 오디오는 마지막 내레이션에서 끝나므로 `apad` + `-shortest` 로 영상 길이에 맞춥니다.
