"""Focused tests for guide/body rendering extraction (modernization slice 2a)."""

from prism import scanner
from prism.scanner_submodules import render_guide


def test_render_guide_identity_sections_matches_scanner_wrapper_for_license_author():
    metadata = {
        "meta": {
            "galaxy_info": {
                "license": "BSD-3-Clause",
                "author": "Example Author",
            }
        }
    }
    galaxy = metadata["meta"]["galaxy_info"]

    wrapped = scanner._render_guide_identity_sections(
        "license_author",
        "demo",
        "desc",
        [],
        galaxy,
        metadata,
    )
    extracted = render_guide._render_guide_identity_sections(
        "license_author",
        "demo",
        "desc",
        [],
        galaxy,
        metadata,
    )

    assert extracted == wrapped
    assert extracted == "License: BSD-3-Clause\n\nAuthor: Example Author"


def test_render_guide_section_body_matches_scanner_wrapper_for_faq_pitfalls():
    metadata = {
        "meta": {"galaxy_info": {}},
        "features": {"recursive_task_includes": 2},
        "doc_insights": {},
        "tests": [],
        "variable_insights": [],
    }
    default_filters = [
        {"file": "tasks/main.yml", "line_no": 1, "match": "x", "args": "y"}
    ]

    wrapped = scanner._render_guide_section_body(
        "faq_pitfalls",
        "demo",
        "desc",
        {},
        [],
        default_filters,
        metadata,
    )
    extracted = render_guide._render_guide_section_body(
        "faq_pitfalls",
        "demo",
        "desc",
        {},
        [],
        default_filters,
        metadata,
    )

    assert extracted == wrapped
    assert "Ensure default values are defined" in extracted
    assert "Nested include chains are detected" in extracted
    assert "`default()` usages are captured" in extracted


def test_render_guide_section_body_unknown_section_is_empty_string():
    rendered = render_guide._render_guide_section_body(
        "unknown_custom_section",
        "demo",
        "desc",
        {},
        [],
        [],
        {"meta": {}},
    )

    assert rendered == ""
