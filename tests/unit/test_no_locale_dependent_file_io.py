"""Regression guard for a real Windows bug: `open()`/`Path.open()`/
`Path.read_text()`/`Path.write_text()` without an explicit `encoding=`
default to `locale.getpreferredencoding(False)`, which is `cp949` on
Korean-locale Windows — not `utf-8`. Every config/fixture/YAML file in this
repo contains non-ASCII characters (em dashes, section signs, Japanese/Korean
product names), so a locale-dependent text read reliably crashes with
`UnicodeDecodeError` on Windows while working fine on Linux/macOS (whose
default locale is usually UTF-8) — exactly the kind of bug that survives
Linux-only CI and breaks the first time a Windows user runs `scripts/seed.ps1`.

This test statically scans every first-party .py file (not third-party
dependencies) for text-mode file I/O missing an explicit `encoding=`
keyword, so a future call site can't reintroduce the same bug class.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SCAN_DIRS = ["packages", "apps/api", "apps/worker", "tests", "scripts"]
EXCLUDE_DIR_NAMES = {"node_modules", ".venv", "__pycache__", ".next"}

# Path.read_text()/write_text() are always text-mode: no "b" variant exists,
# so they must always carry an explicit encoding.
ALWAYS_TEXT_METHODS = {"read_text", "write_text"}
# open()/Path.open() are text-mode unless a binary mode string is passed.
MODE_AWARE_CALLS = {"open"}


def _iter_python_files():
    for rel_dir in SCAN_DIRS:
        base = REPO_ROOT / rel_dir
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if any(part in EXCLUDE_DIR_NAMES for part in path.parts):
                continue
            yield path


def _call_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _has_binary_mode(node: ast.Call) -> bool:
    # Positional mode arg: open(path, "rb"), path.open("wb")
    for arg in node.args[1:]:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and "b" in arg.value:
            return True
    # Keyword mode arg: open(path, mode="rb")
    for kw in node.keywords:
        if (
            kw.arg == "mode"
            and isinstance(kw.value, ast.Constant)
            and isinstance(kw.value.value, str)
        ):
            if "b" in kw.value.value:
                return True
    return False


def _has_encoding_kwarg(node: ast.Call) -> bool:
    return any(kw.arg == "encoding" for kw in node.keywords) or any(
        kw.arg is None for kw in node.keywords
    )


def _find_violations(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name in ALWAYS_TEXT_METHODS:
            if not _has_encoding_kwarg(node):
                violations.append(
                    f"{path.relative_to(REPO_ROOT)}:{node.lineno}: {name}() missing encoding="
                )
        elif name in MODE_AWARE_CALLS:
            if _has_binary_mode(node):
                continue
            if not _has_encoding_kwarg(node):
                violations.append(
                    f"{path.relative_to(REPO_ROOT)}:{node.lineno}: {name}() missing encoding="
                )
    return violations


def test_no_locale_dependent_text_file_io():
    all_violations = []
    for path in _iter_python_files():
        all_violations.extend(_find_violations(path))
    assert not all_violations, (
        "Text-mode file I/O without an explicit encoding= found (breaks on "
        "non-UTF-8-locale Windows — see this test's module docstring):\n"
        + "\n".join(all_violations)
    )
