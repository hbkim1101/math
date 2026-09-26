"""액션 카탈로그: 액션 함수의 시그니처와 docstring 을 편집기에서 쓸 수 있는 형태로 정리한다."""

from __future__ import annotations

import inspect
from typing import Any

from ..render.actions import REGISTRY

CATEGORIES: dict[str, list[str]] = {
    "카드·전환": ["title_card", "end_card", "section", "wait", "clear", "fade", "dim", "undim", "highlight"],
    "문제": ["problem", "problem_focus", "problem_dock", "answer", "caption"],
    "칠판 판서": ["goto", "write", "space", "camera"],
    "식 전개": ["derive", "step"],
    "그래프": ["axes", "plot", "line", "vline", "point", "points", "polygon", "segment", "arrow", "guides",
             "translate_copy", "reflect", "label"],
    "보드(panel 스타일)": ["board_init", "board_write", "board_replace", "board_highlight", "board_clear", "board_title"],
    "사용자 정의": ["custom"],
}

# 자주 쓰는 액션의 시작 템플릿 (새 액션 추가 시 채워 넣는 값)
TEMPLATES: dict[str, dict[str, Any]] = {
    "title_card": {"title": "제목", "subtitle": "부제", "tag": "수학Ⅰ"},
    "goto": {"section": "sol", "run_time": 1.6},
    "problem": {"title": "1. [2점]", "lines": ["$x^{2}$의 값은?"], "choices": ["1", "2", "3", "4", "5"]},
    "problem_focus": {"at": "s2", "index": 1},
    "write": {"tex": "$x=1$", "ko": True},
    "caption": {"text": "설명"},
    "derive": {"id": "d", "steps": [{"parts": ["x", "=", "1"]}, {"parts": ["=", "1"], "why": "이유"}]},
    "step": {"of": "d", "parts": ["=", "2"], "why": "이유"},
    "answer": {"choice": 1},
    "axes": {"run_time": 0.9, "equal_aspect": False},
    "plot": {"id": "f", "expr": "x**2", "color": "q1", "label": "y=x^{2}", "run_time": 1.2},
    "point": {"id": "P", "pos": [1, 1], "label": "P"},
    "camera": {"focus": "d", "width": 7.0},
    "custom": {"fn": "my_hook"},
}

DOC_FALLBACK: dict[str, str] = {
    "fade": "등록된 id 들을 서서히 사라지게(out) / 나타나게 한다",
    "title_card": "제목 카드 (제목·부제·태그)",
    "wait": "지정한 초만큼 기다린다",
    "arrow": "두 점 a→b 화살표 (label 가능)",
    "axes": "좌표평면 그리기 (x_range/y_range, equal_aspect)",
    "polygon": "점 목록으로 다각형 (fill_opacity)",
    "segment": "두 점을 잇는 선분",
    "board_clear": "보드 내용을 지운다 (panel 스타일)",
    "board_highlight": "보드의 한 줄을 강조 (panel 스타일)",
    "board_replace": "보드의 한 줄을 다른 식으로 바꾼다 (panel 스타일)",
    "board_title": "보드 제목을 바꾼다 (panel 스타일)",
}

DOCS_EXTRA: dict[str, str] = {
    "derive": "steps 의 각 항목: parts(조각 목록), why(이유), from(대입 매핑), focus/new, cancel, box, pulse, at, hold, cancel_at, run_time",
    "step": "이미 만든 derive 에 단계를 더한다. parts 외 옵션은 derive.steps 항목과 같다",
    "custom": "프로젝트 폴더의 hooks.py 에 정의한 함수 fn 을 호출한다. 나머지 키는 함수 인자",
}


def _default_repr(v: Any) -> Any:
    if v is inspect.Parameter.empty:
        return None
    if isinstance(v, (int, float, str, bool)) or v is None:
        return v
    return repr(v)


def _annotation_repr(p: inspect.Parameter) -> str:
    a = p.annotation
    if a is inspect.Parameter.empty:
        return ""
    return getattr(a, "__name__", None) or str(a).replace("typing.", "")


def build_catalog() -> list[dict[str, Any]]:
    """[{name, category, doc, params: [{name, default, required, type}], template}]"""
    cat_of = {n: c for c, names in CATEGORIES.items() for n in names}
    items: list[dict[str, Any]] = []
    for name, fn in sorted(REGISTRY.items()):
        sig = inspect.signature(fn)
        params = []
        for pname, p in list(sig.parameters.items())[1:]:      # scene 제외
            if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            params.append({
                "name": pname,
                "default": _default_repr(p.default),
                "required": p.default is inspect.Parameter.empty,
                "type": _annotation_repr(p),
            })
        doc = inspect.getdoc(fn) or ""
        first = doc.strip().splitlines()[0] if doc.strip() else DOC_FALLBACK.get(name, "")
        items.append({
            "name": name,
            "category": cat_of.get(name, "기타"),
            "doc": first,
            "doc_full": doc + ("\n\n" + DOCS_EXTRA[name] if name in DOCS_EXTRA else ""),
            "params": params,
            "template": TEMPLATES.get(name, {}),
        })
    order = list(CATEGORIES) + ["기타"]
    items.sort(key=lambda it: (order.index(it["category"]), it["name"]))
    return items
