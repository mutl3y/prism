"""Governance tests for runtime module public API guardrails (A36).

These tests verify that module boundaries are enforced at runtime via
__getattr__ hooks, not just through test-only architecture assertions.

This reduces reliance on fragile test-only enforcement by making boundary
violations raise AttributeError immediately at import/access time.
"""

from __future__ import annotations

import pytest

import prism.scanner_core
import prism.scanner_data
import prism.scanner_extract
import prism.scanner_readme


class TestScannerDataPublicApiGuardrails:
    """Verify scanner_data module enforces public API at runtime."""

    def test_public_symbol_accessible(self) -> None:
        """Public symbols from __all__ are accessible."""
        # All of these are in __all__
        assert hasattr(prism.scanner_data, "Variable")
        assert hasattr(prism.scanner_data, "VariableRow")
        assert hasattr(prism.scanner_data, "ScanContext")
        assert hasattr(prism.scanner_data, "ScanPayloadBuilder")

    def test_private_symbol_raises_attribute_error(self) -> None:
        """Accessing private symbols (prefixed with _) raises AttributeError."""
        with pytest.raises(
            AttributeError,
            match="private member; only __all__ symbols are public",
        ):
            _ = prism.scanner_data._StyleSection

    def test_private_contract_type_raises_attribute_error(self) -> None:
        """Private contract types are not accessible even if they existed before."""
        with pytest.raises(
            AttributeError,
            match="private member; only __all__ symbols are public",
        ):
            _ = prism.scanner_data._SectionTitleBucket

    def test_nonexistent_symbol_raises_attribute_error(self) -> None:
        """Accessing non-existent symbols still raises AttributeError."""
        with pytest.raises(AttributeError, match="has no attribute 'FakeSymbol'"):
            _ = prism.scanner_data.FakeSymbol  # type: ignore

    def test_dir_shows_only_public_symbols(self) -> None:
        """dir() on the module shows only public symbols from __all__."""
        public_symbols = dir(prism.scanner_data)
        # Verify it excludes private symbols
        assert "_StyleSection" not in public_symbols
        assert "_SectionTitleBucket" not in public_symbols
        # Verify it includes public symbols
        assert "Variable" in public_symbols
        assert "ScanContext" in public_symbols


class TestScannerCorePublicApiGuardrails:
    """Verify scanner_core module enforces public API at runtime."""

    def test_public_symbol_accessible(self) -> None:
        """Public symbols from __all__ are accessible."""
        # All of these are in __all__
        assert hasattr(prism.scanner_core, "DIContainer")
        assert hasattr(prism.scanner_core, "ScannerContext")
        assert hasattr(prism.scanner_core, "VariableDiscovery")

    def test_private_symbol_raises_attribute_error(self) -> None:
        """Accessing private symbols (prefixed with _) raises AttributeError."""
        with pytest.raises(
            AttributeError,
            match="private member; only __all__ symbols are public",
        ):
            _ = prism.scanner_core._some_private_function  # type: ignore

    def test_nonexistent_symbol_raises_attribute_error(self) -> None:
        """Accessing non-existent symbols raises AttributeError."""
        with pytest.raises(AttributeError, match="has no attribute 'FakeClass'"):
            _ = prism.scanner_core.FakeClass  # type: ignore

    def test_dir_shows_only_public_symbols(self) -> None:
        """dir() on the module shows only public symbols from __all__."""
        public_symbols = dir(prism.scanner_core)
        # Verify it includes public symbols from __all__
        assert "DIContainer" in public_symbols
        assert "ScannerContext" in public_symbols
        assert "VariableDiscovery" in public_symbols


class TestScannerExtractPublicApiGuardrails:
    """Verify scanner_extract module enforces public API at runtime."""

    def test_public_symbol_accessible(self) -> None:
        """Public symbols from __all__ are accessible."""
        assert hasattr(prism.scanner_extract, "load_yaml_file")
        assert hasattr(prism.scanner_extract, "collect_task_files")
        assert hasattr(prism.scanner_extract, "TASK_INCLUDE_KEYS")

    def test_private_symbol_raises_attribute_error(self) -> None:
        """Accessing private symbols (prefixed with _) raises AttributeError."""
        with pytest.raises(
            AttributeError,
            match="private member; only __all__ symbols are public",
        ):
            _ = prism.scanner_extract._some_helper  # type: ignore

    def test_dir_shows_only_public_symbols(self) -> None:
        """dir() on the module shows only public symbols from __all__."""
        public_symbols = dir(prism.scanner_extract)
        # Verify it includes public symbols from __all__
        assert "load_yaml_file" in public_symbols
        assert "TASK_INCLUDE_KEYS" in public_symbols


class TestScannerReadmePublicApiGuardrails:
    """Verify scanner_readme module enforces public API at runtime."""

    def test_public_symbol_accessible(self) -> None:
        """Public symbols from __all__ are accessible."""
        assert hasattr(prism.scanner_readme, "render_readme")
        assert hasattr(prism.scanner_readme, "parse_style_readme")
        assert hasattr(prism.scanner_readme, "DEFAULT_SECTION_SPECS")

    def test_private_symbol_raises_attribute_error(self) -> None:
        """Accessing private symbols (prefixed with _) raises AttributeError."""
        with pytest.raises(
            AttributeError,
            match="private member; only __all__ symbols are public",
        ):
            _ = prism.scanner_readme._private_helper  # type: ignore

    def test_dir_shows_only_public_symbols(self) -> None:
        """dir() on the module shows only public symbols from __all__."""
        public_symbols = dir(prism.scanner_readme)
        # Verify it includes public symbols from __all__
        assert "render_readme" in public_symbols
        assert "parse_style_readme" in public_symbols


class TestGuardrailsComplimentTestArchitecture:
    """Verify runtime guardrails work alongside architectural test suite.

    The goal is to reduce reliance on test-only enforcement. These tests
    verify both work together:
    - Runtime __getattr__ catches violations immediately
    - Architecture tests verify the pattern across the codebase
    """

    def test_getattr_blocks_immediate_access(self) -> None:
        """__getattr__ raises AttributeError before any other code runs."""
        # This is the runtime guardrail that complements tests
        with pytest.raises(AttributeError):
            getattr(prism.scanner_data, "_PrivateSymbol")

    def test_public_api_remains_accessible(self) -> None:
        """Public API remains fully accessible despite guardrails."""
        # Verify common usage patterns still work
        from prism.scanner_data import Variable
        from prism.scanner_core import DIContainer
        from prism.scanner_extract import load_yaml_file

        assert Variable is not None
        assert DIContainer is not None
        assert load_yaml_file is not None

    def test_guardrail_message_provides_guidance(self) -> None:
        """Error messages guide users toward the public API."""
        with pytest.raises(AttributeError) as exc_info:
            _ = prism.scanner_data._UndocumentedPrivate  # type: ignore

        error_msg = str(exc_info.value)
        assert "private member" in error_msg
        assert "__all__" in error_msg
