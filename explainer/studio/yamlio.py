"""YAML 읽기/쓰기 + 저장 이력.

편집기의 폼에서 만든 dict 를 기존 프로젝트 파일과 비슷한 모양으로 덤프한다:
짧은 액션은 한 줄 flow 스타일 `{do: goto, section: sol}`, 긴 내레이션은 접힌 블록 `>`.
"""

from __future__ import annotations

import datetime as _dt
import shutil
from pathlib import Path
from typing import Any

import yaml

HISTORY_KEEP = 30


class _Dumper(yaml.SafeDumper):
    pass


def _is_short_flow(d: dict) -> bool:
    if not d or len(d) > 8:
        return False
    for k, v in d.items():
        if isinstance(v, (dict, list)):
            if isinstance(v, list) and all(isinstance(x, (int, float, str, bool)) or x is None for x in v) and len(v) <= 6:
                continue
            return False
        if isinstance(v, str) and (len(v) > 60 or "\n" in v):
            return False
    return sum(len(str(k)) + len(str(v)) for k, v in d.items()) < 110


def _repr_dict(dumper: _Dumper, data: dict):
    # 액션처럼 짧은 매핑은 한 줄로
    flow = "do" in data and _is_short_flow(data)
    return dumper.represent_mapping("tag:yaml.org,2002:map", data, flow_style=flow)


def _repr_str(dumper: _Dumper, data: str):
    # 긴 한 줄 문장(내레이션)은 접힌 블록 `>` 로 — 앞뒤 공백/줄바꿈이 있으면 PyYAML 이 알아서 인용한다
    if len(data) > 100 and data == data.strip() and "\n" not in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=">")
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|" if data.endswith("\n") and data.strip() == data.rstrip("\n") else None)
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def _repr_list(dumper: _Dumper, data: list):
    flow = bool(data) and len(data) <= 8 and all(
        (isinstance(x, (int, float, bool)) or x is None or (isinstance(x, str) and len(x) <= 24)) for x in data
    )
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=flow)


_Dumper.add_representer(dict, _repr_dict)
_Dumper.add_representer(str, _repr_str)
_Dumper.add_representer(list, _repr_list)


TOP_ORDER = ["meta", "params", "colors", "t2c", "layout", "segments"]


def dump_project(doc: dict[str, Any]) -> str:
    ordered = {k: doc[k] for k in TOP_ORDER if k in doc}
    ordered.update({k: v for k, v in doc.items() if k not in ordered})
    chunks = []
    for k, v in ordered.items():
        chunks.append(yaml.dump({k: v}, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=140))
    return "\n".join(chunks)


def parse_yaml(text: str) -> dict[str, Any]:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("최상위는 매핑이어야 합니다 (meta:, segments: …)")
    return data


def history_dir(project_yaml: Path) -> Path:
    return project_yaml.parent / ".history"


def snapshot(project_yaml: Path) -> Path | None:
    """저장 직전의 파일을 .history/ 에 보관한다 (최근 HISTORY_KEEP 개 유지)."""
    if not project_yaml.exists():
        return None
    hd = history_dir(project_yaml)
    hd.mkdir(exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dst = hd / f"{stamp}.yaml"
    shutil.copy2(project_yaml, dst)
    olds = sorted(hd.glob("*.yaml"))
    for old in olds[:-HISTORY_KEEP]:
        old.unlink(missing_ok=True)
    return dst


def list_history(project_yaml: Path) -> list[dict[str, Any]]:
    hd = history_dir(project_yaml)
    if not hd.exists():
        return []
    out = []
    for p in sorted(hd.glob("*.yaml"), reverse=True):
        out.append({"name": p.stem, "size": p.stat().st_size,
                    "time": _dt.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")})
    return out


NEW_PROJECT_TEMPLATE = """\
meta:
  id: {id}
  title: {title}
  subtitle: ""
  voice: ko-KR-InJoonNeural
  resolution: 1080p
  fps: 30
  style: chalkboard

params: {{}}

layout:
  chalk:
    line_scale: 1.1
    sections:
      - {{id: title, title: "", layout: full}}
      - {{id: problem, title: 문제, layout: full}}
      - {{id: sol, title: 풀이, layout: full}}

segments:
  - id: intro
    narration: >
      여기에 첫 내레이션을 씁니다. 문장 단위로 끊어 쓰면 at: s2 처럼 문장에 애니메이션을 맞출 수 있습니다.
    actions:
      - {{do: title_card, title: "{title}", subtitle: "부제", tag: "수학"}}

  - id: read_problem
    narration: >
      문제입니다.
    actions:
      - {{do: goto, section: problem, run_time: 1.4}}
      - do: problem
        title: "1. [2점]"
        lines:
          - "$2^{{2}}\\\\times 2^{{3}}$의 값은?"
        choices: ["8", "16", "32", "64", "128"]

  - id: solve
    narration: >
      밑이 같은 거듭제곱의 곱은 지수를 더합니다. 2 더하기 3은 5, 2의 5제곱은 32입니다.
    actions:
      - {{do: goto, section: sol, run_time: 1.6}}
      - do: derive
        id: d
        steps:
          - {{parts: ["2^{{2}}", "\\\\times", "2^{{3}}"]}}
          - {{parts: ["=", "2^{{2+3}}"], why: "$a^{{m}}\\\\times a^{{n}}=a^{{m+n}}$", at: s2}}
          - {{parts: ["=", "32"], box: true, pulse: true}}

  - id: answer
    narration: >
      정답은 3번, 32입니다.
    actions:
      - {{do: answer, choice: 3}}
"""


def new_project_text(pid: str, title: str) -> str:
    return NEW_PROJECT_TEMPLATE.format(id=pid, title=title)
