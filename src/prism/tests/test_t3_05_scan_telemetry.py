"""T3-05: Structured scan telemetry tests."""

from __future__ import annotations

import io
import json

from prism.scanner_core.events import (
    ScanPhaseEvent,
    clear_default_listeners,
    get_default_listeners,
)
from prism.scanner_core.telemetry import (
    ScanTelemetry,
    TelemetryCollector,
    telemetry_session,
)
from prism.scanner_data.contracts_request import ScanOptionsDict


def _scan_options() -> ScanOptionsDict:
    return {
        "role_path": "/tmp/role",
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


def test_telemetry_collector_records_phase_durations() -> None:
    collector = TelemetryCollector()
    collector(ScanPhaseEvent(phase_name="feature_detection", kind="pre"))
    collector(ScanPhaseEvent(phase_name="feature_detection", kind="post"))
    collector(ScanPhaseEvent(phase_name="variable_discovery", kind="pre"))
    collector(ScanPhaseEvent(phase_name="variable_discovery", kind="post"))

    snapshot = collector.snapshot(plugin_key="ansible")
    assert snapshot["plugin_key"] == "ansible"
    assert snapshot["errors"] == []
    assert snapshot["scan_duration_ms"] >= 0
    phases = snapshot["phases"]
    assert [p["phase_name"] for p in phases] == [
        "feature_detection",
        "variable_discovery",
    ]
    for phase in phases:
        assert phase["duration_ms"] >= 0


def test_telemetry_collector_handles_post_without_pre() -> None:
    collector = TelemetryCollector()
    collector(ScanPhaseEvent(phase_name="orphan", kind="post"))
    snapshot = collector.snapshot()
    assert snapshot["phases"][0]["duration_ms"] == 0


def test_telemetry_session_registers_and_clears() -> None:
    clear_default_listeners()
    with telemetry_session() as collector:
        assert collector in get_default_listeners()
    assert collector not in get_default_listeners()


def test_telemetry_json_log_emits_records(monkeypatch) -> None:
    monkeypatch.setenv("PRISM_TELEMETRY_JSON_LOG", "1")
    buf = io.StringIO()
    collector = TelemetryCollector(log_stream=buf)
    collector(ScanPhaseEvent(phase_name="output_render", kind="pre"))
    collector(ScanPhaseEvent(phase_name="output_render", kind="post"))

    lines = [ln for ln in buf.getvalue().splitlines() if ln]
    assert len(lines) == 2
    pre = json.loads(lines[0])
    post = json.loads(lines[1])
    assert pre == {"phase": "output_render", "kind": "pre"}
    assert post["phase"] == "output_render"
    assert post["kind"] == "post"
    assert "duration_ms" in post


def test_telemetry_snapshot_typed_dict_shape() -> None:
    collector = TelemetryCollector()
    snapshot: ScanTelemetry = collector.snapshot()
    assert "scan_duration_ms" in snapshot
    assert "phases" in snapshot
    assert "errors" in snapshot
    assert "plugin_key" not in snapshot


def test_telemetry_collector_via_di_container_event_bus() -> None:
    from prism.scanner_core.di import DIContainer

    collector = TelemetryCollector()
    container = DIContainer(
        role_path="/tmp/role",
        scan_options=_scan_options(),
        event_listeners=[collector],
    )
    bus = container.factory_event_bus()
    with bus.phase("feature_detection"):
        pass
    snapshot = collector.snapshot()
    assert [p["phase_name"] for p in snapshot["phases"]] == ["feature_detection"]
