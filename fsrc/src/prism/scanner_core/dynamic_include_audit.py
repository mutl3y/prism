"""Core-owned adapter seam for unconstrained dynamic include analysis."""

from __future__ import annotations

from pathlib import Path

from prism.scanner_core.di_helpers import _scan_options_from_di
from prism.scanner_core.task_extract_adapters import collect_task_files
from prism.scanner_core.task_extract_adapters import load_task_yaml_file


def _get_task_traversal_policy(di: object | None = None) -> object:
    if di is not None:
        scan_options = _scan_options_from_di(di)
        if isinstance(scan_options, dict):
            bundle = scan_options.get("prepared_policy_bundle")
            if isinstance(bundle, dict):
                policy = bundle.get("task_traversal")
                if policy is not None:
                    return policy
    raise ValueError(
        "prepared_policy_bundle.task_traversal must be provided before "
        "dynamic include audit execution"
    )


def collect_unconstrained_dynamic_task_includes(
    role_path: str,
    *,
    exclude_paths: list[str] | None = None,
    di: object | None = None,
) -> list[str]:
    policy = _get_task_traversal_policy(di)
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
    policy = _get_task_traversal_policy(di)
    role_root = Path(role_path).resolve()
    return policy.collect_unconstrained_dynamic_role_includes(
        role_root=role_root,
        task_files=collect_task_files(role_root, exclude_paths=exclude_paths, di=di),
        load_yaml_file=lambda file_path: load_task_yaml_file(file_path, di=di),
    )
