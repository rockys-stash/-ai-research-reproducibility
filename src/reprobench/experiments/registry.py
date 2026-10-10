"""Experiment registry: name → module with ``run(cfg, results)``."""

from __future__ import annotations

from reprobench.experiments import e1_scores, e2_controls, e3_failures, e4_machines, e5_weights

EXPERIMENTS = {
    "e1": ("e1_scores", e1_scores.run),
    "e2": ("e2_controls", e2_controls.run),
    "e3": ("e3_failures", e3_failures.run),
    "e4": ("e4_machines", e4_machines.run),
    "e5": ("e5_weights", e5_weights.run),
}
