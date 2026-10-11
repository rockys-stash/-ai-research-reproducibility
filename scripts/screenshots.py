"""Capture screenshots of the running console from the committed artifacts, reruns and results.

Usage: uv run python scripts/screenshots.py [--out docs/screenshots]
Needs the built console (npm --prefix web run build), Chromium for Playwright and
the measured results (make experiments).
"""

from __future__ import annotations

import argparse
import socket
import threading
import time
import urllib.request
from pathlib import Path

import uvicorn
from playwright.sync_api import ViewportSize, sync_playwright

from reprobench.api import create_app

ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS: dict[str, ViewportSize] = {
    "desktop": {"width": 1440, "height": 900},
    "mobile": {"width": 390, "height": 844},
}


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "screenshots")
    ap.add_argument("--results", type=Path, default=ROOT / "results")
    args = ap.parse_args()
    app = create_app(results=args.results)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(base + "/api/health", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    shots = [("overview", "/overview"), ("artifacts", "/artifacts"), ("artifact-agent", "/artifacts/compare-phi-4-mini-s0"),
             ("artifact-reference", "/artifacts/ref-overclaim"), ("e1", "/experiments/e1_scores"),
             ("e2", "/experiments/e2_controls"), ("e3", "/experiments/e3_failures"), ("e4", "/experiments/e4_machines"),
             ("method", "/method")]  # fmt: skip
    args.out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for vp, size in VIEWPORTS.items():
            for scheme in ("light", "dark"):
                if vp == "mobile" and scheme == "dark":
                    continue
                ctx = browser.new_context(viewport=size, color_scheme=scheme, device_scale_factor=1)
                page = ctx.new_page()
                for name, path in shots:
                    page.goto(base + path)
                    page.locator("h1").first.wait_for(timeout=30000)
                    page.wait_for_load_state("networkidle")
                    if page.locator(".skeleton").count():
                        page.locator(".skeleton").first.wait_for(state="detached", timeout=30000)
                    out = args.out / f"{name}-{vp}{'-dark' if scheme == 'dark' else ''}.png"
                    page.screenshot(path=str(out), full_page=vp == "desktop")
                    print(out)
                ctx.close()
        browser.close()
    server.should_exit = True


if __name__ == "__main__":
    main()
