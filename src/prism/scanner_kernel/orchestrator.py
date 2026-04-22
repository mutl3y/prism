"""Kernel orchestration helpers for plugin-based scanner execution."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable

from prism.errors import PrismRuntimeError


_SCAN_PIPELINE_SELECTION_ORDER: tuple[str, ...] = (
    "request.option.scan_pipeline_plugin",
    "policy_context.selection.plugin",
    "platform",
    "registry_default",
)

_ROUTING_MODE_PLUGIN = "scan_pipeline_plugin"


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


def _is_explicitly_selected_plugin_name(scan_options: dict[str, Any]) -> bool:
    configured = scan_options.get("scan_pipeline_plugin")
    if isinstance(configured, str) and configured.strip():
        return True
    if _resolve_policy_context_scan_pipeline_plugin_name(scan_options) is not None:
        return True
    platform = scan_options.get("platform")
    if isinstance(platform, str) and platform.strip():
        return True
    return False


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

    if registry is None:
        raise ValueError("registry must be provided for plugin name resolution")
    return _resolve_default_scan_pipeline_plugin_name(registry)


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


def _append_scan_policy_warning(
    *,
    payload: dict[str, Any],
    code: str,
    message: str,
    detail: dict[str, Any],
) -> dict[str, Any]:
    warning_metadata = _ensure_payload_metadata(payload)
    existing_warnings = warning_metadata.get("scan_policy_warnings")
    warnings_list = (
        list(existing_warnings) if isinstance(existing_warnings, list) else []
    )
    warning = {
        "code": code,
        "message": message,
        "detail": copy.deepcopy(detail),
    }
    if warning not in warnings_list:
        warnings_list.append(warning)
    warning_metadata["scan_policy_warnings"] = warnings_list
    return payload


def apply_scan_policy_blocker_runtime_outcomes(
    *,
    payload: dict[str, Any],
    strict_mode: bool,
) -> dict[str, Any]:
    """Translate emitted blocker facts into preserved runtime outcomes."""
    metadata = _ensure_payload_metadata(payload)
    blocker_facts = metadata.get("scan_policy_blocker_facts")
    if not isinstance(blocker_facts, dict):
        return payload

    blocker_events: list[tuple[str, str, str, dict[str, Any]]] = []

    dynamic_facts = blocker_facts.get("dynamic_includes")
    if isinstance(dynamic_facts, dict):
        dynamic_total = int(dynamic_facts.get("total_count") or 0)
        if bool(dynamic_facts.get("enabled")) and dynamic_total > 0:
            blocker_events.append(
                (
                    "unconstrained_dynamic_includes_detected",
                    "Scan policy failure: unconstrained dynamic include targets were detected.",
                    "Scan policy warning: unconstrained dynamic include targets were detected.",
                    {
                        "dynamic_task_includes": int(
                            dynamic_facts.get("task_count") or 0
                        ),
                        "dynamic_role_includes": int(
                            dynamic_facts.get("role_count") or 0
                        ),
                    },
                )
            )

    yaml_like_facts = blocker_facts.get("yaml_like_annotations")
    if isinstance(yaml_like_facts, dict):
        yaml_like_count = int(yaml_like_facts.get("count") or 0)
        if bool(yaml_like_facts.get("enabled")) and yaml_like_count > 0:
            blocker_events.append(
                (
                    "yaml_like_task_annotations_detected",
                    "Scan policy failure: yaml-like task annotations were detected.",
                    "Scan policy warning: yaml-like task annotations were detected.",
                    {"yaml_like_task_annotations": yaml_like_count},
                )
            )

    if strict_mode and blocker_events:
        code, failure_message, _warning_message, detail = blocker_events[0]
        raise PrismRuntimeError(
            code=code,
            category="runtime",
            message=failure_message,
            detail=detail,
        )

    for code, _failure_message, warning_message, detail in blocker_events:
        _append_scan_policy_warning(
            payload=payload,
            code=code,
            message=warning_message,
            detail=detail,
        )

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
    return kernel_orchestrator_fn(
        role_path=role_path,
        scan_options=scan_options,
        route_preflight_runtime=route_preflight_runtime,
    )


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
    payload = apply_scan_policy_blocker_runtime_outcomes(
        payload=payload,
        strict_mode=strict_mode,
    )
    if registry is None:
        raise ValueError("registry must be provided for scan pipeline orchestration")
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
                registry=registry,
            )
        plugin_class = resolve_scan_pipeline_plugin_class(
            registry=registry,
            plugin_name=plugin_name,
        )
    except Exception as exc:
        routing = _build_routing_metadata(
            failure_mode="runtime_execution_exception",
            selected_plugin=None if plugin_name == "unresolved" else plugin_name,
        )
        _raise_contract_error(
            code="scan_pipeline_execution_failed",
            message="scan-pipeline runtime execution failed",
            routing=routing,
            cause=exc,
        )

    if plugin_class is None:
        routing = _build_routing_metadata(
            failure_mode="plugin_not_found",
            selected_plugin=plugin_name,
        )
        _raise_contract_error(
            code="scan_pipeline_plugin_not_found",
            message=(
                f"scan-pipeline plugin '{plugin_name}' resolved by name but is "
                "not registered in the registry"
            ),
            routing=routing,
        )

    assert plugin_class is not None
    plugin_instance = plugin_class()
    orchestrate_scan_payload: Any = getattr(
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
        )
        _raise_contract_error(
            code="scan_pipeline_execution_failed",
            message="scan-pipeline runtime execution failed",
            routing=routing,
            cause=exc,
        )

    if isinstance(result, dict) and existing_preflight_routing:
        _apply_routing_metadata(payload=result, routing=existing_preflight_routing)
    return result


def route_scan_payload_orchestration(
    *,
    role_path: str,
    scan_options: dict[str, Any],
    kernel_orchestrator_fn: Callable[..., dict[str, Any]],
    registry: Any | None = None,
) -> dict[str, Any]:
    """Route orchestration using registered scan-pipeline plugin decision context."""
    if registry is None:
        raise ValueError("registry must be provided for scan pipeline routing")

    plugin_name = resolve_scan_pipeline_plugin_name(
        scan_options=scan_options,
        registry=registry,
    )

    plugin_class = resolve_scan_pipeline_plugin_class(
        registry=registry,
        plugin_name=plugin_name,
    )

    if plugin_class is None:
        if hasattr(
            registry, "is_reserved_unsupported_platform"
        ) and registry.is_reserved_unsupported_platform(plugin_name):
            routing = _build_routing_metadata(
                mode="unsupported",
                selected_plugin=plugin_name,
                failure_mode="platform_not_supported",
                include_selection_order=True,
            )
            _raise_contract_error(
                code="platform_not_supported",
                message=f"selected platform '{plugin_name}' is reserved but not supported for scanning",
                routing=routing,
            )
        if _is_explicitly_selected_plugin_name(scan_options):
            routing = _build_routing_metadata(
                mode="unsupported",
                selected_plugin=plugin_name,
                failure_mode="platform_not_registered",
                include_selection_order=True,
            )
            _raise_contract_error(
                code="platform_not_registered",
                message=f"selected platform '{plugin_name}' is not registered",
                routing=routing,
            )
        _raise_contract_error(
            code="scan_pipeline_plugin_missing",
            message="selected scan-pipeline plugin is not registered",
            routing=_build_routing_metadata(
                selected_plugin=plugin_name,
                failure_mode="selected_plugin_missing",
                include_selection_order=True,
            ),
        )

    plugin_context = execute_scan_pipeline_plugin(
        plugin_class=plugin_class,
        scan_options=dict(scan_options),
        scan_context={"role_path": role_path},
    )

    plugin_enabled: Any = None
    if isinstance(plugin_context, dict):
        plugin_enabled = plugin_context.get("plugin_enabled")

    if plugin_enabled is None:
        plugin_enabled = True

    if not bool(plugin_enabled):
        raise PrismRuntimeError(
            code="scan_pipeline_plugin_disabled",
            category="runtime",
            message=f"scan-pipeline plugin '{plugin_name}' disabled itself during preflight",
            detail={"plugin_name": plugin_name},
        )

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
