"""Kubernetes plugin contract fixtures for focused execution-bundle tests."""

from __future__ import annotations

from typing import Any


def build_kubernetes_scan_options() -> dict[str, Any]:
    return {
        "role_path": "/workspace/k8s/demo",
        "role_name_override": None,
        "readme_config_path": None,
        "policy_config_path": None,
        "include_vars_main": False,
        "exclude_path_patterns": None,
        "detailed_catalog": False,
        "include_task_parameters": False,
        "include_task_runbooks": False,
        "inline_task_runbooks": False,
        "include_collection_checks": False,
        "keep_unknown_style_sections": False,
        "adopt_heading_mode": None,
        "vars_seed_paths": None,
        "style_readme_path": None,
        "style_source_path": None,
        "style_guide_skeleton": False,
        "compare_role_path": None,
        "fail_on_unconstrained_dynamic_includes": True,
        "fail_on_yaml_like_task_annotations": True,
        "ignore_unresolved_internal_underscore_references": False,
        "comment_doc_marker_prefix": "prism",
        "strict_phase_failures": True,
    }


def build_kubernetes_scan_context() -> dict[str, Any]:
    return {
        "features": {"kubernetes_manifest": True},
        "role_notes": {"warnings": [], "deprecations": [], "notes": [], "additionals": []},
    }