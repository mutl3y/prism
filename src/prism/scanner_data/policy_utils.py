"""Shared policy normalization utilities for scanner_core and scanner_extract."""

from __future__ import annotations

from typing import TypeGuard

from prism.scanner_data.contracts_request import ScanPolicyContext, ScanPolicyWarning


def is_scan_policy_context(value: object) -> TypeGuard[ScanPolicyContext]:
    """Check if value is a valid ScanPolicyContext dict."""
    return isinstance(value, dict)


def copy_scan_policy_context(
    policy_context: ScanPolicyContext,
) -> ScanPolicyContext:
    """Preserve the ScanPolicyContext TypedDict contract across shallow copies."""
    return ScanPolicyContext(**policy_context)


def normalize_policy_context(
    policy_context: ScanPolicyContext | None,
) -> tuple[ScanPolicyContext | None, list[ScanPolicyWarning]]:
    """Normalize and validate policy context, returning tuple of (normalized, warnings).

    Returns (None, []) if policy_context is invalid or None.
    Preserves TypedDict contract for normalized context.
    """
    if not is_scan_policy_context(policy_context):
        return None, []
    return copy_scan_policy_context(policy_context), []
