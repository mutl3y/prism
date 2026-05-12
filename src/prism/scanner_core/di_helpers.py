"""Shared DI utility helpers for scanner_core and scanner_extract."""

from __future__ import annotations

from contextlib import AbstractContextManager, contextmanager
import logging
from typing import TYPE_CHECKING, Any, Callable, Iterator, Protocol, runtime_checkable

from prism.errors import (
    ERROR_CATEGORY_RUNTIME,
    PrismRuntimeError,
    ROLE_SCAN_RUNTIME_ERROR,
)

if TYPE_CHECKING:
    from prism.scanner_plugins.registry import PluginRegistry
    from prism.scanner_plugins.interfaces import (
        FeatureDetectionPlugin,
        VariableDiscoveryPlugin,
    )

_logger = logging.getLogger(__name__)

DI_TARGET_NAMES = frozenset(
    {
        "audit_plugin",
        "comment_driven_doc_plugin",
        "feature_detection_plugin",
        "feature_detector",
        "jinja_analysis_policy_plugin",
        "policy_manager",
        "policy_registry",
        "task_annotation_policy_plugin",
        "task_line_parsing_policy_plugin",
        "task_traversal_policy_plugin",
        "variable_discovery",
        "variable_discovery_plugin",
        "variable_extractor_policy_plugin",
        "yaml_parsing_policy_plugin",
    }
)


def factory_override_key(target_name: str) -> str:
    if target_name not in DI_TARGET_NAMES:
        raise PrismRuntimeError(
            code=ROLE_SCAN_RUNTIME_ERROR,
            category=ERROR_CATEGORY_RUNTIME,
            message=f"Unsupported DI target: {target_name!r}",
            layer="core",
        )
    return f"{target_name}_factory"


def inject_mock(di: object, target_name: str, mock: Any) -> None:
    if target_name not in DI_TARGET_NAMES:
        raise PrismRuntimeError(
            code=ROLE_SCAN_RUNTIME_ERROR,
            category=ERROR_CATEGORY_RUNTIME,
            message=f"Unsupported DI target: {target_name!r}",
            layer="core",
        )
    injector = getattr(di, "inject_mock", None)
    if not callable(injector):
        raise PrismRuntimeError(
            code=ROLE_SCAN_RUNTIME_ERROR,
            category=ERROR_CATEGORY_RUNTIME,
            message="DI object does not expose inject_mock(name, mock)",
            layer="core",
        )
    injector(target_name, mock)


@contextmanager
def temporary_default_plugin_registry(
    registry: "PluginRegistry",
) -> Iterator["PluginRegistry"]:
    from prism.scanner_plugins.bootstrap import (
        temporary_default_plugin_registry as _override,
    )

    with _override(registry):
        yield registry


@runtime_checkable
class HasScanOptions(Protocol):
    """DI interface for scan_options access."""

    scan_options: dict[str, Any]


@runtime_checkable
class EventBusProtocol(Protocol):
    """Minimal event-bus contract needed by scanner_core callers."""

    def phase(
        self,
        phase_name: str,
        *,
        context: dict[str, object] | None = None,
    ) -> AbstractContextManager[object]: ...


@runtime_checkable
class HasEventBusFactory(Protocol):
    """DI interface for event bus factory access."""

    def factory_event_bus(self) -> EventBusProtocol | None: ...


@runtime_checkable
class HasVariableDiscoveryPluginFactory(Protocol):
    """DI interface for variable discovery plugin factory access."""

    def factory_variable_discovery_plugin(self) -> VariableDiscoveryPlugin: ...


@runtime_checkable
class HasFeatureDetectionPluginFactory(Protocol):
    """DI interface for feature detection plugin factory access."""

    def factory_feature_detection_plugin(self) -> FeatureDetectionPlugin: ...


def scan_options_from_di(di: object | None = None) -> dict[str, object] | None:
    if di is None:
        _logger.debug("scan_options_from_di: di is None; returning None")
        return None
    if isinstance(di, HasScanOptions):
        scan_options = di.scan_options
        if isinstance(scan_options, dict):
            return scan_options
        _logger.debug(
            "scan_options_from_di: di.scan_options is type %s (not dict); returning None",
            type(scan_options).__name__,
        )
        return None
    _logger.debug(
        "scan_options_from_di: di does not implement HasScanOptions protocol; returning None"
    )
    return None


def get_prepared_policy_or_none(di: object | None, policy_name: str) -> object | None:
    scan_options = scan_options_from_di(di)
    if not isinstance(scan_options, dict):
        _logger.debug(
            "get_prepared_policy_or_none: scan_options not available for policy '%s'; returning None",
            policy_name,
        )
        return None
    prepared_policy_bundle = scan_options.get("prepared_policy_bundle")
    if not isinstance(prepared_policy_bundle, dict):
        _logger.debug(
            "get_prepared_policy_or_none: prepared_policy_bundle not a dict for policy '%s'; returning None",
            policy_name,
        )
        return None
    policy = prepared_policy_bundle.get(policy_name)
    if policy is None:
        _logger.debug(
            "get_prepared_policy_or_none: policy '%s' not found in prepared_policy_bundle; returning None",
            policy_name,
        )
    return policy


def require_prepared_policy(
    di: object | None,
    policy_name: str,
    context_label: str,
) -> object:
    """Retrieve a required policy from the prepared_policy_bundle or raise."""
    policy = get_prepared_policy_or_none(di, policy_name)
    if policy is not None:
        return policy
    raise ValueError(
        f"prepared_policy_bundle.{policy_name} must be provided before "
        f"{context_label} canonical execution"
    )


def get_event_bus_or_none(di: object) -> EventBusProtocol | None:
    """Return the event bus from DI or None if the factory is not registered."""
    if not isinstance(di, HasEventBusFactory):
        return None
    factory_event_bus = di.factory_event_bus
    if not callable(factory_event_bus):
        return None
    return factory_event_bus()


def get_variable_discovery_plugin_factory_or_none(
    di: object,
) -> Callable[[], VariableDiscoveryPlugin] | None:
    """Get the variable discovery plugin factory from DI or None if not registered.

    Returns the callable factory (not the result of calling it).
    Consolidates duplicate isinstance + callable checks across scanner_core.
    """
    if not isinstance(di, HasVariableDiscoveryPluginFactory):
        return None
    factory = di.factory_variable_discovery_plugin
    if not callable(factory):
        return None
    return factory


def get_feature_detection_plugin_factory_or_none(
    di: object,
) -> Callable[[], FeatureDetectionPlugin] | None:
    """Get the feature detection plugin factory from DI or None if not registered.

    Returns the callable factory (not the result of calling it).
    Consolidates duplicate isinstance + callable checks across scanner_core.
    """
    if not isinstance(di, HasFeatureDetectionPluginFactory):
        return None
    factory = di.factory_feature_detection_plugin
    if not callable(factory):
        return None
    return factory
