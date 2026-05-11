"""Integration tests for Kubernetes README renderer output contracts (Wave 3).

Tests verify that the renderer produces meaningful output from metadata,
with stateless contract compliance and proper handling of section bodies
and identity sections.
"""

from __future__ import annotations
from typing import Any

from prism.scanner_plugins.kubernetes.readme_renderer import (
    KubernetesReadmeRendererPlugin,
)


class TestKubernetesRendererSectionBodyContracts:
    """Test K8s renderer section_body contract with metadata-driven output."""

    def test_render_purpose_section_with_metadata(self) -> None:
        """Purpose section should use description or role name."""
        renderer = KubernetesReadmeRendererPlugin()
        
        # Test with description
        body = renderer.render_section_body(
            section_id="purpose",
            role_name="nginx-deployment",
            description="Production nginx reverse proxy",
            variables={},
            requirements=[],
            default_filters=[],
            metadata={},
        )
        
        assert body is not None
        assert "Production nginx reverse proxy" in body

    def test_render_purpose_section_fallback_to_role_name(self) -> None:
        """Purpose section should fallback to role name if no description."""
        renderer = KubernetesReadmeRendererPlugin()
        
        body = renderer.render_section_body(
            section_id="purpose",
            role_name="nginx-deployment",
            description="",
            variables={},
            requirements=[],
            default_filters=[],
            metadata={},
        )
        
        assert body is not None
        assert "nginx-deployment" in body

    def test_render_resources_section_with_inventory(self) -> None:
        """Resources section should format resource list from metadata."""
        renderer = KubernetesReadmeRendererPlugin()
        metadata: dict[str, Any] = {
            "resource_kinds": ["Deployment", "Service", "ConfigMap", "Secret"]
        }
        
        body = renderer.render_section_body(
            section_id="resources",
            role_name="app",
            description="",
            variables={},
            requirements=[],
            default_filters=[],
            metadata=metadata,
        )
        
        assert body is not None
        assert "Deployment" in body
        assert "Service" in body
        assert "ConfigMap" in body
        assert "Secret" in body
        # Should be formatted as bullet list
        assert "- `Deployment`" in body

    def test_render_resources_section_empty_metadata(self) -> None:
        """Resources section should report unavailable for empty metadata."""
        renderer = KubernetesReadmeRendererPlugin()
        
        body = renderer.render_section_body(
            section_id="resources",
            role_name="app",
            description="",
            variables={},
            requirements=[],
            default_filters=[],
            metadata={},
        )
        
        assert body is not None
        assert "available" in body.lower() or "inventory" in body.lower()

    def test_render_operational_notes_with_list(self) -> None:
        """Operational notes section should format list from metadata."""
        renderer = KubernetesReadmeRendererPlugin()
        metadata: dict[str, Any] = {
            "operational_notes": [
                "Requires network policy configuration",
                "Must run in dedicated namespace",
                "Pod security policy required",
            ]
        }
        
        body = renderer.render_section_body(
            section_id="operational_notes",
            role_name="app",
            description="",
            variables={},
            requirements=[],
            default_filters=[],
            metadata=metadata,
        )
        
        assert body is not None
        assert "Requires network policy" in body
        assert "Must run in dedicated" in body
        assert "Pod security policy" in body
        # Should be formatted as bullet list
        assert "- Requires network policy" in body

    def test_render_operational_notes_with_variables(self) -> None:
        """Operational notes should indicate bootstrap status when variables present."""
        renderer = KubernetesReadmeRendererPlugin()
        
        body = renderer.render_section_body(
            section_id="operational_notes",
            role_name="app",
            description="",
            variables={"var1": "value1"},  # Non-empty variables
            requirements=[],
            default_filters=[],
            metadata={},
        )
        
        assert body is not None
        assert "Bootstrap" in body or "not emitted yet" in body

    def test_render_scanner_report_with_path(self) -> None:
        """Scanner report section should link to report when available."""
        renderer = KubernetesReadmeRendererPlugin()
        metadata: dict[str, Any] = {
            "scanner_report_relpath": "reports/k8s-scan.md"
        }
        
        body = renderer.render_section_body(
            section_id="scanner_report",
            role_name="app",
            description="",
            variables={},
            requirements=[],
            default_filters=[],
            metadata=metadata,
        )
        
        assert body is not None
        assert "reports/k8s-scan.md" in body
        assert "Detailed scanner output" in body

    def test_render_scanner_report_unavailable(self) -> None:
        """Scanner report section should report unavailable when no path."""
        renderer = KubernetesReadmeRendererPlugin()
        
        body = renderer.render_section_body(
            section_id="scanner_report",
            role_name="app",
            description="",
            variables={},
            requirements=[],
            default_filters=[],
            metadata={},
        )
        
        assert body is not None
        assert "bootstrap" in body.lower() or "not wired" in body.lower()

    def test_render_unknown_section_returns_none(self) -> None:
        """Unknown section IDs should return None."""
        renderer = KubernetesReadmeRendererPlugin()
        
        body = renderer.render_section_body(
            section_id="unknown_section",
            role_name="app",
            description="",
            variables={},
            requirements=[],
            default_filters=[],
            metadata={},
        )
        
        assert body is None


