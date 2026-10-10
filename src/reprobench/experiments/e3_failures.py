"""E3: why reruns fail or differ. A taxonomy built from the rerun logs."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from reprobench import scoring
from reprobench.experiments._data import manifests
from reprobench.experiments.common import result_dir, table
from reprobench.paths import ARTIFACTS, RERUNS

DESCRIPTION = "Failure and difference taxonomy over every rerun, from build and run logs and result values"


def value_pattern(art: Path, reruns: list[scoring.Rerun]) -> str:
    """How the reproduced values relate: same everywhere, rerun-to-rerun noise, drift from the author, or machine."""
    orig = scoring.numeric(scoring._json(art / "results.json"))
    ok = [r for r in reruns if r.ran]
    if not orig or not ok:
        return "no comparison"

    def same(a: dict[str, float], b: dict[str, float]) -> bool:
        return all(k in b and scoring.close(v, b[k]) for k, v in a.items() if k in orig)

    vals = [scoring.numeric(r.results) for r in ok]
    cont = [scoring.numeric(r.results) for r in ok if r.meta.get("mode") == "container"]
    other = [scoring.numeric(r.results) for r in ok if r.meta.get("mode") != "container"]
    if all(same(orig, v) for v in vals):
        return "reproduced"
    if len(cont) >= 2 and not same(cont[0], cont[1]):
        return "non-deterministic (two identical containers disagree)"
    if all(same(vals[0], v) for v in vals[1:]):
        return "reruns agree with each other, not with the author"
    if cont and other and not same(cont[0], other[0]):
        return "differs between machines"
    return "other"


def run(cfg: dict[str, Any], results: Path | None = None) -> Path:
    with result_dir("e3_failures", cfg, DESCRIPTION, results) as (rd, s):
        s.title = "E3 Why reproduction fails"
        s.question = "When a rerun fails or gives different numbers, what is the cause in its logs?"
        per_rerun, per_art = [], []
        for m in manifests():
            art = ARTIFACTS / m["artifact"]
            rs = scoring.load_reruns(m["artifact"], RERUNS)
            for r in rs:
                per_rerun.append({"artifact": m["artifact"], "kind": m["kind"], "rerun": r.id,
                                  "category": scoring.classify(r) or "ran", "evidence": r.tail("run.err")[:240] if not r.ran else ""})  # fmt: skip
            cl = scoring.claims(art, rs)
            per_art.append({"artifact": m["artifact"], "kind": m["kind"], "author_ran": m["author_succeeded"],
                            "values": value_pattern(art, rs), "claims_false_for_author":
                            sum("original:" in e.detail for e in cl.evidence)})  # fmt: skip
        rd.write_json("reruns.json", per_rerun)
        rd.write_json("artifacts.json", per_art)
        for kind in ("agent", "reference"):
            c = Counter(r["category"] for r in per_rerun if r["kind"] == kind)
            s.tables.append(table(f"categories_{kind}", f"Rerun outcomes, {kind} artifacts",
                                  [("category", "Outcome", "l"), ("n", "Reruns", "r")],
                                  [{"category": k, "n": n} for k, n in c.most_common()]))  # fmt: skip
        s.tables.append(table("values", "Value patterns and claims per artifact",
                              [("artifact", "Artifact", "l"), ("author_ran", "Ran for author", "l"), ("values", "Values", "l"),
                               ("claims_false_for_author", "Claims false on the author's own results", "r")], per_art))  # fmt: skip
        agent = [r for r in per_rerun if r["kind"] == "agent"]
        fails = Counter(r["category"] for r in agent if r["category"] != "ran")
        s.findings.append(f"Agent artifacts: {sum(r['category'] == 'ran' for r in agent)} of {len(agent)} reruns produced "
                          "results" + ("; failures: " + ", ".join(f"{k} {n}" for k, n in fails.most_common()) if fails else "") + ".")  # fmt: skip
        vp = Counter(a["values"] for a in per_art if a["kind"] == "agent")
        s.findings.append("Agent value patterns: " + ", ".join(f"{k} ({n})" for k, n in vp.most_common()) + ".")
        s.findings.append(
            f"Claims false on the author's own results: {sum(a['claims_false_for_author'] for a in per_art if a['kind'] == 'agent')} (agent artifacts)."
        )
    return rd.path
