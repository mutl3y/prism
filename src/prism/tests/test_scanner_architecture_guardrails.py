"""Architecture guardrails for scanner facade decomposition."""

from __future__ import annotations

import ast
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCANNER_CORE_DIR = PROJECT_ROOT / "src" / "prism" / "scanner_core"
SCANNER_FACADE_PATH = PROJECT_ROOT / "src" / "prism" / "scanner.py"
CANONICAL_SCANNER_PACKAGE_DIRS = {
    "prism.scanner_core": PROJECT_ROOT / "src" / "prism" / "scanner_core",
    "prism.scanner_extract": PROJECT_ROOT / "src" / "prism" / "scanner_extract",
    "prism.scanner_readme": PROJECT_ROOT / "src" / "prism" / "scanner_readme",
    "prism.scanner_analysis": PROJECT_ROOT / "src" / "prism" / "scanner_analysis",
    "prism.scanner_io": PROJECT_ROOT / "src" / "prism" / "scanner_io",
    "prism.scanner_config": PROJECT_ROOT / "src" / "prism" / "scanner_config",
}
SCANNER_PRIVATE_IMPORT_BOUNDARIES = (
    "prism.scanner_extract",
    "prism.scanner_readme",
    "prism.scanner_analysis",
    "prism.scanner_io",
    "prism.scanner_config",
)

_ALLOWED_CANONICAL_PRIVATE_CROSS_PACKAGE_TOUCHPOINTS: dict[str, set[str]] = {
    "prism.scanner_core.feature_detector": {
        "prism.scanner_extract.task_parser:_collect_task_files",
        "prism.scanner_extract.task_parser:_detect_task_module",
        "prism.scanner_extract.task_parser:_extract_collection_from_module_name",
        "prism.scanner_extract.task_parser:_extract_task_annotations_for_file",
        "prism.scanner_extract.task_parser:_iter_dynamic_role_include_targets",
        "prism.scanner_extract.task_parser:_iter_role_include_targets",
        "prism.scanner_extract.task_parser:_iter_task_include_targets",
        "prism.scanner_extract.task_parser:_iter_task_mappings",
        "prism.scanner_extract.task_parser:_load_yaml_file",
    },
    "prism.scanner_core.variable_pipeline": {
        "prism.scanner_extract.task_parser:_format_inline_yaml",
        "prism.scanner_extract.task_parser:_load_yaml_file",
        "prism.scanner_extract.variable_extractor:_collect_dynamic_include_vars_refs",
        "prism.scanner_extract.variable_extractor:_collect_dynamic_task_include_refs",
        "prism.scanner_extract.variable_extractor:_collect_include_vars_files",
        "prism.scanner_extract.variable_extractor:_collect_referenced_variable_names",
        "prism.scanner_extract.variable_extractor:_collect_register_names",
        "prism.scanner_extract.variable_extractor:_collect_set_fact_names",
        "prism.scanner_extract.variable_extractor:_find_variable_line_in_yaml",
        "prism.scanner_extract.variable_extractor:_infer_variable_type",
        "prism.scanner_extract.variable_extractor:_is_sensitive_variable",
    },
}


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


def _module_name_for_path(module_path: Path) -> str:
    rel = module_path.relative_to(PROJECT_ROOT / "src")
    stem = rel.with_suffix("")
    if stem.name == "__init__":
        return ".".join(stem.parts[:-1])
    return ".".join(stem.parts)


def _boundary_root(module_name: str) -> str:
    parts = module_name.split(".")
    if len(parts) < 2:
        return module_name
    return ".".join(parts[:2])


def _iter_python_modules(package_dirs: dict[str, Path]) -> list[tuple[str, Path]]:
    modules: list[tuple[str, Path]] = []
    for package_name, package_dir in sorted(package_dirs.items()):
        for module_path in sorted(package_dir.rglob("*.py")):
            modules.append((package_name, module_path))
    return modules


