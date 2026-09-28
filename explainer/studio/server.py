"""Studio 백엔드 (FastAPI).

    GET  /                                 편집기 (정적 페이지)
    GET  /api/projects                     프로젝트 목록
    POST /api/projects                     새 프로젝트 {id, title}
    GET  /api/projects/{pid}               {yaml, doc, hooks, outputs}
    PUT  /api/projects/{pid}               저장 {yaml} 또는 {doc}
    POST /api/projects/{pid}/validate      {yaml|doc, tex} → 구조/액션/LaTeX 검사 (저장 안 함)
    GET  /api/projects/{pid}/timing        문장별 내레이션 타이밍 (TTS 캐시 사용)
    GET  /api/projects/{pid}/history       저장 이력 / POST …/history/{name}/restore
    POST /api/projects/{pid}/build         {preview, segments, force_tts} → job
    GET  /api/projects/{pid}/outputs       산출물(영상/스토리보드/검증/타임라인) 경로
    GET  /api/jobs/{jid}?offset=N          작업 상태 + 로그 증분 / POST /api/jobs/{jid}/cancel
    GET  /api/actions                      액션 카탈로그
    POST /api/yaml/format                  {doc} → yaml / POST /api/yaml/parse {yaml} → doc
    POST /api/tts                          {text, voice, rate} → mp3 url + 문장 타이밍
"""

from __future__ import annotations

import json
import re
import threading
import webbrowser
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from ..script.models import Project
from .catalog import build_catalog
from .jobs import JobManager
from .yamlio import dump_project, list_history, new_project_text, parse_yaml, snapshot

STATIC = Path(__file__).parent / "static"
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_\-]{1,63}$")


class SaveBody(BaseModel):
    yaml: Optional[str] = None
    doc: Optional[dict[str, Any]] = None


class ValidateBody(SaveBody):
    tex: bool = False


class BuildBody(BaseModel):
    preview: bool = True
    segments: Optional[list[str]] = None
    force_tts: bool = False


class NewProjectBody(BaseModel):
    id: str
    title: str = "새 영상"


class TTSBody(BaseModel):
    text: str
    voice: str = "ko-KR-InJoonNeural"
    rate: str = "+0%"
    pitch: str = "+0Hz"


class DocBody(BaseModel):
    doc: dict[str, Any]


class YamlBody(BaseModel):
    yaml: str


