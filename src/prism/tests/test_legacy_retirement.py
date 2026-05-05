"""Tests for the public legacy-retirement error contract."""

from __future__ import annotations

import pytest

from prism.scanner_config import legacy_retirement


def test_legacy_section_config_filename_is_dot_ansible_role_doc_yml() -> None:
    assert legacy_retirement.LEGACY_SECTION_CONFIG_FILENAME == ".ansible_role_doc.yml"


def test_legacy_runtime_style_source_env_is_ansible_role_doc_style_source() -> None:
    assert (
        legacy_retirement.LEGACY_RUNTIME_STYLE_SOURCE_ENV
        == "ANSIBLE_ROLE_DOC_STYLE_SOURCE"
    )


def test_legacy_section_config_unsupported_code_and_message_are_stable() -> None:
    assert (
        legacy_retirement.LEGACY_SECTION_CONFIG_UNSUPPORTED
        == "LEGACY_SECTION_CONFIG_UNSUPPORTED"
    )
    assert (
        ".ansible_role_doc.yml"
        in legacy_retirement.LEGACY_SECTION_CONFIG_UNSUPPORTED_MESSAGE
    )
    assert ".prism.yml" in legacy_retirement.LEGACY_SECTION_CONFIG_UNSUPPORTED_MESSAGE


def test_legacy_runtime_path_unavailable_code_and_message_are_stable() -> None:
    assert (
        legacy_retirement.LEGACY_RUNTIME_PATH_UNAVAILABLE
        == "LEGACY_RUNTIME_PATH_UNAVAILABLE"
    )
    assert "retired" in legacy_retirement.LEGACY_RUNTIME_PATH_UNAVAILABLE_MESSAGE


def test_format_legacy_retirement_error_combines_code_and_message() -> None:
    formatted = legacy_retirement.format_legacy_retirement_error(
        legacy_retirement.LEGACY_SECTION_CONFIG_UNSUPPORTED,
        legacy_retirement.LEGACY_SECTION_CONFIG_UNSUPPORTED_MESSAGE,
    )
    assert formatted.startswith("LEGACY_SECTION_CONFIG_UNSUPPORTED: ")
    assert legacy_retirement.LEGACY_SECTION_CONFIG_UNSUPPORTED_MESSAGE in formatted


@pytest.mark.parametrize(
    "name",
    [
        "LEGACY_SECTION_CONFIG_FILENAME",
        "LEGACY_RUNTIME_STYLE_SOURCE_ENV",
        "LEGACY_SECTION_CONFIG_UNSUPPORTED",
        "LEGACY_SECTION_CONFIG_UNSUPPORTED_MESSAGE",
        "LEGACY_RUNTIME_PATH_UNAVAILABLE",
        "LEGACY_RUNTIME_PATH_UNAVAILABLE_MESSAGE",
        "format_legacy_retirement_error",
    ],
)
def test_public_symbol_is_exported(name: str) -> None:
    assert name in legacy_retirement.__all__
    assert hasattr(legacy_retirement, name)
