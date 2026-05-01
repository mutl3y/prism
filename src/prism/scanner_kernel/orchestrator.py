"""Kernel orchestration helpers for plugin-based scanner execution."""

from __future__ import annotations

import copy
from typing import Callable, NoReturn, Protocol, TypeGuard, runtime_checkable

from prism.errors import PrismRuntimeError
from prism.scanner_core.protocols_runtime import KernelOrchestrator
from prism.scanner_kernel.plugin_name_resolver import (
    RoutePreflightRuntimeCarrier,
    _resolve_policy_context_scan_pipeline_plugin_name,
    execute_scan_pipeline_plugin,
    resolve_scan_pipeline_plugin_class,
    resolve_scan_pipeline_plugin_name,
)
from prism.scanner_kernel.scan_payload_helpers import (
    _apply_routing_metadata,
    _build_routing_metadata,
    _merge_metadata_preserving_existing,
    _merge_routing_metadata,
    apply_scan_policy_blocker_runtime_outcomes,
)


_ROUTING_MODE_PLUGIN = "scan_pipeline_plugin"


@runtime_checkable
class _ProcessScanPipelinePlugin(Protocol):
    """Minimal plugin surface for preflight-only fallback orchestration."""

    def process_scan_pipeline(
        self,
        scan_options: dict[str, object],
        scan_context: dict[str, object],
    ) -> dict[str, object]: ...


@runtime_checkable
class _OrchestrateScanPayloadPlugin(Protocol):
    """Minimal plugin surface for runtime payload orchestration."""

    def orchestrate_scan_payload(
        self,
        *,
        payload: dict[str, object],
        scan_options: dict[str, object],
        strict_mode: bool,
        preflight_context: dict[str, object] | None = None,
    ) -> dict[str, object]: ...


class _ScanPipelinePluginFactory(Protocol):
    """Factory contract for scan-pipeline plugin classes."""

    def __call__(self) -> object: ...


def _is_scan_pipeline_plugin_factory(
    value: object,
) -> TypeGuard[_ScanPipelinePluginFactory]:
    return callable(value)


def _is_process_scan_pipeline_plugin(
    value: object,
) -> TypeGuard[_ProcessScanPipelinePlugin]:
    return isinstance(value, _ProcessScanPipelinePlugin)


def _is_orchestrate_scan_payload_plugin(
    value: object,
) -> TypeGuard[_OrchestrateScanPayloadPlugin]:
    return isinstance(value, _OrchestrateScanPayloadPlugin)


def _instantiate_scan_pipeline_plugin(plugin_factory: object) -> object:
    if not _is_scan_pipeline_plugin_factory(plugin_factory):
        raise TypeError("resolved scan-pipeline plugin is not callable")
    return plugin_factory()


def _is_explicitly_selected_plugin_name(scan_options: dict[str, object]) -> bool:
    configured = scan_options.get("scan_pipeline_plugin")
    if isinstance(configured, str) and configured.strip():
        return True
    if _resolve_policy_context_scan_pipeline_plugin_name(scan_options) is not None:
        return True
    platform = scan_options.get("platform")
    if isinstance(platform, str) and platform.strip():
        return True
    return False


def _build_route_preflight_runtime_carrier(
    *,
    plugin_name: str,
    plugin_context: dict[str, object] | None,
) -> RoutePreflightRuntimeCarrier:
    preflight_context = dict(plugin_context) if isinstance(plugin_context, dict) else {}
    preflight_context.setdefault("plugin_name", plugin_name)
    existing_routing = preflight_context.get("routing")
    routing_seed = existing_routing if isinstance(existing_routing, dict) else None
    routing = _merge_routing_metadata(
        routing_seed,
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
    kernel_orchestrator_fn: KernelOrchestrator,
    role_path: str,
    scan_options: dict[str, object],
    route_preflight_runtime: RoutePreflightRuntimeCarrier,
) -> dict[str, object]:
    return kernel_orchestrator_fn(
        role_path=role_path,
        scan_options=scan_options,
        route_preflight_runtime=route_preflight_runtime,
    )


