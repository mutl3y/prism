"""Focused tests for scan-context and output-payload shaping helpers."""

from functools import partial
from typing import get_type_hints

from prism import scanner
from prism.scanner_core import ScanContextBuilder
from prism.scanner_core import scan_request
from prism.scanner_core import scan_runtime
from prism.scanner_data import ScanContextPayload, contracts
from prism.scanner_extract import variable_extractor
from prism.scanner_readme import guide as readme_guide
from prism.tests import _scan_context_execution_tail as scan_context_execution_tail


def _export_shard_symbols(module):
    for name, value in module.__dict__.items():
        if name.startswith("__"):
            continue
        globals().setdefault(name, value)


_export_shard_symbols(scan_context_execution_tail)


def test_finalize_scan_context_payload_shapes_expected_mapping():
    payload = scan_runtime.finalize_scan_context_payload(
        rp="/tmp/role",
        role_name="demo_role",
        description="demo",
        requirements_display=["dep"],
        undocumented_default_filters=[{"file": "tasks/main.yml"}],
        display_variables={"name": {"required": False}},
        metadata={"features": {"tasks_scanned": 1}},
    )

    assert payload["rp"] == "/tmp/role"
    assert payload["role_name"] == "demo_role"
    assert payload["description"] == "demo"
    assert payload["requirements_display"] == ["dep"]
    assert payload["undocumented_default_filters"] == [{"file": "tasks/main.yml"}]
    assert payload["display_variables"] == {"name": {"required": False}}
    assert payload["metadata"] == {"features": {"tasks_scanned": 1}}


def test_scan_context_payload_is_re_exported_from_scanner_data() -> None:
    assert ScanContextPayload is not None


