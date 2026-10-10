"""Read-only HTTP API for the Laboratory console.

Every route reads frozen artifacts, rerun directories and result directories; nothing is written.
With ``REPROBENCH_TOKEN`` set, every route but ``/api/health`` needs ``Authorization: Bearer
<token>``. Every client is rate limited; security headers on every response.
"""

from __future__ import annotations

import hmac
import json
import re
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from reprobench import claims, scoring
from reprobench.paths import ARTIFACTS, RERUNS, RESULTS, ROOT
from reprobench.results_md import EXPERIMENTS

_ID = re.compile(r"^[a-z0-9][a-z0-9.-]{0,80}$")
_RESULT = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-z]{4,40}$")
ARTIFACT_FILES = ("requirements.txt", "run.py", "results.json", "claims.json", "README.md")
RERUN_FILES = ("build.log", "freeze.txt", "run.out", "run.err", "results.json", "meta.json")
MAX_TEXT = 400_000


class RateLimiter:
    """Token bucket per client address."""

    def __init__(self, rate: float, burst: int) -> None:
        self.rate, self.burst = rate, burst
        self._b: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            tokens, last = self._b.get(key, (float(self.burst), now))
            tokens = min(self.burst, tokens + (now - last) * self.rate)
            ok = tokens >= 1
            self._b[key] = (tokens - 1 if ok else tokens, now)
            if len(self._b) > 10_000:
                self._b = dict(list(self._b.items())[-5_000:])
            return ok


class Guard(BaseHTTPMiddleware):
    def __init__(self, app: Any, token: str, limiter: RateLimiter) -> None:
        super().__init__(app)
        self.token, self.limiter = token, limiter

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path.startswith("/api"):
            client = request.client.host if request.client else "unknown"
            if not self.limiter.allow(client):
                return JSONResponse({"detail": "rate limit exceeded"}, status_code=429, headers={"Retry-After": "1"})
            if request.method not in ("GET", "HEAD"):
                return JSONResponse({"detail": "method not allowed"}, status_code=405)
            if self.token and path != "/api/health":
                supplied = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
                if not hmac.compare_digest(supplied.encode(), self.token.encode()):
                    return JSONResponse({"detail": "unauthorized"}, status_code=401)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return response


