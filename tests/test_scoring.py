from __future__ import annotations

from pathlib import Path

from reprobench import scoring
from tests.conftest import write_artifact, write_rerun

CLAIMS = [{"text": "b beats a", "left": "b", "op": ">", "right": "a", "tolerance": 0},
          {"text": "a is about 1", "left": "a", "op": "≈", "right": "1", "tolerance": 0.001}]  # fmt: skip


def test_fully_reproduced_artifact_scores_one(tmp_path: Path) -> None:
    arts, rr = tmp_path / "a", tmp_path / "r"
    write_artifact(arts, "x", {"a": 1.0, "b": 2.0}, CLAIMS, code="import json\n", requirements="")
    for rid in ("container-1", "container-2", "ci-1"):
        write_rerun(rr, "x", rid, {"a": 1.0, "b": 2.0001})
    s = scoring.score("x", arts, rr)
    assert {k: c.score for k, c in s.components.items()} == {
        "code": 1.0,
        "environment": 1.0,
        "results": 1.0,
        "claims": 1.0,
    }
    assert s.rrs == 1.0
    assert all(e.ok for c in s.components.values() for e in c.evidence)


def test_noise_failures_and_unpinned_requirements(tmp_path: Path) -> None:
    arts, rr = tmp_path / "a", tmp_path / "r"
    code = "import json\nimport numpy\nimport pandas\n"
    write_artifact(arts, "x", {"a": 1.0, "b": 2.0}, CLAIMS, code=code, requirements="numpy\n")
    write_rerun(rr, "x", "container-1", {"a": 1.0, "b": 2.5})
    write_rerun(rr, "x", "container-2", None, run=1, err="Traceback\nModuleNotFoundError: No module named 'pandas'\n")
    s = scoring.score("x", arts, rr)
    c = {k: v.score for k, v in s.components.items()}
    assert c["code"] == 0.5
    assert c["environment"] == (1.0 + 0.0 + 0.0) / 3  # builds; pandas undeclared; numpy unpinned
    assert c["results"] == 0.0  # a failed rerun reproduces nothing
    assert c["claims"] == 0.0
    assert abs(s.rrs - (0.25 * 0.5 + 0.2 * c["environment"])) < 1e-9
    reruns = scoring.load_reruns("x", rr)
    assert [scoring.classify(r) for r in reruns] == [None, "import_error"]


def test_failure_taxonomy(tmp_path: Path) -> None:
    rr = tmp_path / "r"
    write_rerun(rr, "x", "1", None, build=1, run=1, err="ModuleNotFoundError: sklearn")
    write_rerun(rr, "x", "2", None, run=1, err="FileNotFoundError: [Errno 2] No such file or directory: '/tmp/a.csv'")
    write_rerun(rr, "x", "3", None, run=124)
    write_rerun(rr, "x", "4", None, run=0)
    write_rerun(rr, "x", "5", None, run=1, err="ValueError: bad")
    got = [scoring.classify(r) for r in scoring.load_reruns("x", rr)]
    assert got == ["install_failure", "missing_file", "timeout", "no_results", "runtime_error"]


def test_author_failure_and_no_claims(tmp_path: Path) -> None:
    arts, rr = tmp_path / "a", tmp_path / "r"
    write_artifact(arts, "x", {}, [], ok=False)
    write_rerun(rr, "x", "container-1", None, run=1, err="SyntaxError")
    s = scoring.score("x", arts, rr)
    assert s.components["results"].score == 0.0 and s.components["claims"].score == 0.0
    assert "no claims" in s.components["claims"].evidence[0].detail
