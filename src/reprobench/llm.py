"""Local open-weights language models through llama.cpp, used as research agents.

Models are GGUF files pinned by SHA-256 (``configs/models.yaml``). Assistant replies are JSON
constrained by a schema grammar, so a reply always parses and the scorers judge content, not
formatting. Sampling uses an explicit seed per call.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import urllib.request
from pathlib import Path
from typing import Any, cast

import yaml

from reprobench.paths import CONFIGS, MODELS


def config() -> dict[str, Any]:
    return dict(yaml.safe_load((CONFIGS / "models.yaml").read_text(encoding="utf-8")))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_models(names: list[str] | None = None) -> list[Path]:
    cfg = config()
    MODELS.mkdir(exist_ok=True)
    out = []
    for name in names or list(cfg["models"]):
        m = cfg["models"][name]
        path = MODELS / m["file"]
        shared = Path(os.environ.get("REPROBENCH_MODEL_DIR", "/nonexistent")) / m["file"]
        if not path.exists() and shared.exists():
            path.symlink_to(shared)
        if not path.exists():
            tmp = path.with_suffix(".part")
            with urllib.request.urlopen(m["url"], timeout=120) as r, tmp.open("wb") as f:
                shutil.copyfileobj(r, f)
            tmp.replace(path)
        if sha256(path) != m["sha256"]:
            raise ValueError(f"{path.name}: checksum does not match configs/models.yaml; delete it and retry")
        out.append(path)
    return out


class LocalModel:
    def __init__(self, name: str) -> None:
        from llama_cpp import Llama

        cfg = config()
        m = cfg["models"][name]
        path = MODELS / m["file"]
        if not path.exists():
            raise FileNotFoundError(f"{path} is missing: run `make models`")
        self.name, self.label, self.sha256 = name, m["label"], m["sha256"]
        self.threads = int(os.environ.get("REPROBENCH_LLM_THREADS", cfg["threads"]))
        self.llm = Llama(model_path=str(path), n_ctx=cfg["n_ctx"], n_threads=self.threads,
                         n_threads_batch=self.threads, verbose=False, seed=0)  # fmt: skip
        self.calls: list[dict[str, Any]] = []

    def json(self, system: str, user: str, schema: dict[str, Any], seed: int, max_tokens: int = 700,
             temperature: float = 0.3) -> dict[str, Any]:  # fmt: skip
        """One schema-constrained reply; the prompt, reply and timing are kept in ``calls``."""
        t0 = time.perf_counter()
        self.llm.set_seed(seed)
        out = self.llm.create_chat_completion(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object", "schema": schema},
            temperature=temperature, top_p=0.95, top_k=40, seed=seed, max_tokens=max_tokens,
        )  # fmt: skip
        res = cast(dict[str, Any], out)
        text = str(res["choices"][0]["message"]["content"] or "")
        usage = res.get("usage", {})
        try:
            parsed = json.loads(text)
            error = ""
        except json.JSONDecodeError as e:  # truncated by max_tokens
            parsed, error = {}, f"reply is not complete JSON: {e}"
        self.calls.append({"system": system, "user": user, "reply": text, "seed": seed, "error": error,
                           "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
                           "seconds": round(time.perf_counter() - t0, 2)})  # fmt: skip
        return parsed if isinstance(parsed, dict) else {}
