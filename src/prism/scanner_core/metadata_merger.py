"""Policy warning list merge helpers for scanner_core metadata assembly."""

from __future__ import annotations

import copy

from typing import TypeGuard

from prism.scanner_data.contracts_request import ScanPolicyWarning


def _is_policy_warning_entry(value: object) -> TypeGuard[ScanPolicyWarning]:
    return isinstance(value, dict)


def _copy_policy_warning_entries(raw_warnings: object) -> list[ScanPolicyWarning]:
    if not isinstance(raw_warnings, list):
        return []
    return [
        copy.copy(warning)
        for warning in raw_warnings
        if _is_policy_warning_entry(warning)
    ]


def merge_policy_warning_entries(
    ingress_warnings: object,
    metadata_warnings: object,
) -> list[ScanPolicyWarning]:
    merged: list[ScanPolicyWarning] = []
    for warning in _copy_policy_warning_entries(ingress_warnings):
        if warning not in merged:
            merged.append(warning)
    for warning in _copy_policy_warning_entries(metadata_warnings):
        if warning not in merged:
            merged.append(warning)
    return merged
