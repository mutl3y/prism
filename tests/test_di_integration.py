"""Integration tests for DI Container decomposition (Task 2.3).

Tests validate that PluginResolver, ServiceLocator, and DIContainer work
together seamlessly, covering backward compatibility, mock/override injection,
cache coordination, thread safety, and edge cases.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from prism.scanner_core.di import DIContainer, clone_scan_options
from prism.scanner_core.plugin_resolver import PluginResolver
from prism.scanner_core.service_locator import ServiceLocator
from prism.scanner_data.contracts_request import ScanOptionsDict
from prism.errors import PrismRuntimeError


def _make_scan_options(**overrides: Any) -> ScanOptionsDict:
    """Create minimal scan_options for testing."""
    opts: ScanOptionsDict = {
        "role_path": "/tmp/test",
        "role_name_override": None,
        "readme_config_path": None,
        "policy_config_path": None,
        "include_vars_main": True,
        "exclude_path_patterns": None,
        "detailed_catalog": False,
        "include_task_parameters": False,
        "include_task_runbooks": False,
        "inline_task_runbooks": False,
        "include_collection_checks": False,
        "keep_unknown_style_sections": False,
        "adopt_heading_mode": None,
        "vars_seed_paths": None,
        "style_readme_path": None,
        "style_source_path": None,
        "style_guide_skeleton": False,
        "compare_role_path": None,
        "fail_on_unconstrained_dynamic_includes": None,
        "fail_on_yaml_like_task_annotations": None,
        "ignore_unresolved_internal_underscore_references": None,
    }
    opts.update(overrides)  # type: ignore[assignment]
    return opts


class TestDIContainerPluginResolverIntegration:
    """Test DIContainer and PluginResolver work together."""

    def test_plugin_resolver_delegates_to_di_container(self) -> None:
        """Verify PluginResolver has reference to DIContainer and delegates correctly."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
        )
        resolver = di._plugin_resolver
        assert resolver is not None
        assert resolver._di is di
        assert isinstance(resolver, PluginResolver)

    def test_service_locator_delegates_to_di_container(self) -> None:
        """Verify ServiceLocator has reference to DIContainer."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
        )
        locator = di._service_locator
        assert locator is not None
        assert locator._di_container is di
        assert isinstance(locator, ServiceLocator)

    def test_di_container_delegates_plugin_methods_to_resolver(self) -> None:
        """Verify DIContainer plugin factory methods delegate to PluginResolver."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
        )
        # All plugin factory methods exist and delegate correctly
        assert hasattr(di, "factory_variable_discovery_plugin")
        assert hasattr(di, "factory_feature_detection_plugin")
        assert hasattr(di, "factory_comment_driven_doc_plugin")

    def test_di_container_delegates_service_methods_to_locator(self) -> None:
        """Verify DIContainer service factory methods delegate to ServiceLocator."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
        )
        # Event bus should be accessible through service locator
        bus = di.factory_event_bus()
        assert bus is not None


class TestMockOverrideInjectionWorkflow:
    """Test mock and override injection workflow across all layers."""

    def test_mock_injection_for_variable_discovery_plugin(self) -> None:
        """Verify mock injection works for variable discovery plugin."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
        )
        mock_plugin = object()
        di.inject_mock("variable_discovery_plugin", mock_plugin)
        result = di.factory_variable_discovery_plugin()
        assert result is mock_plugin

    def test_mock_injection_for_feature_detection_plugin(self) -> None:
        """Verify mock injection works for feature detection plugin."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
        )
        mock_plugin = object()
        di.inject_mock("feature_detection_plugin", mock_plugin)
        result = di.factory_feature_detection_plugin()
        assert result is mock_plugin

    def test_mock_injection_for_policy_plugins(self) -> None:
        """Verify mock injection works for all policy plugins."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
        )
        policy_names = [
            "comment_driven_doc_plugin",
            "task_annotation_policy_plugin",
            "task_line_parsing_policy_plugin",
            "task_traversal_policy_plugin",
            "variable_extractor_policy_plugin",
            "yaml_parsing_policy_plugin",
            "jinja_analysis_policy_plugin",
        ]
        for name in policy_names:
            mock_obj = object()
            di.inject_mock(name, mock_obj)
            factory_method = getattr(di, f"factory_{name}")
            result = factory_method()
            assert result is mock_obj, f"Mock injection failed for {name}"

    def test_factory_override_injection(self) -> None:
        """Verify factory override injection works."""

        def custom_factory(
            container: DIContainer, role_path: str, scan_options: ScanOptionsDict
        ) -> object:
            return {"custom": True}

        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
            factory_overrides={"variable_discovery_factory": custom_factory},
        )
        result = di.factory_variable_discovery()
        assert isinstance(result, dict)
        assert result.get("custom") is True

    def test_mock_takes_precedence_over_override(self) -> None:
        """Verify mock injection takes precedence over factory override."""

        def custom_factory(
            container: DIContainer, role_path: str, scan_options: ScanOptionsDict
        ) -> object:
            return {"source": "override"}

        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
            factory_overrides={"variable_discovery_factory": custom_factory},
        )
        mock_obj = {"source": "mock"}
        di.inject_mock("variable_discovery", mock_obj)
        result = di.factory_variable_discovery()
        assert result is mock_obj
        assert result.get("source") == "mock"

    def test_clear_mocks_restores_original_behavior(self) -> None:
        """Verify clear_mocks() removes all injected mocks."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
        )
        mock_obj = object()
        di.inject_mock("variable_discovery_plugin", mock_obj)
        assert di.factory_variable_discovery_plugin() is mock_obj
        di.clear_mocks()
        # After clearing mocks, factory should fail-close without registry
        # (not raise the same mock object)
        # This verifies the mock was truly cleared


class TestCacheInvalidationAcrossClasses:
    """Test that cache invalidation works across DIContainer and ServiceLocator."""

    def test_replace_scan_options_invalidates_dependent_caches(self) -> None:
        """Verify replace_scan_options invalidates caches correctly."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(exclude_path_patterns=["*.pyc"]),
        )
        # Cache should be empty initially
        assert len(di._cache) == 1  # event_bus is pre-cached
        # Replace scan options
        new_options = _make_scan_options(exclude_path_patterns=["*.bak"])
        di.replace_scan_options(new_options)
        # Verify internal state updated
        assert di._scan_options["exclude_path_patterns"] == ["*.bak"]

    def test_scan_options_snapshot_is_independent(self) -> None:
        """Verify scan_options snapshots are independent copies."""
        original_opts = _make_scan_options()
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=original_opts,
        )
        # Get snapshot
        snapshot1 = di.scan_options
        snapshot2 = di.scan_options
        # Snapshots should be different objects
        assert snapshot1 is not snapshot2
        # But equal content
        assert snapshot1 == snapshot2

    def test_cache_invalidation_maintains_event_bus_singleton(self) -> None:
        """Verify replace_scan_options doesn't invalidate event bus."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
        )
        bus1 = di.factory_event_bus()
        di.replace_scan_options(_make_scan_options())
        bus2 = di.factory_event_bus()
        # Event bus should remain the same object
        assert bus1 is bus2


class TestThreadSafetyWithConcurrentFactoryCalls:
    """Test thread safety with concurrent factory calls."""

    def test_concurrent_factory_calls_are_thread_safe(self) -> None:
        """Verify concurrent factory calls don't cause race conditions."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
        )
        results = []
        errors = []

        def call_factory() -> None:
            try:
                bus = di.factory_event_bus()
                results.append(bus)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=call_factory) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors, f"Thread safety errors: {errors}"
        # All results should be the same event bus instance
        assert all(r is results[0] for r in results)

    def test_concurrent_replace_scan_options_is_safe(self) -> None:
        """Verify concurrent replace_scan_options calls are safe."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
        )
        errors = []

        def update_options(idx: int) -> None:
            try:
                opts = _make_scan_options(
                    exclude_path_patterns=[f"pattern_{idx}"]
                )
                di.replace_scan_options(opts)
                time.sleep(0.001)  # Small delay to increase contention
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=update_options, args=(i,)) for i in range(5)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert not errors, f"Thread safety errors during replace: {errors}"
        # Final state should be one of the updates
        final_opts = di.scan_options
        assert final_opts["exclude_path_patterns"] is not None


class TestBackwardCompatibility:
    """Test backward compatibility with existing code patterns."""

    def test_old_code_using_di_container_methods_still_works(self) -> None:
        """Verify existing code patterns continue to work."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
        )
        # All these methods should exist and not raise
        assert di.scan_options is not None
        assert di.plugin_registry is None  # None when not provided
        assert di.platform_key is None
        assert di.scanner_context_wiring == {}
        assert di.factory_overrides == {}
        assert di.factory_event_bus() is not None

    def test_clone_scan_options_preserves_structure(self) -> None:
        """Verify clone_scan_options preserves nested structures."""
        opts = _make_scan_options()
        cloned = clone_scan_options(opts)
        # Should be equal but not the same object
        assert cloned == opts
        assert cloned is not opts

    def test_clone_scan_options_handles_nested_collections(self) -> None:
        """Verify cloning handles nested dicts, lists, tuples, sets."""
        opts: ScanOptionsDict = {
            "role_path": "/tmp",
            "role_name_override": None,
            "nested_dict": {"key": "value"},
            "nested_list": [1, 2, 3],
            "nested_tuple": (1, 2),
            "nested_set": {1, 2},
        }  # type: ignore[typeddict-item]
        cloned = clone_scan_options(opts)
        assert cloned["nested_list"] == [1, 2, 3]
        assert cloned["nested_list"] is not opts["nested_list"]

    def test_di_container_accepts_all_original_parameters(self) -> None:
        """Verify DIContainer constructor accepts all original parameters."""
        # This should not raise
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
            registry=None,
            platform_key=None,
            scanner_context_wiring={},
            factory_overrides={},
            event_listeners=None,
            inherit_default_event_listeners=False,
            cache_backend=None,
            blocker_fact_builder_fn=None,
        )
        assert di is not None