def create_app(root: str | Path = ".") -> FastAPI:
    root = Path(root).resolve()
    projects_dir = root / "projects"
    output_dir = root / "output"
    projects_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    jobs = JobManager(root)

    app = FastAPI(title="Explainer Studio", version="1.0")
    app.state.root = root
    app.state.jobs = jobs

    # ------------------------------------------------------------------ 헬퍼
    def project_yaml(pid: str) -> Path:
        if not ID_RE.match(pid):
            raise HTTPException(400, f"잘못된 프로젝트 id: {pid}")
        p = projects_dir / pid / "project.yaml"
        if not p.exists():
            raise HTTPException(404, f"프로젝트 없음: {pid}")
        return p

    def doc_from_body(body: SaveBody) -> tuple[dict[str, Any], str]:
        if body.yaml is not None:
            doc = parse_yaml(body.yaml)
            return doc, body.yaml
        if body.doc is not None:
            return body.doc, dump_project(body.doc)
        raise HTTPException(400, "yaml 또는 doc 이 필요합니다")

    def check_doc(doc: dict[str, Any], tex: bool = False, source: Path | None = None) -> dict[str, Any]:
        """구조(pydantic) → 액션/섹션/at 검사(원본 dict 기준, 구조 오류가 있어도 계속) → (선택) LaTeX 사전 컴파일."""
        from ..render.actions import REGISTRY
        from ..script.loader import resolve_params
        errors: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        project: Project | None = None
        try:
            project = Project.model_validate(doc)
            if source is not None:
                project.source_path = str(source)
        except ValidationError as e:
            for err in e.errors():
                errors.append(_friendly_pydantic(err, doc))
        try:
            resolve_params(doc.get("params") or {})
        except Exception as e:  # noqa: BLE001
            errors.append({"where": "params", "msg": f"상수 값을 계산할 수 없습니다: {e}",
                           "hint": "⚙ 영상 설정 › 상수에서 식의 철자와 순서를 확인하세요."})

        style = (doc.get("meta") or {}).get("style", "panel")
        sections = ((doc.get("layout") or {}).get("chalk") or {}).get("sections") or []
        section_ids = {s.get("id") for s in sections if isinstance(s, dict)}
        segments = doc.get("segments") or []
        # 구조 오류가 있으면 pydantic 은 중복 검사까지 가지 않으므로 여기서 한 번에 알려 준다
        if not any("장면 이름 중복" in e["msg"] for e in errors):
            seen: dict[str, int] = {}
            for si, seg in enumerate(segments):
                sid = str(seg.get("id")) if isinstance(seg, dict) else None
                if sid is None:
                    continue
                if sid in seen:
                    errors.append({"where": f"segments[{si}:{sid}].id",
                                   "msg": f"장면 이름 중복 — ‘{sid}’ 은(는) {seen[sid] + 1}번째 장면과 이름이 같습니다.",
                                   "hint": "장면마다 다른 이름을 쓰세요 (장면 편집기 맨 위의 이름 칸)."})
                else:
                    seen[sid] = si
        for si, seg in enumerate(segments):
            if not isinstance(seg, dict):
                errors.append({"where": f"segments[{si}]", "msg": "세그먼트는 매핑이어야 합니다"})
                continue
            sid = seg.get("id", "?")
            n_sent = len(_sentences_for(doc, seg, output_dir)["sentences"])
            acts = seg.get("actions") or []
            for ai, act in enumerate(acts):
                if not isinstance(act, dict) or "do" not in act:
                    errors.append({"where": f"segments[{si}:{sid}].actions[{ai}]", "msg": "액션에는 do: 가 필요합니다"})
                    continue
                where = f"segments[{si}:{sid}].actions[{ai}:{act['do']}]"
                if act["do"] not in REGISTRY:
                    errors.append({"where": where, "msg": f"‘{act['do']}’ 라는 동작은 없습니다.",
                                   "hint": "카드를 열어 ‘종류’ 에서 동작을 다시 고르세요."})
                at = act.get("at")
                if isinstance(at, str) and at.startswith("s"):
                    try:
                        k = int(at[1:])
                        if k > max(n_sent, 1):
                            warnings.append({"where": where, "msg": f"시작 시점이 {k}번째 문장({at})인데, 대본에는 문장이 {n_sent}개뿐입니다.",
                                             "hint": "‘시작 시점’ 에서 대본에 있는 문장을 고르거나, 대본에 문장을 더 쓰세요."})
                    except ValueError:
                        errors.append({"where": where, "msg": f"시작 시점 값 ‘{at}’ 을(를) 알아볼 수 없습니다.",
                                       "hint": "‘시작 시점’ 에서 문장을 고르거나 비워 두세요 (s2 = 2번째 문장, 3.5 = 3.5초)."})
                if act["do"] == "goto" and style == "chalkboard":
                    sec = act.get("section")
                    if sec and sec not in section_ids:
                        errors.append({"where": where, "msg": f"‘{sec}’ 라는 칠판 칸이 없습니다.",
                                       "hint": "⚙ 영상 설정 › 칠판 칸에 이 이름으로 칸을 추가하거나, 카드에서 있는 칸을 고르세요."})
                if act["do"] in ("derive", "step"):
                    steps = act.get("steps") if act["do"] == "derive" else [act]
                    for k, st in enumerate(steps or []):
                        if isinstance(st, dict) and not (st.get("parts") or st.get("tex")):
                            errors.append({"where": f"{where}.steps[{k}]", "msg": f"식 전개 {k + 1}단계에 식이 비어 있습니다.",
                                           "hint": "그 단계의 조각 입력란에 식을 쓰거나 단계를 지우세요."})
            if not seg.get("narration") and not acts:
                warnings.append({"where": f"segments[{si}:{sid}]", "msg": "대본과 동작이 모두 비어 있는 장면입니다.",
                                 "hint": "대본을 쓰거나, 필요 없으면 장면을 삭제하세요."})
        if tex and project is not None and not errors:
            from ..lint import lint_tex
            msgs: list[str] = []
            for t in lint_tex(project, media_dir=output_dir / "_cache" / "lint", log=msgs.append):
                errors.append({"where": "LaTeX", "msg": t,
                               "hint": "메시지에 나온 수식을 찾아 괄호 짝·명령어 철자(\\frac, \\sqrt …)를 확인하세요. 한글이 섞였다면 ‘한글 포함’ 을 켜세요."})
        for item in errors + warnings:
            item.update(_locate(item["where"], doc))
        summary = {
            "segments": len(segments),
            "actions": sum(len(s.get("actions") or []) for s in segments if isinstance(s, dict)),
        }
        return {"ok": not errors, "errors": errors, "warnings": warnings, "summary": summary}

    def outputs_for(pid: str) -> dict[str, Any]:
        def entry(out_id: str) -> dict[str, Any] | None:
            d = output_dir / out_id
            if not d.exists():
                return None
            info: dict[str, Any] = {"dir": f"/output/{out_id}"}
            for name, pat in (("final", f"{out_id}.mp4"), ("preview", f"{out_id}_preview.mp4"),
                              ("storyboard", "storyboard.png"), ("srt", "subtitles.srt")):
                f = d / pat
                if f.exists():
                    info[name] = f"/output/{out_id}/{pat}?v={int(f.stat().st_mtime)}"
            for name in ("verify_report", "timeline", "actions_log"):
                f = d / f"{name}.json"
                if f.exists():
                    try:
                        info[name] = json.loads(f.read_text(encoding="utf-8"))
                    except Exception:  # noqa: BLE001
                        pass
            return info
        return {"full": entry(pid), "partial": entry(pid + "__part")}

    # ------------------------------------------------------------------ 라우트
    @app.get("/api/projects")
    def list_projects():
        items = []
        for p in sorted(projects_dir.glob("*/project.yaml")):
            pid = p.parent.name
            title = pid
            try:
                doc = parse_yaml(p.read_text(encoding="utf-8"))
                title = str(doc.get("meta", {}).get("title", pid))
            except Exception:  # noqa: BLE001
                pass
            outs = outputs_for(pid)["full"] or {}
            items.append({"id": pid, "title": title, "has_final": "final" in outs, "has_preview": "preview" in outs,
                          "running": jobs.running_for(pid) is not None})
        return items

    @app.post("/api/projects")
    def new_project(body: NewProjectBody):
        if not ID_RE.match(body.id):
            raise HTTPException(400, "id 는 영문 소문자/숫자/밑줄/하이픈 2~64자")
        d = projects_dir / body.id
        if d.exists():
            raise HTTPException(409, f"이미 있는 프로젝트: {body.id}")
        d.mkdir(parents=True)
        text = new_project_text(body.id, body.title)
        (d / "project.yaml").write_text(text, encoding="utf-8")
        return {"id": body.id, "yaml": text, "doc": parse_yaml(text)}

    @app.get("/api/projects/{pid}")
    def get_project(pid: str):
        p = project_yaml(pid)
        text = p.read_text(encoding="utf-8")
        try:
            doc = parse_yaml(text)
            parse_error = None
        except Exception as e:  # noqa: BLE001
            doc, parse_error = None, str(e)
        autofix = _autofix(doc, pid)
        hooks = []
        hp = p.parent / "hooks.py"
        if hp.exists():
            hooks = re.findall(r"^def\s+([a-zA-Z_]\w*)\s*\(", hp.read_text(encoding="utf-8"), flags=re.M)
            hooks = [h for h in hooks if not h.startswith("_")]
        sentences = {}
        if isinstance(doc, dict):
            for seg in doc.get("segments") or []:
                if isinstance(seg, dict) and seg.get("id"):
                    sentences[str(seg["id"])] = _sentences_for(doc, seg, output_dir)
        return {"id": pid, "yaml": text, "doc": doc, "parse_error": parse_error, "hooks": hooks, "autofix": autofix,
                "sentences": sentences,
                "outputs": outputs_for(pid), "job": (jobs.running_for(pid) or _NoJob()).to_json()}

    @app.post("/api/projects/{pid}/sentences")
    def sentences(pid: str, body: DocBody):
        """편집 중인 문서의 세그먼트별 문장 경계 (TTS 캐시가 있으면 실제 경계·시각, 없으면 추정)."""
        project_yaml(pid)
        doc = body.doc
        out = {}
        for seg in doc.get("segments") or []:
            if isinstance(seg, dict) and seg.get("id"):
                out[str(seg["id"])] = _sentences_for(doc, seg, output_dir)
        return out

    @app.put("/api/projects/{pid}")
    def save_project(pid: str, body: SaveBody):
        p = project_yaml(pid)
        try:
            doc, text = doc_from_body(body)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, f"YAML 파싱 실패: {e}")
        if _autofix(doc, pid):
            text = dump_project(doc)
        result = check_doc(doc, tex=False, source=p)
        snapshot(p)
        p.write_text(text, encoding="utf-8")
        sentences = {str(seg["id"]): _sentences_for(doc, seg, output_dir)
                     for seg in (doc.get("segments") or []) if isinstance(seg, dict) and seg.get("id")}
        return {"saved": True, "yaml": text, "doc": doc, "check": result, "sentences": sentences}

    @app.post("/api/projects/{pid}/validate")
    def validate_project(pid: str, body: ValidateBody):
        p = project_yaml(pid)
        try:
            doc, _ = doc_from_body(body)
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "errors": [{"where": "YAML", "msg": f"YAML 문법 오류: {e}", "hint": "고급 모드의 YAML 원문에서 들여쓰기와 콜론(:)을 확인하세요.",
                                             **_locate("YAML", {})}], "warnings": [], "summary": {}}
        _autofix(doc, pid)
        return check_doc(doc, tex=body.tex, source=p)

    @app.get("/api/projects/{pid}/timing")
    def timing(pid: str):
        p = project_yaml(pid)
        from ..narration.timeline import build_timeline
        from ..script.loader import load_project
        project = load_project(p)
        tl = build_timeline(project, cache_dir=output_dir / "_cache" / "tts", log=None)
        t = float(project.meta.intro_silence)
        out = []
        for seg in tl.segments:
            item = {"id": seg.id, "start": round(t, 2), "audio": round(seg.audio_duration, 2), "pad": seg.pad,
                    "sentences": []}
            if seg.clip:
                for i, s in enumerate(seg.clip.sentences, 1):
                    item["sentences"].append({"i": i, "text": s.text, "start": round(s.start, 2), "end": round(s.end, 2),
                                              "abs": round(t + s.start, 2)})
                item["audio_url"] = _media_url(seg.clip.audio_path, output_dir)
            t += seg.audio_duration + seg.pad
            item["end"] = round(t, 2)
            out.append(item)
        return {"segments": out, "total": round(t + project.meta.outro_silence, 2)}

    @app.get("/api/projects/{pid}/history")
    def history(pid: str):
        return list_history(project_yaml(pid))

    @app.post("/api/projects/{pid}/history/{name}/restore")
    def restore(pid: str, name: str):
        p = project_yaml(pid)
        src = p.parent / ".history" / f"{name}.yaml"
        if not src.exists() or not re.match(r"^[0-9\-]+$", name):
            raise HTTPException(404, "이력 없음")
        snapshot(p)
        text = src.read_text(encoding="utf-8")
        p.write_text(text, encoding="utf-8")
        return {"restored": name, "yaml": text, "doc": parse_yaml(text)}

    @app.get("/api/projects/{pid}/outputs")
    def outputs(pid: str):
        project_yaml(pid)
        return outputs_for(pid)

    @app.post("/api/projects/{pid}/build")
    def build(pid: str, body: BuildBody):
        p = project_yaml(pid)
        try:
            job = jobs.start(pid, p.relative_to(root), preview=body.preview, segments=body.segments,
                             force_tts=body.force_tts)
        except RuntimeError as e:
            raise HTTPException(409, str(e))
        return job.to_json()

    @app.get("/api/jobs")
    def list_jobs(project: str | None = None):
        return jobs.list(project)

    @app.get("/api/jobs/{jid}")
    def job_status(jid: str, offset: int = 0):
        if jid not in jobs.jobs:
            raise HTTPException(404, "작업 없음")
        text, new_offset = jobs.log_tail(jid, offset)
        return {"job": jobs.jobs[jid].to_json(), "log": text, "offset": new_offset}

    @app.post("/api/jobs/{jid}/cancel")
    def job_cancel(jid: str):
        if jid not in jobs.jobs:
            raise HTTPException(404, "작업 없음")
        return jobs.cancel(jid).to_json()

    @app.get("/api/actions")
    def actions():
        return build_catalog()

    @app.post("/api/yaml/format")
    def yaml_format(body: DocBody):
        return {"yaml": dump_project(body.doc)}

    @app.post("/api/yaml/parse")
    def yaml_parse(body: YamlBody):
        try:
            return {"doc": parse_yaml(body.yaml)}
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, f"YAML 파싱 실패: {e}")

    @app.post("/api/tts")
    def tts(body: TTSBody):
        from ..narration.tts import synthesize_segment
        try:
            clip = synthesize_segment(body.text, voice=body.voice, rate=body.rate, pitch=body.pitch,
                                      cache_dir=output_dir / "_cache" / "tts")
        except Exception as e:  # noqa: BLE001
            raise HTTPException(502, f"TTS 실패: {e}")
        if clip is None:
            raise HTTPException(400, "빈 문장")
        return {"audio_url": _media_url(clip.audio_path, output_dir), "duration": clip.duration,
                "sentences": [{"i": i, "text": s.text, "start": round(s.start, 2), "end": round(s.end, 2)}
                              for i, s in enumerate(clip.sentences, 1)]}

    @app.get("/api/health")
    def health():
        return {"ok": True, "root": str(root)}

    # 산출물/정적 파일
    app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    return app


