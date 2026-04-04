"""Focused tests for canonical scan-request option normalization helpers."""

import inspect

import pytest

from prism import scanner
from prism.scanner_core import scan_request
from prism.scanner_data import ScanOptionsDict


def test_resolve_detailed_catalog_flag_enables_catalog_for_runbook_outputs():
    assert (
        scan_request.resolve_scan_request_for_runtime(
            detailed_catalog=False,
            runbook_output="runbook.md",
            runbook_csv_output=None,
        )
        is True
    )
    assert (
        scan_request.resolve_scan_request_for_runtime(
            detailed_catalog=False,
            runbook_output=None,
            runbook_csv_output="runbook.csv",
        )
        is True
    )


def test_resolve_detailed_catalog_flag_preserves_explicit_flag_without_runbooks():
    assert (
        scan_request.resolve_scan_request_for_runtime(
            detailed_catalog=True,
            runbook_output=None,
            runbook_csv_output=None,
        )
        is True
    )
    assert (
        scan_request.resolve_scan_request_for_runtime(
            detailed_catalog=False,
            runbook_output=None,
            runbook_csv_output=None,
        )
        is False
    )


def test_build_run_scan_options_canonical_shapes_expected_option_map():
    options = scan_request.build_run_scan_options_canonical(
        role_path="/tmp/role",
        role_name_override="demo_role",
        readme_config_path="/tmp/role/.prism.yml",
        include_vars_main=True,
        exclude_path_patterns=["tasks/generated/*"],
        detailed_catalog=False,
        include_task_parameters=True,
        include_task_runbooks=False,
        inline_task_runbooks=False,
        include_collection_checks=True,
        keep_unknown_style_sections=True,
        adopt_heading_mode="canonical",
        vars_seed_paths=["vars/seed.yml"],
        style_readme_path=None,
        style_source_path="/tmp/style.md",
        style_guide_skeleton=False,
        compare_role_path=None,
        fail_on_unconstrained_dynamic_includes=None,
        fail_on_yaml_like_task_annotations=True,
        ignore_unresolved_internal_underscore_references=False,
    )

    assert isinstance(options, dict)
    assert options["role_path"] == "/tmp/role"
    assert options["role_name_override"] == "demo_role"
    assert options["readme_config_path"] == "/tmp/role/.prism.yml"
    assert options["exclude_path_patterns"] == ["tasks/generated/*"]
    assert options["include_task_runbooks"] is False
    assert options["fail_on_unconstrained_dynamic_includes"] is None
    assert options["fail_on_yaml_like_task_annotations"] is True
    assert options["ignore_unresolved_internal_underscore_references"] is False


def test_scan_options_dict_is_re_exported_from_scanner_data():
    assert ScanOptionsDict is not None


def test_scanner_build_run_scan_options_canonical_is_deterministic_for_same_inputs():
    first = scan_request.build_run_scan_options_canonical(
        role_path="/tmp/role",
        role_name_override=None,
        readme_config_path=None,
        include_vars_main=True,
        exclude_path_patterns=None,
        detailed_catalog=False,
        include_task_parameters=True,
        include_task_runbooks=True,
        inline_task_runbooks=True,
        include_collection_checks=True,
        keep_unknown_style_sections=True,
        adopt_heading_mode=None,
        vars_seed_paths=None,
        style_readme_path=None,
        style_source_path=None,
        style_guide_skeleton=False,
        compare_role_path=None,
        fail_on_unconstrained_dynamic_includes=None,
        fail_on_yaml_like_task_annotations=None,
        ignore_unresolved_internal_underscore_references=None,
    )
    second = scan_request.build_run_scan_options_canonical(
        role_path="/tmp/role",
        role_name_override=None,
        readme_config_path=None,
        include_vars_main=True,
        exclude_path_patterns=None,
        detailed_catalog=False,
        include_task_parameters=True,
        include_task_runbooks=True,
        inline_task_runbooks=True,
        include_collection_checks=True,
        keep_unknown_style_sections=True,
        adopt_heading_mode=None,
        vars_seed_paths=None,
        style_readme_path=None,
        style_source_path=None,
        style_guide_skeleton=False,
        compare_role_path=None,
        fail_on_unconstrained_dynamic_includes=None,
        fail_on_yaml_like_task_annotations=None,
        ignore_unresolved_internal_underscore_references=None,
    )

    assert first == second