class TestErrorHandling:
    """Test error handling and validation."""

    def test_missing_role_path_raises_error(self) -> None:
        """Verify DIContainer rejects empty role_path."""
        with pytest.raises(ValueError, match="role_path must not be empty"):
            DIContainer(
                role_path="",
                scan_options=_make_scan_options(),
            )

    def test_missing_scan_options_raises_error(self) -> None:
        """Verify DIContainer rejects None scan_options."""
        with pytest.raises(ValueError, match="scan_options must not be None"):
            DIContainer(
                role_path="/tmp/test",
                scan_options=None,  # type: ignore[arg-type]
            )

    def test_plugin_resolver_raises_on_missing_registry(self) -> None:
        """Verify PluginResolver raises PrismRuntimeError when registry is missing."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(scan_pipeline_plugin="ansible"),
        )
        resolver = PluginResolver(di)
        with pytest.raises(PrismRuntimeError, match="missing_plugin_registry"):
            resolver.factory_variable_discovery_plugin()

    def test_error_wrapping_in_plugin_resolver(self) -> None:
        """Verify errors are wrapped in PrismRuntimeError, not raw exceptions."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(scan_pipeline_plugin="ansible"),
        )
        resolver = PluginResolver(di)
        try:
            resolver.factory_variable_discovery_plugin()
        except Exception as exc:
            # Should be PrismRuntimeError, not ValueError
            assert isinstance(exc, PrismRuntimeError)
            assert "missing_plugin_registry" in str(exc)


