import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ErrorOrPending, Loading, PageHead, PassMark, Segmented } from "../components/ui";
import {
  api,
  type ArtifactDetail,
  COMPONENTS,
  getText,
  type Meta,
  type RerunRow,
  useApi,
} from "../lib/api";
import {
  AGENT_LABEL,
  CATEGORY_LABEL,
  COMPONENT_HELP,
  COMPONENT_LABEL,
  cell,
  close,
  rerunLabel,
  when,
} from "../lib/format";

export function Artifact() {
  const { id = "" } = useParams();
  const d = useApi<ArtifactDetail>(api.artifact(id));
  const meta = useApi<Meta>(api.meta);
  if ((d.loading && !d.data) || (meta.loading && !meta.data))
    return <Loading label={`Loading ${id}`} />;
  const err = d.error ?? meta.error;
  if (err)
    return (
      <>
        <PageHead title={id} />
        <ErrorOrPending
          error={err}
          retry={() => {
            d.retry();
            meta.retry();
          }}
          what={`artifact ${id}`}
          command="make reruns"
        />
      </>
    );
  if (!d.data || !meta.data) return null;
  const { manifest: m, score, reruns } = d.data;
  const problem = meta.data.problems.find((p) => p.key === m.problem);
  return (
    <>
      <p className="small">
        <Link to="/artifacts">← All artifacts</Link>
      </p>
      <PageHead title={m.artifact}>{problem?.problem}</PageHead>
      <dl className="stat-row">
        <Stat k="Author" v={AGENT_LABEL[m.agent] ?? m.agent_label} />
        <Stat k="Problem" v={problem?.title ?? m.problem} />
        <Stat
          k="Ran for its author"
          v={`${m.author_succeeded ? "yes" : "no"} (${m.executions} execution${m.executions === 1 ? "" : "s"})`}
        />
        <Stat k="Independent reruns" v={String(reruns.length)} />
        <Stat k="RRS" v={score.rrs.toFixed(2)} />
        <Stat k="Frozen" v={when(m.frozen_at)} />
      </dl>
      {m.kind === "reference" && (
        <p className="secondary">
          <strong>Reference control.</strong> Planted defect: {m.defect}. Expected: {m.expect}.
        </p>
      )}

      <section aria-labelledby="components-head" className="stack">
        <h2 id="components-head" className="sr-only">
          Components
        </h2>
        <div className="cards">
          {COMPONENTS.map((c) => {
            const comp = score.components[c];
            return (
              <article key={c} className="card" aria-labelledby={`c-${c}`}>
                <h3 id={`c-${c}`}>{COMPONENT_LABEL[c]}</h3>
                <div className="big">{comp.score.toFixed(2)}</div>
                <p className="muted small">{COMPONENT_HELP[c]}</p>
                {Object.keys(comp.parts).length > 0 && (
                  <p className="small">
                    {Object.entries(comp.parts)
                      .map(([k, v]) => `${k} ${v.toFixed(2)}`)
                      .join(" · ")}
                  </p>
                )}
                <details>
                  <summary className="small">Evidence ({comp.evidence.length})</summary>
                  <ul className="evidence">
                    {comp.evidence.map((e, i) => (
                      <li key={i}>
                        <PassMark passed={e.ok} />{" "}
                        <span className="mono">
                          {e.rerun === "artifact" || e.rerun === "original"
                            ? e.rerun
                            : rerunLabel(e.rerun)}
                          /{e.file}
                        </span>
                        : {e.detail}
                      </li>
                    ))}
                  </ul>
                </details>
              </article>
            );
          })}
        </div>
      </section>

      <Comparison detail={d.data} tol={meta.data.tolerance} />
      <Claims detail={d.data} />
      <Reruns id={m.artifact} reruns={reruns} />
      <Files detail={d.data} />
      <Transcript detail={d.data} />
    </>
  );
}

function Stat({ k, v }: { k: string; v: string }) {
  return (
    <div className="stat">
      <dt className="muted small">{k}</dt>
      <dd>
        <strong>{v}</strong>
      </dd>
    </div>
  );
}

