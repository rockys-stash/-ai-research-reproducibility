"""Structured claims and checking them against a results file.

A claim reads ``left OP right``: ``left`` is a results key, ``right`` is a results key or a number,
and OP is one of ``>``, ``<``, ``>=``, ``<=`` or ``≈`` (within ``tolerance``). A claim that names a
key the results do not contain, or does not have this shape, cannot hold.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

OPS = (">", "<", ">=", "<=", "≈")


@dataclass(frozen=True)
class Check:
    holds: bool
    detail: str


def _value(token: Any, results: dict[str, Any]) -> float | None:
    if isinstance(token, bool):
        return None
    if isinstance(token, int | float):
        return float(token)
    s = str(token).strip()
    if s in results:
        v = results[s]
        return float(v) if isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v) else None
    try:
        return float(s)
    except ValueError:
        return None


def check(claim: dict[str, Any], results: dict[str, Any]) -> Check:
    op = claim.get("op")
    if op not in OPS:
        return Check(False, f"operator {op!r} is not one of {', '.join(OPS)}")
    left_key = str(claim.get("left", ""))
    if left_key not in results:
        return Check(False, f"{left_key!r} is not in the results")
    a, b = _value(left_key, results), _value(claim.get("right"), results)
    if a is None or b is None:
        return Check(False, f"cannot read {claim.get('left')!r} or {claim.get('right')!r} as numbers")
    if op == "≈":
        tol = claim.get("tolerance")
        if not isinstance(tol, int | float) or isinstance(tol, bool) or tol < 0:
            return Check(False, "≈ needs a non-negative tolerance")
        ok = abs(a - b) <= float(tol)
        return Check(ok, f"|{a:.4f} − {b:.4f}| = {abs(a - b):.4f} {'≤' if ok else '>'} {float(tol):g}")
    ok = {">": a > b, "<": a < b, ">=": a >= b, "<=": a <= b}[op]
    return Check(ok, f"{a:.4f} {op} {b:.4f} is {'true' if ok else 'false'}")
