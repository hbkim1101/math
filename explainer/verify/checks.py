"""최종 영상 자동 검증.

검사 항목
- 컨테이너: 해상도/fps/코덱, 오디오 트랙 존재, 오디오-비디오 길이 일치
- 타임라인: 세그먼트 시작 시각이 단조 증가, 각 세그먼트 길이 ≥ 내레이션 길이(오디오가 잘리지 않음)
- 자막: 큐가 겹치지 않고 영상 길이 안에 있음, 한 줄 길이 제한
- 프레임 품질: 검은/빈 프레임 없음, 프레임 간 변화 존재(정지 화면이 전체를 차지하지 않음), 선명도(라플라시안 분산)
- 오디오: 통합 라우드니스(LUFS)와 트루피크, 무음 구간 비율
"""

from __future__ import annotations

import json
import math
import re
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path

import numpy as np


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    value: float | None = None


@dataclass
class VerifyReport:
    video: str
    checks: list[Check] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    def add(self, name: str, ok: bool, detail: str, value: float | None = None) -> None:
        self.checks.append(Check(name, bool(ok), detail, value))

    def to_json(self) -> dict:
        return {"video": self.video, "ok": self.ok, "checks": [asdict(c) for c in self.checks]}

    def render_text(self) -> str:
        lines = [f"검증 대상: {self.video}"]
        for c in self.checks:
            mark = "PASS" if c.ok else "FAIL"
            lines.append(f"  [{mark}] {c.name:<28} {c.detail}")
        lines.append(f"결과: {'모든 검사 통과' if self.ok else '실패한 검사 있음'}")
        return "\n".join(lines)


def _probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def _sample_frames(path: Path, count: int, width: int = 320) -> list[np.ndarray]:
    """영상에서 균등 간격으로 count 장의 회색조 프레임을 뽑는다."""
    info = _probe(path)
    duration = float(info["format"]["duration"])
    frames = []
    for i in range(count):
        t = duration * (i + 0.5) / count
        proc = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
             "-vf", f"scale={width}:-1,format=gray", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
            capture_output=True, check=True,
        )
        raw = np.frombuffer(proc.stdout, dtype=np.uint8)
        if raw.size == 0:
            continue
        h = raw.size // width
        frames.append(raw[: h * width].reshape(h, width).astype(np.float32))
    return frames


def _laplacian_var(img: np.ndarray) -> float:
    lap = (-4 * img[1:-1, 1:-1] + img[:-2, 1:-1] + img[2:, 1:-1] + img[1:-1, :-2] + img[1:-1, 2:])
    return float(lap.var())


def _loudness(path: Path) -> dict:
    proc = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    txt = proc.stderr
    summary = txt[txt.rfind("Summary:"):] if "Summary:" in txt else txt
    def grab(pattern):
        m = re.search(pattern, summary)
        return float(m.group(1)) if m else None
    return {
        "integrated": grab(r"I:\s+(-?[\d.]+) LUFS"),
        "true_peak": grab(r"Peak:\s+(-?[\d.]+) dBFS"),
        "lra": grab(r"LRA:\s+(-?[\d.]+) LU"),
    }


def _silence_ratio(path: Path, duration: float, threshold_db: float = -45.0, min_len: float = 1.5) -> tuple[float, float]:
    proc = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(path), "-af", f"silencedetect=noise={threshold_db}dB:d={min_len}",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    total = 0.0
    longest = 0.0
    for m in re.finditer(r"silence_duration:\s*([\d.]+)", proc.stderr):
        d = float(m.group(1))
        total += d
        longest = max(longest, d)
    return (total / duration if duration else 0.0), longest


