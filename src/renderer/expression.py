from __future__ import annotations

import math
import re
from typing import Callable

import numpy as np
import sympy as sp

_x = sp.Symbol("x")
_a = sp.Symbol("a")


def _normalize_expr(expr: str) -> str:
    text = expr.strip()
    text = text.replace("^", "**")
    text = re.sub(r"\b(\d+)x\b", r"\1*x", text)
    text = re.sub(r"\bx(\d+)\b", r"x*\1", text)
    text = re.sub(r"\(\s*x\s*\)", "(x)", text)
    return text


def make_function(expr: str, extra_symbols: dict[str, float] | None = None) -> Callable[[float], float]:
    """Parse a math expression string into a callable f(x)."""
    normalized = _normalize_expr(expr)
    symbols = {"x": _x, "a": _a, "e": sp.E, "pi": sp.pi}
    local = sp.sympify(normalized, locals=symbols)
    free = local.free_symbols
    subs = {s: float(extra_symbols.get(str(s), 0.0)) for s in free if str(s) != "x"}
    if subs:
        local = local.subs(subs)
    fn = sp.lambdify(_x, local, modules=["numpy"])
    return _safe_float_wrapper(fn)


def make_parametric_function(expr: str, param: str, param_value: float) -> Callable[[float], float]:
    normalized = _normalize_expr(expr)
    sym = sp.Symbol(param)
    symbols = {"x": _x, param: sym, "e": sp.E, "pi": sp.pi}
    local = sp.sympify(normalized, locals=symbols).subs(sym, param_value)
    fn = sp.lambdify(_x, local, modules=["numpy"])
    return _safe_float_wrapper(fn)


def eval_expr(expr: str, x: float, **params: float) -> float:
    fn = make_function(expr, extra_symbols=params)
    return float(fn(x))


def derivative_at(expr: str, x0: float, **params: float) -> float:
    normalized = _normalize_expr(expr)
    symbols = {"x": _x, "a": _a, "e": sp.E, "pi": sp.pi}
    local = sp.sympify(normalized, locals=symbols)
    for key, val in params.items():
        local = local.subs(sp.Symbol(key), val)
    d = sp.diff(local, _x)
    fn = sp.lambdify(_x, d, modules=["numpy"])
    return float(_safe_float_wrapper(fn)(x0))


def _safe_float_wrapper(fn: Callable[[float], float]) -> Callable[[float], float]:
    def wrapped(x: float) -> float:
        try:
            val = fn(x)
            if isinstance(val, (np.ndarray, list, tuple)):
                val = val[0]
            result = float(val)
            if math.isnan(result) or math.isinf(result):
                return 0.0
            return result
        except (TypeError, ValueError, ZeroDivisionError, OverflowError):
            return 0.0

    return wrapped
