"""The research agent: a local language model writes code, runs it in its own sandbox, fixes it, and
states its conclusions. The result is a frozen *artifact*.

The agent's sandbox is the author's machine: this repository's Python environment (numpy, scipy,
pandas, scikit-learn and more already installed). The agent is told which packages are there and
that someone else will rerun its work from the files it leaves; it is not told how to make work
reproducible (seeds, pins), because that is what is measured.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any, Protocol

from reprobench.claims import OPS
from reprobench.paths import ARTIFACTS
from reprobench.problems import Problem

MAX_EXECUTIONS = 4
RUN_TIMEOUT_S = 300
FILES = ("requirements.txt", "run.py", "results.json", "claims.json", "README.md")
AUTHOR_PACKAGES = ("numpy", "scipy", "pandas", "scikit-learn")

SYSTEM = "You are a careful research engineer. You write complete, runnable Python research code and report results honestly."
CODE_SCHEMA = {
    "type": "object",
    "properties": {"requirements": {"type": "string", "maxLength": 400}, "code": {"type": "string"}},
    "required": ["requirements", "code"],
}


def claims_schema(keys: list[str]) -> dict[str, Any]:
    claim = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "maxLength": 300},
            "left": {"type": "string", "enum": keys},
            "op": {"type": "string", "enum": list(OPS)},
            "right": {"type": "string", "maxLength": 60},
            "tolerance": {"type": "number"},
        },
        "required": ["text", "left", "op", "right", "tolerance"],
    }
    return {
        "type": "object",
        "properties": {"claims": {"type": "array", "items": claim, "minItems": 1, "maxItems": 5},
                       "readme": {"type": "string"}},
        "required": ["claims", "readme"],
    }  # fmt: skip


class Model(Protocol):
    name: str
    label: str
    calls: list[dict[str, Any]]

    def json(self, system: str, user: str, schema: dict[str, Any], seed: int, max_tokens: int = 700,
             temperature: float = 0.3) -> dict[str, Any]: ...  # fmt: skip


def author_environment() -> dict[str, Any]:
    pk: dict[str, str | None] = {}
    for p in AUTHOR_PACKAGES:
        try:
            pk[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            pk[p] = None
    return {"python": sys.version.split()[0], "platform": platform.platform(), "packages": pk}


def environment_note() -> str:
    env = author_environment()
    pk = ", ".join(f"{k} {v}" for k, v in env["packages"].items() if v)
    return (f"Your machine: Python {env['python']} with {pk} installed. No internet access while your script "
            "runs. Another researcher will rerun your work on their own machine from the files you leave.")  # fmt: skip


@dataclass
class Execution:
    exit_code: int | None
    stdout: str
    stderr: str
    seconds: float
    results: dict[str, Any] | None
    problem: str  # empty when the run is usable


def validate_results(path: Path, keys: list[str]) -> tuple[dict[str, Any] | None, str]:
    if not path.exists():
        return None, "the script did not write results.json"
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return None, f"results.json is not valid JSON: {e}"
    if not isinstance(d, dict):
        return None, "results.json must contain a JSON object"
    missing = [k for k in keys if k not in d]
    bad = [k for k in keys if k in d and not (isinstance(d[k], int | float) and not isinstance(d[k], bool)
                                              and math.isfinite(d[k]))]  # fmt: skip
    if missing or bad:
        return d, "results.json " + "; ".join(
            x for x in (f"is missing {', '.join(missing)}" if missing else "",
                        f"has non-numeric {', '.join(bad)}" if bad else "") if x)  # fmt: skip
    return d, ""


def execute(code: str, requirements: str, keys: list[str], python: str = sys.executable) -> Execution:
    """Run ``run.py`` in a fresh directory on the author's machine."""
    with tempfile.TemporaryDirectory(prefix="author-") as tmp:
        work = Path(tmp)
        (work / "run.py").write_text(code, encoding="utf-8")
        (work / "requirements.txt").write_text(requirements, encoding="utf-8")
        env = os.environ | {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
        t0 = time.perf_counter()
        try:
            p = subprocess.run(
                [python, "run.py"], cwd=work, capture_output=True, text=True, timeout=RUN_TIMEOUT_S, env=env
            )
            code_, out, err = p.returncode, p.stdout, p.stderr
        except subprocess.TimeoutExpired as e:
            code_, out, err = None, str(e.stdout or ""), f"timed out after {RUN_TIMEOUT_S} s"
        secs = round(time.perf_counter() - t0, 2)
        if code_ != 0:
            return Execution(code_, out[-4000:], err[-4000:], secs, None, f"the script exited with code {code_}")
        res, why = validate_results(work / "results.json", keys)
        return Execution(code_, out[-4000:], err[-4000:], secs, res, why)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def generate(problem: Problem, model: Model, seed: int = 0, root: Path = ARTIFACTS,
             artifact_id: str | None = None) -> Path:  # fmt: skip
    """Run the agent on ``problem`` and freeze the artifact; returns its directory."""
    aid = artifact_id or f"{problem.key}-{model.name}-s{seed}"
    out = root / aid
    if (out / "manifest.json").exists():
        raise FileExistsError(f"{out} is frozen; delete it to regenerate")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    keys = list(problem.results_keys)
    transcript: list[dict[str, Any]] = []
    feedback = ""
    files: dict[str, str] = {}
    last: Execution | None = None
    for attempt in range(MAX_EXECUTIONS):
        user = f"Research problem:\n{problem.brief()}\n\n{environment_note()}\n\n" + (
            "Write requirements.txt (the third-party packages run.py needs, one per line) and run.py, a complete "
            "script that does the whole experiment and writes results.json."
            if not feedback else
            f"{feedback}\n\nFix the problem and reply with the complete requirements.txt and run.py again.")  # fmt: skip
        if feedback:
            user += f"\n\nYour previous run.py:\n```python\n{files['run.py']}\n```"
        reply = model.json(SYSTEM, user, CODE_SCHEMA, seed=seed * 1000 + attempt, max_tokens=2000)
        files = {
            "requirements.txt": str(reply.get("requirements", "")).strip() + "\n",
            "run.py": str(reply.get("code", "")),
        }
        last = execute(files["run.py"], files["requirements.txt"], keys)
        transcript.append({"step": "code", "attempt": attempt + 1, "call": model.calls[-1] if model.calls else None,
                           "execution": {"exit_code": last.exit_code, "seconds": last.seconds, "problem": last.problem,
                                         "stdout": last.stdout[-2000:], "stderr": last.stderr[-2000:]}})  # fmt: skip
        if not last.problem:
            break
        tail = "\n".join(last.stderr.strip().splitlines()[-15:])
        feedback = f"When run, {last.problem}." + (f"\nLast lines of the error output:\n{tail}" if tail else "")
    ok = last is not None and not last.problem and last.results is not None
    results: dict[str, Any] = (last.results or {}) if ok and last is not None else {}
    files["results.json"] = json.dumps(results, indent=1) + "\n"
    if ok:
        user = (f"Research problem:\n{problem.brief()}\n\nYour script ran and wrote results.json:\n{files['results.json']}\n"
                "State your conclusions as 1 to 5 structured claims. Each claim reads `left op right`: left is a key "
                "of results.json, right is another key or a number, op is one of > < >= <= ≈ (≈ means within "
                "`tolerance`; give tolerance 0 for the other operators). Also write a short README for someone "
                "rerunning your work: what the script does and what you found.")  # fmt: skip
        r = model.json(SYSTEM, user, claims_schema(sorted(results)), seed=seed * 1000 + 100, max_tokens=900)
        claims = list(r.get("claims", []))
        readme = str(r.get("readme", ""))
        transcript.append({"step": "claims", "call": model.calls[-1] if model.calls else None})
    else:
        claims, readme = [], "The agent did not produce a working script within its execution budget."
    files["claims.json"] = json.dumps(claims, indent=1, ensure_ascii=False) + "\n"
    files["README.md"] = readme.strip() + "\n"
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
    with (out / "transcript.jsonl").open("w", encoding="utf-8") as f:
        for t in transcript:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    manifest = {
        "artifact": aid, "problem": problem.key, "agent": model.name, "agent_label": model.label, "seed": seed,
        "kind": "agent", "author_succeeded": ok, "executions": sum(t["step"] == "code" for t in transcript),
        "author_environment": author_environment(), "frozen_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "sha256": {n: _sha(files[n]) for n in FILES},
    }  # fmt: skip
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return out


def verify(artifact: Path) -> tuple[bool, list[str]]:
    """Whether the frozen files still match their hashes in the manifest."""
    m = json.loads((artifact / "manifest.json").read_text(encoding="utf-8"))
    changed = [n for n, h in m["sha256"].items() if _sha((artifact / n).read_text(encoding="utf-8")) != h]
    return not changed, changed
