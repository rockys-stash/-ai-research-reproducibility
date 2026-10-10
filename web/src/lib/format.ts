export const COMPONENT_LABEL: Record<string, string> = {
  code: "Code",
  environment: "Environment",
  results: "Results",
  claims: "Claims",
};

export const COMPONENT_HELP: Record<string, string> = {
  code: "Share of reruns where run.py exits 0 and writes results.json.",
  environment:
    "Mean of: the clean environment builds; every imported package is declared; every requirement is pinned.",
  results:
    "Share of the author's numbers that every rerun reproduces within tolerance.",
  claims:
    "Share of the author's claims that hold in the original and in every rerun.",
};

export const AGENT_LABEL: Record<string, string> = {
  "qwen3-4b": "Qwen3-4B",
  "phi-4-mini": "Phi-4-mini",
  reference: "Reference control",
};

export const CATEGORY_LABEL: Record<string, string> = {
  install_failure: "Environment did not build",
  import_error: "Import error",
  missing_file: "Missing file",
  timeout: "Timed out",
  runtime_error: "Runtime error",
  no_results: "No results written",
};

export const RERUN_LABEL: Record<string, string> = {
  "container-1": "Container 1",
  "container-2": "Container 2",
};

export function rerunLabel(id: string): string {
  if (RERUN_LABEL[id]) return RERUN_LABEL[id];
  if (id.startsWith("ci-")) return "CI runner";
  return id;
}

export function num(v: number | null | undefined, digits = 3): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  return v.toFixed(digits);
}

export function cell(v: unknown): string {
  if (v === null || v === undefined) return "–";
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (typeof v === "number") {
    if (Number.isInteger(v)) return v.toLocaleString("en");
    return Math.abs(v) < 100 ? v.toFixed(4) : v.toLocaleString("en", { maximumFractionDigits: 2 });
  }
  return String(v);
}

export function when(iso: string | null | undefined): string {
  if (!iso) return "–";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toISOString().slice(0, 16).replace("T", " ") + " UTC";
}

/** Same tolerance as the scorer: |a − b| ≤ max(abs, rel·|a|). */
export function close(a: number, b: number, abs: number, rel: number): boolean {
  return Math.abs(a - b) <= Math.max(abs, rel * Math.abs(a));
}
