"""Assemble scan-policy blocker facts from runtime state."""

from __future__ import annotations

from typing import Any

from prism.scanner_core.dynamic_include_audit import (
    collect_unconstrained_dynamic_role_includes,
    collect_unconstrained_dynamic_task_includes,
)
from prism.scanner_data.contracts_request import ScanOptionsDict, ScanPolicyBlockerFacts

_YAML_LIKE_FEATURE_SOURCE = "metadata.features.yaml_like_task_annotations"
_DYNAMIC_INCLUDE_SOURCES = [
    "scanner_core.dynamic_include_audit.collect_unconstrained_dynamic_task_includes",
    "scanner_core.dynamic_include_audit.collect_unconstrained_dynamic_role_includes",
]


def build_scan_policy_blocker_facts(
    *,
    scan_options: ScanOptionsDict,
    metadata: dict[str, Any],
    di: Any,
) -> ScanPolicyBlockerFacts:
    features = metadata.get("features")
    feature_map = dict(features) if isinstance(features, dict) else {}

    dynamic_include_enabled = bool(
        scan_options.get("fail_on_unconstrained_dynamic_includes")
    )
    dynamic_task_count = 0
    dynamic_role_count = 0

    if dynamic_include_enabled:
        dynamic_task_count = len(
            collect_unconstrained_dynamic_task_includes(
                str(scan_options["role_path"]),
                exclude_paths=scan_options.get("exclude_path_patterns"),
                di=di,
            )
        )
        dynamic_role_count = len(
            collect_unconstrained_dynamic_role_includes(
                str(scan_options["role_path"]),
                exclude_paths=scan_options.get("exclude_path_patterns"),
                di=di,
            )
        )

    yaml_like_enabled = bool(scan_options.get("fail_on_yaml_like_task_annotations"))
    yaml_like_count = 0
    if yaml_like_enabled:
        yaml_like_count = int(feature_map.get("yaml_like_task_annotations") or 0)

    exclude_paths = scan_options.get("exclude_path_patterns")
    normalized_exclude_paths = (
        [path for path in exclude_paths if isinstance(path, str)]
        if isinstance(exclude_paths, list)
        else None
    )

    return {
        "dynamic_includes": {
            "enabled": dynamic_include_enabled,
            "task_count": dynamic_task_count,
            "role_count": dynamic_role_count,
            "total_count": dynamic_task_count + dynamic_role_count,
        },
        "yaml_like_annotations": {
            "enabled": yaml_like_enabled,
            "count": yaml_like_count,
        },
        "provenance": {
            "role_path": str(scan_options["role_path"]),
            "exclude_path_patterns": normalized_exclude_paths,
            "metadata_feature_source": _YAML_LIKE_FEATURE_SOURCE,
            "dynamic_include_sources": list(_DYNAMIC_INCLUDE_SOURCES),
        },
    }
