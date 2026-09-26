"""렌더 작업 관리: 별도 프로세스로 `python -m explainer build …` 를 돌리고 로그를 파일로 모은다."""

from __future__ import annotations

import datetime as _dt
import os
import re
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# ANSI 색/스타일(CSI), 터미널 하이퍼링크(OSC 8), 그 밖의 OSC 시퀀스
_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\]8;[^\x1b\x07]*(?:\x1b\\|\x07)|\x1b\][^\x1b\x07]*(?:\x1b\\|\x07)")
_NOISE = ("libncursesw",)


def clean_log(text: str) -> str:
    """manim(rich)·ffmpeg 가 찍는 ANSI 장식과 알려진 잡음 줄을 걷어낸 사람이 읽을 로그."""
    text = _ANSI_RE.sub("", text)
    lines = [ln.rstrip() for ln in text.splitlines() if not any(n in ln for n in _NOISE)]
    lines = [ln for ln in lines if ln.strip()]
    return "\n".join(lines) + ("\n" if lines else "")


@dataclass
class Job:
    id: str
    project_id: str
    kind: str                       # preview | final | partial
    cmd: list[str]
    log_path: Path
    status: str = "running"         # running | done | failed | cancelled
    returncode: Optional[int] = None
    started: str = field(default_factory=lambda: _dt.datetime.now().isoformat(timespec="seconds"))
    finished: Optional[str] = None
    out_dir: Optional[str] = None
    proc: Any = None

    def to_json(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if k not in ("proc", "cmd", "log_path")} | {
            "cmd": " ".join(self.cmd), "log_path": str(self.log_path)}


class JobManager:
    def __init__(self, root: Path):
        self.root = root
        self.jobs: dict[str, Job] = {}
        self.log_dir = root / "output" / "_studio_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def build_command(self, project_yaml: Path, preview: bool, segments: list[str] | None,
                      force_tts: bool = False) -> list[str]:
        cmd = [sys.executable, "-u", "-m", "explainer", "build", str(project_yaml), "--out", "output"]
        if preview:
            cmd.append("--preview")
        if segments:
            cmd += ["--segments", ",".join(segments)]
        if force_tts:
            cmd.append("--force-tts")
        return cmd

    def running_for(self, project_id: str) -> Optional[Job]:
        for j in self.jobs.values():
            if j.project_id == project_id and j.status == "running":
                return j
        return None

    def start(self, project_id: str, project_yaml: Path, preview: bool = True,
              segments: list[str] | None = None, force_tts: bool = False) -> Job:
        with self._lock:
            if self.running_for(project_id):
                raise RuntimeError("이 프로젝트의 렌더가 이미 진행 중입니다")
            jid = uuid.uuid4().hex[:10]
            kind = "partial" if segments else ("preview" if preview else "final")
            log_path = self.log_dir / f"{project_id}-{kind}-{jid}.log"
            cmd = self.build_command(project_yaml, preview, segments, force_tts)
            out_id = project_id + ("__part" if segments else "")
            job = Job(id=jid, project_id=project_id, kind=kind, cmd=cmd, log_path=log_path,
                      out_dir=str(self.root / "output" / out_id))
            env = dict(os.environ, PYTHONIOENCODING="utf-8")
            log_f = open(log_path, "w", encoding="utf-8")
            job.proc = subprocess.Popen(cmd, cwd=str(self.root), stdout=log_f, stderr=subprocess.STDOUT, env=env)
            self.jobs[jid] = job
            threading.Thread(target=self._watch, args=(job, log_f), daemon=True).start()
            return job

    def _watch(self, job: Job, log_f) -> None:
        rc = job.proc.wait()
        log_f.close()
        job.returncode = rc
        if job.status != "cancelled":
            job.status = "done" if rc == 0 else "failed"
        job.finished = _dt.datetime.now().isoformat(timespec="seconds")

    def cancel(self, jid: str) -> Job:
        job = self.jobs[jid]
        if job.status == "running" and job.proc is not None:
            job.status = "cancelled"
            job.proc.terminate()
        return job

    def log_tail(self, jid: str, offset: int = 0) -> tuple[str, int]:
        """offset 바이트 이후의 로그 텍스트와 새 offset."""
        job = self.jobs[jid]
        if not job.log_path.exists():
            return "", 0
        with open(job.log_path, "rb") as f:
            f.seek(offset)
            data = f.read()
        text = clean_log(data.decode("utf-8", errors="replace"))
        return text, offset + len(data)

    def list(self, project_id: str | None = None) -> list[dict[str, Any]]:
        out = [j.to_json() for j in self.jobs.values() if project_id is None or j.project_id == project_id]
        return sorted(out, key=lambda j: j["started"], reverse=True)
