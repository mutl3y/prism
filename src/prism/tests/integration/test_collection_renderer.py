"""Unit tests for prism.scanner_io.collection_renderer (FIND-13 closure)."""

from __future__ import annotations

from pathlib import Path

from prism.scanner_io.collection_renderer import (
    format_collection_summary,
    render_collection_markdown,
    write_collection_runbook_artifacts,
)


def _payload(**overrides) -> dict:
    base = {
        "collection": {
            "metadata": {"namespace": "ns", "name": "col", "version": "1.0"}
        },
        "summary": {"total_roles": 2, "scanned_roles": 1, "failed_roles": 1},
        "dependencies": {"collections": [], "roles": [], "conflicts": []},
        "plugin_catalog": {"summary": {}, "by_type": {}, "failures": []},
        "roles": [],
        "failures": [],
    }
    base.update(overrides)
    return base


def test_render_includes_fqcn_and_summary_block() -> None:
    out = render_collection_markdown(_payload())
    assert "# ns.col Collection Documentation" in out
    assert "FQCN: `ns.col`" in out
    assert "Total roles: 2" in out
    assert "Scanned roles: 1" in out
    assert "Failed roles: 1" in out


def test_render_handles_missing_metadata_gracefully() -> None:
    out = render_collection_markdown({})
    assert "unknown.collection" in out


def test_render_lists_collection_dependencies() -> None:
    payload = _payload(
        dependencies={
            "collections": [{"key": "ns.dep", "version": "2.0"}],
            "roles": [{"name": "rdep"}],
            "conflicts": [{"key": "k", "versions": ["1", "2"]}],
        }
    )
    out = render_collection_markdown(payload)
    assert "Collection Dependencies" in out
    assert "`ns.dep` (2.0)" in out
    assert "Role Dependencies" in out
    assert "`rdep` (latest)" in out
    assert "Dependency Conflicts" in out


def test_render_truncates_roles_above_limit() -> None:
    roles = [{"role": f"r{i:03d}", "payload": {"metadata": {}}} for i in range(70)]
    payload = _payload(roles=roles)
    out = render_collection_markdown(payload)
    assert "and 10 more roles" in out


def test_render_lists_role_scanner_counters() -> None:
    payload = _payload(
        roles=[
            {
                "role": "r1",
                "payload": {
                    "metadata": {"scanner_counters": {"task_files": 5, "templates": 3}}
                },
            }
        ]
    )
    out = render_collection_markdown(payload)
    assert "task_files=5" in out
    assert "templates=3" in out


def test_render_lists_plugin_summary_and_filter_capabilities() -> None:
    payload = _payload(
        plugin_catalog={
            "summary": {"total_plugins": 3, "files_scanned": 5, "files_failed": 0},
            "by_type": {
                "filter": [
                    {
                        "name": "f1",
                        "symbols": ["a", "b"],
                        "confidence": "high",
                    }
                ],
                "module": [{"name": "m"}],
            },
            "failures": [{"relative_path": "p", "stage": "scan", "error": "boom"}],
        }
    )
    out = render_collection_markdown(payload)
    assert "Total plugins: 3" in out
    assert "Plugin Types" in out
    assert "`filter`: 1" in out
    assert "Filter Capabilities" in out
    assert "`f1` [high]: a, b" in out
    assert "Plugin Scan Failures" in out
    assert "`p` (scan): boom" in out


def test_render_lists_role_failures() -> None:
    payload = _payload(failures=[{"role": "broken", "error": "explosion"}])
    out = render_collection_markdown(payload)
    assert "Role Scan Failures" in out
    assert "`broken`: explosion" in out


def test_format_collection_summary_includes_namespace_dot_name() -> None:
    out = format_collection_summary(_payload())
    assert "Collection: ns.col" in out
    assert "Roles scanned: 1" in out
    assert "Roles failed: 1" in out


def test_format_collection_summary_falls_back_to_path_basename() -> None:
    payload = {
        "collection": {"path": "/some/dir/mycol/", "metadata": {}},
        "summary": {"scanned_roles": 0, "failed_roles": 0},
    }
    out = format_collection_summary(payload)
    assert "Collection: mycol" in out


def test_format_collection_summary_default_when_no_data() -> None:
    out = format_collection_summary({})
    assert "Collection: collection" in out


def test_write_runbook_artifacts_writes_only_to_configured_dirs(tmp_path: Path) -> None:
    rb_dir = tmp_path / "rb"
    csv_dir = tmp_path / "csv"
    write_collection_runbook_artifacts(
        role_name="r1",
        metadata={"k": "v"},
        runbook_output_dir=str(rb_dir),
        runbook_csv_output_dir=str(csv_dir),
        render_runbook_fn=lambda name, meta: f"# {name}",
        render_runbook_csv_fn=lambda meta: "name,value\n",
    )
    assert (rb_dir / "r1.runbook.md").read_text(encoding="utf-8") == "# r1"
    assert (csv_dir / "r1.runbook.csv").read_text(encoding="utf-8") == "name,value\n"


def test_write_runbook_artifacts_skips_when_dirs_unset(tmp_path: Path) -> None:
    calls: list[str] = []
    write_collection_runbook_artifacts(
        role_name="r1",
        metadata={},
        runbook_output_dir=None,
        runbook_csv_output_dir=None,
        render_runbook_fn=lambda *_a: "x",
        render_runbook_csv_fn=lambda *_a: "x",
    )
    assert calls == []
