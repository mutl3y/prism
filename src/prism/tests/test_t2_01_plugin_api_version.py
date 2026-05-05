"""T2-01: Plugin API versioning + compatibility enforcement tests."""

from __future__ import annotations

import pytest

from prism.scanner_plugins import (
    PRISM_PLUGIN_API_VERSION,
    PluginAPIVersionMismatch,
    validate_plugin_api_version,
)
from prism.scanner_plugins.registry import PluginRegistry


def test_constant_is_two_int_tuple() -> None:
    assert isinstance(PRISM_PLUGIN_API_VERSION, tuple)
    assert len(PRISM_PLUGIN_API_VERSION) == 2
    assert all(isinstance(p, int) for p in PRISM_PLUGIN_API_VERSION)


def test_validate_accepts_plugin_without_attribute() -> None:
    class _NoVersionPlugin:
        pass

    validate_plugin_api_version(_NoVersionPlugin, name="x", slot="any")


def test_validate_accepts_matching_major_and_lesser_or_equal_minor() -> None:
    class _Plugin:
        PRISM_PLUGIN_API_VERSION = (1, 0)

    validate_plugin_api_version(_Plugin, name="x", slot="any", core_version=(1, 5))


def test_validate_rejects_mismatched_major() -> None:
    class _Plugin:
        PRISM_PLUGIN_API_VERSION = (2, 0)

    with pytest.raises(PluginAPIVersionMismatch, match="2.0"):
        validate_plugin_api_version(
            _Plugin, name="future", slot="variable_discovery", core_version=(1, 0)
        )


def test_validate_rejects_minor_higher_than_core() -> None:
    class _Plugin:
        PRISM_PLUGIN_API_VERSION = (1, 9)

    with pytest.raises(PluginAPIVersionMismatch, match="1.9"):
        validate_plugin_api_version(
            _Plugin, name="newer", slot="scan_pipeline", core_version=(1, 0)
        )


def test_validate_rejects_malformed_attribute() -> None:
    class _Plugin:
        PRISM_PLUGIN_API_VERSION = "1.0"

    with pytest.raises(PluginAPIVersionMismatch, match="invalid"):
        validate_plugin_api_version(_Plugin, name="bad", slot="any")


def test_registry_enforces_version_on_scan_pipeline_plugin() -> None:
    reg = PluginRegistry()

    class _BadPlugin:
        PRISM_PLUGIN_API_VERSION = (99, 0)

        def process_scan_pipeline(self, scan_options, scan_context):
            return {}

    with pytest.raises(PluginAPIVersionMismatch):
        reg.register_scan_pipeline_plugin("bad", _BadPlugin)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "method",
    [
        "register_variable_discovery_plugin",
        "register_feature_detection_plugin",
        "register_output_orchestration_plugin",
        "register_scan_pipeline_plugin",
        "register_comment_driven_doc_plugin",
        "register_extract_policy_plugin",
        "register_yaml_parsing_policy_plugin",
        "register_jinja_analysis_policy_plugin",
    ],
)
def test_all_register_methods_validate_version(method: str) -> None:
    reg = PluginRegistry()

    class _BadPlugin:
        PRISM_PLUGIN_API_VERSION = (2, 0)

    with pytest.raises(PluginAPIVersionMismatch):
        getattr(reg, method)("bad", _BadPlugin)


def test_registry_accepts_plugin_with_matching_version() -> None:
    reg = PluginRegistry()

    class _GoodPlugin:
        PRISM_PLUGIN_API_VERSION = PRISM_PLUGIN_API_VERSION
        PLUGIN_IS_STATELESS = True

    reg.register_scan_pipeline_plugin("good", _GoodPlugin)  # type: ignore[arg-type]
    assert "good" in reg.list_scan_pipeline_plugins()


def test_default_bootstrap_plugins_register_without_error() -> None:
    """Smoke: importing scanner_plugins must not raise version errors."""
    from prism.api_layer.plugin_facade import get_default_plugin_registry

    default_plugin_registry = get_default_plugin_registry()

    assert "default" in default_plugin_registry.list_scan_pipeline_plugins()
    assert "ansible" in default_plugin_registry.list_scan_pipeline_plugins()
