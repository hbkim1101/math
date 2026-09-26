"""색상·폰트·LaTeX 템플릿 등 시각 테마."""

from __future__ import annotations

from dataclasses import dataclass, field

from manim import TexTemplate

KOREAN_FONT = "Noto Sans CJK KR"

# xelatex + kotex: 한글과 수식을 한 문장에 섞어 조판한다.
KO_TEX_TEMPLATE = TexTemplate(
    tex_compiler="xelatex",
    output_format=".xdv",
    documentclass=r"\documentclass[preview]{standalone}",
    preamble=r"""
\usepackage{amsmath,amssymb,mathtools}
\usepackage{fontspec}
\usepackage{kotex}
\setmainhangulfont{Noto Sans CJK KR}
\setsanshangulfont{Noto Sans CJK KR}
\setlength{\parindent}{0pt}
% 한글 어절 중간에서 줄이 바뀌지 않게 (xetexko 기본은 글자 단위 줄바꿈 허용)
\XeTeXlinebreakpenalty=10000
\emergencystretch=3em
""",
)

# 수식 전용(pdflatex, 빠름). Manim 기본 템플릿에 몇 개 패키지를 추가.
MATH_TEX_TEMPLATE = TexTemplate()
MATH_TEX_TEMPLATE.add_to_preamble(r"\usepackage{amssymb,mathtools}")


@dataclass
class Theme:
    background: str = "#0b0f19"
    text: str = "#e5e7eb"
    muted: str = "#9aa3b5"
    axis: str = "#8b93a7"
    grid: str = "#1e293b"
    grid_faded: str = "#131c2e"
    panel: str = "#111827"
    panel_border: str = "#243049"
    accent: str = "#58c4dd"
    highlight: str = "#fde047"
    palette: dict[str, str] = field(
        default_factory=lambda: {
            "exp": "#ff8a65",  # y = a^x
            "log": "#4fc3f7",  # 로그
            "q1": "#a3e635",  # 첫 번째 포물선
            "q2": "#c084fc",  # 두 번째 포물선
            "point": "#fde047",
            "rect": "#f8fafc",
            "axis_sym": "#f472b6",
            "guide": "#64748b",
            "ok": "#34d399",
            "warn": "#fb7185",
        }
    )

    # 폰트/조판 템플릿 (칠판 테마는 손글씨 폰트로 바꾼다)
    font: str = KOREAN_FONT
    title_font: str = KOREAN_FONT
    ko_template: TexTemplate = field(default_factory=lambda: KO_TEX_TEMPLATE)
    chalk: bool = False  # True 면 배경 사각형/패널 없이 분필 느낌으로 그린다

    _ATTR_COLORS = ("text", "muted", "axis", "grid", "panel", "accent", "highlight", "background")

    def color(self, name: str | None, default: str | None = None) -> str | None:
        """팔레트 이름 → 색상. 팔레트에 없으면 테마 속성(accent, highlight, ...), 그것도 없으면 그대로(hex 등)."""
        if name is None:
            return default
        if name in self.palette:
            return self.palette[name]
        if name in self._ATTR_COLORS:
            return getattr(self, name)
        return name
