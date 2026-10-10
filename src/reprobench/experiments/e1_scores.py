"""E1: the Research Reproducibility Score and its components for every agent-written artifact."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reprobench.experiments._data import COMPONENTS, row, scored
from reprobench.experiments.common import fmt, result_dir, table
from reprobench.scoring import WEIGHTS

DESCRIPTION = "RRS and components per agent artifact, from the committed rerun logs"
COLS = [("artifact", "Artifact", "l"), ("author_ran", "Ran for its author", "l"), ("executions", "Author executions", "r"),
        ("reruns", "Reruns", "r"), ("code", "Code", "r"), ("environment", "Environment", "r"), ("results", "Results", "r"),
        ("claims", "Claims", "r"), ("rrs", "RRS", "r")]  # fmt: skip


def run(cfg: dict[str, Any], results: Path | None = None) -> Path:
    with result_dir("e1_scores", cfg, DESCRIPTION, results) as (rd, s):
        s.title = "E1 Reproducibility of agent-written research"
        s.question = "When an agent's research is rerun from its own files on clean machines, what reproduces?"
        pairs = scored("agent")
        rows = [row(m, sc) for m, sc in pairs]
        rd.write_json("scores.json", [sc.as_dict() for _, sc in pairs])
        rd.write_json("rows.json", rows)
        s.tables.append(table("artifacts", "Every agent artifact (components in [0, 1]; RRS weighted)", COLS,
                              [{**r, **{c: fmt(r[c], 2) for c in (*COMPONENTS, "rrs")}} for r in rows]))  # fmt: skip
        agg = []
        for a in sorted({r["agent"] for r in rows}):
            rs = [r for r in rows if r["agent"] == a]
            agg.append({"agent": a, "n": len(rs), "author_ran": sum(r["author_ran"] for r in rs),
                        **{c: fmt(sum(r[c] for r in rs) / len(rs), 2) for c in (*COMPONENTS, "rrs")}})  # fmt: skip
        s.tables.append(table("by_agent", "Mean per agent", [("agent", "Agent", "l"), ("n", "Artifacts", "r"),
                              ("author_ran", "Ran for author", "r")] + [(c, c.capitalize() if c != "rrs" else "RRS", "r")
                              for c in (*COMPONENTS, "rrs")], agg))  # fmt: skip
        for a in agg:
            s.findings.append(f"{a['agent']}: {a['author_ran']}/{a['n']} artifacts ran for their author; mean RRS {a['rrs']} "
                              f"(code {a['code']}, environment {a['environment']}, results {a['results']}, claims {a['claims']}).")  # fmt: skip
        if rows:
            best = max(rows, key=lambda r: r["rrs"])
            worst = min(rows, key=lambda r: r["rrs"])
            s.findings.append(
                f"Highest RRS {fmt(best['rrs'], 2)} ({best['artifact']}); lowest {fmt(worst['rrs'], 2)} ({worst['artifact']})."
            )
        s.notes.append("RRS = " + " + ".join(f"{w:g}·{k}" for k, w in WEIGHTS.items()) + ". Every component's evidence "
                       "(rerun, file, log line) is in scores.json and on the artifact's page in the console.")  # fmt: skip
    return rd.path
