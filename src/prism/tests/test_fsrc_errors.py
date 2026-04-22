"""Parity tests for the fsrc centralized Prism errors contract."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "src"


@contextmanager
def _prefer_fsrc_prism_on_sys_path() -> object:
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


def test_fsrc_errors_to_failure_detail_shapes_optional_fields() -> None:
    cause = ValueError("bad payload")

    with _prefer_fsrc_prism_on_sys_path():
        errors = importlib.import_module("prism.errors")
        detail = errors.to_failure_detail(
            code=errors.REPO_CONTENT_INVALID,
            message="repo payload invalid",
            source="scan_repo",
            detail_code="repo_scan_payload_shape_invalid",
            cause=cause,
            traceback_text="traceback text",
        )

    assert detail == {
        "code": "repo_content_invalid",
        "category": "repo",
        "message": "repo payload invalid",
        "source": "scan_repo",
        "detail_code": "repo_scan_payload_shape_invalid",
        "cause_type": "ValueError",
        "traceback": "traceback text",
    }


def test_fsrc_errors_category_for_code_and_warning_normalization() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        errors = importlib.import_module("prism.errors")

        assert errors.category_for_code("unknown-code") == errors.ERROR_CATEGORY_RUNTIME
        assert (
            errors.category_for_code("ROLE_README_MARKER_CONFIG_YAML_INVALID")
            == errors.ERROR_CATEGORY_CONFIG
        )
        assert (
            errors.normalize_warning_code("  ROLE_SCAN_PHASE_FAILED ")
            == errors.ROLE_SCAN_PHASE_FAILED
        )
        assert errors.normalize_warning_code(None) == errors.ROLE_SCAN_DEGRADED


def test_fsrc_errors_normalize_metadata_warnings_stable_shape() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        errors = importlib.import_module("prism.errors")
        warnings = errors.normalize_metadata_warnings(
            {
                "scan_errors": [
                    {
                        "phase": "discovery",
                        "message": "failed to parse",
                        "error_type": "PrismRuntimeError",
                    }
                ],
                "yaml_parse_failures": [
                    {
                        "file": "defaults/main.yml",
                        "line": 3,
                        "column": 4,
                        "error": "expected <block end>",
                    }
                ],
                "meta_load_warnings": [
                    "ROLE_METADATA_LOAD_FAILED:meta/main.yml:metadata not loaded"
                ],
                "scan_degraded": True,
            }
        )

    assert warnings == [
        {
            "code": "role_scan_phase_failed",
            "category": "runtime",
            "message": "failed to parse",
            "detail_code": "discovery",
            "source": "scan_phase:discovery",
            "cause_type": "PrismRuntimeError",
        },
        {
            "code": "role_content_yaml_invalid",
            "category": "parser",
            "message": "YAML parse failure: expected <block end>",
            "detail_code": "yaml_parse_failure",
            "source": "defaults/main.yml:3:4",
        },
        {
            "code": "role_metadata_load_failed",
            "category": "config",
            "message": "metadata not loaded",
            "detail_code": "ROLE_METADATA_LOAD_FAILED",
            "source": "meta/main.yml",
        },
    ]


def test_fsrc_errors_prism_runtime_error_contract_compatibility() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        errors = importlib.import_module("prism.errors")
        exc = errors.PrismRuntimeError(
            code="role_scan_runtime_error",
            category="runtime",
            message="boom",
            detail={"phase": "discovery"},
        )

    assert isinstance(exc, RuntimeError)
    assert exc.code == "role_scan_runtime_error"
    assert exc.category == "runtime"
    assert exc.message == "boom"
    assert exc.detail == {"phase": "discovery"}
    assert str(exc) == "role_scan_runtime_error: boom"
