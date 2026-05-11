"""Test Kubernetes feature detection and variable discovery plugins."""

from __future__ import annotations

from prism.scanner_plugins.kubernetes import (
    KubernetesFeatureDetectionPlugin,
    KubernetesVariableDiscoveryPlugin,
)
from prism.tests.fixtures.fixtures_kubernetes_pipeline import (
    build_kubernetes_scan_context,
    build_kubernetes_scan_options,
)


class TestKubernetesFeatureDetectionPlugin:
    """Tests for Kubernetes feature detection contract."""

    def test_kubernetes_feature_detection_plugin_is_stateless(self) -> None:
        """Verify plugin satisfies stateless contract."""
        assert KubernetesFeatureDetectionPlugin.PLUGIN_IS_STATELESS is True

    def test_kubernetes_feature_detection_plugin_detects_features(self) -> None:
        """Verify plugin detects Kubernetes-specific features."""
        plugin = KubernetesFeatureDetectionPlugin()
        
        features = plugin.detect_features(
            role_path="/tmp/k8s-demo",
            options=build_kubernetes_scan_options(),
        )
        
        assert isinstance(features, dict)
        assert "task_files_scanned" in features
        assert features["task_files_scanned"] == 0
        assert features["tasks_scanned"] == 0

    def test_kubernetes_feature_detection_plugin_analyzes_task_catalog(
        self,
    ) -> None:
        """Verify plugin can analyze task catalog (returns empty for bootstrap)."""
        plugin = KubernetesFeatureDetectionPlugin()
        
        catalog = plugin.analyze_task_catalog(
            role_path="/tmp/k8s-demo",
            options=build_kubernetes_scan_options(),
        )
        
        assert isinstance(catalog, dict)
        assert len(catalog) == 0

    def test_kubernetes_feature_detection_plugin_init_accepts_di(self) -> None:
        """Verify plugin accepts optional DI container."""
        plugin = KubernetesFeatureDetectionPlugin(di=None)
        assert plugin is not None


class TestKubernetesVariableDiscoveryPlugin:
    """Tests for Kubernetes variable discovery contract."""

    def test_kubernetes_variable_discovery_plugin_is_stateless(self) -> None:
        """Verify plugin satisfies stateless contract."""
        assert KubernetesVariableDiscoveryPlugin.PLUGIN_IS_STATELESS is True

    def test_kubernetes_variable_discovery_plugin_discovers_static_variables(
        self,
    ) -> None:
        """Verify plugin discovers static variables (empty for bootstrap)."""
        plugin = KubernetesVariableDiscoveryPlugin()
        
        variables = plugin.discover_static_variables(
            role_path="/tmp/k8s-demo",
            options=build_kubernetes_scan_options(),
        )
        
        assert isinstance(variables, tuple)
        assert len(variables) == 0

    def test_kubernetes_variable_discovery_plugin_discovers_referenced_variables(
        self,
    ) -> None:
        """Verify plugin discovers referenced variables (empty for bootstrap)."""
        plugin = KubernetesVariableDiscoveryPlugin()
        
        variables = plugin.discover_referenced_variables(
            role_path="/tmp/k8s-demo",
            options=build_kubernetes_scan_options(),
        )
        
        assert isinstance(variables, frozenset)
        assert len(variables) == 0

    def test_kubernetes_variable_discovery_plugin_resolves_unresolved_variables(
        self,
    ) -> None:
        """Verify plugin resolves unresolved variables (empty for bootstrap)."""
        plugin = KubernetesVariableDiscoveryPlugin()
        
        resolved = plugin.resolve_unresolved_variables(
            static_names=frozenset(),
            referenced=frozenset(),
            options=build_kubernetes_scan_options(),
        )
        
        assert isinstance(resolved, dict)
        assert len(resolved) == 0

    def test_kubernetes_variable_discovery_plugin_init_accepts_di(self) -> None:
        """Verify plugin accepts optional DI container."""
        plugin = KubernetesVariableDiscoveryPlugin(di=None)
        assert plugin is not None
