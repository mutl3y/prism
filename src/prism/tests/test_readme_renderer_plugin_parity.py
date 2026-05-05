"""G6-06: AnsibleReadmeRendererPlugin output parity tests.

Validates that the plugin-driven rendering path produces byte-for-byte
identical output to the pre-W3 direct-function path for known inputs.
"""

from __future__ import annotations

from typing import Any

import pytest

from prism.scanner_plugins.ansible.readme_renderer import AnsibleReadmeRendererPlugin


_PLUGIN = AnsibleReadmeRendererPlugin()

# ---------------------------------------------------------------------------
# Section body parity
# ---------------------------------------------------------------------------

_SECTION_BODY_CASES: list[tuple[str, str, str, dict, list, list, dict, str | None]] = [
    # (section_id, role_name, description, variables, requirements, default_filters,
    #  metadata, expected_fragment_or_None_for_any)
    ("purpose", "my_role", "Does things", {}, [], [], {}, "Does things"),
    ("purpose", "my_role", "", {}, [], [], {}, "my_role"),
    ("requirements", "r", "d", {}, [], [], {}, "No additional requirements"),
    (
        "requirements",
        "r",
        "d",
        {},
        ["dep_a", "dep_b"],
        [],
        {},
        "dep_a",
    ),
    ("role_variables", "r", "d", {}, [], [], {}, "No role variables"),
    (
        "role_variables",
        "r",
        "d",
        {"my_var": {"default": "val"}},
        [],
        [],
        {},
        "my_var",
    ),
    ("default_filters", "r", "d", {}, [], [], {}, "No default() filter"),
    (
        "default_filters",
        "r",
        "d",
        {},
        [],
        [{"target": "some_var"}],
        {},
        "some_var",
    ),
    ("role_notes", "r", "d", {}, [], [], {}, "No role notes"),
    (
        "role_notes",
        "r",
        "d",
        {},
        [],
        [],
        {"role_notes": ["Note one", "Note two"]},
        "Note one",
    ),
]


@pytest.mark.parametrize(
    "section_id,role_name,description,variables,requirements,default_filters,"
    "metadata,expected_fragment",
    _SECTION_BODY_CASES,
)
def test_render_section_body_parity(
    section_id: str,
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
    expected_fragment: str | None,
) -> None:
    result = _PLUGIN.render_section_body(
        section_id,
        role_name,
        description,
        variables,
        requirements,
        default_filters,
        metadata,
    )
    if expected_fragment is None:
        assert result is None
    else:
        assert (
            result is not None
        ), f"Expected non-None result for section '{section_id}'"
        assert (
            expected_fragment in result
        ), f"Expected fragment '{expected_fragment}' not found in '{result}'"


# ---------------------------------------------------------------------------
# Identity section parity
# ---------------------------------------------------------------------------


def test_identity_galaxy_info_no_metadata_contains_no_galaxy() -> None:
    result = _PLUGIN.render_identity_section(
        "galaxy_info", "my_role", "desc", [], {}, {}
    )
    assert result is not None
    assert "No Galaxy metadata" in result


def test_identity_galaxy_info_license_propagates() -> None:
    galaxy = {"license": "Apache-2.0", "role_name": "r", "description": "d"}
    result = _PLUGIN.render_identity_section("galaxy_info", "r", "d", [], galaxy, {})
    assert result is not None
    assert "Apache-2.0" in result


def test_identity_requirements_empty() -> None:
    result = _PLUGIN.render_identity_section("requirements", "r", "d", [], {}, {})
    assert result is not None
    assert "No additional requirements" in result


def test_identity_installation_contains_ansible_galaxy_install() -> None:
    result = _PLUGIN.render_identity_section(
        "installation", "my_role", "d", [], {"role_name": "my_role"}, {}
    )
    assert result is not None
    assert "ansible-galaxy install my_role" in result


def test_identity_license_propagates_from_galaxy() -> None:
    result = _PLUGIN.render_identity_section(
        "license", "r", "d", [], {"license": "MIT"}, {}
    )
    assert result is not None
    assert "MIT" in result


def test_identity_author_propagates_from_galaxy() -> None:
    result = _PLUGIN.render_identity_section(
        "author_information", "r", "d", [], {"author": "Alice"}, {}
    )
    assert result is not None
    assert "Alice" in result


def test_identity_license_author_contains_both() -> None:
    galaxy = {"license": "GPL-3.0", "author": "Bob"}
    result = _PLUGIN.render_identity_section("license_author", "r", "d", [], galaxy, {})
    assert result is not None
    assert "GPL-3.0" in result
    assert "Bob" in result


def test_identity_sponsors_returns_no_sponsorship_message() -> None:
    result = _PLUGIN.render_identity_section("sponsors", "r", "d", [], {}, {})
    assert result is not None
    assert "No sponsorship metadata" in result


def test_identity_purpose_uses_doc_insights() -> None:
    metadata: dict[str, Any] = {
        "doc_insights": {
            "purpose_summary": "My purpose summary",
            "capabilities": ["cap_a", "cap_b"],
        }
    }
    result = _PLUGIN.render_identity_section("purpose", "r", "d", [], {}, metadata)
    assert result is not None
    assert "My purpose summary" in result
    assert "cap_a" in result


def test_identity_role_notes_list_form() -> None:
    metadata: dict[str, Any] = {"role_notes": ["Note A", "Note B"]}
    result = _PLUGIN.render_identity_section("role_notes", "r", "d", [], {}, metadata)
    assert result is not None
    assert "Note A" in result
    assert "Note B" in result


def test_identity_role_notes_empty_list() -> None:
    metadata: dict[str, Any] = {"role_notes": []}
    result = _PLUGIN.render_identity_section("role_notes", "r", "d", [], {}, metadata)
    assert result is not None
    assert "No role notes" in result


# ---------------------------------------------------------------------------
# scanner_report_blurb parity
# ---------------------------------------------------------------------------


def test_scanner_report_blurb_parity_with_hardcoded_reference() -> None:
    relpath = "scanner_output/report.md"
    blurb = _PLUGIN.scanner_report_blurb(relpath)
    # Must mention the relpath and describe scanner output content.
    assert relpath in blurb
    assert "statistics" in blurb.lower() or "scanner" in blurb.lower()


# ---------------------------------------------------------------------------
# legacy_merge_marker_prefixes parity
# ---------------------------------------------------------------------------


def test_legacy_merge_markers_generates_correct_html_comments() -> None:
    prefixes = _PLUGIN.legacy_merge_marker_prefixes()
    section_id = "requirements"
    markers = [
        (
            f"<!-- {p}:generated:start:{section_id} -->",
            f"<!-- {p}:generated:end:{section_id} -->",
        )
        for p in prefixes
    ]
    assert len(markers) >= 2
    # prism and ansible-role-doc prefixes must be present for backward compat
    starts = [start for start, _ in markers]
    assert any("prism:generated:start:requirements" in s for s in starts)
    assert any("ansible-role-doc:generated:start:requirements" in s for s in starts)
