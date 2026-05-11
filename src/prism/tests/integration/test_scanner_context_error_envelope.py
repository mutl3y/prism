"""Integration tests for error envelope in ScannerContext orchestration.

Tests cover:
- Error recording with new optional fields
- Multiple platform errors in single scan
- Error assembly during scan phases
- Error normalization with new fields
- Integration with Ansible adapter
"""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


from prism.scanner_core.scanner_context import ScannerContext
from prism.scanner_plugins.ansible.error_adapter import build_ansible_error_detail

PROJECT_ROOT = Path(__file__).resolve().parents[4]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "src"


@contextmanager
def _prefer_fsrc_prism_on_sys_path() -> Iterator[None]:
    original_path = list(sys.path)
    original_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == "prism" or key.startswith("prism.")
    }
    try:
        sys.path.insert(0, str(FSRC_SOURCE_ROOT))
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        yield
    finally:
        sys.path[:] = original_path
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        sys.modules.update(original_modules)


def _create_test_scanner_context() -> ScannerContext:
    """Create a ScannerContext for testing error envelope recording.

    Returns a minimal ScannerContext that can record errors without
    going through full orchestration.
    """
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        core_module = importlib.import_module("prism.scanner_core.scanner_context")

        # Minimal scan options
        options = {
            "role_path": "/tmp/test_role",
            "role_name_override": None,
            "readme_config_path": None,
            "include_vars_main": True,
            "exclude_path_patterns": None,
            "detailed_catalog": False,
            "include_task_parameters": True,
            "include_task_runbooks": True,
            "inline_task_runbooks": True,
            "include_collection_checks": True,
            "keep_unknown_style_sections": True,
            "adopt_heading_mode": None,
            "vars_seed_paths": None,
            "style_readme_path": None,
            "style_source_path": None,
            "style_guide_skeleton": False,
            "compare_role_path": None,
            "fail_on_unconstrained_dynamic_includes": None,
            "fail_on_yaml_like_task_annotations": None,
            "ignore_unresolved_internal_underscore_references": False,
        }

        # Create a minimal DIContainer
        container = di_module.DIContainer(
            role_path=options["role_path"], scan_options=options
        )

        # Create ScannerContext - we won't call orchestrate_scan,
        # just use it for error recording
        context = core_module.ScannerContext(
            di=container,
            role_path=options["role_path"],
            scan_options=options,
        )

        return context


