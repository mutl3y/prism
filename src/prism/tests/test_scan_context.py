"""Focused tests for scan-context and output-payload shaping helpers."""

from functools import partial
from typing import get_type_hints

from prism import scanner
from prism.scanner_core import ScanContextBuilder
from prism.scanner_data import contracts


def test_finalize_scan_context_payload_shapes_expected_tuple():
    payload = scanner._finalize_scan_context_payload(
        rp="/tmp/role",
        role_name="demo_role",
        description="demo",
        requirements_display=["dep"],
        undocumented_default_filters=[{"file": "tasks/main.yml"}],
        display_variables={"name": {"required": False}},
        metadata={"features": {"tasks_scanned": 1}},
    )

    assert payload[0] == "/tmp/role"
    assert payload[1] == "demo_role"
    assert payload[2] == "demo"
    assert payload[3] == ["dep"]
    assert payload[4] == [{"file": "tasks/main.yml"}]
    assert payload[5]["display_variables"] == {"name": {"required": False}}
    assert payload[5]["metadata"] == {"features": {"tasks_scanned": 1}}


def test_build_scan_output_payload_shapes_expected_map():
    payload = scanner._build_scan_output_payload(
        role_name="demo_role",
        description="demo",
        display_variables={"name": {"required": False}},
        requirements_display=["dep"],
        undocumented_default_filters=[{"file": "tasks/main.yml"}],
        metadata={"features": {"tasks_scanned": 1}},
    )

    assert payload == {
        "role_name": "demo_role",
        "description": "demo",
        "display_variables": {"name": {"required": False}},
        "requirements_display": ["dep"],
        "undocumented_default_filters": [{"file": "tasks/main.yml"}],
        "metadata": {"features": {"tasks_scanned": 1}},
    }


def test_prepare_run_scan_payload_maps_prepared_context(monkeypatch):
    prepared_context = (
        "/tmp/role",
        "demo_role",
        "demo",
        ["dep"],
        [{"file": "tasks/main.yml"}],
        {
            "display_variables": {"name": {"required": False}},
            "metadata": {"features": {"tasks_scanned": 1}},
        },
    )
    monkeypatch.setattr(
        scanner, "_prepare_scan_context", lambda _scan_options: prepared_context
    )

    payload = scanner._prepare_run_scan_payload({"role_path": "/tmp/role"})

    assert payload == {
        "role_name": "demo_role",
        "description": "demo",
        "requirements_display": ["dep"],
        "undocumented_default_filters": [{"file": "tasks/main.yml"}],
        "display_variables": {"name": {"required": False}},
        "metadata": {"features": {"tasks_scanned": 1}},
    }


def test_scan_context_builder_is_importable_from_scanner_core() -> None:
    assert ScanContextBuilder is not None


def _resolve_callable(helper):
    return helper.func if isinstance(helper, partial) else helper


def test_prepare_scan_context_routes_to_scan_runtime_builder():
    helper = _resolve_callable(scanner._prepare_scan_context)
    assert callable(helper)
    assert helper.__module__ == "prism.scanner_core.scan_runtime"


def test_scanner_variable_insight_collection_helper_is_flattened_partial_alias():
    helper = scanner._collect_variable_insights_and_default_filter_findings
    assert isinstance(helper, partial)
    assert (
        helper.func
        is scanner._variable_insights.collect_variable_insights_and_default_filter_findings
    )
    assert helper.keywords["build_variable_insights"] is scanner.build_variable_insights
    assert (
        helper.keywords["attach_external_vars_context"]
        is scanner._attach_external_vars_context
    )
    assert (
        helper.keywords["collect_yaml_parse_failures"]
        is scanner._collect_yaml_parse_failures
    )


def test_scanner_build_variable_insights_is_flattened_partial_alias():
    helper = scanner.build_variable_insights
    assert callable(helper)


def test_scanner_runtime_policy_helpers_are_flattened_partial_aliases():
    unconstrained = scanner._apply_unconstrained_dynamic_include_policy
    yaml_like = scanner._apply_yaml_like_task_annotation_policy

    assert callable(unconstrained)
    assert callable(yaml_like)
    assert (
        _resolve_callable(unconstrained).__module__ == "prism.scanner_core.scan_runtime"
    )
    assert _resolve_callable(yaml_like).__module__ == "prism.scanner_core.scan_runtime"


