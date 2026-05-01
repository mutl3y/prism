"""fsrc-lane guardrails: scanner package import boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FSRC_RUNTIME_DIR = PROJECT_ROOT / "src" / "prism"


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


def _module_resolves_within_package_dir(
    *,
    module_name: str,
    package_dir: Path,
    package_name: str,
) -> bool:
    if module_name == package_name:
        return (package_dir / "__init__.py").exists()

    package_prefix = f"{package_name}."
    if not module_name.startswith(package_prefix):
        return False

    rel_parts = module_name[len(package_prefix) :].split(".")
    module_file = package_dir.joinpath(*rel_parts).with_suffix(".py")
    package_init = package_dir.joinpath(*rel_parts, "__init__.py")
    return module_file.exists() or package_init.exists()


def _iter_forbidden_import_offenders(
    *,
    package_dir: Path,
    package_name: str,
    forbidden_roots: tuple[str, ...],
) -> list[str]:
    def _is_external_forbidden_target(target: str) -> bool:
        if not any(
            target == root or target.startswith(f"{root}.") for root in forbidden_roots
        ):
            return False
        return not _module_resolves_within_package_dir(
            module_name=target,
            package_dir=package_dir,
            package_name=package_name,
        )

    offenders: list[str] = []

    for module_path in sorted(package_dir.rglob("*.py")):
        if "tests" in module_path.parts:
            continue
        stem = module_path.with_suffix("")
        try:
            rel = stem.relative_to(PROJECT_ROOT / "src")
            if stem.name == "__init__":
                module_name = ".".join(rel.parts[:-1])
            else:
                module_name = ".".join(rel.parts)
        except ValueError:
            rel = stem.relative_to(package_dir)
            parts = package_name.split(".") + list(rel.parts)
            if stem.name == "__init__":
                module_name = ".".join(parts[:-1])
            else:
                module_name = ".".join(parts)

        tree = ast.parse(module_path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    if _is_external_forbidden_target(target):
                        offenders.append(f"{module_name}:{target}")
                continue

            if isinstance(node, ast.ImportFrom):
                resolved_target = _resolve_import_from(module_name, node)
                if not resolved_target:
                    continue
                if _is_external_forbidden_target(resolved_target):
                    offenders.append(f"{module_name}:{resolved_target}")

    return sorted(set(offenders))


def _iter_scan_options_registry_bypass_offenders(
    module_path: Path,
    *,
    option_names: tuple[str, ...],
) -> list[str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    offenders: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "get":
            continue
        if not isinstance(node.func.value, ast.Name):
            continue
        if node.func.value.id not in option_names:
            continue
        if not node.args:
            continue
        key_arg = node.args[0]
        if not isinstance(key_arg, ast.Constant) or key_arg.value != "plugin_registry":
            continue
        offenders.append(
            f"{module_path.relative_to(PROJECT_ROOT / 'src')}:{node.lineno}"
        )

    return offenders


def test_fsrc_runtime_modules_do_not_import_src_scanner_packages() -> None:
    offenders = _iter_forbidden_import_offenders(
        package_dir=FSRC_RUNTIME_DIR,
        package_name="prism",
        forbidden_roots=(
            "prism.scanner",
            "prism.scanner_core",
            "prism.scanner_extract",
            "prism.scanner_readme",
            "prism.scanner_reporting",
            "prism.scanner_io",
            "prism.scanner_config",
            "prism.scanner_plugins",
            "prism.scanner_kernel",
            "prism.scanner_extensions",
        ),
    )

    assert (
        not offenders
    ), "fsrc runtime modules import src scanner packages: " + ", ".join(offenders)


def test_fsrc_cross_path_guardrail_allows_local_fsrc_scanner_imports(
    tmp_path: Path,
) -> None:
    runtime_dir = tmp_path / "prism"
    runtime_dir.mkdir()
    scanner_core_dir = runtime_dir / "scanner_core"
    scanner_core_dir.mkdir()
    (scanner_core_dir / "__init__.py").write_text("", encoding="utf-8")
    module_path = runtime_dir / "api.py"
    module_path.write_text(
        "from prism.scanner_core import DIContainer\n", encoding="utf-8"
    )

    offenders = _iter_forbidden_import_offenders(
        package_dir=runtime_dir,
        package_name="prism",
        forbidden_roots=("prism.scanner_core",),
    )

    assert offenders == []


def test_fsrc_cross_path_guardrail_detects_src_only_scanner_imports(
    tmp_path: Path,
) -> None:
    runtime_dir = tmp_path / "prism"
    runtime_dir.mkdir()
    module_path = runtime_dir / "api.py"
    module_path.write_text(
        "from prism.scanner_io.output import emit\n", encoding="utf-8"
    )

    offenders = _iter_forbidden_import_offenders(
        package_dir=runtime_dir,
        package_name="prism",
        forbidden_roots=("prism.scanner_io",),
    )

    assert offenders == ["prism.api:prism.scanner_io.output"]


def test_fsrc_cross_path_guardrail_detects_src_only_resolution_when_local_module_absent(
    tmp_path: Path,
) -> None:
    runtime_dir = tmp_path / "prism"
    runtime_dir.mkdir()
    module_path = runtime_dir / "api.py"
    module_path.write_text(
        "from prism.scanner_reporting.report import build_scanner_report_markdown\n",
        encoding="utf-8",
    )

    offenders = _iter_forbidden_import_offenders(
        package_dir=runtime_dir,
        package_name="prism",
        forbidden_roots=("prism.scanner_reporting",),
    )

    assert offenders == ["prism.api:prism.scanner_reporting.report"]


def test_scanner_reporting_does_not_import_scanner_plugins_internals() -> None:
    offenders = _iter_forbidden_import_offenders(
        package_dir=FSRC_RUNTIME_DIR / "scanner_reporting",
        package_name="prism.scanner_reporting",
        forbidden_roots=(
            "prism.scanner_plugins.parsers",
            "prism.scanner_plugins.ansible",
        ),
    )

    assert not offenders, (
        "scanner_reporting imports scanner_plugins internals directly "
        "(use scanner_plugins.defaults seam): " + ", ".join(offenders)
    )


def test_api_cli_entrypoints_do_not_import_scanner_plugins_directly() -> None:
    """Verify entrypoints route plugin access through approved facade seams."""
    api_py = FSRC_RUNTIME_DIR / "api.py"
    cli_py = FSRC_RUNTIME_DIR / "cli.py"

    offenders: list[str] = []

    for module_path in [api_py, cli_py]:
        if not module_path.exists():
            continue

        module_name = f"prism.{module_path.stem}"
        tree = ast.parse(module_path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = alias.name
                    if target == "prism.scanner_plugins" or target.startswith(
                        "prism.scanner_plugins."
                    ):
                        offenders.append(f"{module_name}:{target}")

            if isinstance(node, ast.ImportFrom):
                resolved_target = _resolve_import_from(module_name, node)
                if resolved_target and (
                    resolved_target == "prism.scanner_plugins"
                    or resolved_target.startswith("prism.scanner_plugins.")
                ):
                    offenders.append(f"{module_name}:{resolved_target}")

    assert not offenders, (
        "entrypoint modules must not import scanner_plugins directly; "
        "use api_layer.plugin_facade or another approved facade seam: "
        + ", ".join(offenders)
    )


def test_api_layer_non_collection_does_not_import_scanner_plugins_directly() -> None:
    """Verify api_layer/non_collection.py routes plugin access through plugin_facade."""
    non_collection_py = FSRC_RUNTIME_DIR / "api_layer" / "non_collection.py"

    if not non_collection_py.exists():
        pytest.skip("api_layer/non_collection.py does not exist")

    module_name = "prism.api_layer.non_collection"
    tree = ast.parse(non_collection_py.read_text(encoding="utf-8"))

    offenders: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = alias.name
                if target == "prism.scanner_plugins" or target.startswith(
                    "prism.scanner_plugins."
                ):
                    offenders.append(f"{module_name}:{target}")

        if isinstance(node, ast.ImportFrom):
            resolved_target = _resolve_import_from(module_name, node)
            if resolved_target and (
                resolved_target == "prism.scanner_plugins"
                or resolved_target.startswith("prism.scanner_plugins.")
            ):
                offenders.append(f"{module_name}:{resolved_target}")

    assert not offenders, (
        "api_layer/non_collection.py must not import scanner_plugins directly; "
        "use api_layer.plugin_facade instead: " + ", ".join(offenders)
    )


def test_di_does_not_import_plugin_registry_at_runtime() -> None:
    """O001: DI composition root must not import PluginRegistry at runtime.

    PluginRegistry may be imported in TYPE_CHECKING blocks for type hints,
    but must not be imported at runtime. Runtime registry access must go
    through scanner_plugins.bootstrap.get_default_plugin_registry() facade.
    """
    di_py = FSRC_RUNTIME_DIR / "scanner_core" / "di.py"

    if not di_py.exists():
        pytest.skip("scanner_core/di.py does not exist")

    tree = ast.parse(di_py.read_text(encoding="utf-8"))

    # Find TYPE_CHECKING block
    type_checking_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                for stmt in node.body:
                    if isinstance(stmt, ast.ImportFrom):
                        if stmt.module and "PluginRegistry" in [
                            alias.name for alias in stmt.names
                        ]:
                            type_checking_imports.add(stmt.module)

    # Check runtime imports
    runtime_offenders: list[str] = []
    for node in tree.body:
        # Skip TYPE_CHECKING blocks
        if isinstance(node, ast.If):
            if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                continue

        if isinstance(node, ast.ImportFrom):
            if node.module and "PluginRegistry" in [alias.name for alias in node.names]:
                if node.module == "prism.scanner_plugins.registry":
                    runtime_offenders.append(
                        f"from {node.module} import PluginRegistry"
                    )

    assert not runtime_offenders, (
        "scanner_core/di.py imports PluginRegistry at runtime (O001 violation); "
        "use scanner_plugins.bootstrap facade: " + ", ".join(runtime_offenders)
    )


def test_defaults_does_not_import_plugin_registry_singleton_directly() -> None:
    """O008/O010: defaults.py must not import plugin_registry singleton directly.

    Plugin registry access must go through bootstrap.get_default_plugin_registry()
    to maintain explicit bootstrap phase ordering.
    """
    defaults_py = FSRC_RUNTIME_DIR / "scanner_plugins" / "defaults.py"

    if not defaults_py.exists():
        pytest.skip("scanner_plugins/defaults.py does not exist")

    tree = ast.parse(defaults_py.read_text(encoding="utf-8"))

    offenders: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            if node.module == "prism.scanner_plugins.registry":
                for alias in node.names:
                    if alias.name == "plugin_registry":
                        offenders.append(
                            "from prism.scanner_plugins.registry import plugin_registry"
                        )

    assert not offenders, (
        "scanner_plugins/defaults.py imports plugin_registry singleton directly "
        "(O008/O010 violation); use scanner_plugins.bootstrap.get_default_plugin_registry(): "
        + ", ".join(offenders)
    )


def test_plugin_registry_bootstrap_initialization_smoke() -> None:
    """Bootstrap smoke test: verify registry can be initialized and accessed."""
    from prism.scanner_plugins.bootstrap import (
        get_default_plugin_registry,
        is_registry_initialized,
    )

    # Should already be initialized from package import
    assert is_registry_initialized(), "Registry should be initialized at import time"

    registry = get_default_plugin_registry()

    # Smoke checks: registry should have baseline plugins
    assert (
        len(registry.list_scan_pipeline_plugins()) >= 2
    ), "Registry should have at least 2 scan_pipeline plugins (default, ansible)"
    assert "ansible" in registry.list_scan_pipeline_plugins()
    assert "default" in registry.list_scan_pipeline_plugins()

    # Should have extract policy plugins
    assert "task_line_parsing" in registry.list_extract_policy_plugins()
    assert "task_traversal" in registry.list_extract_policy_plugins()
    assert "variable_extractor" in registry.list_extract_policy_plugins()
    assert "task_annotation_parsing" in registry.list_extract_policy_plugins()


def test_plugin_registry_bootstrap_idempotence() -> None:
    """Bootstrap initialization is idempotent; safe to call multiple times."""
    from prism.scanner_plugins.bootstrap import initialize_default_registry

    registry1 = initialize_default_registry()
    registry2 = initialize_default_registry()

    # Should return the same singleton instance
    assert registry1 is registry2, "initialize_default_registry() should be idempotent"


def test_registry_identity_does_not_reopen_scan_options_bypass_paths() -> None:
    """Registry identity must come from DI wiring, not scan_options payload lookups."""
    offenders = _iter_scan_options_registry_bypass_offenders(
        FSRC_RUNTIME_DIR / "scanner_core" / "execution_request_builder.py",
        option_names=("canonical_options",),
    )
    offenders.extend(
        _iter_scan_options_registry_bypass_offenders(
            FSRC_RUNTIME_DIR / "scanner_io" / "loader.py",
            option_names=("scan_options",),
        )
    )

    assert not offenders, (
        "registry identity must not be sourced from scan_options payloads: "
        + ", ".join(offenders)
    )
