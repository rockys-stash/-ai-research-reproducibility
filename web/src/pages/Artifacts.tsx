import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { type Column, DataTable } from "../components/DataTable";
import { ScoreBar } from "../components/ScoreBar";
import { Empty, ErrorOrPending, Loading, PageHead } from "../components/ui";
import { api, type ArtifactRow, COMPONENTS, useApi } from "../lib/api";
import { AGENT_LABEL, COMPONENT_HELP, COMPONENT_LABEL } from "../lib/format";

const FILTERS = ["kind", "agent", "problem"] as const;

export function artifactColumns(): Column<ArtifactRow>[] {
  return [
    {
      key: "artifact",
      label: "Artifact",
      render: (r) => (
        <Link to={`/artifacts/${r.artifact}`} className="mono">
          {r.artifact}
        </Link>
      ),
    },
    {
      key: "author",
      label: "Ran for author",
      render: (r) =>
        r.author_succeeded ? (
          <span className="ok">✓ yes ({r.executions})</span>
        ) : (
          <span className="bad">✗ no ({r.executions})</span>
        ),
      title: "Whether run.py worked on the author's machine, and after how many executions",
    },
    ...COMPONENTS.map((c) => ({
      key: c,
      label: COMPONENT_LABEL[c] ?? c,
      title: COMPONENT_HELP[c],
      render: (r: ArtifactRow) => <ScoreBar value={r.components[c]} label={c} />,
    })),
    {
      key: "rrs",
      label: "RRS",
      title: "Research Reproducibility Score (weighted)",
      render: (r) => <strong>{r.rrs.toFixed(2)}</strong>,
      align: "r",
    },
    { key: "reruns", label: "Reruns", align: "r", render: (r) => r.reruns },
  ];
}

export function Artifacts() {
  const list = useApi<{ artifacts: ArtifactRow[] }>(api.artifacts);
  const [params, setParams] = useSearchParams();
  const rows = useMemo(
    () =>
      (list.data?.artifacts ?? []).filter((r) =>
        FILTERS.every((f) => !params.get(f) || r[f] === params.get(f)),
      ),
    [list.data, params],
  );
  if (list.loading && !list.data) return <Loading label="Loading artifacts" />;
  if (list.error)
    return (
      <>
        <PageHead title="Artifacts" />
        <ErrorOrPending
          error={list.error}
          retry={list.retry}
          what="artifacts"
          command="make generate references reruns"
        />
      </>
    );
  if (!list.data) return null;
  const all = list.data.artifacts;
  const options = (f: (typeof FILTERS)[number]) =>
    [...new Set(all.map((r) => String(r[f])))].sort();
  return (
    <>
      <PageHead title="Artifacts">
        Every frozen piece of research: written by an agent, or a hand-written
        reference control with a known defect. Open one to compare what its
        author got with what the reruns got.
      </PageHead>
      <div className="filters" role="group" aria-label="Filter artifacts">
        {FILTERS.map((f) => (
          <label key={f} className="field">
            <span className="secondary">
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </span>
            <select
              value={params.get(f) ?? ""}
              onChange={(e) => {
                const next = new URLSearchParams(params);
                if (e.target.value) next.set(f, e.target.value);
                else next.delete(f);
                setParams(next, { replace: true });
              }}
            >
              <option value="">All</option>
              {options(f).map((o) => (
                <option key={o} value={o}>
                  {f === "agent" ? (AGENT_LABEL[o] ?? o) : o}
                </option>
              ))}
            </select>
          </label>
        ))}
        <span className="muted small" aria-live="polite">
          {rows.length} of {all.length} artifacts
        </span>
      </div>
      {all.length === 0 ? (
        <Empty title="No artifacts yet">
          <p>
            Status: pending. Run <code>make generate references</code>.
          </p>
        </Empty>
      ) : (
        <section className="panel">
          <DataTable
            caption="Artifacts with their reproducibility components"
            columns={artifactColumns()}
            rows={rows}
            rowKey={(r) => r.artifact}
          />
        </section>
      )}
    </>
  );
}
