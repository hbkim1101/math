"""Studio(브라우저 편집기) 백엔드 API 테스트 — 임시 작업 폴더에서 실행."""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from explainer.studio.server import create_app
from explainer.studio.yamlio import dump_project, parse_yaml

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def studio(tmp_path):
    (tmp_path / "projects").mkdir()
    shutil.copytree(ROOT / "projects" / "2027_sep_q03", tmp_path / "projects" / "2027_sep_q03")
    app = create_app(tmp_path)
    return TestClient(app), tmp_path


def test_list_and_get_project(studio):
    client, root = studio
    items = client.get("/api/projects").json()
    assert [i["id"] for i in items] == ["2027_sep_q03"]
    assert "3번" in items[0]["title"]
    d = client.get("/api/projects/2027_sep_q03").json()
    assert d["doc"]["meta"]["id"] == "2027_sep_q03"
    assert "term_hops" in d["hooks"]
    assert d["outputs"]["full"] is None
    assert client.get("/api/projects/nope").status_code == 404
    assert client.get("/api/projects/../etc").status_code in (400, 404)


def test_actions_catalog_has_signatures_and_templates(studio):
    client, _ = studio
    cat = client.get("/api/actions").json()
    names = {a["name"] for a in cat}
    assert {"derive", "step", "goto", "problem", "answer", "custom"} <= names
    goto = next(a for a in cat if a["name"] == "goto")
    assert goto["category"] == "칠판 판서"
    assert any(p["name"] == "section" and p["required"] for p in goto["params"])
    derive = next(a for a in cat if a["name"] == "derive")
    assert derive["template"]["steps"]


def test_validate_reports_structure_action_section_and_at_problems(studio):
    client, root = studio
    doc = parse_yaml((root / "projects/2027_sep_q03/project.yaml").read_text(encoding="utf-8"))
    ok = client.post("/api/projects/2027_sep_q03/validate", json={"doc": doc}).json()
    assert ok["ok"] and ok["summary"]["segments"] == 5

    bad = json.loads(json.dumps(doc))
    bad["segments"][2]["actions"][0]["section"] = "nope"
    bad["segments"][2]["actions"].append({"do": "bogus"})
    bad["segments"][2]["actions"].append({"do": "caption", "at": "s9", "text": "x"})
    bad["segments"].append({"id": "intro", "narration": "dup"})
    r = client.post("/api/projects/2027_sep_q03/validate", json={"doc": bad}).json()
    assert not r["ok"]
    msgs = " ".join(e["msg"] for e in r["errors"])
    assert "nope" in msgs and "bogus" in msgs and "중복" in msgs
    assert any("s9" in w["msg"] for w in r["warnings"])

    r2 = client.post("/api/projects/2027_sep_q03/validate", json={"yaml": "segments: [\n"}).json()
    assert not r2["ok"] and r2["errors"][0]["where"] == "YAML"


def test_save_roundtrip_keeps_content_and_writes_history(studio):
    client, root = studio
    p = root / "projects/2027_sep_q03/project.yaml"
    doc = parse_yaml(p.read_text(encoding="utf-8"))
    doc["meta"]["title"] = "바뀐 제목"
    doc["segments"][0]["actions"].append({"do": "caption", "text": "새 캡션", "at": "s2"})
    r = client.put("/api/projects/2027_sep_q03", json={"doc": doc}).json()
    assert r["saved"] and r["check"]["ok"]
    saved = parse_yaml(p.read_text(encoding="utf-8"))
    assert saved == json.loads(json.dumps(doc))           # 폼(JSON) → YAML → 다시 읽어도 같은 내용
    assert "{do: caption" in p.read_text(encoding="utf-8")   # 짧은 액션은 한 줄 flow 스타일
    hist = client.get("/api/projects/2027_sep_q03/history").json()
    assert len(hist) == 1
    # 원문 그대로 저장 (YAML 텍스트) 도 가능 — 주석 보존
    text = "# 주석\n" + p.read_text(encoding="utf-8")
    r = client.put("/api/projects/2027_sep_q03", json={"yaml": text}).json()
    assert r["saved"] and p.read_text(encoding="utf-8").startswith("# 주석")
    # 이력 복원
    hist = client.get("/api/projects/2027_sep_q03/history").json()
    r = client.post(f"/api/projects/2027_sep_q03/history/{hist[-1]['name']}/restore").json()
    assert r["doc"]["meta"]["title"].endswith("3번")


def test_new_project_from_template_validates(studio):
    client, root = studio
    r = client.post("/api/projects", json={"id": "demo_new", "title": "데모"})
    assert r.status_code == 200
    assert (root / "projects/demo_new/project.yaml").exists()
    doc = r.json()["doc"]
    chk = client.post("/api/projects/demo_new/validate", json={"doc": doc}).json()
    assert chk["ok"], chk
    assert client.post("/api/projects", json={"id": "demo_new"}).status_code == 409
    assert client.post("/api/projects", json={"id": "Bad Id!"}).status_code == 400


