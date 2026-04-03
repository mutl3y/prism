from prism import scanner
from prism.scanner_core import scan_request


def test_execute_scan_with_context_does_not_set_fallback_reason_when_context_path_used(
    monkeypatch, tmp_path
):
    role_path = str(tmp_path / "demo_role")
    (tmp_path / "demo_role").mkdir()
    scan_options = scan_request.build_run_scan_options_canonical(
        role_path=role_path,
        role_name_override=None,
        readme_config_path=None,
        include_vars_main=True,
        exclude_path_patterns=None,
        detailed_catalog=False,
        include_task_parameters=True,
        include_task_runbooks=True,
        inline_task_runbooks=False,
        include_collection_checks=True,
        keep_unknown_style_sections=False,
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
    captured = {}

    def fake_build_emit_args(**kwargs):
        captured["payload"] = kwargs["payload"]
        return {"emit_args": True}

    monkeypatch.setattr(scanner, "_build_emit_scan_outputs_args", fake_build_emit_args)
    monkeypatch.setattr(scanner, "_emit_scan_outputs", lambda args: "rendered")

    result = scanner._execute_scan_with_context(
        role_path=role_path,
        scan_options=scan_options,
        output="README.md",
        output_format="md",
        concise_readme=False,
        scanner_report_output=None,
        include_scanner_report_link=True,
        template=None,
        dry_run=False,
        runbook_output=None,
        runbook_csv_output=None,
    )

    assert result == "rendered"
    assert set(captured["payload"]) == {
        "role_name",
        "description",
        "display_variables",
        "requirements_display",
        "undocumented_default_filters",
        "metadata",
    }
    assert "scanner_context_fallback_reason" not in captured["payload"]["metadata"]


def test_execute_scan_with_context_emitted_args_keep_canonical_keyset_across_paths(
    monkeypatch, tmp_path
):
    role_path = str(tmp_path / "role")
    (tmp_path / "role").mkdir()

    canonical_keys: set[str] | None = None
    captured_keys: list[set[str]] = []

    def fake_emit(args):
        nonlocal canonical_keys
        current_keys = set(args.keys())
        captured_keys.append(current_keys)
        if canonical_keys is None:
            canonical_keys = current_keys
        else:
            assert current_keys == canonical_keys
        return "rendered"

    monkeypatch.setattr(scanner, "_emit_scan_outputs", fake_emit)

    context_scan_options = scan_request.build_run_scan_options_canonical(
        role_path=role_path,
        role_name_override=None,
        readme_config_path=None,
        include_vars_main=True,
        exclude_path_patterns=None,
        detailed_catalog=False,
        include_task_parameters=True,
        include_task_runbooks=True,
        inline_task_runbooks=False,
        include_collection_checks=True,
        keep_unknown_style_sections=False,
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
    result_context = scanner._execute_scan_with_context(
        role_path=role_path,
        scan_options=context_scan_options,
        output="README.md",
        output_format="md",
        concise_readme=False,
        scanner_report_output=None,
        include_scanner_report_link=True,
        template=None,
        dry_run=False,
        runbook_output=None,
        runbook_csv_output=None,
    )

    second_scan_options = scan_request.build_run_scan_options_canonical(
        role_path=role_path,
        role_name_override="role_override",
        readme_config_path=None,
        include_vars_main=True,
        exclude_path_patterns=None,
        detailed_catalog=False,
        include_task_parameters=True,
        include_task_runbooks=True,
        inline_task_runbooks=False,
        include_collection_checks=True,
        keep_unknown_style_sections=False,
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

    result_second = scanner._execute_scan_with_context(
        role_path=role_path,
        scan_options=second_scan_options,
        output="README.md",
        output_format="md",
        concise_readme=False,
        scanner_report_output=None,
        include_scanner_report_link=True,
        template=None,
        dry_run=False,
        runbook_output=None,
        runbook_csv_output=None,
    )

    assert result_context == "rendered"
    assert result_second == "rendered"
    assert len(captured_keys) == 2
    assert captured_keys[0] == captured_keys[1]
