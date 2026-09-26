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
                loc = ".".join(str(x) for x in err["loc"])
                errors.append({"where": loc or "project", "msg": err["msg"]})
        try:
            resolve_params(doc.get("params") or {})
        except Exception as e:  # noqa: BLE001
            errors.append({"where": "params", "msg": str(e)})

        style = (doc.get("meta") or {}).get("style", "panel")
        sections = ((doc.get("layout") or {}).get("chalk") or {}).get("sections") or []
        section_ids = {s.get("id") for s in sections if isinstance(s, dict)}
        segments = doc.get("segments") or []
        for si, seg in enumerate(segments):
            if not isinstance(seg, dict):
                errors.append({"where": f"segments[{si}]", "msg": "세그먼트는 매핑이어야 합니다"})
                continue
            sid = seg.get("id", "?")
            n_sent = len(_split_sentences(str(seg.get("narration") or "")))
            acts = seg.get("actions") or []
            for ai, act in enumerate(acts):
                if not isinstance(act, dict) or "do" not in act:
                    errors.append({"where": f"segments[{si}:{sid}].actions[{ai}]", "msg": "액션에는 do: 가 필요합니다"})
                    continue
                where = f"segments[{si}:{sid}].actions[{ai}:{act['do']}]"
                if act["do"] not in REGISTRY:
                    errors.append({"where": where, "msg": f"알 수 없는 액션 '{act['do']}'"})
                at = act.get("at")
                if isinstance(at, str) and at.startswith("s"):
                    try:
                        k = int(at[1:])
                        if k > max(n_sent, 1):
                            warnings.append({"where": where, "msg": f"at: {at} 인데 문장은 {n_sent}개"})
                    except ValueError:
                        errors.append({"where": where, "msg": f"at 값이 이상합니다: {at!r}"})
                if act["do"] == "goto" and style == "chalkboard":
                    sec = act.get("section")
                    if sec and sec not in section_ids:
                        errors.append({"where": where, "msg": f"없는 섹션 '{sec}' (layout.chalk.sections 에 추가)"})
                if act["do"] in ("derive", "step"):
                    steps = act.get("steps") if act["do"] == "derive" else [act]
                    for k, st in enumerate(steps or []):
                        if isinstance(st, dict) and not (st.get("parts") or st.get("tex")):
                            errors.append({"where": f"{where}.steps[{k}]", "msg": "parts(조각 목록) 또는 tex 가 필요합니다"})
            if not seg.get("narration") and not acts:
                warnings.append({"where": f"segments[{si}:{sid}]", "msg": "내레이션과 액션이 모두 비어 있음"})
        if tex and project is not None and not errors:
            from ..lint import lint_tex
            msgs: list[str] = []
            for t in lint_tex(project, media_dir=output_dir / "_cache" / "lint", log=msgs.append):
                errors.append({"where": "LaTeX", "msg": t})
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
        hooks = []
        hp = p.parent / "hooks.py"
        if hp.exists():
            hooks = re.findall(r"^def\s+([a-zA-Z_]\w*)\s*\(", hp.read_text(encoding="utf-8"), flags=re.M)
            hooks = [h for h in hooks if not h.startswith("_")]
        return {"id": pid, "yaml": text, "doc": doc, "parse_error": parse_error, "hooks": hooks,
                "outputs": outputs_for(pid), "job": (jobs.running_for(pid) or _NoJob()).to_json()}

    @app.put("/api/projects/{pid}")
    def save_project(pid: str, body: SaveBody):
        p = project_yaml(pid)
        try:
            doc, text = doc_from_body(body)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, f"YAML 파싱 실패: {e}")
        result = check_doc(doc, tex=False, source=p)
        snapshot(p)
        p.write_text(text, encoding="utf-8")
        return {"saved": True, "yaml": text, "doc": doc, "check": result}

    @app.post("/api/projects/{pid}/validate")
    def validate_project(pid: str, body: ValidateBody):
        p = project_yaml(pid)
        try:
            doc, _ = doc_from_body(body)
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "errors": [{"where": "YAML", "msg": str(e)}], "warnings": [], "summary": {}}
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


def _split_sentences(text: str) -> list[str]:
    from ..narration.tts import split_sentences
    return split_sentences(text) if text else []


def _media_url(path: str, output_dir: Path) -> str | None:
    try:
        rel = Path(path).resolve().relative_to(output_dir.resolve())
    except ValueError:
        return None
    return "/output/" + rel.as_posix()


def serve(root: str | Path = ".", host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    import uvicorn
    app = create_app(root)
    url = f"http://{host}:{port}/"
    print(f"Explainer Studio → {url}   (작업 폴더: {app.state.root})")
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=host, port=port, log_level="warning")
