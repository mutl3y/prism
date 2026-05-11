from __future__ import annotations

import logging
from typing import Any

import pytest

from prism.errors import PrismRuntimeError
from prism.scanner_data.contracts_request import ScanOptionsDict
from prism.scanner_plugins.ansible.default_policies import (
    AnsibleDefaultTaskLineParsingPolicyPlugin,
)
from prism.scanner_plugins.defaults import (
    resolve_blocker_fact_builder,
    resolve_task_line_parsing_policy_plugin,
)
from prism.scanner_plugins.registry import PluginRegistry


def _scan_options(role_path: str) -> ScanOptionsDict:
    return {
        "role_path": role_path,
        "role_name_override": None,
        "readme_config_path": None,
        "policy_config_path": None,
        "include_vars_main": True,
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
        "fail_on_unconstrained_dynamic_includes": None,
        "fail_on_yaml_like_task_annotations": None,
        "ignore_unresolved_internal_underscore_references": None,
    }


def test_validate_shape_strict_mode_raises_for_malformed_task_line_plugin() -> None:
    class _MalformedTaskLinePlugin:
        pass

    class _DI:
        def factory_task_line_parsing_policy_plugin(self) -> _MalformedTaskLinePlugin:
            return _MalformedTaskLinePlugin()

    with pytest.raises(PrismRuntimeError) as exc_info:
        resolve_task_line_parsing_policy_plugin(_DI(), strict_mode=True)

    assert exc_info.value.code == "malformed_plugin_shape"


def test_validate_shape_non_strict_mode_uses_fallback_for_malformed_di_plugin() -> None:
    class _MalformedTaskLinePlugin:
        pass

    class _DI:
        def factory_task_line_parsing_policy_plugin(self) -> _MalformedTaskLinePlugin:
            return _MalformedTaskLinePlugin()

    plugin = resolve_task_line_parsing_policy_plugin(_DI(), strict_mode=False)

    assert isinstance(plugin, AnsibleDefaultTaskLineParsingPolicyPlugin)


def test_validate_shape_non_strict_mode_uses_fallback_when_registry_construction_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class _FailingPlugin:
        PLUGIN_API_VERSION = 1
        PLUGIN_IS_STATELESS = True

        def __init__(self) -> None:
            raise ValueError("Simulated plugin construction failure")

    registry = PluginRegistry()
    registry.register_extract_policy_plugin("task_line_parsing", _FailingPlugin)

    caplog.set_level(logging.WARNING, logger="prism.scanner_plugins.defaults")
    plugin = resolve_task_line_parsing_policy_plugin(
        di=None,
        strict_mode=False,
        registry=registry,
    )

    assert isinstance(plugin, AnsibleDefaultTaskLineParsingPolicyPlugin)
    assert any(
        "Failed to construct" in record.message and "falling back" in record.message
        for record in caplog.records
    )


def test_blocker_fact_builder_resolver_exposes_runtime_protocol_contract() -> None:
    class _DI:
        pass

    assert (
        resolve_blocker_fact_builder.__annotations__["return"] == "BlockerFactBuilder"
    )

    builder = resolve_blocker_fact_builder()
    result = builder(
        scan_options=_scan_options("roles/example"),
        metadata={"features": {"yaml_like_task_annotations": 2}},
        di=_DI(),
    )

    expected: dict[str, Any] = {
        "dynamic_includes": {
            "enabled": False,
            "task_count": 0,
            "role_count": 0,
            "total_count": 0,
        },
        "yaml_like_annotations": {
            "enabled": False,
            "count": 0,
        },
        "provenance": {
            "role_path": "roles/example",
            "exclude_path_patterns": None,
            "metadata_feature_source": "metadata.features.yaml_like_task_annotations",
            "dynamic_include_sources": [
                "scanner_plugins.audit.dynamic_include_audit.collect_unconstrained_dynamic_task_includes",
                "scanner_plugins.audit.dynamic_include_audit.collect_unconstrained_dynamic_role_includes",
            ],
        },
    }
    assert result == expected
