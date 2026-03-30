"""Ownership and compatibility tests for requirements/readme touchpoints."""

import inspect
import re
from pathlib import Path

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


def test_scanner_output_glue_remains_flattened_without_local_wrapper_defs():
    scanner_source = inspect.getsource(scanner)

    assert "scanner_submodules.scan_output" not in scanner_source
    assert "def _render_and_write_scan_output(" not in scanner_source
    assert "def _emit_scan_outputs(" not in scanner_source


def test_canonical_scanner_packages_do_not_reverse_import_scanner_facade():
    package_root = Path(__file__).resolve().parents[1]
    canonical_packages = (
        "scanner_core",
        "scanner_extract",
        "scanner_io",
        "scanner_analysis",
        "scanner_readme",
        "scanner_config",
    )
    forbidden_import_pattern = re.compile(
        r"^\s*(from\s+prism\s+import\s+scanner|import\s+prism\.scanner|from\s+\.\.\s+import\s+scanner|from\s+\.\.scanner\s+import\s+)",
        re.MULTILINE,
    )

    offenders: list[str] = []
    for package_name in canonical_packages:
        for py_file in (package_root / package_name).rglob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            if forbidden_import_pattern.search(source):
                offenders.append(str(py_file.relative_to(package_root)))

    assert not offenders, (
        "Canonical scanner packages must not reverse-import prism.scanner facade: "
        + ", ".join(sorted(offenders))
    )
