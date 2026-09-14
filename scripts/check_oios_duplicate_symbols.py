#!/usr/bin/env python3
"""
scripts/check_oios_duplicate_symbols.py
==========================================
Pre-commit guard for oios/ — detects duplicate top-level class names defined
in different files under oios/.

WHY THIS EXISTS
----------------
The sibling platform (iios/) already suffered exactly this bug: two different
files each defined a class named `AIPolicyViolationError`, so an
`except AIPolicyViolationError` in one module silently failed to catch the
other module's instance (documented in AI_PLATFORM_ARCHITECTURE_AUDIT_V1.md,
since fixed via an explicit alias + identity test). oios/ is the subsystem
actually wired into live trading (orchestrator/master_orchestrator.py imports
it 26+ times) yet had zero equivalent automated protection against the same
class of bug. This script closes that gap.

Scope: class definitions only (the exact bug class that already occurred),
scanned via the standard library `ast` module — no new dependency required.
A class name is flagged only when it is defined at module top level in two
or more DIFFERENT files under oios/. Re-exports/aliases (e.g. `Foo = Bar`)
are not flagged — only genuine duplicate `class Foo:` definitions.

Usage:
    python scripts/check_oios_duplicate_symbols.py        # scans oios/
    python scripts/check_oios_duplicate_symbols.py --path other/dir

A pre-existing-duplicate baseline (scripts/oios_duplicate_symbols_baseline.json,
same convention as this repo's own .secrets.baseline for detect-secrets) lets
already-known, reviewed duplicates be accepted without blocking every future
commit, while still failing on any NEW duplicate class name introduced later.

Exit code: 0 = no new duplicates found, 1 = new duplicates found (pre-commit fails).
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set


def _iter_python_files(root: Path):
    for p in root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        yield p


def _top_level_class_names(path: Path) -> List[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return []
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def find_duplicate_class_names(root: Path) -> Dict[str, List[Path]]:
    """Return {class_name: [file1, file2, ...]} for names defined in >=2 files."""
    locations: Dict[str, List[Path]] = defaultdict(list)
    for path in _iter_python_files(root):
        for name in _top_level_class_names(path):
            locations[name].append(path)
    return {name: paths for name, paths in locations.items() if len(paths) > 1}


def _load_baseline(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return set()
    return set(data.get("accepted_duplicate_class_names", []))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", default="oios", help="Directory to scan (default: oios)")
    parser.add_argument(
        "--baseline",
        default="scripts/oios_duplicate_symbols_baseline.json",
        help="Path to the accepted-duplicates baseline file",
    )
    args = parser.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"[oios-duplicate-symbols] path not found, skipping: {root}")
        return 0

    duplicates = find_duplicate_class_names(root)
    baseline = _load_baseline(Path(args.baseline))
    new_duplicates = {name: paths for name, paths in duplicates.items() if name not in baseline}

    if not new_duplicates:
        if duplicates:
            print(
                f"[oios-duplicate-symbols] OK — {len(duplicates)} known duplicate(s) "
                f"already accepted in baseline, no NEW duplicates under {root}/"
            )
        else:
            print(f"[oios-duplicate-symbols] OK — no duplicate class names under {root}/")
        return 0

    print(f"[oios-duplicate-symbols] FAIL — NEW duplicate class name(s) found under {root}/:")
    for name, paths in sorted(new_duplicates.items()):
        print(f"  class {name} defined in:")
        for p in paths:
            print(f"    - {p}")
    print(
        "\nA class name defined in two different files means `except <Name>` or "
        "`isinstance(x, <Name>)` in one module can silently miss the other "
        "module's instances (this exact bug already occurred once in iios/ — "
        "see AI_PLATFORM_ARCHITECTURE_AUDIT_V1.md). Rename one of the classes, "
        "consolidate them with an explicit alias, or add it to "
        "scripts/oios_duplicate_symbols_baseline.json if reviewed and accepted."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
