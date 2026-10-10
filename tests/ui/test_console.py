"""Browser tests for the Laboratory console.

The fixture writes artifacts and rerun directories to a temporary tree (an agent artifact whose
reruns partly fail, and a reproducible reference control) plus one experiment result, then serves
the built console. Run with ``uv run pytest -m ui`` after ``npm --prefix web run build``.
"""

from __future__ import annotations

import json
import socket
import threading
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import write_artifact, write_rerun

ROOT = Path(__file__).resolve().parents[2]
AXE = ROOT / "web" / "node_modules" / "axe-core" / "axe.min.js"
pytestmark = [pytest.mark.ui]
playwright_api = pytest.importorskip("playwright.sync_api")

VIEWPORTS = {"desktop": {"width": 1440, "height": 900}, "mobile": {"width": 390, "height": 844}}
AGENT, REF = "compare-qwen3-4b-s0", "ref-reproducible"
VALUES = {"rf_accuracy_mean": 0.9561, "lr_accuracy_mean": 0.9508, "accuracy_difference": 0.0053}
CLAIMS = [{"text": "The random forest is more accurate", "left": "rf_accuracy_mean", "op": ">",
           "right": "lr_accuracy_mean", "tolerance": 0}]  # fmt: skip


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _tree(tmp: Path) -> tuple[Path, Path, Path]:
    arts, rr, res = tmp / "artifacts", tmp / "reruns", tmp / "results"
    a = write_artifact(arts, AGENT, VALUES, CLAIMS, code="import json\nimport numpy\n", requirements="numpy\n")
    (a / "transcript.jsonl").write_text(
        json.dumps({"step": "code", "attempt": 1, "call": {"seconds": 12.5, "completion_tokens": 300},
                    "execution": {"exit_code": 1, "seconds": 0.4, "problem": "the script exited with code 1",
                                  "stdout": "", "stderr": "NameError: name 'np' is not defined"}}) + "\n"
        + json.dumps({"step": "code", "attempt": 2, "call": {"seconds": 10.0, "completion_tokens": 280},
                      "execution": {"exit_code": 0, "seconds": 3.1, "problem": "", "stdout": "", "stderr": ""}}) + "\n"
        + json.dumps({"step": "claims", "call": {"seconds": 4.0, "completion_tokens": 90}}) + "\n")  # fmt: skip
    write_rerun(rr, AGENT, "container-1", {**VALUES, "rf_accuracy_mean": 0.9490, "accuracy_difference": -0.0018})
    write_rerun(
        rr, AGENT, "container-2", None, run=1, err="Traceback\nModuleNotFoundError: No module named 'sklearn'\n"
    )
    r = write_artifact(arts, REF, VALUES, CLAIMS, requirements="numpy==2.5.4\n", kind="reference",
                       code="import json\nimport numpy\n")  # fmt: skip
    m = json.loads((r / "manifest.json").read_text())
    (r / "manifest.json").write_text(json.dumps({**m, "defect": "none", "expect": "every component high"}))
    for rid in ("container-1", "container-2"):
        write_rerun(rr, REF, rid, VALUES)
    run = res / "e1_scores" / "20260101T000000Z-abcdef0"
    run.mkdir(parents=True)
    table = {"id": "t", "caption": "RRS per artifact", "columns": [{"key": "artifact", "label": "Artifact", "align": "l"},
             {"key": "rrs", "label": "RRS", "align": "r"}], "rows": [{"artifact": AGENT, "rrs": 0.4}]}  # fmt: skip
    (run / "summary.json").write_text(json.dumps({"title": "E1 Reproducibility scores", "question": "How reproducible?",
                                                  "findings": ["A finding."], "tables": [table], "notes": []}))  # fmt: skip
    (run / "provenance.json").write_text(json.dumps({"experiment": "e1_scores", "run_id": run.name, "commit": "abcdef0",
                                                     "dirty": False, "created_at": "2026-01-01", "runtime_seconds": 1}))  # fmt: skip
    (res / "e1_scores" / "LATEST").write_text(run.name + "\n")
    return arts, rr, res


