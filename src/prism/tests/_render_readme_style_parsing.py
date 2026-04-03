from prism import scanner
from prism.scanner_readme import style as readme_style


def test_detect_style_section_level_skips_headings_inside_fenced_blocks():
    """Headings inside fenced code blocks must not influence the detected level."""
    lines = [
        "# Title",
        "",
        "## Real Section",
        "",
        "```",
        "## Not a heading inside fence",
        "more content",
        "```",
        "",
        "## Another Section",
    ]
    level = readme_style.detect_style_section_level(lines)
    assert level == 2


def test_parse_style_readme_detects_table_variable_style(tmp_path):
    """parse_style_readme sets variable_style='table' for pipe-table variable sections."""
    style = tmp_path / "STYLE.md"
    style.write_text(
        "# Role\n\n"
        "Role Variables\n"
        "--------------\n\n"
        "Available variables:\n\n"
        "| Name | Default | Description |\n"
        "| --- | --- | --- |\n"
        "| `var1` | `value` | A variable |\n",
        encoding="utf-8",
    )
    parsed = scanner.parse_style_readme(str(style))
    assert parsed["variable_style"] == "table"
    assert parsed["variable_intro"] == "Available variables:"


def test_parse_style_readme_with_no_role_variables_section_returns_simple_list(
    tmp_path,
):
    """parse_style_readme defaults to simple_list when no Role Variables section exists."""
    style = tmp_path / "STYLE.md"
    style.write_text(
        "# Role\n\n" "Requirements\n" "------------\n\n" "Some requirements here.\n",
        encoding="utf-8",
    )
    parsed = scanner.parse_style_readme(str(style))
    assert parsed["variable_style"] == "simple_list"
    assert parsed["variable_intro"] is None


def test_parse_style_readme_detects_nested_bullets_with_intro(tmp_path):
    """parse_style_readme detects nested_bullets style with intro text before bullets."""
    style = tmp_path / "STYLE_NB_INTRO.md"
    style.write_text(
        "# Role\n\n"
        "Role Variables\n"
        "--------------\n\n"
        "Available below:\n\n"
        "- `var1`\n"
        "- Default: value1\n",
        encoding="utf-8",
    )
    parsed = scanner.parse_style_readme(str(style))
    assert parsed["variable_style"] == "nested_bullets"
    assert parsed["variable_intro"] == "Available below:"


def test_parse_style_readme_detects_nested_bullets_without_intro(tmp_path):
    """parse_style_readme detects nested_bullets style with no intro paragraph."""
    style = tmp_path / "STYLE_NB_PLAIN.md"
    style.write_text(
        "# Role\n\n"
        "Role Variables\n"
        "--------------\n\n"
        "- `var1`\n"
        "- Default: value1\n",
        encoding="utf-8",
    )
    parsed = scanner.parse_style_readme(str(style))
    assert parsed["variable_style"] == "nested_bullets"
    assert parsed["variable_intro"] is None


def test_detect_style_section_level_non_matching_fence_inside_fence():
    """A tilde fence inside a backtick fence does not close the backtick fence."""
    lines = [
        "# Title",
        "",
        "## Real Section",
        "",
        "```",
        "~~~",
        "## Still inside fence",
        "```",
        "",
        "## Outside Section",
    ]
    level = readme_style.detect_style_section_level(lines)
    assert level == 2
