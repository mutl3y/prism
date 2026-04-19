"""Tests for blocker_fact_evaluator — extracted blocker-fact assembly."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from prism.scanner_core.blocker_fact_evaluator import build_scan_policy_blocker_facts


def _make_scan_options(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "role_path": "/tmp/test-role",
        "role_name_override": None,
        "readme_config_path": None,
        "include_vars_main": True,
        "exclude_path_patterns": None,
        "detailed_catalog": False,
        "include_task_parameters": True,
        "include_task_runbooks": True,
        "inline_task_runbooks": True,
        "include_collection_checks": True,
        "keep_unknown_style_sections": True,
        "adopt_heading_mode": None,
        "vars_seed_paths": None,
        "style_readme_path": None,
        "style_source_path": None,
        "style_guide_skeleton": None,
        "compare_role_path": None,
        "fail_on_unconstrained_dynamic_includes": False,
        "fail_on_yaml_like_task_annotations": False,
        "ignore_unresolved_internal_underscore_references": False,
    }
    base.update(overrides)
    return base


def test_blocker_facts_disabled_policies_returns_zeroed_counts() -> None:
    opts = _make_scan_options()
    result = build_scan_policy_blocker_facts(
        scan_options=opts,
        metadata={},
        di=None,
    )
    assert result["dynamic_includes"]["enabled"] is False
    assert result["dynamic_includes"]["total_count"] == 0
    assert result["yaml_like_annotations"]["enabled"] is False
    assert result["yaml_like_annotations"]["count"] == 0
    assert result["provenance"]["role_path"] == "/tmp/test-role"


@patch(
    "prism.scanner_core.blocker_fact_evaluator.collect_unconstrained_dynamic_task_includes",
    return_value=["a", "b"],
)
@patch(
    "prism.scanner_core.blocker_fact_evaluator.collect_unconstrained_dynamic_role_includes",
    return_value=["c"],
)
def test_blocker_facts_dynamic_includes_enabled(mock_role: Any, mock_task: Any) -> None:
    opts = _make_scan_options(fail_on_unconstrained_dynamic_includes=True)
    result = build_scan_policy_blocker_facts(
        scan_options=opts,
        metadata={},
        di=None,
    )
    assert result["dynamic_includes"]["enabled"] is True
    assert result["dynamic_includes"]["task_count"] == 2
    assert result["dynamic_includes"]["role_count"] == 1
    assert result["dynamic_includes"]["total_count"] == 3


def test_blocker_facts_yaml_like_enabled() -> None:
    opts = _make_scan_options(fail_on_yaml_like_task_annotations=True)
    metadata: dict[str, Any] = {"features": {"yaml_like_task_annotations": 5}}
    result = build_scan_policy_blocker_facts(
        scan_options=opts,
        metadata=metadata,
        di=None,
    )
    assert result["yaml_like_annotations"]["enabled"] is True
    assert result["yaml_like_annotations"]["count"] == 5


def test_blocker_facts_provenance_exclude_paths() -> None:
    opts = _make_scan_options(exclude_path_patterns=["tests/", "docs/"])
    result = build_scan_policy_blocker_facts(
        scan_options=opts,
        metadata={},
        di=None,
    )
    assert result["provenance"]["exclude_path_patterns"] == ["tests/", "docs/"]
