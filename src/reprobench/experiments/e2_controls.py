"""E2: does the score catch known defects? Hand-written reference artifacts with planted defects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from reprobench.experiments._data import COMPONENTS, row, scored
from reprobench.experiments.common import fmt, result_dir, table
from reprobench.paths import REFERENCES

DESCRIPTION = "Reference artifacts with known defects: does each component land where the defect says it should?"
LOW = 0.67


def run(cfg: dict[str, Any], results: Path | None = None) -> Path:
    with result_dir("e2_controls", cfg, DESCRIPTION, results) as (rd, s):
        s.title = "E2 Known-defect controls"
        s.question = "Does each component fall when, and only when, its planted defect is present?"
        rows, checks = [], []
        for m, sc in scored("reference"):
            name = m["artifact"].removeprefix("ref-")
            exp = yaml.safe_load((REFERENCES / name / "expected.yaml").read_text(encoding="utf-8"))
            r = row(m, sc)
            hits = []
            for c in COMPONENTS:
                want = "low" if c in exp.get("low", []) else "high" if c in exp.get("high", []) else None
                if want is None:
                    continue
                got = "low" if r[c] < LOW else "high"
                hits.append(got == want)
                checks.append(
                    {"control": name, "component": c, "expected": want, "score": r[c], "as_expected": got == want}
                )
            rows.append({**r, "control": name, "defect": exp["defect"], "as_expected": f"{sum(hits)}/{len(hits)}"})
        rd.write_json("rows.json", rows)
        rd.write_json("checks.json", checks)
        s.tables.append(table("controls", "Reference controls: components and RRS", [("control", "Control", "l"),
                              ("defect", "Planted defect", "l")] + [(c, c.capitalize(), "r") for c in COMPONENTS]
                              + [("rrs", "RRS", "r"), ("as_expected", "Components as expected", "r")],
                              [{**r, **{c: fmt(r[c], 2) for c in (*COMPONENTS, "rrs")}} for r in rows]))  # fmt: skip
        ok = sum(c["as_expected"] for c in checks)
        s.findings.append(f"{ok} of {len(checks)} expected component outcomes observed (low means below {LOW}).")
        miss = [
            f"{c['control']}/{c['component']} ({fmt(c['score'], 2)}, expected {c['expected']})"
            for c in checks
            if not c["as_expected"]
        ]
        s.findings.append("Not as expected: " + ("; ".join(miss) if miss else "none") + ".")
        if rows:
            order = sorted(rows, key=lambda r: -r["rrs"])
            s.findings.append("RRS order: " + ", ".join(f"{r['control']} {fmt(r['rrs'], 2)}" for r in order) + ".")
        s.notes.append("Expected outcomes were written in references/*/expected.yaml before any rerun: " + json.dumps(
            {r["control"]: r["defect"] for r in rows}, ensure_ascii=False))  # fmt: skip
    return rd.path
