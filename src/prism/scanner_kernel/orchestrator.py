"""Kernel orchestration helpers for plugin-based scanner execution."""

from __future__ import annotations

import copy
from typing import Callable, NoReturn, Protocol, TypeGuard, cast, runtime_checkable

from prism.errors import PrismRuntimeError
from prism.scanner_core.protocols_runtime import KernelOrchestrator, KernelResponse
from prism.scanner_data.contracts_request import ScanMetadata, ScanOptionsDict
from prism.scanner_kernel.plugin_name_resolver import (
    RoutePreflightRuntimeCarrier,
    ScanPipelineRegistry,
    ScanPipelineRouting,
    _resolve_policy_context_scan_pipeline_plugin_name,
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
        scan_options: ScanOptionsDict,
        scan_context: ScanMetadata,
    ) -> ScanMetadata: ...


@runtime_checkable
class _OrchestrateScanPayloadPlugin(Protocol):
    """Minimal plugin surface for runtime payload orchestration."""

    def orchestrate_scan_payload(
        self,
        *,
        payload: dict[str, object],
        scan_options: ScanOptionsDict,
        strict_mode: bool,
        preflight_context: ScanMetadata | None = None,
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


def _is_scan_pipeline_registry(value: object) -> TypeGuard[ScanPipelineRegistry]:
    return callable(getattr(value, "get_scan_pipeline_plugin", None))


def _is_scan_metadata(value: object) -> TypeGuard[ScanMetadata]:
    return isinstance(value, dict)


def _is_scan_pipeline_routing(value: object) -> TypeGuard[ScanPipelineRouting]:
    return isinstance(value, dict)


def _copy_scan_metadata(value: object) -> ScanMetadata:
    if _is_scan_metadata(value):
        return copy.copy(value)
    return ScanMetadata()


def _copy_scan_pipeline_routing(value: object) -> ScanPipelineRouting:
    if _is_scan_pipeline_routing(value):
        return copy.copy(value)
    return ScanPipelineRouting()


def _clone_container_structure(value: object) -> object:
    if isinstance(value, dict):
        return {key: _clone_container_structure(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clone_container_structure(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_clone_container_structure(item) for item in value)
    if isinstance(value, set):
        return {_clone_container_structure(item) for item in value}
    if isinstance(value, frozenset):
        return frozenset(_clone_container_structure(item) for item in value)
    return value


def _copy_scan_options(value: ScanOptionsDict) -> ScanOptionsDict:
    return cast(ScanOptionsDict, _clone_container_structure(value))


def _require_scan_pipeline_registry(registry: object | None) -> ScanPipelineRegistry:
    if not _is_scan_pipeline_registry(registry):
        raise ValueError("registry must implement the scan-pipeline registry contract")
    return registry


def _is_explicitly_selected_plugin_name(scan_options: ScanOptionsDict) -> bool:
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
    plugin_context: ScanMetadata | None,
    plugin_factory: object | None = None,
) -> RoutePreflightRuntimeCarrier:
    preflight_context_data: ScanMetadata = (
        copy.copy(plugin_context)
        if _is_scan_metadata(plugin_context)
        else ScanMetadata()
    )
    preflight_context_data["plugin_name"] = plugin_name
    routing_seed = None
    if _is_scan_metadata(plugin_context):
        existing_routing = plugin_context.get("routing")
        if _is_scan_pipeline_routing(existing_routing):
            routing_seed = existing_routing
    routing_seed_dict = dict(routing_seed) if routing_seed is not None else None
    routing = _merge_routing_metadata(
        routing_seed_dict,
        _build_routing_metadata(
            mode=_ROUTING_MODE_PLUGIN,
            selected_plugin=plugin_name,
            include_selection_order=True,
        ),
    )
    return RoutePreflightRuntimeCarrier(
        plugin_name=plugin_name,
        preflight_context=preflight_context_data,
        routing=_copy_scan_pipeline_routing(routing),
        plugin_factory=(
            cast(_ScanPipelinePluginFactory, plugin_factory)
            if _is_scan_pipeline_plugin_factory(plugin_factory)
            else None
        ),
    )


def _invoke_kernel_orchestrator(
    *,
    kernel_orchestrator_fn: KernelOrchestrator,
    role_path: str,
    scan_options: ScanOptionsDict,
    route_preflight_runtime: RoutePreflightRuntimeCarrier,
) -> KernelResponse:
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


def _raise_invalid_preflight_output_error(
    *,
    plugin_name: str,
    plugin_output: object,
) -> NoReturn:
    _raise_contract_error(
        code="scan_pipeline_execution_failed",
        message=(
            f"scan-pipeline plugin '{plugin_name}' returned invalid preflight "
            f"output type '{type(plugin_output).__name__}'; expected dict"
        ),
        routing=_build_routing_metadata(
            mode=_ROUTING_MODE_PLUGIN,
            selected_plugin=plugin_name,
            failure_mode="invalid_preflight_output",
        ),
    )


def _raise_execution_failure(
    *,
    phase: str,
    plugin_name: str | None,
    failure_mode: str,
    cause: Exception,
) -> NoReturn:
    _raise_contract_error(
        code="scan_pipeline_execution_failed",
        message=f"scan-pipeline {phase} execution failed",
        routing=_build_routing_metadata(
            mode=_ROUTING_MODE_PLUGIN,
            selected_plugin=plugin_name,
            failure_mode=failure_mode,
        ),
        cause=cause,
    )


def _construct_scan_pipeline_plugin(
    *,
    plugin_factory: object,
    plugin_name: str,
    phase: str,
) -> object:
    try:
        return _instantiate_scan_pipeline_plugin(plugin_factory)
    except PrismRuntimeError:
        raise
    except Exception as exc:
        _raise_execution_failure(
            phase=phase,
            plugin_name=plugin_name,
            failure_mode="constructor_exception",
            cause=exc,
        )


def _orchestrate_scan_payload_with_plugin_instance(
    *,
    plugin: object,
    plugin_name: str,
    payload: dict[str, object],
    scan_options: ScanOptionsDict,
    strict_mode: bool,
    preflight_context: ScanMetadata | None = None,
) -> dict[str, object]:
    metadata = payload.get("metadata")
    base_metadata = copy.deepcopy(metadata) if isinstance(metadata, dict) else {}

    if _is_scan_metadata(preflight_context):
        plugin_output: object = copy.copy(preflight_context)
    else:
        if _is_process_scan_pipeline_plugin(plugin):
            plugin_output = plugin.process_scan_pipeline(
                scan_options=_copy_scan_options(scan_options),
                scan_context=_copy_scan_metadata(base_metadata),
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
    scan_options: ScanOptionsDict,
    strict_mode: bool,
    preflight_context: ScanMetadata | None = None,
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
    scan_pipeline_registry = _require_scan_pipeline_registry(registry)
    plugin_name = "unresolved"
    existing_preflight_routing: ScanPipelineRouting = ScanPipelineRouting()

    if route_preflight_runtime is not None:
        plugin_name = route_preflight_runtime.plugin_name
        preflight_context = _copy_scan_metadata(
            route_preflight_runtime.preflight_context
        )
        existing_preflight_routing = _copy_scan_pipeline_routing(
            route_preflight_runtime.routing
        )
        _apply_routing_metadata(
            payload=payload,
            routing=cast(dict[str, object], copy.copy(existing_preflight_routing)),
        )
    elif _is_scan_metadata(preflight_context):
        preflight_routing = preflight_context.get("routing")
        if _is_scan_pipeline_routing(preflight_routing):
            existing_preflight_routing = _copy_scan_pipeline_routing(preflight_routing)
            _apply_routing_metadata(
                payload=payload,
                routing=cast(dict[str, object], copy.copy(existing_preflight_routing)),
            )

    try:
        plugin_factory = None
        if plugin_name == "unresolved":
            plugin_name = resolve_scan_pipeline_plugin_name(
                scan_options=scan_options,
                registry=scan_pipeline_registry,
            )
        if (
            route_preflight_runtime is not None
            and route_preflight_runtime.plugin_factory is not None
        ):
            plugin_factory = route_preflight_runtime.plugin_factory
        else:
            plugin_factory = resolve_scan_pipeline_plugin_class(
                registry=scan_pipeline_registry,
                plugin_name=plugin_name,
            )
    except Exception as exc:
        _raise_execution_failure(
            phase="runtime",
            plugin_name=None if plugin_name == "unresolved" else plugin_name,
            failure_mode="runtime_execution_exception",
            cause=exc,
        )

    if plugin_factory is None:
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

    plugin_instance = _construct_scan_pipeline_plugin(
        plugin_factory=plugin_factory,
        plugin_name=plugin_name,
        phase="runtime",
    )
    try:
        if _is_orchestrate_scan_payload_plugin(plugin_instance):
            result = plugin_instance.orchestrate_scan_payload(
                payload=payload,
                scan_options=_copy_scan_options(scan_options),
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
        _raise_execution_failure(
            phase="runtime",
            plugin_name=plugin_name,
            failure_mode="runtime_execution_exception",
            cause=exc,
        )

    if not isinstance(result, dict):
        _raise_invalid_plugin_output_error(
            plugin_name=plugin_name,
            plugin_output=result,
        )

    if isinstance(result, dict) and existing_preflight_routing:
        _apply_routing_metadata(
            payload=result,
            routing=cast(dict[str, object], copy.copy(existing_preflight_routing)),
        )
    return result


def route_scan_payload_orchestration(
    *,
    role_path: str,
    scan_options: ScanOptionsDict,
    kernel_orchestrator_fn: KernelOrchestrator,
    registry: object | None = None,
) -> dict[str, object]:
    """Route orchestration using registered scan-pipeline plugin decision context."""
    if registry is None:
        raise ValueError("registry must be provided for scan pipeline routing")
    scan_pipeline_registry = _require_scan_pipeline_registry(registry)

    plugin_name = "unresolved"
    try:
        plugin_name = resolve_scan_pipeline_plugin_name(
            scan_options=scan_options,
            registry=scan_pipeline_registry,
        )
        plugin_class = resolve_scan_pipeline_plugin_class(
            registry=scan_pipeline_registry,
            plugin_name=plugin_name,
        )
    except PrismRuntimeError:
        raise
    except Exception as exc:
        _raise_execution_failure(
            phase="preflight",
            plugin_name=None if plugin_name == "unresolved" else plugin_name,
            failure_mode="preflight_resolution_exception",
            cause=exc,
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

    plugin_instance = _construct_scan_pipeline_plugin(
        plugin_factory=plugin_class,
        plugin_name=plugin_name,
        phase="preflight",
    )
    if not _is_process_scan_pipeline_plugin(plugin_instance):
        _raise_contract_error(
            code="scan_pipeline_execution_failed",
            message=(
                f"scan-pipeline plugin '{plugin_name}' does not implement "
                "process_scan_pipeline"
            ),
            routing=_build_routing_metadata(
                mode=_ROUTING_MODE_PLUGIN,
                selected_plugin=plugin_name,
                failure_mode="invalid_preflight_contract",
            ),
        )
    try:
        plugin_context = plugin_instance.process_scan_pipeline(
            scan_options=_copy_scan_options(scan_options),
            scan_context=ScanMetadata(),
        )
    except PrismRuntimeError:
        raise
    except Exception as exc:
        _raise_execution_failure(
            phase="preflight",
            plugin_name=plugin_name,
            failure_mode="preflight_execution_exception",
            cause=exc,
        )

    if not isinstance(plugin_context, dict):
        _raise_invalid_preflight_output_error(
            plugin_name=plugin_name,
            plugin_output=plugin_context,
        )

    plugin_enabled: object | None = None
    plugin_enabled = plugin_context.get("plugin_enabled")

    if not isinstance(plugin_enabled, bool):
        _raise_contract_error(
            code="scan_pipeline_execution_failed",
            message=(
                f"scan-pipeline plugin '{plugin_name}' returned invalid preflight "
                f"'plugin_enabled' value type '{type(plugin_enabled).__name__}'; "
                "expected bool"
            ),
            routing=_build_routing_metadata(
                mode=_ROUTING_MODE_PLUGIN,
                selected_plugin=plugin_name,
                failure_mode="invalid_preflight_contract",
            ),
        )

    if not bool(plugin_enabled):
        raise PrismRuntimeError(
            code="scan_pipeline_plugin_disabled",
            category="runtime",
            message=f"scan-pipeline plugin '{plugin_name}' disabled itself during preflight",
            detail={"plugin_name": plugin_name},
        )

    route_preflight_runtime = _build_route_preflight_runtime_carrier(
        plugin_name=plugin_name,
        plugin_context=_copy_scan_metadata(plugin_context),
        plugin_factory=plugin_class,
    )
    return cast(
        dict[str, object],
        _invoke_kernel_orchestrator(
            kernel_orchestrator_fn=kernel_orchestrator_fn,
            role_path=role_path,
            scan_options=_copy_scan_options(scan_options),
            route_preflight_runtime=route_preflight_runtime,
        ),
    )
