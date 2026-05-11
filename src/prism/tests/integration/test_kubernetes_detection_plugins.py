"""Test Kubernetes feature detection and variable discovery plugins."""

from __future__ import annotations

from pathlib import Path

from prism.scanner_plugins.kubernetes import (
    KubernetesFeatureDetectionPlugin,
    KubernetesReadmeRendererPlugin,
    KubernetesScanPipelinePlugin,
    KubernetesVariableDiscoveryPlugin,
)
from prism.tests.fixtures.fixtures_kubernetes_pipeline import (
    build_kubernetes_scan_context,
    build_kubernetes_scan_options,
)


def _fixture_role_path() -> str:
    return str(Path(__file__).resolve().parents[1] / "fixtures" / "kubernetes")


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

    def test_kubernetes_feature_detection_counts_manifest_inventory(self) -> None:
        """Real manifest fixtures should contribute deterministic counters."""
        plugin = KubernetesFeatureDetectionPlugin()
        options = build_kubernetes_scan_options()
        options["role_path"] = _fixture_role_path()

        features = plugin.detect_features(
            role_path=_fixture_role_path(),
            options=options,
        )

        assert features["task_files_scanned"] == 4
        assert features["tasks_scanned"] == 4
        assert features["unique_modules"] == "ConfigMap, Deployment, Secret, Service"
        assert features["privileged_tasks"] >= 1

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


class TestKubernetesScanPipelinePlugin:
    """Tests for Kubernetes scan-pipeline metadata population."""

    def test_process_scan_pipeline_populates_manifest_metadata(self) -> None:
        """Manifest fixtures should produce renderer-consumable metadata."""
        plugin = KubernetesScanPipelinePlugin()
        scan_options = build_kubernetes_scan_options()
        scan_options["role_path"] = _fixture_role_path()

        result = plugin.process_scan_pipeline(
            scan_options=scan_options,
            scan_context=build_kubernetes_scan_context(),
        )

        assert result["resource_kinds"] == [
            "ConfigMap",
            "Deployment",
            "Secret",
            "Service",
        ]
        assert "Service uses LoadBalancer exposure" in result["operational_notes"]
        assert "Deployment configures a liveness probe" in result["operational_notes"]
        assert "Deployment references Secret app-secrets via env" in result["operational_notes"]

    def test_process_scan_pipeline_outputs_renderer_consumable_metadata(self) -> None:
        """Pipeline metadata should render directly into Kubernetes README sections."""
        plugin = KubernetesScanPipelinePlugin()
        renderer = KubernetesReadmeRendererPlugin()
        scan_options = build_kubernetes_scan_options()
        scan_options["role_path"] = _fixture_role_path()

        metadata = plugin.process_scan_pipeline(
            scan_options=scan_options,
            scan_context=build_kubernetes_scan_context(),
        )

        resources_body = renderer.render_section_body(
            section_id="resources",
            role_name="mock-app",
            description="",
            variables={},
            requirements=[],
            default_filters=[],
            metadata=metadata,
        )
        notes_body = renderer.render_section_body(
            section_id="operational_notes",
            role_name="mock-app",
            description="",
            variables={},
            requirements=[],
            default_filters=[],
            metadata=metadata,
        )

        assert resources_body is not None
        assert "Deployment" in resources_body
        assert "Service" in resources_body
        assert notes_body is not None
        assert "LoadBalancer exposure" in notes_body
        assert "liveness probe" in notes_body
