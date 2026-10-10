"""E4: does a second machine change anything? Container reruns against the CI runner's rerun."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from reprobench import scoring
from reprobench.experiments._data import manifests
from reprobench.experiments.common import fmt, result_dir, table
from reprobench.paths import RERUNS

DESCRIPTION = "Container reruns on this machine vs the venv rerun on a GitHub Actions runner, value by value"


def run(cfg: dict[str, Any], results: Path | None = None) -> Path:
    with result_dir("e4_machines", cfg, DESCRIPTION, results) as (rd, s):
        s.title = "E4 A second machine"
        s.question = "Do results reproduced in a clean container also reproduce on a different machine?"
        rows, values = [], []
        for m in manifests():
            rs = scoring.load_reruns(m["artifact"], RERUNS)
            cont = [r for r in rs if r.meta.get("mode") == "container"]
            ci = [r for r in rs if r.meta.get("mode") == "venv"]
            if not cont or not ci:
                continue
            a, b = cont[0], ci[0]
            va, vb = scoring.numeric(a.results), scoring.numeric(b.results)
            diffs = [abs(va[k] - vb[k]) for k in va if k in vb]
            for k in sorted(set(va) | set(vb)):
                values.append({"artifact": m["artifact"], "key": k, "container": va.get(k), "ci": vb.get(k),
                               "same": k in va and k in vb and scoring.close(va[k], vb[k])})  # fmt: skip
            rows.append({"artifact": m["artifact"], "kind": m["kind"], "container_ran": a.ran, "ci_ran": b.ran,
                         "ci_python": b.meta.get("python"), "ci_machine": b.meta.get("machine"),
                         "max_abs_diff": fmt(max(diffs), 6) if diffs else "–",
                         "agree": a.ran == b.ran and all(scoring.close(va[k], vb[k]) for k in va if k in vb)})  # fmt: skip
        rd.write_json("rows.json", rows)
        rd.write_json("values.json", values)
        s.tables.append(table("machines", "First container rerun vs the CI runner rerun",
                              [("artifact", "Artifact", "l"), ("container_ran", "Container ran", "l"), ("ci_ran", "CI ran", "l"),
                               ("ci_python", "CI Python", "l"), ("max_abs_diff", "Largest difference", "r"),
                               ("agree", "Agree within tolerance", "l")], rows))  # fmt: skip
        if not rows:
            s.findings.append("Status: pending. No artifact has both a container rerun and a CI rerun yet.")
        else:
            s.findings.append(f"{sum(r['agree'] for r in rows)} of {len(rows)} artifacts agree between the two machines "
                              "(same success, every shared value within tolerance).")  # fmt: skip
            dis = [r["artifact"] for r in rows if not r["agree"]]
            s.findings.append("Disagreeing: " + (", ".join(dis) if dis else "none") + ".")
    return rd.path
