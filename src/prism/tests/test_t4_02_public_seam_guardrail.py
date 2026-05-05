"""T4-02: Verify api.py does not import private scanner internals."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
API_PATH = REPO_ROOT / "src/prism/api.py"
SCANNER_PLUGINS_PATH = REPO_ROOT / "src/prism/scanner_plugins"

PRIVATE_SCANNER_PATTERNS = (
    re.compile(r"^from\s+prism\.scanner\s+import\s+_"),
    re.compile(r"^from\s+prism\.scanner\.\w+\s+import\s+_"),
    re.compile(r"^import\s+prism\.scanner\._"),
    re.compile(r"_run_scan_payload"),
)


def _iter_import_lines() -> list[str]:
    source = API_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                lines.append(f"from {module} import {alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                lines.append(f"import {alias.name}")
    return lines


def _iter_scanner_plugin_private_kernel_imports() -> list[str]:
    offenders: list[str] = []

    for module_path in sorted(SCANNER_PLUGINS_PATH.rglob("*.py")):
        if "tests" in module_path.parts:
            continue

        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        rel_path = module_path.relative_to(REPO_ROOT)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                if not module_name.startswith("prism.scanner_kernel"):
                    continue
                for alias in node.names:
                    if alias.name.startswith("_"):
                        offenders.append(
                            f"{rel_path}:{node.lineno}: from {module_name} import {alias.name}"
                        )
                continue

            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("prism.scanner_kernel._"):
                        offenders.append(
                            f"{rel_path}:{node.lineno}: import {alias.name}"
                        )

    return offenders


def test_api_has_no_private_scanner_imports() -> None:
    for line in _iter_import_lines():
        for pattern in PRIVATE_SCANNER_PATTERNS:
            assert not pattern.search(
                line
            ), f"api.py must not import private scanner internals: {line!r}"


def test_legacy_scanner_module_absent() -> None:
    legacy = REPO_ROOT / "src/prism/scanner.py"
    assert not legacy.exists(), (
        "Legacy prism.scanner god-module must remain retired; "
        "public surface lives in prism.api + prism.scanner_kernel."
    )


def test_run_scan_payload_symbol_absent() -> None:
    for path in (REPO_ROOT / "src/prism").rglob("*.py"):
        if "tests" in path.parts:
            continue
        content = path.read_text(encoding="utf-8")
        assert (
            "_run_scan_payload" not in content
        ), f"_run_scan_payload leaked back into {path}; keep it retired."


def test_scanner_plugins_avoid_private_scanner_kernel_imports() -> None:
    offenders = _iter_scanner_plugin_private_kernel_imports()
    assert not offenders, (
        "scanner_plugins modules must not import underscore-prefixed scanner_kernel symbols:\n"
        + "\n".join(offenders)
    )


@pytest.mark.parametrize(
    "entrypoint",
    ["run_scan", "scan_role", "scan_collection", "scan_repo"],
)
def test_public_api_entrypoints_exist(entrypoint: str) -> None:
    from prism import api

    fn = getattr(api, entrypoint, None)
    assert callable(fn), f"prism.api.{entrypoint} must be public callable"
