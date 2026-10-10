"""Shared fixtures: synthetic artifacts and rerun directories written straight to disk, and a scripted
stand-in for the language model."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("OMP_NUM_THREADS", "1")

GOOD_CODE = """import json
json.dump({"a": 1.0, "b": 2.0}, open("results.json", "w"))
"""


def write_artifact(root: Path, aid: str, results: dict[str, Any], claims: list[dict[str, Any]],
                   code: str = GOOD_CODE, requirements: str = "", kind: str = "agent", ok: bool = True) -> Path:  # fmt: skip
    d = root / aid
    d.mkdir(parents=True)
    (d / "run.py").write_text(code)
    (d / "requirements.txt").write_text(requirements)
    (d / "results.json").write_text(json.dumps(results))
    (d / "claims.json").write_text(json.dumps(claims))
    (d / "README.md").write_text("readme\n")
    (d / "manifest.json").write_text(json.dumps({
        "artifact": aid, "problem": "compare", "agent": "qwen3-4b" if kind == "agent" else "reference",
        "agent_label": "Qwen3-4B", "seed": 0, "kind": kind, "defect": None if kind == "agent" else "none",
        "expect": "", "author_succeeded": ok, "executions": 1, "frozen_at": "2026-10-10T00:00:00+00:00",
        "author_environment": {"python": "3.13", "platform": "linux", "packages": {"numpy": "2"}}, "sha256": {}}))  # fmt: skip
    return d


def write_rerun(root: Path, aid: str, rid: str, results: dict[str, Any] | None, build: int = 0, run: int = 0,
                err: str = "", mode: str = "container") -> Path:  # fmt: skip
    d = root / aid / rid
    d.mkdir(parents=True)
    (d / "meta.json").write_text(json.dumps({"rerun_id": rid, "mode": mode, "machine": "test", "started": "",
                                             "build_exit": build, "run_exit": run, "run_seconds": 0.1,
                                             "total_seconds": 1.0, "python": "3.12.0", "platform": "linux",
                                             "results_written": results is not None}))  # fmt: skip
    (d / "build.log").write_text("Successfully installed\n" if build == 0 else "ERROR: No matching distribution\n")
    (d / "run.err").write_text(err)
    (d / "run.out").write_text("")
    if results is not None:
        (d / "results.json").write_text(json.dumps(results))
    return d


class ScriptedModel:
    """Replies from a list, in order; records calls like LocalModel."""

    name, label = "scripted", "Scripted test model"

    def __init__(self, replies: list[dict[str, Any]]) -> None:
        self.replies = list(replies)
        self.calls: list[dict[str, Any]] = []

    def json(self, system: str, user: str, schema: dict[str, Any], seed: int, max_tokens: int = 700,
             temperature: float = 0.3) -> dict[str, Any]:  # fmt: skip
        r = self.replies.pop(0)
        self.calls.append({"system": system, "user": user, "reply": json.dumps(r), "seed": seed, "seconds": 0.0,
                           "completion_tokens": 1, "prompt_tokens": 1, "error": ""})  # fmt: skip
        return r