class _NoJob:
    def to_json(self):
        return None


# ---------------------------------------------------------------------- 검사 결과를 사용자 말로
_META_KO = {
    "id": "프로젝트 ID", "title": "제목", "subtitle": "부제", "voice": "목소리", "rate": "말 속도", "pitch": "음높이",
    "resolution": "해상도", "fps": "fps", "subtitles": "자막", "style": "스타일", "segment_pad": "장면 사이 쉼",
    "intro_silence": "시작 전 무음", "outro_silence": "끝난 뒤 무음", "background": "배경색", "loudnorm": "음량 맞춤",
}
_SEG_KO = {"id": "이름", "narration": "대본", "actions": "동작 목록", "pad": "뒤 여백", "voice": "목소리", "rate": "말 속도", "subtitle": "자막"}
_ACT_KO = {"do": "종류", "at": "시작 시점", "run_time": "길이"}
_TYPE_KO = {str: "글자", int: "숫자", float: "숫자", bool: "켬/끔", list: "목록", dict: "묶음", type(None): "빈 값"}


def _friendly_pydantic(err: dict[str, Any], doc: dict[str, Any]) -> dict[str, Any]:
    """pydantic 오류 하나 → {where, msg, hint, raw}. where 는 _locate 가 알아듣는 형식."""
    loc = [x for x in err.get("loc", ())]
    typ = err.get("type", "")
    inp = err.get("input")
    shown = repr(inp) if not isinstance(inp, (dict, list)) else ("묶음" if isinstance(inp, dict) else "목록")
    kind = _TYPE_KO.get(type(inp), type(inp).__name__)
    ctx = err.get("ctx") or {}
    raw = f"{'.'.join(str(x) for x in loc) or 'project'}: {err.get('msg', '')}"

    # where: segments.3.actions.1.do → segments[3:<id>].actions[1:<do>].do
    where = ".".join(str(x) for x in loc) or "project"
    if loc[:1] == ["segments"] and len(loc) >= 2 and isinstance(loc[1], int):
        segs = doc.get("segments") or []
        seg = segs[loc[1]] if loc[1] < len(segs) and isinstance(segs[loc[1]], dict) else {}
        where = f"segments[{loc[1]}:{seg.get('id', '')}]"
        rest = loc[2:]
        if rest[:1] == ["actions"] and len(rest) >= 2 and isinstance(rest[1], int):
            acts = seg.get("actions") or []
            act = acts[rest[1]] if rest[1] < len(acts) and isinstance(acts[rest[1]], dict) else {}
            where += f".actions[{rest[1]}:{act.get('do', '')}]"
            rest = rest[2:]
        if rest:
            where += "." + ".".join(str(x) for x in rest)

    hint = ""
    if typ == "missing":
        msg = "꼭 있어야 하는 값이 비어 있습니다."
        hint = "값을 입력하세요."
    elif typ == "string_type":
        msg = f"글자여야 하는데 {kind} {shown} 이(가) 들어 있습니다."
        if isinstance(inp, (int, float)):
            hint = "YAML 은 따옴표 없는 2611_22 · 22 같은 값을 숫자로 읽습니다. 따옴표로 감싸 \"2611_22\" 처럼 쓰세요."
    elif typ in ("int_type", "int_parsing", "int_from_float"):
        msg = f"정수여야 하는데 {shown} 이(가) 들어 있습니다."
        hint = "소수점·글자 없이 숫자만 쓰세요 (예: 30)."
    elif typ in ("float_type", "float_parsing"):
        msg = f"숫자여야 하는데 {shown} 이(가) 들어 있습니다."
        hint = "숫자만 쓰세요 (예: 0.5)."
    elif typ in ("bool_type", "bool_parsing"):
        msg = f"켬/끔(true/false) 이어야 하는데 {shown} 이(가) 들어 있습니다."
    elif typ == "literal_error":
        msg = f"쓸 수 없는 값 {shown} 입니다."
        exp = str(ctx.get("expected") or "").replace(" or ", ", ")
        hint = f"가능한 값: {exp}" if exp else "목록에서 고르세요."
    elif typ == "list_type":
        msg = f"목록이어야 하는데 {kind} 값이 들어 있습니다."
    elif typ in ("dict_type", "model_type", "model_attributes_type"):
        msg = f"여러 항목의 묶음이어야 하는데 {kind} 값이 들어 있습니다."
    elif typ == "value_error":
        msg = str(err.get("msg", "")).removeprefix("Value error, ")
        if "segment id 중복" in msg:
            msg = msg.replace("segment id 중복", "장면 이름 중복 — 같은 이름의 장면이 둘 이상 있습니다")
            hint = "장면마다 다른 이름을 쓰세요 (장면 편집기 맨 위의 이름 칸)."
        elif "segments 가 비어" in msg:
            msg, hint = "장면이 하나도 없습니다.", "왼쪽 ‘＋ 장면’ 으로 장면을 추가하세요."
    else:
        msg = str(err.get("msg", ""))
    if not hint and typ.endswith("_type"):
        hint = "입력 칸의 값을 확인하세요."
    return {"where": where, "msg": msg, "hint": hint, "raw": raw}


