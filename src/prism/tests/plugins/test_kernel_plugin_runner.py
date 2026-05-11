"""Branch-focused tests for scanner_kernel.kernel_plugin_runner."""

from __future__ import annotations

from typing import Any
from typing import cast

from prism.scanner_core.protocols_runtime import KernelPhaseFailure, KernelResponse
from prism.scanner_kernel.kernel_plugin_runner import run_kernel_plugin_orchestrator


def _first_error(response: KernelResponse) -> KernelPhaseFailure:
    errors = response.get("errors")
    if not isinstance(errors, list) or not errors or not isinstance(errors[0], dict):
        raise AssertionError("expected kernel error payload")
    return cast(KernelPhaseFailure, errors[0])


class _PluginMissingAnalyzeFinalize:
    def prepare(self, request: dict[str, Any]) -> dict[str, Any]:
        del request
        return {}

    def scan(self, request: dict[str, Any]) -> dict[str, Any]:
        del request
        return {"payload": {"items": [1]}}


class _PluginFailingPrepare:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def prepare(self, request: dict[str, Any]) -> dict[str, Any]:
        del request
        self._events.append("prepare")
        raise RuntimeError("prepare failed")

    def scan(self, request: dict[str, Any]) -> dict[str, Any]:
        del request
        self._events.append("scan")
        return {}

    def analyze(
        self, request: dict[str, Any], response: dict[str, Any]
    ) -> dict[str, Any]:
        del request
        del response
        self._events.append("analyze")
        return {}

    def finalize(
        self, request: dict[str, Any], response: dict[str, Any]
    ) -> dict[str, Any]:
        del request
        del response
        self._events.append("finalize")
        return {}


class _PluginMergeOutputs:
    def prepare(self, request: dict[str, Any]) -> dict[str, Any]:
        del request
        return {
            "metadata": {"prepare": "ok"},
            "warnings": ["warn-prepare"],
            "provenance": ["prov-prepare"],
        }

    def scan(self, request: dict[str, Any]) -> dict[str, Any]:
        del request
        return {
            "payload": {"resource_count": 3},
            "metadata": {"scan": "ok"},
            "warnings": ["warn-scan"],
            "errors": ["soft-scan-error"],
            "provenance": ["prov-scan"],
        }

    def analyze(
        self, request: dict[str, Any], response: dict[str, Any]
    ) -> dict[str, Any]:
        del request
        del response
        return {
            "metadata": {"analyze": "ok"},
            "warnings": ["warn-analyze"],
        }

    def finalize(
        self, request: dict[str, Any], response: dict[str, Any]
    ) -> dict[str, Any]:
        del request
        del response
        return {
            "metadata": {"finalize": "ok"},
            "provenance": ["prov-finalize"],
        }


class _PluginReusingResponseMetadata:
    def __init__(self) -> None:
        self.shared_metadata: dict[str, Any] | None = None

    def prepare(self, request: dict[str, Any]) -> dict[str, Any]:
        del request
        return {"metadata": {"prepare": "ok"}}

    def scan(self, request: dict[str, Any]) -> dict[str, Any]:
        del request
        return {"metadata": {"scan": "ok"}}

    def analyze(
        self, request: dict[str, Any], response: dict[str, Any]
    ) -> dict[str, Any]:
        del request
        metadata = response.get("metadata")
        if not isinstance(metadata, dict):
            raise AssertionError("expected response metadata")
        self.shared_metadata = metadata
        return {"metadata": {"analyze": "ok"}}


def test_run_kernel_plugin_orchestrator_marks_missing_phase_handlers_as_skipped() -> (
    None
):
    response = run_kernel_plugin_orchestrator(
        platform="ansible",
        target_path="/tmp/role",
        scan_options={},
        load_plugin_fn=lambda _platform: _PluginMissingAnalyzeFinalize(),
    )

    assert response["phase_results"]["prepare"]["status"] == "completed"
    assert response["phase_results"]["scan"]["status"] == "completed"
    assert response["phase_results"]["analyze"]["status"] == "skipped"
    assert response["phase_results"]["finalize"]["status"] == "skipped"


