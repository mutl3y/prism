"""Architecture guardrails for scanner facade decomposition."""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCANNER_CORE_DIR = PROJECT_ROOT / "src" / "prism" / "scanner_core"
SCANNER_FACADE_PATH = PROJECT_ROOT / "src" / "prism" / "scanner.py"
SCANNER_PRIVATE_IMPORT_BOUNDARIES = (
    "prism.scanner_extract",
    "prism.scanner_readme",
    "prism.scanner_analysis",
    "prism.scanner_io",
    "prism.scanner_config",
)


def _iter_import_targets(module_path: Path) -> list[str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    targets: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
            continue

        if isinstance(node, ast.ImportFrom) and node.module is not None:
            module = node.module
            if node.level <= 0:
                targets.append(module)
                continue

            if module_path.stem == "__init__":
                base = "prism.scanner_core"
            else:
                base = f"prism.scanner_core.{module_path.stem}"

            base_parts = base.split(".")
            keep = max(0, len(base_parts) - node.level)
            prefix = ".".join(base_parts[:keep])
            targets.append(f"{prefix}.{module}" if prefix else module)

    return targets


def test_scanner_core_modules_do_not_import_scanner_facade() -> None:
    """Enforce one-way decomposition: scanner_core must not import prism.scanner."""
    offenders: list[str] = []

    for module_path in sorted(SCANNER_CORE_DIR.glob("*.py")):
        if module_path.name == "__init__.py":
            continue

        targets = _iter_import_targets(module_path)
        if any(
            target == "prism.scanner" or target.startswith("prism.scanner.")
            for target in targets
        ):
            offenders.append(module_path.name)

    assert (
        not offenders
    ), "scanner_core reverse-imports scanner facade; offenders: " + ", ".join(offenders)


def _iter_scanner_private_cross_package_imports(module_path: Path) -> list[str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    offenders: list[str] = []
    base = "prism.scanner"
    base_parts = base.split(".")

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue

        if node.level <= 0:
            resolved_module = node.module
        else:
            keep = max(0, len(base_parts) - node.level)
            prefix = ".".join(base_parts[:keep])
            resolved_module = f"{prefix}.{node.module}" if prefix else node.module

        if not any(
            resolved_module == boundary or resolved_module.startswith(f"{boundary}.")
            for boundary in SCANNER_PRIVATE_IMPORT_BOUNDARIES
        ):
            continue

        for alias in node.names:
            if alias.name.startswith("_"):
                offenders.append(f"{resolved_module}:{alias.name}")

    return offenders


def test_scanner_facade_uses_public_cross_package_imports_only() -> None:
    offenders = _iter_scanner_private_cross_package_imports(SCANNER_FACADE_PATH)
    assert (
        not offenders
    ), "scanner facade imports private cross-package names: " + ", ".join(offenders)
