"""시나리오(프로젝트) DSL의 데이터 모델.

YAML 파일 하나가 영상 하나에 대응한다.

    meta:      제목, 목소리, 해상도 등 전역 설정
    params:    수식/좌표에서 쓸 수 있는 상수 (문자열 표현식 허용)
    colors:    이름 → 색상 (t2c 등에서 재사용)
    layout:    좌표평면/보드 패널 배치
    segments:  내레이션 한 덩어리 + 그 동안 실행할 액션 목록
"""

from __future__ import annotations

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

Number = Union[int, float]


class Meta(BaseModel):
    id: str
    title: str
    subtitle: str = ""
    voice: str = "ko-KR-InJoonNeural"
    rate: str = "+0%"
    pitch: str = "+0Hz"
    resolution: Literal["480p", "720p", "1080p", "1440p", "2160p"] = "1080p"
    fps: int = 30
    subtitles: Literal["none", "soft", "burn"] = "burn"
    background: str = "#0b0f19"
    segment_pad: float = 0.45  # 내레이션이 끝난 뒤 다음 세그먼트까지의 여백(초)
    intro_silence: float = 0.6
    outro_silence: float = 1.0
    loudnorm: bool = True
    # panel: 그래프 + 오른쪽 보드 패널(지우고 다시 쓰는 방식)
    # chalkboard: 하나의 큰 칠판에 계속 써 나가며 카메라가 줌인/아웃으로 따라가는 강의 방식
    style: Literal["panel", "chalkboard"] = "panel"


class ChalkLayout(BaseModel):
    """chalkboard 스타일에서 칠판(캔버스) 섹션 배치."""

    board_color: str = "#24493a"
    section_width: float = 14.2   # 한 섹션 = 카메라가 꽉 차게 보는 폭 (16:9 → 높이 약 8)
    section_height: float = 8.0
    gap: float = 1.6              # 섹션 사이 간격
    graph_width: float = 7.2      # split 섹션에서 왼쪽 그림 영역 폭
    margin: float = 0.55
    line_gap: float = 0.26
    line_scale: float = 0.72
    bottom_reserve: float = 1.1   # 화면 하단 자막 띠에 판서가 가리지 않도록 비워 두는 높이
    texture: bool = True
    sections: list[dict[str, Any]] = Field(default_factory=list)  # [{id, title, layout: split|full, graph_width}]


class GraphLayout(BaseModel):
    x_range: list[Number] = Field(default_factory=lambda: [-1, 4, 1])
    y_range: list[Number] = Field(default_factory=lambda: [-1, 4, 1])
    width: float = 8.0
    height: float = 5.9
    center: list[Number] = Field(default_factory=lambda: [-2.9, 0.35])
    axis_color: str = "#8b93a7"
    grid: bool = True
    numbers: bool = True


class BoardLayout(BaseModel):
    width: float = 5.7
    height: float = 6.5
    center: list[Number] = Field(default_factory=lambda: [4.05, 0.3])
    title: str = "풀이"
    line_scale: float = 0.72
    max_lines: int = 9
    background: str = "#111827"
    border: str = "#243049"


class Layout(BaseModel):
    graph: GraphLayout = Field(default_factory=GraphLayout)
    board: BoardLayout = Field(default_factory=BoardLayout)
    chalk: ChalkLayout = Field(default_factory=ChalkLayout)


class Action(BaseModel):
    """세그먼트 안에서 실행되는 애니메이션 한 단위.

    `do` 는 액션 이름이고 나머지 필드는 액션별 파라미터다.
    `at` 는 세그먼트 시작 기준 실행 시각. 숫자(초) 또는 "s2"(2번째 문장 시작)처럼 문장 인덱스를 지정할 수 있다.
    """

    model_config = {"extra": "allow"}

    do: str
    at: Optional[Union[Number, str]] = None
    run_time: Optional[float] = None

    @property
    def params(self) -> dict[str, Any]:
        base = self.model_dump(exclude={"do", "at", "run_time"})
        extra = dict(self.model_extra or {})
        base.update(extra)
        return base


class Segment(BaseModel):
    id: str
    narration: str = ""
    actions: list[Action] = Field(default_factory=list)
    pad: Optional[float] = None  # meta.segment_pad 덮어쓰기
    voice: Optional[str] = None
    rate: Optional[str] = None
    subtitle: Optional[str] = None  # 자막을 내레이션과 다르게 표시하고 싶을 때

    @field_validator("narration")
    @classmethod
    def _strip(cls, v: str) -> str:
        return " ".join(v.split())


class Project(BaseModel):
    meta: Meta
    params: dict[str, Union[Number, str]] = Field(default_factory=dict)
    colors: dict[str, str] = Field(default_factory=dict)
    t2c: dict[str, str] = Field(default_factory=dict)  # MathTex 토큰 → 색상 이름/코드
    layout: Layout = Field(default_factory=Layout)
    segments: list[Segment]
    source_path: Optional[str] = None

    @model_validator(mode="after")
    def _unique_ids(self) -> "Project":
        ids = [s.id for s in self.segments]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            raise ValueError(f"segment id 중복: {sorted(dup)}")
        if not self.segments:
            raise ValueError("segments 가 비어 있습니다")
        return self

    def resolve_color(self, name: str | None) -> str | None:
        if name is None:
            return None
        return self.colors.get(name, name)
