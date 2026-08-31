#!/usr/bin/env python3
"""수학 한수 스타일 자동 영상 생성 CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pipeline.runner import VideoPipeline, enrich_exam_file  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="수학 한수 스타일 자동 해설 영상 생성")
    sub = parser.add_subparsers(dest="command", required=True)

    render = sub.add_parser("render", help="YAML 문제 파일에서 영상 렌더")
    render.add_argument("exam", type=Path, help="exam YAML 경로")
    render.add_argument("--id", type=int, required=True, help="문항 번호")
    render.add_argument("-q", "--quality", default="l", choices=["l", "m", "h"], help="Manim quality")
    render.add_argument("--no-tts", action="store_true", help="TTS 나레이션 비활성화")

    gen = sub.add_parser("generate", help="텍스트 문제 → YAML + 영상")
    gen.add_argument("text", help="문제 텍스트")
    gen.add_argument("--topic", default="수학")
    gen.add_argument("--id", type=int, default=1)
    gen.add_argument("-q", "--quality", default="l", choices=["l", "m", "h"])

    enrich = sub.add_parser("enrich", help="YAML에 시각화 플랜 자동 추가")
    enrich.add_argument("exam", type=Path)
    enrich.add_argument("-o", "--output", type=Path)

    batch = sub.add_parser("batch", help="exam 파일의 모든 문항 렌더")
    batch.add_argument("exam", type=Path)
    batch.add_argument("-q", "--quality", default="l", choices=["l", "m", "h"])
    batch.add_argument("--no-tts", action="store_true")

    args = parser.parse_args()
    pipeline = VideoPipeline(ROOT)

    if args.command == "render":
        result = pipeline.run(
            args.exam.resolve(),
            args.id,
            quality=args.quality,
            with_tts=not args.no_tts,
        )
        print(f"✓ Final: {result.final}")
        print(f"  SRT:   {result.srt}")
        return

    if args.command == "generate":
        result = pipeline.from_text(args.text, topic=args.topic, problem_id=args.id, quality=args.quality)
        print(f"✓ Final: {result.final}")
        return

    if args.command == "enrich":
        out = enrich_exam_file(args.exam.resolve(), args.output.resolve() if args.output else None)
        print(f"✓ Enriched: {out}")
        return

    if args.command == "batch":
        from src.dsl.models import load_exam

        exam = load_exam(args.exam.resolve())
        for p in exam.problems:
            print(f"\n>>> Rendering problem {p.id}: {p.topic}")
            try:
                result = pipeline.run(
                    args.exam.resolve(),
                    p.id,
                    quality=args.quality,
                    with_tts=not args.no_tts,
                )
                print(f"    → {result.final}")
            except Exception as exc:
                print(f"    ✗ Failed: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