class TestKubernetesRendererIdentitySectionContracts:
    """Test K8s renderer identity_section contract with identity metadata."""

    def test_render_identity_purpose_with_namespace(self) -> None:
        """Identity purpose should include namespace from identity_metadata."""
        renderer = KubernetesReadmeRendererPlugin()
        identity_metadata: dict[str, Any] = {
            "namespace": "production"
        }
        
        body = renderer.render_identity_section(
            section_id="purpose",
            role_name="app",
            description="Main application",
            requirements=[],
            identity_metadata=identity_metadata,
            metadata={},
        )
        
        assert body is not None
        assert "Main application" in body
        assert "production" in body
        assert "namespace" in body.lower()

    def test_render_identity_purpose_without_namespace(self) -> None:
        """Identity purpose should fallback to description without namespace."""
        renderer = KubernetesReadmeRendererPlugin()
        
        body = renderer.render_identity_section(
            section_id="purpose",
            role_name="app",
            description="Main application",
            requirements=[],
            identity_metadata={},
            metadata={},
        )
        
        assert body is not None
        assert "Main application" in body
        assert "namespace" not in body.lower()

    def test_render_identity_resources_with_cluster(self) -> None:
        """Identity resources should include cluster info from identity_metadata."""
        renderer = KubernetesReadmeRendererPlugin()
        identity_metadata: dict[str, Any] = {
            "cluster": "us-west-2-prod"
        }
        
        body = renderer.render_identity_section(
            section_id="resources",
            role_name="app",
            description="",
            requirements=[],
            identity_metadata=identity_metadata,
            metadata={},
        )
        
        assert body is not None
        assert "us-west-2-prod" in body
        assert "Cluster" in body

    def test_render_identity_resources_without_cluster(self) -> None:
        """Identity resources should report undeclared when no cluster."""
        renderer = KubernetesReadmeRendererPlugin()
        
        body = renderer.render_identity_section(
            section_id="resources",
            role_name="app",
            description="",
            requirements=[],
            identity_metadata={},
            metadata={},
        )
        
        assert body is not None
        assert "not declared" in body.lower()

    def test_render_identity_unknown_section_returns_none(self) -> None:
        """Unknown identity section IDs should return None."""
        renderer = KubernetesReadmeRendererPlugin()
        
        body = renderer.render_identity_section(
            section_id="unknown",
            role_name="app",
            description="",
            requirements=[],
            identity_metadata={},
            metadata={},
        )
        
        assert body is None


class TestKubernetesRendererStatelessContract:
    """Test that renderer maintains stateless contract."""

    def test_renderer_is_stateless(self) -> None:
        """Renderer should declare PLUGIN_IS_STATELESS = True."""
        renderer = KubernetesReadmeRendererPlugin()
        assert renderer.PLUGIN_IS_STATELESS is True

    def test_renderer_has_api_version(self) -> None:
        """Renderer should declare PRISM_PLUGIN_API_VERSION."""
        renderer = KubernetesReadmeRendererPlugin()
        assert hasattr(renderer, "PRISM_PLUGIN_API_VERSION")
        assert renderer.PRISM_PLUGIN_API_VERSION == (1, 0)

    def test_multiple_instances_produce_identical_output(self) -> None:
        """Stateless renderer instances should produce identical output."""
        renderer1 = KubernetesReadmeRendererPlugin()
        renderer2 = KubernetesReadmeRendererPlugin()
        
        metadata: dict[str, Any] = {
            "resource_kinds": ["Pod", "Service"],
            "operational_notes": ["Note 1", "Note 2"],
        }
        
        output1 = renderer1.render_section_body(
            section_id="resources",
            role_name="test",
            description="Test",
            variables={"v": "1"},
            requirements=[],
            default_filters=[],
            metadata=metadata,
        )
        
        output2 = renderer2.render_section_body(
            section_id="resources",
            role_name="test",
            description="Test",
            variables={"v": "1"},
            requirements=[],
            default_filters=[],
            metadata=metadata,
        )
        
        assert output1 == output2
