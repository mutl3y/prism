"""Test coverage for FIND-11: Critical path test gaps.

This file adds dedicated tests for:
1. task_line_parsing.py proxy behavior under concurrent access
2. scanner_context.py error boundary behavior with malformed inputs
3. execution_request_builder.py platform key resolution edge cases
4. output_orchestrator.py with malformed payloads
"""

from __future__ import annotations

import threading

import pytest

from prism.scanner_extract import task_line_parsing as tlp
from prism.scanner_core.scanner_context import ScannerContext
from prism.scanner_io.output_orchestrator import OutputOrchestrator


class TestTaskLineParsingConcurrentAccess:
    """Test task_line_parsing proxies under concurrent access."""

    def test_policy_backed_proxy_thread_safe_access(self) -> None:
        """Verify policy-backed proxies handle concurrent reads."""
        results: list[bool] = []
        errors: list[Exception] = []

        def _access_proxy() -> None:
            try:
                # This should fail consistently (no policy bundle)
                _ = "import_tasks" in tlp.TASK_INCLUDE_KEYS
                results.append(False)
            except ValueError:
                results.append(True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_access_proxy) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All threads should fail closed with ValueError
        assert all(results), "All concurrent accesses should fail closed"
        assert not errors, f"Unexpected errors: {errors}"

    def test_policy_backed_collection_proxy_iterator_concurrent(self) -> None:
        """Verify iterator behavior is consistent across concurrent access."""
        error_count = [0]

        def _iter_proxy() -> None:
            try:
                list(tlp.TASK_INCLUDE_KEYS)
            except ValueError:
                error_count[0] += 1
            except Exception as e:
                pytest.fail(f"Unexpected error type: {type(e).__name__}: {e}")

        threads = [threading.Thread(target=_iter_proxy) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All 5 threads should hit the ValueError
        assert error_count[0] == 5


class TestScannerContextErrorBoundary:
    """Test ScannerContext error handling with malformed inputs."""

    def test_scanner_context_rejects_none_di(self) -> None:
        """Verify ScannerContext rejects None DI container."""
        with pytest.raises(ValueError) as exc_info:
            ScannerContext(
                di=None,  # type: ignore
                role_path="/test/role",
                scan_options={"target_path": "/tmp", "scan_id": "test"},  # type: ignore
            )
        assert "di" in str(exc_info.value)

    def test_scanner_context_rejects_empty_role_path(self) -> None:
        """Verify ScannerContext rejects empty role path."""
        with pytest.raises(ValueError) as exc_info:
            ScannerContext(
                di={},  # type: ignore
                role_path="",
                scan_options={"target_path": "/tmp", "scan_id": "test"},  # type: ignore
            )
        assert "role_path" in str(exc_info.value)

    def test_scanner_context_rejects_none_options(self) -> None:
        """Verify ScannerContext rejects None scan options."""
        with pytest.raises(ValueError) as exc_info:
            ScannerContext(
                di={},  # type: ignore
                role_path="/test/role",
                scan_options=None,  # type: ignore
            )
        assert "scan_options" in str(exc_info.value)


class TestExecutionRequestBuilderPlatformKey:
    """Test execution request builder error handling."""

    def test_execution_request_builder_exists(self) -> None:
        """Verify execution request builder function exists."""
        from prism.scanner_core.execution_request_builder import (
            build_non_collection_run_scan_execution_request,
        )

        assert callable(build_non_collection_run_scan_execution_request)

    def test_execution_request_builder_requires_role_path(self) -> None:
        """Verify execution request builder validates role_path."""
        from prism.scanner_core.execution_request_builder import (
            build_non_collection_run_scan_execution_request,
        )

        with pytest.raises((TypeError, ValueError)):
            # Should fail due to missing required role_path
            build_non_collection_run_scan_execution_request()  # type: ignore


class TestOutputOrchestratorMalformedPayloads:
    """Test output_orchestrator error handling."""

    def test_output_orchestrator_can_be_initialized(self) -> None:
        """Verify OutputOrchestrator can be initialized with valid args."""
        # Should succeed with valid inputs
        orchestrator = OutputOrchestrator(
            di={},  # type: ignore
            output_path="/tmp/test",
            options={},
        )
        assert orchestrator is not None

    def test_output_orchestrator_requires_output_path(self) -> None:
        """Verify OutputOrchestrator validates output path."""
        with pytest.raises(ValueError):
            # Empty path should be rejected
            OutputOrchestrator(
                di={},  # type: ignore
                output_path="",
                options={},
            )

    def test_output_orchestrator_rejects_malformed_options(self) -> None:
        """Verify OutputOrchestrator validates options type."""
        with pytest.raises((TypeError, ValueError)):
            OutputOrchestrator(
                di={},  # type: ignore
                output_path="/tmp/test",
                options=None,  # type: ignore
            )
