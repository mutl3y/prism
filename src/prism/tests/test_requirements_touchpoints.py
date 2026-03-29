"""Ownership and compatibility tests for requirements/readme touchpoints."""

import inspect

from prism import scanner
from prism.scanner_extract import requirements as canonical_requirements
from prism.scanner_readme import doc_insights as canonical_doc_insights
from prism.scanner_readme import guide as readme_guide
from prism.scanner_readme import doc_insights as compat_doc_insights
from prism.scanner_extract import requirements as compat_requirements


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


def test_canonical_readme_modules_have_no_scanner_submodules_runtime_imports():
    doc_insights_source = inspect.getsource(canonical_doc_insights)
    guide_source = inspect.getsource(readme_guide)

    assert "scanner_submodules" not in doc_insights_source
    assert "scanner_submodules" not in guide_source
