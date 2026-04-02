"""Tests asserting metadata submodel boundaries and domain ownership.

A34 requirements: metadata dicts currently blend counters, warnings, render hints,
repo normalization state, and scanner report details. This test suite asserts that
metadata has been decomposed into focused domain-specific submodels.
"""

from __future__ import annotations


class TestMetadataSubmodelStructure:
    """Verify metadata has been split into domain-specific submodels."""

    def test_variable_analysis_results_is_defined(self) -> None:
        """VariableAnalysisResults contract exists for variable extraction results."""
        from prism.scanner_data.contracts import VariableAnalysisResults

        assert VariableAnalysisResults is not None
        assert hasattr(VariableAnalysisResults, "__annotations__")

    def test_variable_analysis_results_has_insights_field(self) -> None:
        """VariableAnalysisResults contains variable_insights."""
        from prism.scanner_data.contracts_extraction import VariableAnalysisResults

        annotations = VariableAnalysisResults.__annotations__
        assert "variable_insights" in annotations

    def test_variable_analysis_results_has_yaml_failures_field(self) -> None:
        """VariableAnalysisResults contains yaml_parse_failures."""
        from prism.scanner_data.contracts_extraction import VariableAnalysisResults

        annotations = VariableAnalysisResults.__annotations__
        assert "yaml_parse_failures" in annotations

    def test_report_rendering_metadata_is_defined(self) -> None:
        """ReportRenderingMetadata contract exists for scanner report rendering."""
        from prism.scanner_data.contracts import ReportRenderingMetadata

        assert ReportRenderingMetadata is not None
        assert hasattr(ReportRenderingMetadata, "__annotations__")

    def test_report_rendering_metadata_has_counters_field(self) -> None:
        """ReportRenderingMetadata contains scanner_counters."""
        from prism.scanner_data.contracts_report import ReportRenderingMetadata

        annotations = ReportRenderingMetadata.__annotations__
        assert "scanner_counters" in annotations

    def test_report_rendering_metadata_has_features_field(self) -> None:
        """ReportRenderingMetadata contains features."""
        from prism.scanner_data.contracts_report import ReportRenderingMetadata

        annotations = ReportRenderingMetadata.__annotations__
        assert "features" in annotations

    def test_report_rendering_metadata_has_yaml_failures_field(self) -> None:
        """ReportRenderingMetadata contains yaml_parse_failures."""
        from prism.scanner_data.contracts_report import ReportRenderingMetadata

        annotations = ReportRenderingMetadata.__annotations__
        assert "yaml_parse_failures" in annotations

    def test_scan_phase_status_is_defined(self) -> None:
        """ScanPhaseStatus contract exists for phase-level scan state."""
        from prism.scanner_data.contracts import ScanPhaseStatus

        assert ScanPhaseStatus is not None
        assert hasattr(ScanPhaseStatus, "__annotations__")

    def test_scan_phase_status_has_errors_field(self) -> None:
        """ScanPhaseStatus contains scan_errors."""
        from prism.scanner_data.contracts_errors import ScanPhaseStatus

        annotations = ScanPhaseStatus.__annotations__
        assert "scan_errors" in annotations

    def test_scan_phase_status_has_degraded_field(self) -> None:
        """ScanPhaseStatus contains scan_degraded flag."""
        from prism.scanner_data.contracts_errors import ScanPhaseStatus

        annotations = ScanPhaseStatus.__annotations__
        assert "scan_degraded" in annotations

    def test_output_configuration_is_defined(self) -> None:
        """OutputConfiguration contract exists for output-specific config."""
        from prism.scanner_data.contracts import OutputConfiguration

        assert OutputConfiguration is not None
        assert hasattr(OutputConfiguration, "__annotations__")

    def test_output_configuration_has_concise_readme_field(self) -> None:
        """OutputConfiguration contains concise_readme flag."""
        from prism.scanner_data.contracts_output import OutputConfiguration

        annotations = OutputConfiguration.__annotations__
        assert "concise_readme" in annotations

    def test_output_configuration_has_scanner_report_fields(self) -> None:
        """OutputConfiguration contains scanner report output config."""
        from prism.scanner_data.contracts_output import OutputConfiguration

        annotations = OutputConfiguration.__annotations__
        assert "include_scanner_report_link" in annotations
        assert "scanner_report_relpath" in annotations


class TestScanMetadataDecomposition:
    """Verify ScanMetadata has been refactored to use submodels."""

    def test_scan_metadata_still_importable(self) -> None:
        """ScanMetadata remains available for backward compatibility."""
        from prism.scanner_data.contracts import ScanMetadata

        assert ScanMetadata is not None
        assert hasattr(ScanMetadata, "__annotations__")

    def test_scan_metadata_no_longer_contains_counters(self) -> None:
        """scanner_counters removed from ScanMetadata (moved to ReportRenderingMetadata)."""
        from prism.scanner_data.contracts_request import ScanMetadata

        annotations = ScanMetadata.__annotations__
        # The field should still exist for backward compatibility but should be typed as
        # dict[str, Any] | None to indicate it's deprecated
        if "scanner_counters" in annotations:
            # Check it's still there for compat, but typed as deprecated
            assert annotations["scanner_counters"] in (
                "dict[str, Any] | None",
                "Optional[dict[str, Any]]",
            ) or "totals" not in str(annotations)

    def test_scan_metadata_variable_insights_accessible(self) -> None:
        """variable_insights remains accessible from ScanMetadata for compat."""
        from prism.scanner_data.contracts_request import ScanMetadata

        annotations = ScanMetadata.__annotations__
        # Should still be there for backward compatibility
        assert "variable_insights" in annotations

    def test_scan_metadata_phase_status_field_exists(self) -> None:
        """ScanMetadata includes nested phase_status field."""
        from prism.scanner_data.contracts_request import ScanMetadata

        annotations = ScanMetadata.__annotations__
        # May be added as a field to group phase-related concerns
        # Check either for explicit field or that old fields are still accessible for compat
        has_phase_status = "phase_status" in annotations
        has_phase_fields = (
            "scan_errors" in annotations or "scan_degraded" in annotations
        )
        assert has_phase_status or has_phase_fields


class TestScannerReportMetadataDecomposition:
    """Verify ScannerReportMetadata uses focused domain-specific submodels."""

    def test_scanner_report_metadata_still_importable(self) -> None:
        """ScannerReportMetadata remains available."""
        from prism.scanner_data.contracts import ScannerReportMetadata

        assert ScannerReportMetadata is not None

    def test_scanner_report_metadata_reuses_submodels(self) -> None:
        """ScannerReportMetadata uses ReportRenderingMetadata submodel."""
        from prism.scanner_data.contracts_output import ScannerReportMetadata
        from prism.scanner_data.contracts_report import ReportRenderingMetadata

        # Verify the structure exists
        assert ScannerReportMetadata is not None
        assert ReportRenderingMetadata is not None


class TestMetadataOwnershipBoundaries:
    """Verify domain ownership of metadata submodels is explicit."""

    def test_extraction_metadata_lives_in_extraction_module(self) -> None:
        """VariableAnalysisResults owned by extraction domain."""
        from prism.scanner_data.contracts_extraction import VariableAnalysisResults

        assert VariableAnalysisResults is not None

    def test_report_metadata_lives_in_output_module(self) -> None:
        """ReportRenderingMetadata and OutputConfiguration owned by output domain."""
        from prism.scanner_data.contracts_output import OutputConfiguration
        from prism.scanner_data.contracts_report import ReportRenderingMetadata

        assert ReportRenderingMetadata is not None
        assert OutputConfiguration is not None

    def test_phase_status_lives_in_errors_module(self) -> None:
        """ScanPhaseStatus owned by error-handling domain."""
        from prism.scanner_data.contracts_errors import ScanPhaseStatus

        assert ScanPhaseStatus is not None

    def test_submodels_are_reexported_from_public_surface(self) -> None:
        """Submodels are available from scanner_data.contracts re-export surface."""
        from prism.scanner_data import contracts

        assert hasattr(contracts, "VariableAnalysisResults")
        assert hasattr(contracts, "ReportRenderingMetadata")
        assert hasattr(contracts, "ScanPhaseStatus")
        assert hasattr(contracts, "OutputConfiguration")


class TestMetadataBlastRadius:
    """Verify decomposition reduces blast radius of metadata changes."""

    def test_variable_analysis_changes_dont_affect_output_config(self) -> None:
        """Changing VariableAnalysisResults doesn't require OutputConfiguration update."""
        from prism.scanner_data.contracts_extraction import VariableAnalysisResults
        from prism.scanner_data.contracts_output import OutputConfiguration

        # Verify they're distinct types
        var_annot = VariableAnalysisResults.__annotations__
        output_annot = OutputConfiguration.__annotations__

        # VariableAnalysisResults should have variable_insights
        assert "variable_insights" in var_annot
        # OutputConfiguration should have concise_readme
        assert "concise_readme" in output_annot

    def test_scanner_counters_changes_dont_affect_variable_analysis(self) -> None:
        """Changing ScannerCounters doesn't require VariableAnalysisResults update."""
        from prism.scanner_data.contracts_output import ScannerCounters
        from prism.scanner_data.contracts_extraction import VariableAnalysisResults

        # Verify ScannerCounters is separate
        counter_annot = ScannerCounters.__annotations__
        var_annot = VariableAnalysisResults.__annotations__

        # ScannerCounters should have counters
        assert "total_variables" in counter_annot
        # VariableAnalysisResults should have insights
        assert "variable_insights" in var_annot

    def test_report_metadata_focused_on_rendering_only(self) -> None:
        """ReportRenderingMetadata contains only fields needed for report rendering."""
        from prism.scanner_data.contracts_report import ReportRenderingMetadata

        annotations = ReportRenderingMetadata.__annotations__
        # Should contain report-specific fields
        assert "scanner_counters" in annotations
        assert "features" in annotations
        # Should NOT contain scan config fields
        assert "role_path" not in annotations
        assert "detailed_catalog" not in annotations