def test_scanner_runtime_context_helpers_are_flattened_partial_aliases():
    prepare_scan_context = scanner._prepare_scan_context
    collect_scan_base_context = scanner._collect_scan_base_context
    collect_scan_identity_and_artifacts = scanner._collect_scan_identity_and_artifacts
    apply_scan_metadata_configuration = scanner._apply_scan_metadata_configuration
    enrich_scan_context_with_insights = scanner._enrich_scan_context_with_insights

    helpers = [
        prepare_scan_context,
        collect_scan_base_context,
        collect_scan_identity_and_artifacts,
        apply_scan_metadata_configuration,
        enrich_scan_context_with_insights,
    ]

    assert all(callable(helper) for helper in helpers)
    assert all(
        _resolve_callable(helper).__module__ == "prism.scanner_core.scan_runtime"
        for helper in helpers
    )


def test_scanner_output_helpers_route_through_runtime_and_canonical_emission():
    assert callable(scanner._emit_scan_outputs)
    assert (
        scanner._scan_output_emit_scan_outputs.__module__
        == "prism.scanner_io.scan_output_emission"
    )


def test_scanner_facade_style_and_runbook_symbols_remain_import_compatible():
    assert callable(scanner.render_runbook)
    assert callable(scanner.render_runbook_csv)
    assert callable(scanner.parse_style_readme)
    assert callable(scanner.resolve_default_style_guide_source)


def test_scan_output_payload_typed_seam_contract_annotations():
    assert set(contracts.RunScanOutputPayload.__annotations__) == {
        "role_name",
        "description",
        "display_variables",
        "requirements_display",
        "undocumented_default_filters",
        "metadata",
    }

    build_hints = get_type_hints(scanner._build_scan_output_payload)
    prepare_hints = get_type_hints(scanner._prepare_run_scan_payload)

    assert build_hints["return"] is contracts.RunScanOutputPayload
    assert prepare_hints["return"] is contracts.RunScanOutputPayload


def test_scan_context_contracts_use_canonical_scanner_data_symbols():
    assert set(get_type_hints(contracts.ScanBaseContext).keys()) == {
        "rp",
        "role_name",
        "description",
        "marker_prefix",
        "variables",
        "found",
        "metadata",
        "requirements_display",
    }


def test_scanner_wrapper_finalize_scan_context_payload_matches_helper():
    wrapped = scanner._finalize_scan_context_payload(
        rp="/tmp/role",
        role_name="demo_role",
        description="demo",
        requirements_display=["dep"],
        undocumented_default_filters=[{"file": "tasks/main.yml"}],
        display_variables={"name": {"required": False}},
        metadata={"features": {"tasks_scanned": 1}},
    )
    assert wrapped == (
        "/tmp/role",
        "demo_role",
        "demo",
        ["dep"],
        [{"file": "tasks/main.yml"}],
        {
            "display_variables": {"name": {"required": False}},
            "metadata": {"features": {"tasks_scanned": 1}},
        },
    )


def test_scanner_wrapper_build_scan_output_payload_matches_helper():
    wrapped = scanner._build_scan_output_payload(
        role_name="demo_role",
        description="demo",
        display_variables={"name": {"required": False}},
        requirements_display=["dep"],
        undocumented_default_filters=[{"file": "tasks/main.yml"}],
        metadata={"features": {"tasks_scanned": 1}},
    )
    assert wrapped == {
        "role_name": "demo_role",
        "description": "demo",
        "display_variables": {"name": {"required": False}},
        "requirements_display": ["dep"],
        "undocumented_default_filters": [{"file": "tasks/main.yml"}],
        "metadata": {"features": {"tasks_scanned": 1}},
    }


