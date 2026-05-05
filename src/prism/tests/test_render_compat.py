"""Tests for scanner_readme render and guide helpers (formerly via render_compat shim)."""

from __future__ import annotations


def test_scanner_readme_render_importable() -> None:
    import prism.scanner_readme.render  # noqa: F401


def test_generated_merge_markers_returns_list_of_tuples() -> None:
    from prism.scanner_readme.render import (
        _generated_merge_markers as generated_merge_markers,
    )

    result = generated_merge_markers("requirements")
    assert isinstance(result, list)
    assert result == [
        (
            "<!-- prism:generated:start:requirements -->",
            "<!-- prism:generated:end:requirements -->",
        )
    ]
    for pair in result:
        assert isinstance(pair, tuple)
        assert len(pair) == 2
        start, end = pair
        assert "requirements" in start
        assert "requirements" in end


def test_generated_merge_markers_honors_plugin_prefixes_when_provided() -> None:
    from prism.scanner_readme.render import (
        _generated_merge_markers as generated_merge_markers,
    )

    result = generated_merge_markers("requirements", ("prism", "ansible-role-doc"))
    assert result == [
        (
            "<!-- prism:generated:start:requirements -->",
            "<!-- prism:generated:end:requirements -->",
        ),
        (
            "<!-- ansible-role-doc:generated:start:requirements -->",
            "<!-- ansible-role-doc:generated:end:requirements -->",
        ),
    ]


def test_strip_prior_generated_merge_block_passthrough() -> None:
    from prism.scanner_readme.render import (
        _strip_prior_generated_merge_block as strip_prior_generated_merge_block,
    )

    section = {"id": "purpose"}
    guide_body = "This is the guide body with no markers."
    result = strip_prior_generated_merge_block(section, guide_body)
    assert result == guide_body


def test_strip_prior_generated_merge_block_removes_marked_content() -> None:
    from prism.scanner_readme.render import (
        _strip_prior_generated_merge_block as strip_prior_generated_merge_block,
    )

    section = {"id": "requirements"}
    guide_body = (
        "Header text\n\n"
        "<!-- prism:generated:start:requirements -->\n"
        "auto generated\n"
        "<!-- prism:generated:end:requirements -->\n\n"
        "Footer text"
    )

    result = strip_prior_generated_merge_block(section, guide_body)
    assert result == "Header text\n\nFooter text"


def test_strip_prior_generated_merge_block_uses_plugin_prefixes_when_metadata_supplied() -> (
    None
):
    from prism.scanner_readme.render import (
        _strip_prior_generated_merge_block as strip_prior_generated_merge_block,
    )

    section = {"id": "requirements"}
    guide_body = (
        "Header text\n\n"
        "<!-- ansible-role-doc:generated:start:requirements -->\n"
        "auto generated\n"
        "<!-- ansible-role-doc:generated:end:requirements -->\n\n"
        "Footer text"
    )

    result = strip_prior_generated_merge_block(
        section,
        guide_body,
        {"platform_key": "ansible"},
    )
    assert result == "Header text\n\nFooter text"


def test_strip_prior_generated_merge_block_removes_legacy_requirements_label() -> None:
    from prism.scanner_readme.render import (
        _strip_prior_generated_merge_block as strip_prior_generated_merge_block,
    )

    section = {"id": "requirements"}
    guide_body = "Requirements body\n\nDetected requirements from scanner:\n- pkg"

    result = strip_prior_generated_merge_block(section, guide_body)
    assert result == "Requirements body"


def test_resolve_section_content_mode_honors_configured_modes() -> None:
    from prism.scanner_readme.render import (
        _resolve_section_content_mode as resolve_section_content_mode,
    )

    section = {"id": "purpose", "body": "some content"}

    assert resolve_section_content_mode(section, {"purpose": "replace"}) == "replace"
    assert resolve_section_content_mode(section, {"purpose": "merge"}) == "merge"
    assert resolve_section_content_mode(section, {"purpose": "generate"}) == "generate"


def test_resolve_section_content_mode_defaults_to_merge_for_requirements() -> None:
    from prism.scanner_readme.render import (
        _resolve_section_content_mode as resolve_section_content_mode,
    )

    section = {"id": "requirements", "body": ""}
    assert resolve_section_content_mode(section, {}) == "merge"


def test_resolve_section_content_mode_defaults_to_merge_for_allowlisted_section_with_body() -> (
    None
):
    from prism.scanner_readme.render import (
        _resolve_section_content_mode as resolve_section_content_mode,
    )

    section = {"id": "purpose", "body": "authored guidance"}
    assert resolve_section_content_mode(section, {}) == "merge"


def test_resolve_section_content_mode_defaults_to_generate_for_unlisted_sections() -> (
    None
):
    from prism.scanner_readme.render import (
        _resolve_section_content_mode as resolve_section_content_mode,
    )

    section = {"id": "custom_section", "body": "authored guidance"}
    assert resolve_section_content_mode(section, {}) == "generate"


def test_resolve_section_content_mode_uses_plugin_merge_eligible_ids() -> None:
    from prism.scanner_plugins.ansible.readme_renderer import (
        AnsibleReadmeRendererPlugin,
    )
    from prism.scanner_readme.render import (
        _resolve_section_content_mode as resolve_section_content_mode,
    )

    section = {"id": "handlers", "body": "authored guidance"}
    plugin = AnsibleReadmeRendererPlugin()

    assert resolve_section_content_mode(section, {}, plugin) == "merge"


def test_render_guide_identity_sections_callable() -> None:
    from prism.scanner_readme.guide import (
        _render_guide_identity_sections as render_guide_identity_sections,
    )

    result = render_guide_identity_sections(
        section_id="sponsors",
        role_name="test_role",
        description="A test role",
        requirements=[],
        galaxy={},
        metadata={},
    )
    assert result is not None
    assert isinstance(result, str)
