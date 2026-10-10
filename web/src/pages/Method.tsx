import { ErrorOrPending, Loading, PageHead } from "../components/ui";
import { api, COMPONENTS, type Meta, useApi } from "../lib/api";
import { COMPONENT_HELP, COMPONENT_LABEL } from "../lib/format";

export function Method() {
  const meta = useApi<Meta>(api.meta);
  if (meta.loading && !meta.data) return <Loading label="Loading method" />;
  if (meta.error)
    return <ErrorOrPending error={meta.error} retry={meta.retry} what="the method" command="make serve" />;
  if (!meta.data) return null;
  const m = meta.data;
  return (
    <article className="stack prose">
      <PageHead title="Method">
        How artifacts are produced, rerun and scored.
      </PageHead>
      <section className="panel">
        <div className="panel-head">
          <h2>Producing an artifact</h2>
        </div>
        <div className="panel-body stack">
          <p>
            An agent (a local language model) reads a research problem and
            writes <code>requirements.txt</code> and <code>run.py</code>. Its
            script runs on the author's machine; on an error it sees the last
            lines of the error output and tries again, up to four executions.
            When the script writes the required results, the agent states its
            conclusions as structured claims and writes a README. The files
            are then frozen with their SHA-256.
          </p>
          <p>
            The agent is told which packages its machine has and that someone
            else will rerun its work. It is not told how to make work
            reproducible: seeds and pins are what is measured.
          </p>
        </div>
      </section>
      <section className="panel">
        <div className="panel-head">
          <h2>Rerunning it</h2>
        </div>
        <div className="panel-body stack">
          <p>
            Only <code>requirements.txt</code> and <code>run.py</code> are
            copied into an empty directory. Two reruns use a fresh{" "}
            <code>python:3.12-slim</code> container each, installing the
            requirements from PyPI; one runs on a GitHub Actions runner in a new
            virtual environment. Every rerun keeps its build log, installed
            versions, output, error output, exit codes and results.
          </p>
        </div>
      </section>
      <section className="panel">
        <div className="panel-head">
          <h2>Components and score</h2>
        </div>
        <div className="panel-body">
          <dl className="kv">
            {COMPONENTS.map((c) => (
              <div className="kv-pair" key={c}>
                <dt>
                  {COMPONENT_LABEL[c]} (weight {m.weights[c]})
                </dt>
                <dd>{COMPONENT_HELP[c]}</dd>
              </div>
            ))}
          </dl>
          <p className="secondary small">
            A number is reproduced when |Δ| ≤ max({m.tolerance.absolute},{" "}
            {m.tolerance.relative * 100}% of the author's value). A claim holds
            when it is true on the author's results and on every rerun's. The
            reference controls carry one planted defect each, so E2 shows
            whether each component falls when it should.
          </p>
        </div>
      </section>
    </article>
  );
}
