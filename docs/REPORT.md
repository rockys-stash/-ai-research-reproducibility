# Report: can AI-generated research be reproduced?

Every number is quoted from `docs/generated/results.md`, rendered from the experiment results in
`results/<experiment>/LATEST` (all on a clean commit). Evidence for each number is in the committed
artifacts (`artifacts/`) and rerun logs (`reruns/`).

## 1. Set-up

**Agents.** Qwen3-4B-Instruct-2507 and Phi-4-mini-instruct, 4-bit, on CPU through llama.cpp, with
schema-constrained replies (D1). Each agent was given four small problems with data bundled in
scikit-learn (D3 in PLAN §3): random forest vs logistic regression (breast cancer), polynomial
features for ridge regression (diabetes), MLP hidden size (digits), and a bootstrap interval
(wine). It wrote `run.py`, ran it in the author sandbox (this repository's interpreter, D4), revised
on errors (at most four executions), then read its results and wrote claims and a README. It was
told that someone would rerun its work, and nothing about seeds or pins (D3).

**Reruns.** Each frozen artifact was rerun three times from only `run.py` and `requirements.txt`
(D5): twice in a fresh `python:3.12-slim` container on this machine and once in a fresh virtual
environment on a GitHub Actions runner (D6). Six hand-written controls, each with one planted defect
and expectations written before any rerun, went through the same reruns (D11).

**Score.** Code (share of reruns that run), Environment (builds, declared, pinned), Results (share
of the author's numbers every rerun reproduces within max(0.005, 1%)), Claims (share of claims that
hold on the author's results and every rerun); RRS = 0.25·C + 0.20·E + 0.30·R + 0.25·Cl.

## 2. Results

### E1. How reproducible is agent-written research?

| Artifact | Code | Environment | Results | Claims | RRS |
|---|---:|---:|---:|---:|---:|
| bootstrap-phi-4-mini | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| bootstrap-qwen3-4b | 1.00 | 1.00 | 0.33 | 0.20 | 0.60 |
| compare-phi-4-mini | 1.00 | 0.33 | 0.67 | 1.00 | 0.77 |
| compare-qwen3-4b | 1.00 | 1.00 | 1.00 | 0.20 | 0.80 |
| features-phi-4-mini | 1.00 | 0.33 | 1.00 | 0.50 | 0.74 |
| features-qwen3-4b | 1.00 | 1.00 | 1.00 | 0.20 | 0.80 |
| mlp-phi-4-mini | 1.00 | 0.67 | 1.00 | 0.80 | 0.88 |
| mlp-qwen3-4b | 1.00 | 1.00 | 1.00 | 0.20 | 0.80 |

Mean RRS: Qwen3-4B 0.75, Phi-4-mini 0.60. All eight artifacts ran for their author, and seven of
eight ran in every clean rerun. The two agents fail in different places. Qwen3-4B pinned every
dependency, seeded three of four scripts, and its numbers reproduced; but most of its claims could
not be checked. Phi-4-mini's claims were well formed, but it left `scikit-learn` unpinned in three
artifacts, did not seed its random forest, and broke one `requirements.txt`.

### E2. Does the score catch known defects?

All 22 expected component outcomes were observed (a component is "low" below 0.67). The
reproducible control scored 1.00; the absolute-path and undeclared-import controls scored 0.20 and
0.13; the unpinned control kept a high score (0.93) because nothing has yet broken, which is the
intended reading of "a missing pin is a risk, not yet a failure". The no-seed control's claims
component is 0 because a claim that the larger network is more accurate is false on its own run
(0.9800 vs 0.9822), as well as unstable across reruns; the over-claim control had two unsupported
claims, not one. Both are properties of the controls as written, recorded here rather than fixed
after the fact.

### E3. Why does reproduction fail?

21 of 24 agent reruns produced results. All three failures are `bootstrap-phi-4-mini`, whose
`requirements.txt` reads `numpy==2.5.4, pandas==3.0.6, scikit-learn==1.9.1` on one line; pip rejects
it in every clean environment. It ran for its author only because the author sandbox already had
those packages (D4): the defect is invisible until someone else runs the code.

Where numbers moved:

- `compare-phi-4-mini`: `RandomForestClassifier()` without a seed. Two identical containers gave
  0.9631 and 0.9543 against the author's 0.9596.
- `bootstrap-qwen3-4b`: a bootstrap without a seed. The interval's lower bound was −4.172 for the
  author and −4.210, −4.175 and −4.239 on reruns; the CI run is 1.6% away, just outside the
  tolerance, so the pattern reads "differs between machines" (D15). The cause in the code is the
  missing seed.

Claims: the agents made 37 claims; 15 cannot be evaluated and 6 of the remaining 22 are false on the
author's own results (D14). All 15 unevaluable claims are Qwen3-4B's: its claim text was right
("rf_accuracy_mean ≥ 0.95") but the structured value was a stray word or fragment (`Heavy`, `: 0`,
empty). Phi-4-mini's false claims include three in `bootstrap-phi-4-mini` that place the mean difference
above its own upper bound, below its lower bound, or equal to the lower bound.

**Reproducible is not correct.** `bootstrap-qwen3-4b` takes "alcohol" from column 3 of the wine
data, which is alcalinity of ash (alcohol is column 0). Its difference of −3.20 reproduces on every
run, and it answers a different question from the one asked; Phi-4-mini's +1.47 uses the right
column. The score measures whether research can be rerun, not whether it is right.

### E4. Does a second machine change anything?

13 of 14 artifacts agree between the first container and the CI runner. Beyond the unseeded
bootstrap, one systematic difference appeared: logistic regression on unscaled breast-cancer
features, which stops before converging (the warning is in every log), scored 0.9438 on the CI
runner against 0.9473 in the containers, two samples of 569, in both agents' `compare` artifacts.
That is within tolerance, but it is an environment difference that no pin or seed controls: the
same library versions on a different CPU take a different path through an unconverged optimiser.
The hand-written control, which scales its features, reproduced to every digit on both machines.

### E5. Do the weights matter?

Equal weights give the same ranking as the default (Spearman 1.00); dropping the environment
component gives 0.89 and weighting results only gives 0.88, which changes the top artifact. The
ranking of the worst artifacts is stable under every weighting.

## 3. What this means

- Running for the author says little: all eight artifacts did, and one of them could not even be
  installed by anyone else. A clean rerun is the minimum test.
- Pins and seeds are the difference between the two agents' reproducibility, and both are things
  the agent could have done when told only that someone would rerun its work.
- Structured claims expose a failure that prose would hide: an agent can get its numbers right and
  still state conclusions that cannot be checked.
- Even pinned, seeded code can move across machines when it relies on an unconverged optimiser.
- Reproducibility is necessary, not sufficient: one fully reproducible artifact analysed the wrong
  variable. Checking correctness needs a reference answer or a reviewer.

## 4. Threats to validity

- **Scale.** Eight agent artifacts from two small 4-bit models, one generation each. Counts, not
  rates; another sample from the same models could differ.
- **Harness.** The claim schema leaves the `right` field a free string; a schema that allowed only
  a number or a results key might have prevented Qwen3-4B's unevaluable claims. The agents were
  told the author's installed versions, which makes exact pins easy.
- **Problems** are small, fast and use bundled data, so download failures, long runs and GPU
  non-determinism are outside this study.
- **Machines.** Both are Linux x86-64 with Python 3.12 from the same base image family.
- **Correctness is out of scope.** The score has no reference answers; the wrong-column artifact
  above was found by reading the code.
- **Tolerance.** The 1% / 0.005 tolerance decides several verdicts (D15); E5 varies the weights,
  not the tolerance.

## 5. Reproducibility

`make experiments` recomputes E1–E5 from the committed artifacts and reruns, writing versioned
result directories with config, commit, dirty flag and input hashes, and renders the results file.
Regenerating the evidence needs the local models (`make setup-llm models generate`), Docker
(`make reruns`) and GitHub Actions (`make ci-rerun`, `make import-ci`). Fresh-clone results are in
[REVIEW.md](REVIEW.md).
