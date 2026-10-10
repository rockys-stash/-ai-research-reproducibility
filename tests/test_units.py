from __future__ import annotations

from typing import Any

import pytest

from reprobench import claims, imports


def test_imports_and_requirements() -> None:
    code = (
        "import os, json\nimport numpy as np\nfrom sklearn.linear_model import Ridge\nimport pandas\nfrom . import x\n"
    )
    assert imports.third_party(imports.imported_modules(code) or set()) == {"numpy", "sklearn", "pandas"}
    req = "numpy==2.1.3\nScikit_Learn>=1.5  # comment\n-r other.txt\n"
    parsed = imports.parse_requirements(req)
    assert [(r["name"], r["pinned"]) for r in parsed] == [("numpy", True), ("scikit-learn", False)]
    assert imports.undeclared(code, req) == ["pandas"]
    assert imports.undeclared("def (", req) is None


@pytest.mark.parametrize(
    ("claim", "holds"),
    [
        ({"left": "a", "op": ">", "right": "b"}, False),
        ({"left": "b", "op": ">", "right": "a"}, True),
        ({"left": "a", "op": "<=", "right": "1"}, True),
        ({"left": "a", "op": "≈", "right": "1.004", "tolerance": 0.005}, True),
        ({"left": "a", "op": "≈", "right": "1.01", "tolerance": 0.005}, False),
        ({"left": "a", "op": "≈", "right": "1"}, False),  # no tolerance
        ({"left": "missing", "op": ">", "right": "0"}, False),
        ({"left": "a", "op": "==", "right": "1"}, False),
        ({"left": "a", "op": ">", "right": "not a number"}, False),
        ({"left": "flag", "op": ">", "right": "0"}, False),  # booleans are not numbers
    ],
)
def test_claim_checks(claim: dict[str, Any], holds: bool) -> None:
    assert claims.check(claim, {"a": 1.0, "b": 2.0, "flag": True}).holds is holds