def test_yaml_format_and_parse_roundtrip(studio):
    client, root = studio
    text = (root / "projects/2027_sep_q03/project.yaml").read_text(encoding="utf-8")
    doc = client.post("/api/yaml/parse", json={"yaml": text}).json()["doc"]
    out = client.post("/api/yaml/format", json={"doc": doc}).json()["yaml"]
    assert parse_yaml(out) == doc
    assert out.startswith("meta:")
    assert client.post("/api/yaml/parse", json={"yaml": "- just a list"}).status_code == 400


def test_dump_project_styles():
    doc = {"meta": {"id": "x", "title": "t"}, "segments": [{"id": "a", "narration": ("긴 문장. " * 30).strip(),
            "actions": [{"do": "goto", "section": "sol", "run_time": 1.6},
                        {"do": "derive", "id": "d", "steps": [{"parts": ["x", "=", "1"], "why": "이유"}]}]}]}
    out = dump_project(doc)
    assert "narration: >" in out                 # 긴 내레이션은 접힌 블록
    assert "{do: goto, section: sol, run_time: 1.6}" in out
    assert parse_yaml(out) == doc


def test_build_job_runs_command_and_streams_log(studio, monkeypatch):
    client, root = studio
    jobs = client.app.state.jobs
    # 실제 렌더 대신 로그를 찍는 짧은 명령으로 대체
    monkeypatch.setattr(jobs, "build_command", lambda project_yaml, preview, segments, force_tts=False:
                        [sys.executable, "-c", f"print({str(project_yaml)!r}, 'preview=', {preview!r}, 'segs=', {segments!r}); print('RENDER_DONE')"])
    r = client.post("/api/projects/2027_sep_q03/build", json={"preview": True, "segments": ["find_d"]})
    assert r.status_code == 200
    job = r.json()
    assert job["kind"] == "partial" and job["out_dir"].endswith("2027_sep_q03__part")
    for _ in range(50):
        st = client.get(f"/api/jobs/{job['id']}").json()
        if st["job"]["status"] != "running":
            break
        time.sleep(0.1)
    assert st["job"]["status"] == "done", st
    assert "RENDER_DONE" in st["log"] and "segs= ['find_d']" in st["log"]
    assert client.get("/api/jobs?project=2027_sep_q03").json()[0]["id"] == job["id"]
    assert client.get("/api/jobs/zzz").status_code == 404


def test_build_rejects_concurrent_job(studio, monkeypatch):
    client, root = studio
    jobs = client.app.state.jobs
    monkeypatch.setattr(jobs, "build_command", lambda *a, **k: [sys.executable, "-c", "import time; time.sleep(3)"])
    j = client.post("/api/projects/2027_sep_q03/build", json={"preview": True}).json()
    assert client.post("/api/projects/2027_sep_q03/build", json={"preview": True}).status_code == 409
    c = client.post(f"/api/jobs/{j['id']}/cancel").json()
    assert c["status"] == "cancelled"


def test_real_build_command_uses_cli_flags(studio):
    client, root = studio
    cmd = client.app.state.jobs.build_command(Path("projects/x/project.yaml"), preview=True, segments=["a", "b"])
    assert cmd[1:5] == ["-u", "-m", "explainer", "build"] and "--preview" in cmd and cmd[cmd.index("--segments") + 1] == "a,b"


def test_index_and_static_served(studio):
    client, _ = studio
    assert "Explainer" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/api/health").json()["ok"]


def test_pipeline_partial_build_filters_segments(tmp_path, monkeypatch):
    """pipeline.build(segments=…) 는 선택한 세그먼트만 남기고 id 에 __part 를 붙인다 (렌더는 가짜)."""
    import explainer.pipeline as pl
    captured = {}

    def fake_timeline(project, cache_dir, force, log):
        from explainer.narration.timeline import SegmentTiming, Timeline
        tl = Timeline()
        for s in project.segments:
            tl.segments.append(SegmentTiming(id=s.id, narration=s.narration, clip=None, pad=0.1))
        return tl

    def fake_render(project, timeline, out_dir, preview, hooks, log):
        captured["ids"] = [s.id for s in project.segments]
        captured["pid"] = project.meta.id
        m = Path(out_dir) / "fake.mp4"
        m.write_bytes(b"0")
        return m

    monkeypatch.setattr(pl, "build_timeline", fake_timeline)
    monkeypatch.setattr(pl, "render_project", fake_render)
    monkeypatch.setattr(pl, "finalize_video", lambda project, timeline, movie, out_dir, preview, log: {"final_video": str(movie)})
    pl.build(ROOT / "projects/2027_sep_q03/project.yaml", out_root=tmp_path, preview=True, verify=False,
             segments=["find_d", "answer"], log=lambda *_: None)
    assert captured["ids"] == ["find_d", "answer"] and captured["pid"] == "2027_sep_q03__part"
    with pytest.raises(ValueError):
        pl.build(ROOT / "projects/2027_sep_q03/project.yaml", out_root=tmp_path, preview=True, verify=False,
                 segments=["nope"], log=lambda *_: None)