_WHERE_RE = re.compile(r"^segments\[(\d+):?([^\]]*)\](?:\.actions\[(\d+):?([^\]]*)\])?(?:\.(.*))?$")


def _locate(where: str, doc: dict[str, Any]) -> dict[str, Any]:
    """where 문자열 → {label: 사람이 읽는 위치, target: 편집기에서 이동할 곳}."""
    m = _WHERE_RE.match(where or "")
    if m:
        si = int(m.group(1))
        label = f"{si + 1}번째 장면" + (f" ‘{m.group(2)}’" if m.group(2) else "")
        target: dict[str, Any] = {"seg": si}
        rest = m.group(5) or ""
        if m.group(3) is not None:
            ai = int(m.group(3))
            label += f" › {ai + 1}번째 동작"
            target["act"] = ai
            key = rest.split(".")[0] if rest else ""
            if key and not key.startswith("steps["):
                label += f" › {_ACT_KO.get(key, key)}"
        elif rest:
            label += f" › {_SEG_KO.get(rest.split('.')[0], rest)}"
        return {"label": label, "target": target}
    parts = (where or "").split(".")
    if parts[0] == "meta":
        key = parts[1] if len(parts) > 1 else ""
        return {"label": f"⚙ 영상 설정 › {_META_KO.get(key, key or '영상 정보')}", "target": {"pane": "settings", "field": f"meta.{key}"}}
    if parts[0] == "layout":
        return {"label": "⚙ 영상 설정 › 칠판 배치" + (f" › {parts[-1]}" if len(parts) > 2 else ""), "target": {"pane": "settings"}}
    if parts[0] == "params":
        return {"label": "⚙ 영상 설정 › 상수" + (f" › {parts[1]}" if len(parts) > 1 else ""), "target": {"pane": "settings"}}
    if parts[0] == "segments":
        return {"label": "장면 목록", "target": None}
    if where == "LaTeX":
        return {"label": "수식 (LaTeX)", "target": None}
    if where == "YAML":
        return {"label": "YAML 원문", "target": {"pane": "yaml"}}
    return {"label": "프로젝트 전체", "target": None}


