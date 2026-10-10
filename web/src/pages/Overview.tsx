import { Link } from "react-router-dom";
import { DataTable } from "../components/DataTable";
import { ScoreBar } from "../components/ScoreBar";
import { Empty, ErrorOrPending, Loading, PageHead } from "../components/ui";
import {
  api,
  type ArtifactRow,
  COMPONENTS,
  type ExperimentItem,
  type Meta,
  useApi,
} from "../lib/api";
import { AGENT_LABEL, COMPONENT_LABEL } from "../lib/format";
import { artifactColumns } from "./Artifacts";

export function Overview() {
  const list = useApi<{ artifacts: ArtifactRow[] }>(api.artifacts);
  const meta = useApi<Meta>(api.meta);
  const exps = useApi<{ experiments: ExperimentItem[] }>(api.experiments);
  if ((list.loading && !list.data) || (meta.loading && !meta.data))
    return <Loading label="Loading overview" />;
  const err = list.error ?? meta.error;
  if (err)
    return (
      <>
        <PageHead title="Overview" />
        <ErrorOrPending
          error={err}
          retry={() => {
            list.retry();
            meta.retry();
          }}
          what="the overview"
          command="make reruns"
        />
      </>
    );
  if (!list.data || !meta.data) return null;
  const m = meta.data;
  const agent = list.data.artifacts.filter((a) => a.kind === "agent");
  const refs = list.data.artifacts.filter((a) => a.kind === "reference");
  const agents = [...new Set(agent.map((a) => a.agent))].sort();
  const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0);
  const e1 = exps.data?.experiments.find((e) => e.name === "e1_scores");
  return (
    <>
      <PageHead title="Overview">
        Local language-model agents were given four small research problems.
        What each agent left behind (code, requirements, results, claims) was
        frozen and rerun from scratch in clean containers and on a second
        machine. Every score below comes from those rerun logs.
      </PageHead>
      <section className="panel" aria-labelledby="formula">
        <div className="panel-head">
          <h2 id="formula">Research Reproducibility Score</h2>
        </div>
        <div className="panel-body">
          <p>
            RRS ={" "}
            {COMPONENTS.map((c, i) => (
              <span key={c}>
                {i > 0 && " + "}
                {m.weights[c]} × {COMPONENT_LABEL[c]}
              </span>
            ))}
            . A number is reproduced when |Δ| ≤ max({m.tolerance.absolute},{" "}
            {m.tolerance.relative * 100}% of the value). <Link to="/method">How each component is computed</Link>.
          </p>
        </div>
      </section>
      {agents.length > 0 && (
        <section className="panel" aria-labelledby="by-agent">
          <div className="panel-head">
            <h2 id="by-agent">By agent (mean over problems)</h2>
          </div>
          <div className="table-wrap" tabIndex={0} role="region" aria-label="Mean components by agent (table)">
            <table>
              <thead>
                <tr>
                  <th scope="col">Agent</th>
                  <th scope="col" className="num">Artifacts</th>
                  <th scope="col" className="num">Ran for author</th>
                  {COMPONENTS.map((c) => (
                    <th key={c} scope="col">{COMPONENT_LABEL[c]}</th>
                  ))}
                  <th scope="col" className="num">RRS</th>
                </tr>
              </thead>
              <tbody>
                {agents.map((a) => {
                  const rs = agent.filter((r) => r.agent === a);
                  return (
                    <tr key={a}>
                      <th scope="row">
                        <Link to={`/artifacts?agent=${a}`}>{AGENT_LABEL[a] ?? a}</Link>
                      </th>
                      <td className="num">{rs.length}</td>
                      <td className="num">{rs.filter((r) => r.author_succeeded).length}</td>
                      {COMPONENTS.map((c) => (
                        <td key={c}>
                          <ScoreBar value={mean(rs.map((r) => r.components[c]))} label={c} />
                        </td>
                      ))}
                      <td className="num">
                        <strong>{mean(rs.map((r) => r.rrs)).toFixed(2)}</strong>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}
      {e1?.status === "done" && e1.findings && (
        <section className="panel" aria-labelledby="findings">
          <div className="panel-head">
            <h2 id="findings">Findings (E1)</h2>
            <Link to="/experiments/e1_scores" className="small">All experiments →</Link>
          </div>
          <div className="panel-body">
            <ul className="findings">
              {e1.findings.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          </div>
        </section>
      )}
      <section className="panel" aria-labelledby="controls">
        <div className="panel-head">
          <h2 id="controls">Reference controls</h2>
          <span className="muted small">hand-written, each with one planted defect</span>
        </div>
        {refs.length === 0 ? (
          <Empty title="No controls frozen yet" />
        ) : (
          <DataTable
            caption="Reference controls with their components"
            columns={[
              {
                key: "defect",
                label: "Planted defect",
                wrap: true,
                render: (r: ArtifactRow) => (
                  <Link to={`/artifacts/${r.artifact}`}>{r.defect ?? "none"}</Link>
                ),
              },
              ...artifactColumns().slice(2),
            ]}
            rows={refs}
            rowKey={(r) => r.artifact}
          />
        )}
      </section>
      <section className="panel" aria-labelledby="problems">
        <div className="panel-head">
          <h2 id="problems">Research problems</h2>
        </div>
        <div className="panel-body stack">
          {m.problems.map((p) => (
            <div key={p.key}>
              <h3>{p.title}</h3>
              <p>{p.problem}</p>
              <p className="secondary small">
                results.json must contain: {Object.keys(p.results_keys).join(", ")}
              </p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
