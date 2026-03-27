"""Focused tests for scan-request option normalization helpers."""

from prism import scanner
from prism.scanner_submodules import scan_request


def test_resolve_detailed_catalog_flag_enables_catalog_for_runbook_outputs():
    assert (
        scan_request.resolve_detailed_catalog_flag(
            detailed_catalog=False,
            runbook_output="runbook.md",
            runbook_csv_output=None,
        )
        is True
    )
    assert (
        scan_request.resolve_detailed_catalog_flag(
            detailed_catalog=False,
            runbook_output=None,
            runbook_csv_output="runbook.csv",
        )
        is True
    )


def test_resolve_detailed_catalog_flag_preserves_explicit_flag_without_runbooks():
    assert (
        scan_request.resolve_detailed_catalog_flag(
            detailed_catalog=True,
            runbook_output=None,
            runbook_csv_output=None,
        )
        is True
    )
    assert (
        scan_request.resolve_detailed_catalog_flag(
            detailed_catalog=False,
            runbook_output=None,
            runbook_csv_output=None,
        )
        is False
    )


def test_build_run_scan_options_shapes_expected_option_map():
    options = scan_request.build_run_scan_options(
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


def test_scanner_wrapper_build_run_scan_options_matches_scan_request_helper():
    wrapped = scanner._build_run_scan_options(
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
    direct = scan_request.build_run_scan_options(
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

    assert wrapped == direct


def test_scanner_wrapper_resolve_detailed_catalog_flag_matches_scan_request_helper():
    wrapped = scanner._resolve_detailed_catalog_flag(
        detailed_catalog=False,
        runbook_output="runbook.md",
        runbook_csv_output=None,
    )
    direct = scan_request.resolve_detailed_catalog_flag(
        detailed_catalog=False,
        runbook_output="runbook.md",
        runbook_csv_output=None,
    )

    assert wrapped is True
    assert wrapped == direct
