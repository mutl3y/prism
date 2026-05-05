"""Branch-focused tests for scanner_kernel.plugin_name_resolver."""

from __future__ import annotations

from typing import cast

import pytest

from prism.scanner_data.contracts_request import ScanMetadata, ScanOptionsDict
from prism.scanner_kernel.plugin_name_resolver import resolve_scan_pipeline_plugin_name


class _Plugin:
    def process_scan_pipeline(
        self,
        *,
        scan_options: ScanOptionsDict,
        scan_context: ScanMetadata,
    ) -> ScanMetadata:
        del scan_options
        return scan_context


class _Registry:
    def __init__(self, plugin_names: list[str]) -> None:
        self._plugin_names = plugin_names

    def list_scan_pipeline_plugins(self) -> list[str]:
        return list(self._plugin_names)

    def get_scan_pipeline_plugin(self, plugin_name: str) -> type[_Plugin] | None:
        if plugin_name in self._plugin_names:
            return _Plugin
        return None

    def get_default_platform_key(self) -> str | None:
        return None


def _scan_options(**overrides: object) -> ScanOptionsDict:
    return cast(
        ScanOptionsDict,
        {
            "role_path": "/tmp/role",
            "role_name_override": None,
            "readme_config_path": None,
            "policy_config_path": None,
            "include_vars_main": True,
            "exclude_path_patterns": None,
            "detailed_catalog": False,
            "include_task_parameters": True,
            "include_task_runbooks": True,
            "inline_task_runbooks": True,
            "include_collection_checks": False,
            "keep_unknown_style_sections": True,
            "adopt_heading_mode": None,
            "vars_seed_paths": None,
            "style_readme_path": None,
            "style_source_path": None,
            "style_guide_skeleton": False,
            "compare_role_path": None,
            "fail_on_unconstrained_dynamic_includes": None,
            "fail_on_yaml_like_task_annotations": None,
            "ignore_unresolved_internal_underscore_references": None,
            **overrides,
        },
    )


def test_resolve_plugin_name_prefers_explicit_scan_pipeline_plugin() -> None:
    result = resolve_scan_pipeline_plugin_name(
        scan_options=_scan_options(scan_pipeline_plugin="  custom  "),
        registry=_Registry(["default"]),
    )

    assert result == "custom"


def test_resolve_plugin_name_uses_policy_context_selection_plugin() -> None:
    result = resolve_scan_pipeline_plugin_name(
        scan_options=_scan_options(
            policy_context={"selection": {"plugin": "  policy_plugin  "}},
        ),
        registry=_Registry(["default"]),
    )

    assert result == "policy_plugin"


def test_resolve_plugin_name_falls_back_to_platform() -> None:
    result = resolve_scan_pipeline_plugin_name(
        scan_options=cast(
            ScanOptionsDict, {**_scan_options(), "platform": "  kubernetes  "}
        ),
        registry=_Registry(["default"]),
    )

    assert result == "kubernetes"


def test_resolve_plugin_name_uses_default_plugin_when_present() -> None:
    result = resolve_scan_pipeline_plugin_name(
        scan_options=_scan_options(),
        registry=_Registry(["other", "default", "zeta"]),
    )

    assert result == "default"


def test_resolve_plugin_name_uses_single_registered_plugin_when_no_default() -> None:
    result = resolve_scan_pipeline_plugin_name(
        scan_options=_scan_options(),
        registry=_Registry(["only_plugin"]),
    )

    assert result == "only_plugin"


def test_resolve_plugin_name_uses_lexical_fallback_when_multiple_plugins() -> None:
    result = resolve_scan_pipeline_plugin_name(
        scan_options=_scan_options(),
        registry=_Registry(["zeta", "beta", "gamma"]),
    )

    assert result == "beta"


def test_resolve_plugin_name_errors_when_registry_missing_for_unresolved_selection() -> (
    None
):
    with pytest.raises(ValueError, match="registry must be provided"):
        resolve_scan_pipeline_plugin_name(scan_options=_scan_options())