def test_scanner_resolve_detailed_catalog_flag_is_deterministic_for_same_inputs():
    first = scan_request.resolve_scan_request_for_runtime(
        detailed_catalog=False,
        runbook_output="runbook.md",
        runbook_csv_output=None,
    )
    second = scan_request.resolve_scan_request_for_runtime(
        detailed_catalog=False,
        runbook_output="runbook.md",
        runbook_csv_output=None,
    )

    assert first is True
    assert first == second


def test_scanner_no_longer_keeps_scan_request_compatibility_imports():
    scanner_source = inspect.getsource(scanner)

    assert "scanner_submodules.scan_request" not in scanner_source


def test_scanner_core_build_run_scan_options_canonical_shapes_expected_option_map():
    options = scan_request.build_run_scan_options_canonical(
        role_path="/tmp/role",
        role_name_override="demo_role",
        readme_config_path="/tmp/role/.prism.yml",
        include_vars_main=True,
        exclude_path_patterns=["tasks/generated/*"],
        detailed_catalog=False,
        include_task_parameters=True,
        include_task_runbooks=False,
        inline_task_runbooks=False,
        include_collection_checks=True,
        keep_unknown_style_sections=True,
        adopt_heading_mode="canonical",
        vars_seed_paths=["vars/seed.yml"],
        style_readme_path=None,
        style_source_path="/tmp/style.md",
        style_guide_skeleton=False,
        compare_role_path=None,
        fail_on_unconstrained_dynamic_includes=None,
        fail_on_yaml_like_task_annotations=True,
        ignore_unresolved_internal_underscore_references=False,
    )

    assert options["role_path"] == "/tmp/role"
    assert options["role_name_override"] == "demo_role"
    assert options["readme_config_path"] == "/tmp/role/.prism.yml"
    assert options["exclude_path_patterns"] == ["tasks/generated/*"]
    assert options["include_task_runbooks"] is False
    assert options["fail_on_unconstrained_dynamic_includes"] is None
    assert options["fail_on_yaml_like_task_annotations"] is True
    assert options["ignore_unresolved_internal_underscore_references"] is False


def test_scanner_no_longer_exports_run_scan_canonical_alias_helpers():
    assert not hasattr(scanner, "_build_run_scan_options")
    assert not hasattr(scanner, "_resolve_detailed_catalog_flag")
    assert not hasattr(scanner, "_build_run_scan_options_canonical")
    assert not hasattr(scanner, "_resolve_detailed_catalog_flag_canonical")
    assert not hasattr(scanner, "_render_guide_section_body")


def _build_valid_scan_options(**overrides):
    """Return a valid canonical request payload, optionally overridden per test."""
    options = {
        "role_path": "/tmp/role",
        "role_name_override": None,
        "readme_config_path": None,
        "include_vars_main": True,
        "exclude_path_patterns": ["tasks/generated/*"],
        "detailed_catalog": False,
        "include_task_parameters": True,
        "include_task_runbooks": True,
        "inline_task_runbooks": False,
        "include_collection_checks": True,
        "keep_unknown_style_sections": True,
        "adopt_heading_mode": None,
        "vars_seed_paths": ["vars/seed.yml"],
        "style_readme_path": None,
        "style_source_path": None,
        "style_guide_skeleton": False,
        "compare_role_path": None,
        "fail_on_unconstrained_dynamic_includes": None,
        "fail_on_yaml_like_task_annotations": None,
        "ignore_unresolved_internal_underscore_references": None,
        "policy_context": {
            "section_aliases": {"runtime inputs": "inputs"},
            "ignored_identifiers": frozenset({"omit"}),
            "variable_guidance_keywords": ("required", "default"),
        },
    }
    options.update(overrides)
    return options


@pytest.mark.parametrize("role_path", ["", "   ", None, 42])
def test_build_run_scan_options_canonical_rejects_invalid_role_path(role_path):
    with pytest.raises(ValueError, match="'role_path' must be a non-empty string"):
        scan_request.build_run_scan_options_canonical(
            **_build_valid_scan_options(role_path=role_path)
        )