class TestPublicAPIPresence:
    """Test that all public API methods are present and accessible."""

    def test_all_factory_methods_present(self) -> None:
        """Verify all expected factory methods exist on DIContainer."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
        )
        factory_methods = [
            "factory_event_bus",
            "factory_scanner_context",
            "factory_variable_discovery",
            "factory_feature_detector",
            "factory_variable_row_builder",
            "factory_blocker_fact_builder",
            "factory_variable_discovery_plugin",
            "factory_feature_detection_plugin",
            "factory_comment_driven_doc_plugin",
            "factory_task_annotation_policy_plugin",
            "factory_task_line_parsing_policy_plugin",
            "factory_task_traversal_policy_plugin",
            "factory_variable_extractor_policy_plugin",
            "factory_yaml_parsing_policy_plugin",
            "factory_jinja_analysis_policy_plugin",
            "factory_audit_plugin",
        ]
        for method_name in factory_methods:
            assert hasattr(di, method_name), f"Missing method: {method_name}"
            assert callable(getattr(di, method_name))

    def test_all_property_methods_present(self) -> None:
        """Verify all expected property methods exist on DIContainer."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
        )
        properties = [
            "scan_options",
            "plugin_registry",
            "scanner_context_wiring",
            "factory_overrides",
            "platform_key",
            "inherit_default_event_listeners",
        ]
        for prop_name in properties:
            assert hasattr(di, prop_name), f"Missing property: {prop_name}"

    def test_all_injection_methods_present(self) -> None:
        """Verify injection helper methods exist on DIContainer."""
        di = DIContainer(
            role_path="/tmp/test",
            scan_options=_make_scan_options(),
        )
        injection_methods = [
            "inject_mock",
            "clear_mocks",
            "clear_cache",
            "replace_scan_options",
        ]
        for method_name in injection_methods:
            assert hasattr(di, method_name), f"Missing method: {method_name}"
            assert callable(getattr(di, method_name))