class TestErrorRecordingWithNewFields:
    """Test error recording in ScannerContext with new optional fields."""

    def test_record_phase_error_with_error_code(self) -> None:
        """Test _record_phase_error() with error_code parameter."""
        context = _create_test_scanner_context()
        exc = RuntimeError("Extraction failed")
        context._record_phase_error(
            phase="extraction",
            error=exc,
            error_code="ANSIBLE_TASK_FAILED",
        )
        assert len(context._scan_errors) == 1
        entry = context._scan_errors[0]
        assert entry["error_code"] == "ANSIBLE_TASK_FAILED"

    def test_record_phase_error_with_category(self) -> None:
        """Test _record_phase_error() accepts category parameter."""
        context = _create_test_scanner_context()
        exc = RuntimeError("Extraction failed")
        context._record_phase_error(
            phase="extraction",
            error=exc,
            category="runtime",
        )
        assert len(context._scan_errors) == 1
        entry = context._scan_errors[0]
        assert entry.get("category") == "runtime"

    def test_record_phase_error_with_recoverable_flag(self) -> None:
        """Test _record_phase_error() accepts recoverable parameter."""
        context = _create_test_scanner_context()
        exc = TimeoutError("Request timed out")
        context._record_phase_error(
            phase="extraction",
            error=exc,
            recoverable=True,
        )
        assert len(context._scan_errors) == 1
        entry = context._scan_errors[0]
        assert entry.get("recoverable") is True

    def test_record_phase_error_with_resource_id(self) -> None:
        """Test _record_phase_error() accepts resource_id parameter."""
        context = _create_test_scanner_context()
        exc = RuntimeError("Resource processing failed")
        context._record_phase_error(
            phase="extraction",
            error=exc,
            resource_id="my_role/tasks/main.yml",
        )
        assert len(context._scan_errors) == 1
        entry = context._scan_errors[0]
        assert entry.get("resource_id") == "my_role/tasks/main.yml"

    def test_record_phase_error_with_detail_dict(self) -> None:
        """Test _record_phase_error() accepts detail dict parameter."""
        context = _create_test_scanner_context()
        detail = {
            "task_file": "tasks/main.yml",
            "line_number": 42,
            "module_name": "copy",
        }
        exc = RuntimeError("Task execution failed")
        context._record_phase_error(
            phase="extraction",
            error=exc,
            detail=detail,
        )
        assert len(context._scan_errors) == 1
        entry = context._scan_errors[0]
        # Detail might be sanitized, so check keys exist
        assert "detail" in entry

    def test_record_phase_error_with_cause_type(self) -> None:
        """Test _record_phase_error() accepts cause_type parameter."""
        context = _create_test_scanner_context()
        exc = RuntimeError("Exception occurred")
        context._record_phase_error(
            phase="extraction",
            error=exc,
            cause_type="ModuleNotFoundError",
        )
        assert len(context._scan_errors) == 1
        entry = context._scan_errors[0]
        assert entry.get("cause_type") == "ModuleNotFoundError"

    def test_record_phase_error_with_all_optional_fields(self) -> None:
        """Test _record_phase_error() with all optional fields."""
        context = _create_test_scanner_context()
        detail = {"line_number": 42, "task_file": "main.yml"}
        exc = RuntimeError("Complete error")
        context._record_phase_error(
            phase="extraction",
            error=exc,
            error_code="ANSIBLE_TASK_FAILED",
            category="runtime",
            recoverable=False,
            resource_id="task_id",
            detail=detail,
            cause_type="TaskFailure",
        )
        assert len(context._scan_errors) == 1
        entry = context._scan_errors[0]
        assert entry["phase"] == "extraction"
        assert entry["error_code"] == "ANSIBLE_TASK_FAILED"
        assert entry["category"] == "runtime"
        assert entry["recoverable"] is False
        assert entry["resource_id"] == "task_id"
        assert entry.get("cause_type") == "TaskFailure"


class TestMultiplePlatformErrors:
    """Test recording errors from multiple platforms in single scan."""

    def test_record_ansible_error_with_detail(self) -> None:
        """Test recording Ansible error with detail."""
        context = _create_test_scanner_context()
        task_context = {
            "task_file": "tasks/main.yml",
            "line_number": 10,
            "task_index": 2,
            "module_name": "copy",
            "task_name": "Copy file",
        }
        detail = build_ansible_error_detail(task_context, Exception("test"))
        exc = RuntimeError("Ansible task failed")
        context._record_phase_error(
            phase="extraction",
            error=exc,
            error_code="ANSIBLE_TASK_FAILED",
            detail=detail,
        )
        assert len(context._scan_errors) == 1
        entry = context._scan_errors[0]
        assert "detail" in entry

    def test_record_kubernetes_stub_error(self) -> None:
        """Test recording K8s stub error (not implemented yet)."""
        context = _create_test_scanner_context()
        k8s_detail = {
            "cluster": "prod-us-west",
            "namespace": "default",
            "kind": "Pod",
            "name": "nginx",
        }
        exc = RuntimeError("K8s API error")
        context._record_phase_error(
            phase="extraction",
            error=exc,
            error_code="K8S_API_ERROR",
            detail=k8s_detail,
        )
        assert len(context._scan_errors) == 1
        entry = context._scan_errors[0]
        assert entry["error_code"] == "K8S_API_ERROR"

    def test_record_terraform_stub_error(self) -> None:
        """Test recording Terraform stub error (not implemented yet)."""
        context = _create_test_scanner_context()
        tf_detail = {
            "provider": "aws",
            "region": "us-west-2",
            "resource_type": "aws_instance",
        }
        exc = RuntimeError("Terraform plan failed")
        context._record_phase_error(
            phase="extraction",
            error=exc,
            error_code="TF_PLAN_PARSE_ERROR",
            detail=tf_detail,
        )
        assert len(context._scan_errors) == 1
        entry = context._scan_errors[0]
        assert entry["error_code"] == "TF_PLAN_PARSE_ERROR"

    def test_multiple_errors_in_single_scan(self) -> None:
        """Test recording multiple different platform errors in single scan."""
        context = _create_test_scanner_context()

        exc1 = RuntimeError("Ansible failed")
        context._record_phase_error(
            phase="extraction",
            error=exc1,
            error_code="ANSIBLE_TASK_FAILED",
        )

        exc2 = RuntimeError("K8s failed")
        context._record_phase_error(
            phase="extraction",
            error=exc2,
            error_code="K8S_API_ERROR",
        )

        exc3 = RuntimeError("Terraform failed")
        context._record_phase_error(
            phase="extraction",
            error=exc3,
            error_code="TF_EXECUTION_ERROR",
        )

        assert len(context._scan_errors) == 3
        codes = [e.get("error_code") for e in context._scan_errors]
        assert "ANSIBLE_TASK_FAILED" in codes
        assert "K8S_API_ERROR" in codes
        assert "TF_EXECUTION_ERROR" in codes


