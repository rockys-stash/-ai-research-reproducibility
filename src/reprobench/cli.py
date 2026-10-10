"""Command line: generate artifacts, freeze references, rerun, score, run experiments, serve the console."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from reprobench.paths import ARTIFACTS, CONFIGS, RERUNS, RESULTS, ROOT

CONTAINER_RERUNS = ("container-1", "container-2")


def cmd_generate(args: argparse.Namespace) -> int:
    from reprobench import agent, problems
    from reprobench.llm import LocalModel

    keys = args.problems or problems.all_keys()
    for name in args.agents:
        model = LocalModel(name)
        for k in keys:
            aid = f"{k}-{name}-s{args.seed}"
            if (ARTIFACTS / aid / "manifest.json").exists():
                print(f"{aid}: frozen, skipped", flush=True)
                continue
            out = agent.generate(problems.load(k), model, args.seed, ARTIFACTS, aid)
            m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            print(f"{aid}: author ran={m['author_succeeded']} after {m['executions']} executions", flush=True)
    return 0


def cmd_references(args: argparse.Namespace) -> int:
    from reprobench import references

    for n in references.names():
        if (ARTIFACTS / f"ref-{n}" / "manifest.json").exists():
            print(f"ref-{n}: frozen, skipped")
            continue
        print(references.freeze(n), flush=True)
    return 0


def cmd_rerun(args: argparse.Namespace) -> int:
    """Container reruns (two per artifact) for every frozen artifact that lacks them."""
    from reprobench.rerun import rerun

    os.environ.setdefault("REPROBENCH_CA_BUNDLE", os.environ.get("SSL_CERT_FILE", ""))
    arts = sorted(p.parent.name for p in ARTIFACTS.glob("*/manifest.json") if not p.parent.name.startswith("dev-"))
    if args.only:
        arts = [a for a in arts if a in args.only]
    for a in arts:
        for rid in CONTAINER_RERUNS:
            out = RERUNS / a / rid
            if (out / "meta.json").exists():
                continue
            if out.exists():
                shutil.rmtree(out)
            m = rerun(ARTIFACTS / a, out, "container", rid, args.machine)
            print(f"{a}/{rid}: build {m['build_exit']} run {m['run_exit']} results {m['results_written']}", flush=True)
    return 0


def cmd_import_ci(args: argparse.Namespace) -> int:
    """Copy rerun directories downloaded from a CI run (``gh run download``) into reruns/."""
    src = Path(args.directory)
    n = 0
    for meta in sorted(src.rglob("meta.json")):
        d = meta.parent
        artifact, rid = d.parent.name, d.name
        if not (ARTIFACTS / artifact / "manifest.json").exists():
            continue
        dest = RERUNS / artifact / rid
        if dest.exists():
            print(f"{artifact}/{rid}: exists, skipped")
            continue
        shutil.copytree(d, dest)
        n += 1
    print(f"imported {n} reruns")
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    from reprobench import scoring

    arts = sorted(p.parent.name for p in ARTIFACTS.glob("*/manifest.json") if not p.parent.name.startswith("dev-"))
    for a in arts:
        s = scoring.score(a)
        comps = " ".join(f"{k} {c.score:.2f}" for k, c in s.components.items())
        print(f"{a:40s} RRS {s.rrs:.3f}  {comps}  ({len(s.reruns)} reruns)")
    return 0


def cmd_experiment(args: argparse.Namespace) -> int:
    from reprobench.experiments.common import load_config
    from reprobench.experiments.registry import EXPERIMENTS

    names = list(EXPERIMENTS) if args.name == "all" else [args.name]
    for n in names:
        cfg = load_config(Path(args.configs) / f"{n}.yaml")
        print(f"{n}: running", flush=True)
        print(EXPERIMENTS[n][1](cfg, Path(args.results)), flush=True)
    return 0


def cmd_results(args: argparse.Namespace) -> int:
    from reprobench.results_md import render

    out = ROOT / "docs" / "generated" / "results.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(RESULTS), encoding="utf-8")
    print(out)
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from reprobench.api import create_app

    token = os.environ.get("REPROBENCH_TOKEN", "")
    if args.host not in ("127.0.0.1", "localhost", "::1") and not token:
        raise SystemExit("refusing to bind a non-loopback address without REPROBENCH_TOKEN")
    uvicorn.run(create_app(token=token), host=args.host, port=args.port, log_level="info")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="reprobench", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("models", help="download the local language models and check their hashes")
    g = sub.add_parser("generate", help="run the agents on the problems and freeze their artifacts (skips frozen ones)")
    g.add_argument("--agents", nargs="+", default=["qwen3-4b", "phi-4-mini"])
    g.add_argument("--problems", nargs="*")
    g.add_argument("--seed", type=int, default=0)
    sub.add_parser("references", help="freeze the hand-written reference artifacts (controls)")
    r = sub.add_parser("rerun", help="rerun every frozen artifact twice in a fresh container (skips done reruns)")
    r.add_argument("--only", nargs="*")
    r.add_argument("--machine", default="")
    i = sub.add_parser("import-ci", help="import rerun directories downloaded from the CI reproduction workflow")
    i.add_argument("directory")
    sub.add_parser("score", help="print the RRS and components of every artifact")
    e = sub.add_parser("experiment", help="run an experiment")
    e.add_argument("name", choices=["e1", "e2", "e3", "e4", "e5", "all"])
    e.add_argument("--configs", default=str(CONFIGS / "experiments"))
    e.add_argument("--results", default=str(RESULTS))
    sub.add_parser("results", help="render docs/generated/results.md from results/*/LATEST")
    s = sub.add_parser("serve", help="serve the console and API")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    args = p.parse_args(argv)
    if args.cmd == "models":
        from reprobench.llm import fetch_models

        for f in fetch_models():
            print(f)
        return 0
    return {"generate": cmd_generate, "references": cmd_references, "rerun": cmd_rerun, "import-ci": cmd_import_ci,
            "score": cmd_score, "experiment": cmd_experiment, "results": cmd_results, "serve": cmd_serve}[args.cmd](args)  # fmt: skip


if __name__ == "__main__":
    raise SystemExit(main())