def test_scanner_wrapper_prepare_run_scan_payload_delegates(monkeypatch):
    prepared_context = (
        "/tmp/role",
        "demo_role",
        "demo",
        ["dep"],
        [{"file": "tasks/main.yml"}],
        {
            "display_variables": {"name": {"required": False}},
            "metadata": {"features": {"tasks_scanned": 1}},
        },
    )
    monkeypatch.setattr(
        scanner, "_prepare_scan_context", lambda options: prepared_context
    )

    result = scanner._prepare_run_scan_payload({"role_path": "/tmp/role"})
    assert result == {
        "role_name": "demo_role",
        "description": "demo",
        "requirements_display": ["dep"],
        "undocumented_default_filters": [{"file": "tasks/main.yml"}],
        "display_variables": {"name": {"required": False}},
        "metadata": {"features": {"tasks_scanned": 1}},
    }


def test_emit_scan_outputs_args_typed_seam_contract_annotations():
    assert set(contracts.EmitScanOutputsArgs.__annotations__) == {
        "output",
        "output_format",
        "concise_readme",
        "scanner_report_output",
        "include_scanner_report_link",
        "role_name",
        "description",
        "display_variables",
        "requirements_display",
        "undocumented_default_filters",
        "metadata",
        "template",
        "dry_run",
        "runbook_output",
        "runbook_csv_output",
    }

    build_hints = get_type_hints(scanner._build_emit_scan_outputs_args)
    assert build_hints["return"] is contracts.EmitScanOutputsArgs


def test_build_emit_scan_outputs_args_flattens_payload_fields():
    payload = {
        "role_name": "my_role",
        "description": "desc",
        "display_variables": {"v": {"required": True}},
        "requirements_display": ["req"],
        "undocumented_default_filters": [{"file": "tasks/main.yml"}],
        "metadata": {"features": {"tasks_scanned": 2}},
    }
    args = scanner._build_emit_scan_outputs_args(
        output="README.md",
        output_format="md",
        concise_readme=False,
        scanner_report_output=None,
        include_scanner_report_link=True,
        payload=payload,
        template=None,
        dry_run=False,
        runbook_output=None,
        runbook_csv_output=None,
    )

    assert args["output"] == "README.md"
    assert args["output_format"] == "md"
    assert args["concise_readme"] is False
    assert args["scanner_report_output"] is None
    assert args["include_scanner_report_link"] is True
    assert args["role_name"] == "my_role"
    assert args["description"] == "desc"
    assert args["display_variables"] == {"v": {"required": True}}
    assert args["requirements_display"] == ["req"]
    assert args["undocumented_default_filters"] == [{"file": "tasks/main.yml"}]
    assert args["metadata"] == {"features": {"tasks_scanned": 2}}
    assert args["template"] is None
    assert args["dry_run"] is False
    assert args["runbook_output"] is None
    assert args["runbook_csv_output"] is None


def test_scanner_wrapper_build_emit_scan_outputs_args_shapes_expected_map():
    payload = {
        "role_name": "wrap_role",
        "description": "wrap_desc",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
    }
    result = scanner._build_emit_scan_outputs_args(
        output="README.md",
        output_format="md",
        concise_readme=False,
        scanner_report_output=None,
        include_scanner_report_link=True,
        payload=payload,
        template=None,
        dry_run=True,
        runbook_output=None,
        runbook_csv_output=None,
    )

    assert result["output"] == "README.md"
    assert result["role_name"] == "wrap_role"
    assert result["dry_run"] is True


def test_scan_report_sidecar_args_typed_seam_contract_annotations():
    assert set(contracts.ScanReportSidecarArgs.__annotations__) == {
        "concise_readme",
        "scanner_report_output",
        "out_path",
        "include_scanner_report_link",
        "role_name",
        "description",
        "display_variables",
        "requirements_display",
        "undocumented_default_filters",
        "metadata",
        "dry_run",
    }

    build_hints = get_type_hints(scanner._build_scan_report_sidecar_args)
    assert build_hints["return"] is contracts.ScanReportSidecarArgs