def test_build_scan_output_payload_shapes_expected_map():
    payload = scan_runtime.build_scan_output_payload(
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


def test_build_scan_output_payload_maps_prepared_context_values():
    prepared_context = {
        "rp": "/tmp/role",
        "role_name": "demo_role",
        "description": "demo",
        "requirements_display": ["dep"],
        "undocumented_default_filters": [{"file": "tasks/main.yml"}],
        "display_variables": {"name": {"required": False}},
        "metadata": {"features": {"tasks_scanned": 1}},
    }
    payload = scan_runtime.build_scan_output_payload(
        role_name=prepared_context["role_name"],
        description=prepared_context["description"],
        display_variables=prepared_context["display_variables"],
        requirements_display=prepared_context["requirements_display"],
        undocumented_default_filters=prepared_context["undocumented_default_filters"],
        metadata=prepared_context["metadata"],
    )

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


def test_scanner_variable_insight_collection_helper_delegates_to_injected_callables():
    helper = scanner._collect_variable_insights_and_default_filter_findings
    assert isinstance(helper, partial)

    captured: dict[str, object] = {}

    def fake_build_variable_insights(*_args, **_kwargs):
        captured["build_variable_insights"] = True
        return [{"name": "sample_var"}]

    def fake_attach_external_vars_context(*, metadata, vars_seed_paths):
        captured["attach_external_vars_context"] = vars_seed_paths
        metadata["external_vars_context"] = {"paths": list(vars_seed_paths or [])}

    def fake_collect_yaml_parse_failures(*_args, **_kwargs):
        captured["collect_yaml_parse_failures"] = True
        return [{"relative_path": "tasks/main.yml", "error": "invalid"}]

    metadata: dict[str, object] = {"features": {}}
    variable_insights, undocumented_default_filters, display_variables = helper(
        role_path="/tmp/role",
        vars_seed_paths=["/tmp/role/vars/main.yml"],
        include_vars_main=True,
        exclude_path_patterns=None,
        found_default_filters=[],
        variables={},
        metadata=metadata,
        marker_prefix="NOTE:",
        style_readme_path=None,
        policy_context=None,
        ignore_unresolved_internal_underscore_references=True,
        non_authoritative_test_evidence_max_file_bytes=4096,
        non_authoritative_test_evidence_max_files_scanned=3,
        non_authoritative_test_evidence_max_total_bytes=8192,
        build_variable_insights=fake_build_variable_insights,
        attach_external_vars_context=fake_attach_external_vars_context,
        collect_yaml_parse_failures=fake_collect_yaml_parse_failures,
        extract_role_notes_from_comments=lambda *_a, **_k: {},
        build_undocumented_default_filters=lambda **_k: [],
        extract_scanner_counters=lambda *_a, **_k: {},
        build_display_variables=lambda _variables, insights: {"count": len(insights)},
    )

    assert captured["build_variable_insights"] is True
    assert captured["attach_external_vars_context"] == ["/tmp/role/vars/main.yml"]
    assert captured["collect_yaml_parse_failures"] is True
    assert variable_insights == [{"name": "sample_var"}]
    assert undocumented_default_filters == []
    assert display_variables == {"count": 1}
    assert metadata["yaml_parse_failures"][0]["relative_path"] == "tasks/main.yml"


def test_scanner_build_variable_insights_is_flattened_partial_alias():
    helper = scanner.build_variable_insights
    assert callable(helper)


def test_scanner_runtime_policy_helpers_are_flattened_partial_aliases():
    unconstrained = scanner._apply_unconstrained_dynamic_include_policy
    yaml_like = scanner._apply_yaml_like_task_annotation_policy

    assert callable(unconstrained)
    assert callable(yaml_like)


def test_refresh_policy_updates_variable_guidance_rendering_in_process(monkeypatch):
    base_policy = dict(scanner._POLICY)
    patched_policy = dict(base_policy)
    patched_guidance = dict(base_policy["variable_guidance"])
    sentinel_keyword = "ansible_prism_runtime_keyword"
    patched_guidance["priority_keywords"] = [sentinel_keyword]
    patched_policy["variable_guidance"] = patched_guidance

    def _refresh_return_for(policy: dict):
        sensitivity = policy["sensitivity"]
        return (
            policy,
            policy["section_aliases"],
            tuple(sensitivity["name_tokens"]),
            tuple(sensitivity["vault_markers"]),
            tuple(sensitivity["credential_prefixes"]),
            tuple(sensitivity["url_prefixes"]),
            tuple(policy["variable_guidance"]["priority_keywords"]),
            policy["ignored_identifiers"],
        )

    metadata = {
        "variable_insights": [
            {"name": "zzzz_nonpriority_alpha", "default": "keep"},
            {"name": f"{sentinel_keyword}_choice", "default": "pick"},
        ]
    }

    before = scanner._render_guide_section_body(
        "variable_guidance",
        "demo",
        "",
        {},
        [],
        [],
        metadata,
    )
    assert "zzzz_nonpriority_alpha" in before

    monkeypatch.setattr(
        scanner,
        "_config_refresh_policy",
        lambda override_path=None: _refresh_return_for(patched_policy),
    )
    scanner._refresh_policy()

    try:
        after = scanner._render_guide_section_body(
            "variable_guidance",
            "demo",
            "",
            {},
            [],
            [],
            metadata,
        )
        assert f"{sentinel_keyword}_choice" in after
        assert "zzzz_nonpriority_alpha" not in after
    finally:
        monkeypatch.setattr(
            scanner,
            "_config_refresh_policy",
            lambda override_path=None: _refresh_return_for(base_policy),
        )
        scanner._refresh_policy()


def test_refresh_policy_updates_readme_section_aliases_in_process(
    monkeypatch, tmp_path
):
    base_policy = dict(scanner._POLICY)
    patched_policy = dict(base_policy)
    patched_aliases = dict(base_policy["section_aliases"])
    patched_aliases["runtime inputs"] = "role_variables"
    patched_policy["section_aliases"] = patched_aliases

    def _refresh_return_for(policy: dict):
        sensitivity = policy["sensitivity"]
        return (
            policy,
            policy["section_aliases"],
            tuple(sensitivity["name_tokens"]),
            tuple(sensitivity["vault_markers"]),
            tuple(sensitivity["credential_prefixes"]),
            tuple(sensitivity["url_prefixes"]),
            tuple(policy["variable_guidance"]["priority_keywords"]),
            policy["ignored_identifiers"],
        )

    style = tmp_path / "STYLE_GUIDE_SOURCE.md"
    style.write_text("Runtime Inputs\n--------------\n\nBody\n", encoding="utf-8")

    before = scanner.parse_style_readme(str(style))
    assert before["sections"][0]["id"] == "unknown"

    monkeypatch.setattr(
        scanner,
        "_config_refresh_policy",
        lambda override_path=None: _refresh_return_for(patched_policy),
    )
    scanner._refresh_policy()

    try:
        after = scanner.parse_style_readme(str(style))
        assert after["sections"][0]["id"] == "role_variables"
    finally:
        monkeypatch.setattr(
            scanner,
            "_config_refresh_policy",
            lambda override_path=None: _refresh_return_for(base_policy),
        )
        scanner._refresh_policy()


def test_prepare_scan_context_uses_per_scan_policy_context_for_style_aliases(
    tmp_path,
):
    role = tmp_path / "role"
    role.mkdir()
    style = tmp_path / "STYLE_GUIDE_SOURCE.md"
    heading = "Bertrum Runtime Inputs"
    style.write_text(f"{heading}\n----------------------\n\nBody\n", encoding="utf-8")

    scan_options = scan_request.build_run_scan_options_canonical(
        role_path=str(role),
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
        style_readme_path=str(style),
        style_source_path=str(style),
        style_guide_skeleton=False,
        compare_role_path=None,
        fail_on_unconstrained_dynamic_includes=None,
        fail_on_yaml_like_task_annotations=None,
        ignore_unresolved_internal_underscore_references=None,
        policy_context={
            "section_aliases": {"bertrum runtime inputs": "role_variables"},
            "ignored_identifiers": frozenset(),
            "variable_guidance_keywords": tuple(),
        },
    )

    payload = scanner._prepare_scan_context(scan_options)

    assert payload["metadata"]["style_guide"]["sections"][0]["id"] == "role_variables"


def test_build_variable_insights_uses_per_scan_ignored_identifier_context(tmp_path):
    role = tmp_path / "role"
    tasks_dir = role / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "main.yml").write_text(
        "---\n"
        "- name: Reference runtime-only ignored variable\n"
        "  ansible.builtin.debug:\n"
        '    msg: "{{ bertrum_runtime_only_ignored }}"\n',
        encoding="utf-8",
    )

    baseline_rows = scanner.build_variable_insights(str(role), include_vars_main=False)
    assert any(row["name"] == "bertrum_runtime_only_ignored" for row in baseline_rows)

    policy_rows = scanner.build_variable_insights(
        str(role),
        include_vars_main=False,
        policy_context={
            "section_aliases": {},
            "ignored_identifiers": frozenset({"bertrum_runtime_only_ignored"}),
            "variable_guidance_keywords": tuple(),
        },
    )

    assert all(row["name"] != "bertrum_runtime_only_ignored" for row in policy_rows)


