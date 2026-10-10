"""E5: how much does the RRS ranking depend on its weights?"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scipy.stats import spearmanr

from reprobench.experiments._data import COMPONENTS, row, scored
from reprobench.experiments.common import fmt, result_dir, table
from reprobench.scoring import WEIGHTS, rrs

DESCRIPTION = "Rank agreement of artifacts under alternative weightings of the four components"
SCHEMES: dict[str, dict[str, float]] = {
    "default": WEIGHTS,
    "equal": dict.fromkeys(COMPONENTS, 0.25),
    "results_only": {"code": 0.0, "environment": 0.0, "results": 1.0, "claims": 0.0},
    "no_environment": {"code": 1 / 3, "environment": 0.0, "results": 1 / 3, "claims": 1 / 3},
}


def gated(r: dict[str, Any]) -> float:
    """Code-gated: nothing counts unless the code runs everywhere."""
    return rrs(r) if r["code"] == 1.0 else 0.0


def run(cfg: dict[str, Any], results: Path | None = None) -> Path:
    with result_dir("e5_weights", cfg, DESCRIPTION, results) as (rd, s):
        s.title = "E5 Weight sensitivity"
        s.question = "Would a different weighting of the components rank the artifacts differently?"
        rows = [row(m, sc) for m, sc in scored()]
        for r in rows:
            for k, w in SCHEMES.items():
                r[k] = round(rrs(r, w), 4)
            r["code_gated"] = round(gated(r), 4)
        rd.write_json("rows.json", rows)
        names = [*SCHEMES, "code_gated"]
        s.tables.append(table("scores", "RRS of every artifact under each weighting", [("artifact", "Artifact", "l")]
                              + [(n, n.replace("_", " "), "r") for n in names],
                              [{**r, **{n: fmt(r[n], 2) for n in names}} for r in rows]))  # fmt: skip
        corr = []
        for n in names[1:]:
            rho = (
                float(spearmanr([r["default"] for r in rows], [r[n] for r in rows]).statistic)
                if len(rows) > 2
                else float("nan")
            )
            corr.append({"scheme": n, "rho": fmt(rho, 3), "top_same": (max(rows, key=lambda r: r["default"])["artifact"]
                         == max(rows, key=lambda r: r[n])["artifact"]) if rows else False})  # fmt: skip
        s.tables.append(table("rank", "Spearman rank correlation with the default weighting",
                              [("scheme", "Weighting", "l"), ("rho", "ρ", "r"), ("top_same", "Same top artifact", "l")], corr))  # fmt: skip
        s.findings.append(
            "Rank correlation with the default weighting: " + ", ".join(f"{c['scheme']} {c['rho']}" for c in corr) + "."
        )
    return rd.path