def test_build_scan_report_sidecar_args_flattens_payload_fields():
    from pathlib import Path

    payload = {
        "role_name": "my_role",
        "description": "desc",
        "display_variables": {"v": {"required": True}},
        "requirements_display": ["req"],
        "undocumented_default_filters": [{"file": "tasks/main.yml"}],
        "metadata": {"features": {"tasks_scanned": 2}},
    }
    out_path = Path("/tmp/docs/README.md")

    args = scanner._build_scan_report_sidecar_args(
        concise_readme=True,
        scanner_report_output=None,
        out_path=out_path,
        include_scanner_report_link=False,
        payload=payload,
        dry_run=True,
    )

    assert args["concise_readme"] is True
    assert args["scanner_report_output"] is None
    assert args["out_path"] is out_path
    assert args["include_scanner_report_link"] is False
    assert args["role_name"] == "my_role"
    assert args["description"] == "desc"
    assert args["display_variables"] == {"v": {"required": True}}
    assert args["requirements_display"] == ["req"]
    assert args["undocumented_default_filters"] == [{"file": "tasks/main.yml"}]
    assert args["metadata"] == {"features": {"tasks_scanned": 2}}
    assert args["dry_run"] is True


def test_scanner_wrapper_build_scan_report_sidecar_args_shapes_expected_map():
    from pathlib import Path

    payload = {
        "role_name": "wrap_role",
        "description": "wrap_desc",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
    }
    out_path = Path("/tmp/README.md")
    result = scanner._build_scan_report_sidecar_args(
        concise_readme=True,
        scanner_report_output=None,
        out_path=out_path,
        include_scanner_report_link=False,
        payload=payload,
        dry_run=True,
    )

    assert result["concise_readme"] is True
    assert result["out_path"] is out_path
    assert result["role_name"] == "wrap_role"
    assert result["dry_run"] is True


def test_runbook_sidecar_args_typed_seam_contract_annotations():
    """Verify RunbookSidecarArgs TypedDict annotations match build_runbook_sidecar_args return."""
    from typing import get_type_hints

    assert set(contracts.RunbookSidecarArgs.__annotations__) == {
        "runbook_output",
        "runbook_csv_output",
        "role_name",
        "metadata",
    }

    build_hints = get_type_hints(scanner._build_runbook_sidecar_args)
    assert build_hints["return"] is contracts.RunbookSidecarArgs


def test_build_runbook_sidecar_args_from_payload():
    payload = {
        "role_name": "runbook_role",
        "description": "runbook_desc",
        "display_variables": {"x": 1},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {"key": "val"},
    }
    args = scanner._build_runbook_sidecar_args(
        runbook_output="/tmp/runbook.md",
        runbook_csv_output="/tmp/runbook.csv",
        payload=payload,
    )
    assert args["runbook_output"] == "/tmp/runbook.md"
    assert args["runbook_csv_output"] == "/tmp/runbook.csv"
    assert args["role_name"] == "runbook_role"
    assert args["metadata"] == {"key": "val"}


def test_build_runbook_sidecar_args_none_paths():
    payload = {
        "role_name": "r",
        "description": "d",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
    }
    args = scanner._build_runbook_sidecar_args(
        runbook_output=None,
        runbook_csv_output=None,
        payload=payload,
    )
    assert args["runbook_output"] is None
    assert args["runbook_csv_output"] is None


def test_scanner_wrapper_build_runbook_sidecar_args_shapes_expected_map():
    payload = {
        "role_name": "wrap_r",
        "description": "wrap_d",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
    }
    result = scanner._build_runbook_sidecar_args(
        runbook_output="/out/runbook.md",
        runbook_csv_output=None,
        payload=payload,
    )

    assert result["runbook_output"] == "/out/runbook.md"
    assert result["runbook_csv_output"] is None
    assert result["role_name"] == "wrap_r"
    assert result["metadata"] == {}


def test_scanner_runtime_output_helpers_alias_scan_runtime_canonical_functions():
    assert (
        scanner._finalize_scan_context_payload
        is scanner._scan_runtime.finalize_scan_context_payload
    )
    assert (
        scanner._build_scan_output_payload
        is scanner._scan_runtime.build_scan_output_payload
    )
    assert (
        scanner._build_emit_scan_outputs_args
        is scanner._scan_runtime.build_emit_scan_outputs_args
    )
    assert (
        scanner._build_scan_report_sidecar_args
        is scanner._scan_runtime.build_scan_report_sidecar_args
    )
    assert (
        scanner._build_runbook_sidecar_args
        is scanner._scan_runtime.build_runbook_sidecar_args
    )


