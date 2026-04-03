"""Tests asserting that builders are co-located with the contracts they produce.

A33 requirement: each builder must be defined in the same domain module as the
contract TypedDict it constructs, not in a separate builders.py god-file.
"""

from __future__ import annotations

import inspect

import prism.scanner_data.contracts_output as contracts_output_mod
import prism.scanner_data.contracts_variables as contracts_variables_mod
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