def test_run_kernel_plugin_orchestrator_stops_on_failed_phase_when_fail_fast_true() -> (
    None
):
    events: list[str] = []

    response = run_kernel_plugin_orchestrator(
        platform="ansible",
        target_path="/tmp/role",
        scan_options={},
        load_plugin_fn=lambda _platform: _PluginFailingPrepare(events),
        fail_fast=True,
    )

    assert events == ["prepare"]
    assert response["phase_results"]["prepare"]["status"] == "failed"
    assert "scan" not in response["phase_results"]
    assert _first_error(response)["recoverable"] is False


def test_run_kernel_plugin_orchestrator_continues_after_failure_when_fail_fast_false() -> (
    None
):
    """When fail_fast=False, downstream phases are SKIPPED (not executed).

    This test verifies the fail-per-plugin semantics: when a phase fails and
    fail_fast=False, the plugin marks the error as recoverable but DOES NOT
    execute downstream phases because phases are stateful and depend on
    successful upstream execution.

    Old behavior (BROKEN): events == ["prepare", "scan", "analyze", "finalize"]
    New behavior (CORRECT): events == ["prepare"] only
    """
    events: list[str] = []

    response = run_kernel_plugin_orchestrator(
        platform="ansible",
        target_path="/tmp/role",
        scan_options={},
        load_plugin_fn=lambda _platform: _PluginFailingPrepare(events),
        fail_fast=False,
    )

    assert events == ["prepare"], "Downstream phases must not execute after failure"
    assert response["phase_results"]["prepare"]["status"] == "failed"

    assert (
        response["phase_results"]["scan"]["status"] == "skipped_due_to_upstream_failure"
    )
    assert (
        "upstream" in response["phase_results"]["scan"]["reason"].lower()
    ), "Must explain why scan was skipped"

    assert (
        response["phase_results"]["analyze"]["status"]
        == "skipped_due_to_upstream_failure"
    )
    assert (
        response["phase_results"]["finalize"]["status"]
        == "skipped_due_to_upstream_failure"
    )

    error = _first_error(response)
    assert error["recoverable"] is True, "Error should be recoverable"
    assert error["phase"] == "prepare", "Error should identify failed phase"


def test_run_kernel_plugin_orchestrator_merges_phase_payload_metadata_and_lists() -> (
    None
):
    response = run_kernel_plugin_orchestrator(
        platform="ansible",
        target_path="/tmp/role",
        scan_options={},
        load_plugin_fn=lambda _platform: _PluginMergeOutputs(),
    )

    assert response["payload"] == {"resource_count": 3}
    assert response["metadata"] == {
        "kernel_orchestrator": "fsrc-v1",
        "prepare": "ok",
        "scan": "ok",
        "analyze": "ok",
        "finalize": "ok",
    }
    assert response["warnings"] == ["warn-prepare", "warn-scan", "warn-analyze"]
    assert response["errors"] == ["soft-scan-error"]
    assert response["provenance"] == ["prov-prepare", "prov-scan", "prov-finalize"]


def test_run_kernel_plugin_orchestrator_does_not_mutate_shared_response_metadata() -> (
    None
):
    plugin = _PluginReusingResponseMetadata()

    response = run_kernel_plugin_orchestrator(
        platform="ansible",
        target_path="/tmp/role",
        scan_options={},
        load_plugin_fn=lambda _platform: plugin,
    )

    assert plugin.shared_metadata == {
        "kernel_orchestrator": "fsrc-v1",
        "prepare": "ok",
        "scan": "ok",
    }
    assert response["metadata"] == {
        "kernel_orchestrator": "fsrc-v1",
        "prepare": "ok",
        "scan": "ok",
        "analyze": "ok",
    }
    assert plugin.shared_metadata is not response["metadata"]


# ============================================================================
# CASCADE FAILURE TESTS (CF005 Resolution)
# ============================================================================


class _PluginFailingScan:
    """Plugin that fails at scan phase to test mid-pipeline cascade."""

    def __init__(self, events: list[str]) -> None:
        self._events = events

    def prepare(self, request: dict[str, Any]) -> dict[str, Any]:
        del request
        self._events.append("prepare")
        return {"metadata": {"prepare": "success"}}

    def scan(self, request: dict[str, Any]) -> dict[str, Any]:
        del request
        self._events.append("scan")
        raise RuntimeError("scan phase encountered corrupt state")

    def analyze(
        self, request: dict[str, Any], response: dict[str, Any]
    ) -> dict[str, Any]:
        del request
        del response
        self._events.append("analyze")
        return {}

    def finalize(
        self, request: dict[str, Any], response: dict[str, Any]
    ) -> dict[str, Any]:
        del request
        del response
        self._events.append("finalize")
        return {}


