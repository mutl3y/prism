"""Unit tests for prism.scanner_config.section constants (FIND-13 closure)."""

from __future__ import annotations

from prism.scanner_config import section


def test_default_doc_marker_prefix_is_prism() -> None:
    assert section.DEFAULT_DOC_MARKER_PREFIX == "prism"


def test_section_config_filename_is_prism_yml() -> None:
    assert section.SECTION_CONFIG_FILENAME == ".prism.yml"


def test_section_config_filenames_tuple_contains_canonical_filename() -> None:
    assert isinstance(section.SECTION_CONFIG_FILENAMES, tuple)
    assert section.SECTION_CONFIG_FILENAME in section.SECTION_CONFIG_FILENAMES


def test_public_api_matches_all() -> None:
    assert set(section.__all__) == {
        "DEFAULT_DOC_MARKER_PREFIX",
        "SECTION_CONFIG_FILENAME",
        "SECTION_CONFIG_FILENAMES",
    }
