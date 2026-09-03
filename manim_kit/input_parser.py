"""
사용자 입력 → LaTeX / SubstitutionSpec 변환.

일반 LaTeX을 쓰고, 아래 shortcut만 추가 지원:

  f`(x)        → f'(x)     (백틱 = 프라임, LaTeX 몰라도 OK)
  [식]_{x=2}   → x=2 대입  (대입 애니메이션)
  3 2^2        → 3 \\cdot 2^2  (공백 곱셈)

입력 예:
  \\lim_{h \\to 0} \\frac{f(2+h)-f(2)}{h} = f`(2)
  [f`(x)=3x^2-8]_{x=2}
  f`(2)=3 2^2-8 =4
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from manim_kit.substitution import SubstitutionSpec


@dataclass
class ParsedProblem:
    """parse_input() 결과."""

    raw_lines: list[str]
    problem_latex: str | None = None
    header_latex: list[str] = field(default_factory=list)
    substitution_steps: list[str] = field(default_factory=list)
    highlight: str = "x"
    sub_var: str = "x"
    sub_value: str | None = None


def prime_to_latex(s: str) -> str:
    """f`(x) → f'(x)  (프라임을 백틱으로 쓸 때)"""
    return re.sub(r"(\w)`", r"\1'", s)


def implicit_mul_to_latex(s: str) -> str:
    """3 2^2 → 3 \\cdot 2^2"""
    return re.sub(r"(\d)\s+(\d)", r"\1 \\cdot \2", s)


def normalize_line(expr: str) -> str:
    """LaTeX 한 줄 + shortcut 정리 → MathTex용."""
    s = prime_to_latex(expr.strip())
    s = implicit_mul_to_latex(s)
    s = re.sub(r"\s*=\s*", " = ", s)
    return s.strip()


# 하위 호환 alias
dsl_to_latex = normalize_line


def _parse_sub_line(line: str) -> tuple[list[str], str, str]:
    """[f`(x)=3x^2-8]_{x=2} → (steps, var, value)"""
    m = re.match(r"\[(.+)\]_\{([^=]+)=([^}]+)\}", line.strip())
    if not m:
        raise ValueError(f"대입 문법 아님: {line}")

    expr_latex = normalize_line(m.group(1))
    var, val = m.group(2).strip(), m.group(3).strip()
    return [expr_latex, _substitute_var(expr_latex, var, val)], var, val


def _substitute_var(expr: str, var: str, val: str) -> str:
    lhs, _, rhs = expr.partition("=")
    lhs, rhs = lhs.strip(), rhs.strip()

    rhs_sub = re.sub(rf"(\d){re.escape(var)}", rf"\1 \\cdot {val}", rhs)
    rhs_sub = re.sub(rf"(?<![a-zA-Z0-9]){re.escape(var)}(?![a-zA-Z0-9])", val, rhs_sub)
    rhs_sub = implicit_mul_to_latex(rhs_sub)

    if f"{var}'(" in lhs or f"{var}(" in lhs:
        lhs_sub = re.sub(rf"{re.escape(var)}'\(", f"{var}'({val}", lhs)
        lhs_sub = re.sub(rf"{re.escape(var)}\(", f"{var}({val}", lhs_sub)
    else:
        lhs_sub = re.sub(
            rf"(?<![a-zA-Z0-9]){re.escape(var)}(?![a-zA-Z0-9])", val, lhs
        )

    return f"{lhs_sub} = {rhs_sub}"


def _parse_calc_line(line: str) -> list[str]:
    """f`(2)=3 2^2-8 =4 → 계산 단계 리스트"""
    s = normalize_line(line)
    parts = [p.strip() for p in s.split("=")]
    if len(parts) <= 2:
        return [s]

    steps = []
    lhs = parts[0]
    for i in range(1, len(parts)):
        chunk = parts[i]
        if i == len(parts) - 1 and len(parts) > 2:
            prev_lhs = steps[-1].split("=")[0].strip() if steps else lhs
            steps.append(f"{prev_lhs} = {chunk}")
        else:
            steps.append(f"{lhs} = {chunk}")
            lhs = chunk.split()[0] if chunk else lhs
    return steps


def _is_calc_line(line: str) -> bool:
    """f`(2)=...=4 처럼 값 대입·계산 줄."""
    s = prime_to_latex(line)
    return bool(re.match(r"^f['`]?\(\d", s)) and line.count("=") >= 2


def parse_input(text: str) -> ParsedProblem:
    """여러 줄 입력 파싱. 1줄=LaTeX 문제식, [..]_{x=n}=대입, f`(2)=..=답=계산."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip() and not ln.startswith("#")]
    result = ParsedProblem(raw_lines=lines)
    all_sub_steps: list[str] = []

    for line in lines:
        if line.startswith("[") and "_{" in line:
            steps, var, val = _parse_sub_line(line)
            all_sub_steps.extend(steps)
            result.sub_var = var
            result.sub_value = val
            result.highlight = var
        elif _is_calc_line(line):
            all_sub_steps.extend(_parse_calc_line(line))
        else:
            latex = normalize_line(line)
            if result.problem_latex is None:
                result.problem_latex = latex
            else:
                result.header_latex.append(latex)

    seen: set[str] = set()
    result.substitution_steps = [s for s in all_sub_steps if not (s in seen or seen.add(s))]
    return result


# 하위 호환 alias
parse_dsl = parse_input


def substitution_spec_from_input(text: str, anchor, scale: float = 0.58) -> SubstitutionSpec:
    parsed = parse_input(text)
    if len(parsed.substitution_steps) < 2:
        raise ValueError("대입/계산 단계가 2개 이상 필요합니다.")
    key_map = {parsed.highlight: parsed.sub_value} if parsed.sub_value else None
    return SubstitutionSpec(
        steps=parsed.substitution_steps,
        anchor=anchor,
        scale=scale,
        highlight=parsed.highlight,
        key_map=key_map,
    )


substitution_spec_from_dsl = substitution_spec_from_input


SUNEUNG_2_INPUT = r"""
\lim_{h \to 0} \frac{f(2+h)-f(2)}{h} = f`(2)
[f`(x)=3x^2-8]_{x=2}
f`(2)=3 2^2-8 =4
"""

# 하위 호환
SUNEUNG_2_DSL = SUNEUNG_2_INPUT
