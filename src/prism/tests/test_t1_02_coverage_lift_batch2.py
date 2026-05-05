"""T1-02: targeted unit tests, batch 2 — ansible/yaml/runbook helpers.

No filesystem fixtures beyond pytest tmp_path; pure-Python behavior tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest


# ---- scanner_plugins/ansible/task_line_parsing.py -------------------------


def test_detect_task_module_include_tasks_and_role() -> None:
    from prism.scanner_plugins.ansible.task_line_parsing import detect_task_module

    assert detect_task_module({"include_tasks": "x.yml"}) == "include_tasks"
    assert detect_task_module({"ansible.builtin.import_tasks": "x"}) == "import_tasks"
    assert detect_task_module({"include_role": {"name": "r"}}) == "include_role"
    assert (
        detect_task_module({"ansible.builtin.import_role": {"name": "r"}})
        == "import_role"
    )


def test_detect_task_module_picks_first_non_meta_key() -> None:
    from prism.scanner_plugins.ansible.task_line_parsing import detect_task_module

    assert detect_task_module({"name": "n", "shell": "ls"}) == "shell"
    # all-meta task -> None
    assert detect_task_module({"name": "n", "when": "x", "tags": []}) is None
    # with_* loop helpers should be skipped
    assert detect_task_module({"with_items": [1], "command": "echo"}) == "command"
    # block-style tasks: only meta keys -> None
    assert detect_task_module({"block": [], "name": "g"}) is None


def test_task_line_parsing_constants_present() -> None:
    from prism.scanner_plugins.ansible import task_line_parsing as tlp

    assert "include_tasks" in tlp.TASK_INCLUDE_KEYS
    assert "import_role" in tlp.ROLE_INCLUDE_KEYS
    assert "set_fact" in tlp.SET_FACT_KEYS
    assert "block" in tlp.TASK_BLOCK_KEYS
    assert "name" in tlp.TASK_META_KEYS


# ---- scanner_plugins/parsers/yaml/parsing_policy.py -----------------------


def test_yaml_load_yaml_file_valid_and_invalid(tmp_path: Path) -> None:
    from prism.scanner_plugins.parsers.yaml.parsing_policy import (
        DefaultYAMLParsingPolicyPlugin,
    )

    good = tmp_path / "g.yml"
    good.write_text("a: 1\nb: [1,2]\n", encoding="utf-8")
    assert DefaultYAMLParsingPolicyPlugin.load_yaml_file(good) == {"a": 1, "b": [1, 2]}

    bad = tmp_path / "b.yml"
    bad.write_text("a: [unterminated\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="yaml_load_error"):
        DefaultYAMLParsingPolicyPlugin.load_yaml_file(bad)

    missing = tmp_path / "missing.yml"
    with pytest.raises(RuntimeError, match="yaml_load_error"):
        DefaultYAMLParsingPolicyPlugin.load_yaml_file(missing)


def test_yaml_parse_yaml_candidate_paths(tmp_path: Path) -> None:
    from prism.scanner_plugins.parsers.yaml.parsing_policy import (
        DefaultYAMLParsingPolicyPlugin,
    )

    role_root = tmp_path
    valid = tmp_path / "tasks" / "main.yml"
    valid.parent.mkdir()
    valid.write_text("- name: x\n  command: echo\n", encoding="utf-8")
    assert DefaultYAMLParsingPolicyPlugin.parse_yaml_candidate(valid, role_root) is None

    invalid = tmp_path / "tasks" / "broken.yml"
    invalid.write_text("a: [oops\n", encoding="utf-8")
    failure = DefaultYAMLParsingPolicyPlugin.parse_yaml_candidate(invalid, role_root)
    assert failure is not None
    assert failure["file"] == "tasks/broken.yml"
    assert failure["line"] is not None
    assert "error" in failure

    missing = tmp_path / "missing.yml"
    failure2 = DefaultYAMLParsingPolicyPlugin.parse_yaml_candidate(missing, role_root)
    assert failure2 is not None
    assert failure2["error"].startswith("read_error:")


def test_yaml_parse_yaml_candidate_outside_role_root(tmp_path: Path) -> None:
    from prism.scanner_plugins.parsers.yaml.parsing_policy import (
        DefaultYAMLParsingPolicyPlugin,
    )

    role_root = tmp_path / "role"
    role_root.mkdir()
    other = tmp_path / "other.yml"
    other.write_text("a: [bad\n", encoding="utf-8")
    failure = DefaultYAMLParsingPolicyPlugin.parse_yaml_candidate(other, role_root)
    assert failure is not None
    # When candidate is outside role_root, helper falls back to absolute path
    assert failure["file"].endswith("other.yml")


# ---- scanner_reporting/runbook.py -----------------------------------------


def test_build_runbook_rows_handles_mixed_kinds() -> None:
    from prism.scanner_plugins.parsers.comment_doc.runbook_renderer import (
        build_runbook_rows,
    )

    metadata = {
        "task_catalog": [
            {
                "file": "tasks/main.yml",
                "name": "Install",
                "annotations": [
                    {"kind": "runbook", "text": "run apt-get update"},
                    {"kind": "warn", "text": "needs sudo"},
                    {"kind": "note", "text": ""},  # empty -> skipped
                    "not-a-dict",  # skipped
                ],
            },
            {
                "file": "tasks/run.yml",
                "name": "Restart",
                "annotations": "not-a-list",  # treated as []
            },
            "not-a-dict-task",  # skipped
        ]
    }
    rows = build_runbook_rows(metadata)
    assert rows == [
        ("tasks/main.yml", "Install", "run apt-get update"),
        ("tasks/main.yml", "Install", "Warn: needs sudo"),
    ]


def test_build_runbook_rows_empty_inputs() -> None:
    from prism.scanner_plugins.parsers.comment_doc.runbook_renderer import (
        build_runbook_rows,
    )

    assert build_runbook_rows(None) == []
    assert build_runbook_rows({}) == []
    assert build_runbook_rows({"task_catalog": None}) == []


def test_render_runbook_csv_header_and_rows() -> None:
    from prism.scanner_plugins.parsers.comment_doc.runbook_renderer import (
        render_runbook_csv,
    )

    metadata = {
        "task_catalog": [
            {
                "file": "tasks/main.yml",
                "name": "Step",
                "annotations": [{"kind": "runbook", "text": "do thing"}],
            }
        ]
    }
    out = render_runbook_csv(metadata)
    lines = out.strip().splitlines()
    assert lines[0] == "file,task_name,step"
    assert lines[1] == "tasks/main.yml,Step,do thing"


# ---- scanner_plugins/ansible/__init__.py ----------------------------------


def test_ansible_scan_pipeline_plugin_process_pipeline() -> None:
    from prism.scanner_plugins.ansible import AnsibleScanPipelinePlugin

    plugin = AnsibleScanPipelinePlugin()
    out = plugin.process_scan_pipeline(
        scan_options={"role_path": "/r"},
        scan_context={"existing": True},
    )
    assert out["plugin_platform"] == "ansible"
    assert out["plugin_name"] == "ansible"
    assert out["existing"] is True
    assert out["role_path"] == "/r"
    assert out["plugin_enabled"] is True
    assert "ansible_plugin_enabled" in out and isinstance(
        out["ansible_plugin_enabled"], bool
    )


def test_ansible_scan_pipeline_plugin_keeps_default_route_enabled_when_flags_unset(
    monkeypatch,
) -> None:
    from prism.scanner_plugins.ansible import AnsibleScanPipelinePlugin
    from prism.scanner_plugins.ansible.feature_flags import (
        ANSIBLE_PLUGIN_ENABLED_ENV_VAR,
        KERNEL_ENABLED_ENV_VAR,
    )

    monkeypatch.delenv(KERNEL_ENABLED_ENV_VAR, raising=False)
    monkeypatch.delenv(ANSIBLE_PLUGIN_ENABLED_ENV_VAR, raising=False)

    out = AnsibleScanPipelinePlugin().process_scan_pipeline(
        scan_options={"role_path": "/r"},
        scan_context={},
    )

    assert out["plugin_enabled"] is True
    assert out["ansible_plugin_enabled"] is False


def test_ansible_scan_pipeline_plugin_preserves_existing_role_path() -> None:
    from prism.scanner_plugins.ansible import AnsibleScanPipelinePlugin

    out = AnsibleScanPipelinePlugin().process_scan_pipeline(
        scan_options={"role_path": "/from-options"},
        scan_context={"role_path": "/preserved"},
    )
    assert out["role_path"] == "/preserved"


def test_ansible_orchestrate_scan_payload_merges_metadata() -> None:
    from prism.scanner_plugins.ansible import AnsibleScanPipelinePlugin

    payload = {"metadata": {"existing_key": "keep", "nested": {"a": 1}}}
    result = AnsibleScanPipelinePlugin().orchestrate_scan_payload(
        payload=payload,
        scan_options={"role_path": "/r"},
        strict_mode=False,
        preflight_context={"injected": True, "nested": {"b": 2}},
    )
    md = result["metadata"]
    assert md["existing_key"] == "keep"
    assert md["injected"] is True
    # nested merge preserves existing keys
    assert md["nested"] == {"a": 1, "b": 2}


def test_ansible_orchestrate_scan_payload_with_no_metadata() -> None:
    from prism.scanner_plugins.ansible import AnsibleScanPipelinePlugin

    payload = {"metadata": None}
    result = AnsibleScanPipelinePlugin().orchestrate_scan_payload(
        payload=payload,
        scan_options={"role_path": "/r"},
        strict_mode=False,
        preflight_context=None,
    )
    md = result["metadata"]
    assert md["plugin_platform"] == "ansible"
    assert md["role_path"] == "/r"


def test_ansible_orchestrate_scan_payload_returns_payload_when_plugin_returns_non_dict() -> (
    None
):
    from prism.scanner_plugins.ansible import AnsibleScanPipelinePlugin

    class _Bad(AnsibleScanPipelinePlugin):
        def process_scan_pipeline(self, scan_options, scan_context):  # type: ignore[override]
            return "not a dict"  # type: ignore[return-value]

    payload = {"metadata": {"x": 1}}
    out = _Bad().orchestrate_scan_payload(
        payload=payload,
        scan_options={"role_path": "/r"},
        strict_mode=False,
        preflight_context=None,
    )
    assert out is payload


# ---- scanner_config/marker.py ---------------------------------------------


def _write_role_yaml(role_path: Path, content: str) -> Path:
    role_path.mkdir(parents=True, exist_ok=True)
    cfg = role_path / ".prism.yml"
    cfg.write_text(content, encoding="utf-8")
    return cfg


def test_load_readme_marker_prefix_default_when_missing(tmp_path: Path) -> None:
    from prism.scanner_config.marker import load_readme_marker_prefix

    assert load_readme_marker_prefix(str(tmp_path)) == "prism"


def test_load_readme_marker_prefix_from_config(tmp_path: Path) -> None:
    from prism.scanner_config.marker import load_readme_marker_prefix

    _write_role_yaml(tmp_path, "markers:\n  prefix: doc\n")
    assert load_readme_marker_prefix(str(tmp_path)) == "doc"


def test_load_readme_marker_prefix_via_readme_section(tmp_path: Path) -> None:
    from prism.scanner_config.marker import load_readme_marker_prefix

    _write_role_yaml(tmp_path, "readme:\n  markers:\n    prefix: alt\n")
    assert load_readme_marker_prefix(str(tmp_path)) == "alt"


@pytest.mark.parametrize(
    "yaml_text,expected_code",
    [
        ("a: [oops\n", "README_MARKER_CONFIG_YAML_INVALID"),
        ("just-a-string\n", "README_MARKER_CONFIG_SHAPE_INVALID"),
        ("markers: not-a-mapping\n", "README_MARKER_CONFIG_SHAPE_INVALID"),
        ("markers:\n  prefix: 123\n", "README_MARKER_CONFIG_SHAPE_INVALID"),
        ("markers:\n  prefix: '   '\n", "README_MARKER_CONFIG_SHAPE_INVALID"),
        ("markers:\n  prefix: bad space\n", "README_MARKER_CONFIG_SHAPE_INVALID"),
    ],
)
def test_load_readme_marker_prefix_records_warnings(
    tmp_path: Path, yaml_text: str, expected_code: str
) -> None:
    from prism.scanner_config.marker import load_readme_marker_prefix

    _write_role_yaml(tmp_path, yaml_text)
    warnings: list[str] = []
    assert (
        load_readme_marker_prefix(str(tmp_path), warning_collector=warnings) == "prism"
    )
    assert any(w.startswith(expected_code) for w in warnings), warnings


def test_load_readme_marker_prefix_no_markers_section(tmp_path: Path) -> None:
    from prism.scanner_config.marker import load_readme_marker_prefix

    _write_role_yaml(tmp_path, "other: 1\n")
    warnings: list[str] = []
    assert (
        load_readme_marker_prefix(str(tmp_path), warning_collector=warnings) == "prism"
    )
    assert warnings == []
