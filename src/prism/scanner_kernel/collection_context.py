"""Collection-level context helpers for scanner kernel orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from prism.scanner_kernel.repo_context import CONTEXT_VERSION
from prism.scanner_kernel.repo_context import discover_role_variable_names
from prism.scanner_kernel.repo_context import is_kernel_enabled


class CollectionScanContext(TypedDict):
    """Typed collection context payload used by kernel orchestration."""

    collection_name: str
    collection_path: str
    role_paths: list[str]
    aggregated_variable_names: list[str]
    role_variable_index: dict[str, list[str]]
    cross_role_shared_names: list[str]
    context_version: str


def build_collection_scan_context(
    collection_path: str,
    role_paths: list[str],
    collection_name: str = "",
) -> CollectionScanContext | None:
    """Build sparse collection scan context when kernel is enabled."""
    if not is_kernel_enabled():
        return None

    role_variable_index: dict[str, list[str]] = {
        role_path: discover_role_variable_names(role_path) for role_path in role_paths
    }
    all_names: list[str] = []
    for names in role_variable_index.values():
        all_names.extend(names)

    counts: dict[str, int] = {}
    for name in all_names:
        counts[name] = counts.get(name, 0) + 1

    resolved_name = collection_name or Path(collection_path).name

    return {
        "collection_name": resolved_name,
        "collection_path": collection_path,
        "role_paths": list(role_paths),
        "aggregated_variable_names": sorted(set(all_names)),
        "role_variable_index": role_variable_index,
        "cross_role_shared_names": sorted(
            name for name, count in counts.items() if count > 1
        ),
        "context_version": CONTEXT_VERSION,
    }


__all__ = ["build_collection_scan_context", "CollectionScanContext", "CONTEXT_VERSION"]
