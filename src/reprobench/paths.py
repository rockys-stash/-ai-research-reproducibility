"""Repository locations. Everything the system writes lives under the repository root."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIGS = ROOT / "configs"
PROBLEMS = CONFIGS / "problems"
MODELS = ROOT / "models"
ARTIFACTS = ROOT / "artifacts"  # one directory per agent-written artifact, frozen after generation
REFERENCES = ROOT / "references"  # hand-written control artifacts with known properties
RERUNS = ROOT / "reruns"  # one directory per artifact; one subdirectory per independent rerun
RESULTS = ROOT / "results"
VAR = ROOT / "var"  # scratch; never committed
