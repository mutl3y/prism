"""FallbackPolicyRegistry for default policy lookup and fallback management.

This registry provides default policy implementations for all 6 policy domains
when no plugin or override provides a specific implementation.

Contract
--------
The registry maintains:
- Platform-keyed default policies (ansible, kubernetes, terraform, etc.)
- Fallback chain for policy resolution
- Plugin-provided policies (optional, Wave 2)
- Policy composition and validation

Phase 2 Waves will enhance with:
1. Plugin registry integration
2. Override precedence handling
3. Policy validation and edge cases
4. Caching and performance optimization
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from prism.scanner_data.contracts_request import PreparedPolicyBundle


logger = logging.getLogger(__name__)

# Supported policy types for validation
SUPPORTED_POLICY_TYPES = frozenset(
    {
        "task_line_parsing",
        "task_annotation",
        "task_traversal",
        "variable_extractor",
        "yaml_parsing",
        "jinja_analysis",
    }
)


class FallbackPolicyRegistry:
    """Registry for default and fallback policy implementations.

    Responsibilities:
    - Maintain platform-specific default policies
    - Provide fallback chain for each policy type
    - Validate policy shapes and contracts
    - Support plugin-provided policy overrides (Wave 2+)

    Phase 2 construction sequence:
    1. Initialize with empty registry dict
    2. Populate from plugins (Wave 2)
    3. Accept overrides and precedence rules (Wave 2)
    4. Compose bundles on demand (Wave 1)
    """

    def __init__(self, *, default_platform_key: str | None = None) -> None:
        """Initialize registry with optional default platform.

        Args:
            default_platform_key: Default platform (e.g., "ansible").

        Raises:
            ValueError: If platform key invalid (deferred to Wave 1).
        """
        self._default_platform_key = default_platform_key or "ansible"
        self._registry: dict[str, dict[str, Any]] = {}
        self._registry_lock = threading.RLock()
        self._cache: dict[str, Any] = {}

        # Wave 2: Resolver factory storage
        self._resolvers: dict[str, dict[str, Callable[[], Any]]] = {}
        self._resolver_lock = threading.RLock()

        # Bootstrap all resolver factories
        self._bootstrap_resolvers()

    def get_default_policy(self, policy_type: str) -> dict[str, Any]:
        """Get default policy for given type.

        Supported policy types:
        - task_line_parsing
        - task_annotation
        - task_traversal
        - variable_extractor
        - yaml_parsing
        - jinja_analysis

        Args:
            policy_type: One of the supported policy type strings.

        Returns:
            Default policy dict for the policy type.

        Raises:
            KeyError: If policy type not registered.
            PrismRuntimeError: If default policy invalid.
        """
        if policy_type not in SUPPORTED_POLICY_TYPES:
            raise ValueError(f"Unsupported policy type: {policy_type}")

        with self._registry_lock:
            if policy_type not in self._registry:
                raise KeyError(f"No default policy registered for {policy_type}")
            return self._registry[policy_type]

    def lookup_policy(
        self,
        policy_type: str,
        platform_key: str | None = None,
    ) -> dict[str, Any] | None:
        """Look up policy by type and optional platform key.

        Checks platform-specific policies first, then falls back to default.

        Args:
            policy_type: Policy type to look up.
            platform_key: Optional platform key (e.g., "kubernetes").

        Returns:
            Policy dict if found, None if no policy registered.

        Raises:
            ValueError: If policy_type invalid format.
        """
        if policy_type not in SUPPORTED_POLICY_TYPES:
            raise ValueError(f"Invalid policy_type: {policy_type}")

        platform_key = platform_key or self._default_platform_key

        with self._registry_lock:
            # Check platform-specific registry first
            platform_registry_key = f"{policy_type}:{platform_key}"
            if platform_registry_key in self._registry:
                return self._registry[platform_registry_key]

            # Fall back to default
            if policy_type in self._registry:
                return self._registry[policy_type]

            return None

    def register_policy(
        self,
        policy_type: str,
        policy: dict[str, Any],
        *,
        platform_key: str | None = None,
    ) -> None:
        """Register a policy in the registry.

        Args:
            policy_type: Type of policy being registered.
            policy: Policy implementation dict.
            platform_key: Optional platform-specific registration.

        Raises:
            ValueError: If policy_type or policy invalid.
            TypeError: If policy shape incorrect.
        """
        if policy_type not in SUPPORTED_POLICY_TYPES:
            raise ValueError(f"Invalid policy_type: {policy_type}")

        if not isinstance(policy, dict):
            raise TypeError("policy must be a dict")

        with self._registry_lock:
            if platform_key:
                registry_key = f"{policy_type}:{platform_key}"
            else:
                registry_key = policy_type

            self._registry[registry_key] = policy
            logger.debug(f"Registered policy {registry_key}")

    def set_default_platform_key(self, platform_key: str) -> None:
        """Set the default platform key for policy lookup fallback.

        Args:
            platform_key: Platform key (e.g., "ansible", "kubernetes").

        Raises:
            ValueError: If platform key empty or invalid format.
        """
        if not platform_key or not isinstance(platform_key, str):
            raise ValueError("platform_key must be a non-empty string")

        with self._registry_lock:
            self._default_platform_key = platform_key

    def register_resolver(
        self,
        policy_type: str,
        platform_key: str,
        factory_fn: Callable[[], Any],
    ) -> None:
        """Register a resolver factory function for a policy type and platform.

        Wave 2: Consolidate resolver factories into the registry.

        Args:
            policy_type: Type of policy (e.g., "task_line_parsing").
            platform_key: Platform key (e.g., "ansible", "kubernetes").
            factory_fn: Factory function that returns the resolved policy.

        Raises:
            ValueError: If policy_type is invalid.
            TypeError: If factory_fn is not callable.
        """
        if policy_type not in SUPPORTED_POLICY_TYPES:
            raise ValueError(f"Invalid policy_type: {policy_type}")

        if not callable(factory_fn):
            raise TypeError("factory_fn must be callable")

        with self._resolver_lock:
            if policy_type not in self._resolvers:
                self._resolvers[policy_type] = {}

            self._resolvers[policy_type][platform_key] = factory_fn
            logger.debug(f"Registered resolver for {policy_type}:{platform_key}")

    def get_resolver(
        self,
        policy_type: str,
        platform_key: str,
    ) -> Callable[[], Any] | None:
        """Get a resolver factory function by type and platform.

        Wave 2: Retrieve registered resolver factories.

        Args:
            policy_type: Type of policy.
            platform_key: Platform key.

        Returns:
            Factory function if registered, None otherwise.

        Raises:
            ValueError: If policy_type is invalid.
        """
        if policy_type not in SUPPORTED_POLICY_TYPES:
            raise ValueError(f"Invalid policy_type: {policy_type}")

        with self._resolver_lock:
            if policy_type in self._resolvers:
                return self._resolvers[policy_type].get(platform_key)

        return None

    def _bootstrap_resolvers(self) -> None:
        """Bootstrap all 6 resolver factories at initialization.

        Wave 2: Initialize resolver factories for all supported policy types.
        Currently uses no-op factories as placeholders. Wave 2 will populate
        these with actual resolver implementations.
        """
        # Create placeholder factory functions for all 6 policy types
        # Wave 2 will replace these with actual resolver implementations
        for policy_type in SUPPORTED_POLICY_TYPES:
            # For now, use a generic factory that returns a minimal policy dict
            def make_default_factory(ptype: str) -> Callable[[], dict[str, Any]]:
                def factory() -> dict[str, Any]:
                    return {"type": ptype, "platform": "ansible"}

                return factory

            factory_fn = make_default_factory(policy_type)
            self.register_resolver(policy_type, "ansible", factory_fn)

            logger.debug(f"Bootstrapped resolver for {policy_type}")

    def compose_bundle(self) -> PreparedPolicyBundle:
        """Compose a complete prepared policy bundle from registered policies.

        Returns:
            PreparedPolicyBundle with all 6 policy types.

        Raises:
            PrismRuntimeError: If any required policy missing.
            ValueError: If bundle composition fails validation.
        """
        raise NotImplementedError("Wave 2: compose_bundle")

    def get_platform_key_default(self) -> str | None:
        """Get the default platform key for fallback resolution.

        Returns:
            Default platform key or None if not set.
        """
        return self._default_platform_key

    def get_registry_dict(self) -> dict[str, dict[str, Any]]:
        """Return the internal registry dict structure for debugging.

        Returns:
            Dict mapping policy types to their implementations.
        """
        with self._registry_lock:
            return dict(self._registry)
