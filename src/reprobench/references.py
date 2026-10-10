"""Hand-written reference artifacts with known defects, frozen the same way as agent artifacts.

Each ``references/<name>/`` holds the files an author would leave plus ``expected.yaml`` (the
problem, the planted defect and what the score should show). Freezing runs ``run.py`` on the author's
machine, exactly as the agent's code is run, so the original results come from an execution. A claim
whose ``right`` is ``{key}`` is filled with that key's value from the author's run (used by the
no-seed control, which claims the exact numbers it saw).
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from reprobench.agent import FILES, author_environment, execute
from reprobench.paths import ARTIFACTS, REFERENCES
from reprobench.problems import load as load_problem

AUTHOR_DATA = Path("/tmp/reprobench-author-data")


def _setup(kind: str | None) -> None:
    """Files that exist only on the author's machine."""
    if kind == "diabetes_csv":
        import numpy as np
        from sklearn.datasets import load_diabetes

        X, y = load_diabetes(return_X_y=True)
        AUTHOR_DATA.mkdir(parents=True, exist_ok=True)
        np.savetxt(AUTHOR_DATA / "diabetes.csv", np.column_stack([X, y]), delimiter=",")


def names() -> list[str]:
    return sorted(p.parent.name for p in REFERENCES.glob("*/expected.yaml"))


def freeze(name: str, root: Path = ARTIFACTS) -> Path:
    src = REFERENCES / name
    exp: dict[str, Any] = yaml.safe_load((src / "expected.yaml").read_text(encoding="utf-8"))
    problem = load_problem(exp["problem"])
    out = root / f"ref-{name}"
    if (out / "manifest.json").exists():
        raise FileExistsError(f"{out} is frozen; delete it to refreeze")
    out.mkdir(parents=True, exist_ok=True)
    _setup(exp.get("setup"))
    code = (src / "run.py").read_text(encoding="utf-8")
    req = (src / "requirements.txt").read_text(encoding="utf-8")
    ex = execute(code, req, list(problem.results_keys))
    if ex.problem or ex.results is None:
        raise RuntimeError(f"reference {name} does not run for its author: {ex.problem}\n{ex.stderr[-1500:]}")
    claims = json.loads((src / "claims.json").read_text(encoding="utf-8"))
    for c in claims:
        r = str(c.get("right", ""))
        if r.startswith("{") and r.endswith("}"):
            c["right"] = f"{float(ex.results[r[1:-1]]):.6f}"
    files = {"requirements.txt": req, "run.py": code, "results.json": json.dumps(ex.results, indent=1) + "\n",
             "claims.json": json.dumps(claims, indent=1, ensure_ascii=False) + "\n",
             "README.md": (src / "README.md").read_text(encoding="utf-8")}  # fmt: skip
    for n, t in files.items():
        (out / n).write_text(t, encoding="utf-8")
    manifest = {
        "artifact": out.name, "problem": problem.key, "agent": "reference", "agent_label": "Reference (hand-written)",
        "seed": 0, "kind": "reference", "defect": exp["defect"], "expect": exp["expect"], "author_succeeded": True,
        "executions": 1, "author_environment": author_environment(),
        "frozen_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "sha256": {n: hashlib.sha256(files[n].encode()).hexdigest() for n in FILES},
    }  # fmt: skip
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return out
