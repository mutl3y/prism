"""Focused tests for scan-context and output-payload shaping helpers."""

from typing import get_type_hints

from prism import scanner
from prism.scanner_submodules import scan_context


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
        scanner,
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
        scanner,
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
