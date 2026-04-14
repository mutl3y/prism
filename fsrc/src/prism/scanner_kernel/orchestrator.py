"""Kernel orchestration helpers for plugin-based scanner execution."""

from __future__ import annotations

from typing import Any, Callable

from prism.errors import PrismRuntimeError
from prism.scanner_plugins import DEFAULT_PLUGIN_REGISTRY


def resolve_scan_pipeline_plugin_class(
    *,
    registry: Any,
    plugin_name: str,
) -> Any | None:
    """Resolve a scan-pipeline plugin class from a registry."""
    return registry.get_scan_pipeline_plugin(plugin_name)


def execute_scan_pipeline_plugin(
    *,
    plugin_class: Any,
    scan_options: dict[str, Any],
    scan_context: dict[str, Any],
) -> Any:
    """Instantiate and execute a scan-pipeline plugin."""
    plugin_instance = plugin_class()
    return plugin_instance.process_scan_pipeline(
        scan_options=dict(scan_options),
        scan_context=dict(scan_context),
    )


def _resolve_default_scan_pipeline_plugin_name(registry: Any) -> str:
    list_plugins = getattr(registry, "list_scan_pipeline_plugins", None)
    get_plugin = getattr(registry, "get_scan_pipeline_plugin", None)

    if callable(list_plugins):
        registered = [
            name for name in list_plugins() if isinstance(name, str) and name.strip()
        ]
        if "default" in registered:
            return "default"
        if len(registered) == 1:
            return registered[0]
        if registered:
            return sorted(registered)[0]

    if callable(get_plugin):
        if get_plugin("default") is not None:
            return "default"
        return "default"

    raise PrismRuntimeError(
        code="scan_pipeline_default_unavailable",
        category="runtime",
        message="no scan-pipeline plugin default is registered",
        detail={"registry_type": type(registry).__name__},
    )


def resolve_scan_pipeline_plugin_name(
    *,
    scan_options: dict[str, Any],
    registry: Any | None = None,
) -> str:
    """Resolve the scan-pipeline plugin selector from canonical scan options."""
    configured = scan_options.get("scan_pipeline_plugin")
    if isinstance(configured, str) and configured.strip():
        return configured.strip()

    platform = scan_options.get("platform")
    if isinstance(platform, str) and platform.strip():
        return platform.strip()

    registry_obj = registry or DEFAULT_PLUGIN_REGISTRY
    return _resolve_default_scan_pipeline_plugin_name(registry_obj)


def route_scan_payload_orchestration(
    *,
    role_path: str,
    scan_options: dict[str, Any],
    legacy_orchestrator_fn: Callable[..., dict[str, Any]],
    kernel_orchestrator_fn: Callable[..., dict[str, Any]] | None = None,
    registry: Any | None = None,
) -> dict[str, Any]:
    """Route orchestration using registered scan-pipeline plugin decision context."""
    if not callable(kernel_orchestrator_fn):
        return legacy_orchestrator_fn(role_path=role_path, scan_options=scan_options)

    registry_obj = registry or DEFAULT_PLUGIN_REGISTRY
    plugin_name = "default"

    try:
        plugin_name = resolve_scan_pipeline_plugin_name(
            scan_options=scan_options,
            registry=registry_obj,
        )
        plugin_class = resolve_scan_pipeline_plugin_class(
            registry=registry_obj,
            plugin_name=plugin_name,
        )
        if plugin_class is None:
            return legacy_orchestrator_fn(
                role_path=role_path, scan_options=scan_options
            )

        plugin_context = execute_scan_pipeline_plugin(
            plugin_class=plugin_class,
            scan_options=dict(scan_options),
            scan_context={"role_path": role_path},
        )
    except Exception as exc:
        strict_mode = bool(scan_options.get("strict_phase_failures", True))
        if strict_mode:
            raise PrismRuntimeError(
                code="scan_pipeline_router_failed",
                category="runtime",
                message="scan-pipeline router failed during plugin preflight",
                detail={"plugin": plugin_name, "error": str(exc)},
            ) from exc
        return legacy_orchestrator_fn(role_path=role_path, scan_options=scan_options)

    if isinstance(plugin_context, dict):
        plugin_enabled = plugin_context.get("plugin_enabled")
        if plugin_enabled is None:
            plugin_enabled = plugin_context.get("ansible_plugin_enabled")
    else:
        plugin_enabled = None

    if plugin_enabled is None:
        plugin_enabled = bool(plugin_class is not None)

    if bool(plugin_enabled):
        kernel_scan_options = dict(scan_options)
        if isinstance(plugin_context, dict):
            preflight_context = dict(plugin_context)
            preflight_context.setdefault("plugin_name", plugin_name)
            kernel_scan_options["_scan_pipeline_preflight_context"] = preflight_context
        return kernel_orchestrator_fn(
            role_path=role_path,
            scan_options=kernel_scan_options,
        )

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
