# math

수능 수학 **그래프·핵심 아이디어 중심** 자동 시각화 해설

## 설계 원칙

- 텍스트 슬라이드 ❌ → **그래프·애니메이션·기하直관** ✅
- Manim `Axes`, `plot`, `ValueTracker`로 **개념이 보이게**
- 하단 캡션만 짧게, 본문은 **시각 요소**가 전달

## 현재 시각화

| 문항 | 시각화 내용 | 정답 |
|------|------------|------|
| 2번 | f(x) 곡선 + x=1 접선 기울기 | ④ 16 |
| 4번 | 조각함수 + a 변화 → x=1 연속 | ③ 3 |
| 30번 | h(x) 그래프, 교점 애니메이션, g(m) 계단 | 11 |
| 1,3번 | (텍스트) → 그래프화 예정 | 1, 14 |

### 실행

```bash
source .venv/bin/activate
pip install -r requirements.txt

# 그래프 중심 렌더 (2, 4, 30번 등)
PYTHONPATH=. python scripts/render_viz.py
```

### 구조

```
src/renderer/graph_helpers.py   # h(x), 교점, 계단그래프 등 수학 그래프 API
src/scenes/calc_q30.py          # 30번 그래프 Scene
src/scenes/q04_viz.py           # 4번 연속성 Scene
src/scenes/q02_viz.py           # 2번 접선 Scene
scripts/render_viz.py           # 그래프 Scene 일괄 렌더
docs/videos/                    # 모바일 미리보기용 MP4
```
