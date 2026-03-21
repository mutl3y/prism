from pathlib import Path

import pytest

from prism import scanner


# ---------------------------------------------------------------------------
# readme_config branch coverage
# ---------------------------------------------------------------------------


def _write_role_prism_config(tmp_path: Path, config_text: str) -> Path:
    """Create a role fixture with a .prism.yml config and return role path."""
    role = tmp_path / "role"
    role.mkdir(exist_ok=True)
    (role / ".prism.yml").write_text(config_text, encoding="utf-8")
    return role


def _load_section_display_titles_from_fixture(
    tmp_path: Path,
    config_text: str | None = None,
    filename: str = "titles.yml",
) -> dict[str, str]:
    """Load display titles from a temp fixture file.

    When ``config_text`` is omitted, the file is intentionally left missing.
    """
    from prism.scanner_submodules.readme_config import _load_section_display_titles

    fixture = tmp_path / filename
    if config_text is not None:
        fixture.write_text(config_text, encoding="utf-8")
    return _load_section_display_titles(fixture)


def test_resolve_role_config_file_uses_explicit_config_path(tmp_path):
    """resolve_role_config_file returns Path(config_path) when provided."""
    from prism.scanner_submodules.readme_config import resolve_role_config_file

    role = tmp_path / "role"
    role.mkdir()
    cfg = tmp_path / "custom.yml"
    cfg.write_text("{}", encoding="utf-8")
    result = resolve_role_config_file(str(role), config_path=str(cfg))
    assert result == cfg


@pytest.mark.parametrize(
    "config_text",
    [
        "key: [\n  unclosed bracket\n",
        "- item1\n- item2\n",
        "markers:\n  prefix: 42\n",
        "markers:\n  prefix: '   '\n",
        "markers:\n  prefix: 'has space!'\n",
    ],
)
def test_load_readme_marker_prefix_invalid_config_falls_back_to_default(
    tmp_path, config_text
):
    """Invalid prefix config variants should all return default marker prefix."""
    role = _write_role_prism_config(tmp_path, config_text)
    assert scanner.load_readme_marker_prefix(str(role)) == "prism"


def test_load_fail_on_unconstrained_dynamic_includes_handles_native_bool(tmp_path):
    """_coerce_bool handles a native Python bool (YAML true/false)."""
    role = _write_role_prism_config(
        tmp_path, "fail_on_unconstrained_dynamic_includes: true\n"
    )
    assert scanner.load_fail_on_unconstrained_dynamic_includes(str(role)) is True


def test_load_fail_on_unconstrained_dynamic_includes_handles_falsey_string(tmp_path):
    """_coerce_bool returns False for 'false', 'no', '0', 'off' strings."""
    role = _write_role_prism_config(
        tmp_path,
        "fail_on_unconstrained_dynamic_includes: 'false'\n",
    )
    assert scanner.load_fail_on_unconstrained_dynamic_includes(str(role)) is False


def test_load_fail_on_unconstrained_dynamic_includes_returns_default_on_parse_error(
    tmp_path,
):
    """load_fail_on_unconstrained_dynamic_includes falls back on invalid YAML."""
    role = _write_role_prism_config(tmp_path, "key: [\n  unclosed\n")
    assert (
        scanner.load_fail_on_unconstrained_dynamic_includes(str(role), default=True)
        is True
    )


def test_load_fail_on_unconstrained_dynamic_includes_returns_default_when_not_dict(
    tmp_path,
):
    """load_fail_on_unconstrained_dynamic_includes falls back when root is a list."""
    role = _write_role_prism_config(tmp_path, "- foo\n- bar\n")
    assert scanner.load_fail_on_unconstrained_dynamic_includes(str(role)) is False


def test_load_fail_on_yaml_like_task_annotations_reads_scan_toggle(tmp_path):
    """load_fail_on_yaml_like_task_annotations reads scan-level toggle values."""
    role = _write_role_prism_config(
        tmp_path,
        "scan:\n  fail_on_yaml_like_task_annotations: 'yes'\n",
    )
    assert scanner.load_fail_on_yaml_like_task_annotations(str(role)) is True


def test_load_fail_on_yaml_like_task_annotations_returns_default_on_parse_error(
    tmp_path,
):
    """load_fail_on_yaml_like_task_annotations falls back on invalid YAML."""
    role = _write_role_prism_config(tmp_path, "scan: [\n  unclosed\n")
    assert scanner.load_fail_on_yaml_like_task_annotations(str(role), default=True)


