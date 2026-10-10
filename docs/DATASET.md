# Data

No data is downloaded. Every problem uses a dataset that ships inside scikit-learn, so data
availability cannot be a cause of irreproducibility (that is a different question from the one
studied here).

| Problem | Dataset | Loader | Rows × features | Target |
|---|---|---|---|---|
| compare | Breast Cancer Wisconsin (Diagnostic) | `load_breast_cancer` | 569 × 30 | malignant / benign |
| features | Diabetes (Efron et al., 2004) | `load_diabetes` | 442 × 10 | disease progression after one year |
| mlp | Optical recognition of handwritten digits (8×8) | `load_digits` | 1,797 × 64 | digit 0–9 |
| bootstrap | Wine recognition | `load_wine` | 178 × 13 | cultivar 0–2 |

The reference control `abs-path` writes the diabetes data to `/tmp/reprobench-author-data/diabetes.csv`
on the author's machine before freezing, and reads it from there: the file exists for the author
and nowhere else, which is the defect being planted.

## What is committed

- `artifacts/` — every frozen artifact: the files the agent left, its transcript (every prompt,
  reply, execution and error) and a manifest with SHA-256 hashes and the author's environment.
- `reruns/` — every rerun directory: pip output, `pip freeze`, stdout, stderr, the results the rerun
  wrote, and `meta.json` (exit codes, timings, interpreter, machine, image digest).
- `results/` — versioned experiment outputs with provenance (commit, input hashes, timestamps).

Licences: the scikit-learn datasets are distributed with scikit-learn (BSD-3-Clause); the
underlying datasets are from the UCI Machine Learning Repository and Efron et al.
