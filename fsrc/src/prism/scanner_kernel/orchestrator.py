"""Kernel orchestration helpers for plugin-based scanner execution."""

from __future__ import annotations

import copy
import inspect
from dataclasses import dataclass
from typing import Any, Callable

from prism.errors import PrismRuntimeError
from prism.scanner_plugins import DEFAULT_PLUGIN_REGISTRY


_SCAN_PIPELINE_SELECTION_ORDER: tuple[str, ...] = (
    "request.option.scan_pipeline_plugin",
    "policy_context.selection.plugin",
    "platform",
    "registry_default",
)

_ROUTING_MODE_PLUGIN = "scan_pipeline_plugin"
_ROUTING_MODE_LEGACY = "legacy_orchestrator"


@dataclass(frozen=True, slots=True)
class RoutePreflightRuntimeCarrier:
    """Explicit carrier for selected route, preflight result, and runtime metadata."""

    plugin_name: str
    preflight_context: dict[str, Any]
    routing: dict[str, Any]


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

    raise PrismRuntimeError(
        code="scan_pipeline_default_unavailable",
        category="runtime",
        message="no scan-pipeline plugin default is registered",
        detail={"registry_type": type(registry).__name__},
    )


def _resolve_policy_context_scan_pipeline_plugin_name(
    scan_options: dict[str, Any],
) -> str | None:
    policy_context = scan_options.get("policy_context")
    if not isinstance(policy_context, dict):
        return None

    selection_context = policy_context.get("selection")
    if not isinstance(selection_context, dict):
        return None

    plugin_name = selection_context.get("plugin")
    if not isinstance(plugin_name, str) or not plugin_name.strip():
        return None

    return plugin_name.strip()


def resolve_scan_pipeline_plugin_name(
    *,
    scan_options: dict[str, Any],
    registry: Any | None = None,
) -> str:
    """Resolve the scan-pipeline plugin selector from canonical scan options."""
    configured = scan_options.get("scan_pipeline_plugin")
    if isinstance(configured, str) and configured.strip():
        return configured.strip()

    configured_from_policy = _resolve_policy_context_scan_pipeline_plugin_name(
        scan_options
    )
    if configured_from_policy is not None:
        return configured_from_policy

    platform = scan_options.get("platform")
    if isinstance(platform, str) and platform.strip():
        return platform.strip()

    registry_obj = registry or DEFAULT_PLUGIN_REGISTRY
    return _resolve_default_scan_pipeline_plugin_name(registry_obj)