@pytest.mark.parametrize(
    ("field_name", "field_value", "message"),
    [
        ("role_name_override", 7, "'role_name_override' must be a string or None"),
        ("readme_config_path", False, "'readme_config_path' must be a string or None"),
        (
            "adopt_heading_mode",
            ["canonical"],
            "'adopt_heading_mode' must be a string or None",
        ),
        ("style_readme_path", object(), "'style_readme_path' must be a string or None"),
        ("style_source_path", {}, "'style_source_path' must be a string or None"),
        ("compare_role_path", 3.14, "'compare_role_path' must be a string or None"),
    ],
)
def test_build_run_scan_options_canonical_rejects_invalid_optional_string_fields(
    field_name, field_value, message
):
    with pytest.raises(ValueError, match=message):
        scan_request.build_run_scan_options_canonical(
            **_build_valid_scan_options(**{field_name: field_value})
        )


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("include_vars_main", "yes"),
        ("detailed_catalog", 1),
        ("include_task_parameters", None),
        ("include_task_runbooks", "false"),
        ("inline_task_runbooks", []),
        ("include_collection_checks", "true"),
        ("keep_unknown_style_sections", {}),
        ("style_guide_skeleton", "no"),
    ],
)
def test_build_run_scan_options_canonical_rejects_invalid_bool_fields(
    field_name, field_value
):
    with pytest.raises(ValueError, match=rf"'{field_name}' must be a bool"):
        scan_request.build_run_scan_options_canonical(
            **_build_valid_scan_options(**{field_name: field_value})
        )


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("fail_on_unconstrained_dynamic_includes", "strict"),
        ("fail_on_yaml_like_task_annotations", 1),
        ("ignore_unresolved_internal_underscore_references", []),
    ],
)
def test_build_run_scan_options_canonical_rejects_invalid_optional_bool_fields(
    field_name, field_value
):
    with pytest.raises(ValueError, match=rf"'{field_name}' must be a bool or None"):
        scan_request.build_run_scan_options_canonical(
            **_build_valid_scan_options(**{field_name: field_value})
        )


@pytest.mark.parametrize(
    ("field_name", "field_value", "message"),
    [
        (
            "exclude_path_patterns",
            "tasks/generated/*",
            "'exclude_path_patterns' must be a list\\[str\\] or None",
        ),
        (
            "exclude_path_patterns",
            [1, "tasks/*"],
            "'exclude_path_patterns' must contain only strings",
        ),
        (
            "vars_seed_paths",
            "vars/seed.yml",
            "'vars_seed_paths' must be a list\\[str\\] or None",
        ),
        (
            "vars_seed_paths",
            ["vars/seed.yml", 5],
            "'vars_seed_paths' must contain only strings",
        ),
    ],
)
def test_build_run_scan_options_canonical_rejects_invalid_optional_string_list_fields(
    field_name, field_value, message
):
    with pytest.raises(ValueError, match=message):
        scan_request.build_run_scan_options_canonical(
            **_build_valid_scan_options(**{field_name: field_value})
        )


@pytest.mark.parametrize(
    ("policy_context", "message"),
    [
        ("bad", "'policy_context' must be a dict or None"),
        (
            {
                "section_aliases": ["runtime inputs"],
                "ignored_identifiers": frozenset({"omit"}),
                "variable_guidance_keywords": ("required",),
            },
            "'policy_context.section_aliases' must be a dict\\[str, str\\]",
        ),
        (
            {
                "section_aliases": {"runtime inputs": 1},
                "ignored_identifiers": frozenset({"omit"}),
                "variable_guidance_keywords": ("required",),
            },
            "'policy_context.section_aliases' must be a dict\\[str, str\\]",
        ),
        (
            {
                "section_aliases": {"runtime inputs": "inputs"},
                "ignored_identifiers": {"omit"},
                "variable_guidance_keywords": ("required",),
            },
            "'policy_context.ignored_identifiers' must be a frozenset\\[str\\]",
        ),
        (
            {
                "section_aliases": {"runtime inputs": "inputs"},
                "ignored_identifiers": frozenset({1}),
                "variable_guidance_keywords": ("required",),
            },
            "'policy_context.ignored_identifiers' must be a frozenset\\[str\\]",
        ),
        (
            {
                "section_aliases": {"runtime inputs": "inputs"},
                "ignored_identifiers": frozenset({"omit"}),
                "variable_guidance_keywords": ["required"],
            },
            "'policy_context.variable_guidance_keywords' must be a tuple\\[str, \\.\\.\\.\\]",
        ),
        (
            {
                "section_aliases": {"runtime inputs": "inputs"},
                "ignored_identifiers": frozenset({"omit"}),
                "variable_guidance_keywords": ("required", 5),
            },
            "'policy_context.variable_guidance_keywords' must be a tuple\\[str, \\.\\.\\.\\]",
        ),
    ],
)
def test_build_run_scan_options_canonical_rejects_invalid_policy_context(
    policy_context, message
):
    with pytest.raises(ValueError, match=message):
        scan_request.build_run_scan_options_canonical(
            **_build_valid_scan_options(policy_context=policy_context)
        )
