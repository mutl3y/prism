"""Kernel orchestration helpers for plugin-based scanner execution."""

from __future__ import annotations

from typing import Any, Callable

from prism.scanner_plugins.ansible import is_ansible_plugin_enabled


def route_scan_payload_orchestration(
    *,
    role_path: str,
    scan_options: dict[str, Any],
    legacy_orchestrator_fn: Callable[..., dict[str, Any]],
    kernel_orchestrator_fn: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Route scan payload orchestration using the ansible plugin flag."""
    if is_ansible_plugin_enabled() and callable(kernel_orchestrator_fn):
        return kernel_orchestrator_fn(role_path=role_path, scan_options=scan_options)
    return legacy_orchestrator_fn(role_path=role_path, scan_options=scan_options)


def run_kernel_plugin_orchestrator(
    *,
    platform: str,
    target_path: str,
    scan_options: dict[str, Any],
    load_plugin_fn: Callable[[str], Any],
    scan_id: str = "kernel-scan",
    fail_fast: bool = True,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute baseline lifecycle phases on a loaded kernel plugin."""
    request: dict[str, Any] = {
        "scan_id": scan_id,
        "platform": platform,
        "target_path": target_path,
        "options": dict(scan_options),
    }
    if isinstance(context, dict):
        request["context"] = dict(context)

    response: dict[str, Any] = {
        "scan_id": scan_id,
        "platform": platform,
        "phase_results": {},
        "metadata": {"kernel_orchestrator": "fsrc-v1"},
    }

    plugin = load_plugin_fn(platform)
    phases = ("prepare", "scan", "analyze", "finalize")

    for phase in phases:
        handler = getattr(plugin, phase, None)
        if not callable(handler):
            response["phase_results"][phase] = {"phase": phase, "status": "skipped"}
            continue

        try:
            if phase in {"prepare", "scan"}:
                phase_output = handler(request)
            else:
                phase_output = handler(request, response)
        except Exception as exc:
            error_envelope = {
                "code": "KERNEL_PLUGIN_PHASE_FAILED",
                "message": str(exc),
                "phase": phase,
                "recoverable": not fail_fast,
            }
            response.setdefault("errors", []).append(error_envelope)
            response["phase_results"][phase] = {
                "phase": phase,
                "status": "failed",
                "error": error_envelope,
            }
            if fail_fast:
                break
            continue

        _merge_phase_output(response=response, phase=phase, phase_output=phase_output)
        response["phase_results"][phase] = {"phase": phase, "status": "completed"}

    return response


def _merge_phase_output(
    *,
    response: dict[str, Any],
    phase: str,
    phase_output: Any,
) -> None:
    if not isinstance(phase_output, dict):
        return

    if phase == "scan" and "payload" not in phase_output:
        response["payload"] = dict(phase_output)

    payload = phase_output.get("payload")
    if isinstance(payload, dict):
        response["payload"] = dict(payload)

    metadata = phase_output.get("metadata")
    if isinstance(metadata, dict):
        response.setdefault("metadata", {}).update(metadata)

    for key in ("warnings", "errors", "provenance"):
        value = phase_output.get(key)
        if isinstance(value, list):
            response.setdefault(key, []).extend(value)


def build_stable_field_parity_report(
    *,
    legacy_payload: dict[str, Any],
    kernel_payload: dict[str, Any],
    stable_fields: tuple[str, ...],
) -> dict[str, Any]:
    """Compare stable fields and summarize parity mismatches."""
    mismatches: list[dict[str, Any]] = []
    for field_path in stable_fields:
        legacy_value = _resolve_field(legacy_payload, field_path)
        kernel_value = _resolve_field(kernel_payload, field_path)
        if legacy_value != kernel_value:
            mismatches.append(
                {
                    "field": field_path,
                    "legacy_value": legacy_value,
                    "kernel_value": kernel_value,
                }
            )

    return {
        "stable_fields": list(stable_fields),
        "total_fields": len(stable_fields),
        "matched_fields": len(stable_fields) - len(mismatches),
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


def parity_report_within_threshold(
    *,
    parity_report: dict[str, Any],
    max_mismatches: int,
) -> bool:
    """Return True when mismatch_count is less than or equal to max_mismatches."""
    mismatch_count = parity_report.get("mismatch_count", 0)
    return int(mismatch_count) <= max_mismatches


def _resolve_field(payload: dict[str, Any], field_path: str) -> Any:
    current: Any = payload
    for segment in field_path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current[segment]
    return current
