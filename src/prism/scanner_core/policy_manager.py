"""PolicyManager facade for consolidated policy coordination.

This module provides the primary interface for policy resolution, override management,
and bundle composition across all policy types. Phase 2 consolidates multiple scatter
policy handlers into a single unified facade.

Contract
--------
PolicyManager coordinates policy resolution across 6 policy domains:
- Task line parsing policy
- Task annotation policy
- Task traversal policy
- Variable extractor policy
- YAML parsing policy
- Jinja analysis policy

The manager delegates to FallbackPolicyRegistry for default resolution and accepts
policy overrides at initialization time.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

if TYPE_CHECKING:
    from prism.scanner_core.policy_registry import FallbackPolicyRegistry
    from prism.scanner_data.contracts_request import (
        PreparedPolicyBundle,
        PreparedTaskLineParsingPolicy,
        PreparedTaskAnnotationPolicy,
        PreparedTaskTraversalPolicy,
        PreparedVariableExtractorPolicy,
        PreparedYAMLParsingPolicy,
        PreparedJinjaAnalysisPolicy,
    )

logger = logging.getLogger(__name__)


class PolicyManager:
    """Unified facade for policy resolution and override coordination.

    Responsibilities:
    - Coordinate policy resolution across all 6 policy types
    - Manage policy overrides from scan_options and runtime inputs
    - Compose prepared policy bundles for scanner orchestrators
    - Delegate default policy lookup to FallbackPolicyRegistry

    Phase 2 Wave 1-7 will implement:
    1. Bundle composition from DI registry
    2. Override injection and precedence
    3. Policy validation and error handling
    4. Edge case handling (missing plugins, policy conflicts)
    5. Integration with FeatureDetector and VariableDiscovery
    6. Observable failures (logging, events)
    7. Performance optimization (caching, lazy loading)
    """

    def __init__(
        self,
        *,
        registry: FallbackPolicyRegistry | None = None,
        policy_overrides: dict[str, Any] | None = None,
    ) -> None:
        """Initialize PolicyManager with optional registry and overrides.

        Args:
            registry: Default policy registry (optional for phase 0 stub).
            policy_overrides: Runtime policy overrides (optional for phase 0 stub).

        Raises:
            ValueError: If registry validation fails (deferred to Wave 1).
        """
        self._registry = registry
        self._policy_overrides = policy_overrides or {}
        self._cache: dict[str, Any] = {}
        self._cache_lock = threading.RLock()

        self._bundle_cache: dict[tuple[str, str], Any] = {}
        self._policy_cache: dict[tuple[str, str], Any] = {}
        self._preresolved_cache: dict[str, Any] = {}
        self._bundle_cache_max_size = 10

    def resolve_prepared_bundle(
        self,
        *,
        scan_options: dict[str, object],
    ) -> PreparedPolicyBundle:
        """Compose a complete prepared policy bundle from scan_options and registry.

        Args:
            scan_options: Complete scan options including platform key.

        Returns:
            PreparedPolicyBundle with all 6 policy types resolved.

        Raises:
            PrismRuntimeError: If policy resolution fails.
        """
        if self._registry is None:
            raise ValueError("Cannot resolve bundle without registry")

        return self._registry.compose_bundle()

    def resolve_task_line_parsing_policy(
        self,
        di: Any,
        scan_options: dict[str, object],
    ) -> PreparedTaskLineParsingPolicy:
        """Resolve task line parsing policy.

        Args:
            di: DIContainer for factory access.
            scan_options: Scan options including platform key.

        Returns:
            PreparedTaskLineParsingPolicy implementation.

        Raises:
            ValueError: If policy cannot be resolved.
        """
        policy_type = "task_line_parsing"
        cache_key = f"{policy_type}:{id(scan_options)}"

        with self._cache_lock:
            if cache_key in self._cache:
                logger.debug(f"Cache hit for {policy_type}")
                return cast("PreparedTaskLineParsingPolicy", self._cache[cache_key])

        if self._registry is None:
            raise ValueError("Cannot resolve policy without registry")

        platform_key = self.get_platform_key(scan_options)
        policy = self._registry.lookup_policy(policy_type, platform_key)

        if policy is None:
            logger.warning(
                f"No policy found for {policy_type} on platform {platform_key}"
            )
            policy = self._registry.get_default_policy(policy_type)

        with self._cache_lock:
            self._cache[cache_key] = policy

        logger.debug(f"Resolved {policy_type} for platform {platform_key}")
        return cast("PreparedTaskLineParsingPolicy", policy)

    def resolve_task_annotation_policy(
        self,
        di: Any,
        scan_options: dict[str, object],
    ) -> PreparedTaskAnnotationPolicy:
        """Resolve task annotation parsing policy.

        Args:
            di: DIContainer for factory access.
            scan_options: Scan options including platform key.

        Returns:
            PreparedTaskAnnotationPolicy implementation.

        Raises:
            ValueError: If policy cannot be resolved.
        """
        policy_type = "task_annotation"
        cache_key = f"{policy_type}:{id(scan_options)}"

        with self._cache_lock:
            if cache_key in self._cache:
                logger.debug(f"Cache hit for {policy_type}")
                return cast("PreparedTaskAnnotationPolicy", self._cache[cache_key])

        if self._registry is None:
            raise ValueError("Cannot resolve policy without registry")

        platform_key = self.get_platform_key(scan_options)
        policy = self._registry.lookup_policy(policy_type, platform_key)

        if policy is None:
            policy = self._registry.get_default_policy(policy_type)

        with self._cache_lock:
            self._cache[cache_key] = policy

        logger.debug(f"Resolved {policy_type} for platform {platform_key}")
        return cast("PreparedTaskAnnotationPolicy", policy)

    def resolve_task_traversal_policy(
        self,
        di: Any,
        scan_options: dict[str, object],
    ) -> PreparedTaskTraversalPolicy:
        """Resolve task traversal policy.

        Args:
            di: DIContainer for factory access.
            scan_options: Scan options including platform key.

        Returns:
            PreparedTaskTraversalPolicy implementation.

        Raises:
            ValueError: If policy cannot be resolved.
        """
        policy_type = "task_traversal"
        cache_key = f"{policy_type}:{id(scan_options)}"

        with self._cache_lock:
            if cache_key in self._cache:
                logger.debug(f"Cache hit for {policy_type}")
                return cast("PreparedTaskTraversalPolicy", self._cache[cache_key])

        if self._registry is None:
            raise ValueError("Cannot resolve policy without registry")

        platform_key = self.get_platform_key(scan_options)
        policy = self._registry.lookup_policy(policy_type, platform_key)

        if policy is None:
            policy = self._registry.get_default_policy(policy_type)

        with self._cache_lock:
            self._cache[cache_key] = policy

        logger.debug(f"Resolved {policy_type} for platform {platform_key}")
        return cast("PreparedTaskTraversalPolicy", policy)

    def resolve_variable_extractor_policy(
        self,
        di: Any,
        scan_options: dict[str, object],
    ) -> PreparedVariableExtractorPolicy:
        """Resolve variable extractor policy.

        Args:
            di: DIContainer for factory access.
            scan_options: Scan options including platform key.

        Returns:
            PreparedVariableExtractorPolicy implementation.

        Raises:
            ValueError: If policy cannot be resolved.
        """
        policy_type = "variable_extractor"
        cache_key = f"{policy_type}:{id(scan_options)}"

        with self._cache_lock:
            if cache_key in self._cache:
                logger.debug(f"Cache hit for {policy_type}")
                return cast("PreparedVariableExtractorPolicy", self._cache[cache_key])

        if self._registry is None:
            raise ValueError("Cannot resolve policy without registry")

        platform_key = self.get_platform_key(scan_options)
        policy = self._registry.lookup_policy(policy_type, platform_key)

        if policy is None:
            policy = self._registry.get_default_policy(policy_type)

        with self._cache_lock:
            self._cache[cache_key] = policy

        logger.debug(f"Resolved {policy_type} for platform {platform_key}")
        return cast("PreparedVariableExtractorPolicy", policy)

    def resolve_yaml_parsing_policy(
        self,
        di: Any,
        scan_options: dict[str, object],
    ) -> PreparedYAMLParsingPolicy:
        """Resolve YAML parsing policy.

        Args:
            di: DIContainer for factory access.
            scan_options: Scan options including platform key.

        Returns:
            PreparedYAMLParsingPolicy implementation.

        Raises:
            ValueError: If policy cannot be resolved.
        """
        policy_type = "yaml_parsing"
        cache_key = f"{policy_type}:{id(scan_options)}"

        with self._cache_lock:
            if cache_key in self._cache:
                logger.debug(f"Cache hit for {policy_type}")
                return cast("PreparedYAMLParsingPolicy", self._cache[cache_key])

        if self._registry is None:
            raise ValueError("Cannot resolve policy without registry")

        platform_key = self.get_platform_key(scan_options)
        policy = self._registry.lookup_policy(policy_type, platform_key)

        if policy is None:
            policy = self._registry.get_default_policy(policy_type)

        with self._cache_lock:
            self._cache[cache_key] = policy

        logger.debug(f"Resolved {policy_type} for platform {platform_key}")
        return cast("PreparedYAMLParsingPolicy", policy)

    def resolve_jinja_analysis_policy(
        self,
        di: Any,
        scan_options: dict[str, object],
    ) -> PreparedJinjaAnalysisPolicy:
        """Resolve Jinja analysis policy.

        Args:
            di: DIContainer for factory access.
            scan_options: Scan options including platform key.

        Returns:
            PreparedJinjaAnalysisPolicy implementation.

        Raises:
            ValueError: If policy cannot be resolved.
        """
        policy_type = "jinja_analysis"
        cache_key = f"{policy_type}:{id(scan_options)}"

        with self._cache_lock:
            if cache_key in self._cache:
                logger.debug(f"Cache hit for {policy_type}")
                return cast("PreparedJinjaAnalysisPolicy", self._cache[cache_key])

        if self._registry is None:
            raise ValueError("Cannot resolve policy without registry")

        platform_key = self.get_platform_key(scan_options)
        policy = self._registry.lookup_policy(policy_type, platform_key)

        if policy is None:
            policy = self._registry.get_default_policy(policy_type)

        with self._cache_lock:
            self._cache[cache_key] = policy

        logger.debug(f"Resolved {policy_type} for platform {platform_key}")
        return cast("PreparedJinjaAnalysisPolicy", policy)

    def get_platform_key(self, scan_options: dict[str, object]) -> str:
        """Get platform key from scan_options, defaulting to 'ansible'.

        Args:
            scan_options: Scan options dict containing policy context.

        Returns:
            Platform key string (e.g., 'ansible', 'kubernetes').
        """
        # Check for explicit platform key in scan_options first
        if "scan_pipeline_plugin" in scan_options:
            plugin = scan_options.get("scan_pipeline_plugin")
            if isinstance(plugin, str) and plugin:
                return plugin

        # Check for platform in policy_context
        policy_context = scan_options.get("policy_context")
        if isinstance(policy_context, dict):
            selection = policy_context.get("selection")
            if isinstance(selection, dict):
                plugin = selection.get("plugin")
                if isinstance(plugin, str) and plugin:
                    return plugin

        # Fall back to registry default if available
        if self._registry is not None:
            return self._registry.get_platform_key_default() or "ansible"

        # Final default
        return "ansible"

    def get_fallback_policy(self, policy_type: str) -> Any | None:
        """Get fallback policy for given type.

        Args:
            policy_type: Policy type to look up.

        Returns:
            Policy dict or None if not found.
        """
        if self._registry is None:
            return None

        try:
            return self._registry.get_default_policy(policy_type)
        except KeyError, ValueError:
            return None

    def override_task_line_policy(self, policy: Any) -> None:
        """Override the task line parsing policy at runtime.

        Args:
            policy: PreparedTaskLineParsingPolicy implementation.

        Raises:
            TypeError: If policy shape invalid.
        """
        raise NotImplementedError("Wave 2: override_task_line_policy")

    def override_annotation_policy(self, policy: Any) -> None:
        """Override the task annotation parsing policy at runtime.

        Args:
            policy: PreparedTaskAnnotationPolicy implementation.

        Raises:
            TypeError: If policy shape invalid.
        """
        raise NotImplementedError("Wave 2: override_annotation_policy")

    def override_traversal_policy(self, policy: Any) -> None:
        """Override the task traversal policy at runtime.

        Args:
            policy: PreparedTaskTraversalPolicy implementation.

        Raises:
            TypeError: If policy shape invalid.
        """
        raise NotImplementedError("Wave 2: override_traversal_policy")

    def override_variable_extractor_policy(self, policy: Any) -> None:
        """Override the variable extractor policy at runtime.

        Args:
            policy: PreparedVariableExtractorPolicy implementation.

        Raises:
            TypeError: If policy shape invalid.
        """
        raise NotImplementedError("Wave 2: override_variable_extractor_policy")

    def get_default_platform_policy(self) -> dict[str, Any]:
        """Get the default platform policy from registry.

        Returns:
            Default policy dict for current platform.

        Raises:
            PrismRuntimeError: If no default policy configured.
        """
        raise NotImplementedError("Wave 3: get_default_platform_policy")

    def validate_policy_bundle(self, bundle: PreparedPolicyBundle) -> bool:
        """Validate that a prepared bundle has all required policies.

        Args:
            bundle: PreparedPolicyBundle to validate.

        Returns:
            True if bundle is valid and complete.

        Raises:
            ValueError: If validation fails (Wave 4).
        """
        raise NotImplementedError("Wave 4: validate_policy_bundle")

    def _cache_bundle(self, bundle: Any, scan_id: str, platform_key: str) -> None:
        """Cache a prepared policy bundle at scan ingress.

        Args:
            bundle: PreparedPolicyBundle to cache.
            scan_id: Unique scan identifier.
            platform_key: Platform key (e.g., 'ansible', 'kubernetes').
        """
        with self._cache_lock:
            key = (scan_id, platform_key)
            self._bundle_cache[key] = bundle

            if len(self._bundle_cache) > self._bundle_cache_max_size:
                oldest_key = next(iter(self._bundle_cache))
                del self._bundle_cache[oldest_key]

    def _get_cached_bundle(self, scan_id: str, platform_key: str) -> Any | None:
        """Retrieve cached bundle if available.

        Args:
            scan_id: Unique scan identifier.
            platform_key: Platform key.

        Returns:
            Cached PreparedPolicyBundle or None if miss.
        """
        with self._cache_lock:
            key = (scan_id, platform_key)
            return self._bundle_cache.get(key)

    def _cache_policy(self, policy_type: str, platform_key: str, policy: Any) -> None:
        """Cache a resolved policy.

        Args:
            policy_type: Type of policy (e.g., 'task_line_parsing').
            platform_key: Platform key.
            policy: Policy object to cache.
        """
        with self._cache_lock:
            key = (policy_type, platform_key)
            self._policy_cache[key] = policy

    def _get_cached_policy(self, policy_type: str, platform_key: str) -> Any | None:
        """Retrieve cached policy if available.

        Args:
            policy_type: Type of policy.
            platform_key: Platform key.

        Returns:
            Cached policy object or None if miss.
        """
        with self._cache_lock:
            key = (policy_type, platform_key)
            return self._policy_cache.get(key)

    def _make_preresolved_cache_key(self, scan_options: dict[str, object]) -> str:
        """Create a stable hash key for scan_options.

        Args:
            scan_options: Scan options dict.

        Returns:
            Stable hash key for caching.
        """
        import hashlib
        import json

        options_str = json.dumps(
            {k: str(v) for k, v in scan_options.items()}, sort_keys=True
        )
        return hashlib.sha256(options_str.encode()).hexdigest()

    def _cache_preresolved(
        self, scan_options: dict[str, object], bundle: dict[str, Any]
    ) -> None:
        """Cache pre-resolved collections bundle.

        Args:
            scan_options: Scan options used to generate bundle.
            bundle: Pre-resolved policies bundle.
        """
        with self._cache_lock:
            key = self._make_preresolved_cache_key(scan_options)
            self._preresolved_cache[key] = bundle

    def _get_cached_preresolved(
        self, scan_options: dict[str, object]
    ) -> dict[str, Any] | None:
        """Retrieve cached pre-resolved bundle if available.

        Args:
            scan_options: Scan options to look up.

        Returns:
            Cached bundle or None if miss.
        """
        with self._cache_lock:
            key = self._make_preresolved_cache_key(scan_options)
            return self._preresolved_cache.get(key)

    def clear_caches(self) -> None:
        """Clear all cache levels (bundle, policy, pre-resolved).

        Called on scan end or platform change. Thread-safe.
        """
        with self._cache_lock:
            self._bundle_cache.clear()
            self._policy_cache.clear()
            self._preresolved_cache.clear()

    def invalidate_platform_cache(self, platform_key: str) -> None:
        """Invalidate cache entries for a specific platform.

        Args:
            platform_key: Platform key to invalidate.
        """
        with self._cache_lock:
            to_delete = [
                key for key in self._policy_cache.keys() if key[1] == platform_key
            ]
            for key in to_delete:
                del self._policy_cache[key]

            to_delete_bundle = [
                key for key in self._bundle_cache.keys() if key[1] == platform_key
            ]
            for key in to_delete_bundle:
                del self._bundle_cache[key]


@runtime_checkable
class PolicyResolutionContract(Protocol):
    """Protocol for objects that can resolve policies."""

    def resolve_prepared_bundle(
        self,
        *,
        scan_options: dict[str, object],
    ) -> PreparedPolicyBundle:
        """Resolve a complete prepared policy bundle."""
        ...
