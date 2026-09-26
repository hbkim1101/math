"""세그먼트별 대표 프레임 + 내레이션을 한 장의 스토리보드(콘택트 시트)로 만든다."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import os

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    # Windows: 맑은 고딕 / 사용자 폴더의 나눔 폰트
    r"C:\Windows\Fonts\malgun.ttf",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts\NanumBarunpenR.ttf"),
    # macOS
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def grab_frame(video: Path, t: float, out: Path, width: int = 640) -> Path:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1",
         "-vf", f"scale={width}:-1", str(out)],
        check=True,
    )
    return out


def _wrap(text: str, font, max_w: int, draw) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        cand = f"{cur} {w}".strip()
        if draw.textlength(cand, font=font) <= max_w:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def build_storyboard(out_dir: str | Path, columns: int = 3, thumb_w: int = 640, offset_ratio: float = 0.75,
                     log=print) -> Path:
    """manifest.json 의 세그먼트마다 (시작 + 길이*offset_ratio) 시점의 프레임을 뽑아 격자로 배치."""
    out_dir = Path(out_dir)
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    video = Path(manifest["final_video"])
    segs = manifest["timeline"]["segments"]
    frames_dir = out_dir / "storyboard_frames"
    frames_dir.mkdir(exist_ok=True)

    thumbs = []
    for i, s in enumerate(segs):
        t = s["start"] + (s["end"] - s["start"]) * offset_ratio
        p = grab_frame(video, t, frames_dir / f"{i:02d}_{s['id']}.png", width=thumb_w)
        thumbs.append((s, t, Image.open(p).convert("RGB")))

    thumb_h = thumbs[0][2].height
    text_h = 130
    pad = 16
    cell_w, cell_h = thumb_w + pad, thumb_h + text_h + pad
    rows = (len(thumbs) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w + pad, rows * cell_h + pad + 70), (11, 15, 25))
    draw = ImageDraw.Draw(sheet)
    title_font, id_font, body_font = _font(30), _font(20), _font(17)
    draw.text((pad, pad), f"{manifest['project']['title']} — 스토리보드 ({len(segs)} 세그먼트)", font=title_font,
              fill=(229, 231, 235))

    for i, (s, t, im) in enumerate(thumbs):
        r, c = divmod(i, columns)
        x, y = pad + c * cell_w, pad + 70 + r * cell_h
        sheet.paste(im, (x, y))
        draw.rectangle([x, y, x + thumb_w - 1, y + thumb_h - 1], outline=(36, 48, 73), width=1)
        mm, ss = divmod(int(t), 60)
        draw.text((x, y + thumb_h + 6), f"{i + 1:02d}. {s['id']}   {mm:d}:{ss:02d}", font=id_font, fill=(88, 196, 221))
        lines = _wrap(s["narration"], body_font, thumb_w, draw)[:4]
        if len(lines) == 4:
            lines[-1] = lines[-1][:40] + "…"
        for k, line in enumerate(lines):
            draw.text((x, y + thumb_h + 34 + k * 22), line, font=body_font, fill=(190, 197, 210))

    out = out_dir / "storyboard.png"
    sheet.save(out, optimize=True)
    if log:
        log(f"  [storyboard] {out}  ({sheet.width}x{sheet.height})")
    return out
