# Design

## Pipeline

```
problems/*.yaml ──► agent (local LLM, author sandbox, ≤4 executions) ──► artifacts/<id>/   (frozen, SHA-256)
references/*    ──► references.freeze (same author sandbox)          ──► artifacts/ref-*/
artifacts/<id>  ──► rerun.py container ×2 (this machine, Docker)      ──► reruns/<id>/container-{1,2}/
                ──► rerun.py venv on a GitHub Actions runner          ──► reruns/<id>/ci-1/   (make import-ci)
artifacts + reruns ──► scoring (four components, evidence) ──► experiments E1–E5 ──► results/ ──► console, REPORT
```

Everything downstream of the reruns is a pure function of committed files: `make experiments`
needs no model, no Docker and no network.

## Modules (`src/reprobench`)

| Module | Role |
|---|---|
| `problems.py` | the four research problems (`configs/problems/*.yaml`) and the brief an agent reads |
| `llm.py` | llama.cpp wrapper: schema-constrained JSON, per-call log (prompt, reply, seed, timing, tokens) |
| `agent.py` | the research agent loop; executes `run.py` in a fresh temp dir with the repository's interpreter (the author's machine); freezes `requirements.txt`, `run.py`, `results.json`, `claims.json`, `README.md`, `transcript.jsonl`, `manifest.json` (hashes, author environment) |
| `references.py` | freezes the six hand-written control artifacts through the same author sandbox |
| `rerun.py` | standard library only; stages **only** `run.py` and `requirements.txt` into an empty directory; `container` mode (fresh `python:3.12-slim`) or `venv` mode (new virtual environment, no system site-packages); writes `build.log`, `freeze.txt`, `run.out`, `run.err`, `results.json`, `meta.json` |
| `imports.py` | AST scan of imports; maps modules to distributions; parses requirement lines (pinned means `==`) |
| `claims.py` | structured claims `left op right` (> < >= <= ≈ with tolerance) checked against any results dict |
| `scoring.py` | the four components and the RRS, each with the evidence (rerun, file, detail) behind it; failure taxonomy |
| `experiments/` | E1–E5; each writes a versioned result directory with provenance |
| `api.py` | read-only FastAPI; token auth when `REPROBENCH_TOKEN` is set; rate limit; security headers; path checks |
| `web/` | Laboratory console (React, TypeScript, Vite) |

## Isolation of a rerun

The rerun never sees the author's `results.json`, `claims.json`, README or transcript; it cannot
copy the original numbers. The container starts from an image with nothing but Python and pip;
packages come from PyPI exactly as `requirements.txt` states. Proxy variables and a CA bundle are
passed in only so pip can reach PyPI through this machine's proxy (network plumbing; recorded in
DECISIONS). BLAS/OpenMP threads are fixed to 1 in every rerun and in the author sandbox.

## Console

Overview (RRS by artifact and agent, controls), Artifacts (sortable table with the four
components), Artifact (component cards with their evidence, generated-vs-reproduced value table,
claim-by-rerun matrix, rerun logs, frozen files, generation transcript), Experiments, Method. The
API is read-only: there is nothing to submit, so the console has no write paths.

## Security

Read-only API; bearer token (constant-time comparison) on every route except health when
`REPROBENCH_TOKEN` is set; serving on a non-loopback address without a token is refused; per-client
token-bucket rate limit; strict CSP and security headers; artifact and rerun ids validated by
pattern and resolved paths checked to stay inside their roots; only a fixed list of file names is
served. Agent code is executed in the author sandbox (a temp directory, a timeout) and in
containers; it is not sandboxed against a malicious author, which is acceptable for code written
by local models on fixed problems but is stated as a limitation.