def _merge_metadata_preserving_existing(
    existing: dict[str, Any],
    incoming: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(existing)
    for key, value in incoming.items():
        if key not in merged:
            merged[key] = value
            continue

        existing_value = merged[key]
        if isinstance(existing_value, dict) and isinstance(value, dict):
            merged[key] = _merge_metadata_preserving_existing(existing_value, value)
    return merged


def _build_routing_metadata(
    *,
    mode: str | None = None,
    selected_plugin: str | None = None,
    failure_mode: str | None = None,
    fallback_reason: str | None = None,
    fallback_applied: bool | None = None,
    preflight_stage: str | None = None,
    exception_type: str | None = None,
    include_selection_order: bool = False,
) -> dict[str, Any]:
    routing: dict[str, Any] = {}
    if mode is not None:
        routing["mode"] = mode
    if include_selection_order:
        routing["selection_order"] = list(_SCAN_PIPELINE_SELECTION_ORDER)
    if selected_plugin is not None:
        routing["selected_plugin"] = selected_plugin
    if failure_mode is not None:
        routing["failure_mode"] = failure_mode
    if fallback_reason is not None:
        routing["fallback_reason"] = fallback_reason
    if fallback_applied is not None:
        routing["fallback_applied"] = fallback_applied
    if preflight_stage is not None:
        routing["preflight_stage"] = preflight_stage
    if exception_type is not None:
        routing["exception_type"] = exception_type
    return routing


def _merge_routing_metadata(
    existing: dict[str, Any] | None,
    incoming: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(existing) if isinstance(existing, dict) else {}
    merged.update(incoming)
    return merged


def _ensure_payload_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
        payload["metadata"] = metadata
    return metadata


def _apply_routing_metadata(
    *,
    payload: dict[str, Any],
    routing: dict[str, Any],
) -> dict[str, Any]:
    metadata = _ensure_payload_metadata(payload)
    metadata["routing"] = _merge_routing_metadata(metadata.get("routing"), routing)
    return metadata["routing"]


def _append_scan_pipeline_warning(
    *,
    payload: dict[str, Any],
    code: str,
    message: str,
    routing: dict[str, Any],
) -> dict[str, Any]:
    warning_metadata = _ensure_payload_metadata(payload)
    merged_routing = _apply_routing_metadata(payload=payload, routing=routing)
    existing_warnings = warning_metadata.get("plugin_runtime_warnings")
    warnings_list = (
        list(existing_warnings) if isinstance(existing_warnings, list) else []
    )
    warnings_list.append(
        {
            "code": code,
            "message": message,
            "metadata": {"routing": copy.deepcopy(merged_routing)},
        }
    )
    warning_metadata["plugin_runtime_warnings"] = warnings_list
    return payload


def _build_route_preflight_runtime_carrier(
    *,
    plugin_name: str,
    plugin_context: dict[str, Any] | None,
) -> RoutePreflightRuntimeCarrier:
    preflight_context = dict(plugin_context) if isinstance(plugin_context, dict) else {}
    preflight_context.setdefault("plugin_name", plugin_name)
    routing = _merge_routing_metadata(
        preflight_context.get("routing"),
        _build_routing_metadata(
            mode=_ROUTING_MODE_PLUGIN,
            selected_plugin=plugin_name,
            include_selection_order=True,
        ),
    )
    preflight_context["routing"] = routing
    return RoutePreflightRuntimeCarrier(
        plugin_name=plugin_name,
        preflight_context=preflight_context,
        routing=routing,
    )


def _invoke_kernel_orchestrator(
    *,
    kernel_orchestrator_fn: Callable[..., dict[str, Any]],
    role_path: str,
    scan_options: dict[str, Any],
    route_preflight_runtime: RoutePreflightRuntimeCarrier,
) -> dict[str, Any]:
    try:
        signature = inspect.signature(kernel_orchestrator_fn)
    except (TypeError, ValueError):
        return kernel_orchestrator_fn(role_path=role_path, scan_options=scan_options)

    accepts_route_preflight_runtime = "route_preflight_runtime" in signature.parameters
    accepts_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    if accepts_route_preflight_runtime or accepts_kwargs:
        return kernel_orchestrator_fn(
            role_path=role_path,
            scan_options=scan_options,
            route_preflight_runtime=route_preflight_runtime,
        )
    return kernel_orchestrator_fn(role_path=role_path, scan_options=scan_options)


def _routing_error_detail(routing: dict[str, Any]) -> dict[str, Any]:
    return {"metadata": {"routing": routing}}


def _raise_contract_error(
    *,
    code: str,
    message: str,
    routing: dict[str, Any],
    cause: Exception | None = None,
) -> None:
    raise PrismRuntimeError(
        code=code,
        category="runtime",
        message=message,
        detail=_routing_error_detail(routing),
    ) from cause


def _fallback_to_legacy_orchestrator(
    *,
    legacy_orchestrator_fn: Callable[..., dict[str, Any]],
    role_path: str,
    scan_options: dict[str, Any],
    warning_code: str,
    warning_message: str,
    routing: dict[str, Any],
) -> dict[str, Any]:
    payload = legacy_orchestrator_fn(role_path=role_path, scan_options=scan_options)
    return _append_scan_pipeline_warning(
        payload=payload,
        code=warning_code,
        message=warning_message,
        routing=routing,
    )


def _orchestrate_scan_payload_with_plugin_instance(
    *,
    plugin: Any,
    plugin_name: str,
    payload: dict[str, Any],
    scan_options: dict[str, Any],
    strict_mode: bool,
    preflight_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = payload.get("metadata")
    base_metadata = copy.deepcopy(metadata) if isinstance(metadata, dict) else {}

    if isinstance(preflight_context, dict):
        plugin_output: Any = dict(preflight_context)
    else:
        process_scan_pipeline = getattr(plugin, "process_scan_pipeline", None)
        if callable(process_scan_pipeline):
            plugin_output = process_scan_pipeline(
                scan_options=copy.deepcopy(scan_options),
                scan_context=copy.deepcopy(base_metadata),
            )
        else:
            plugin_output = {}

    if not isinstance(plugin_output, dict):
        return payload

    payload["metadata"] = _merge_metadata_preserving_existing(
        base_metadata,
        plugin_output,
    )
    return payload


def orchestrate_scan_payload_with_selected_plugin(
    *,
    build_payload_fn: Callable[[], dict[str, Any]],
    scan_options: dict[str, Any],
    strict_mode: bool,
    preflight_context: dict[str, Any] | None = None,
    route_preflight_runtime: RoutePreflightRuntimeCarrier | None = None,
    registry: Any | None = None,
) -> dict[str, Any]:
    payload = build_payload_fn()
    registry_obj = registry or DEFAULT_PLUGIN_REGISTRY
    plugin_name = "unresolved"
    existing_preflight_routing: dict[str, Any] = {}

    if route_preflight_runtime is not None:
        plugin_name = route_preflight_runtime.plugin_name
        preflight_context = dict(route_preflight_runtime.preflight_context)
        existing_preflight_routing = copy.deepcopy(route_preflight_runtime.routing)
        _apply_routing_metadata(payload=payload, routing=existing_preflight_routing)
    elif isinstance(preflight_context, dict):
        preflight_plugin_name = preflight_context.get("plugin_name")
        if isinstance(preflight_plugin_name, str) and preflight_plugin_name.strip():
            plugin_name = preflight_plugin_name.strip()
        preflight_routing = preflight_context.get("routing")
        if isinstance(preflight_routing, dict):
            existing_preflight_routing = copy.deepcopy(preflight_routing)
            _apply_routing_metadata(payload=payload, routing=existing_preflight_routing)

    try:
        if plugin_name == "unresolved":
            plugin_name = resolve_scan_pipeline_plugin_name(
                scan_options=scan_options,
                registry=registry_obj,
            )
        plugin_class = resolve_scan_pipeline_plugin_class(
            registry=registry_obj,
            plugin_name=plugin_name,
        )
    except Exception as exc:
        routing = _build_routing_metadata(
            failure_mode="runtime_execution_exception",
            selected_plugin=None if plugin_name == "unresolved" else plugin_name,
            fallback_reason="runtime_execution_exception" if not strict_mode else None,
            fallback_applied=True if not strict_mode else None,
        )
        if strict_mode:
            _raise_contract_error(
                code="scan_pipeline_execution_failed",
                message="scan-pipeline runtime execution failed",
                routing=routing,
                cause=exc,
            )

        return _append_scan_pipeline_warning(
            payload=payload,
            code="scan_pipeline_plugin_failed",
            message="scan-pipeline runtime execution failed",
            routing=_merge_routing_metadata(existing_preflight_routing, routing),
        )

    if plugin_class is None:
        return payload

    plugin_instance = plugin_class()
    orchestrate_scan_payload = getattr(
        plugin_instance, "orchestrate_scan_payload", None
    )
    try:
        if callable(orchestrate_scan_payload):
            result = orchestrate_scan_payload(
                payload=payload,
                scan_options=scan_options,
                strict_mode=strict_mode,
                preflight_context=preflight_context,
            )
        else:
            result = _orchestrate_scan_payload_with_plugin_instance(
                plugin=plugin_instance,
                plugin_name=plugin_name,
                payload=payload,
                scan_options=scan_options,
                strict_mode=strict_mode,
                preflight_context=preflight_context,
            )
    except Exception as exc:
        routing = _build_routing_metadata(
            failure_mode="runtime_execution_exception",
            selected_plugin=plugin_name,
            fallback_reason="runtime_execution_exception" if not strict_mode else None,
            fallback_applied=True if not strict_mode else None,
        )
        if strict_mode:
            _raise_contract_error(
                code="scan_pipeline_execution_failed",
                message="scan-pipeline runtime execution failed",
                routing=routing,
                cause=exc,
            )
        return _append_scan_pipeline_warning(
            payload=payload,
            code="scan_pipeline_plugin_failed",
            message="scan-pipeline runtime execution failed",
            routing=_merge_routing_metadata(existing_preflight_routing, routing),
        )

    if isinstance(result, dict) and existing_preflight_routing:
        _apply_routing_metadata(payload=result, routing=existing_preflight_routing)
    return result


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

    strict_mode = bool(scan_options.get("strict_phase_failures", True))
    registry_obj = registry or DEFAULT_PLUGIN_REGISTRY

    try:
        plugin_name = resolve_scan_pipeline_plugin_name(
            scan_options=scan_options,
            registry=registry_obj,
        )
    except PrismRuntimeError as exc:
        if exc.code != "scan_pipeline_default_unavailable":
            raise

        routing = _build_routing_metadata(
            mode=_ROUTING_MODE_LEGACY,
            failure_mode="registry_default_plugin_unavailable",
            include_selection_order=True,
        )
        if strict_mode:
            _raise_contract_error(
                code="scan_pipeline_default_unavailable",
                message=exc.message,
                routing=routing,
                cause=exc,
            )
        return _fallback_to_legacy_orchestrator(
            legacy_orchestrator_fn=legacy_orchestrator_fn,
            role_path=role_path,
            scan_options=scan_options,
            warning_code="scan_pipeline_default_unavailable",
            warning_message=exc.message,
            routing=_merge_routing_metadata(
                routing,
                _build_routing_metadata(
                    fallback_reason="registry_default_plugin_unavailable",
                    fallback_applied=True,
                ),
            ),
        )
    except Exception as exc:
        routing = _build_routing_metadata(
            mode=_ROUTING_MODE_LEGACY,
            failure_mode="registry_lookup_exception",
            include_selection_order=True,
            exception_type=type(exc).__name__,
        )
        if strict_mode:
            _raise_contract_error(
                code="scan_pipeline_router_failed",
                message="scan-pipeline router failed during route resolution",
                routing=routing,
                cause=exc,
            )
        return _fallback_to_legacy_orchestrator(
            legacy_orchestrator_fn=legacy_orchestrator_fn,
            role_path=role_path,
            scan_options=scan_options,
            warning_code="scan_pipeline_router_failed",
            warning_message="scan-pipeline router failed during route resolution",
            routing=_merge_routing_metadata(
                routing,
                _build_routing_metadata(
                    fallback_reason="registry_lookup_exception",
                    fallback_applied=True,
                ),
            ),
        )

    try:
        plugin_class = resolve_scan_pipeline_plugin_class(
            registry=registry_obj,
            plugin_name=plugin_name,
        )
    except Exception as exc:
        routing = _build_routing_metadata(
            mode=_ROUTING_MODE_LEGACY,
            selected_plugin=plugin_name,
            failure_mode="registry_lookup_exception",
            include_selection_order=True,
            exception_type=type(exc).__name__,
        )
        if strict_mode:
            _raise_contract_error(
                code="scan_pipeline_router_failed",
                message="scan-pipeline router failed during route resolution",
                routing=routing,
                cause=exc,
            )
        return _fallback_to_legacy_orchestrator(
            legacy_orchestrator_fn=legacy_orchestrator_fn,
            role_path=role_path,
            scan_options=scan_options,
            warning_code="scan_pipeline_router_failed",
            warning_message="scan-pipeline router failed during route resolution",
            routing=_merge_routing_metadata(
                routing,
                _build_routing_metadata(
                    fallback_reason="registry_lookup_exception",
                    fallback_applied=True,
                ),
            ),
        )

    if plugin_class is None:
        routing = _build_routing_metadata(
            mode=_ROUTING_MODE_LEGACY,
            selected_plugin=plugin_name,
            failure_mode="selected_plugin_missing",
            include_selection_order=True,
        )
        if strict_mode:
            _raise_contract_error(
                code="scan_pipeline_plugin_missing",
                message="selected scan-pipeline plugin is not registered",
                routing=routing,
            )
        return _fallback_to_legacy_orchestrator(
            legacy_orchestrator_fn=legacy_orchestrator_fn,
            role_path=role_path,
            scan_options=scan_options,
            warning_code="scan_pipeline_plugin_missing",
            warning_message="selected scan-pipeline plugin is not registered",
            routing=_merge_routing_metadata(
                routing,
                _build_routing_metadata(
                    fallback_reason="selected_plugin_missing",
                    fallback_applied=True,
                ),
            ),
        )

    try:
        plugin_context = execute_scan_pipeline_plugin(
            plugin_class=plugin_class,
            scan_options=dict(scan_options),
            scan_context={"role_path": role_path},
        )
    except Exception as exc:
        routing = _build_routing_metadata(
            mode=_ROUTING_MODE_LEGACY,
            selected_plugin=plugin_name,
            failure_mode="preflight_execution_exception",
            preflight_stage="process_scan_pipeline",
            include_selection_order=True,
        )
        if strict_mode:
            _raise_contract_error(
                code="scan_pipeline_router_failed",
                message="scan-pipeline router failed during plugin preflight",
                routing=routing,
                cause=exc,
            )
        return _fallback_to_legacy_orchestrator(
            legacy_orchestrator_fn=legacy_orchestrator_fn,
            role_path=role_path,
            scan_options=scan_options,
            warning_code="scan_pipeline_router_failed",
            warning_message="scan-pipeline router failed during plugin preflight",
            routing=_merge_routing_metadata(
                routing,
                _build_routing_metadata(
                    fallback_reason="preflight_execution_exception",
                    fallback_applied=True,
                ),
            ),
        )

    plugin_enabled: Any = None
    if isinstance(plugin_context, dict):
        plugin_enabled = plugin_context.get("plugin_enabled")
        if plugin_enabled is None:
            plugin_enabled = plugin_context.get("ansible_plugin_enabled")

    if plugin_enabled is None:
        plugin_enabled = True

    if bool(plugin_enabled):
        route_preflight_runtime = _build_route_preflight_runtime_carrier(
            plugin_name=plugin_name,
            plugin_context=(
                dict(plugin_context) if isinstance(plugin_context, dict) else None
            ),
        )
        return _invoke_kernel_orchestrator(
            kernel_orchestrator_fn=kernel_orchestrator_fn,
            role_path=role_path,
            scan_options=dict(scan_options),
            route_preflight_runtime=route_preflight_runtime,
        )

    payload = legacy_orchestrator_fn(role_path=role_path, scan_options=scan_options)
    _apply_routing_metadata(
        payload=payload,
        routing=_build_routing_metadata(
            mode=_ROUTING_MODE_LEGACY,
            selected_plugin=plugin_name,
            include_selection_order=True,
            fallback_reason="plugin_preflight_disabled",
            fallback_applied=True,
        ),
    )
    return payload


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