def test_load_readme_section_visibility_returns_enabled_sections_set(tmp_path):
    """load_readme_section_visibility returns a set of enabled section ids."""
    role = _write_role_prism_config(
        tmp_path,
        "readme:\n  include_sections:\n    - galaxy_info\n",
    )
    result = scanner.load_readme_section_visibility(str(role))
    assert isinstance(result, set)
    assert "galaxy_info" in result


def test_load_readme_section_config_non_dict_raw_returns_none(tmp_path):
    """load_readme_section_config returns None when config root is a list."""
    role = _write_role_prism_config(tmp_path, "- foo\n- bar\n")
    assert scanner.load_readme_section_config(str(role)) is None


def test_load_readme_section_config_skips_non_string_include_items(tmp_path):
    """load_readme_section_config silently skips non-string include_sections items."""
    role = _write_role_prism_config(
        tmp_path,
        "readme:\n  include_sections:\n    - 42\n    - galaxy_info\n",
    )
    config = scanner.load_readme_section_config(str(role))
    assert config is not None
    assert "galaxy_info" in config["enabled_sections"]


def test_load_readme_section_config_skips_unresolvable_include_items(tmp_path):
    """load_readme_section_config silently skips include items that do not resolve."""
    role = _write_role_prism_config(
        tmp_path,
        "readme:\n  include_sections:\n    - totally_unknown_section_xyz\n    - galaxy_info\n",
    )
    config = scanner.load_readme_section_config(str(role))
    assert config is not None
    assert "galaxy_info" in config["enabled_sections"]
    assert "totally_unknown_section_xyz" not in config["enabled_sections"]


def test_load_readme_section_config_skips_non_string_exclude_items(tmp_path):
    """load_readme_section_config silently skips non-string exclude_sections items."""
    role = _write_role_prism_config(
        tmp_path, "readme:\n  exclude_sections:\n    - 99\n"
    )
    config = scanner.load_readme_section_config(str(role))
    assert config is not None


def test_load_readme_section_config_popular_mode_applies_display_title_overrides(
    tmp_path, monkeypatch
):
    """Popular adopt_heading_mode copies display titles into title_overrides."""
    role = tmp_path / "role"
    role.mkdir()
    titles = tmp_path / "titles.yml"
    titles.write_text(
        "display_titles:\n  galaxy_info: Galaxy Metadata\n", encoding="utf-8"
    )
    _write_role_prism_config(
        tmp_path,
        "readme:\n"
        "  include_sections:\n"
        "    - galaxy_info\n"
        "  adopt_heading_mode: popular\n",
    )
    monkeypatch.setattr(scanner, "DEFAULT_SECTION_DISPLAY_TITLES_PATH", titles)
    config = scanner.load_readme_section_config(str(role), adopt_heading_mode="popular")
    assert config is not None
    assert config["section_title_overrides"].get("galaxy_info") == "Galaxy Metadata"


def test_load_readme_section_config_skips_non_string_content_mode_entries(tmp_path):
    """load_readme_section_config ignores non-string selector/mode in section_content_modes."""
    role = _write_role_prism_config(
        tmp_path,
        "readme:\n"
        "  include_sections:\n"
        "    - galaxy_info\n"
        "  section_content_modes:\n"
        "    galaxy_info: generate\n"
        "    123: replace\n",
    )
    config = scanner.load_readme_section_config(str(role))
    assert config is not None
    assert config["section_content_modes"].get("galaxy_info") == "generate"


def test_load_section_display_titles_returns_empty_for_missing_path(tmp_path):
    """_load_section_display_titles returns {} when path does not exist."""
    result = _load_section_display_titles_from_fixture(
        tmp_path,
        config_text=None,
        filename="nonexistent.yml",
    )
    assert result == {}


def test_load_section_display_titles_returns_empty_on_invalid_yaml(tmp_path):
    """_load_section_display_titles returns {} on YAML parse error."""
    result = _load_section_display_titles_from_fixture(
        tmp_path,
        config_text="key: [\n  unclosed\n",
        filename="bad.yml",
    )
    assert result == {}


@pytest.mark.parametrize(
    "config_text",
    [
        "- item1\n- item2\n",
        "display_titles: 'not a dict'\n",
    ],
)
def test_load_section_display_titles_returns_empty_for_invalid_shape(
    tmp_path, config_text
):
    """_load_section_display_titles returns {} for non-dict root/payload variants."""
    result = _load_section_display_titles_from_fixture(tmp_path, config_text)
    assert result == {}


def test_load_section_display_titles_skips_non_string_keys_or_values(tmp_path):
    """_load_section_display_titles skips entries with non-string key or value."""
    result = _load_section_display_titles_from_fixture(
        tmp_path,
        "display_titles:\n" "  valid_section: Valid Label\n" "  42: bad key\n",
    )
    assert result == {"valid_section": "Valid Label"}
