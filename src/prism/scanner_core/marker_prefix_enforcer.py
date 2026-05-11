"""MP1 Runtime Enforcer for marker-prefix.

Enforces fail-closed behavior: marker-prefix must be explicitly available
in the prepared_policy_bundle, never implicitly computed or defaulted.

Contract:
- Input: PreparedPolicyBundle (dict-like)
- Output: marker_prefix (str) or raise ValueError
- Guarantee: All callers that need marker_prefix must call enforce_marker_prefix_available()
- Failure Mode: ValueError if bundle missing, malformed, or invalid (internal validation)
"""

from __future__ import annotations

from typing import Any


def enforce_marker_prefix_available(bundle: Any) -> str:
    """Enforce marker-prefix availability in bundle, fail-closed if missing.

    This function is the enforcement gate for MP1 contract:
    - Marker-prefix must be ingress-owned (set at scan entry point)
    - Marker-prefix is immutable after bundle creation
    - Consumers access marker-prefix ONLY via this enforcer
    - Silent fallbacks are not permitted

    Args:
        bundle: PreparedPolicyBundle (dict) containing comment_doc_marker_prefix.

    Returns:
        marker_prefix: str - the validated marker-prefix value.

    Raises:
        ValueError: If bundle is None, not a dict, missing key, or value invalid.

    Example:
        bundle = scan_options.get("prepared_policy_bundle")
        prefix = enforce_marker_prefix_available(bundle)
        # Now use prefix in task extraction
    """
    # GUARD 1: Bundle must be a dict
    if not isinstance(bundle, dict):
        raise ValueError(f"bundle must be a dict, got {type(bundle).__name__}")

    # GUARD 2: Bundle must contain comment_doc_marker_prefix key
    if "comment_doc_marker_prefix" not in bundle:
        raise ValueError("bundle missing required key 'comment_doc_marker_prefix'")

    marker_prefix = bundle["comment_doc_marker_prefix"]

    # GUARD 3: Value must be a string
    if not isinstance(marker_prefix, str):
        raise ValueError(
            f"comment_doc_marker_prefix must be string, got {type(marker_prefix).__name__}"
        )

    # GUARD 4: Value must not be empty string
    if not marker_prefix:
        raise ValueError("comment_doc_marker_prefix must be non-empty string")

    return marker_prefix
