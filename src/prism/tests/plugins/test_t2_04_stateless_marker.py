"""T2-04: Stateless plugin marker + registry enforcement tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from prism.scanner_plugins.registry import (
    PluginRegistry,
    PluginStatelessRequired,
    require_stateless_plugin,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]


def _resolve_test_node(filename: str, test_name: str) -> str:
    test_root = PROJECT_ROOT / "src/prism/tests"
    matches = sorted(
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in test_root.rglob(filename)
        if path.is_file()
    )
    if len(matches) == 1:
        return f"{matches[0]}::{test_name}"
    if len(matches) > 1:
        raise FileNotFoundError(
            f"Ambiguous guardrail test file for {filename}: {matches}"
        )
    raise FileNotFoundError(f"Unable to locate test file for guardrail: {filename}")


_WARNING_GUARDRAIL_FILES = (
    _resolve_test_node(
        "test_t2_01_plugin_api_version.py",
        "test_registry_accepts_plugin_with_matching_version",
    ),
    _resolve_test_node(
        "test_t2_03_entry_point_discovery.py",
        "test_discover_registers_plugin_via_entry_point",
    ),
    _resolve_test_node(
        "test_di_registry_resolution.py",
        "test_registry_get_default_platform_key_returns_explicit_default",
    ),
    _resolve_test_node(
        "test_platform_routing_fail_closed.py",
        "test_ansible_platform_routing_outcome_absent_on_normal_path",
    ),
)


# ---- direct validator -----------------------------------------------------


def test_stateless_required_for_scan_pipeline_slot_with_explicit_false() -> None:
    class _Bad:
        PLUGIN_IS_STATELESS = False

    with pytest.raises(PluginStatelessRequired, match="scan_pipeline"):
        require_stateless_plugin(_Bad, name="bad", slot="scan_pipeline")


def test_stateless_required_accepts_explicit_true() -> None:
    class _Good:
        PLUGIN_IS_STATELESS = True

    require_stateless_plugin(_Good, name="good", slot="scan_pipeline")


def test_stateless_required_accepts_missing_marker_for_backward_compat() -> None:
    class _Old:
        pass

    with pytest.warns(UserWarning, match="does not declare PLUGIN_IS_STATELESS"):
        require_stateless_plugin(_Old, name="old", slot="scan_pipeline")


def test_stateless_check_skipped_for_non_singleton_slot() -> None:
    class _Stateful:
        PLUGIN_IS_STATELESS = False

    # Slot 'comment_driven_doc' is not in the required set; no exception.
    require_stateless_plugin(_Stateful, name="x", slot="comment_driven_doc")


def test_stateless_check_rejects_non_bool_marker_value() -> None:
    class _Weird:
        PLUGIN_IS_STATELESS = "yes"  # not a real bool

    with pytest.raises(PluginStatelessRequired):
        require_stateless_plugin(_Weird, name="weird", slot="scan_pipeline")


# ---- registry integration -------------------------------------------------


@pytest.mark.parametrize(
    "method",
    [
        "register_scan_pipeline_plugin",
        "register_extract_policy_plugin",
        "register_yaml_parsing_policy_plugin",
        "register_jinja_analysis_policy_plugin",
    ],
)
def test_registry_enforces_stateless_marker_on_required_slots(method: str) -> None:
    reg = PluginRegistry()

    class _Stateful:
        PLUGIN_IS_STATELESS = False

    with pytest.raises(PluginStatelessRequired):
        getattr(reg, method)("stateful", _Stateful)


def test_registry_accepts_stateless_marked_plugin() -> None:
    reg = PluginRegistry()

    class _GoodPlugin:
        PLUGIN_IS_STATELESS = True

        def process_scan_pipeline(self, scan_options, scan_context):
            return {}

    reg.register_scan_pipeline_plugin("good", _GoodPlugin)  # type: ignore[arg-type]
    assert "good" in reg.list_scan_pipeline_plugins()


def test_registry_does_not_enforce_stateless_for_feature_detection_slot() -> None:
    """feature_detection slot isn't in the stateless-required set today."""
    reg = PluginRegistry()

    class _Stateful:
        PLUGIN_IS_STATELESS = False

        def __init__(self, di: object | None = None) -> None:
            self.di = di

    # Should NOT raise.
    reg.register_feature_detection_plugin("ok", _Stateful)  # type: ignore[arg-type]
    assert "ok" in reg.list_feature_detection_plugins()