function asNum(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function Comparison({
  detail,
  tol,
}: {
  detail: ArtifactDetail;
  tol: { absolute: number; relative: number };
}) {
  let original: Record<string, unknown> = {};
  try {
    original = JSON.parse(detail.files["results.json"] ?? "{}") as Record<string, unknown>;
  } catch {
    original = {};
  }
  const keys = [
    ...new Set([
      ...Object.keys(original),
      ...detail.reruns.flatMap((r) => Object.keys(r.results ?? {})),
    ]),
  ].sort();
  return (
    <section className="panel" aria-labelledby="cmp-head">
      <div className="panel-head">
        <h2 id="cmp-head">Generated vs reproduced</h2>
        <span className="muted small">
          ✓ within max({tol.absolute}, {tol.relative * 100}% of the author's value)
        </span>
      </div>
      {keys.length === 0 ? (
        <p className="panel-body secondary">Neither the author nor any rerun produced results.</p>
      ) : (
        <div className="table-wrap" tabIndex={0} role="region" aria-label="Author's values and rerun values (table)">
          <table>
            <thead>
              <tr>
                <th scope="col">Result</th>
                <th scope="col" className="num">
                  Author
                </th>
                {detail.reruns.map((r) => (
                  <th key={r.id} scope="col" className="num">
                    {rerunLabel(r.id)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => {
                const a = asNum(original[k]);
                return (
                  <tr key={k}>
                    <th scope="row" className="mono small">
                      {k}
                    </th>
                    <td className="num">{cell(original[k])}</td>
                    {detail.reruns.map((r) => {
                      const v = asNum(r.results?.[k]);
                      if (!r.ran)
                        return (
                          <td key={r.id} className="num bad">
                            ✗ did not run
                          </td>
                        );
                      if (v === null)
                        return (
                          <td key={r.id} className="num bad">
                            ✗ missing
                          </td>
                        );
                      const same = a !== null && close(a, v, tol.absolute, tol.relative);
                      return (
                        <td key={r.id} className={`num ${same ? "ok" : "bad"}`}>
                          {same ? "✓" : "✗"} {cell(v)}
                          {a !== null && !same && (
                            <span className="muted small"> (Δ {(v - a).toFixed(4)})</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function Claims({ detail }: { detail: ArtifactDetail }) {
  const cols = ["original", ...detail.reruns.map((r) => r.id)];
  return (
    <section className="panel" aria-labelledby="claims-head">
      <div className="panel-head">
        <h2 id="claims-head">Claims, checked against every run</h2>
      </div>
      {detail.claims.length === 0 ? (
        <p className="panel-body secondary">The author stated no claims.</p>
      ) : (
        <div className="table-wrap" tabIndex={0} role="region" aria-label="Claims checked against each run (table)">
          <table>
            <thead>
              <tr>
                <th scope="col">Claim</th>
                <th scope="col">As checked</th>
                {cols.map((c) => (
                  <th key={c} scope="col">
                    {c === "original" ? "Author" : rerunLabel(c)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {detail.claims.map((c, i) => (
                <tr key={i}>
                  <td className="wrap">{c.claim.text}</td>
                  <td className="mono small">
                    {c.claim.left} {c.claim.op} {c.claim.right}
                    {c.claim.op === "≈" ? ` ± ${c.claim.tolerance}` : ""}
                  </td>
                  {cols.map((k) => {
                    const x = c.checks[k];
                    return (
                      <td key={k} title={x?.detail}>
                        {x ? <PassMark passed={x.holds} /> : "–"}
                        {x && !x.holds && <div className="muted small wrap">{x.detail}</div>}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

const LOGS = ["build.log", "run.err", "run.out", "freeze.txt", "meta.json"];

function Reruns({ id, reruns }: { id: string; reruns: RerunRow[] }) {
  const [open, setOpen] = useState<{ rerun: string; file: string; text: string } | null>(null);
  const [error, setError] = useState("");
  async function show(rerun: string, file: string) {
    setError("");
    try {
      setOpen({ rerun, file, text: await getText(api.rerunFile(id, rerun, file)) });
    } catch {
      setError(`${file} was not written by this rerun.`);
      setOpen(null);
    }
  }
  return (
    <section className="panel" aria-labelledby="reruns-head">
      <div className="panel-head">
        <h2 id="reruns-head">Reruns</h2>
      </div>
      {reruns.length === 0 ? (
        <p className="panel-body secondary">Status: pending. No rerun yet (make reruns).</p>
      ) : (
        <div className="panel-body stack">
          <div className="table-wrap" tabIndex={0} role="region" aria-label="Reruns (table)">
            <table>
              <thead>
                <tr>
                  <th scope="col">Rerun</th>
                  <th scope="col">Where</th>
                  <th scope="col">Python</th>
                  <th scope="col">Environment</th>
                  <th scope="col">run.py</th>
                  <th scope="col" className="num">
                    Seconds
                  </th>
                  <th scope="col">Logs</th>
                </tr>
              </thead>
              <tbody>
                {reruns.map((r) => (
                  <tr key={r.id}>
                    <th scope="row">{rerunLabel(r.id)}</th>
                    <td className="wrap small">
                      {r.meta.mode === "container" ? "clean container" : "fresh venv"} · {r.meta.machine}
                    </td>
                    <td>{r.meta.python ?? "–"}</td>
                    <td>
                      <PassMark passed={r.meta.build_exit === 0} />
                    </td>
                    <td className="wrap">
                      {r.ran ? (
                        <span className="ok">✓ ran</span>
                      ) : (
                        <>
                          <span className="bad">
                            ✗ {CATEGORY_LABEL[r.category ?? ""] ?? r.category ?? "failed"}
                          </span>
                          {r.err_tail && (
                            <span className="block mono small secondary wrap">
                              {r.err_tail.split(" / ").slice(-1)[0]}
                            </span>
                          )}
                        </>
                      )}
                    </td>
                    <td className="num">{r.meta.run_seconds ?? "–"}</td>
                    <td>
                      <span className="chips">
                        {LOGS.map((f) => (
                          <button
                            key={f}
                            type="button"
                            className="btn ghost small"
                            aria-pressed={open?.rerun === r.id && open.file === f}
                            onClick={() => void show(r.id, f)}
                          >
                            {f}
                          </button>
                        ))}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {error && (
            <p className="bad" role="status">
              {error}
            </p>
          )}
          {open && (
            <figure className="stack-sm" style={{ margin: 0 }}>
              <figcaption className="small">
                <span className="mono">
                  reruns/{id}/{open.rerun}/{open.file}
                </span>
              </figcaption>
              <pre className="code log" tabIndex={0}>
                {open.text || "(empty)"}
              </pre>
            </figure>
          )}
        </div>
      )}
    </section>
  );
}

const FILES = ["run.py", "requirements.txt", "claims.json", "results.json", "README.md"];

function Files({ detail }: { detail: ArtifactDetail }) {
  const [file, setFile] = useState("run.py");
  return (
    <section className="panel" aria-labelledby="files-head">
      <div className="panel-head">
        <h2 id="files-head">What the author left</h2>
        <Segmented
          label="File"
          options={FILES.map((f) => ({ id: f, label: f }))}
          value={file}
          onChange={setFile}
        />
      </div>
      <div className="panel-body">
        <pre className="code" tabIndex={0} aria-label={file}>
          {detail.files[file] ?? "(not written)"}
        </pre>
        <p className="muted small">
          SHA-256 {detail.manifest.sha256[file]?.slice(0, 16)}… (frozen{" "}
          {when(detail.manifest.frozen_at)}). Author's machine: Python{" "}
          {detail.manifest.author_environment.python},{" "}
          {Object.entries(detail.manifest.author_environment.packages)
            .map(([k, v]) => `${k} ${v ?? "–"}`)
            .join(", ")}
          .
        </p>
      </div>
    </section>
  );
}

function Transcript({ detail }: { detail: ArtifactDetail }) {
  const steps = detail.transcript.filter((t) => t.step === "code");
  if (steps.length === 0) return null;
  return (
    <section className="panel" aria-labelledby="tr-head">
      <div className="panel-head">
        <h2 id="tr-head">How the agent got there</h2>
        <span className="muted small">each execution on the author's machine</span>
      </div>
      <div className="panel-body">
        <ol className="timeline">
          {steps.map((t) => (
            <li key={t.attempt}>
              <div>
                <strong>Execution {t.attempt}</strong> ·{" "}
                {t.execution?.problem ? (
                  <span className="bad">✗ {t.execution.problem}</span>
                ) : (
                  <span className="ok">✓ ran and wrote the required results</span>
                )}
              </div>
              <div className="muted small">
                writing the code took {t.seconds?.toFixed(0) ?? "–"} s ({t.completion_tokens ?? "–"} tokens);
                running it {t.execution?.seconds ?? "–"} s
              </div>
              {t.execution?.stderr && t.execution.problem && (
                <pre className="code log small" tabIndex={0}>
                  {t.execution.stderr.split("\n").slice(-8).join("\n")}
                </pre>
              )}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
