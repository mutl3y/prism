"""T3-01: scan phase event system tests."""

from __future__ import annotations

import pytest

from prism.scanner_core.events import (
    PHASE_FEATURE_DETECTION,
    PHASE_OUTPUT_RENDER,
    PHASE_VARIABLE_DISCOVERY,
    EventBus,
    ScanPhaseEvent,
)
from prism.scanner_data.contracts_request import ScanOptionsDict


def _scan_options() -> ScanOptionsDict:
    return {
        "role_path": "/tmp/x",
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


def test_scan_phase_event_validates_kind() -> None:
    with pytest.raises(ValueError, match="kind"):
        ScanPhaseEvent(phase_name="x", kind="bogus")


def test_scan_phase_event_requires_phase_name() -> None:
    with pytest.raises(ValueError, match="phase_name"):
        ScanPhaseEvent(phase_name="", kind="pre")


def test_event_bus_emit_with_no_listeners_is_noop() -> None:
    bus = EventBus()
    bus.emit(ScanPhaseEvent(phase_name="x", kind="pre"))
    assert bus.listener_count == 0


def test_subscribe_and_emit_dispatches_to_all_listeners() -> None:
    bus = EventBus()
    received_a: list[ScanPhaseEvent] = []
    received_b: list[ScanPhaseEvent] = []
    bus.subscribe(received_a.append)
    bus.subscribe(received_b.append)
    evt = ScanPhaseEvent(phase_name="p", kind="pre", context={"k": "v"})
    bus.emit(evt)
    assert received_a == [evt] and received_b == [evt]


def test_subscribe_rejects_non_callable() -> None:
    bus = EventBus()
    with pytest.raises(TypeError):
        bus.subscribe("not-callable")  # type: ignore[arg-type]


def test_unsubscribe_removes_listener() -> None:
    bus = EventBus()
    received: list[ScanPhaseEvent] = []
    bus.subscribe(received.append)
    bus.unsubscribe(received.append)
    bus.unsubscribe(received.append)  # idempotent
    bus.emit(ScanPhaseEvent(phase_name="p", kind="pre"))
    assert received == []


def test_phase_context_emits_pre_and_post() -> None:
    bus = EventBus()
    received: list[ScanPhaseEvent] = []
    bus.subscribe(received.append)
    with bus.phase("scan", context={"role": "r"}, metadata={"v": 1}):
        pass
    assert [e.kind for e in received] == ["pre", "post"]
    assert all(e.phase_name == "scan" for e in received)
    assert all(e.context == {"role": "r"} for e in received)
    assert all(e.metadata == {"v": 1} for e in received)


def test_phase_emits_post_even_on_exception() -> None:
    bus = EventBus()
    received: list[ScanPhaseEvent] = []
    bus.subscribe(received.append)

    class _Boom(RuntimeError):
        pass

    with pytest.raises(_Boom):
        with bus.phase("scan"):
            raise _Boom()
    assert [e.kind for e in received] == ["pre", "post"]


def test_listener_exception_does_not_break_emit() -> None:
    bus = EventBus()
    seen: list[ScanPhaseEvent] = []

    def bad(evt: ScanPhaseEvent) -> None:
        raise RuntimeError("listener failure")

    bus.subscribe(bad)
    bus.subscribe(seen.append)
    bus.emit(ScanPhaseEvent(phase_name="p", kind="pre"))
    assert len(seen) == 1


def test_di_container_exposes_event_bus() -> None:
    from prism.scanner_core.di import DIContainer

    received: list[ScanPhaseEvent] = []
    di = DIContainer(
        role_path="/tmp/x",
        scan_options=_scan_options(),
        event_listeners=[received.append],
    )
    bus = di.factory_event_bus()
    assert isinstance(bus, EventBus) and bus.listener_count == 1
    bus.emit(ScanPhaseEvent(phase_name="p", kind="pre"))
    assert len(received) == 1


def test_canonical_phase_constants_exist() -> None:
    assert PHASE_FEATURE_DETECTION == "feature_detection"
    assert PHASE_VARIABLE_DISCOVERY == "variable_discovery"
    assert PHASE_OUTPUT_RENDER == "output_render"


def test_feature_detector_emits_phase_events(tmp_path) -> None:
    from prism.scanner_core.di import DIContainer
    from prism.scanner_core.feature_detector import FeatureDetector

    received: list[ScanPhaseEvent] = []

    class _Plugin:
        def detect_features(self, role_path: str, options: dict) -> dict:
            return {"detected": True}

    di = DIContainer(
        role_path=str(tmp_path),
        scan_options=_scan_options(),
        event_listeners=[received.append],
    )
    di.inject_mock("feature_detection_plugin", _Plugin())
    fd = FeatureDetector(di, str(tmp_path), _scan_options())
    result = fd.detect()
    assert result == {"detected": True}
    phase_events = [e for e in received if e.phase_name == PHASE_FEATURE_DETECTION]
    assert [e.kind for e in phase_events] == ["pre", "post"]


def test_variable_discovery_emits_phase_events(tmp_path) -> None:
    from prism.scanner_core.di import DIContainer
    from prism.scanner_core.variable_discovery import VariableDiscovery

    received: list[ScanPhaseEvent] = []

    class _Plugin:
        def discover_static_variables(self, role_path: str, options: dict):
            return ()

        def discover_referenced_variables(self, role_path: str, options: dict):
            return frozenset()

    di = DIContainer(
        role_path=str(tmp_path),
        scan_options=_scan_options(),
        event_listeners=[received.append],
    )
    di.inject_mock("variable_discovery_plugin", _Plugin())
    vd = VariableDiscovery(di, str(tmp_path), _scan_options())
    vd.discover_static()
    vd.discover_referenced()

    var_events = [e for e in received if e.phase_name == PHASE_VARIABLE_DISCOVERY]
    assert [e.kind for e in var_events] == ["pre", "post", "pre", "post"]
    steps = [e.context.get("step") for e in var_events]
    assert steps == ["static", "static", "referenced", "referenced"]
