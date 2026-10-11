# Decisions

Made during the build, after `docs/PLAN.md` was written; each says what changed and why.

**D1. Local open-weights agents only.** The portfolio owner chose to work without a hosted-model API
key (Project 04, 2026-10-09). The agents are Qwen3-4B-Instruct-2507 (Q4_0) and Phi-4-mini-instruct
(Q4_K_M) on CPU through llama.cpp with schema-constrained JSON replies. Results describe these
small models, not frontier agents.

**D2. One claim form instead of two.** The plan had *comparison* and *value* claims. Both are now
`left op right` where `right` is a key or a number and `≈` carries a tolerance. One checker covers
both, the agent fills one schema, and the claim's left side is restricted (by the schema's enum) to
keys its own `results.json` contains.

**D3. The agent is told that someone will rerun its work, and nothing more.** It is told its
installed packages and that another researcher will rerun from the files it leaves. It is not told
to set seeds or pin versions: those choices are what is measured.

**D4. Author sandbox = this repository's interpreter.** The agent's `run.py` runs with the same
Python and packages (numpy 2.5.4, scipy 1.18.1, scikit-learn 1.9.1, pandas) that the repository
uses, in an empty temp directory, with a 300 s timeout and BLAS threads fixed to 1. That is the
"author's machine": it has packages installed that a clean environment does not.

**D5. Reruns see only `run.py` and `requirements.txt`.** Never the original results or claims.

**D6. Two container reruns plus one CI rerun.** Two identical container reruns on this machine
separate non-determinism (they disagree with each other) from environment drift (they agree with
each other and not with the author). The third rerun is on a GitHub Actions runner in a fresh
virtual environment: another machine, kernel and CPU. The rerun script uses only the standard
library so CI runs it straight from a checkout.

**D7. Container image from a mirror.** Docker Hub returned HTTP 429 (anonymous pull limit) from
this machine. The image is `mirror.gcr.io/library/python:3.12-slim`, Google's pull-through mirror
of the same official image; its digest is recorded in every rerun's `meta.json`.

**D8. Network plumbing passed into containers.** This machine reaches PyPI only through an
outbound proxy with its own CA. Containers run with `--network host`, the proxy variables and the
CA bundle mounted read-only (`PIP_CERT`, `SSL_CERT_FILE`). This changes how pip reaches PyPI, not
what it installs; it is recorded here because it is a difference from a plain `docker run`.

**D9. One BLAS/OpenMP thread in every rerun.** Without it, a 4-core machine running four
containers' worth of OpenBLAS threads made one reference take 220 s instead of 2.5 s. One thread
also removes thread-count-dependent floating-point reduction order as a source of differences, so
differences that remain are the code's own. Recorded in `meta.json` (`thread_env`).

**D10. Schema string caps removed.** llama.cpp's grammar compiler aborts the process on long
`maxLength` constraints (observed in Project 09 at 1,400 characters). The code and README fields
have no cap; the token budget bounds them instead.

**D11. Controls are hand-written, with expectations written first.** Six reference artifacts, each
with one planted defect (or none), go through the same author sandbox and the same reruns. Their
expected high/low components are in `references/*/expected.yaml`, written before any rerun; E2
reports where the score agrees and where it does not, without adjusting the expectations.

**D12. Reference pins match the author environment.** The pinned references pin the exact versions
the author sandbox has (numpy 2.5.4, scipy 1.18.1, scikit-learn 1.9.1), so a pinned control
reproduces the author's environment and an unpinned one gets whatever PyPI serves on the day of the
rerun.

**D13. No error bars.** Eight agent artifacts and six controls: counts are reported, not rates
with intervals (METRICS).

**D14. Claims that cannot be evaluated are reported apart from false claims.** The claims
component is unchanged: a claim that cannot be evaluated cannot hold (METRICS). But E3 first
counted both kinds as "false on the author's own results", which overstated how often the agents
were wrong about their numbers. Qwen3-4B wrote the number in the claim's text and a word in the
structured `right` field (for example `"right": "Heavy"` for "rf_accuracy_mean ≥ 0.95") in 15 of
its 20 claims. E3 now reports claims that cannot be evaluated and well-formed false claims
separately. Changed after the first E3 run was read; it changes a table, not a score.

**D15. Value patterns follow the tolerance, not the cause.** E3's per-artifact pattern compares
values with the reproduction tolerance (|Δ| ≤ max(0.005, 1%)). An unseeded bootstrap whose noise is
close to the tolerance can therefore read as "differs between machines" when two container reruns
happened to land within tolerance of each other and the CI rerun did not
(`bootstrap-qwen3-4b-s0`). The report names the cause (no seed) from the code, not from the label.
