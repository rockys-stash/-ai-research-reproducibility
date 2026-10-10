# Plan: AI Research Reproducibility Benchmark

> Written before any agent ran; changes made during the build are recorded in `docs/DECISIONS.md`.

## 1. Question

When an AI agent produces a small piece of research (code, environment, results and claims), **can
that research be reproduced by someone else, on another machine, from what the agent left
behind?** We give agents controlled research problems, freeze what they produce, and rerun it
independently in clean environments. Every component of the score is computed from a rerun log.

## 2. What an agent produces (an *artifact*)

For a research problem the agent writes, in its own sandbox:

| File | Content |
|---|---|
| `requirements.txt` | the third-party packages the code needs (the agent decides whether to pin) |
| `run.py` | the whole experiment: load data, process, train/evaluate, write `results.json` |
| `results.json` | written by `run.py` (numbers only, flat keys) |
| `claims.json` | the agent's conclusions, as structured claims about its results (§5) |
| `README.md` | what was done, in the agent's words |

The agent works in a loop: write `run.py`, execute it in its sandbox, read the error or the output,
revise (at most 4 executions). Then it reads its `results.json` and writes its claims. The
artifact is frozen (hashed) at that point; nothing in it is edited afterwards.

## 3. Problems

Four controlled problems, each solvable on CPU in under a minute with data shipped inside
scikit-learn (no download, so data availability is not a confound). Each problem states what must
be in `results.json`.

| Key | Problem | Reproducibility hazard it exposes |
|---|---|---|
| compare | Breast cancer (sklearn): does a random forest beat logistic regression in 5-fold CV accuracy? | stochastic model, fold shuffling |
| features | Diabetes (sklearn): do degree-2 polynomial features improve ridge regression R² under 5-fold CV? | deterministic baseline (a reproducible control from the agent itself) |
| mlp | Digits (sklearn): test accuracy of a small MLP on a 75/25 split, and how it changes with hidden size 32 vs 128 | stochastic training, split seed |
| bootstrap | Wine (sklearn): 95% bootstrap interval of the difference in mean alcohol between classes 0 and 1 | resampling randomness |

## 4. Agents

Qwen3-4B-Instruct-2507 and Phi-4-mini-instruct, local, CPU (no hosted model; portfolio decision
2026-10-09). 4 problems × 2 agents = 8 artifacts. Plus **reference artifacts** written by hand with
known properties, used as controls (§7 E2).

## 5. Claims

A claim is structured so that it can be checked against any rerun's results:

```json
{"text": "The random forest is more accurate than logistic regression",
 "kind": "comparison", "left": "rf_accuracy_mean", "op": ">", "right": "lr_accuracy_mean"}
{"text": "Logistic regression reaches about 0.95 accuracy",
 "kind": "value", "key": "lr_accuracy_mean", "value": 0.95, "tolerance": 0.01}
```

Claims about keys that are not in `results.json`, or that do not parse, are counted as
unsupported.

## 6. Reproduction and the four components

Each artifact is rerun in three independent executions:

| Rerun | Where | Environment |
|---|---|---|
| R1, R2 | a fresh container (`python:3.12-slim`), twice | only `requirements.txt` installed, from PyPI, in a clean image |
| R3 | another machine: a GitHub Actions `ubuntu-latest` runner | the same, built by CI; its logs are downloaded and committed |

Each rerun writes a log: environment build output, installed versions, the command, exit code,
stdout/stderr, wall time, and the `results.json` it produced.

| Component | Score in [0, 1] | From |
|---|---|---|
| **Code** | share of reruns whose `run.py` exits 0 and writes a valid `results.json` | rerun exit codes |
| **Environment** | mean of: the environment builds in the clean image (share of reruns); every third-party module the code imports is declared; every declared package is pinned to a version | build logs; static import scan of `run.py` |
| **Results** | share of the original numeric results that every successful rerun reproduces within tolerance (|Δ| ≤ max(0.005, 1% of the value)); a failed rerun reproduces nothing | original vs rerun `results.json` |
| **Claims** | share of claims that hold in every rerun (and in the original) | claims checked against each `results.json` |

**Research Reproducibility Score (RRS)** = 0.25 Code + 0.20 Environment + 0.30 Results + 0.25 Claims.
Results weigh most because a reproduced number is the core of reproducibility; the environment
weighs least because a missing pin is a risk, not yet a failure. E5 reports how the ranking
changes under other weightings. Every component links to the log lines it came from.

## 7. Experiments

| | Question |
|---|---|
| E1 | RRS and components per artifact and agent |
| E2 | Does the score catch known defects? Reference artifacts: fully reproducible; no random seed; unpinned dependency; undeclared import; claim not supported by its own results; code that fails outside the author's machine (absolute path) |
| E3 | Why do reruns fail or differ? A taxonomy from the logs (import error, install failure, runtime error, non-determinism, version drift, unsupported claim) |
| E4 | Does the second machine change anything? Container vs CI runner, value by value |
| E5 | Weight sensitivity: rank correlation of artifacts under equal, results-only and code-gated weightings |

## 8. Deliverables

Python package `reprobench`; problems; frozen artifacts with generation transcripts; rerun logs from
both machines; E1–E5 with versioned results; `docs/REPORT.md`; the **Laboratory** console
(artifact list; generated-vs-reproduced comparison of every value and claim; logs); tests; CI.