@pytest.fixture(scope="module")
def base_url(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    if not (ROOT / "web" / "dist" / "index.html").exists():
        pytest.skip("frontend not built (npm --prefix web run build)")
    import uvicorn

    from reprobench.api import create_app

    arts, rr, res = _tree(tmp_path_factory.mktemp("ui"))
    app = create_app(artifacts=arts, reruns=rr, results=res)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(f"{url}/api/health", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    yield url
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    with playwright_api.sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


PAGES = [
    ("overview", "/overview", "Research Reproducibility Score"),
    ("artifacts", "/artifacts", "of 2 artifacts"),
    ("artifact", f"/artifacts/{AGENT}", "Generated vs reproduced"),
    ("reference", f"/artifacts/{REF}", "Claims, checked against every run"),
    ("e1", "/experiments/e1_scores", "Findings"),
    ("e4-pending", "/experiments/e4_machines", "pending"),
    ("method", "/method", "Rerunning it"),
    ("not-found", "/nowhere", "Page not found"),
]


def _open(browser: Any, base_url: str, viewport: str, path: str, marker: str, scheme: str = "light") -> Any:
    ctx = browser.new_context(viewport=VIEWPORTS[viewport], color_scheme=scheme)
    page = ctx.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "40" not in m.text else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base_url + path)
    page.get_by_text(marker, exact=False).first.wait_for(timeout=30000)
    page.wait_for_load_state("networkidle")
    page.errors = errors
    return page


@pytest.mark.parametrize("viewport", list(VIEWPORTS))
@pytest.mark.parametrize(("name", "path", "marker"), PAGES)
def test_page_renders(browser: Any, base_url: str, viewport: str, name: str, path: str, marker: str) -> None:
    page = _open(browser, base_url, viewport, path, marker)
    assert page.locator("h1").count() == 1
    assert not page.locator(".skeleton").count(), "loading skeleton still visible"
    assert not page.locator("[role=alert]").count(), "error state rendered"
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert overflow <= 1, f"page scrolls horizontally by {overflow}px"
    assert not page.errors, page.errors
    page.context.close()


def test_filter_and_drill_down_to_a_failed_rerun(browser: Any, base_url: str) -> None:
    page = _open(browser, base_url, "desktop", "/artifacts", "of 2 artifacts")
    page.get_by_role("combobox", name="Kind").select_option("agent")
    page.get_by_text("1 of 2 artifacts").wait_for()
    page.get_by_role("link", name=AGENT).click()
    page.get_by_text("Generated vs reproduced").wait_for()
    page.get_by_text("No module named 'sklearn'").filter(visible=True).first.wait_for()
    page.get_by_text("NameError: name 'np' is not defined").filter(visible=True).first.wait_for()
    page.context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport", list(VIEWPORTS))
def test_no_wcag_violations(browser: Any, base_url: str, viewport: str, scheme: str) -> None:
    """axe-core audit (WCAG 2.1 A/AA and best practices) of every view in both themes."""
    if not AXE.exists():
        pytest.skip("axe-core not installed (npm --prefix web ci)")
    ctx = browser.new_context(viewport=VIEWPORTS[viewport], color_scheme=scheme, bypass_csp=True)
    page = ctx.new_page()
    found: dict[str, list[str]] = {}
    for _, path, marker in PAGES:
        page.goto(base_url + path)
        page.get_by_text(marker, exact=False).first.wait_for(timeout=30000)
        page.wait_for_load_state("networkidle")
        page.add_script_tag(path=str(AXE))
        violations = page.evaluate(
            """async () => (await axe.run(document, {runOnly: ['wcag2a', 'wcag2aa', 'wcag21aa',
               'best-practice']})).violations.map(v => v.id + ': ' + v.nodes.map(n => n.target.join(' ')).join(', '))"""
        )
        if violations:
            found[path] = violations
    ctx.close()
    assert not found, found
