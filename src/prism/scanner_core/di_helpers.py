"""Shared DI utility helpers for scanner_core and scanner_extract."""

from __future__ import annotations

from contextlib import AbstractContextManager
import logging
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from prism.scanner_plugins.interfaces import (
        FeatureDetectionPlugin,
        VariableDiscoveryPlugin,
    )

_logger = logging.getLogger(__name__)


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
) -> Any:
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
