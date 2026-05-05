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


PROJECT_ROOT = Path(__file__).resolve().parents[3]
_WARNING_GUARDRAIL_FILES = (
    "src/prism/tests/test_t2_01_plugin_api_version.py::test_registry_accepts_plugin_with_matching_version",
    "src/prism/tests/test_t2_03_entry_point_discovery.py::test_discover_registers_plugin_via_entry_point",
    "src/prism/tests/test_di_registry_resolution.py::test_registry_get_default_platform_key_returns_explicit_default",
    "src/prism/tests/test_platform_routing_fail_closed.py::test_ansible_platform_routing_outcome_absent_on_normal_path",
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