def test_sentences_use_tts_cache_when_available(studio):
    """숫자 뒤의 '.' 처럼 추정 분리와 TTS 실제 경계가 다를 때, 캐시가 있으면 실제 경계(exact)를 돌려준다."""
    from explainer.narration.tts import NarrationClip, Sentence, _cache_key

    client, root = studio
    d = client.get("/api/projects/2027_sep_q03").json()
    seg = d["doc"]["segments"][0]
    assert d["sentences"][seg["id"]]["exact"] is False           # 아직 합성한 적 없음 → 추정

    # 캐시에 '엔진이 실제로 끊어 읽은' 경계를 심는다 (문장 2개짜리로)
    text = " ".join(str(seg["narration"]).split())
    voice, rate = d["doc"]["meta"]["voice"], d["doc"]["meta"].get("rate", "+0%")
    cache = root / "output" / "_cache" / "tts"
    cache.mkdir(parents=True)
    key = _cache_key(text, voice, rate, "+0Hz")
    (cache / f"{key}.mp3").write_bytes(b"\0" * 2000)
    clip = NarrationClip(text=text, audio_path=str(cache / f"{key}.mp3"), duration=9.0,
                         sentences=[Sentence("앞부분.", 0.0, 4.0), Sentence("뒷부분.", 4.0, 9.0)])
    (cache / f"{key}.json").write_text(json.dumps(clip.to_json(), ensure_ascii=False), encoding="utf-8")

    d2 = client.get("/api/projects/2027_sep_q03").json()
    info = d2["sentences"][seg["id"]]
    assert info["exact"] is True and [s["i"] for s in info["sentences"]] == [1, 2]
    assert info["sentences"][1]["start"] == 4.0

    # 검사도 실제 경계를 기준으로 경고한다: s3 은 문장 2개를 넘는다
    doc = json.loads(json.dumps(d2["doc"]))
    doc["segments"][0]["actions"].append({"do": "caption", "at": "s3", "text": "x"})
    r = client.post("/api/projects/2027_sep_q03/validate", json={"doc": doc}).json()
    assert any("문장은 2개" in w["msg"] for w in r["warnings"])

    # 편집 중 문서에 대한 조회
    r2 = client.post("/api/projects/2027_sep_q03/sentences", json={"doc": doc}).json()
    assert r2[seg["id"]]["exact"] is True


def test_clean_log_strips_ansi_and_noise():
    from explainer.studio.jobs import clean_log

    raw = ("\x1b[2m[07:22:17]\x1b[0m WARNING  Some options \x1b]8;id=1;file:///x/scene_file_writer.py\x1b\\scene_file_writer.py\x1b]8;;\x1b\\:1018\n"
           "ffmpeg: /lib/libncursesw.so.6: no version information available\n"
           "\n"
           "  [render] output/x.mp4  (52.9 MB)\n")
    out = clean_log(raw)
    assert "\x1b" not in out and "libncursesw" not in out
    assert out.splitlines() == ["[07:22:17] WARNING  Some options scene_file_writer.py:1018", "  [render] output/x.mp4  (52.9 MB)"]


def test_sentences_fall_back_to_last_render_timeline(studio):
    """TTS 캐시가 없어도(다른 PC에서 받은 저장소) 마지막 렌더의 timeline.json 에서 실제 문장 시각을 가져온다."""
    client, root = studio
    d = client.get("/api/projects/2027_sep_q03").json()
    seg = d["doc"]["segments"][0]
    assert d["sentences"][seg["id"]]["exact"] is False

    out = root / "output" / "2027_sep_q03"
    out.mkdir(parents=True)
    tl = {"segments": [{"id": seg["id"], "narration": seg["narration"], "start": 0.6, "end": 9.6, "audio_duration": 9.0,
                        "sentences": [{"text": "앞.", "start": 0.0, "end": 4.0}, {"text": "뒤.", "start": 4.0, "end": 9.0}]}]}
    (out / "timeline.json").write_text(json.dumps(tl, ensure_ascii=False), encoding="utf-8")

    info = client.get("/api/projects/2027_sep_q03").json()["sentences"][seg["id"]]
    assert info["exact"] is True and info.get("source") == "timeline" and info["duration"] == 9.0
    assert [s["start"] for s in info["sentences"]] == [0.0, 4.0]

    # 내레이션이 바뀌면 더 이상 그 시각을 믿지 않는다 → 추정으로 돌아감
    doc = json.loads(json.dumps(d["doc"]))
    doc["segments"][0]["narration"] = seg["narration"] + " 새 문장입니다."
    r = client.post("/api/projects/2027_sep_q03/sentences", json={"doc": doc}).json()
    assert r[seg["id"]]["exact"] is False