def _resolve_import_from(module_name: str, node: ast.ImportFrom) -> str | None:
    if node.module is None:
        return None
    if node.level <= 0:
        return node.module

    module_parts = module_name.split(".")
    if module_name.endswith(".__init__"):
        module_parts = module_parts[:-1]
    keep = max(0, len(module_parts) - node.level)
    prefix = ".".join(module_parts[:keep])
    return f"{prefix}.{node.module}" if prefix else node.module


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


def test_canonical_scanner_packages_do_not_import_scanner_facade() -> None:
    offenders: list[str] = []

    for package_name, module_path in _iter_python_modules(
        CANONICAL_SCANNER_PACKAGE_DIRS
    ):
        module_name = _module_name_for_path(module_path)
        tree = ast.parse(module_path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    if target == "prism.scanner" or target.startswith("prism.scanner."):
                        offenders.append(f"{module_name}:{target}")
            if isinstance(node, ast.ImportFrom):
                resolved_target = _resolve_import_from(module_name, node)
                if not resolved_target:
                    continue
                if resolved_target == "prism.scanner" or resolved_target.startswith(
                    "prism.scanner."
                ):
                    offenders.append(f"{module_name}:{resolved_target}")

    assert not offenders, (
        "canonical scanner packages reverse-import scanner facade; offenders: "
        + ", ".join(sorted(set(offenders)))
    )


def _iter_scanner_private_cross_package_imports(module_path: Path) -> list[str]:
    return _iter_private_cross_package_imports(
        module_path=module_path,
        module_name="prism.scanner",
        boundaries=SCANNER_PRIVATE_IMPORT_BOUNDARIES,
    )


def _iter_private_cross_package_imports(
    *,
    module_path: Path,
    module_name: str,
    boundaries: tuple[str, ...],
) -> list[str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    offenders: list[str] = []
    module_boundary = _boundary_root(module_name)
    imported_boundary_aliases: dict[str, str] = {}

    def _is_private_boundary_module(module: str) -> bool:
        return any(
            module == boundary or module.startswith(f"{boundary}.")
            for boundary in SCANNER_PRIVATE_IMPORT_BOUNDARIES
        )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Import):
            continue
        for alias in node.names:
            module_name = alias.name
            if not _is_private_boundary_module(module_name):
                continue
            alias_name = alias.asname or module_name.rsplit(".", 1)[-1]
            imported_boundary_aliases[alias_name] = module_name

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue

        resolved_module = _resolve_import_from(module_name, node)
        if not resolved_module:
            continue

        if not _is_private_boundary_module(resolved_module):
            continue

        resolved_boundary = _boundary_root(resolved_module)

        for alias in node.names:
            if alias.name != "*":
                alias_name = alias.asname or alias.name
                imported_boundary_aliases[alias_name] = (
                    f"{resolved_module}.{alias.name}"
                )
            if alias.name.startswith("_") and resolved_boundary != module_boundary:
                offenders.append(f"{resolved_module}:{alias.name}")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        if not node.attr.startswith("_"):
            continue
        if not isinstance(node.value, ast.Name):
            continue
        imported_module = imported_boundary_aliases.get(node.value.id)
        if not imported_module:
            continue
        if _boundary_root(imported_module) == module_boundary:
            continue
        offenders.append(f"{imported_module}:{node.attr}")

    return sorted(set(offenders))


def test_scanner_facade_uses_public_cross_package_imports_only() -> None:
    offenders = _iter_scanner_private_cross_package_imports(SCANNER_FACADE_PATH)
    assert (
        not offenders
    ), "scanner facade imports private cross-package names: " + ", ".join(offenders)


def test_canonical_scanner_packages_use_public_cross_package_imports_only() -> None:
    offenders_by_module: list[str] = []

    for package_name, module_path in _iter_python_modules(
        CANONICAL_SCANNER_PACKAGE_DIRS
    ):
        module_name = _module_name_for_path(module_path)
        offenders = _iter_private_cross_package_imports(
            module_path=module_path,
            module_name=module_name,
            boundaries=SCANNER_PRIVATE_IMPORT_BOUNDARIES,
        )
        allowed = _ALLOWED_CANONICAL_PRIVATE_CROSS_PACKAGE_TOUCHPOINTS.get(
            module_name,
            set(),
        )
        offenders = [offender for offender in offenders if offender not in allowed]
        if offenders:
            offenders_by_module.append(f"{module_name}: {', '.join(offenders)}")

    assert (
        not offenders_by_module
    ), "canonical scanner packages import private cross-package names: " + " | ".join(
        offenders_by_module
    )


def test_canonical_scanner_packages_smoke_check_no_scanner_facade_import_tokens() -> (
    None
):
    reverse_import_pattern = re.compile(
        r"(?:^|\n)\s*(?:from\s+prism\.scanner\b|import\s+prism\.scanner\b)",
        re.MULTILINE,
    )
    offenders: list[str] = []

    for _package_name, module_path in _iter_python_modules(
        CANONICAL_SCANNER_PACKAGE_DIRS
    ):
        source = module_path.read_text(encoding="utf-8")
        if reverse_import_pattern.search(source):
            offenders.append(module_path.name)

    assert (
        not offenders
    ), "regex smoke detected potential reverse scanner imports: " + ", ".join(
        sorted(set(offenders))
    )


def test_private_cross_package_attribute_access_is_detected(tmp_path: Path) -> None:
    module_path = tmp_path / "fake_scanner.py"
    module_path.write_text(
        "\n".join(
            [
                "import prism.scanner_readme.style as readme_style",
                "readme_style._render_variable_summary_section({}, {})",
            ]
        ),
        encoding="utf-8",
    )

    offenders = _iter_scanner_private_cross_package_imports(module_path)

    assert offenders == ["prism.scanner_readme.style:_render_variable_summary_section"]


def test_from_import_alias_private_attribute_access_is_detected(tmp_path: Path) -> None:
    module_path = tmp_path / "fake_scanner.py"
    module_path.write_text(
        "\n".join(
            [
                "from prism.scanner_readme import style as readme_style",
                "readme_style._private_name",
            ]
        ),
        encoding="utf-8",
    )

    offenders = _iter_scanner_private_cross_package_imports(module_path)

    assert offenders == ["prism.scanner_readme.style:_private_name"]


def test_private_from_import_symbol_alias_is_detected(tmp_path: Path) -> None:
    module_path = tmp_path / "fake_scanner.py"
    module_path.write_text(
        "\n".join(
            [
                "from prism.scanner_readme.style import _private_symbol as private_symbol",
                "_ = private_symbol",
            ]
        ),
        encoding="utf-8",
    )

    offenders = _iter_scanner_private_cross_package_imports(module_path)

    assert offenders == ["prism.scanner_readme.style:_private_symbol"]


def test_private_cross_package_offenders_are_deduplicated(tmp_path: Path) -> None:
    module_path = tmp_path / "fake_scanner.py"
    module_path.write_text(
        "\n".join(
            [
                "from prism.scanner_readme import style as readme_style",
                "_ = readme_style._private_name",
                "_ = readme_style._private_name",
            ]
        ),
        encoding="utf-8",
    )

    offenders = _iter_scanner_private_cross_package_imports(module_path)

    assert offenders == ["prism.scanner_readme.style:_private_name"]


def test_wildcard_from_import_private_names_are_intentionally_ignored(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "fake_scanner.py"
    module_path.write_text(
        "\n".join(
            [
                "from prism.scanner_readme.style import *",
                "_ = _private_symbol",
            ]
        ),
        encoding="utf-8",
    )

    offenders = _iter_scanner_private_cross_package_imports(module_path)

    assert offenders == []