def _autofix(doc: Any, pid: str) -> list[str]:
    """편집기에서 고칠 수단이 없는 형식 문제를 바로잡는다. 고친 내용 설명 목록을 돌려준다."""
    fixes: list[str] = []
    if not isinstance(doc, dict):
        return fixes
    meta = doc.get("meta")
    if isinstance(meta, dict) and not isinstance(meta.get("id"), str):
        old = meta.get("id")
        meta["id"] = pid
        fixes.append(f"프로젝트 ID 가 {old!r} (숫자) 로 읽혀서 폴더 이름 ‘{pid}’ 로 고쳤습니다")
    for seg in doc.get("segments") or []:
        if isinstance(seg, dict) and isinstance(seg.get("id"), (int, float)) and not isinstance(seg.get("id"), bool):
            seg["id"] = str(seg["id"])
            fixes.append(f"장면 이름 {seg['id']} 을(를) 글자로 고쳤습니다")
    return fixes


def _split_sentences(text: str) -> list[str]:
    from ..narration.tts import split_sentences
    return split_sentences(text) if text else []


def _sentences_for(doc: dict[str, Any], seg: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    """세그먼트의 문장 목록. TTS 캐시에 같은 내레이션이 있으면 엔진이 실제로 끊어 읽은 경계와 시각(exact=True)을,
    없으면 문장부호 기준 추정(exact=False)을 돌려준다. `at: sN` 은 실제 경계를 기준으로 하므로 이 구분이 중요하다."""
    from ..narration.tts import cached_clip
    text = str(seg.get("narration") or "")
    meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
    clip = None
    if text.strip():
        try:
            clip = cached_clip(text, voice=str(seg.get("voice") or meta.get("voice") or "ko-KR-InJoonNeural"),
                               rate=str(seg.get("rate") or meta.get("rate") or "+0%"),
                               pitch=str(meta.get("pitch") or "+0Hz"), cache_dir=output_dir / "_cache" / "tts")
        except Exception:  # noqa: BLE001
            clip = None
    if clip is not None:
        return {"exact": True, "duration": round(clip.duration, 2),
                "sentences": [{"i": i, "text": s.text, "start": round(s.start, 2), "end": round(s.end, 2)}
                              for i, s in enumerate(clip.sentences, 1)]}
    # TTS 캐시가 없어도(다른 PC에서 받은 저장소 등) 마지막 렌더의 timeline.json 에 같은 내레이션이 있으면 그 시각을 쓴다
    hit = _timeline_sentences(doc, seg, output_dir)
    if hit is not None:
        return hit
    return {"exact": False, "duration": None,
            "sentences": [{"i": i, "text": t} for i, t in enumerate(_split_sentences(text), 1)]}


_TIMELINE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _timeline_sentences(doc: dict[str, Any], seg: dict[str, Any], output_dir: Path) -> dict[str, Any] | None:
    """output/<id>/timeline.json (마지막 빌드) 에서 같은 id·같은 내레이션의 세그먼트를 찾아 문장 시각을 돌려준다."""
    meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
    pid = str(meta.get("id") or "")
    if not pid:
        return None
    norm = lambda s: " ".join(str(s or "").split())  # noqa: E731
    want = norm(seg.get("narration"))
    if not want:
        return None
    for out_id in (pid, pid + "__part"):
        f = output_dir / out_id / "timeline.json"
        if not f.exists():
            continue
        try:
            mtime = f.stat().st_mtime
            cached = _TIMELINE_CACHE.get(str(f))
            if cached is None or cached[0] != mtime:
                cached = (mtime, json.loads(f.read_text(encoding="utf-8")))
                _TIMELINE_CACHE[str(f)] = cached
            tl = cached[1]
        except Exception:  # noqa: BLE001
            continue
        for s in tl.get("segments") or []:
            if norm(s.get("narration")) != want or not s.get("sentences"):
                continue
            sents = s["sentences"]
            return {"exact": True, "duration": round(float(s.get("audio_duration") or sents[-1]["end"]), 2),
                    "source": "timeline",
                    "sentences": [{"i": i, "text": x["text"], "start": round(float(x["start"]), 2), "end": round(float(x["end"]), 2)}
                                  for i, x in enumerate(sents, 1)]}
    return None


def _media_url(path: str, output_dir: Path) -> str | None:
    try:
        rel = Path(path).resolve().relative_to(output_dir.resolve())
    except ValueError:
        return None
    return "/output/" + rel.as_posix()


def serve(root: str | Path = ".", host: str = "0.0.0.0", port: int = 8765, open_browser: bool = True) -> None:
    import uvicorn
    app = create_app(root)
    # 브라우저로 열 주소는 localhost 로 안내 (0.0.0.0 은 바인드용)
    browse = f"http://127.0.0.1:{port}/" if host in ("0.0.0.0", "::") else f"http://{host}:{port}/"
    print(f"Explainer Studio → {browse}   (bind {host}:{port}, 작업 폴더: {app.state.root})")
    print("  Cursor Cloud Agent 이면 Agents Window 오른쪽 위 플러그(Forwarded Ports)에서")
    print(f"  포트 {port} 을 연 뒤 내 PC 브라우저로 http://localhost:{port}/ 를 여세요.")
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(browse)).start()
    uvicorn.run(app, host=host, port=port, log_level="warning")