def test_scan_base_context_typed_seam_keys():
    """ScanBaseContext TypedDict must expose all expected base-context fields."""
    from typing import get_type_hints

    hints = get_type_hints(contracts.ScanBaseContext)
    expected_keys = {
        "rp",
        "role_name",
        "description",
        "marker_prefix",
        "variables",
        "found",
        "metadata",
        "requirements_display",
    }
    assert expected_keys == set(hints.keys())


def test_execute_scan_with_context_invokes_scanner_context_once(monkeypatch, tmp_path):
    role_path = str(tmp_path / "role")
    (tmp_path / "role").mkdir()
    scan_options = {"role_path": role_path, "include_vars_main": True}
    context_payload = {
        "role_name": "demo_role",
        "description": "desc",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
    }

    calls = {
        "orchestrate": 0,
        "build_emit_args": 0,
        "emit": 0,
    }

    class FakeContext:
        def __init__(self, *, di, role_path, scan_options, **_kwargs):
            assert role_path == role_path_ref
            assert scan_options is scan_options_ref

        def orchestrate_scan(self):
            calls["orchestrate"] += 1
            return context_payload

    scan_options_ref = scan_options
    role_path_ref = role_path

    def fake_build_emit_args(**kwargs):
        calls["build_emit_args"] += 1
        assert kwargs["payload"] is context_payload
        return {"emit_args": True, "payload": kwargs["payload"]}

    def fake_emit(args):
        calls["emit"] += 1
        assert args["emit_args"] is True
        return "rendered"

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("_prepare_run_scan_payload should not be called")

    monkeypatch.setattr(
        scanner, "DIContainer", lambda role_path, scan_options: object()
    )
    monkeypatch.setattr(scanner, "ScannerContext", FakeContext)
    monkeypatch.setattr(scanner, "_build_emit_scan_outputs_args", fake_build_emit_args)
    monkeypatch.setattr(scanner, "_emit_scan_outputs", fake_emit)
    monkeypatch.setattr(scanner, "_prepare_run_scan_payload", fail_if_called)

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
    assert calls == {
        "orchestrate": 1,
        "build_emit_args": 1,
        "emit": 1,
    }


def test_execute_scan_with_context_does_not_fall_back_for_orchestrated_payload_shape(
    monkeypatch, tmp_path
):
    role_path = str(tmp_path / "role")
    (tmp_path / "role").mkdir()
    scan_options = {"role_path": role_path, "include_vars_main": True}

    class FakeContext:
        def __init__(self, *, di, role_path, scan_options, **_kwargs):
            pass

        def orchestrate_scan(self):
            return {
                "role_name": "",
                "description": "",
                "display_variables": {},
                "requirements_display": [],
                "undocumented_default_filters": [],
                "metadata": {},
            }

    captured = {}

    def fail_if_prepare_called(*_args, **_kwargs):
        raise AssertionError("_prepare_run_scan_payload should not be called")

    def fake_build_emit_args(**kwargs):
        captured["payload"] = kwargs["payload"]
        return {"emit_args": True}

    monkeypatch.setattr(
        scanner, "DIContainer", lambda role_path, scan_options: object()
    )
    monkeypatch.setattr(scanner, "ScannerContext", FakeContext)
    monkeypatch.setattr(scanner, "_prepare_run_scan_payload", fail_if_prepare_called)
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
    assert captured["payload"] == {
        "role_name": "",
        "description": "",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
    }
    assert "scanner_context_fallback_reason" not in captured["payload"]["metadata"]