class TestErrorAssemblyDuringScan:
    """Test error assembly during different scan phases."""

    def test_errors_recorded_during_ingress_phase(self) -> None:
        """Test errors recorded during ingress phase are stored."""
        context = _create_test_scanner_context()
        exc = ValueError("Invalid configuration")
        context._record_phase_error(
            phase="ingress",
            error=exc,
        )
        assert len(context._scan_errors) == 1
        assert context._scan_errors[0]["phase"] == "ingress"

    def test_errors_recorded_during_extraction_phase(self) -> None:
        """Test errors recorded during extraction phase are stored."""
        context = _create_test_scanner_context()
        exc = RuntimeError("Extraction failed")
        context._record_phase_error(
            phase="extraction",
            error=exc,
        )
        assert len(context._scan_errors) == 1
        assert context._scan_errors[0]["phase"] == "extraction"

    def test_errors_recorded_during_rendering_phase(self) -> None:
        """Test errors recorded during rendering phase are stored."""
        context = _create_test_scanner_context()
        exc = IOError("Rendering failed")
        context._record_phase_error(
            phase="rendering",
            error=exc,
        )
        assert len(context._scan_errors) == 1
        assert context._scan_errors[0]["phase"] == "rendering"

    def test_scan_errors_list_maintains_insertion_order(self) -> None:
        """Test that scan_errors list maintains insertion order."""
        context = _create_test_scanner_context()

        exc1 = RuntimeError("First error")
        context._record_phase_error(
            phase="ingress",
            error=exc1,
        )

        exc2 = RuntimeError("Second error")
        context._record_phase_error(
            phase="extraction",
            error=exc2,
        )

        exc3 = RuntimeError("Third error")
        context._record_phase_error(
            phase="rendering",
            error=exc3,
        )

        assert len(context._scan_errors) == 3
        assert "First error" in context._scan_errors[0]["message"]
        assert "Second error" in context._scan_errors[1]["message"]
        assert "Third error" in context._scan_errors[2]["message"]

    def test_errors_across_multiple_phases(self) -> None:
        """Test errors recorded across multiple phases."""
        context = _create_test_scanner_context()

        exc1 = ValueError("Ingress error")
        context._record_phase_error(
            phase="ingress",
            error=exc1,
        )

        exc2 = RuntimeError("Extraction error 1")
        context._record_phase_error(
            phase="extraction",
            error=exc2,
        )

        exc3 = RuntimeError("Extraction error 2")
        context._record_phase_error(
            phase="extraction",
            error=exc3,
        )

        exc4 = IOError("Rendering error")
        context._record_phase_error(
            phase="rendering",
            error=exc4,
        )

        assert len(context._scan_errors) == 4
        phases = [e["phase"] for e in context._scan_errors]
        assert phases == ["ingress", "extraction", "extraction", "rendering"]


