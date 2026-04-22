"""Tests for fsrc scanner_compat.render_compat compatibility shim."""

from __future__ import annotations


def test_render_compat_importable() -> None:
    import prism.scanner_compat.render_compat  # noqa: F401


def test_generated_merge_markers_returns_list_of_tuples() -> None:
    from prism.scanner_compat.render_compat import generated_merge_markers

    result = generated_merge_markers("requirements")
    assert isinstance(result, list)
    assert len(result) >= 1
    for pair in result:
        assert isinstance(pair, tuple)
        assert len(pair) == 2
        start, end = pair
        assert "requirements" in start
        assert "requirements" in end


def test_strip_prior_generated_merge_block_passthrough() -> None:
    from prism.scanner_compat.render_compat import strip_prior_generated_merge_block

    section = {"id": "purpose"}
    guide_body = "This is the guide body with no markers."
    result = strip_prior_generated_merge_block(section, guide_body)
    assert result == guide_body


def test_resolve_section_content_mode_returns_string() -> None:
    from prism.scanner_compat.render_compat import resolve_section_content_mode

    section = {"id": "purpose", "body": "some content"}
    modes: dict[str, str] = {}
    result = resolve_section_content_mode(section, modes)
    assert isinstance(result, str)
    assert result in {"generate", "replace", "merge"}


def test_render_guide_identity_sections_callable() -> None:
    from prism.scanner_compat.render_compat import render_guide_identity_sections

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
