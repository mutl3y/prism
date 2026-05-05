"""Unit tests for prism.scanner_readme public API guard (FIND-13 closure)."""

from __future__ import annotations

import pytest

import prism.scanner_readme as scanner_readme


_EXPECTED_ALL = {
    "render_readme",
    "append_scanner_report_section_if_enabled",
    "render_guide_section_body",
    "STYLE_SECTION_ALIASES",
    "get_style_section_aliases_snapshot",
    "detect_style_section_level",
    "format_heading",
    "normalize_style_heading",
    "parse_style_readme",
    "refresh_policy_derived_state",
    "build_doc_insights",
    "parse_comma_values",
}


def test_all_contains_expected_public_symbols() -> None:
    assert set(scanner_readme.__all__) == _EXPECTED_ALL


def test_dir_returns_sorted_all() -> None:
    assert scanner_readme.__dir__() == sorted(_EXPECTED_ALL)


def test_private_attribute_raises_attribute_error() -> None:
    with pytest.raises(AttributeError, match="private member"):
        scanner_readme.__getattr__("_hidden")


def test_underscore_name_raises_for_any_private_name() -> None:
    with pytest.raises(AttributeError):
        scanner_readme.__getattr__("_some_internal")


def test_nonexistent_public_name_raises_without_private_message() -> None:
    with pytest.raises(AttributeError) as exc_info:
        scanner_readme.__getattr__("totally_missing")
    assert "private member" not in str(exc_info.value)


def test_public_symbols_are_importable() -> None:
    for name in _EXPECTED_ALL:
        obj = getattr(scanner_readme, name)
        assert obj is not None


def test_refresh_policy_derived_state_callable() -> None:
    assert callable(scanner_readme.refresh_policy_derived_state)
    scanner_readme.refresh_policy_derived_state({})
