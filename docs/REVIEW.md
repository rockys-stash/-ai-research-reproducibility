# Internal review board

Reviewed 2026-10-11 against [REPORT.md](REPORT.md), the experiment results it cites (all on a clean
commit) and the committed artifacts and rerun logs. **Overall: pass.**

| Reviewer | Verdict | Required fixes |
|---|---|---|
| Research | Pass | Fixed during review: E3 counted unevaluable claims as false (D14) |
| Engineering | Pass | Fixed during review: CI failed because the screenshot script did not exist yet |
| QA | Pass | None open |
| Security | Pass | None open |
| UX | Pass | None open |
| Release | Pass | None open |

## Research reviewer

- Every score traces to a log: rerun exit codes, pip output, `pip freeze`, stdout/stderr and the
  results each rerun wrote are committed for all 14 artifacts × 3 reruns, including the GitHub
  Actions rerun (run 38096564065), imported unchanged.
- The controls were specified before any rerun (`references/*/expected.yaml`) and all 22 expected
  outcomes were observed. The report states where the controls are imperfect (the no-seed control
  also over-claims; the over-claim control has two unsupported claims) instead of rewriting them.
- The review read the agents' code behind each verdict rather than relying on labels. That found
  the wrong-column bootstrap (reproducible, not correct), the comma-separated requirements line,
  the unconverged logistic regression behind the only cross-machine drift in seeded code, and that
  the "differs between machines" label on the unseeded bootstrap is a tolerance effect (D15).
- E3 originally reported 21 "false" agent claims; 15 of them cannot be evaluated at all. They are
  now separated (D14); the claims score is unchanged.
- Limits are stated: eight agent artifacts, two small local models, one generation each; correctness
  is not scored; the claim schema's free-text `right` field is a harness choice that may have
  invited Qwen3-4B's malformed claims.

## Engineering reviewer

- `make experiments` recomputes E1–E5 from committed evidence in about a second; results are
  versioned with config, commit, dirty flag and input hashes. Regenerating evidence is separate and
  documented (local models, Docker, GitHub Actions).
- The rerun script uses only the standard library, so the CI rerun needs no install of this package.
- ruff, ruff format, mypy (`src`, `tests`, `scripts`), ESLint and `tsc`.

## QA reviewer

- 20 unit, agent (scripted model), rerun and API tests and 21 browser tests pass, including a
  drill-down to a failed rerun and axe-core (WCAG 2.1 A/AA and best practice) on every page in both
  themes at desktop and mobile width.
- 27 screenshots from the running console on the committed evidence.
- **Fresh clone** (2026-10-11): a new clone of `d07a509` ran `make setup test lint experiments
  test-ui` and passed; `docs/generated/results.md` was identical to the committed file except the
  result-directory lines.

## Security reviewer

- Agent code runs only in a temporary directory with a timeout (author sandbox) or inside a
  container or fresh virtual environment (reruns); nothing an agent wrote is imported by this
  package.
- Read-only API, rate limited, security headers; `reprobench serve` refuses a non-loopback bind
  without `REPROBENCH_TOKEN`. No secrets are committed; the CI rerun workflow has read-only
  permissions.

## UX reviewer

- Every value the author reported is shown next to every rerun's value with a pass/fail mark and
  the difference; claims are shown both as the agent wrote them and as checked, so a mismatch such
  as "==" written but ">" structured is visible.

## Release reviewer

- README, PLAN, DESIGN, METRICS, DATASET, DECISIONS, REPORT and this review are present; the
  screenshots are real captures.