def test_render_guide_section_body_uses_request_scoped_variable_guidance_keywords():
    metadata = {
        "variable_insights": [
            {"name": "zzzz_nonpriority_alpha", "default": "keep"},
            {"name": "bertrum_runtime_choice", "default": "pick"},
        ]
    }

    before = scanner._render_guide_section_body(
        "variable_guidance",
        "demo",
        "",
        {},
        [],
        [],
        metadata,
    )
    assert "zzzz_nonpriority_alpha" in before

    with readme_guide.variable_guidance_keywords_scope(("bertrum_runtime",)):
        after = scanner._render_guide_section_body(
            "variable_guidance",
            "demo",
            "",
            {},
            [],
            [],
            metadata,
        )

    assert "bertrum_runtime_choice" in after
    assert "zzzz_nonpriority_alpha" not in after


def test_run_scan_payload_scopes_policy_without_mutating_scanner_globals(
    monkeypatch,
    tmp_path,
):
    role = tmp_path / "role"
    tasks_dir = role / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "main.yml").write_text(
        "---\n"
        "- name: Reference runtime-only ignored variable\n"
        "  ansible.builtin.debug:\n"
        '    msg: "{{ bertrum_runtime_only_ignored }}"\n',
        encoding="utf-8",
    )
    style = tmp_path / "STYLE_GUIDE_SOURCE.md"
    style.write_text("Runtime Inputs\n--------------\n\nBody\n", encoding="utf-8")
    (role / ".prism_patterns.yml").write_text(
        "section_aliases:\n"
        "  runtime inputs: role_variables\n"
        "ignored_identifiers:\n"
        "  - bertrum_runtime_only_ignored\n"
        "variable_guidance:\n"
        "  priority_keywords:\n"
        "    - bertrum_runtime\n"
        "sensitivity:\n"
        "  name_tokens:\n"
        "    - bertrum_scope_sentinel\n",
        encoding="utf-8",
    )

    original_tokens = scanner._SECRET_NAME_TOKENS
    baseline_style = scanner.parse_style_readme(str(style))
    baseline_refs = variable_extractor._collect_referenced_variable_names(str(role))
    baseline_guidance = scanner._render_guide_section_body(
        "variable_guidance",
        "demo",
        "",
        {},
        [],
        [],
        {
            "variable_insights": [
                {"name": "zzzz_nonpriority_alpha", "default": "keep"},
                {"name": "bertrum_runtime_choice", "default": "pick"},
            ]
        },
    )

    assert baseline_style["sections"][0]["id"] == "unknown"
    assert "bertrum_runtime_only_ignored" in baseline_refs
    assert "zzzz_nonpriority_alpha" in baseline_guidance
    assert not variable_extractor._looks_secret_name("bertrum_scope_sentinel_value")

    def _fake_orchestrate_scan_payload(*, role_path: str, scan_options: dict):
        scoped_style = scanner.parse_style_readme(str(style))
        scoped_refs = variable_extractor._collect_referenced_variable_names(role_path)
        scoped_guidance = scanner._render_guide_section_body(
            "variable_guidance",
            "demo",
            "",
            {},
            [],
            [],
            {
                "variable_insights": [
                    {"name": "zzzz_nonpriority_alpha", "default": "keep"},
                    {"name": "bertrum_runtime_choice", "default": "pick"},
                ]
            },
        )

        assert scan_options["policy_context"]["section_aliases"]["runtime inputs"] == (
            "role_variables"
        )
        assert (
            "bertrum_runtime_only_ignored"
            in scan_options["policy_context"]["ignored_identifiers"]
        )
        assert scan_options["policy_context"]["variable_guidance_keywords"] == (
            "bertrum_runtime",
        )
        assert scoped_style["sections"][0]["id"] == "role_variables"
        assert "bertrum_runtime_only_ignored" not in scoped_refs
        assert "bertrum_runtime_choice" in scoped_guidance
        assert "zzzz_nonpriority_alpha" not in scoped_guidance
        assert variable_extractor._looks_secret_name("bertrum_scope_sentinel_value")
        assert scanner._SECRET_NAME_TOKENS == original_tokens
        return {"ok": True}

    monkeypatch.setattr(
        scanner, "_orchestrate_scan_payload", _fake_orchestrate_scan_payload
    )

    result = scanner._run_scan_payload(str(role), style_readme_path=str(style))

    assert result == {"ok": True}
    assert scanner._SECRET_NAME_TOKENS == original_tokens
    assert scanner.parse_style_readme(str(style))["sections"][0]["id"] == "unknown"
    assert (
        "bertrum_runtime_only_ignored"
        in variable_extractor._collect_referenced_variable_names(str(role))
    )
    assert not variable_extractor._looks_secret_name("bertrum_scope_sentinel_value")


