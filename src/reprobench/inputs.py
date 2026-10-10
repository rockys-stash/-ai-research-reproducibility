"""Hashes of every input a result depends on: problems, frozen artifacts and rerun logs."""

from __future__ import annotations

import hashlib
from pathlib import Path

from reprobench.paths import ARTIFACTS, PROBLEMS, RERUNS


def _hash_files(files: list[Path], root: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(files):
        h.update(str(f.relative_to(root)).encode())
        h.update(f.read_bytes())
    return h.hexdigest() if files else ""


def _kept(p: Path, root: Path) -> bool:
    return not p.relative_to(root).parts[0].startswith("dev-")


def input_hashes() -> dict[str, str]:
    return {
        "problems": _hash_files(list(PROBLEMS.glob("*.yaml")), PROBLEMS),
        "artifacts": _hash_files([p for p in ARTIFACTS.glob("*/*") if p.is_file() and _kept(p, ARTIFACTS)], ARTIFACTS),
        "reruns": _hash_files([p for p in RERUNS.glob("*/*/*") if p.is_file() and _kept(p, RERUNS)], RERUNS),
    }
