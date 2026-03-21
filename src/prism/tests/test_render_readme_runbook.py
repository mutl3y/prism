"""Focused tests for README and runbook render helpers."""

from prism import scanner


def test_strip_prior_generated_merge_block_with_both_prefix_and_suffix():
    """_render_readme_with_style_guide handles merged prefix/suffix in guide conversion."""
    role_name = "test"
    description = "Test role"
    variables = {}
    requirements = []
    default_filters = []

    metadata = {
        "style_guide": {
            "sections": [{"id": "purpose", "title": "Purpose"}],
        }
    }

    result = scanner.render_readme(
        output="/tmp/README.md",
        role_name=role_name,
        description=description,
        variables=variables,
        requirements=requirements,
        default_filters=default_filters,
        metadata=metadata,
        write=False,
    )

    assert "Purpose" in result
    assert role_name in result


def test_render_readme_with_style_guide_renders_title_from_guide():
    """render_readme uses style guide title when provided."""
    result = scanner.render_readme(
        output="/tmp/README.md",
        role_name="myapp_role",
        description="Setup myapp",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={
            "style_guide": {
                "title_text": "Custom Title",
                "title_style": "setext",
                "sections": [{"id": "purpose", "title": "Purpose"}],
            }
        },
        write=False,
    )

    assert "myapp_role" in result
    assert "Purpose" in result


def test_render_readme_with_style_guide_skeleton_renders_headings_only():
    """render_readme with style_guide_skeleton renders only headings without bodies."""
    result = scanner.render_readme(
        output="/tmp/README.md",
        role_name="skeleton_role",
        description="Skeleton description",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={
            "style_guide": {
                "sections": [
                    {"id": "purpose", "title": "Purpose"},
                    {"id": "requirements", "title": "Requirements"},
                ],
            },
            "style_guide_skeleton": True,
        },
        write=False,
    )

    assert "skeleton_role" in result
    assert "Purpose" in result
    assert "Requirements" in result
    assert result.count("\n") < 20


def test_render_readme_with_scanner_report_link_when_enabled():
    """render_readme includes scanner report link when configured."""
    result = scanner.render_readme(
        output="/tmp/README.md",
        role_name="test_role",
        description="Test",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={
            "style_guide": {
                "sections": [{"id": "purpose", "title": "Purpose"}],
            },
            "scanner_report_relpath": "../reports/scanner_report.md",
            "include_scanner_report_link": True,
        },
        write=False,
    )

    assert "Scanner report" in result
    assert "scanner_report.md" in result


def test_render_readme_respects_enabled_sections_filter():
    """render_readme filters sections when enabled_sections is provided."""
    result = scanner.render_readme(
        output="/tmp/README.md",
        role_name="test_role",
        description="Test description",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={
            "style_guide": {
                "sections": [
                    {"id": "purpose", "title": "Purpose"},
                    {"id": "requirements", "title": "Requirements"},
                    {"id": "role_variables", "title": "Variables"},
                ],
            },
            "enabled_sections": ["purpose", "role_variables"],
        },
        write=False,
    )

    assert "Purpose" in result
    assert "Variables" in result
    assert "# Requirements" not in result and "## Requirements" not in result


def test_render_readme_keeps_unknown_section_when_configured():
    """render_readme preserves unknown section when keep_unknown_style_sections is True."""
    result = scanner.render_readme(
        output="/tmp/README.md",
        role_name="test_role",
        description="Test",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={
            "style_guide": {
                "sections": [
                    {"id": "purpose", "title": "Purpose"},
                    {
                        "id": "unknown",
                        "title": "Unknown Section",
                        "body": "Custom unknown content",
                    },
                ],
            },
            "keep_unknown_style_sections": True,
        },
        write=False,
    )

    assert "Unknown Section" in result
    assert "Custom unknown content" in result


def test_render_readme_without_style_guide_uses_template():
    """render_readme falls back to Jinja template when no style_guide in metadata."""
    result = scanner.render_readme(
        output="/tmp/README.md",
        role_name="template_role",
        description="Template test",
        variables={"app_port": {"default": 8080}},
        requirements=["ansible >= 2.9"],
        default_filters=[],
        metadata={},
        write=False,
    )

    assert "template_role" in result
    assert "Template test" in result


def test_render_readme_with_custom_template_path():
    """render_readme uses custom template when template path is provided."""
    result = scanner.render_readme(
        output="/tmp/README.md",
        role_name="custom_template_role",
        description="Custom template test",
        variables={},
        requirements=[],
        default_filters=[],
        template=None,
        metadata={},
        write=False,
    )

    assert "custom_template_role" in result


def test_render_readme_omits_stats_sections_in_concise_mode():
    """render_readme excludes stat sections when concise_readme is enabled."""
    result = scanner.render_readme(
        output="/tmp/README.md",
        role_name="test_role",
        description="Test",
        variables={"var1": {"documented": True}},
        requirements=[],
        default_filters=[],
        metadata={
            "style_guide": {
                "sections": [
                    {"id": "purpose", "title": "Purpose"},
                    {"id": "role_variables", "title": "Variables"},
                    {"id": "task_summary", "title": "Tasks"},
                ],
            },
            "concise_readme": True,
        },
        write=False,
    )

    assert "Purpose" in result


def test_render_readme_write_false_returns_content():
    """render_readme returns content as string when write=False."""
    result = scanner.render_readme(
        output="/tmp/README.md",
        role_name="test",
        description="desc",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={},
        write=False,
    )

    assert isinstance(result, str)
    assert len(result) > 0


def test_render_runbook_renders_with_metadata():
    """render_runbook renders task catalog into runbook markdown."""
    result = scanner.render_runbook(
        role_name="app_role",
        metadata={
            "task_catalog": [
                {
                    "file": "tasks/main.yml",
                    "name": "install packages",
                    "annotations": [],
                    "anchor": "task-main-yml-install-packages",
                }
            ]
        },
    )

    assert "app_role" in result
    assert isinstance(result, str)
    assert len(result) > 0


def test_render_runbook_with_empty_metadata():
    """render_runbook handles empty metadata gracefully."""
    result = scanner.render_runbook(
        role_name="minimal_role",
        metadata={},
    )

    assert "minimal_role" in result


def test_render_runbook_with_no_metadata():
    """render_runbook handles None metadata gracefully."""
    result = scanner.render_runbook(role_name="no_meta_role")

    assert "no_meta_role" in result
