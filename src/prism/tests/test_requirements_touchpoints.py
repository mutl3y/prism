"""Ownership and compatibility tests for requirements/readme touchpoints."""

from prism import scanner
from prism.scanner_extract import requirements as canonical_requirements
from prism.scanner_readme import doc_insights as canonical_doc_insights
from prism.scanner_readme import guide as readme_guide
from prism.scanner_readme import doc_insights as compat_doc_insights
from prism.scanner_extract import requirements as compat_requirements
from prism.tests._boundary_acceptance import (
    assert_packages_do_not_reference_scanner_facade,
    assert_scanner_output_wiring_is_canonical,
)


def test_scanner_requirements_shim_exports_canonical_functions():
    assert (
        compat_requirements.normalize_requirements
        is canonical_requirements.normalize_requirements
    )
    assert (
        compat_requirements.build_requirements_display
        is canonical_requirements.build_requirements_display
    )


def test_readme_guide_uses_canonical_requirements_normalization():
    assert (
        readme_guide.normalize_requirements
        is canonical_requirements.normalize_requirements
    )


def test_scanner_doc_insights_uses_canonical_readme_touchpoint():
    assert scanner.build_doc_insights is canonical_doc_insights.build_doc_insights
    assert (
        canonical_doc_insights.build_doc_insights
        is compat_doc_insights.build_doc_insights
    )


def test_scanner_output_glue_remains_canonically_wired():
    assert_scanner_output_wiring_is_canonical(scanner)


def test_canonical_scanner_packages_do_not_reverse_import_scanner_facade():
    assert_packages_do_not_reference_scanner_facade(
        (
            "scanner_core",
            "scanner_extract",
            "scanner_io",
            "scanner_analysis",
            "scanner_readme",
            "scanner_config",
        )
    )
