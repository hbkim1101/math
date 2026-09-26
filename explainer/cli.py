"""명령줄 인터페이스.

    python -m explainer build projects/2027_sep_q22/project.yaml            # 최종 렌더
    python -m explainer build projects/.../project.yaml --preview           # 480p 빠른 확인
    python -m explainer timing projects/.../project.yaml                    # 문장별 타이밍표
    python -m explainer verify output/2027_sep_q22                          # 기존 산출물 재검증
    python -m explainer validate projects/.../project.yaml                  # YAML 문법/참조 검사
    python -m explainer actions                                             # 사용 가능한 액션 목록
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="explainer", description="수학 해설 영상 스튜디오")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="프로젝트 렌더링")
    b.add_argument("project")
    b.add_argument("--out", default="output")
    b.add_argument("--preview", action="store_true", help="480p/15fps 빠른 렌더")
    b.add_argument("--force-tts", action="store_true", help="TTS 캐시 무시")
    b.add_argument("--no-verify", action="store_true")
    b.add_argument("--segments", default=None, help="쉼표로 구분한 세그먼트 id 만 렌더 (부분 확인)")

    t = sub.add_parser("timing", help="문장별 내레이션 타이밍표 출력")
    t.add_argument("project")
    t.add_argument("--out", default="output")

    v = sub.add_parser("verify", help="산출물 재검증")
    v.add_argument("out_dir")

    va = sub.add_parser("validate", help="시나리오 YAML 검사")
    va.add_argument("project")
    va.add_argument("--tex", action="store_true", help="모든 LaTeX 문자열을 미리 컴파일해 검사")

    sb = sub.add_parser("storyboard", help="세그먼트별 대표 프레임 스토리보드 PNG 생성")
    sb.add_argument("out_dir")
    sb.add_argument("--columns", type=int, default=3)

    sub.add_parser("actions", help="액션 목록")

    st = sub.add_parser("studio", help="브라우저 편집기(Studio) 실행")
    st.add_argument("--host", default="127.0.0.1")
    st.add_argument("--port", type=int, default=8765)
    st.add_argument("--root", default=".", help="projects/ 와 output/ 이 있는 작업 폴더")
    st.add_argument("--no-browser", action="store_true")

    args = p.parse_args(argv)

    if args.cmd == "build":
        from .pipeline import build
        segs = [x.strip() for x in args.segments.split(",") if x.strip()] if args.segments else None
        final, report = build(args.project, out_root=args.out, preview=args.preview,
                              force_tts=args.force_tts, verify=not args.no_verify, segments=segs)
        return 0 if (report is None or report.ok) else 2

    if args.cmd == "timing":
        from .pipeline import timing_table
        timing_table(args.project, out_root=args.out)
        return 0

    if args.cmd == "verify":
        from .verify.checks import verify_output
        rep = verify_output(args.out_dir)
        print(rep.render_text())
        return 0 if rep.ok else 2

    if args.cmd == "validate":
        from .script.loader import load_project
        from .render.actions import REGISTRY
        proj = load_project(args.project)
        unknown = sorted({a.do for s in proj.segments for a in s.actions} - set(REGISTRY))
        n_actions = sum(len(s.actions) for s in proj.segments)
        print(f"{proj.meta.title}: 세그먼트 {len(proj.segments)}개, 액션 {n_actions}개")
        if unknown:
            print(f"알 수 없는 액션: {unknown}")
            return 2
        if args.tex:
            from .lint import lint_tex
            errors = lint_tex(proj)
            if errors:
                return 2
        print("OK")
        return 0

    if args.cmd == "storyboard":
        from .verify.storyboard import build_storyboard
        build_storyboard(args.out_dir, columns=args.columns)
        return 0

    if args.cmd == "studio":
        from .studio.server import serve
        serve(root=args.root, host=args.host, port=args.port, open_browser=not args.no_browser)
        return 0

    if args.cmd == "actions":
        from .render.actions import REGISTRY
        for name, fn in sorted(REGISTRY.items()):
            doc = (fn.__doc__ or "").strip().splitlines()
            print(f"  {name:<18} {doc[0] if doc else ''}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
