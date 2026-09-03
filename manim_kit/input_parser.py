"""
사용자 입력 DSL → LaTeX / SubstitutionSpec 변환.

입력 예:
  \\lim{h->0}{나누기{f(2+h)-f(2)}{h}}=f`(2)
  [f`(x)=3x^2-8]_{x=2}
  f`(2)=3 2^2-8 =4
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from manim_kit.substitution import SubstitutionSpec


# ---------------------------------------------------------------------------
# DSL 규칙
# ---------------------------------------------------------------------------
# f`(x)     → f'(x)          (백틱 ` = 프라임)
# \lim{a->b}{...}  → \lim_{a \to b}{...}
# 나누기{a}{b}     → \frac{a}{b}
# [식]_{x=2}       → x=2 대입 (대입 애니메이션 1·2단계 생성)
# 3 2^2            → 3 \cdot 2^2  (공백 곱셈)
# ---------------------------------------------------------------------------


@dataclass
class ParsedProblem:
    """parse_dsl() 결과."""

    raw_lines: list[str]
    problem_latex: str | None = None
    header_latex: list[str] = field(default_factory=list)
    substitution_steps: list[str] = field(default_factory=list)
    highlight: str = "x"
    sub_var: str = "x"
    sub_value: str | None = None


def prime_to_latex(s: str) -> str:
    """f`(x) → f'(x)"""
    return re.sub(r"(\w)`", r"\1'", s)


def implicit_mul_to_latex(s: str) -> str:
    """3 2^2 → 3 \\cdot 2^2"""
    return re.sub(r"(\d)\s+(\d)", r"\1 \\cdot \2", s)


def _find_brace_block(s: str, start: int) -> tuple[str, int]:
    if start >= len(s) or s[start] != "{":
        raise ValueError(f"expected '{{' at {start}")
    depth = 0
    i = start
    while i < len(s):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start + 1 : i], i + 1
        i += 1
    raise ValueError("unmatched brace")


def _replace_lim(s: str) -> str:
    out = []
    i = 0
    while i < len(s):
        if s.startswith("\\lim{", i):
            i += 4  # `\lim` 다음 `{` 위치
            var_part, i = _find_brace_block(s, i)
            body, i = _find_brace_block(s, i)
            var, _, to = var_part.partition("->")
            out.append(rf"\lim_{{{var.strip()} \to {to.strip()}}} {dsl_to_latex(body)}")
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def _replace_frac(s: str) -> str:
    key = "나누기"
    while key in s:
        idx = s.index(key)
        num, end1 = _find_brace_block(s, idx + len(key))
        den, end2 = _find_brace_block(s, end1)
        repl = rf"\frac{{{dsl_to_latex(num)}}}{{{dsl_to_latex(den)}}}"
        s = s[:idx] + repl + s[end2:]
    return s


def dsl_to_latex(expr: str) -> str:
    """DSL 한 줄 → Manim MathTex용 LaTeX."""
    s = prime_to_latex(expr.strip())
    while "\\lim{" in s:
        s = _replace_lim(s)
    s = _replace_frac(s)
    s = implicit_mul_to_latex(s)
    s = re.sub(r"\s*=\s*", " = ", s)
    return s.strip()


def _parse_sub_line(line: str) -> tuple[list[str], str, str]:
    """[f`(x)=3x^2-8]_{x=2} → (steps, var, value)"""
    m = re.match(r"\[(.+)\]_\{([^=]+)=([^}]+)\}", line.strip())
    if not m:
        raise ValueError(f"대입 문법 아님: {line}")

    expr_latex = dsl_to_latex(m.group(1))
    var, val = m.group(2).strip(), m.group(3).strip()
    return [expr_latex, _substitute_var(expr_latex, var, val)], var, val


def _substitute_var(expr: str, var: str, val: str) -> str:
    lhs, _, rhs = expr.partition("=")
    lhs, rhs = lhs.strip(), rhs.strip()

    # 3x^2 → 3·2^2 (계수 붙은 x)
    rhs_sub = re.sub(rf"(\d){re.escape(var)}", rf"\1 \\cdot {val}", rhs)
    rhs_sub = re.sub(rf"(?<![a-zA-Z0-9]){re.escape(var)}(?![a-zA-Z0-9])", val, rhs_sub)
    rhs_sub = implicit_mul_to_latex(rhs_sub)

    lhs_sub = lhs
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
    s = dsl_to_latex(line)
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


def parse_dsl(text: str) -> ParsedProblem:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    result = ParsedProblem(raw_lines=lines)
    all_sub_steps: list[str] = []

    for line in lines:
        if line.startswith("[") and "_{" in line:
            steps, var, val = _parse_sub_line(line)
            all_sub_steps.extend(steps)
            result.sub_var = var
            result.sub_value = val
            result.highlight = var
        elif re.match(r"^f`\(\d", line) or re.match(r"^f'\(\d", prime_to_latex(line)):
            all_sub_steps.extend(_parse_calc_line(line))
        else:
            latex = dsl_to_latex(line)
            if result.problem_latex is None:
                result.problem_latex = latex
            else:
                result.header_latex.append(latex)

    seen: set[str] = set()
    result.substitution_steps = [s for s in all_sub_steps if not (s in seen or seen.add(s))]
    return result


def substitution_spec_from_dsl(text: str, anchor, scale: float = 0.58) -> SubstitutionSpec:
    parsed = parse_dsl(text)
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


SUNEUNG_2_DSL = r"""
\lim{h->0}{나누기{f(2+h)-f(2)}{h}}=f`(2)
[f`(x)=3x^2-8]_{x=2}
f`(2)=3 2^2-8 =4
"""