def test_execute_scan_with_context_normalized_options_do_not_emit_runtime_fallback_reason(
    monkeypatch, tmp_path
):
    role_path = str(tmp_path / "role")
    (tmp_path / "role").mkdir()
    scan_options = scanner._build_run_scan_options(
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

    class FakeContext:
        def __init__(self, *, di, role_path, scan_options, **_kwargs):
            pass

        def orchestrate_scan(self):
            return {
                "role_name": "",
                "description": "",
                "display_variables": {},
                "requirements_display": [],
                "undocumented_default_filters": [],
                "metadata": {},
            }

    def fail_if_prepare_called(*_args, **_kwargs):
        raise AssertionError("_prepare_run_scan_payload should not be called")

    monkeypatch.setattr(
        scanner, "DIContainer", lambda role_path, scan_options: object()
    )
    monkeypatch.setattr(scanner, "ScannerContext", FakeContext)
    monkeypatch.setattr(scanner, "_prepare_run_scan_payload", fail_if_prepare_called)
    monkeypatch.setattr(
        scanner,
        "_build_emit_scan_outputs_args",
        lambda **kwargs: {"ok": captured.setdefault("payload", kwargs["payload"])},
    )
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
    assert captured["payload"] == {
        "role_name": "",
        "description": "",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
    }
    assert "scanner_context_fallback_reason" not in captured["payload"]["metadata"]
    assert not hasattr(scanner, "_resolve_run_scan_payload_fallback_reason")


def test_execute_scan_with_context_uses_real_scanner_context_without_fallback(
    monkeypatch, tmp_path
):
    role_path = str(tmp_path / "demo_role")
    (tmp_path / "demo_role").mkdir()
    scan_options = scanner._build_run_scan_options(
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

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("_prepare_run_scan_payload should not be called")

    def fake_build_emit_args(**kwargs):
        captured["payload"] = kwargs["payload"]
        return {"emit_args": True}

    monkeypatch.setattr(scanner, "_prepare_run_scan_payload", fail_if_called)
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
    assert captured["payload"]["role_name"]
    assert captured["payload"]["role_name"] == "demo_role"


def test_execute_scan_with_context_uses_scanner_context_when_vars_seed_paths_present(
    monkeypatch, tmp_path
):
    role_path = str(tmp_path / "role")
    (tmp_path / "role").mkdir()
    scan_options = {
        "role_path": role_path,
        "include_vars_main": True,
        "vars_seed_paths": ["/tmp/group_vars/all.yml"],
    }
    captured = {}

    def fake_build_emit_args(**kwargs):
        captured["payload"] = kwargs["payload"]
        return {"emit_args": True}

    def fail_if_prepare_called(*_args, **_kwargs):
        raise AssertionError("_prepare_run_scan_payload should not be called")

    class FakeContext:
        def __init__(self, *, di, role_path, scan_options, **_kwargs):
            captured["scan_options"] = scan_options

        def orchestrate_scan(self):
            return {
                "role_name": "context_role",
                "description": "context_desc",
                "display_variables": {},
                "requirements_display": [],
                "undocumented_default_filters": [],
                "metadata": {},
            }

    monkeypatch.setattr(
        scanner, "DIContainer", lambda role_path, scan_options: object()
    )
    monkeypatch.setattr(scanner, "ScannerContext", FakeContext)
    monkeypatch.setattr(scanner, "_prepare_run_scan_payload", fail_if_prepare_called)
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
    assert captured["scan_options"] is scan_options
    assert captured["payload"]["role_name"] == "context_role"
    assert "scanner_context_fallback_reason" not in captured["payload"]["metadata"]


def test_execute_scan_with_context_uses_scanner_context_when_style_readme_path_missing(
    monkeypatch,
    tmp_path,
):
    role_path = str(tmp_path / "role")
    (tmp_path / "role").mkdir()
    scan_options = {
        "role_path": role_path,
        "include_vars_main": True,
        "style_readme_path": str(tmp_path / "missing-style.md"),
    }
    captured = {}

    def fake_build_emit_args(**kwargs):
        captured["payload"] = kwargs["payload"]
        return {"emit_args": True}

    def fail_if_prepare_called(*_args, **_kwargs):
        raise AssertionError("_prepare_run_scan_payload should not be called")

    class FakeContext:
        def __init__(self, *, di, role_path, scan_options, **_kwargs):
            captured["scan_options"] = scan_options

        def orchestrate_scan(self):
            return {
                "role_name": "context_role",
                "description": "context_desc",
                "display_variables": {},
                "requirements_display": [],
                "undocumented_default_filters": [],
                "metadata": {},
            }

    monkeypatch.setattr(
        scanner, "DIContainer", lambda role_path, scan_options: object()
    )
    monkeypatch.setattr(scanner, "ScannerContext", FakeContext)
    monkeypatch.setattr(scanner, "_prepare_run_scan_payload", fail_if_prepare_called)
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
    assert captured["scan_options"] is scan_options
    assert captured["payload"]["role_name"] == "context_role"
    assert "scanner_context_fallback_reason" not in captured["payload"]["metadata"]


def test_execute_scan_with_context_uses_scanner_context_when_compare_role_path_missing(
    monkeypatch,
    tmp_path,
):
    role_path = str(tmp_path / "role")
    (tmp_path / "role").mkdir()
    scan_options = {
        "role_path": role_path,
        "include_vars_main": True,
        "compare_role_path": str(tmp_path / "missing-compare-role"),
    }
    captured = {}

    def fake_build_emit_args(**kwargs):
        captured["payload"] = kwargs["payload"]
        return {"emit_args": True}

    def fail_if_prepare_called(*_args, **_kwargs):
        raise AssertionError("_prepare_run_scan_payload should not be called")

    class FakeContext:
        def __init__(self, *, di, role_path, scan_options, **_kwargs):
            captured["scan_options"] = scan_options

        def orchestrate_scan(self):
            return {
                "role_name": "context_role",
                "description": "context_desc",
                "display_variables": {},
                "requirements_display": [],
                "undocumented_default_filters": [],
                "metadata": {},
            }

    monkeypatch.setattr(
        scanner, "DIContainer", lambda role_path, scan_options: object()
    )
    monkeypatch.setattr(scanner, "ScannerContext", FakeContext)
    monkeypatch.setattr(scanner, "_prepare_run_scan_payload", fail_if_prepare_called)
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
    assert captured["scan_options"] is scan_options
    assert captured["payload"]["role_name"] == "context_role"
    assert "scanner_context_fallback_reason" not in captured["payload"]["metadata"]


def test_execute_scan_with_context_uses_scanner_context_when_role_name_override_present(
    monkeypatch,
    tmp_path,
):
    role_path = str(tmp_path / "role")
    (tmp_path / "role").mkdir()
    scan_options = {
        "role_path": role_path,
        "include_vars_main": True,
        "role_name_override": "override_name",
    }
    captured = {}

    def fake_build_emit_args(**kwargs):
        captured["payload"] = kwargs["payload"]
        return {"emit_args": True}

    def fail_if_prepare_called(*_args, **_kwargs):
        raise AssertionError("_prepare_run_scan_payload should not be called")

    class FakeContext:
        def __init__(self, *, di, role_path, scan_options, **_kwargs):
            captured["scan_options"] = scan_options

        def orchestrate_scan(self):
            return {
                "role_name": "override_name",
                "description": "context_desc",
                "display_variables": {},
                "requirements_display": [],
                "undocumented_default_filters": [],
                "metadata": {},
            }

    monkeypatch.setattr(
        scanner, "DIContainer", lambda role_path, scan_options: object()
    )
    monkeypatch.setattr(scanner, "ScannerContext", FakeContext)
    monkeypatch.setattr(scanner, "_prepare_run_scan_payload", fail_if_prepare_called)
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
    assert captured["scan_options"] is scan_options
    assert captured["payload"]["role_name"] == "override_name"
    assert "scanner_context_fallback_reason" not in captured["payload"]["metadata"]


def test_execute_scan_with_context_does_not_set_fallback_reason_when_context_path_used(
    monkeypatch, tmp_path
):
    role_path = str(tmp_path / "demo_role")
    (tmp_path / "demo_role").mkdir()
    scan_options = scanner._build_run_scan_options(
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

    context_scan_options = scanner._build_run_scan_options(
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

    second_scan_options = scanner._build_run_scan_options(
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
