"""Core-owned adapter seam for unconstrained dynamic include analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from prism.scanner_core.task_extract_adapters import collect_task_files
from prism.scanner_core.task_extract_adapters import load_task_yaml_file
from prism.scanner_plugins.defaults import resolve_task_traversal_policy_plugin


def _resolve_plugin_registry(di: object | None = None) -> Any | None:
    if di is None:
        return None
    registry = getattr(di, "plugin_registry", None)
    if registry is not None:
        return registry
    scan_options = getattr(di, "_scan_options", None)
    if isinstance(scan_options, dict):
        return scan_options.get("plugin_registry")
    return None


def _resolve_policy_with_registry(di: object | None = None) -> Any:
    registry = _resolve_plugin_registry(di)
    if registry is None:
        return resolve_task_traversal_policy_plugin(di)
    try:
        return resolve_task_traversal_policy_plugin(di, registry=registry)
    except TypeError:
        return resolve_task_traversal_policy_plugin(di)


def collect_unconstrained_dynamic_task_includes(
    role_path: str,
    *,
    exclude_paths: list[str] | None = None,
    di: object | None = None,
) -> list[str]:
    policy = _resolve_policy_with_registry(di)
    role_root = Path(role_path).resolve()
    return policy.collect_unconstrained_dynamic_task_includes(
        role_root=role_root,
        task_files=collect_task_files(role_root, exclude_paths=exclude_paths, di=di),
        load_yaml_file=lambda file_path: load_task_yaml_file(file_path, di=di),
    )


def collect_unconstrained_dynamic_role_includes(
    role_path: str,
    *,
    exclude_paths: list[str] | None = None,
    di: object | None = None,
) -> list[str]:
    policy = _resolve_policy_with_registry(di)
    role_root = Path(role_path).resolve()
    return policy.collect_unconstrained_dynamic_role_includes(
        role_root=role_root,
        task_files=collect_task_files(role_root, exclude_paths=exclude_paths, di=di),
        load_yaml_file=lambda file_path: load_task_yaml_file(file_path, di=di),
    )
