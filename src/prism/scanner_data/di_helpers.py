"""Shared DI utility helpers for scanner_core and scanner_extract."""

from __future__ import annotations

from typing import Any


def scan_options_from_di(di: object | None = None) -> dict[str, object] | None:
    if di is None:
        return None
    scan_options = getattr(di, "scan_options", None)
    if isinstance(scan_options, dict):
        return scan_options
    return None


def get_prepared_policy_or_none(di: object | None, policy_name: str) -> object | None:
    scan_options = scan_options_from_di(di)
    if not isinstance(scan_options, dict):
        return None
    prepared_policy_bundle = scan_options.get("prepared_policy_bundle")
    if not isinstance(prepared_policy_bundle, dict):
        return None
    return prepared_policy_bundle.get(policy_name)


def require_prepared_policy(
    di: object | None,
    policy_name: str,
    context_label: str,
) -> Any:
    """Retrieve a required policy from the prepared_policy_bundle or raise."""
    policy = get_prepared_policy_or_none(di, policy_name)
    if policy is not None:
        return policy
    raise ValueError(
        f"prepared_policy_bundle.{policy_name} must be provided before "
        f"{context_label} canonical execution"
    )
