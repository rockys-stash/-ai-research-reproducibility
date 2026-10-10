"""Rerun an artifact from scratch in a clean environment and log everything.

This module uses the standard library only, so another machine can run it straight from a checkout
without installing this package (the CI rerun does exactly that):

    python src/reprobench/rerun.py ARTIFACT_DIR OUT_DIR --mode venv --rerun-id ci-1

Only ``requirements.txt`` and ``run.py`` are copied into an empty working directory; the original
``results.json`` and ``claims.json`` are never visible to the rerun. Two modes:

- ``container``: a fresh ``python:3.12-slim`` container (Docker); packages are installed from PyPI
  into the image's interpreter, which has nothing else installed;
- ``venv``: a new virtual environment created with the machine's own Python, without system
  site-packages.

The rerun directory receives ``build.log`` (pip output), ``freeze.txt`` (what was installed),
``run.out`` / ``run.err``, ``results.json`` if the script wrote one, and ``meta.json`` with exit
codes, timings, the interpreter and machine.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

IMAGE = "mirror.gcr.io/library/python:3.12-slim"
BUILD_TIMEOUT_S = 900
RUN_TIMEOUT_S = 900
COPIED = ("requirements.txt", "run.py")


def _stage(artifact: Path, work: Path) -> None:
    for name in COPIED:
        src = artifact / name
        if src.exists():
            shutil.copy2(src, work / name)
    if not (work / "requirements.txt").exists():
        (work / "requirements.txt").write_text("", encoding="utf-8")


def _proxy_env() -> list[str]:
    """Pass this machine's outbound proxy and CA bundle into the container (network plumbing only)."""
    args: list[str] = []
    for k in ("HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "https_proxy", "http_proxy", "no_proxy"):
        if os.environ.get(k):
            args += ["-e", k]
    ca = os.environ.get("REPROBENCH_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    if ca and Path(ca).exists():
        args += ["-v", f"{ca}:/etc/rerun-ca.crt:ro", "-e", "PIP_CERT=/etc/rerun-ca.crt",
                 "-e", "SSL_CERT_FILE=/etc/rerun-ca.crt", "-e", "REQUESTS_CA_BUNDLE=/etc/rerun-ca.crt"]  # fmt: skip
    return args


# One BLAS/OpenMP thread in every rerun: a harness setting that keeps reruns comparable across
# machines with different core counts and keeps the host responsive; it is recorded in meta.json.
THREAD_ENV = {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}

SCRIPT = """
set +e
python -m pip install --disable-pip-version-check --no-cache-dir --no-input -r requirements.txt > build.log 2>&1
echo $? > build.exit
python -m pip freeze --all > freeze.txt 2>/dev/null
python -c "import sys, platform; print(sys.version.split()[0]); print(platform.platform())" > python.txt
start=$(date +%s.%N)
timeout {run_timeout} python run.py > run.out 2> run.err
echo $? > run.exit
end=$(date +%s.%N)
echo "$start $end" > run.time
"""


def _container(work: Path) -> dict[str, Any]:
    digest = subprocess.run(["docker", "image", "inspect", "--format", "{{json .RepoDigests}}", IMAGE],
                            capture_output=True, text=True).stdout.strip()  # fmt: skip
    if not digest:
        subprocess.run(["docker", "pull", "-q", IMAGE], capture_output=True, text=True, timeout=600)
        digest = subprocess.run(["docker", "image", "inspect", "--format", "{{json .RepoDigests}}", IMAGE],
                                capture_output=True, text=True).stdout.strip()  # fmt: skip
    threads = [x for k, v in THREAD_ENV.items() for x in ("-e", f"{k}={v}")]
    cmd = ["docker", "run", "--rm", "--network", "host", *threads, *_proxy_env(), "-v", f"{work}:/work", "-w", "/work",
           IMAGE, "sh", "-c", SCRIPT.format(run_timeout=RUN_TIMEOUT_S)]  # fmt: skip
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=BUILD_TIMEOUT_S + RUN_TIMEOUT_S + 120)
    return {"image": IMAGE, "image_digests": json.loads(digest) if digest else [], "docker_exit": p.returncode,
            "docker_stderr": p.stderr[-2000:]}  # fmt: skip


def _venv(work: Path) -> dict[str, Any]:
    env_dir = work / ".venv"
    subprocess.run([sys.executable, "-m", "venv", str(env_dir)], check=True, capture_output=True, timeout=300)
    py = env_dir / "bin" / "python"
    script = SCRIPT.replace("python ", f"{py} ").format(run_timeout=RUN_TIMEOUT_S)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "VIRTUAL_ENV"))} | THREAD_ENV
    p = subprocess.run(["bash", "-c", script], cwd=work, capture_output=True, text=True, env=env,
                       timeout=BUILD_TIMEOUT_S + RUN_TIMEOUT_S + 120)  # fmt: skip
    return {"base_python": sys.version.split()[0], "shell_exit": p.returncode}


def _read(p: Path, default: str = "") -> str:
    return p.read_text(encoding="utf-8", errors="replace") if p.exists() else default


def _int(p: Path) -> int | None:
    s = _read(p).strip()
    return int(s) if s.lstrip("-").isdigit() else None


def rerun(artifact: Path, out: Path, mode: str, rerun_id: str, machine: str = "") -> dict[str, Any]:
    """Rerun ``artifact`` and write the rerun directory ``out``; returns its meta record."""
    out.mkdir(parents=True, exist_ok=False)
    started = datetime.now(UTC).isoformat(timespec="seconds")
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="rerun-") as tmp:
        work = Path(tmp)
        work.chmod(0o777)
        _stage(artifact, work)
        info = _container(work) if mode == "container" else _venv(work)
        for name in ("build.log", "freeze.txt", "run.out", "run.err", "results.json"):
            if (work / name).exists():
                text = _read(work / name)
                if name != "results.json" and len(text) > 200_000:  # keep logs bounded; the tail holds the error
                    text = "[... truncated ...]\n" + text[-200_000:]
                (out / name).write_text(text, encoding="utf-8")
        times = _read(work / "run.time").split()
        py = _read(work / "python.txt").splitlines()
        meta = {
            "rerun_id": rerun_id,
            "mode": mode,
            "machine": machine or platform.node(),
            "started": started,
            "build_exit": _int(work / "build.exit"),
            "run_exit": _int(work / "run.exit"),
            "run_seconds": round(float(times[1]) - float(times[0]), 2) if len(times) == 2 else None,
            "total_seconds": round(time.perf_counter() - t0, 2),
            "python": py[0] if py else None,
            "platform": py[1] if len(py) > 1 else None,
            "results_written": (work / "results.json").exists(),
            "thread_env": THREAD_ENV,
            **info,
        }
    (out / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("artifact", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--mode", choices=["container", "venv"], default="container")
    ap.add_argument("--rerun-id", required=True)
    ap.add_argument("--machine", default="")
    a = ap.parse_args(argv)
    m = rerun(a.artifact.resolve(), a.out.resolve(), a.mode, a.rerun_id, a.machine)
    print(json.dumps({k: m[k] for k in ("rerun_id", "build_exit", "run_exit", "results_written")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
