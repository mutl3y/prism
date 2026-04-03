"""Shared behavioral acceptance checks for boundary ownership tests."""

from __future__ import annotations

import functools
import importlib
import inspect
import pkgutil
from types import ModuleType
from typing import Any, Iterable, Mapping


def assert_named_exports_exist(
    export_owner: Any,
    export_names: Iterable[str],
) -> None:
    """Assert named exports exist on the boundary owner."""
    for export_name in export_names:
        assert hasattr(
            export_owner, export_name
        ), f"{export_name} must exist on {export_owner!r}"


def assert_callable_aliases_bind_exactly(
    alias_owner: Any,
    expected_aliases: Mapping[str, object],
    *,
    expected_owner_modules: Mapping[str, str] | None = None,
) -> None:
    """Assert aliased boundary callables are present and identity-bound."""
    for alias_name, expected_callable in expected_aliases.items():
        actual = getattr(alias_owner, alias_name, None)
        assert callable(actual), f"{alias_name} must be callable"
        assert (
            actual is expected_callable
        ), f"{alias_name} must bind to shared canonical callable"

        if expected_owner_modules and alias_name in expected_owner_modules:
            expected_module = expected_owner_modules[alias_name]
            actual_module = getattr(actual, "__module__", None)
            assert (
                actual_module == expected_module
            ), f"{alias_name} must be owned by {expected_module}"


def assert_callable_aliases_expose_contract(
    alias_owner: Any,
    alias_names: Iterable[str],
    *,
    expected_owner_modules: Mapping[str, str] | None = None,
) -> None:
    """Assert boundary aliases remain callable and module-owned as expected."""
    for alias_name in alias_names:
        actual = getattr(alias_owner, alias_name, None)
        assert callable(actual), f"{alias_name} must be callable"

        if expected_owner_modules and alias_name in expected_owner_modules:
            expected_module = expected_owner_modules[alias_name]
            actual_module = getattr(actual, "__module__", None)
            assert (
                actual_module == expected_module
            ), f"{alias_name} must be owned by {expected_module}"


def assert_repo_scan_facade_contract(repo_scan_facade: Any) -> None:
    """Assert the minimal shared repo facade contract exists and is callable."""
    for member_name in (
        "build_repo_intake_components",
        "run_repo_scan",
        "normalize_repo_scan_payload",
    ):
        member = getattr(repo_scan_facade, member_name, None)
        assert callable(member), f"repo facade member {member_name} must be callable"


def assert_scanner_output_wiring_is_canonical(scanner_module: Any) -> None:
    """Assert scanner output glue is wired to canonical emission modules."""
    render_binding = getattr(scanner_module, "_render_and_write_scan_output", None)
    assert isinstance(render_binding, functools.partial)
    assert (
        render_binding.func
        is scanner_module._scan_output_primary_render_and_write_scan_output
    )

    emit_binding = getattr(scanner_module, "_emit_scan_outputs", None)
    assert isinstance(emit_binding, functools.partial)
    assert emit_binding.func is scanner_module._scan_runtime.emit_scan_outputs
    assert (
        emit_binding.keywords.get("emit_scan_outputs_fn")
        is scanner_module._scan_output_emit_scan_outputs
    )


def assert_packages_do_not_reference_scanner_facade(
    package_names: Iterable[str],
) -> None:
    """Assert canonical packages do not import or re-export scanner facade symbols."""
    scanner_module = importlib.import_module("prism.scanner")
    offenders: list[str] = []

    for package_name in package_names:
        package = importlib.import_module(f"prism.{package_name}")
        package_paths = getattr(package, "__path__", None)
        if package_paths is None:
            continue

        for module_info in pkgutil.walk_packages(
            package_paths, prefix=f"prism.{package_name}."
        ):
            module = importlib.import_module(module_info.name)
            if _module_references_scanner_facade(module, scanner_module):
                offenders.append(module_info.name)

    assert not offenders, (
        "Canonical scanner packages must not reference prism.scanner facade symbols: "
        + ", ".join(sorted(offenders))
    )


def _module_references_scanner_facade(
    module: ModuleType,
    scanner_module: ModuleType,
) -> bool:
    for value in module.__dict__.values():
        if isinstance(value, ModuleType) and value is scanner_module:
            return True
        if inspect.isfunction(value) and value.__module__ == "prism.scanner":
            return True
    return False