def test_resolve_test_node_finds_nested_moved_plugin_test(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    moved_test = (
        tmp_path / "src" / "prism" / "tests" / "plugins" / "moved" / "test_demo.py"
    )
    moved_test.parent.mkdir(parents=True)
    moved_test.write_text("def test_ok():\n    pass\n", encoding="utf-8")

    monkeypatch.setattr(f"{__name__}.PROJECT_ROOT", tmp_path)

    assert _resolve_test_node("test_demo.py", "test_ok") == (
        "src/prism/tests/plugins/moved/test_demo.py::test_ok"
    )


def test_bootstrap_custom_registry_reserves_future_platform_names_without_wiring_plugins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from prism import scanner_plugins
    from prism.scanner_plugins.registry import PluginRegistry

    registry = PluginRegistry()
    monkeypatch.setattr(scanner_plugins, "discover_entry_point_plugins", lambda **_: [])

    scanner_plugins.bootstrap_default_plugins(registry)

    assert registry.get_default_platform_key() == "ansible"
    assert registry.is_reserved_unsupported_platform("kubernetes") is True
    assert registry.is_reserved_unsupported_platform("terraform") is True
    assert registry.get_scan_pipeline_plugin("kubernetes") is None
    assert registry.get_scan_pipeline_plugin("terraform") is None


def test_register_platform_plugin_bundle_reserves_unsupported_platform_without_runtime_plugins() -> (
    None
):
    from prism.scanner_plugins.bootstrap import register_platform_plugin_bundle
    from prism.scanner_plugins.registry import PluginRegistry

    registry = PluginRegistry()

    register_platform_plugin_bundle(
        registry,
        platform_key="kubernetes",
        support_state="unsupported",
    )

    assert registry.is_reserved_unsupported_platform("kubernetes") is True
    assert registry.get_scan_pipeline_plugin("kubernetes") is None
    assert registry.get_variable_discovery_plugin("kubernetes") is None
    assert registry.get_feature_detection_plugin("kubernetes") is None
    assert registry.get_default_platform_key() is None


def test_register_platform_plugin_bundle_registers_supported_runtime_seams() -> None:
    from prism.scanner_plugins.bootstrap import register_platform_plugin_bundle
    from prism.scanner_plugins.registry import PluginRegistry

    registry = PluginRegistry()

    class _PlatformScanPipelinePlugin:
        PLUGIN_IS_STATELESS = True

        def process_scan_pipeline(self, scan_options, scan_context):
            return scan_context

    class _PlatformVariableDiscoveryPlugin:
        def __init__(self, di: object | None = None) -> None:
            self.di = di

    class _PlatformFeatureDetectionPlugin:
        def __init__(self, di: object | None = None) -> None:
            self.di = di

    register_platform_plugin_bundle(
        registry,
        platform_key="example",
        support_state="supported",
        scan_pipeline_plugin=_PlatformScanPipelinePlugin,
        variable_discovery_plugin=_PlatformVariableDiscoveryPlugin,
        feature_detection_plugin=_PlatformFeatureDetectionPlugin,
    )

    assert registry.is_reserved_unsupported_platform("example") is False
    assert registry.get_scan_pipeline_plugin("example") is _PlatformScanPipelinePlugin
    assert (
        registry.get_variable_discovery_plugin("example")
        is _PlatformVariableDiscoveryPlugin
    )
    assert (
        registry.get_feature_detection_plugin("example")
        is _PlatformFeatureDetectionPlugin
    )


def test_register_platform_plugin_bundle_registers_platform_default_providers() -> None:
    from prism.scanner_plugins.bootstrap import register_platform_plugin_bundle
    from prism.scanner_plugins.registry import PluginRegistry

    registry = PluginRegistry()
    sentinel = object()

    register_platform_plugin_bundle(
        registry,
        platform_key="example",
        support_state="supported",
        default_providers={"task_line_parsing_policy": lambda: sentinel},
    )

    provider = registry.get_platform_default_provider(
        "example",
        "task_line_parsing_policy",
    )

    assert provider is not None
    assert provider() is sentinel


def test_describe_platform_registration_state_activates_reserved_platform_only_after_all_runtime_seams() -> (
    None
):
    from prism.scanner_plugins.bootstrap import (
        describe_platform_registration_state,
        register_platform_plugin_bundle,
    )
    from prism.scanner_plugins.registry import PluginRegistry

    registry = PluginRegistry()

    class _PlatformScanPipelinePlugin:
        PLUGIN_IS_STATELESS = True

        def process_scan_pipeline(self, scan_options, scan_context):
            return scan_context

    class _PlatformVariableDiscoveryPlugin:
        def __init__(self, di: object | None = None) -> None:
            self.di = di

    class _PlatformFeatureDetectionPlugin:
        def __init__(self, di: object | None = None) -> None:
            self.di = di

    register_platform_plugin_bundle(
        registry,
        platform_key="kubernetes",
        support_state="unsupported",
        scan_pipeline_plugin=_PlatformScanPipelinePlugin,
        variable_discovery_plugin=_PlatformVariableDiscoveryPlugin,
    )

    assert (
        describe_platform_registration_state(registry, platform_key="kubernetes")
        == "reserved_partial"
    )

    register_platform_plugin_bundle(
        registry,
        platform_key="kubernetes",
        support_state="supported",
        feature_detection_plugin=_PlatformFeatureDetectionPlugin,
    )

    assert (
        describe_platform_registration_state(registry, platform_key="kubernetes")
        == "supported"
    )


def test_warning_prone_scan_pipeline_fixture_cluster_stays_warning_clean() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            *_WARNING_GUARDRAIL_FILES,
            "-W",
            "error::UserWarning",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, (
        "warning-clean stateless fixture guardrail failed\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )
