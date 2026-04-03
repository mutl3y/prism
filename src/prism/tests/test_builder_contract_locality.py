"""Tests asserting that builders are co-located with the contracts they produce.

A33 requirement: each builder must be defined in the same domain module as the
contract TypedDict it constructs, not in a separate builders.py god-file.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from types import ModuleType

import prism.scanner_data.contracts_output as contracts_output_mod
import prism.scanner_data.contracts_variables as contracts_variables_mod
import prism.scanner_analysis.report as scanner_report_mod
import prism.scanner_core.feature_detector as feature_detector_mod
import prism.scanner_core.scan_context_builder as scan_context_builder_mod
import prism.scanner_core.scan_facade_helpers as scan_facade_helpers_mod
import prism.scanner_core.scan_request as scan_request_mod
import prism.scanner_core.scan_runtime as scan_runtime_mod
import prism.scanner_core.scanner_context as scanner_context_mod
import prism.scanner_core.variable_discovery as variable_discovery_mod
import prism.scanner_core.variable_insights as variable_insights_mod
import prism.scanner_core.variable_pipeline as variable_pipeline_mod
import prism.scanner_io.emit_output as emit_output_mod
import prism.scanner_io.output as output_mod
import prism.scanner_io.scan_output_emission as scan_output_emission_mod
import prism.scanner_io.scan_output_primary as scan_output_primary_mod
import prism.scanner_readme.render as readme_render_mod
from prism.scanner_data.builders import ScanPayloadBuilder, VariableRowBuilder
from prism.scanner_data.contracts_output import (
    RunScanOutputPayload,
    ScanPayloadBuilder as ScanPayloadBuilderDirect,
)
from prism.scanner_data.contracts_variables import (
    VariableRow,
    VariableRowBuilder as VariableRowBuilderDirect,
)


class TestVariableRowBuilderLocality:
    """VariableRowBuilder must live in contracts_variables (same module as VariableRow)."""

    def test_variable_row_builder_defined_in_contracts_variables(self) -> None:
        """VariableRowBuilder.__module__ points to contracts_variables."""
        assert VariableRowBuilderDirect.__module__.endswith("contracts_variables")

    def test_variable_row_builder_importable_from_contracts_variables(self) -> None:
        """VariableRowBuilder is directly importable from contracts_variables."""
        assert hasattr(contracts_variables_mod, "VariableRowBuilder")

    def test_variable_row_builder_in_contracts_variables_all(self) -> None:
        """VariableRowBuilder appears in contracts_variables.__all__."""
        assert "VariableRowBuilder" in contracts_variables_mod.__all__

    def test_variable_row_builder_and_variable_row_share_module(self) -> None:
        """VariableRowBuilder and VariableRow are in the same module."""
        builder_module = VariableRowBuilderDirect.__module__
        row_module = VariableRow.__module__
        assert builder_module == row_module

    def test_variable_row_builder_shim_is_same_class(self) -> None:
        """builders.VariableRowBuilder is the same object as contracts_variables.VariableRowBuilder."""
        assert VariableRowBuilder is VariableRowBuilderDirect

    def test_variable_row_builder_produces_variable_row(self) -> None:
        """VariableRowBuilder.build() returns a dict compatible with VariableRow."""
        row = VariableRowBuilder().name("x").type("string").build()
        # Verify key fields are present as expected by VariableRow
        assert row["name"] == "x"
        assert row["type"] == "string"


class TestScanPayloadBuilderLocality:
    """ScanPayloadBuilder must live in contracts_output (same module as RunScanOutputPayload)."""

    def test_scan_payload_builder_defined_in_contracts_output(self) -> None:
        """ScanPayloadBuilder.__module__ points to contracts_output."""
        assert ScanPayloadBuilderDirect.__module__.endswith("contracts_output")

    def test_scan_payload_builder_importable_from_contracts_output(self) -> None:
        """ScanPayloadBuilder is directly importable from contracts_output."""
        assert hasattr(contracts_output_mod, "ScanPayloadBuilder")

    def test_scan_payload_builder_in_contracts_output_all(self) -> None:
        """ScanPayloadBuilder appears in contracts_output.__all__."""
        assert "ScanPayloadBuilder" in contracts_output_mod.__all__

    def test_scan_payload_builder_and_run_scan_output_payload_share_module(
        self,
    ) -> None:
        """ScanPayloadBuilder and RunScanOutputPayload are in the same module."""
        builder_module = ScanPayloadBuilderDirect.__module__
        contract_module = RunScanOutputPayload.__module__
        assert builder_module == contract_module

    def test_scan_payload_builder_shim_is_same_class(self) -> None:
        """builders.ScanPayloadBuilder is the same object as contracts_output.ScanPayloadBuilder."""
        assert ScanPayloadBuilder is ScanPayloadBuilderDirect

    def test_scan_payload_builder_produces_run_scan_output_payload(self) -> None:
        """ScanPayloadBuilder.build() returns a RunScanOutputPayload-shaped dict."""
        payload = (
            ScanPayloadBuilder()
            .role_name("my_role")
            .description("desc")
            .metadata({})
            .build()
        )
        assert "role_name" in payload
        assert "metadata" in payload
        assert payload["role_name"] == "my_role"


class TestBuildersShimBackwardCompat:
    """builders.py shim must still export both builders for backward compatibility."""

    def test_builders_module_exports_variable_row_builder(self) -> None:
        import prism.scanner_data.builders as builders_mod

        assert hasattr(builders_mod, "VariableRowBuilder")

    def test_builders_module_exports_scan_payload_builder(self) -> None:
        import prism.scanner_data.builders as builders_mod

        assert hasattr(builders_mod, "ScanPayloadBuilder")

    def test_builders_variable_row_builder_is_not_redefined(self) -> None:
        """builders.py must not define its own VariableRowBuilder; it re-exports."""
        import prism.scanner_data.builders as builders_mod

        # The class defined location should be contracts_variables, not builders
        assert not builders_mod.VariableRowBuilder.__module__.endswith("builders")

    def test_builders_scan_payload_builder_is_not_redefined(self) -> None:
        """builders.py must not define its own ScanPayloadBuilder; it re-exports."""
        import prism.scanner_data.builders as builders_mod

        assert not builders_mod.ScanPayloadBuilder.__module__.endswith("builders")

    def test_builders_source_has_no_class_definition(self) -> None:
        """builders.py source code must not contain a 'class' keyword definition."""
        import prism.scanner_data.builders as builders_mod

        source = inspect.getsource(builders_mod)
        # Only re-export lines allowed; no class VariableRowBuilder or ScanPayloadBuilder
        assert "class VariableRowBuilder" not in source
        assert "class ScanPayloadBuilder" not in source


class TestOutputModulesImportCanonicalContracts:
    """Output-domain internals should import contracts from canonical owner modules."""

    def _imported_modules(self, module: ModuleType) -> set[str]:
        assert module.__file__ is not None
        return self._imported_modules_from_path(Path(module.__file__))

    def _imported_modules_from_path(self, path: Path) -> set[str]:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module)
        return imported

    def _assert_avoids_umbrella_contracts(self, module: ModuleType) -> set[str]:
        imported = self._imported_modules(module)
        assert "prism.scanner_data.contracts" not in imported
        assert "scanner_data.contracts" not in imported
        return imported

    def _assert_imports_owner_modules(
        self,
        module: ModuleType | Path,
        *owner_modules: str,
    ) -> None:
        imported = (
            self._assert_avoids_umbrella_contracts(module)
            if isinstance(module, ModuleType)
            else self._imported_modules_from_path(module)
        )
        if isinstance(module, Path):
            assert "prism.scanner_data.contracts" not in imported
            assert "scanner_data.contracts" not in imported
        for owner_module in owner_modules:
            assert any(
                imported_module.endswith(owner_module) for imported_module in imported
            ), (
                module.__name__ if isinstance(module, ModuleType) else str(module),
                imported,
                owner_module,
            )

    def test_scan_output_emission_imports_contracts_output_directly(self) -> None:
        self._assert_imports_owner_modules(
            scan_output_emission_mod,
            "scanner_data.contracts_output",
        )

    def test_scan_output_primary_imports_contracts_output_directly(self) -> None:
        self._assert_imports_owner_modules(
            scan_output_primary_mod,
            "scanner_data.contracts_output",
        )

    def test_output_imports_contracts_output_directly(self) -> None:
        self._assert_imports_owner_modules(
            output_mod,
            "scanner_data.contracts_output",
        )

    def test_emit_output_imports_contract_owner_modules_directly(self) -> None:
        self._assert_imports_owner_modules(
            emit_output_mod,
            "scanner_data.contracts_output",
            "scanner_data.contracts_request",
        )

    def test_scan_runtime_imports_contract_owner_modules_directly(self) -> None:
        self._assert_imports_owner_modules(
            scan_runtime_mod,
            "scanner_data.contracts_output",
            "scanner_data.contracts_request",
        )

    def test_scan_context_builder_imports_contracts_request_directly(self) -> None:
        self._assert_imports_owner_modules(
            scan_context_builder_mod,
            "scanner_data.contracts_request",
        )

    def test_scanner_context_imports_contracts_request_directly(self) -> None:
        self._assert_imports_owner_modules(
            scanner_context_mod,
            "scanner_data.contracts_request",
        )

    def test_scan_request_imports_contracts_request_directly(self) -> None:
        self._assert_imports_owner_modules(
            scan_request_mod,
            "scanner_data.contracts_request",
        )

    def test_variable_insights_imports_contracts_request_directly(self) -> None:
        self._assert_imports_owner_modules(
            variable_insights_mod,
            "scanner_data.contracts_request",
        )

    def test_variable_pipeline_imports_contract_owner_modules_directly(self) -> None:
        self._assert_imports_owner_modules(
            variable_pipeline_mod,
            "scanner_data.contracts_request",
            "scanner_data.contracts_variables",
        )

    def test_feature_detector_imports_contracts_request_directly(self) -> None:
        self._assert_imports_owner_modules(
            feature_detector_mod,
            "scanner_data.contracts_request",
        )

    def test_variable_discovery_imports_contracts_variables_directly(self) -> None:
        self._assert_imports_owner_modules(
            variable_discovery_mod,
            "scanner_data.contracts_variables",
        )

    def test_scanner_report_helpers_import_contracts_output_directly(self) -> None:
        self._assert_imports_owner_modules(
            scanner_report_mod,
            "scanner_data.contracts_output",
        )

    def test_readme_render_imports_contracts_request_directly(self) -> None:
        self._assert_imports_owner_modules(
            readme_render_mod,
            "scanner_data.contracts_request",
        )

    def test_render_compat_imports_contracts_request_directly(self) -> None:
        self._assert_imports_owner_modules(
            Path("src/prism/scanner_compat/render_compat.py"),
            "scanner_data.contracts_request",
        )

    def test_scan_facade_helpers_no_longer_imports_umbrella_contracts(self) -> None:
        self._assert_avoids_umbrella_contracts(scan_facade_helpers_mod)
