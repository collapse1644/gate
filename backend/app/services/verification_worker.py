"""Isolated expression evaluator. Invoked as: python -I verification_worker.py.

Reads one JSON object from stdin. Only a small mathematical subset is allowed.
No imports, attribute access, lambdas, comprehensions, assignments, or calls to
non-whitelisted names can reach SymPy's parser.
"""

from __future__ import annotations

import ast
import json
import sys

import sympy as sp

ALLOWED_NAMES = {
    "sqrt": sp.sqrt,
    "log": sp.log,
    "ln": sp.log,
    "log2": lambda x: sp.log(x, 2),
    "exp": sp.exp,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "asin": sp.asin,
    "acos": sp.acos,
    "atan": sp.atan,
    "pi": sp.pi,
    "E": sp.E,
    "factorial": sp.factorial,
    "Rational": sp.Rational,
    "Abs": sp.Abs,
    "floor": sp.floor,
    "ceil": sp.ceiling,
    "ceiling": sp.ceiling,
    "binom": sp.binomial,
}
ALLOWED_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Call,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.USub,
    ast.UAdd,
    ast.FloorDiv,
)


def validate(node: ast.AST) -> None:
    for child in ast.walk(node):
        if not isinstance(child, ALLOWED_NODES):
            raise ValueError(f"Disallowed expression construct: {type(child).__name__}")
        if isinstance(child, ast.Name) and child.id not in ALLOWED_NAMES:
            raise ValueError(f"Disallowed name: {child.id}")
        if isinstance(child, ast.Call):
            if not isinstance(child.func, ast.Name) or child.func.id not in ALLOWED_NAMES:
                raise ValueError("Only whitelisted mathematical functions may be called.")
            if len(child.args) > 4:
                raise ValueError("Too many function arguments.")


def parse(value: str):
    if len(value) > 2000:
        raise ValueError("Expression too long.")
    tree = ast.parse(value, mode="eval")
    validate(tree)
    return sp.sympify(value, locals=ALLOWED_NAMES)


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
        expr = parse(str(payload["expression"]))
        expected = parse(str(payload["expected"]))
        tolerance = float(payload.get("tolerance", 1e-9))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"passed": False, "error": str(exc)[:400], "actual": None}))
        return 0
    try:
        difference = sp.simplify(expr - expected)
        symbolic_equal = difference == 0
        if symbolic_equal:
            print(
                json.dumps(
                    {
                        "passed": True,
                        "actual": str(expr),
                        "difference": "0",
                        "method": "symbolic",
                    }
                )
            )
            return 0
        numeric = complex(sp.N(difference, 20))
        passed = abs(numeric) <= max(tolerance, 1e-12) * max(1.0, abs(complex(sp.N(expected, 20))))
        print(
            json.dumps(
                {
                    "passed": bool(passed),
                    "actual": str(sp.N(expr, 20)),
                    "expected": str(sp.N(expected, 20)),
                    "difference": str(sp.N(difference, 20)),
                    "method": "numeric",
                }
            )
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"passed": False, "error": str(exc)[:400]}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
