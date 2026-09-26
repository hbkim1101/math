"""식 전개(derivation) 엔진 — 학생이 '어디서 어디로' 바뀌었는지 눈으로 따라갈 수 있는 판서.

한 줄(step)은 여러 조각(parts)으로 이루어진 MathTex 이다. 새 줄을 쓸 때 이전 줄과 조각을 맞춰
  - 그대로인 조각은 이전 줄에서 새 자리로 미끄러져 내려오고 (TransformFromCopy)
  - 바뀌는 조각은 이전 줄의 '출처'가 상자로 강조된 뒤 새 자리로 날아가 변형되며 (강조색)
  - 등호 반대편으로 옮겨 간 조각(이항)은 호를 그리며 건너가고 새 부호가 강조되고
  - 완전히 새로운 조각은 강조색 손글씨로 쓰인다.
그 옆에 (∵ 이유) 주석을 적고, 소거는 취소선, 결과는 상자로 강조한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, DL, DR, UR, PI,
    AnimationGroup, Circumscribe, Create, DrawBorderThenFill, FadeOut, Line, MathTex, Mobject, RoundedRectangle,
    TransformFromCopy, VGroup,
)

from .chalk import handwrite, handwrite_time
from .theme import MATH_TEX_TEMPLATE

# 바뀐 조각의 강조색: 칠판의 흰 분필과 뚜렷이 구분되는 진한 노란 분필
DERIVE_ACCENT = "#ffd23f"

# 매칭에서 '내용'으로 취급하지 않는 조각(연산자·괄호). 이들은 그대로면 슬라이드, 새로 생기면 빠르게 쓴다.
OPERATORS = {
    "=", "+", "-", "\\times", "\\cdot", "(", ")", "\\left(", "\\right)", ",", "\\Rightarrow", "\\therefore",
    "\\quad", "\\qquad", "\\;", "\\,", "\\iff", "\\Leftrightarrow", "<", ">", "\\le", "\\ge", "\\pm",
}


def is_operator(s: str) -> bool:
    return s.strip() in OPERATORS


@dataclass
class DerivLine:
    parts: list[str]
    mob: MathTex
    eq_index: Optional[int] = None
    extras: list[Mobject] = field(default_factory=list)   # why 주석, 상자, 취소선 등

    @property
    def part_mobs(self) -> list[Mobject]:
        return list(self.mob.submobjects)

    def side_of(self, i: int) -> int:
        """조각 i 가 등호의 왼쪽(-1)/오른쪽(+1)/등호 없음(0)."""
        if self.eq_index is None:
            return 0
        return -1 if i < self.eq_index else (1 if i > self.eq_index else 0)


@dataclass
class MatchPlan:
    slide: list[tuple[int, int]]        # (prev_i, new_i) 그대로 이동
    move: list[tuple[int, int]]         # (prev_i, new_i) 이항(등호 건너감)
    morph: list[tuple[int, int]]        # (prev_i, new_i) 출처 → 변형
    new: list[int]                      # 새로 쓰는 조각(내용)
    ops: list[int]                      # 새로 쓰는 연산자
    sources: list[int]                  # 강조만 하는 출처(짝 없는 것)


def plan_match(prev: Optional[DerivLine], parts: list[str], from_map: dict[str, str] | None = None,
               focus: list[str] | None = None, new: list[str] | None = None) -> MatchPlan:
    """이전 줄과 새 줄의 조각을 짝짓는다 (순수 함수 → 테스트 가능)."""
    n = len(parts)
    if prev is None:
        return MatchPlan([], [], [], [i for i in range(n) if not is_operator(parts[i])],
                         [i for i in range(n) if is_operator(parts[i])], [])
    used_prev: set[int] = set()
    assigned: dict[int, int] = {}    # new_i -> prev_i
    morph: list[tuple[int, int]] = []
    pparts = prev.parts

    def take(s: str, near: int, allow_reuse: bool = False) -> Optional[int]:
        cands = [j for j, q in enumerate(pparts) if q == s and j not in used_prev]
        if not cands and allow_reuse:
            cands = [j for j, q in enumerate(pparts) if q == s]
        if not cands:
            return None
        j = min(cands, key=lambda j: abs(j - near))
        used_prev.add(j)
        return j

    # 1) 명시 매핑 (대입·합치기): new 조각 문자열 → prev 조각 문자열(또는 목록: 여러 출처가 한 조각으로 합쳐짐).
    #    prev 가 부족하면 같은 출처를 다시 쓴다 (x 하나가 여러 자리의 2 로 대입되는 경우).
    for i, s in enumerate(parts):
        if from_map and s in from_map:
            srcs = from_map[s]
            if isinstance(srcs, str):
                srcs = [srcs]
            for k, src_s in enumerate(srcs):
                j = take(src_s, i, allow_reuse=(k == 0))
                if j is not None:
                    if i not in assigned:
                        assigned[i] = j
                    morph.append((j, i))
    # 2) 문자열이 같은 조각은 슬라이드/이항
    slide: list[tuple[int, int]] = []
    move: list[tuple[int, int]] = []
    for i, s in enumerate(parts):
        if i in assigned:
            continue
        j = take(s, i)
        if j is None:
            continue
        assigned[i] = j
        side_prev, side_new = prev.side_of(j), _side(parts, i)
        if (not is_operator(s)) and side_prev != 0 and side_new != 0 and side_prev != side_new:
            move.append((j, i))
        else:
            slide.append((j, i))
    # 3) 남은 내용 조각: 출처(prev) ↔ 대상(new) 순서대로 짝지어 변형
    if focus is not None:
        src = [j for j, q in enumerate(pparts) if q in focus and j not in used_prev]
    else:
        src = [j for j, q in enumerate(pparts) if j not in used_prev and not is_operator(q)]
        # 연쇄 등식("= …"로 이어지는 줄)은 앞줄의 우변만 바뀐 것이므로 좌변은 출처로 삼지 않는다
        if _eq_index(parts) == 0 and prev.eq_index is not None:
            src = [j for j in src if prev.side_of(j) == 1]
    if new is not None:
        tgt = [i for i, s in enumerate(parts) if s in new and i not in assigned]
    else:
        tgt = [i for i, s in enumerate(parts) if i not in assigned and not is_operator(s)]
    # 출처와 대상을 순서대로 짝짓고, 남는 대상은 새로 쓴다. 출처가 더 많으면(두 항이 하나로 합쳐짐) 마지막 대상으로 모인다.
    for j, i in zip(src, tgt):
        morph.append((j, i))
        assigned[i] = j
        used_prev.add(j)
    if tgt:
        for j in src[len(tgt):]:
            morph.append((j, tgt[-1]))
            used_prev.add(j)
        src = src[:len(tgt)]
    new_idx = [i for i in tgt if i not in assigned]
    ops = [i for i, s in enumerate(parts) if i not in assigned and is_operator(s) and i not in new_idx]
    if new is not None:
        # 명시된 new 에 없는 남은 내용 조각도 새로 쓴다
        new_idx += [i for i, s in enumerate(parts) if i not in assigned and not is_operator(s) and i not in new_idx]
    sources = [j for j in src[len(tgt):]]
    return MatchPlan(slide, move, morph, new_idx, ops, sources)


def _side(parts: list[str], i: int) -> int:
    eq = _eq_index(parts)
    if eq is None:
        return 0
    return -1 if i < eq else (1 if i > eq else 0)


def _eq_index(parts: list[str]) -> Optional[int]:
    for k, s in enumerate(parts):
        if s.strip() == "=":
            return k
    return None


class Derivation:
    """한 섹션 안의 식 전개 묶음. 등호를 세로로 맞춰 가며 줄을 더한다."""

    def __init__(self, scene, sec, did: str, scale: float, color: str | None, indent: float = 0.0,
                 accent: str | None = None, why_color: str | None = None, keep_color: bool = False):
        self.scene = scene
        self.sec = sec
        self.id = did
        self.scale = scale
        self.base_color = scene.color(color, scene.theme.text)
        self.accent = scene.color(accent, DERIVE_ACCENT)
        self.why_color = scene.color(why_color, scene.theme.palette.get("log", scene.theme.muted))
        self.keep_color = keep_color
        self.indent = indent
        self.lines: list[DerivLine] = []
        self.eq_x: Optional[float] = None
        self.note_x: Optional[float] = None
        self.group = VGroup()
        scene.register(did, self.group)

    # ------------------------------------------------------------------ 배치
    @property
    def notes_right(self) -> float:
        return self.sec.notes_left + self.sec.notes_width

    def _build(self, parts: list[str]) -> MathTex:
        m = MathTex(*parts, tex_template=MATH_TEX_TEMPLATE)
        m.set_color(self.base_color)
        m.scale(self.scale)
        return self.scene.finish_text(m)

    def _place(self, mob: MathTex, parts: list[str], same_line: str | bool, indent: float) -> bool:
        """줄 위치를 정한다. 같은 줄에 이어 쓰면 True."""
        cv = self.scene.chalk
        sec = self.sec
        left0 = sec.notes_left + self.indent + indent
        max_w = self.notes_right - left0
        if mob.width > max_w:
            mob.scale_to_fit_width(max_w)
        eq = _eq_index(parts)
        prev = self.lines[-1] if self.lines else None

        starts_with_eq = eq == 0
        want_same = same_line is True or (same_line == "auto" and prev is not None and prev.eq_index is None
                                          and starts_with_eq)
        if prev is not None and want_same and starts_with_eq:
            buff = 0.22 * self.scale / 0.7
            x = prev.mob.get_right()[0] + buff
            if x + mob.width <= self.notes_right + 1e-6:
                mob.move_to(np.array([x, prev.mob.get_center()[1], 0.0]), aligned_edge=LEFT)
                # 등호 높이를 이전 줄(수식 중앙)에 맞춘다
                dy = prev.mob.get_center()[1] - mob[0].get_center()[1]
                mob.shift(UP * dy)
                self.eq_x = float(mob[0].get_center()[0])
                sec.cursor_y = min(sec.cursor_y, mob.get_bottom()[1] - cv.line_gap)
                sec.lines.append(mob)
                return True
        if starts_with_eq and self.eq_x is not None:
            mob.move_to(np.array([self.eq_x, sec.cursor_y, 0.0]), aligned_edge=UP)
            mob.shift(RIGHT * (self.eq_x - mob[0].get_center()[0]))
            if mob.get_right()[0] > self.notes_right:
                over = mob.get_right()[0] - self.notes_right
                if mob.get_left()[0] - over >= sec.notes_left:
                    mob.shift(LEFT * over)
                else:
                    mob.scale_to_fit_width(mob.width - over)
                    mob.move_to(np.array([self.notes_right, sec.cursor_y, 0.0]), aligned_edge=UR)
            sec.cursor_y -= mob.height + cv.line_gap
            sec.lines.append(mob)
            return False
        cv.place_line(mob, indent=self.indent + indent, sec=sec)
        if eq is not None:
            self.eq_x = float(mob[eq].get_center()[0])
        return False

    # ------------------------------------------------------------------ 한 단계
    def step(self, parts: list[str], same_line: str | bool = "auto", focus: list[str] | None = None,
             new: list[str] | None = None, from_map: dict[str, str] | None = None, why: str | None = None,
             box: bool = False, underline: bool = False, cancel: list[str] | None = None,
             run_time: float | None = None, indent: float = 0.0, color: str | None = None,
             pulse: bool = False, space: float = 0.0, hold=None, cancel_hold=None) -> DerivLine:
        """hold: 출처 상자를 그린 뒤 호출되는 콜러블(예: 다음 문장까지 대기). 짚어 주기와 움직이기를 내레이션에 따로 맞춘다."""
        scene = self.scene
        cv = scene.chalk
        sec = self.sec
        if space:
            sec.cursor_y -= space
        prev = self.lines[-1] if self.lines else None
        mob = self._build(parts)
        if color:
            mob.set_color(scene.color(color))
        self._place(mob, parts, same_line, indent)
        line = DerivLine(parts=parts, mob=mob, eq_index=_eq_index(parts))
        plan = plan_match(prev, parts, from_map, focus, new)
        pm = line.part_mobs
        rt_scale = 1.0 if run_time is None else float(run_time) / 2.0

        # 0) 이전 줄들의 강조색을 기본색으로 되돌린다 (현재 단계만 색이 있게)
        revert = []
        if not self.keep_color:
            for ln in self.lines:
                for p in ln.part_mobs:
                    if getattr(p, "_deriv_accent", False):
                        p._deriv_accent = False
                        revert.append(p.animate.set_color(self.base_color))

        # 1) 출처 강조: 변형/이항의 출처를 상자로 감싼다
        hl_rects: list[Mobject] = []
        src_idx = [j for j, _ in plan.morph] + [j for j, _ in plan.move] + plan.sources
        if prev is not None and src_idx:
            for j in src_idx:
                sp = prev.part_mobs[j]
                # 형광펜처럼 옅게 채운 상자: 글자 뒤(z<0)에 깔려 출처가 멀리서도 눈에 띈다
                r = RoundedRectangle(corner_radius=0.08, width=sp.width + 0.2, height=sp.height + 0.2,
                                     stroke_color=self.accent, stroke_width=3.0,
                                     fill_color=self.accent, fill_opacity=0.16).move_to(sp)
                r.set_z_index(-1)
                hl_rects.append(r)
            scene.play(*[DrawBorderThenFill(r) for r in hl_rects], *revert, run_time=0.6 * rt_scale)
            revert = []
            if hold is not None:
                hold()
        elif revert:
            scene.play(*revert, run_time=0.3)

        # 2) 두 단계로 움직인다: (A) 그대로인 조각이 먼저 미끄러져 내려와 뼈대를 만들고,
        #    (B) 강조된 조각이 출처에서 날아와 빈자리에 들어간다 → 바뀐 곳이 한눈에 보인다
        phase_a = []
        for j, i in plan.slide:
            phase_a.append(TransformFromCopy(prev.part_mobs[j], pm[i], run_time=0.9 * rt_scale))
        for i in plan.ops:
            # 새 부호: 이항으로 생긴 부호(+/-)면 강조색으로 (B) 단계에서, 아니면 기본색으로 (A) 단계에서 쓴다
            if any(abs(i - k) == 1 for _, k in plan.move):
                pm[i].set_color(self.accent)
                pm[i]._deriv_accent = True
            else:
                phase_a.append(handwrite(pm[i], run_time=0.4 * rt_scale))
        phase_b = []
        for j, i in plan.move:
            pm[i].set_color(self.accent)
            pm[i]._deriv_accent = True
            dx = pm[i].get_center()[0] - prev.part_mobs[j].get_center()[0]
            phase_b.append(TransformFromCopy(prev.part_mobs[j], pm[i], path_arc=-PI / 2.2 if dx > 0 else PI / 2.2,
                                             run_time=1.3 * rt_scale))
        for i in plan.ops:
            if getattr(pm[i], "_deriv_accent", False):
                phase_b.append(handwrite(pm[i], run_time=0.4 * rt_scale))
        ghosts: list[Mobject] = []
        morph_targets: set[int] = set()
        for j, i in plan.morph:
            pm[i].set_color(self.accent)
            pm[i]._deriv_accent = True
            if i in morph_targets:
                # 여러 출처가 한 조각으로 합쳐질 때: 두 번째 출처부터는 '유령' 복사본이 날아와 겹친 뒤 사라진다
                # (같은 mobject 에 Transform 을 두 번 걸면 점 데이터가 깨진다)
                ghost = pm[i].copy().set_opacity(0.85)
                ghosts.append(ghost)
                phase_b.append(TransformFromCopy(prev.part_mobs[j], ghost, path_arc=-PI / 6, run_time=1.2 * rt_scale))
                continue
            morph_targets.add(i)
            phase_b.append(TransformFromCopy(prev.part_mobs[j], pm[i], path_arc=-PI / 6, run_time=1.2 * rt_scale))
        for i in plan.new:
            pm[i].set_color(self.accent)
            pm[i]._deriv_accent = True
            phase_b.append(handwrite(pm[i], run_time=max(0.6, handwrite_time(pm[i], per_glyph=0.07, hi=2.4)) * rt_scale))
        if prev is None:
            # 첫 줄은 통째로 판서 (강조 없음)
            for i in plan.new + plan.ops:
                pm[i].set_color(self.base_color if color is None else scene.color(color))
                pm[i]._deriv_accent = False
            scene.play(handwrite(mob, run_time=run_time if run_time is not None else handwrite_time(mob, per_glyph=0.05, hi=2.6)))
        else:
            if phase_a:
                scene.play(AnimationGroup(*phase_a, lag_ratio=0.05))
            if phase_b:
                if hl_rects:
                    scene.wait(0.2 * rt_scale)   # 출처 상자를 잠깐 보여 준 뒤 날린다
                scene.play(AnimationGroup(*phase_b, lag_ratio=0.1))
        # 3) 출처 상자 정리 (조각은 씬에 개별로 들어갔으므로 줄 단위로 다시 묶는다)
        scene.remove(*pm, mob, *ghosts)
        scene.add(mob)
        after = [FadeOut(r, run_time=0.4) for r in hl_rects]
        self.lines.append(line)
        self.group.add(mob)
        scene.register(f"{self.id}_{len(self.lines) - 1}", mob)

        # 4) 이유 주석
        if why:
            note = self._why_note(why, mob, indent)
            line.extras.append(note)
            self.group.add(note)
            scene.play(*after, handwrite(note, run_time=max(0.6, min(1.6, handwrite_time(note, per_glyph=0.03)))))
            after = []
        if after:
            scene.play(*after)

        # 5) 소거(취소선)
        if cancel:
            if cancel_hold is not None:
                cancel_hold()
            strikes = []
            for i, s in enumerate(parts):
                if s in cancel or i in cancel:
                    p = pm[i]
                    ln = Line(p.get_corner(DL) + DL * 0.05, p.get_corner(UR) + UR * 0.05,
                              stroke_color=scene.theme.palette.get("warn", self.accent), stroke_width=3)
                    ln.set_z_index(6)
                    strikes.append(ln)
            if strikes:
                line.extras.extend(strikes)
                self.group.add(*strikes)
                scene.play(*[Create(s) for s in strikes], run_time=0.5)

        # 6) 결과 강조
        if box or underline:
            hl = self.accent
            if box:
                mark = RoundedRectangle(corner_radius=0.1, width=mob.width + 0.4, height=mob.height + 0.3,
                                        fill_opacity=0, stroke_color=hl, stroke_width=3).move_to(mob)
                cv.advance(0.18, sec)
            else:
                mark = Line(mob.get_corner(DL) + DOWN * 0.08, mob.get_corner(DR) + DOWN * 0.08,
                            stroke_color=hl, stroke_width=3)
                cv.advance(0.1, sec)
            mark.set_z_index(3)
            line.extras.append(mark)
            self.group.add(mark)
            scene.register(f"{self.id}_{len(self.lines) - 1}_mark", mark)
            scene.play(Create(mark), run_time=0.5)
            if pulse:
                scene.play(Circumscribe(mark, color=hl, buff=0.08), run_time=0.8)
        elif pulse:
            scene.play(Circumscribe(mob, color=self.accent, buff=0.1), run_time=0.8)
        return line

    def _why_note(self, why: str, mob: Mobject, indent: float) -> Mobject:
        """(∵ 이유) 메모. 식 오른쪽의 '이유 칸'에 세로로 맞춰 적고, 자리가 없으면 식 아래 오른쪽에 적는다."""
        text = why.strip()
        if not text.startswith("("):
            text = rf"($\because$ {text})"
        sec = self.sec
        sc = self.scale * 0.64
        gap = 0.45
        x = mob.get_right()[0] + gap
        if self.note_x is not None and self.note_x >= x:
            x = self.note_x
        avail = self.notes_right - x
        note = self.scene.ktex(text, scale=sc, color=None)
        if note.width > avail and avail >= 3.0:
            note = self.scene.ktex(text, scale=sc, color=None, width=avail)
        note.set_color(self.why_color)
        if note.width <= avail + 1e-6:
            note.move_to(np.array([x, mob.get_center()[1], 0.0]), aligned_edge=LEFT)
            if self.note_x is None or x < self.note_x:
                self.note_x = x
            if note.get_bottom()[1] < sec.cursor_y + self.scene.chalk.line_gap:
                sec.cursor_y = note.get_bottom()[1] - self.scene.chalk.line_gap
            return note
        # 오른쪽에 자리가 없다: 식 아래, 오른쪽 맞춤
        width = min(note.width, self.notes_right - (sec.notes_left + self.indent + indent) - 0.8)
        if note.width > width:
            note = self.scene.ktex(text, scale=sc, color=None, width=width).set_color(self.why_color)
        note.move_to(np.array([self.notes_right, sec.cursor_y + self.scene.chalk.line_gap * 0.5, 0.0]), aligned_edge=UR)
        sec.cursor_y = note.get_bottom()[1] - self.scene.chalk.line_gap
        return note
