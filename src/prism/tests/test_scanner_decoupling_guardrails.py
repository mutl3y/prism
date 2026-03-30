"""Guardrails that prevent migrated tests from re-coupling to scanner private helpers."""

from pathlib import Path


def test_migrated_test_modules_do_not_use_targeted_scanner_private_helpers():
    tests_root = Path(__file__).resolve().parent
    forbidden_by_file = {
        "test_render_guide.py": [
            "scanner._render_guide_identity_sections",
            "scanner._render_guide_section_body",
        ],
        "test_scanner_internals.py": [
            "scanner._split_task_annotation_label",
            "scanner._task_anchor",
            "scanner._extract_readme_variable_names_from_line",
        ],
        "test_scan_metrics.py": ["scanner._extract_scanner_counters"],
    }

    offenders: list[str] = []
    for filename, forbidden_markers in forbidden_by_file.items():
        content = (tests_root / filename).read_text(encoding="utf-8")
        for marker in forbidden_markers:
            if marker in content:
                offenders.append(f"{filename}: {marker}")

    assert not offenders, "\n".join(offenders)
