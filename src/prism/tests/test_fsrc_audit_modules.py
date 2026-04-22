"""Tests for audit modules moved from scanner_core to scanner_plugins.audit."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch


def test_audit_blocker_fact_evaluator_importable_from_new_location() -> None:
    from prism.scanner_plugins.audit.blocker_fact_evaluator import (
        build_scan_policy_blocker_facts,
    )

    assert callable(build_scan_policy_blocker_facts)


def test_audit_dynamic_include_audit_importable_from_new_location() -> None:
    from prism.scanner_plugins.audit.dynamic_include_audit import (
        collect_unconstrained_dynamic_task_includes,
        collect_unconstrained_dynamic_role_includes,
    )

    assert callable(collect_unconstrained_dynamic_task_includes)
    assert callable(collect_unconstrained_dynamic_role_includes)


def test_audit_blocker_facts_disabled_policies_zeroed() -> None:
    from prism.scanner_plugins.audit.blocker_fact_evaluator import (
        build_scan_policy_blocker_facts,
    )

    opts: dict[str, Any] = {
        "role_path": "/tmp/test-role",
        "fail_on_unconstrained_dynamic_includes": False,
        "fail_on_yaml_like_task_annotations": False,
        "exclude_path_patterns": None,
    }
    result = build_scan_policy_blocker_facts(
        scan_options=opts,
        metadata={},
        di=None,
    )
    assert result["dynamic_includes"]["enabled"] is False
    assert result["dynamic_includes"]["total_count"] == 0
    assert result["yaml_like_annotations"]["enabled"] is False
    assert result["yaml_like_annotations"]["count"] == 0


@patch(
    "prism.scanner_plugins.audit.blocker_fact_evaluator.collect_unconstrained_dynamic_task_includes",
    return_value=["a", "b"],
)
@patch(
    "prism.scanner_plugins.audit.blocker_fact_evaluator.collect_unconstrained_dynamic_role_includes",
    return_value=["c"],
)
def test_audit_blocker_facts_dynamic_enabled(mock_role: Any, mock_task: Any) -> None:
    from prism.scanner_plugins.audit.blocker_fact_evaluator import (
        build_scan_policy_blocker_facts,
    )

    opts: dict[str, Any] = {
        "role_path": "/tmp/test-role",
        "fail_on_unconstrained_dynamic_includes": True,
        "fail_on_yaml_like_task_annotations": False,
        "exclude_path_patterns": None,
    }
    result = build_scan_policy_blocker_facts(
        scan_options=opts,
        metadata={},
        di=None,
    )
    assert result["dynamic_includes"]["enabled"] is True
    assert result["dynamic_includes"]["total_count"] == 3
