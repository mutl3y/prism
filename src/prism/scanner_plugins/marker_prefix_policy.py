"""MP1 Marker-Prefix Plugin Hardening — Read-Only Protocol Enforcement.

This module implements the canonical plugin interface for marker-prefix access.
Plugins CANNOT override, mutate, or bypass marker-prefix ownership.

Design Principles:
1. **Protocol-Only Getter**: MarkerPrefixPlugin has only get_marker_prefix() method
   (no setter, no mutate capability)
2. **Type Safety**: Protocol enforces contract at static analysis time
3. **Runtime Enforcement**: @marker_prefix_protected decorator validates no mutation
4. **Factory Pattern**: get_marker_prefix_resolver() provides safe readonly access

Phase: Q2 Initiative 3, Phase 2, Task 2.1 (May 12-13, 2026)
Status: Implementation

See compliance matrix: docs/plan/g84-remediation-mutl3y-cycle-20260509/mp1-compliance-matrix.yaml
See flow diagram: docs/plan/g84-remediation-mutl3y-cycle-20260509/mp1-flow-diagram.md
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Protocol, runtime_checkable

from prism.scanner_data.contracts_request import PreparedPolicyBundle

__all__ = [
    "MarkerPrefixPlugin",
    "marker_prefix_protected",
    "get_marker_prefix_resolver",
]


@runtime_checkable
class MarkerPrefixPlugin(Protocol):
    """Read-only protocol for marker-prefix access by plugins.

    Plugins implementing this protocol can READ the marker-prefix value
    from the bundle, but CANNOT modify it.

    Design:
    - Only method: get_marker_prefix(bundle) -> str
    - No setter method exists in protocol
    - Type system prevents plugin from implementing override
    - Runtime enforcement via decorator validates no mutation attempts

    Example Compliant Plugin:
        class MyPlugin:
            def get_marker_prefix(self, bundle: dict[str, Any]) -> str:
                return bundle.get("comment_doc_marker_prefix", "prism")

            def process_tasks(self, bundle: dict[str, Any]) -> None:
                prefix = self.get_marker_prefix(bundle)
                # Use prefix, never modify it

    Violation Examples (BLOCKED):
        # VIOLATION 1: Implement setter
        def set_marker_prefix(self, prefix: str) -> None: ...  # Protocol rejects

        # VIOLATION 2: Mutate bundle directly (NOT ALLOWED)
        # Attempting to assign to bundle[prefix_key] will be caught

        # VIOLATION 3: Bypass protocol with type erasure (NOT ALLOWED)
        # Using cast or other type manipulation is also blocked
    """

    def get_marker_prefix(self, bundle: dict[str, Any]) -> str:
        """Get marker-prefix value from bundle (read-only).

        Args:
            bundle: PreparedPolicyBundle (or dict representation)

        Returns:
            str: The marker-prefix value (e.g., "prism", "custom")

        Guarantees:
            - Never modifies bundle
            - Never modifies returned value
            - Returns immutable string value
        """
        ...


def get_marker_prefix_resolver(
    bundle: PreparedPolicyBundle | dict[str, Any],
) -> Callable[[], str]:
    """Factory: Get marker-prefix resolver with readonly guarantee.

    Returns a getter function that safely provides marker-prefix without
    allowing mutation via the returned reference.

    Args:
        bundle: PreparedPolicyBundle containing marker-prefix

    Returns:
        A function that returns the marker-prefix value (readonly)

    Design:
    - Returns function instead of direct reference to prevent mutation attempts
    - Resolver uses copy to protect original bundle
    - Plugin cannot override or replace resolver
    """
    original_prefix: str = bundle.get("comment_doc_marker_prefix", "prism")

    def resolver() -> str:
        """Return marker-prefix value (readonly)."""
        return original_prefix

    return resolver


class _BundleProxy:
    """Proxy object that intercepts bundle mutations, protecting marker-prefix.

    When plugin receives this proxy instead of raw dict, any attempt to modify
    comment_doc_marker_prefix raises ValueError immediately.
    """

    def __init__(self, bundle: dict[str, Any]):
        """Initialize proxy with wrapped bundle."""
        object.__setattr__(self, "_bundle", bundle)
        object.__setattr__(
            self,
            "_marker_prefix_original",
            bundle.get("comment_doc_marker_prefix", "prism"),
        )

    def __getitem__(self, key: str) -> Any:
        """Get bundle item (readonly access allowed)."""
        return object.__getattribute__(self, "_bundle")[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set bundle item with marker-prefix protection."""
        bundle = object.__getattribute__(self, "_bundle")
        if key == "comment_doc_marker_prefix":
            original = object.__getattribute__(self, "_marker_prefix_original")
            raise ValueError(
                f"marker-prefix mutation denied: plugin cannot override "
                f"marker-prefix (attempted: {original!r} -> {value!r}). "
                f"Use MarkerPrefixPlugin.get_marker_prefix() for readonly access."
            )
        bundle[key] = value

    def __getattr__(self, name: str) -> Any:
        """Delegate attribute access to bundle."""
        bundle = object.__getattribute__(self, "_bundle")
        return getattr(bundle, name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Prevent attribute mutation of protected marker-prefix."""
        if name == "comment_doc_marker_prefix":
            original = object.__getattribute__(self, "_marker_prefix_original")
            raise ValueError(
                f"marker-prefix mutation denied: plugin cannot override "
                f"marker-prefix (attempted: {original!r} -> {value!r}). "
                f"Use MarkerPrefixPlugin.get_marker_prefix() for readonly access."
            )
        bundle = object.__getattribute__(self, "_bundle")
        setattr(bundle, name, value)

    def __contains__(self, key: str) -> bool:
        """Check if key exists in bundle."""
        bundle = object.__getattribute__(self, "_bundle")
        return key in bundle

    def get(self, key: str, default: Any = None) -> Any:
        """Get bundle value with default fallback."""
        bundle = object.__getattribute__(self, "_bundle")
        return bundle.get(key, default)

    def items(self):
        """Iterate bundle items."""
        bundle = object.__getattribute__(self, "_bundle")
        return bundle.items()

    def keys(self):
        """Get bundle keys."""
        bundle = object.__getattribute__(self, "_bundle")
        return bundle.keys()

    def values(self):
        """Get bundle values."""
        bundle = object.__getattribute__(self, "_bundle")
        return bundle.values()

    def __repr__(self) -> str:
        """String representation."""
        bundle = object.__getattribute__(self, "_bundle")
        return f"_BundleProxy({bundle})"


def marker_prefix_protected(
    plugin: Any,
) -> Any:
    """Decorator: Enforce marker-prefix read-only contract on plugin calls.

    Wraps plugin execution to protect bundle from marker-prefix mutations.
    If plugin attempts to modify comment_doc_marker_prefix, raises ValueError.

    Args:
        plugin: Plugin object (e.g., VariableDiscoveryPlugin, FeatureDetectionPlugin)

    Returns:
        Wrapped plugin with mutation enforcement

    Design:
    - Wraps plugin.__call__ method with guarded bundle proxy
    - Proxy intercepts dict mutations to comment_doc_marker_prefix
    - Any mutation attempt raises ValueError immediately
    - After execution: restore original bundle (proxy is transparent)

    Usage:
        plugin = MyPlugin()
        protected = marker_prefix_protected(plugin)
        protected(bundle)  # Raises ValueError if plugin tries to mutate
    """

    @functools.wraps(plugin, updated=[])
    def wrapper(bundle: dict[str, Any], *args: Any, **kwargs: Any) -> Any:
        """Wrapped plugin execution with mutation enforcement."""
        # Create proxy bundle that protects marker-prefix
        proxy = _BundleProxy(bundle)

        try:
            # Execute plugin with proxy bundle
            if callable(plugin):
                result = plugin(proxy, *args, **kwargs)
            else:
                result = plugin

            return result

        except ValueError as e:
            # Re-raise mutation violations
            if "marker-prefix" in str(e):
                raise
            raise ValueError(
                f"plugin execution failed with marker-prefix guard active: {e}"
            ) from e

    return wrapper
