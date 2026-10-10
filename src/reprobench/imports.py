"""Static scan of the third-party modules a script imports, and whether its requirements declare them."""

from __future__ import annotations

import ast
import re
import sys

# import name -> distribution name, for the packages whose names differ
DISTRIBUTION = {
    "sklearn": "scikit-learn",
    "PIL": "pillow",
    "yaml": "pyyaml",
    "cv2": "opencv-python",
    "skimage": "scikit-image",
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
}
REQ_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*(.*)$")


def canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def imported_modules(code: str) -> set[str] | None:
    """Top-level modules imported anywhere in ``code``; None if it does not parse."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            mods.add(node.module.split(".")[0])
    return mods


def third_party(mods: set[str]) -> set[str]:
    return {m for m in mods if m not in sys.stdlib_module_names and m != "__future__"}


def parse_requirements(text: str) -> list[dict[str, str | bool]]:
    """Each requirement line: name, specifier, and whether it pins an exact version (``==``)."""
    out: list[dict[str, str | bool]] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = REQ_RE.match(line)
        if not m:
            continue
        spec = m.group(3).strip()
        out.append({"name": canonical(m.group(1)), "spec": spec,
                    "pinned": bool(re.match(r"^==\s*[0-9][^,;*]*$", spec))})  # fmt: skip
    return out


def undeclared(code: str, requirements: str) -> list[str] | None:
    """Third-party modules imported but not declared (by distribution name); None if the code does not parse."""
    mods = imported_modules(code)
    if mods is None:
        return None
    declared = {str(r["name"]) for r in parse_requirements(requirements)}
    return sorted(m for m in third_party(mods) if canonical(DISTRIBUTION.get(m, m)) not in declared)