def _routing_error_detail(routing: dict[str, object]) -> dict[str, object]:
    return {"metadata": {"routing": routing}}


def _raise_contract_error(
    *,
    code: str,
    message: str,
    routing: dict[str, object],
    cause: Exception | None = None,
) -> NoReturn:
    raise PrismRuntimeError(
        code=code,
        category="runtime",
        message=message,
        detail=_routing_error_detail(routing),
    ) from cause


def _raise_invalid_plugin_output_error(
    *,
    plugin_name: str,
    plugin_output: object,
) -> NoReturn:
    _raise_contract_error(
        code="scan_pipeline_execution_failed",
        message=(
            f"scan-pipeline plugin '{plugin_name}' returned invalid runtime "
            f"output type '{type(plugin_output).__name__}'; expected dict"
        ),
        routing=_build_routing_metadata(
            mode=_ROUTING_MODE_PLUGIN,
            selected_plugin=plugin_name,
            failure_mode="invalid_plugin_output",
        ),
    )


def _orchestrate_scan_payload_with_plugin_instance(
    *,
    plugin: object,
    plugin_name: str,
    payload: dict[str, object],
    scan_options: dict[str, object],
    strict_mode: bool,
    preflight_context: dict[str, object] | None = None,
) -> dict[str, object]:
    metadata = payload.get("metadata")
    base_metadata = copy.deepcopy(metadata) if isinstance(metadata, dict) else {}

    if isinstance(preflight_context, dict):
        plugin_output: object = copy.deepcopy(preflight_context)
    else:
        if _is_process_scan_pipeline_plugin(plugin):
            plugin_output = plugin.process_scan_pipeline(
                scan_options=copy.deepcopy(scan_options),
                scan_context=copy.deepcopy(base_metadata),
            )
        else:
            plugin_output = {}

    if not isinstance(plugin_output, dict):
        _raise_invalid_plugin_output_error(
            plugin_name=plugin_name,
            plugin_output=plugin_output,
        )

    payload["metadata"] = _merge_metadata_preserving_existing(
        base_metadata,
        plugin_output,
    )
    return payload


def orchestrate_scan_payload_with_selected_plugin(
    *,
    build_payload_fn: Callable[[], dict[str, object]],
    scan_options: dict[str, object],
    strict_mode: bool,
    preflight_context: dict[str, object] | None = None,
    route_preflight_runtime: RoutePreflightRuntimeCarrier | None = None,
    registry: object | None = None,
) -> dict[str, object]:
    payload = build_payload_fn()
    payload = apply_scan_policy_blocker_runtime_outcomes(
        payload=payload,
        strict_mode=strict_mode,
    )
    if registry is None:
        raise ValueError("registry must be provided for scan pipeline orchestration")
    plugin_name = "unresolved"
    existing_preflight_routing: dict[str, object] = {}

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

    plugin_instance = _instantiate_scan_pipeline_plugin(plugin_class)
    try:
        if _is_orchestrate_scan_payload_plugin(plugin_instance):
            result = plugin_instance.orchestrate_scan_payload(
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
    except PrismRuntimeError:
        raise
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

    if not isinstance(result, dict):
        _raise_invalid_plugin_output_error(
            plugin_name=plugin_name,
            plugin_output=result,
        )

    if isinstance(result, dict) and existing_preflight_routing:
        _apply_routing_metadata(payload=result, routing=existing_preflight_routing)
    return result


def route_scan_payload_orchestration(
    *,
    role_path: str,
    scan_options: dict[str, object],
    kernel_orchestrator_fn: KernelOrchestrator,
    registry: object | None = None,
) -> dict[str, object]:
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

    plugin_enabled: object | None = None
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
