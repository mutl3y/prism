"""G6-06: ReadmeRendererPlugin protocol compliance tests.

Validates that AnsibleReadmeRendererPlugin fully satisfies the
ReadmeRendererPlugin protocol contract: API version, stateless marker,
and all 8 method signatures.
"""

from __future__ import annotations

import pathlib


from prism.scanner_plugins.ansible.readme_renderer import AnsibleReadmeRendererPlugin
from prism.scanner_plugins.interfaces import ReadmeRendererPlugin


# ---- class-level metadata ------------------------------------------------


def test_prism_plugin_api_version_is_tuple_of_two_ints() -> None:
    v = AnsibleReadmeRendererPlugin.PRISM_PLUGIN_API_VERSION
    assert isinstance(v, tuple)
    assert len(v) == 2
    assert all(isinstance(x, int) for x in v)


def test_prism_plugin_api_version_is_1_0() -> None:
    assert AnsibleReadmeRendererPlugin.PRISM_PLUGIN_API_VERSION == (1, 0)


def test_plugin_is_stateless_is_true() -> None:
    assert AnsibleReadmeRendererPlugin.PLUGIN_IS_STATELESS is True


# ---- protocol structural compliance --------------------------------------


def test_is_runtime_checkable_subtype() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    assert isinstance(plugin, ReadmeRendererPlugin)


# ---- default_section_specs -----------------------------------------------


def test_default_section_specs_returns_tuple_of_pairs() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    specs = plugin.default_section_specs()
    assert isinstance(specs, tuple)
    assert len(specs) > 0
    for item in specs:
        assert isinstance(item, tuple)
        assert len(item) == 2
        assert all(isinstance(s, str) for s in item)


def test_default_section_specs_contains_expected_ids() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    ids = {sid for sid, _ in plugin.default_section_specs()}
    for expected in (
        "galaxy_info",
        "requirements",
        "role_variables",
        "default_filters",
    ):
        assert expected in ids, f"Missing expected section id: {expected}"


# ---- extra_section_ids ---------------------------------------------------


def test_extra_section_ids_returns_frozenset_of_strings() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    result = plugin.extra_section_ids()
    assert isinstance(result, frozenset)
    assert all(isinstance(s, str) for s in result)


def test_extra_section_ids_contains_scanner_report() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    assert "scanner_report" in plugin.extra_section_ids()


# ---- scanner_stats_section_ids -------------------------------------------


def test_scanner_stats_section_ids_returns_frozenset() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    result = plugin.scanner_stats_section_ids()
    assert isinstance(result, frozenset)


def test_scanner_stats_section_ids_contains_task_summary() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    assert "task_summary" in plugin.scanner_stats_section_ids()


# ---- merge_eligible_section_ids ------------------------------------------


def test_merge_eligible_section_ids_returns_frozenset() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    result = plugin.merge_eligible_section_ids()
    assert isinstance(result, frozenset)


def test_merge_eligible_section_ids_contains_requirements() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    assert "requirements" in plugin.merge_eligible_section_ids()


# ---- legacy_merge_marker_prefixes ----------------------------------------


def test_legacy_merge_marker_prefixes_returns_tuple_of_strings() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    result = plugin.legacy_merge_marker_prefixes()
    assert isinstance(result, tuple)
    assert all(isinstance(s, str) for s in result)


def test_legacy_merge_marker_prefixes_includes_prism_and_ansible_role_doc() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    prefixes = plugin.legacy_merge_marker_prefixes()
    assert "prism" in prefixes
    assert "ansible-role-doc" in prefixes


# ---- render_section_body -------------------------------------------------


def test_render_section_body_purpose_returns_description() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    result = plugin.render_section_body(
        "purpose", "my_role", "Does things", {}, [], [], {}
    )
    assert result == "Does things"


def test_render_section_body_purpose_falls_back_to_role_name() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    result = plugin.render_section_body("purpose", "my_role", "", {}, [], [], {})
    assert "my_role" in (result or "")


def test_render_section_body_requirements_no_reqs() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    result = plugin.render_section_body("requirements", "r", "d", {}, [], [], {})
    assert "No additional requirements" in (result or "")


def test_render_section_body_requirements_with_items() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    result = plugin.render_section_body(
        "requirements", "r", "d", {}, ["req_a", "req_b"], [], {}
    )
    assert "req_a" in (result or "")
    assert "req_b" in (result or "")


def test_render_section_body_unknown_section_returns_none() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    result = plugin.render_section_body(
        "completely_unknown_section_xyz", "r", "d", {}, [], [], {}
    )
    assert result is None


# ---- render_identity_section ---------------------------------------------


def test_render_identity_section_galaxy_info_no_metadata() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    result = plugin.render_identity_section(
        "galaxy_info", "my_role", "desc", [], {}, {}
    )
    assert result is not None
    assert "No Galaxy metadata" in result


def test_render_identity_section_galaxy_info_with_metadata() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    galaxy = {"role_name": "my_role", "description": "desc", "license": "MIT"}
    result = plugin.render_identity_section(
        "galaxy_info", "my_role", "desc", [], galaxy, {}
    )
    assert result is not None
    assert "MIT" in result


def test_render_identity_section_installation_returns_ansible_galaxy_command() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    result = plugin.render_identity_section(
        "installation", "my_role", "desc", [], {"role_name": "my_role"}, {}
    )
    assert result is not None
    assert "ansible-galaxy install" in result


def test_render_identity_section_unknown_returns_none() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    result = plugin.render_identity_section("not_a_real_section", "r", "d", [], {}, {})
    assert result is None


# ---- default_template_path -----------------------------------------------


def test_default_template_path_returns_path_object() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    path = plugin.default_template_path()
    assert isinstance(path, pathlib.Path)


def test_default_template_path_points_to_existing_template() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    path = plugin.default_template_path()
    assert path is not None
    assert path.exists(), f"Template not found: {path}"
    assert path.suffix == ".j2"


# ---- scanner_report_blurb ------------------------------------------------


def test_scanner_report_blurb_includes_relpath() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    blurb = plugin.scanner_report_blurb("scanner_report.md")
    assert "scanner_report.md" in blurb


def test_scanner_report_blurb_is_non_empty_string() -> None:
    plugin = AnsibleReadmeRendererPlugin()
    blurb = plugin.scanner_report_blurb("some/path.md")
    assert isinstance(blurb, str)
    assert len(blurb) > 0
