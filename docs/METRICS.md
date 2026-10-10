# Metrics

All computed by `reprobench.scoring` from the frozen artifact and its rerun directories.
Tolerance for a reproduced value: |original − rerun| ≤ max(0.005, 0.01 × |original|).

| Component | Definition | Evidence |
|---|---|---|
| Code | share of reruns where `run.py` exits 0 **and** writes a `results.json` object | `meta.json` exit codes, `run.err` tail |
| Environment | mean of three parts: *build* (share of reruns whose `pip install -r requirements.txt` exits 0); *declared* (1 if every third-party module `run.py` imports is declared, else 0; 0 if `run.py` does not parse); *pinned* (share of requirement lines pinned with `==`; with no requirements, 1 only if `run.py` imports nothing third-party) | `build.log`, static scan of `run.py` and `requirements.txt` |
| Results | share of the author's numeric values reproduced within tolerance by **every** rerun; a failed or missing rerun reproduces nothing; 0 if the author produced no results or there are no reruns | original vs each rerun's `results.json` |
| Claims | share of claims that hold on the author's own results **and** on every rerun; 0 when no claims were stated | `claims.json` checked against each `results.json` |

**RRS** = 0.25 Code + 0.20 Environment + 0.30 Results + 0.25 Claims, in [0, 1].

Claims: `left` is a results key; `right` a key or a number; `≈` holds when |left − right| ≤
tolerance (a missing or non-positive tolerance makes `≈` fail); a key that is missing or not a
number makes the claim fail. Booleans are not numbers.

Failure taxonomy (per rerun that produced no results): `timeout` (exit 124), `install_failure`
(pip exit ≠ 0), `import_error` (ModuleNotFoundError/ImportError in `run.err`), `missing_file`
(FileNotFoundError), `no_results` (exit 0, no valid results), `runtime_error` (anything else).
Value patterns (per artifact): reproduced; non-deterministic (two identical containers disagree);
reruns agree with each other, not with the author; differs between machines.

E2 calls a component *low* when it is below 0.67 and *high* otherwise; expected outcomes are in
`references/*/expected.yaml`, written before the first rerun. E5 compares rankings with Spearman's ρ.

No confidence intervals are reported: there are 8 agent artifacts and 6 controls, and every
number is a count over them; the report states counts, not rates with error bars.
