import json
import shutil
import subprocess
from pathlib import Path

import pytest

from explainer.verify.checks import verify_output

ffmpeg = shutil.which("ffmpeg")


def _make_test_video(path: Path, seconds: float = 4.0, with_audio: bool = True, fps: int = 30):
    """색이 변하는 테스트 패턴 + 사인파 오디오로 짧은 mp4 를 만든다."""
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate={fps}:duration={seconds}"]
    if with_audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-c:a", "aac", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(cmd, check=True)


@pytest.mark.skipif(ffmpeg is None, reason="ffmpeg 필요")
def test_verify_output_passes_on_well_formed_video(tmp_path):
    video = tmp_path / "v.mp4"
    _make_test_video(video)
    manifest = {
        "final_video": str(video),
        "cues": [
            {"index": 1, "start": 0.2, "end": 1.9, "text": "첫 자막"},
            {"index": 2, "start": 2.0, "end": 3.8, "text": "둘째 자막"},
        ],
        "timeline": {
            "segments": [
                {"id": "a", "start": 0.0, "end": 2.0, "audio_duration": 1.8, "sentences": [{}]},
                {"id": "b", "start": 2.0, "end": 4.0, "audio_duration": 1.8, "sentences": [{}]},
            ]
        },
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    rep = verify_output(tmp_path, expect_resolution=(1280, 720), expect_fps=30, frame_samples=8)
    names = {c.name: c for c in rep.checks}
    assert names["해상도"].ok and names["프레임레이트"].ok and names["오디오 스트림"].ok
    assert names["내레이션 잘림 없음"].ok
    assert names["자막 겹침 없음"].ok and names["자막이 모든 문장을 포함"].ok
    assert names["검은/빈 프레임 없음"].ok and names["화면 변화(정지 아님)"].ok
    assert (tmp_path / "verify_report.json").exists()


@pytest.mark.skipif(ffmpeg is None, reason="ffmpeg 필요")
def test_verify_output_detects_clipped_narration_and_overlapping_cues(tmp_path):
    video = tmp_path / "v.mp4"
    _make_test_video(video, with_audio=False)
    manifest = {
        "final_video": str(video),
        "cues": [
            {"index": 1, "start": 0.0, "end": 2.5, "text": "a"},
            {"index": 2, "start": 2.0, "end": 3.0, "text": "b"},
        ],
        "timeline": {
            "segments": [
                {"id": "a", "start": 0.0, "end": 1.0, "audio_duration": 3.0, "sentences": [{}, {}]},
            ]
        },
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    rep = verify_output(tmp_path, frame_samples=6)
    names = {c.name: c for c in rep.checks}
    assert not names["오디오 스트림"].ok
    assert not names["내레이션 잘림 없음"].ok
    assert not names["자막 겹침 없음"].ok
    assert not rep.ok
