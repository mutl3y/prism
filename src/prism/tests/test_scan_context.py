"""Focused tests for scan-context and output-payload shaping helpers."""

from typing import get_type_hints

from prism import scanner
from prism.scanner_submodules import render_reports, scan_context


def test_finalize_scan_context_payload_shapes_expected_tuple():
    payload = scan_context.finalize_scan_context_payload(
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
    payload = scan_context.build_scan_output_payload(
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


def test_prepare_run_scan_payload_maps_prepared_context():
    payload = scan_context.prepare_run_scan_payload(
        prepared_scan_context=(
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
    )

    assert payload == {
        "role_name": "demo_role",
        "description": "demo",
        "requirements_display": ["dep"],
        "undocumented_default_filters": [{"file": "tasks/main.yml"}],
        "display_variables": {"name": {"required": False}},
        "metadata": {"features": {"tasks_scanned": 1}},
    }


def test_scan_output_payload_typed_seam_contract_annotations():
    assert set(scan_context.RunScanOutputPayload.__annotations__) == {
        "role_name",
        "description",
        "display_variables",
        "requirements_display",
        "undocumented_default_filters",
        "metadata",
    }

    build_hints = get_type_hints(scan_context.build_scan_output_payload)
    prepare_hints = get_type_hints(scan_context.prepare_run_scan_payload)

    assert build_hints["return"] is scan_context.RunScanOutputPayload
    assert prepare_hints["return"] is scan_context.RunScanOutputPayload


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
    direct = scan_context.finalize_scan_context_payload(
        rp="/tmp/role",
        role_name="demo_role",
        description="demo",
        requirements_display=["dep"],
        undocumented_default_filters=[{"file": "tasks/main.yml"}],
        display_variables={"name": {"required": False}},
        metadata={"features": {"tasks_scanned": 1}},
    )

    assert wrapped == direct


def test_scanner_wrapper_build_scan_output_payload_matches_helper():
    wrapped = scanner._build_scan_output_payload(
        role_name="demo_role",
        description="demo",
        display_variables={"name": {"required": False}},
        requirements_display=["dep"],
        undocumented_default_filters=[{"file": "tasks/main.yml"}],
        metadata={"features": {"tasks_scanned": 1}},
    )
    direct = scan_context.build_scan_output_payload(
        role_name="demo_role",
        description="demo",
        display_variables={"name": {"required": False}},
        requirements_display=["dep"],
        undocumented_default_filters=[{"file": "tasks/main.yml"}],
        metadata={"features": {"tasks_scanned": 1}},
    )

    assert wrapped == direct


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

    captured = {}

    def fake_prepare_run_scan_payload(*, prepared_scan_context):
        captured["prepared_scan_context"] = prepared_scan_context
        return {"ok": True}

    monkeypatch.setattr(
        scanner,
        "_scan_context_prepare_run_scan_payload",
        fake_prepare_run_scan_payload,
    )

    result = scanner._prepare_run_scan_payload({"role_path": "/tmp/role"})

    assert captured["prepared_scan_context"] == prepared_context
    assert result == {"ok": True}


def test_emit_scan_outputs_args_typed_seam_contract_annotations():
    assert set(scan_context.EmitScanOutputsArgs.__annotations__) == {
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

    build_hints = get_type_hints(scan_context.build_emit_scan_outputs_args)
    assert build_hints["return"] is scan_context.EmitScanOutputsArgs


def test_build_emit_scan_outputs_args_flattens_payload_fields():
    payload = {
        "role_name": "my_role",
        "description": "desc",
        "display_variables": {"v": {"required": True}},
        "requirements_display": ["req"],
        "undocumented_default_filters": [{"file": "tasks/main.yml"}],
        "metadata": {"features": {"tasks_scanned": 2}},
    }
    args = scan_context.build_emit_scan_outputs_args(
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


def test_scanner_wrapper_build_emit_scan_outputs_args_delegates():
    payload = {
        "role_name": "wrap_role",
        "description": "wrap_desc",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
    }
    captured = {}

    def fake_build(
        *,
        output,
        output_format,
        concise_readme,
        scanner_report_output,
        include_scanner_report_link,
        payload,
        template,
        dry_run,
        runbook_output,
        runbook_csv_output,
    ):
        captured["output"] = output
        captured["payload"] = payload
        captured["dry_run"] = dry_run
        return {"delegated": True}

    import unittest.mock as mock

    with mock.patch.object(
        scanner,
        "_scan_context_build_emit_scan_outputs_args",
        side_effect=fake_build,
    ):
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

    assert captured["output"] == "README.md"
    assert captured["payload"] is payload
    assert captured["dry_run"] is True
    assert result == {"delegated": True}


def test_scan_report_sidecar_args_typed_seam_contract_annotations():
    assert set(scan_context.ScanReportSidecarArgs.__annotations__) == {
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

    build_hints = get_type_hints(scan_context.build_scan_report_sidecar_args)
    assert build_hints["return"] is scan_context.ScanReportSidecarArgs


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

    args = scan_context.build_scan_report_sidecar_args(
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


def test_scanner_wrapper_build_scan_report_sidecar_args_delegates():
    from pathlib import Path
    import unittest.mock as mock

    payload = {
        "role_name": "wrap_role",
        "description": "wrap_desc",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
    }
    out_path = Path("/tmp/README.md")
    captured = {}

    def fake_build(
        *,
        concise_readme,
        scanner_report_output,
        out_path,
        include_scanner_report_link,
        payload,
        dry_run,
    ):
        captured["concise_readme"] = concise_readme
        captured["out_path"] = out_path
        captured["payload"] = payload
        captured["dry_run"] = dry_run
        return {"delegated": True}

    with mock.patch.object(
        render_reports,
        "_scan_context_build_scan_report_sidecar_args",
        side_effect=fake_build,
    ):
        result = scanner._build_scan_report_sidecar_args(
            concise_readme=True,
            scanner_report_output=None,
            out_path=out_path,
            include_scanner_report_link=False,
            payload=payload,
            dry_run=True,
        )

    assert captured["concise_readme"] is True
    assert captured["out_path"] is out_path

    assert captured["payload"] is payload
    assert captured["dry_run"] is True
    assert result == {"delegated": True}


def test_runbook_sidecar_args_typed_seam_contract_annotations():
    """Verify RunbookSidecarArgs TypedDict annotations match build_runbook_sidecar_args return."""
    from typing import get_type_hints

    assert set(scan_context.RunbookSidecarArgs.__annotations__) == {
        "runbook_output",
        "runbook_csv_output",
        "role_name",
        "metadata",
    }

    build_hints = get_type_hints(scan_context.build_runbook_sidecar_args)
    assert build_hints["return"] is scan_context.RunbookSidecarArgs


def test_build_runbook_sidecar_args_from_payload():
    payload = {
        "role_name": "runbook_role",
        "description": "runbook_desc",
        "display_variables": {"x": 1},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {"key": "val"},
    }
    args = scan_context.build_runbook_sidecar_args(
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
    args = scan_context.build_runbook_sidecar_args(
        runbook_output=None,
        runbook_csv_output=None,
        payload=payload,
    )
    assert args["runbook_output"] is None
    assert args["runbook_csv_output"] is None


def test_scanner_wrapper_build_runbook_sidecar_args_delegates():
    import unittest.mock as mock

    payload = {
        "role_name": "wrap_r",
        "description": "wrap_d",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
    }
    captured = {}

    def fake_build(*, runbook_output, runbook_csv_output, payload):
        captured["runbook_output"] = runbook_output
        captured["runbook_csv_output"] = runbook_csv_output
        captured["payload"] = payload
        return {"delegated": True}

    with mock.patch.object(
        render_reports,
        "_scan_context_build_runbook_sidecar_args",
        side_effect=fake_build,
    ):
        result = scanner._build_runbook_sidecar_args(
            runbook_output="/out/runbook.md",
            runbook_csv_output=None,
            payload=payload,
        )

    assert captured["runbook_output"] == "/out/runbook.md"
    assert captured["runbook_csv_output"] is None
    assert captured["payload"] is payload
    assert result == {"delegated": True}


def test_scan_base_context_typed_seam_keys():
    """ScanBaseContext TypedDict must expose all expected base-context fields."""
    from typing import get_type_hints

    hints = get_type_hints(scan_context.ScanBaseContext)
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
        def __init__(self, *, di, role_path, scan_options):
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


def test_execute_scan_with_context_falls_back_when_orchestrated_payload_incomplete(
    monkeypatch,
):
    scan_options = {"role_path": "/tmp/role", "include_vars_main": True}
    fallback_payload = {
        "role_name": "fallback_role",
        "description": "fallback_desc",
        "display_variables": {"x": {"required": False}},
        "requirements_display": ["dep"],
        "undocumented_default_filters": [],
        "metadata": {"features": {}},
    }

    class FakeContext:
        def __init__(self, *, di, role_path, scan_options):
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

    def fake_prepare(options):
        assert options is scan_options
        return fallback_payload

    def fake_build_emit_args(**kwargs):
        captured["payload"] = kwargs["payload"]
        return {"emit_args": True}

    monkeypatch.setattr(
        scanner, "DIContainer", lambda role_path, scan_options: object()
    )
    monkeypatch.setattr(scanner, "ScannerContext", FakeContext)
    monkeypatch.setattr(scanner, "_prepare_run_scan_payload", fake_prepare)
    monkeypatch.setattr(scanner, "_build_emit_scan_outputs_args", fake_build_emit_args)
    monkeypatch.setattr(scanner, "_emit_scan_outputs", lambda args: "rendered")

    result = scanner._execute_scan_with_context(
        role_path="/tmp/role",
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
    assert captured["payload"] is fallback_payload


def test_execute_scan_with_context_uses_real_scanner_context_without_fallback(
    monkeypatch, tmp_path
):
    role_path = str(tmp_path / "demo_role")
    (tmp_path / "demo_role").mkdir()
    scan_options = {"role_path": role_path, "include_vars_main": True}
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
    assert scanner._is_complete_scan_output_payload(captured["payload"])
    assert captured["payload"]["role_name"] == "demo_role"


def test_execute_scan_with_context_falls_back_when_vars_seed_paths_present(
    monkeypatch,
    tmp_path,
):
    role_path = str(tmp_path / "role")
    (tmp_path / "role").mkdir()
    scan_options = {
        "role_path": role_path,
        "include_vars_main": True,
        "vars_seed_paths": ["/tmp/group_vars/all.yml"],
    }
    fallback_payload = {
        "role_name": "fallback_role",
        "description": "fallback_desc",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {"external_vars_context": {"sources": []}},
    }

    captured = {}

    def fake_prepare(options):
        assert options is scan_options
        return fallback_payload

    def fake_build_emit_args(**kwargs):
        captured["payload"] = kwargs["payload"]
        return {"emit_args": True}

    def fail_if_container_called(*_args, **_kwargs):
        raise AssertionError(
            "DIContainer should not be called for deterministic fallback"
        )

    class FailIfScannerContextConstructed:
        def __init__(self, **_kwargs):
            raise AssertionError(
                "ScannerContext should not be constructed for deterministic fallback"
            )

    monkeypatch.setattr(scanner, "DIContainer", fail_if_container_called)
    monkeypatch.setattr(scanner, "ScannerContext", FailIfScannerContextConstructed)
    monkeypatch.setattr(scanner, "_prepare_run_scan_payload", fake_prepare)
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
    assert captured["payload"] is fallback_payload
    assert (
        captured["payload"]["metadata"]["scanner_context_fallback_reason"]
        == "vars_seed_paths_present"
    )


def test_execute_scan_with_context_falls_back_when_style_readme_path_missing(
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
    fallback_payload = {
        "role_name": "fallback_role",
        "description": "fallback_desc",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
    }
    captured = {}

    def fake_prepare(options):
        assert options is scan_options
        return fallback_payload

    def fake_build_emit_args(**kwargs):
        captured["payload"] = kwargs["payload"]
        return {"emit_args": True}

    def fail_if_container_called(*_args, **_kwargs):
        raise AssertionError(
            "DIContainer should not be called for deterministic fallback"
        )

    class FailIfScannerContextConstructed:
        def __init__(self, **_kwargs):
            raise AssertionError(
                "ScannerContext should not be constructed for deterministic fallback"
            )

    monkeypatch.setattr(scanner, "DIContainer", fail_if_container_called)
    monkeypatch.setattr(scanner, "ScannerContext", FailIfScannerContextConstructed)
    monkeypatch.setattr(scanner, "_prepare_run_scan_payload", fake_prepare)
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
    assert captured["payload"] is fallback_payload
    assert (
        captured["payload"]["metadata"]["scanner_context_fallback_reason"]
        == "style_readme_path_missing"
    )


def test_execute_scan_with_context_falls_back_when_compare_role_path_missing(
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
    fallback_payload = {
        "role_name": "fallback_role",
        "description": "fallback_desc",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
    }
    captured = {}

    def fake_prepare(options):
        assert options is scan_options
        return fallback_payload

    def fake_build_emit_args(**kwargs):
        captured["payload"] = kwargs["payload"]
        return {"emit_args": True}

    def fail_if_container_called(*_args, **_kwargs):
        raise AssertionError(
            "DIContainer should not be called for deterministic fallback"
        )

    class FailIfScannerContextConstructed:
        def __init__(self, **_kwargs):
            raise AssertionError(
                "ScannerContext should not be constructed for deterministic fallback"
            )

    monkeypatch.setattr(scanner, "DIContainer", fail_if_container_called)
    monkeypatch.setattr(scanner, "ScannerContext", FailIfScannerContextConstructed)
    monkeypatch.setattr(scanner, "_prepare_run_scan_payload", fake_prepare)
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
    assert captured["payload"] is fallback_payload
    assert (
        captured["payload"]["metadata"]["scanner_context_fallback_reason"]
        == "compare_role_path_missing"
    )


def test_execute_scan_with_context_falls_back_when_role_path_missing_reason_is_recorded(
    monkeypatch,
):
    scan_options = {
        "role_path": "/tmp/missing-role",
        "include_vars_main": True,
    }
    fallback_payload = {
        "role_name": "fallback_role",
        "description": "fallback_desc",
        "display_variables": {},
        "requirements_display": [],
        "undocumented_default_filters": [],
        "metadata": {},
    }

    captured = {}

    def fake_prepare(options):
        assert options is scan_options
        return fallback_payload

    def fake_build_emit_args(**kwargs):
        captured["payload"] = kwargs["payload"]
        return {"emit_args": True}

    def fail_if_container_called(*_args, **_kwargs):
        raise AssertionError(
            "DIContainer should not be called for deterministic fallback"
        )

    class FailIfScannerContextConstructed:
        def __init__(self, **_kwargs):
            raise AssertionError(
                "ScannerContext should not be constructed for deterministic fallback"
            )

    monkeypatch.setattr(scanner, "DIContainer", fail_if_container_called)
    monkeypatch.setattr(scanner, "ScannerContext", FailIfScannerContextConstructed)
    monkeypatch.setattr(scanner, "_prepare_run_scan_payload", fake_prepare)
    monkeypatch.setattr(scanner, "_build_emit_scan_outputs_args", fake_build_emit_args)
    monkeypatch.setattr(scanner, "_emit_scan_outputs", lambda args: "rendered")

    result = scanner._execute_scan_with_context(
        role_path="/tmp/missing-role",
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
    assert captured["payload"] is fallback_payload
    assert (
        captured["payload"]["metadata"]["scanner_context_fallback_reason"]
        == "role_path_missing"
    )


def test_execute_scan_with_context_does_not_set_fallback_reason_when_context_path_used(
    monkeypatch, tmp_path
):
    role_path = str(tmp_path / "demo_role")
    (tmp_path / "demo_role").mkdir()
    scan_options = {"role_path": role_path, "include_vars_main": True}
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
    assert scanner._is_complete_scan_output_payload(captured["payload"])
    assert "scanner_context_fallback_reason" not in captured["payload"]["metadata"]


def test_execute_scan_with_context_emitted_args_keep_canonical_keyset_across_paths(
    monkeypatch, tmp_path
):
    role_path = str(tmp_path / "role")
    (tmp_path / "role").mkdir()

    canonical_keys: set[str] | None = None
    captured_paths: dict[str, set[str]] = {}

    def fake_emit(args):
        nonlocal canonical_keys
        current_keys = set(args.keys())
        path_label = (
            "fallback" if args["role_name"].startswith("fallback") else "context"
        )
        captured_paths[path_label] = current_keys
        if canonical_keys is None:
            canonical_keys = current_keys
        else:
            assert current_keys == canonical_keys
        return "rendered"

    monkeypatch.setattr(scanner, "_emit_scan_outputs", fake_emit)

    context_scan_options = {
        "role_path": role_path,
        "include_vars_main": True,
    }
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

    fallback_scan_options = {
        "role_path": role_path,
        "include_vars_main": True,
        "vars_seed_paths": ["/tmp/group_vars/all.yml"],
    }

    def fake_prepare(options):
        return {
            "role_name": "fallback_role",
            "description": "fallback_desc",
            "display_variables": {},
            "requirements_display": [],
            "undocumented_default_filters": [],
            "metadata": {},
        }

    monkeypatch.setattr(scanner, "_prepare_run_scan_payload", fake_prepare)

    result_fallback = scanner._execute_scan_with_context(
        role_path=role_path,
        scan_options=fallback_scan_options,
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
    assert result_fallback == "rendered"
    assert captured_paths["context"] == captured_paths["fallback"]