class TestErrorNormalization:
    """Test error normalization with new fields."""

    def test_error_entry_with_new_fields_normalized(self) -> None:
        """Test error entries with new fields are normalized correctly."""
        context = _create_test_scanner_context()
        detail = {
            "task_file": "main.yml",
            "line_number": 42,
        }
        exc = RuntimeError("Test error")
        context._record_phase_error(
            phase="extraction",
            error=exc,
            error_code="ANSIBLE_TASK_FAILED",
            category="runtime",
            detail=detail,
        )

        entry = context._scan_errors[0]
        assert entry["error_code"] == "ANSIBLE_TASK_FAILED"
        assert entry["category"] == "runtime"

    def test_optional_fields_included_when_present(self) -> None:
        """Test optional fields are included in normalized output when present."""
        context = _create_test_scanner_context()
        exc = RuntimeError("Test")
        context._record_phase_error(
            phase="extraction",
            error=exc,
            error_code="ANSIBLE_TASK_FAILED",
            category="runtime",
            recoverable=False,
            resource_id="task1",
        )

        entry = context._scan_errors[0]
        assert "error_code" in entry
        assert "category" in entry
        assert "recoverable" in entry
        assert "resource_id" in entry

    def test_optional_fields_omitted_when_not_set(self) -> None:
        """Test optional fields are omitted when not set (backward compat)."""
        context = _create_test_scanner_context()
        exc = RuntimeError("Test")
        context._record_phase_error(
            phase="extraction",
            error=exc,
        )

        entry = context._scan_errors[0]
        assert "error_code" not in entry
        assert "category" not in entry
        assert "recoverable" not in entry


class TestIntegrationWithAnsibleAdapter:
    """Test integration with Ansible error adapter."""

    def test_record_error_with_ansible_adapter_output(self) -> None:
        """Test scanner_context._record_phase_error() with Ansible adapter output."""
        context = _create_test_scanner_context()
        task_context = {
            "task_file": "roles/myapp/tasks/main.yml",
            "line_number": 25,
            "task_index": 5,
            "module_name": "template",
            "task_name": "Deploy configuration",
            "role_path": "/path/to/roles/myapp",
            "collection": "ansible.builtin",
        }
        detail = build_ansible_error_detail(task_context, Exception("test"))

        exc = RuntimeError("Ansible template failed")
        context._record_phase_error(
            phase="extraction",
            error=exc,
            error_code="ANSIBLE_TASK_FAILED",
            detail=detail,
        )

        entry = context._scan_errors[0]
        assert "detail" in entry

    def test_task_context_flows_through_scanner_context(self) -> None:
        """Test task context flows through scanner_context correctly."""
        context = _create_test_scanner_context()
        task_context = {
            "task_file": "handlers/main.yml",
            "line_number": 10,
            "module_name": "service",
        }
        detail = build_ansible_error_detail(
            task_context, RuntimeError("service failed")
        )

        exc = RuntimeError("Service handler failed")
        context._record_phase_error(
            phase="extraction",
            error=exc,
            detail=detail,
        )

        entry = context._scan_errors[0]
        assert "detail" in entry

    def test_partial_task_context_handled_gracefully(self) -> None:
        """Test partial task context is handled gracefully."""
        context = _create_test_scanner_context()
        task_context = {"module_name": "shell"}
        detail = build_ansible_error_detail(task_context, Exception("test"))

        exc = RuntimeError("Shell command failed")
        context._record_phase_error(
            phase="extraction",
            error=exc,
            detail=detail,
        )

        entry = context._scan_errors[0]
        assert "detail" in entry


class TestErrorEnvelopeBackwardCompatibility:
    """Test backward compatibility of error envelope in ScannerContext."""

    def test_existing_error_recording_without_new_fields(self) -> None:
        """Test existing error recording code works without new fields."""
        context = _create_test_scanner_context()
        exc = ValueError("Invalid configuration")
        context._record_phase_error(
            phase="extraction",
            error=exc,
        )
        entry = context._scan_errors[0]
        assert entry["phase"] == "extraction"
        assert entry["error_type"] == "ValueError"
        assert "Invalid configuration" in entry["message"]

    def test_multiple_errors_with_and_without_new_fields_mixed(self) -> None:
        """Test mixing errors with and without new fields."""
        context = _create_test_scanner_context()

        exc1 = ValueError("Old style error")
        context._record_phase_error(
            phase="ingress",
            error=exc1,
        )

        exc2 = RuntimeError("New style error")
        context._record_phase_error(
            phase="extraction",
            error=exc2,
            error_code="ANSIBLE_TASK_FAILED",
            category="runtime",
        )

        exc3 = IOError("Another old style error")
        context._record_phase_error(
            phase="rendering",
            error=exc3,
        )

        assert len(context._scan_errors) == 3
        assert "error_code" not in context._scan_errors[0]
        assert context._scan_errors[1]["error_code"] == "ANSIBLE_TASK_FAILED"
        assert "error_code" not in context._scan_errors[2]
