#!/usr/bin/env python3
"""Maintain the machine generated inventory inside INDEX.md.

The generator walks the Python source tree, inspects each module with ``ast`` and
produces a deterministic ``File | Lines | Symbols`` table together with a
detected entry-point list. It is inserted between the ``@@INVENTORY:START@@`` /
``@@INVENTORY:END@@`` markers so the curated prose in ``INDEX.md`` is never
overwritten.

Usage::

    python tools/gen_index.py [--check]

``--check`` exits non-zero if the generated section is stale (useful in CI).
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "INDEX.md"

# Directories scanned for the inventory (relative to ROOT).
SCAN = ["src", "tools", "tests"]
SKIP_SUFFIX = ("__pycache__",)
SKIP_NAMES = {"__pycache__"}

START_MARK = "<!-- @@INVENTORY:START@@ -->"
END_MARK = "<!-- @@INVENTORY:END@@ -->"


def _symbols(tree: ast.Module) -> list[str]:
    out: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.append(node.name)
        elif isinstance(node, ast.ClassDef):
            out.append(node.name)
    return out


def _class_methods(tree: ast.Module) -> list[str]:
    methods: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(f"{node.name}.{sub.name}")
    return methods


def _scan() -> list[dict]:
    files: list[dict] = []
    for base in SCAN:
        base_dir = ROOT / base
        if not base_dir.is_dir():
            continue
        for path in sorted(base_dir.rglob("*.py")):
            if any(part in SKIP_NAMES for part in path.parts):
                continue
            rel = path.relative_to(ROOT)
            try:
                source = path.read_text(encoding="utf-8")
            except OSError:
                continue
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            symbols = _symbols(tree)
            methods = _class_methods(tree)
            files.append({
                "path": str(rel),
                "lines": len(source.splitlines()),
                "symbols": symbols,
                "methods": methods,
                "entry": path.name in ("__main__.py", "app.py") or "main(" in source,
            })
    return files


def _entry_points() -> list[str]:
    entries: list[str] = []
    console = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r"ribbonfm\s*=\s*\"([^\"]+)\"", console)
    if m:
        entries.append(f"console script: ``ribbonfm`` -> ``{m.group(1)}``")
    entries.append("``python -m ribbonfm`` (via src/ribbonfm/__main__.py)")
    return entries


def _render(files: list[dict]) -> str:
    lines: list[str] = [
        "## Generated inventory (auto-updated)",
        "",
        "> Regenerate with `python tools/gen_index.py`. The table below is produced",
        "> mechanically so the curated narrative above never goes stale.",
        "",
        "| File | Lines | Symbols `defs`/`class` |",
        "| --- | ---: | --- |",
    ]
    for f in files:
        sym = ", ".join(f["symbols"]) or "—"
        lines.append(f"| `{f['path']}` | {f['lines']} | {sym} |")
    lines.append("")
    lines.append("### Entry points")
    for e in _entry_points():
        lines.append(f"- {e}")
    # Methods appendix.
    lines.append("")
    lines.append("### Notable methods")
    for f in files:
        if f["methods"]:
            lines.append(f"- `{f['path']}`: " + ", ".join(f["methods"]))
    lines.append("")
    return "\n".join(lines)


def build() -> str:
    return _render(_scan())


def update(check: bool = False) -> int:
    text = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
    new_block = f"{START_MARK}\n{build()}\n{END_MARK}"
    if START_MARK not in text:
        if not text.endswith("\n\n"):
            text = text.rstrip() + "\n\n"
        text += new_block + "\n"
    else:
        begin = text.index(START_MARK)
        end = text.index(END_MARK, begin) + len(END_MARK)
        text = text[:begin] + new_block + text[end:]
    if check:
        stale = text != (INDEX.read_text(encoding="utf-8") if INDEX.exists() else "")
        return 1 if stale else 0
    INDEX.write_text(text, encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="fail if the inventory is stale (CI mode)")
    args = parser.parse_args()
    return update(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
