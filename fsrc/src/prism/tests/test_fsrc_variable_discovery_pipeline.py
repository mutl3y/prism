"""Focused fsrc tests for variable discovery and pipeline parity foundations."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "fsrc" / "src"


@contextmanager
def _prefer_fsrc_prism_on_sys_path() -> object:
    original_path = list(sys.path)
    original_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == "prism" or key.startswith("prism.")
    }
    try:
        sys.path.insert(0, str(FSRC_SOURCE_ROOT))
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        yield
    finally:
        sys.path[:] = original_path
        for module_name in list(sys.modules):
            if module_name == "prism" or module_name.startswith("prism."):
                del sys.modules[module_name]
        sys.modules.update(original_modules)


def test_fsrc_variable_discovery_importable() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        module = importlib.import_module("prism.scanner_core.variable_discovery")

    assert hasattr(module, "VariableDiscovery")


def test_fsrc_variable_discovery_static_and_referenced_foundation(tmp_path) -> None:
    role_path = tmp_path
    (role_path / "defaults").mkdir()
    (role_path / "vars").mkdir()
    (role_path / "tasks").mkdir()
    (role_path / "defaults" / "main.yml").write_text(
        "---\ndefault_only: default\nshared_value: from_defaults\n",
        encoding="utf-8",
    )
    (role_path / "vars" / "main.yml").write_text(
        "---\nvars_only: vars\n",
        encoding="utf-8",
    )
    (role_path / "tasks" / "main.yml").write_text(
        '---\n- name: demo\n  debug:\n    msg: "{{ default_only }} {{ runtime_only }}"\n',
        encoding="utf-8",
    )
    (role_path / "README.md").write_text(
        "Input: {{ readme_input }}\n",
        encoding="utf-8",
    )

    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        discovery_module = importlib.import_module(
            "prism.scanner_core.variable_discovery"
        )
        options = {
            "role_path": str(role_path),
            "include_vars_main": True,
            "exclude_path_patterns": None,
            "vars_seed_paths": None,
            "ignore_unresolved_internal_underscore_references": False,
        }
        container = di_module.DIContainer(
            role_path=str(role_path), scan_options=options
        )
        discovery = discovery_module.VariableDiscovery(
            container, str(role_path), options
        )
        static_rows = discovery.discover_static()
        referenced = discovery.discover_referenced()
        all_rows = discovery.discover()

    static_names = {row["name"] for row in static_rows}
    assert "default_only" in static_names
    assert "vars_only" in static_names

    assert "default_only" in referenced
    assert "runtime_only" in referenced
    assert "readme_input" in referenced

    unresolved = {row["name"] for row in all_rows if row.get("is_unresolved")}
    assert "runtime_only" in unresolved


def test_fsrc_variable_pipeline_build_static_rows_override_shape(tmp_path) -> None:
    role_root = tmp_path
    default_path = role_root / "defaults" / "main.yml"
    var_path = role_root / "vars" / "main.yml"
    default_path.parent.mkdir(parents=True)
    var_path.parent.mkdir(parents=True)
    default_path.write_text("---\nshared: from_default\n", encoding="utf-8")
    var_path.write_text("---\nshared: from_vars\n", encoding="utf-8")

    with _prefer_fsrc_prism_on_sys_path():
        pipeline_module = importlib.import_module(
            "prism.scanner_core.variable_pipeline"
        )
        rows, by_name = pipeline_module.build_static_variable_rows(
            role_root=role_root,
            defaults_data={"shared": "from_default"},
            vars_data={"shared": "from_vars"},
            defaults_sources={"shared": default_path},
            vars_sources={"shared": var_path},
        )

    assert len(rows) == 1
    assert "shared" in by_name
    row = by_name["shared"]
    assert row["name"] == "shared"
    assert row["source"] == "defaults/main.yml + vars/main.yml override"
    assert row["is_ambiguous"] is True
    assert row["provenance_confidence"] == 0.80


def test_fsrc_variable_pipeline_collect_dynamic_include_var_tokens() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        pipeline_module = importlib.import_module(
            "prism.scanner_core.variable_pipeline"
        )
        tokens = pipeline_module.collect_dynamic_include_var_tokens(
            ["{{ include_vars_file }}", "{{ hostvars[inventory_hostname].role_file }}"],
            ignored_identifiers={"hostvars", "inventory_hostname"},
        )

    assert "include_vars_file" in tokens
    assert "role_file" in tokens
    assert "hostvars" not in tokens
