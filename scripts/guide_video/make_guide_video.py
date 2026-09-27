"""Studio 제작 가이드 영상 조립기.

docs/guide_video/scenes.json 의 장면(슬라이드 / 스튜디오 스크린샷 + 강조 영역 / 완성 영상 발췌)을
edge-tts 내레이션과 함께 1920x1080 영상으로 엮는다. 스크린샷 장면은 전체 화면(강조 박스, 나머지는 살짝 어둡게)
→ 강조 영역 확대(zoom) 두 컷으로 보여 준다. 자막은 파이프라인의 ASS 스타일을 그대로 쓴다.

사용:  python scripts/guide_video/make_guide_video.py  [--out output/studio_guide]
필요:  ffmpeg(libass 포함), edge-tts(네트워크; 결과는 output/_cache/tts 에 캐시), Windows 폰트(맑은 고딕·Consolas) 또는 나눔 폰트
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from explainer.compose.subtitles import Cue, split_long_sentence, wrap_korean, write_ass  # noqa: E402
from explainer.narration.tts import synthesize_segment  # noqa: E402

W, H = 1920, 1080
BG = (11, 15, 25)
PANEL = (22, 28, 42)
ACCENT = (255, 210, 63)
TEXT = (230, 233, 240)
MUTED = (139, 147, 167)
CODE_BG = (16, 21, 32)

FONT_CANDIDATES = {
    "bold": [r"C:\Windows\Fonts\malgunbd.ttf", "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
             "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"],
    "regular": [r"C:\Windows\Fonts\malgun.ttf", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"],
    "mono": [r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\malgun.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"],
}


def font(kind: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for p in FONT_CANDIDATES[kind]:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def run(cmd: list[str], cwd: Path | None = None) -> None:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"명령 실패 ({r.returncode}): {' '.join(cmd)}\n{r.stderr[-3000:]}")


# ---------------------------------------------------------------------- 프레임 만들기
def canvas() -> Image.Image:
    return Image.new("RGB", (W, H), BG)


def draw_slide(sc: dict) -> Image.Image:
    im = canvas()
    d = ImageDraw.Draw(im)
    # 왼쪽 세로 강조 띠 + 제목
    d.rectangle([80, 120, 92, 300], fill=ACCENT)
    d.text((120, 120), sc["title"], font=font("bold", 66), fill=TEXT)
    y = 215
    if sc.get("subtitle"):
        d.text((120, y), sc["subtitle"], font=font("regular", 36), fill=MUTED)
        y += 70
    y = max(y, 330)
    for b in sc.get("bullets", []):
        d.ellipse([124, y + 16, 140, y + 32], fill=ACCENT)
        d.text((165, y), b, font=font("regular", 40), fill=TEXT)
        y += 78
    code = sc.get("code")
    if code:
        f = font("mono", 27)
        pad = 28
        line_h = 40
        box_h = pad * 2 + line_h * len(code)
        top = max(y + 10, 320)
        d.rounded_rectangle([110, top, W - 110, top + box_h], radius=14, fill=CODE_BG, outline=(42, 52, 72), width=2)
        fk = font("regular", 26)   # 주석의 한글은 고정폭 폰트에 글리프가 없어 한글 폰트로
        for i, line in enumerate(code):
            x0, y0 = 110 + pad, top + pad + i * line_h
            if line.strip().startswith("#"):
                d.text((x0, y0), line, font=fk, fill=MUTED)
                continue
            code_part, _, comment = line.partition("#")
            col = ACCENT if line.startswith("- ") else TEXT
            d.text((x0, y0), code_part, font=f, fill=col)
            if comment:
                cx = x0 + f.getlength(code_part)
                d.text((cx, y0), "# " + comment.strip(), font=fk, fill=MUTED)
    d.text((120, H - 70), "Explainer Studio · 제작 가이드", font=font("regular", 26), fill=MUTED)
    return im


def spotlight(shot: Image.Image, rects: list[list[int]], dim: int = 120) -> Image.Image:
    """강조 영역 밖을 어둡게 하고 영역에 노란 테두리."""
    base = shot.convert("RGB")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, dim))
    for x, y, w, h in rects:
        overlay.paste((0, 0, 0, 0), (x, y, x + w, y + h))
    out = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    d = ImageDraw.Draw(out)
    for x, y, w, h in rects:
        d.rounded_rectangle([x - 3, y - 3, x + w + 3, y + h + 3], radius=10, outline=ACCENT, width=5)
    return out


def place_full(shot: Image.Image, caption: str | None = None) -> Image.Image:
    """스크린샷 전체를 1920x1080 안에 맞춰 놓는다 (여백은 어두운 배경)."""
    im = canvas()
    s = min(W / shot.width, (H - 60) / shot.height)
    nw, nh = int(shot.width * s), int(shot.height * s)
    r = shot.resize((nw, nh), Image.LANCZOS)
    x, y = (W - nw) // 2, (H - 60 - nh) // 2 + 30
    im.paste(r, (x, y))
    d = ImageDraw.Draw(im)
    d.rectangle([x - 1, y - 1, x + nw, y + nh], outline=(60, 72, 96), width=1)
    if caption:
        d.text((x, 6), caption, font=font("regular", 22), fill=MUTED)
    return im


def fit_16_9(rect: list[int], iw: int, ih: int, min_w: int = 820, pad: int = 36) -> tuple[int, int, int, int]:
    x, y, w, h = rect
    x, y, w, h = x - pad, y - pad, w + 2 * pad, h + 2 * pad
    w = max(w, min_w)
    if w / h > 16 / 9:
        h = w * 9 / 16
    else:
        w = h * 16 / 9
    w, h = min(w, iw), min(h, ih)
    if w / h > 16 / 9:
        w = h * 16 / 9
    else:
        h = w * 9 / 16
    cx, cy = x + (rect[2] + 2 * pad) / 2, y + (rect[3] + 2 * pad) / 2
    x0 = int(min(max(cx - w / 2, 0), iw - w))
    y0 = int(min(max(cy - h / 2, 0), ih - h))
    return x0, y0, int(w), int(h)


def union(rects: list[list[int]]) -> list[int]:
    x0 = min(r[0] for r in rects)
    y0 = min(r[1] for r in rects)
    x1 = max(r[0] + r[2] for r in rects)
    y1 = max(r[1] + r[3] for r in rects)
    return [x0, y0, x1 - x0, y1 - y0]


def place_zoom(shot: Image.Image, rect: list[int]) -> Image.Image:
    x, y, w, h = fit_16_9(rect, shot.width, shot.height)
    crop = shot.crop((x, y, x + w, y + h)).resize((W, H), Image.LANCZOS)
    return crop


# ---------------------------------------------------------------------- 조립
def build(args: argparse.Namespace) -> None:
    spec = json.loads((ROOT / "docs" / "guide_video" / "scenes.json").read_text(encoding="utf-8"))
    base = ROOT / "docs" / "guide_video"
    out = ROOT / args.out
    frames = out / "frames"
    parts = out / "parts"
    for d in (frames, parts):
        d.mkdir(parents=True, exist_ok=True)
    cache = ROOT / "output" / "_cache" / "tts"
    final_video = ROOT / spec["final_video"]

    cues: list[Cue] = []
    t_global = 0.0
    part_files: list[Path] = []
    cue_idx = 1

    for sc in spec["scenes"]:
        sid = sc["id"]
        kind = sc["kind"]
        print(f"[{sid}] {kind}")
        if kind == "clip":
            dur = float(sc["end"]) - float(sc["start"])
            p = parts / f"{sid}.mp4"
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{sc['start']:.3f}", "-to", f"{sc['end']:.3f}", "-i", str(final_video),
                 "-vf", f"scale={W}:{H},fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                 "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-af", "apad", "-t", f"{dur:.3f}", str(p)])
            if sc.get("caption"):
                cues.append(Cue(cue_idx, t_global + 0.3, t_global + min(dur - 0.3, 5.0), wrap_korean(sc["caption"])))
                cue_idx += 1
            part_files.append(p)
            t_global += dur
            continue

        # 내레이션
        clip = synthesize_segment(sc["narration"], voice=spec.get("voice", "ko-KR-InJoonNeural"),
                                  rate=spec.get("rate", "+0%"), cache_dir=cache)
        dur = max(clip.duration + 0.9, 3.0)

        # 프레임(들)
        images: list[tuple[Path, float]] = []
        if kind == "slide":
            f = frames / f"{sid}.png"
            draw_slide(sc).save(f)
            images.append((f, dur))
        else:
            shot = Image.open(base / sc["image"]).convert("RGB")
            rects = sc.get("highlights", [])
            lit = spotlight(shot, rects) if rects else shot
            f_full = frames / f"{sid}_full.png"
            place_full(lit, caption=None).save(f_full)
            do_zoom = sc.get("zoom", True) and rects
            if do_zoom:
                zrect = sc.get("zoom_rect") or union(rects)
                f_zoom = frames / f"{sid}_zoom.png"
                place_zoom(lit, zrect).save(f_zoom)
                t_full = min(3.2, dur * 0.38)
                images.append((f_full, t_full))
                images.append((f_zoom, dur - t_full))
            else:
                images.append((f_full, dur))

        # 장면 mp4: 이미지 시퀀스(concat demuxer) + 내레이션(뒤를 무음으로 채움)
        lst = parts / f"{sid}.txt"
        lines = []
        for img, d in images:
            lines.append(f"file '{img.as_posix()}'")
            lines.append(f"duration {d:.3f}")
        lines.append(f"file '{images[-1][0].as_posix()}'")   # concat demuxer: 마지막 프레임 유지용
        lst.write_text("\n".join(lines) + "\n", encoding="utf-8")
        p = parts / f"{sid}.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", clip.audio_path,
             "-filter_complex", f"[0:v]fps=30,format=yuv420p[v];[1:a]aresample=48000,apad[a]",
             "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
             "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-t", f"{dur:.3f}", str(p)])
        part_files.append(p)

        # 자막 큐 (문장 단위, 긴 문장은 나눔)
        for s in clip.sentences:
            start, end = t_global + s.start, t_global + s.end
            pieces = split_long_sentence(s.text)
            total = sum(len(x) for x in pieces) or 1
            t = start
            span = max(end - start, 0.6)
            for piece in pieces:
                d = span * len(piece) / total
                cues.append(Cue(cue_idx, t, t + d, wrap_korean(piece)))
                cue_idx += 1
                t += d
        t_global += dur

    # 이어 붙이기
    all_lst = out / "parts.txt"
    all_lst.write_text("\n".join(f"file '{p.as_posix()}'" for p in part_files) + "\n", encoding="utf-8")
    joined = out / "joined.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(all_lst), "-c", "copy", str(joined)])

    # 자막 번인 (파이프라인과 같은 ASS 스타일, 맑은 고딕)
    ass = out / "studio_guide.ass"
    write_ass(cues, ass, font=args.font)
    final = out / "studio_guide.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-i", "joined.mp4", "-vf", "ass=studio_guide.ass", "-c:v", "libx264", "-preset", "medium",
         "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", "studio_guide.mp4"], cwd=out)
    print(f"완료: {final}  ({final.stat().st_size / 1e6:.1f} MB, 약 {t_global:.0f}s, 자막 {len(cues)}개)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="output/studio_guide")
    ap.add_argument("--font", default="Malgun Gothic")
    build(ap.parse_args())
