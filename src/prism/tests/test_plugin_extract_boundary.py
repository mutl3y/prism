"""Guardrail test: prevent scanner_plugins from importing scanner_extract.

This test enforces the architectural boundary that scanner_plugins must NOT
directly import from scanner_extract. Platform-specific extraction logic
should live within each plugin package (e.g., ansible/extract_utils.py).

This boundary is critical for multi-platform expansion (Kubernetes, Terraform)
to ensure each platform implements its own extraction logic appropriate to its
file structures and concepts, rather than coupling to Ansible-specific utilities.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCANNER_PLUGINS_DIR = PROJECT_ROOT / "src" / "prism" / "scanner_plugins"
ALLOWED_BRIDGE_FILE = Path("ansible") / "extract_utils.py"
EXPECTED_EXTRACT_UTILS_CALLERS = {
    Path("ansible") / "feature_detection.py",
    Path("ansible") / "variable_discovery.py",
    Path("ansible") / "readme_renderer.py",
    Path("audit") / "dynamic_include_audit.py",
}


def _extract_imports_from_file(file_path: Path) -> list[str]:
    """Extract all import statements from a Python file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
    except (OSError, SyntaxError):
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _find_scanner_extract_imports(file_path: Path) -> list[str]:
    """Find all imports from scanner_extract in a file."""
    imports = _extract_imports_from_file(file_path)
    violations = [
        imp
        for imp in imports
        if imp.startswith("prism.scanner_extract") or imp == "scanner_extract"
    ]
    return violations


def test_scanner_plugins_must_not_import_scanner_extract():
    """Prevent scanner_plugins from importing scanner_extract directly.

    Rationale:
    - scanner_extract contains Ansible-specific traversal logic
    - Each platform plugin (Kubernetes, Terraform) should implement its own
      extraction logic appropriate to its platform's file structure
    - Direct imports create tight coupling and prevent generalization

    Exception:
    - ansible/extract_utils.py is ALLOWED to import from scanner_extract
      as a transitional bridge layer during migration. This exception
      should be removed once scanner_extract is fully refactored.
    """
    violations: dict[str, list[str]] = {}

    for py_file in SCANNER_PLUGINS_DIR.rglob("*.py"):
        # Skip __pycache__ and similar
        if "__pycache__" in py_file.parts:
            continue

        # Allow ansible/extract_utils.py as transitional bridge
        relative_path = py_file.relative_to(SCANNER_PLUGINS_DIR)
        if relative_path == ALLOWED_BRIDGE_FILE:
            continue

        # Check for violations
        bad_imports = _find_scanner_extract_imports(py_file)
        if bad_imports:
            violations[str(py_file.relative_to(PROJECT_ROOT))] = bad_imports

    if violations:
        msg = "\n\nscanner_plugins must NOT import from scanner_extract.\n"
        msg += "Each platform plugin should implement its own extraction logic.\n\n"
        msg += "Violations found:\n"
        for file_path, imports in sorted(violations.items()):
            msg += f"\n  {file_path}:\n"
            for imp in imports:
                msg += f"    - {imp}\n"
        msg += "\nMove platform-specific extraction logic into the plugin package.\n"
        msg += "See scanner_plugins/ansible/extract_utils.py for pattern.\n"
        pytest.fail(msg)


def test_scanner_plugins_limit_scanner_extract_bridge_to_extract_utils() -> None:
    bridge_files: dict[str, list[str]] = {}

    for py_file in SCANNER_PLUGINS_DIR.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        bad_imports = _find_scanner_extract_imports(py_file)
        if bad_imports:
            relative_path = py_file.relative_to(SCANNER_PLUGINS_DIR)
            bridge_files[str(relative_path)] = bad_imports

    assert set(bridge_files) == {str(ALLOWED_BRIDGE_FILE)}, (
        "scanner_plugins must keep scanner_extract imports isolated to "
        f"{ALLOWED_BRIDGE_FILE}; found {sorted(bridge_files)}"
    )


def test_ansible_plugin_callsites_use_extract_utils_seam() -> None:
    offenders: dict[str, list[str]] = {}
    missing_extract_utils_imports: list[str] = []

    for relative_path in sorted(EXPECTED_EXTRACT_UTILS_CALLERS):
        file_path = SCANNER_PLUGINS_DIR / relative_path
        imports = _extract_imports_from_file(file_path)
        extract_utils_imports = [
            imp
            for imp in imports
            if imp == "prism.scanner_plugins.ansible.extract_utils"
            or imp.startswith("prism.scanner_plugins.ansible.extract_utils.")
        ]
        scanner_extract_imports = [
            imp
            for imp in imports
            if imp == "prism.scanner_extract"
            or imp.startswith("prism.scanner_extract.")
        ]

        if not extract_utils_imports:
            missing_extract_utils_imports.append(str(relative_path))
        if scanner_extract_imports:
            offenders[str(relative_path)] = scanner_extract_imports

    assert not missing_extract_utils_imports, (
        "Expected plugin callsites to import the plugin-owned Ansible extract seam: "
        + ", ".join(sorted(missing_extract_utils_imports))
    )
    assert not offenders, (
        "Ansible plugin callsites must not import scanner_extract directly: "
        + ", ".join(
            f"{path} -> {imports}" for path, imports in sorted(offenders.items())
        )
    )
