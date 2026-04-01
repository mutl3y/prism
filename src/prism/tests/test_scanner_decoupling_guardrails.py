"""Guardrails that prevent migrated tests from re-coupling to scanner private helpers."""

from __future__ import annotations

import ast
import json
from pathlib import Path

_SCANNER_DOMAIN_PREFIXES = (
    "prism.scanner_extract",
    "prism.scanner_readme",
    "prism.scanner_analysis",
    "prism.scanner_io",
    "prism.scanner_config",
    "prism.scanner_core",
)

_FORBIDDEN_PRIVATE_HELPERS_BY_DOMAIN: dict[str, set[str]] = {
    "prism.scanner_readme": {
        "_render_guide_identity_sections",
        "_render_guide_section_body",
        "_extract_readme_variable_names_from_line",
    },
    "prism.scanner_extract": {
        "_split_task_annotation_label",
        "_task_anchor",
    },
    "prism.scanner_analysis": {
        "_extract_scanner_counters",
    },
}


def _iter_test_modules(tests_root: Path) -> list[Path]:
    return sorted(path for path in tests_root.glob("test_*.py") if path.is_file())


def _normalize_domain(module_name: str) -> str | None:
    for domain_prefix in _SCANNER_DOMAIN_PREFIXES:
        if module_name == domain_prefix or module_name.startswith(f"{domain_prefix}."):
            return domain_prefix
    return None


def _collect_imported_scanner_domains(tree: ast.AST) -> set[str]:
    imported_domains: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                domain = _normalize_domain(alias.name)
                if domain:
                    imported_domains.add(domain)
        if isinstance(node, ast.ImportFrom) and node.module:
            domain = _normalize_domain(node.module)
            if domain:
                imported_domains.add(domain)
    return imported_domains


def _collect_scanner_private_helper_refs(tree: ast.AST) -> list[tuple[str, int, int]]:
    scanner_aliases: set[str] = set()
    private_refs: list[tuple[str, int, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "prism.scanner":
                    scanner_aliases.add(alias.asname or "scanner")
        if isinstance(node, ast.ImportFrom):
            if node.module == "prism":
                for alias in node.names:
                    if alias.name == "scanner":
                        scanner_aliases.add(alias.asname or alias.name)
            if node.module == "prism.scanner":
                for alias in node.names:
                    if alias.name.startswith("_"):
                        private_refs.append(
                            (alias.name, node.lineno, node.col_offset + 1)
                        )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        if not node.attr.startswith("_"):
            continue
        if not isinstance(node.value, ast.Name):
            continue
        if node.value.id not in scanner_aliases:
            continue
        private_refs.append((node.attr, node.lineno, node.col_offset + 1))

    return private_refs


def test_scanner_domain_tests_do_not_rely_on_migrated_private_facade_helpers() -> None:
    tests_root = Path(__file__).resolve().parent
    offenders: list[dict[str, object]] = []

    for module_path in _iter_test_modules(tests_root):
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        imported_domains = _collect_imported_scanner_domains(tree)
        if not imported_domains:
            continue

        private_refs = _collect_scanner_private_helper_refs(tree)
        if not private_refs:
            continue

        for helper_name, line, col in private_refs:
            for domain in sorted(imported_domains):
                forbidden = _FORBIDDEN_PRIVATE_HELPERS_BY_DOMAIN.get(domain, set())
                if helper_name not in forbidden:
                    continue
                offenders.append(
                    {
                        "file": module_path.name,
                        "line": line,
                        "column": col,
                        "domain": domain,
                        "private_helper": helper_name,
                    }
                )

    assert not offenders, json.dumps(offenders, indent=2, sort_keys=True)
