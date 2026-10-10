import { useCallback, useEffect, useRef, useState } from "react";

/* ---------- types mirrored from the API (src/reprobench/api.py) ---------- */
export interface Provenance {
  experiment: string;
  run_id: string;
  commit: string;
  dirty: boolean;
  created_at: string;
  runtime_seconds: number;
  cpus: number;
}

export type ComponentName = "code" | "environment" | "results" | "claims";
export const COMPONENTS: ComponentName[] = ["code", "environment", "results", "claims"];

export interface ArtifactRow {
  artifact: string;
  problem: string;
  agent: string;
  agent_label: string;
  kind: "agent" | "reference";
  defect: string | null;
  author_succeeded: boolean;
  executions: number;
  reruns: number;
  rrs: number;
  components: Record<ComponentName, number>;
}

export interface Evidence {
  rerun: string;
  file: string;
  detail: string;
  ok: boolean;
}

export interface ScoreDetail {
  artifact: string;
  rrs: number;
  reruns: string[];
  components: Record<
    ComponentName,
    { score: number; parts: Record<string, number>; evidence: Evidence[] }
  >;
}

export interface RerunMeta {
  rerun_id: string;
  mode: "container" | "venv";
  machine: string;
  started: string;
  build_exit: number | null;
  run_exit: number | null;
  run_seconds: number | null;
  total_seconds: number;
  python: string | null;
  platform: string | null;
  results_written: boolean;
  image?: string;
  image_digests?: string[];
}

export interface RerunRow {
  id: string;
  meta: RerunMeta;
  results: Record<string, unknown> | null;
  ran: boolean;
  category: string | null;
  err_tail: string;
}

export interface Claim {
  text: string;
  left: string;
  op: string;
  right: string;
  tolerance: number;
}

export interface Manifest {
  artifact: string;
  problem: string;
  agent: string;
  agent_label: string;
  seed: number;
  kind: "agent" | "reference";
  defect?: string;
  expect?: string;
  author_succeeded: boolean;
  executions: number;
  author_environment: { python: string; platform: string; packages: Record<string, string | null> };
  frozen_at: string;
  sha256: Record<string, string>;
}

export interface TranscriptStep {
  step: "code" | "claims";
  attempt: number | null;
  execution: { exit_code: number | null; seconds: number; problem: string; stdout: string; stderr: string } | null;
  seconds: number | null;
  completion_tokens: number | null;
}

export interface ArtifactDetail {
  manifest: Manifest;
  files: Record<string, string | null>;
  score: ScoreDetail;
  reruns: RerunRow[];
  transcript: TranscriptStep[];
  claims: { claim: Claim; checks: Record<string, { holds: boolean; detail: string }> }[];
}

export interface Problem {
  key: string;
  title: string;
  problem: string;
  results_keys: Record<string, string>;
}

export interface Meta {
  problems: Problem[];
  weights: Record<ComponentName, number>;
  tolerance: { absolute: number; relative: number };
}

export interface Table {
  id: string;
  caption: string;
  columns: { key: string; label: string; align: "l" | "r" }[];
  rows: Record<string, unknown>[];
}

export interface Summary {
  title: string;
  question: string;
  findings: string[];
  tables: Table[];
  notes: string[];
}

export interface ExperimentItem {
  name: string;
  status: "done" | "pending";
  title?: string;
  question?: string;
  findings?: string[];
  run_id?: string;
  commit?: string;
  dirty?: boolean;
  created_at?: string;
  runtime_seconds?: number;
}

export interface ExperimentDetail {
  summary: Summary;
  provenance: Provenance;
}

/* ---------- fetching ---------- */
export class ApiError extends Error {
  constructor(
    public url: string,
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

const cache = new Map<string, unknown>();

const TOKEN_KEY = "laboratory-token";

/** The access token for a server started with RABENCH_TOKEN, kept for this browser tab only. */
export function getToken(): string {
  try {
    return sessionStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
}

export function setToken(token: string): void {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable: the token is not remembered */
  }
  cache.clear();
}

function headers(): Record<string, string> {
  const t = getToken();
  return t ? { Accept: "application/json", Authorization: `Bearer ${t}` } : { Accept: "application/json" };
}

export async function getJson<T>(url: string): Promise<T> {
  if (cache.has(url)) return cache.get(url) as T;
  let res: Response;
  try {
    res = await fetch(url, { headers: headers() });
  } catch {
    throw new ApiError(url, 0, "The Laboratory API could not be reached.");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(url, res.status, detail);
  }
  const data = (await res.json()) as T;
  cache.set(url, data);
  return data;
}

export interface ApiState<T> {
  data: T | undefined;
  error: ApiError | undefined;
  loading: boolean;
  retry: () => void;
}

export function useApi<T>(url: string | null): ApiState<T> {
  const [data, setData] = useState<T | undefined>(undefined);
  const [error, setError] = useState<ApiError | undefined>(undefined);
  const [loading, setLoading] = useState<boolean>(url !== null);
  const [nonce, setNonce] = useState(0);
  const current = useRef(url);

  useEffect(() => {
    current.current = url;
    if (url === null) {
      setLoading(false);
      return;
    }
    let alive = true;
    setLoading(true);
    setError(undefined);
    getJson<T>(url)
      .then((d) => {
        if (alive && current.current === url) setData(d);
      })
      .catch((e: unknown) => {
        if (alive && current.current === url)
          setError(e instanceof ApiError ? e : new ApiError(url, 0, String(e)));
      })
      .finally(() => {
        if (alive && current.current === url) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [url, nonce]);

  const retry = useCallback(() => {
    if (url) cache.delete(url);
    setNonce((n) => n + 1);
  }, [url]);

  return { data, error, loading, retry };
}

export const api = {
  meta: "/api/problems",
  artifacts: "/api/artifacts",
  artifact: (id: string) => `/api/artifacts/${encodeURIComponent(id)}`,
  rerunFile: (id: string, rerun: string, file: string) =>
    `/api/artifacts/${encodeURIComponent(id)}/reruns/${encodeURIComponent(rerun)}/${encodeURIComponent(file)}`,
  experiments: "/api/experiments",
  experiment: (name: string) => `/api/experiments/${encodeURIComponent(name)}`,
};

/** Fetch a log file as text (not cached: logs can be long and are opened on demand). */
export async function getText(url: string): Promise<string> {
  let res: Response;
  try {
    res = await fetch(url, { headers: headers() });
  } catch {
    throw new ApiError(url, 0, "The Laboratory API could not be reached.");
  }
  if (!res.ok) throw new ApiError(url, res.status, res.statusText);
  return res.text();
}
