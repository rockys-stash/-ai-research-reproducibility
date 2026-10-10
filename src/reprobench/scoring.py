"""The four reproducibility components and the Research Reproducibility Score (RRS).

Every component is computed from files on disk (the frozen artifact and its rerun directories) and
returns the evidence it used: which rerun, which file, and what that file said, so any number in
the console or the report can be traced to a log line.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from reprobench import claims as claims_mod
from reprobench import imports
from reprobench.paths import ARTIFACTS, RERUNS

WEIGHTS = {"code": 0.25, "environment": 0.20, "results": 0.30, "claims": 0.25}
ABS_TOL, REL_TOL = 0.005, 0.01


@dataclass
class Evidence:
    rerun: str  # rerun id, or "artifact" / "original"
    file: str
    detail: str
    ok: bool


@dataclass
class Component:
    name: str
    score: float
    evidence: list[Evidence] = field(default_factory=list)
    parts: dict[str, float] = field(default_factory=dict)


@dataclass
class Rerun:
    id: str
    path: Path
    meta: dict[str, Any]
    results: dict[str, Any] | None

    @property
    def ran(self) -> bool:
        return self.meta.get("run_exit") == 0 and isinstance(self.results, dict)

    def tail(self, name: str, n: int = 1) -> str:
        p = self.path / name
        lines = (
            [x for x in p.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()] if p.exists() else []
        )
        return " / ".join(lines[-n:])


def _json(p: Path) -> Any:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def load_reruns(artifact: str, root: Path = RERUNS) -> list[Rerun]:
    out = []
    for d in sorted((root / artifact).glob("*/meta.json")):
        res = _json(d.parent / "results.json")
        out.append(Rerun(d.parent.name, d.parent, _json(d) or {}, res if isinstance(res, dict) else None))
    return out


def numeric(d: dict[str, Any] | None) -> dict[str, float]:
    if not d:
        return {}
    return {k: float(v) for k, v in d.items()
            if isinstance(v, int | float) and not isinstance(v, bool) and math.isfinite(v)}  # fmt: skip


def close(a: float, b: float) -> bool:
    return abs(a - b) <= max(ABS_TOL, REL_TOL * abs(a))


# ---------------------------------------------------------------- components


def code(reruns: list[Rerun]) -> Component:
    ev = []
    for r in reruns:
        if r.ran:
            ev.append(Evidence(r.id, "meta.json", "run.py exited 0 and wrote results.json", True))
        elif r.meta.get("run_exit") == 0:
            ev.append(Evidence(r.id, "meta.json", "run.py exited 0 but wrote no valid results.json", False))
        else:
            ev.append(Evidence(r.id, "run.err", f"exit {r.meta.get('run_exit')}: {r.tail('run.err')[:300]}", False))
    return Component("code", sum(e.ok for e in ev) / len(ev) if ev else 0.0, ev)


def environment(art: Path, reruns: list[Rerun]) -> Component:
    req = (art / "requirements.txt").read_text(encoding="utf-8") if (art / "requirements.txt").exists() else ""
    src = (art / "run.py").read_text(encoding="utf-8") if (art / "run.py").exists() else ""
    ev = []
    for r in reruns:
        ok = r.meta.get("build_exit") == 0
        ev.append(
            Evidence(
                r.id, "build.log", "environment built" if ok else f"pip failed: {r.tail('build.log', 2)[:300]}", ok
            )
        )
    build = sum(e.ok for e in ev) / len(ev) if ev else 0.0
    missing = imports.undeclared(src, req)
    declared = 1.0 if missing == [] else 0.0
    ev.append(Evidence("artifact", "run.py", "run.py does not parse" if missing is None else
                       ("every third-party import is declared" if not missing else f"imported but not declared: {', '.join(missing)}"),
                       declared == 1.0))  # fmt: skip
    reqs = imports.parse_requirements(req)
    mods = imports.imported_modules(src) or set()
    if reqs:
        pinned = sum(bool(r["pinned"]) for r in reqs) / len(reqs)
        loose = [str(r["name"]) for r in reqs if not r["pinned"]]
        detail = "every requirement pinned with ==" if not loose else f"not pinned: {', '.join(loose)}"
    else:
        pinned = 1.0 if not imports.third_party(mods) else 0.0
        detail = "no requirements and no third-party imports" if pinned else "requirements.txt is empty"
    ev.append(Evidence("artifact", "requirements.txt", detail, pinned == 1.0))
    parts = {"build": round(build, 4), "declared": declared, "pinned": round(pinned, 4)}
    return Component("environment", (build + declared + pinned) / 3, ev, parts)


def results(art: Path, reruns: list[Rerun]) -> Component:
    orig = numeric(_json(art / "results.json"))
    ev = []
    if not orig:
        return Component(
            "results", 0.0, [Evidence("original", "results.json", "the author's run produced no results", False)]
        )
    if not reruns:
        return Component("results", 0.0, [Evidence("original", "results.json", "no reruns yet", False)])
    reproduced = 0
    for k, v in sorted(orig.items()):
        bad = []
        for r in reruns:
            got = numeric(r.results).get(k)
            if got is None or not close(v, got):
                bad.append(f"{r.id}: {'missing' if got is None else f'{got:.6g}'}")
        ok = not bad
        reproduced += ok
        ev.append(Evidence("original", "results.json",
                           f"{k} = {v:.6g}: " + ("reproduced in every rerun" if ok else "differs in " + "; ".join(bad)), ok))  # fmt: skip
    return Component("results", reproduced / len(orig), ev)


def claims(art: Path, reruns: list[Rerun]) -> Component:
    cl = _json(art / "claims.json")
    if not isinstance(cl, list) or not cl:
        return Component("claims", 0.0, [Evidence("artifact", "claims.json", "no claims stated", False)])
    orig = _json(art / "results.json") or {}
    ev = []
    held = 0
    for c in cl:
        if not isinstance(c, dict):
            ev.append(Evidence("artifact", "claims.json", "a claim is not an object", False))
            continue
        checks = [("original", claims_mod.check(c, orig if isinstance(orig, dict) else {}))]
        checks += [(r.id, claims_mod.check(c, r.results or {})) for r in reruns]
        ok = bool(reruns) and all(x.holds for _, x in checks)
        held += ok
        fails = [f"{rid}: {x.detail}" for rid, x in checks if not x.holds]
        ev.append(Evidence("artifact", "claims.json", f"“{str(c.get('text', ''))[:120]}” — " +
                           ("holds in the original and every rerun" if ok else "; ".join(fails)[:400]), ok))  # fmt: skip
    return Component("claims", held / len(cl), ev)


@dataclass
class Score:
    artifact: str
    components: dict[str, Component]
    rrs: float
    reruns: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {"artifact": self.artifact, "rrs": round(self.rrs, 4), "reruns": self.reruns,
                "components": {k: {"score": round(c.score, 4), "parts": c.parts, "evidence": [asdict(e) for e in c.evidence]}
                               for k, c in self.components.items()}}  # fmt: skip


def rrs(scores: dict[str, float], weights: dict[str, float] = WEIGHTS) -> float:
    return sum(weights[k] * scores[k] for k in weights) / sum(weights.values())


def score(artifact: str, art_root: Path = ARTIFACTS, rerun_root: Path = RERUNS) -> Score:
    art = art_root / artifact
    rs = load_reruns(artifact, rerun_root)
    comps = {
        "code": code(rs),
        "environment": environment(art, rs),
        "results": results(art, rs),
        "claims": claims(art, rs),
    }
    return Score(artifact, comps, rrs({k: c.score for k, c in comps.items()}), [r.id for r in rs])


# ---------------------------------------------------------------- failure taxonomy

CATEGORIES = ("install_failure", "import_error", "missing_file", "timeout", "runtime_error", "no_results")


def classify(r: Rerun) -> str | None:
    """Why a rerun did not produce results (None when it did)."""
    if r.ran:
        return None
    err = (r.path / "run.err").read_text(encoding="utf-8", errors="replace") if (r.path / "run.err").exists() else ""
    if r.meta.get("run_exit") == 124:
        return "timeout"
    if r.meta.get("build_exit") not in (0, None):
        return "install_failure"
    if re.search(r"ModuleNotFoundError|ImportError", err):
        return "import_error"
    if "FileNotFoundError" in err or "No such file or directory" in err:
        return "missing_file"
    if r.meta.get("run_exit") == 0:
        return "no_results"
    return "runtime_error"