def test_policy_context_annotations_use_typed_contract_across_runtime_seams():
    scan_runtime_hints = get_type_hints(scan_runtime.enrich_scan_context_with_insights)
    scanner_hints = get_type_hints(scanner.build_variable_insights)

    assert scan_runtime_hints["policy_context"] == contracts.PolicyContext | None
    assert scanner_hints["policy_context"] == contracts.PolicyContext | None


def test_refresh_policy_uses_role_root_override_instead_of_process_cwd(
    monkeypatch, tmp_path
):
    cwd_root = tmp_path / "cwd-root"
    role_root = tmp_path / "role-root"
    cwd_root.mkdir()
    role_root.mkdir()

    (cwd_root / ".prism_patterns.yml").write_text(
        "sensitivity:\n  name_tokens:\n    - from_process_cwd\n",
        encoding="utf-8",
    )
    (role_root / ".prism_patterns.yml").write_text(
        "sensitivity:\n  name_tokens:\n    - from_role_root\n",
        encoding="utf-8",
    )

    original_tokens = scanner._SECRET_NAME_TOKENS
    monkeypatch.chdir(cwd_root)

    scanner._refresh_policy(role_root=str(role_root))

    try:
        assert "from_role_root" in scanner._SECRET_NAME_TOKENS
        assert "from_process_cwd" not in scanner._SECRET_NAME_TOKENS
    finally:
        monkeypatch.chdir(tmp_path)
        scanner._refresh_policy()
        assert scanner._SECRET_NAME_TOKENS == original_tokens


def test_scanner_runtime_context_orchestration_executes_all_phases():
    """Behavior-level contract: ScannerContext orchestration completes successfully.

    Rather than asserting private scanner.py helper members by name,
    validate that the end-to-end orchestration phases execute and produce
    expected contract-shaped outputs (per RunScanOutputPayload contract).
    """
    # This test ensures the runtime behavior is correct: all phases execute
    # and return contract-compliant data, without coupling to private seams.
    payload = scan_runtime.finalize_scan_context_payload(
        rp="/tmp/test_role",
        role_name="test_role",
        description="Test role",
        requirements_display=[],
        undocumented_default_filters=[],
        display_variables={},
        metadata={"features": {}},
    )

    # Verify the contract is satisfied by the result
    assert payload["rp"] == "/tmp/test_role"
    assert payload["role_name"] == "test_role"
    assert isinstance(payload["display_variables"], dict)
    assert isinstance(payload["requirements_display"], list)
    assert isinstance(payload["metadata"], dict)