def _read(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def _text(p: Path) -> str | None:
    if not p.is_file():
        return None
    t = p.read_text(encoding="utf-8", errors="replace")
    return t if len(t) <= MAX_TEXT else t[:MAX_TEXT] + "\n[... truncated ...]"


def create_app(token: str = "", artifacts: Path | None = None, reruns: Path | None = None, results: Path | None = None,
               static_dir: Path | None = None) -> FastAPI:  # fmt: skip
    from reprobench import problems

    arts = (artifacts or ARTIFACTS).resolve()
    rr = (reruns or RERUNS).resolve()
    res = (results or RESULTS).resolve()
    static = (static_dir or ROOT / "web" / "dist").resolve()
    app = FastAPI(title="reprobench", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(Guard, token=token, limiter=RateLimiter(rate=20.0, burst=60))

    def art_path(aid: str) -> Path:
        if not _ID.match(aid):
            raise HTTPException(404, "unknown artifact")
        p = (arts / aid).resolve()
        if not p.is_relative_to(arts) or not (p / "manifest.json").is_file() or aid.startswith("dev-"):
            raise HTTPException(404, "unknown artifact")
        return p

    def listed() -> list[str]:
        return sorted(p.parent.name for p in arts.glob("*/manifest.json") if not p.parent.name.startswith("dev-"))

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/problems")
    def problem_list() -> dict[str, Any]:
        ps = [problems.load(k) for k in problems.all_keys()]
        return {"problems": [{"key": p.key, "title": p.title, "problem": p.problem, "results_keys": p.results_keys}
                             for p in ps], "weights": scoring.WEIGHTS,
                "tolerance": {"absolute": scoring.ABS_TOL, "relative": scoring.REL_TOL}}  # fmt: skip

    @app.get("/api/artifacts")
    def artifact_list() -> dict[str, Any]:
        out = []
        for aid in listed():
            m = _read(arts / aid / "manifest.json")
            s = scoring.score(aid, arts, rr)
            out.append({"artifact": aid, "problem": m["problem"], "agent": m["agent"], "agent_label": m["agent_label"],
                        "kind": m["kind"], "defect": m.get("defect"), "author_succeeded": m["author_succeeded"],
                        "executions": m["executions"], "reruns": len(s.reruns), "rrs": round(s.rrs, 4),
                        "components": {k: round(c.score, 4) for k, c in s.components.items()}})  # fmt: skip
        return {"artifacts": out}

    @app.get("/api/artifacts/{aid}")
    def artifact_detail(aid: str) -> dict[str, Any]:
        p = art_path(aid)
        s = scoring.score(aid, arts, rr)
        reruns: list[dict[str, Any]] = []
        loaded = scoring.load_reruns(aid, rr)
        for r in loaded:
            reruns.append({"id": r.id, "meta": r.meta, "results": r.results, "ran": r.ran,
                           "category": scoring.classify(r), "err_tail": r.tail("run.err", 12)})  # fmt: skip
        transcript = []
        if (p / "transcript.jsonl").exists():
            for line in (p / "transcript.jsonl").read_text(encoding="utf-8").splitlines():
                t = json.loads(line)
                call = t.get("call") or {}
                transcript.append({"step": t["step"], "attempt": t.get("attempt"), "execution": t.get("execution"),
                                   "seconds": call.get("seconds"), "completion_tokens": call.get("completion_tokens")})  # fmt: skip
        orig = _read(p / "results.json") if (p / "results.json").is_file() else {}
        cl = _read(p / "claims.json") if (p / "claims.json").is_file() else []
        claim_checks = []
        for c in cl if isinstance(cl, list) else []:
            if not isinstance(c, dict):
                continue
            checks = {"original": claims.check(c, orig if isinstance(orig, dict) else {})}
            checks |= {r.id: claims.check(c, r.results or {}) for r in loaded}
            claim_checks.append(
                {"claim": c, "checks": {k: {"holds": v.holds, "detail": v.detail} for k, v in checks.items()}}
            )
        return {"manifest": _read(p / "manifest.json"), "files": {n: _text(p / n) for n in ARTIFACT_FILES},
                "score": s.as_dict(), "reruns": reruns, "transcript": transcript, "claims": claim_checks}  # fmt: skip

    @app.get("/api/artifacts/{aid}/reruns/{rid}/{name}")
    def rerun_file(aid: str, rid: str, name: str) -> Response:
        art_path(aid)
        if not _ID.match(rid) or name not in RERUN_FILES:
            raise HTTPException(404, "unknown file")
        p = (rr / aid / rid / name).resolve()
        if not p.is_relative_to(rr):
            raise HTTPException(404, "unknown file")
        t = _text(p)
        if t is None:
            raise HTTPException(404, "file not written by this rerun")
        return PlainTextResponse(t)

    def latest(name: str) -> Path | None:
        m = res / name / "LATEST"
        if not m.is_file():
            return None
        rid = m.read_text(encoding="utf-8").strip()
        if not _RESULT.match(rid) or not (res / name / rid / "summary.json").is_file():
            return None
        return res / name / rid

    @app.get("/api/experiments")
    def experiments() -> dict[str, Any]:
        out = []
        for name in EXPERIMENTS:
            d = latest(name)
            if d is None:
                out.append({"name": name, "status": "pending"})
                continue
            s, pv = _read(d / "summary.json"), _read(d / "provenance.json")
            out.append({"name": name, "status": "done", "title": s["title"], "question": s["question"],
                        "findings": s["findings"], "run_id": d.name, "commit": pv["commit"][:7], "dirty": pv["dirty"],
                        "created_at": pv["created_at"], "runtime_seconds": pv["runtime_seconds"]})  # fmt: skip
        return {"experiments": out}

    @app.get("/api/experiments/{name}")
    def experiment(name: str) -> dict[str, Any]:
        if name not in EXPERIMENTS:
            raise HTTPException(404, "unknown experiment")
        d = latest(name)
        if d is None:
            raise HTTPException(404, f"{name} has not been run")
        return {"summary": _read(d / "summary.json"), "provenance": _read(d / "provenance.json")}

    @app.get("/api/{rest:path}")
    def api_404(rest: str) -> Response:
        return JSONResponse({"detail": "not found"}, status_code=404)

    @app.get("/{rest:path}")
    def spa(rest: str) -> Response:
        if not static.exists():
            return JSONResponse({"detail": "console not built (npm --prefix web run build)"}, status_code=404)
        candidate = (static / rest).resolve()
        if rest and candidate.is_file() and candidate.is_relative_to(static):
            return FileResponse(candidate)
        return FileResponse(static / "index.html")

    return app
