"""Shared loading for the experiments: every frozen artifact with its manifest and score."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reprobench import scoring
from reprobench.paths import ARTIFACTS, RERUNS

COMPONENTS = ("code", "environment", "results", "claims")


def manifests(root: Path = ARTIFACTS) -> list[dict[str, Any]]:
    out = []
    for p in sorted(root.glob("*/manifest.json")):
        if p.parent.name.startswith("dev-"):
            continue
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def scored(kind: str | None = None) -> list[tuple[dict[str, Any], scoring.Score]]:
    return [
        (m, scoring.score(m["artifact"], ARTIFACTS, RERUNS)) for m in manifests() if kind is None or m["kind"] == kind
    ]


def row(m: dict[str, Any], s: scoring.Score) -> dict[str, Any]:
    return {"artifact": m["artifact"], "problem": m["problem"], "agent": m["agent"], "kind": m["kind"],
            "author_ran": m["author_succeeded"], "executions": m["executions"], "reruns": len(s.reruns),
            **{c: round(s.components[c].score, 4) for c in COMPONENTS}, "rrs": round(s.rrs, 4)}  # fmt: skip