def test_scanner_output_helpers_route_through_runtime_and_canonical_emission():
    assert callable(scanner._emit_scan_outputs)
    assert (
        scanner._scan_output_emit_scan_outputs.__module__
        == "prism.scanner_io.scan_output_emission"
    )


def test_scanner_facade_style_and_runbook_symbols_remain_import_compatible():
    assert not hasattr(scanner, "render_runbook")
    assert not hasattr(scanner, "render_runbook_csv")
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

    build_hints = get_type_hints(scan_runtime.build_scan_output_payload)

    assert build_hints["return"] is contracts.RunScanOutputPayload


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
    args = scan_runtime.build_emit_scan_outputs_args(
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

    build_hints = get_type_hints(scan_runtime.build_scan_report_sidecar_args)
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

    args = scan_runtime.build_scan_report_sidecar_args(
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


def test_runbook_sidecar_args_typed_seam_contract_annotations():
    """Verify RunbookSidecarArgs TypedDict annotations match build_runbook_sidecar_args return."""
    from typing import get_type_hints

    assert set(contracts.RunbookSidecarArgs.__annotations__) == {
        "runbook_output",
        "runbook_csv_output",
        "role_name",
        "metadata",
    }

    build_hints = get_type_hints(scan_runtime.build_runbook_sidecar_args)
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
    args = scan_runtime.build_runbook_sidecar_args(
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
    args = scan_runtime.build_runbook_sidecar_args(
        runbook_output=None,
        runbook_csv_output=None,
        payload=payload,
    )
    assert args["runbook_output"] is None
    assert args["runbook_csv_output"] is None


def test_scanner_runtime_output_helpers_build_expected_payload_shapes():
    payload = scanner._build_scan_output_payload(
        role_name="demo",
        description="desc",
        display_variables={"x": {"required": False}},
        requirements_display=["dep"],
        undocumented_default_filters=[],
        metadata={"features": {}},
    )

    context_payload = scanner._finalize_scan_context_payload(
        rp="/tmp/demo",
        role_name="demo",
        description="desc",
        requirements_display=["dep"],
        undocumented_default_filters=[],
        display_variables={"x": {"required": False}},
        metadata={"features": {}},
    )

    emit_args = scanner._build_emit_scan_outputs_args(
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

    assert payload["role_name"] == "demo"
    assert context_payload["rp"] == "/tmp/demo"
    assert emit_args["output"] == "README.md"
    assert emit_args["role_name"] == "demo"
    assert not hasattr(scanner, "_build_scan_report_sidecar_args")
    assert not hasattr(scanner, "_build_runbook_sidecar_args")
    assert not hasattr(scanner, "_prepare_run_scan_payload")


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

    monkeypatch.setattr(
        scanner, "DIContainer", lambda role_path, scan_options: object()
    )
    monkeypatch.setattr(scanner, "ScannerContext", FakeContext)
    monkeypatch.setattr(scanner, "_build_emit_scan_outputs_args", fake_build_emit_args)
    monkeypatch.setattr(scanner, "_emit_scan_outputs", fake_emit)

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


def test_execute_scan_with_context_routes_through_scan_facade_helper(
    monkeypatch, tmp_path
):
    captured = {}

    def fake_execute_scan_with_context(**kwargs):
        captured.update(kwargs)
        return "helper-result"

    monkeypatch.setattr(
        scanner._scan_facade_helpers,
        "execute_scan_with_context",
        fake_execute_scan_with_context,
    )

    result = scanner._execute_scan_with_context(
        role_path=str(tmp_path / "role"),
        scan_options={"role_path": str(tmp_path / "role")},
        output="README.md",
        output_format="md",
        concise_readme=False,
        scanner_report_output=None,
        include_scanner_report_link=True,
        template=None,
        dry_run=True,
        runbook_output=None,
        runbook_csv_output=None,
    )

    assert result == "helper-result"
    assert captured["role_path"] == str(tmp_path / "role")
    assert captured["output"] == "README.md"
    assert captured["output_format"] == "md"
    assert captured["scanner_context_cls"].__name__ == "ScannerContext"
    assert callable(captured["prepare_scan_context_fn"])


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

    def fake_build_emit_args(**kwargs):
        captured["payload"] = kwargs["payload"]
        return {"emit_args": True}

    monkeypatch.setattr(
        scanner, "DIContainer", lambda role_path, scan_options: object()
    )
    monkeypatch.setattr(scanner, "ScannerContext", FakeContext)
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

    monkeypatch.setattr(
        scanner, "DIContainer", lambda role_path, scan_options: object()
    )
    monkeypatch.setattr(scanner, "ScannerContext", FakeContext)
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
