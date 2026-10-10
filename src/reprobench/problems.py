"""Research problems given to the agents."""

from __future__ import annotations

from dataclasses import dataclass

import yaml

from reprobench.paths import PROBLEMS


@dataclass(frozen=True)
class Problem:
    key: str
    title: str
    problem: str
    results_keys: dict[str, str]

    def brief(self) -> str:
        keys = "\n".join(f'  "{k}": {v}' for k, v in self.results_keys.items())
        return (f"{self.problem}\n\nYour script must write a file results.json in the current directory containing "
                f"a flat JSON object with at least these numeric keys:\n{keys}")  # fmt: skip


def load(key: str) -> Problem:
    d = yaml.safe_load((PROBLEMS / f"{key}.yaml").read_text(encoding="utf-8"))
    return Problem(d["key"], d["title"], " ".join(str(d["problem"]).split()), dict(d["results_keys"]))


def all_keys() -> list[str]:
    return sorted(p.stem for p in PROBLEMS.glob("*.yaml"))
