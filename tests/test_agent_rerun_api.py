from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from reprobench import agent, problems
from reprobench.api import create_app
from reprobench.rerun import rerun
from tests.conftest import ScriptedModel, write_artifact, write_rerun

BROKEN = "import json\nraise ValueError('bad split')\n"
WORKS = ("import json\n"
         "json.dump({'rf_accuracy_mean': 0.96, 'lr_accuracy_mean': 0.97, 'accuracy_difference': -0.01},"
         " open('results.json', 'w'))\n")  # fmt: skip
CLAIMS = {"claims": [{"text": "LR wins", "left": "lr_accuracy_mean", "op": ">", "right": "rf_accuracy_mean",
                      "tolerance": 0}], "readme": "Compared two models."}  # fmt: skip


def test_agent_fixes_its_code_then_freezes(tmp_path: Path) -> None:
    model = ScriptedModel([{"requirements": "", "code": BROKEN}, {"requirements": "", "code": WORKS}, CLAIMS])
    out = agent.generate(problems.load("compare"), model, 0, tmp_path)
    m = json.loads((out / "manifest.json").read_text())
    assert m["author_succeeded"] and m["executions"] == 2
    assert json.loads((out / "results.json").read_text())["lr_accuracy_mean"] == 0.97
    assert json.loads((out / "claims.json").read_text())[0]["op"] == ">"
    steps = [json.loads(x) for x in (out / "transcript.jsonl").read_text().splitlines()]
    assert "bad split" in steps[0]["execution"]["stderr"]
    assert "bad split" in model.calls[1]["user"]  # the error was fed back
    assert agent.verify(out) == (True, [])
    (out / "claims.json").write_text("[]\n")
    assert agent.verify(out) == (False, ["claims.json"])
    with pytest.raises(FileExistsError):
        agent.generate(problems.load("compare"), ScriptedModel([]), 0, tmp_path)


def test_agent_that_never_succeeds_states_no_claims(tmp_path: Path) -> None:
    model = ScriptedModel([{"requirements": "", "code": BROKEN}] * agent.MAX_EXECUTIONS)
    out = agent.generate(problems.load("compare"), model, 0, tmp_path)
    m = json.loads((out / "manifest.json").read_text())
    assert not m["author_succeeded"] and m["executions"] == agent.MAX_EXECUTIONS
    assert json.loads((out / "claims.json").read_text()) == []


def test_results_validation() -> None:
    ex = agent.execute("import json\njson.dump({'rf_accuracy_mean': 'high'}, open('results.json','w'))\n", "",
                       ["rf_accuracy_mean", "lr_accuracy_mean"])  # fmt: skip
    assert "missing lr_accuracy_mean" in ex.problem and "non-numeric rf_accuracy_mean" in ex.problem


def test_venv_rerun_sees_only_code_and_requirements(tmp_path: Path) -> None:
    art = tmp_path / "art"
    art.mkdir()
    (art / "run.py").write_text("import json, os\njson.dump({'n': len(os.listdir('.'))}, open('results.json', 'w'))\n")
    (art / "requirements.txt").write_text("")
    (art / "results.json").write_text('{"secret": 1}')
    m = rerun(art, tmp_path / "out", "venv", "v1", "test")
    assert m["build_exit"] == 0 and m["run_exit"] == 0 and m["results_written"]
    files = json.loads((tmp_path / "out" / "results.json").read_text())
    assert files["n"] >= 2  # run.py, requirements.txt, the venv and pip's own files; never the original results
    assert "secret" not in (tmp_path / "out" / "results.json").read_text()


def test_api_lists_scores_and_serves_logs(tmp_path: Path) -> None:
    arts, rr = tmp_path / "artifacts", tmp_path / "reruns"
    write_artifact(
        arts, "compare-qwen3-4b-s0", {"a": 1.0}, [{"text": "t", "left": "a", "op": ">", "right": "0", "tolerance": 0}]
    )
    write_rerun(rr, "compare-qwen3-4b-s0", "container-1", {"a": 1.0})
    c = TestClient(create_app(artifacts=arts, reruns=rr, results=tmp_path / "results", static_dir=tmp_path / "none"))
    rows = c.get("/api/artifacts").json()["artifacts"]
    assert rows[0]["rrs"] > 0.9 and rows[0]["components"]["claims"] == 1.0
    d = c.get("/api/artifacts/compare-qwen3-4b-s0").json()
    assert d["claims"][0]["checks"]["container-1"]["holds"] is True
    assert c.get("/api/artifacts/compare-qwen3-4b-s0/reruns/container-1/build.log").text.startswith("Successfully")
    assert c.get("/api/artifacts/compare-qwen3-4b-s0/reruns/container-1/secrets.txt").status_code == 404
    assert c.get("/api/artifacts/..%2F..%2Fetc").status_code == 404
    assert c.post("/api/artifacts").status_code == 405
    assert c.get("/api/experiments").json()["experiments"][0]["status"] == "pending"
    t = TestClient(create_app(token="k", artifacts=arts, reruns=rr, results=tmp_path / "results"))
    assert t.get("/api/artifacts").status_code == 401
    assert t.get("/api/artifacts", headers={"Authorization": "Bearer k"}).status_code == 200
    assert t.get("/api/health").status_code == 200


@pytest.mark.docker
def test_container_rerun_installs_only_requirements(tmp_path: Path) -> None:
    art = tmp_path / "art"
    art.mkdir()
    (art / "run.py").write_text(
        "import json, sys\nimport numpy\njson.dump({'v': numpy.__version__ == '2.1.3'}, open('results.json', 'w'))\n"
    )
    (art / "requirements.txt").write_text("numpy==2.1.3\n")
    m = rerun(art, tmp_path / "out", "container", "c1", "test")
    assert m["build_exit"] == 0 and m["run_exit"] == 0
    assert json.loads((tmp_path / "out" / "results.json").read_text()) == {"v": True}
    assert "numpy==2.1.3" in (tmp_path / "out" / "freeze.txt").read_text()
