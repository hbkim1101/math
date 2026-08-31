from __future__ import annotations

import subprocess
from pathlib import Path


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")


def concat_audio(files: list[Path], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    list_file = output.with_suffix(".txt")
    lines = [f"file '{f.resolve()}'" for f in files if f.exists()]
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(output),
        ]
    )
    list_file.unlink(missing_ok=True)
    return output


def merge_audio_video(
    video: Path,
    audio: Path,
    output: Path,
    *,
    short_video: bool = False,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video),
        "-i",
        str(audio),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
    ]
    if short_video:
        cmd.extend(["-shortest"])
    else:
        cmd.extend(["-map", "0:v:0", "-map", "1:a:0"])
    cmd.append(str(output))
    _run(cmd)
    return output


def burn_subtitles(video: Path, srt: Path, output: Path) -> Path:
    """Optional soft-caption burn-in."""
    output.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-vf",
            f"subtitles={srt.resolve()}",
            "-c:a",
            "copy",
            str(output),
        ]
    )
    return output


def write_srt(captions: list[tuple[float, float, str]], output: Path) -> Path:
    """Write SRT from (start, end, text) tuples."""
    lines: list[str] = []
    for i, (start, end, text) in enumerate(captions, 1):
        lines.append(str(i))
        lines.append(f"{_ts(start)} --> {_ts(end)}")
        lines.append(text)
        lines.append("")
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
