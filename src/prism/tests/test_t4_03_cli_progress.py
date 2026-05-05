"""T4-03: CLI streaming progress output tests."""

from __future__ import annotations

import io
import threading

from prism.progress import ProgressReporter, progress_reporter_enabled
from prism.scanner_core.di import DIContainer
from prism.scanner_core.events import (
    ScanPhaseEvent,
    clear_default_listeners,
    get_default_listeners,
    register_default_listener,
    unregister_default_listener,
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


def test_progress_reporter_writes_pre_post_to_stream() -> None:
    buf = io.StringIO()
    reporter = ProgressReporter(stream=buf)
    reporter(ScanPhaseEvent(phase_name="feature_detection", kind="pre"))
    reporter(ScanPhaseEvent(phase_name="feature_detection", kind="post"))
    out = buf.getvalue()
    assert "feature_detection: start" in out
    assert "feature_detection: done" in out
    assert "ms)" in out


def test_default_listener_registry_roundtrip() -> None:
    clear_default_listeners()
    try:
        assert get_default_listeners() == ()

        def listener(event: ScanPhaseEvent) -> None:
            return None

        register_default_listener(listener)
        assert listener in get_default_listeners()
        unregister_default_listener(listener)
        assert listener not in get_default_listeners()
        unregister_default_listener(listener)
    finally:
        clear_default_listeners()


def test_di_container_picks_up_default_listeners() -> None:
    clear_default_listeners()
    seen: list[ScanPhaseEvent] = []

    def listener(event: ScanPhaseEvent) -> None:
        seen.append(event)

    register_default_listener(listener)
    try:
        container = DIContainer(
            role_path="/tmp/role",
            scan_options=_scan_options(),
            inherit_default_event_listeners=True,
        )
        bus = container.factory_event_bus()
        assert bus.listener_count == 1
        with bus.phase("variable_discovery"):
            pass
        assert [e.kind for e in seen] == ["pre", "post"]
    finally:
        clear_default_listeners()


def test_di_container_inherited_default_listeners_are_bounded_to_construction() -> None:
    clear_default_listeners()
    seen: list[str] = []

    def first_listener(event: ScanPhaseEvent) -> None:
        seen.append(f"first:{event.kind}")

    def second_listener(event: ScanPhaseEvent) -> None:
        seen.append(f"second:{event.kind}")

    register_default_listener(first_listener)
    try:
        container = DIContainer(
            role_path="/tmp/role",
            scan_options=_scan_options(),
            inherit_default_event_listeners=True,
        )
        register_default_listener(second_listener)

        bus = container.factory_event_bus()
        assert bus.listener_count == 1
        with bus.phase("variable_discovery"):
            pass

        assert seen == ["first:pre", "first:post"]
    finally:
        clear_default_listeners()


def test_di_container_does_not_inherit_default_listeners_without_opt_in() -> None:
    clear_default_listeners()

    def listener(event: ScanPhaseEvent) -> None:
        return None

    register_default_listener(listener)
    try:
        container = DIContainer(role_path="/tmp/role", scan_options=_scan_options())
        assert container.factory_event_bus().listener_count == 0
    finally:
        clear_default_listeners()


def test_explicit_empty_listeners_overrides_defaults() -> None:
    clear_default_listeners()

    def listener(event: ScanPhaseEvent) -> None:
        return None

    register_default_listener(listener)
    try:
        container = DIContainer(
            role_path="/tmp/role",
            scan_options=_scan_options(),
            event_listeners=[],
            inherit_default_event_listeners=True,
        )
        assert container.factory_event_bus().listener_count == 0
    finally:
        clear_default_listeners()


def test_default_listener_registry_does_not_cross_thread_boundary() -> None:
    clear_default_listeners()
    observed: list[tuple[int, int]] = []

    def listener(event: ScanPhaseEvent) -> None:
        return None

    def worker() -> None:
        container = DIContainer(
            role_path="/tmp/role",
            scan_options=_scan_options(),
            inherit_default_event_listeners=True,
        )
        observed.append(
            (len(get_default_listeners()), container.factory_event_bus().listener_count)
        )

    register_default_listener(listener)
    try:
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        assert observed == [(0, 0)]
    finally:
        clear_default_listeners()


def test_progress_reporter_enabled_context_manager() -> None:
    clear_default_listeners()
    buf = io.StringIO()
    with progress_reporter_enabled(stream=buf) as reporter:
        assert reporter in get_default_listeners()
    assert reporter not in get_default_listeners()


def test_progress_reporter_non_callable_rejected() -> None:
    import pytest

    with pytest.raises(TypeError):
        register_default_listener("not-callable")  # type: ignore[arg-type]