def verify_output(out_dir: str | Path, expect_resolution: tuple[int, int] | None = None,
                  expect_fps: int | None = None, frame_samples: int = 24,
                  max_silence: float = 4.0) -> VerifyReport:
    out_dir = Path(out_dir)
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    video = Path(manifest["final_video"])
    rep = VerifyReport(str(video))
    if not video.exists():
        rep.add("파일 존재", False, f"{video} 없음")
        return rep

    info = _probe(video)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    duration = float(info["format"]["duration"])

    rep.add("비디오 스트림", v is not None, f"codec={v['codec_name'] if v else None}")
    if v:
        w, h = int(v["width"]), int(v["height"])
        num, den = v["r_frame_rate"].split("/")
        fps = float(num) / float(den)
        if expect_resolution:
            rep.add("해상도", (w, h) == tuple(expect_resolution), f"{w}x{h} (기대 {expect_resolution[0]}x{expect_resolution[1]})")
        else:
            rep.add("해상도", w >= 1280 and h >= 720, f"{w}x{h}")
        if expect_fps:
            rep.add("프레임레이트", abs(fps - expect_fps) < 0.01, f"{fps:.2f} fps (기대 {expect_fps})", fps)
        else:
            rep.add("프레임레이트", fps >= 24, f"{fps:.2f} fps", fps)
        rep.add("픽셀 포맷 호환", v.get("pix_fmt") == "yuv420p", f"pix_fmt={v.get('pix_fmt')}")

    rep.add("오디오 스트림", a is not None, f"codec={a['codec_name'] if a else None}, sr={a.get('sample_rate') if a else None}")
    if a and "duration" in a and v and "duration" in v:
        ad, vd = float(a["duration"]), float(v["duration"])
        rep.add("오디오/비디오 길이 일치", abs(ad - vd) < 0.5, f"video={vd:.2f}s audio={ad:.2f}s (차이 {abs(ad - vd):.2f}s)", abs(ad - vd))

    # ---- 타임라인 / 싱크
    segs = manifest["timeline"]["segments"]
    starts = [s["start"] for s in segs]
    rep.add("세그먼트 순서(단조 증가)", all(b >= a_ for a_, b in zip(starts, starts[1:])), f"{len(segs)}개 세그먼트")
    clipped = [s["id"] for s in segs if s["audio_duration"] > 0 and (s["end"] - s["start"]) + 1e-3 < s["audio_duration"]]
    rep.add("내레이션 잘림 없음", not clipped, "모든 세그먼트가 오디오 길이 이상" if not clipped else f"잘린 세그먼트: {clipped}")
    last_end = segs[-1]["end"] if segs else 0
    rep.add("타임라인이 영상 안에 있음", last_end <= duration + 0.2, f"마지막 세그먼트 종료 {last_end:.2f}s / 영상 {duration:.2f}s")
    total_audio = sum(s["audio_duration"] for s in segs)
    speech_ratio = total_audio / duration if duration else 0
    rep.add("발화 비율", 0.55 <= speech_ratio <= 0.98, f"내레이션 {total_audio:.1f}s / 영상 {duration:.1f}s = {speech_ratio:.0%}", speech_ratio)

    # ---- 자막
    cues = manifest.get("cues", [])
    if cues:
        overlaps = sum(1 for p, n in zip(cues, cues[1:]) if n["start"] < p["end"] - 1e-3)
        rep.add("자막 겹침 없음", overlaps == 0, f"{len(cues)}개 큐, 겹침 {overlaps}")
        in_range = all(0 <= c["start"] < c["end"] <= duration + 0.2 for c in cues)
        rep.add("자막 시간 범위", in_range, "모든 큐가 영상 길이 안")
        long_lines = [c for c in cues if any(len(line) > 34 for line in c["text"].split("\n"))]
        rep.add("자막 줄 길이", not long_lines, f"34자 초과 줄 {len(long_lines)}개")
        expected_cues = sum(len(s["sentences"]) for s in segs)
        rep.add("자막 수 = 문장 수", len(cues) == expected_cues, f"{len(cues)} / {expected_cues}")

    # ---- 프레임 품질
    frames = _sample_frames(video, frame_samples)
    if frames:
        means = np.array([f.mean() for f in frames])
        black = int((means < 6).sum())
        rep.add("검은/빈 프레임 없음", black == 0, f"{frame_samples}장 중 검은 프레임 {black}장 (평균 밝기 {means.mean():.1f})")
        diffs = [float(np.abs(a_ - b).mean()) for a_, b in zip(frames, frames[1:])]
        moving = sum(1 for d in diffs if d > 0.5)
        rep.add("화면 변화(정지 아님)", moving >= len(diffs) * 0.3, f"연속 샘플 {len(diffs)}쌍 중 변화 {moving}쌍")
        sharp = np.array([_laplacian_var(f) for f in frames])
        rep.add("선명도", float(np.median(sharp)) > 20, f"라플라시안 분산 중앙값 {np.median(sharp):.1f}", float(np.median(sharp)))
        content = np.array([(f > 40).mean() for f in frames])
        rep.add("콘텐츠 존재", float(content.mean()) > 0.02, f"밝은 픽셀 비율 평균 {content.mean():.1%}")

    # ---- 오디오 품질
    if a:
        loud = _loudness(video)
        if loud["integrated"] is not None:
            rep.add("라우드니스", -20 <= loud["integrated"] <= -12, f"I={loud['integrated']} LUFS (목표 -16)", loud["integrated"])
        if loud["true_peak"] is not None:
            rep.add("트루피크(클리핑 없음)", loud["true_peak"] <= -0.5, f"peak={loud['true_peak']} dBFS", loud["true_peak"])
        ratio, longest = _silence_ratio(video, duration)
        rep.add("긴 무음 없음", longest <= max_silence, f"최장 무음 {longest:.1f}s, 무음 비율 {ratio:.0%}", longest)

    (out_dir / "verify_report.json").write_text(json.dumps(rep.to_json(), ensure_ascii=False, indent=1), encoding="utf-8")
    return rep
