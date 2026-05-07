from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Collection
from typing import Any


@dataclass(frozen=True)
class PolicyConstants:
    """Pre-resolved policy constants extracted from prepared_policy_bundle.

    All fields are frozen (immutable) and resolved once per scan at initialization.
    This eliminates repeated require_prepared_policy() calls in hotpaths.
    """

    # From prepared_policy_bundle['task_line_parsing']
    task_include_keys: Collection[str]
    role_include_keys: Collection[str]
    include_vars_keys: Collection[str]
    set_fact_keys: Collection[str]
    task_block_keys: Collection[str]
    task_meta_keys: Collection[str]


def build_policy_constants(prepared_policy_bundle: dict[str, Any]) -> PolicyConstants:
    """Build PolicyConstants from nested prepared_policy_bundle structure.

    Args:
        prepared_policy_bundle: TypedDict with required key 'task_line_parsing'

    Returns:
        PolicyConstants with all fields pre-resolved

    Raises:
        ValueError: If prepared_policy_bundle or task_line_parsing policy is missing/invalid
    """
    if not prepared_policy_bundle:
        raise ValueError("prepared_policy_bundle is required")

    task_policy = prepared_policy_bundle.get("task_line_parsing")
    if not task_policy:
        raise ValueError("prepared_policy_bundle['task_line_parsing'] is required")

    return PolicyConstants(
        # ✅ CORRECT nested access
        task_include_keys=task_policy.TASK_INCLUDE_KEYS,
        role_include_keys=task_policy.ROLE_INCLUDE_KEYS,
        include_vars_keys=task_policy.INCLUDE_VARS_KEYS,
        set_fact_keys=task_policy.SET_FACT_KEYS,
        task_block_keys=task_policy.TASK_BLOCK_KEYS,
        task_meta_keys=task_policy.TASK_META_KEYS,
    )