class _PluginFailingAnalyze:
    """Plugin that fails at analyze phase to test late-stage cascade."""

    def __init__(self, events: list[str]) -> None:
        self._events = events

    def prepare(self, request: dict[str, Any]) -> dict[str, Any]:
        del request
        self._events.append("prepare")
        return {}

    def scan(self, request: dict[str, Any]) -> dict[str, Any]:
        del request
        self._events.append("scan")
        return {"payload": {"scanned": True}}

    def analyze(
        self, request: dict[str, Any], response: dict[str, Any]
    ) -> dict[str, Any]:
        del request
        del response
        self._events.append("analyze")
        raise RuntimeError("analysis failed on scan output")

    def finalize(
        self, request: dict[str, Any], response: dict[str, Any]
    ) -> dict[str, Any]:
        del request
        del response
        self._events.append("finalize")
        return {}


def test_cascade_failure_scan_phase_blocks_analyze_and_finalize() -> None:
    """When scan fails, analyze and finalize must NOT execute (cascade blocked)."""
    events: list[str] = []

    response = run_kernel_plugin_orchestrator(
        platform="ansible",
        target_path="/tmp/role",
        scan_options={},
        load_plugin_fn=lambda _platform: _PluginFailingScan(events),
        fail_fast=False,
    )

    assert events == [
        "prepare",
        "scan",
    ], "Only prepare and scan should execute; analyze/finalize blocked"
    assert response["phase_results"]["prepare"]["status"] == "completed"
    assert response["phase_results"]["scan"]["status"] == "failed"
    assert (
        response["phase_results"]["analyze"]["status"]
        == "skipped_due_to_upstream_failure"
    )
    assert (
        response["phase_results"]["finalize"]["status"]
        == "skipped_due_to_upstream_failure"
    )


def test_cascade_failure_analyze_phase_blocks_finalize() -> None:
    """When analyze fails, finalize must NOT execute (respects dependency)."""
    events: list[str] = []

    response = run_kernel_plugin_orchestrator(
        platform="ansible",
        target_path="/tmp/role",
        scan_options={},
        load_plugin_fn=lambda _platform: _PluginFailingAnalyze(events),
        fail_fast=False,
    )

    assert events == [
        "prepare",
        "scan",
        "analyze",
    ], "prepare/scan/analyze execute; finalize blocked"
    assert response["phase_results"]["prepare"]["status"] == "completed"
    assert response["phase_results"]["scan"]["status"] == "completed"
    assert response["phase_results"]["analyze"]["status"] == "failed"
    assert (
        response["phase_results"]["finalize"]["status"]
        == "skipped_due_to_upstream_failure"
    )


def test_cascade_failure_fail_fast_true_breaks_immediately() -> None:
    """When fail_fast=True, execution stops immediately (no cascade, no downstream)."""
    events: list[str] = []

    response = run_kernel_plugin_orchestrator(
        platform="ansible",
        target_path="/tmp/role",
        scan_options={},
        load_plugin_fn=lambda _platform: _PluginFailingScan(events),
        fail_fast=True,
    )

    assert events == ["prepare", "scan"], "Execution stops at first failure"
    assert response["phase_results"]["prepare"]["status"] == "completed"
    assert response["phase_results"]["scan"]["status"] == "failed"
    assert "analyze" not in response["phase_results"], "No downstream phase results"
    assert "finalize" not in response["phase_results"], "No downstream phase results"
    assert _first_error(response)["recoverable"] is False


def test_cascade_failure_phase_dependency_reasoning_in_response() -> None:
    """Verify that skipped phases include explicit dependency reasoning."""
    events: list[str] = []

    response = run_kernel_plugin_orchestrator(
        platform="ansible",
        target_path="/tmp/role",
        scan_options={},
        load_plugin_fn=lambda _platform: _PluginFailingPrepare(events),
        fail_fast=False,
    )

    scan_result = response["phase_results"]["scan"]
    assert scan_result["status"] == "skipped_due_to_upstream_failure"
    assert "reason" in scan_result
    assert "upstream" in scan_result["reason"].lower()
    assert "phase" in scan_result["reason"].lower()
