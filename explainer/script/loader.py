"""YAML 프로젝트 로딩과 안전한 수식 평가."""

from __future__ import annotations

import ast
import math
import operator
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml

from .models import Project

_ALLOWED_FUNCS: dict[str, Callable] = {
    "log": math.log,
    "ln": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "exp": math.exp,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "abs": abs,
    "min": min,
    "max": max,
    "pi": math.pi,
    "e": math.e,
}

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY_OPS = {ast.USub: operator.neg, ast.UAdd: operator.pos}
_CMP_OPS = {
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
}


class ExpressionError(ValueError):
    pass


def _eval_node(node: ast.AST, env: Mapping[str, Any]) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, env)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ExpressionError(f"허용되지 않는 상수: {node.value!r}")
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        if node.id in _ALLOWED_FUNCS:
            return _ALLOWED_FUNCS[node.id]
        raise ExpressionError(f"정의되지 않은 이름: {node.id}")
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval_node(node.left, env), _eval_node(node.right, env))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval_node(node.operand, env))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        # env 에 등록된 함수(예: 앞서 plot 한 그래프 id)도 호출할 수 있다
        fn = env.get(node.func.id)
        if not callable(fn):
            fn = _ALLOWED_FUNCS.get(node.func.id)
        if fn is None or not callable(fn):
            raise ExpressionError(f"허용되지 않는 함수: {node.func.id}")
        args = [_eval_node(a, env) for a in node.args]
        return fn(*args)
    if isinstance(node, ast.IfExp):
        # 조각적으로 정의된 함수: `-f(x) if f(x) >= 0 else 7*f(x)`
        return _eval_node(node.body, env) if _eval_node(node.test, env) else _eval_node(node.orelse, env)
    if isinstance(node, ast.Compare) and all(type(op) in _CMP_OPS for op in node.ops):
        left = _eval_node(node.left, env)
        for op, comp in zip(node.ops, node.comparators):
            right = _eval_node(comp, env)
            if not _CMP_OPS[type(op)](left, right):
                return False
            left = right
        return True
    if isinstance(node, (ast.Tuple, ast.List)):
        return [_eval_node(e, env) for e in node.elts]
    raise ExpressionError(f"허용되지 않는 구문: {ast.dump(node)}")


def safe_eval(expr: str | int | float, env: Mapping[str, Any] | None = None) -> Any:
    """`x`, params 등의 변수만 허용하는 산술식 평가기."""
    if isinstance(expr, (int, float)):
        return expr
    env = dict(env or {})
    try:
        tree = ast.parse(str(expr).strip(), mode="eval")
    except SyntaxError as exc:
        raise ExpressionError(f"수식 구문 오류: {expr!r}") from exc
    return _eval_node(tree, env)


def make_function(expr: str, params: Mapping[str, float], var: str = "x") -> Callable[[float], float]:
    """`expr`를 `var`의 함수로 컴파일한다. (매 호출 시 안전 평가)"""
    tree = ast.parse(expr.strip(), mode="eval")

    def f(v: float) -> float:
        env = dict(params)
        env[var] = v
        return float(_eval_node(tree, env))

    return f


def resolve_params(raw: Mapping[str, Any]) -> dict[str, float]:
    """params 항목은 서로를 참조할 수 있다 (정의 순서대로 평가)."""
    out: dict[str, float] = {}
    for k, v in raw.items():
        out[k] = float(safe_eval(v, out))
    return out


def load_project(path: str | Path) -> Project:
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: 최상위는 매핑이어야 합니다")
    project = Project.model_validate(data)
    project.source_path = str(path.resolve())
    # params 유효성 사전 검증
    resolve_params(project.params)
    return project
