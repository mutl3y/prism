"""Focused fsrc tests for variable discovery and pipeline parity foundations."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

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
        scan_request = importlib.import_module("prism.scanner_core.scan_request")
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
        scan_request.ensure_prepared_policy_bundle(scan_options=options, di=container)
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


def test_fsrc_variable_discovery_routes_via_plugin_when_available() -> None:
    class _Plugin:
        def discover_static_variables(self, role_path: str, options: dict):
            return (
                {
                    "name": "plugin_static",
                    "type": "string",
                    "default": "value",
                    "source": "plugin",
                    "documented": True,
                    "required": False,
                    "secret": False,
                    "provenance_source_file": "plugin",
                    "provenance_line": None,
                    "provenance_confidence": 1.0,
                    "uncertainty_reason": None,
                    "is_unresolved": False,
                    "is_ambiguous": False,
                },
            )

        def discover_referenced_variables(
            self,
            role_path: str,
            options: dict,
            readme_content: str | None = None,
        ):
            return frozenset({"plugin_static", "plugin_unresolved"})

        def resolve_unresolved_variables(
            self,
            static_names,
            referenced,
            options: dict,
        ):
            return {"plugin_unresolved": "plugin resolver"}

    class _DI:
        def factory_variable_discovery_plugin(self) -> _Plugin:
            return _Plugin()

        def factory_variable_row_builder(self):
            raise AssertionError("builder should not be used when plugin is active")

    with _prefer_fsrc_prism_on_sys_path():
        discovery_module = importlib.import_module(
            "prism.scanner_core.variable_discovery"
        )
        discovery = discovery_module.VariableDiscovery(
            _DI(),
            "/tmp/role",
            {
                "include_vars_main": True,
                "exclude_path_patterns": None,
            },
        )
        static_rows = discovery.discover_static()
        referenced = discovery.discover_referenced()
        unresolved = discovery.resolve_unresolved()

    assert static_rows[0]["name"] == "plugin_static"
    assert "plugin_unresolved" in referenced
    assert unresolved["plugin_unresolved"] == "plugin resolver"


def test_fsrc_variable_discovery_prefers_prepared_policy_bundle(
    tmp_path,
    monkeypatch,
) -> None:
    role_path = tmp_path
    (role_path / "tasks").mkdir()
    (role_path / "vars").mkdir()
    (role_path / "vars" / "extra.yml").write_text(
        "---\nfrom_prepared_include: true\n",
        encoding="utf-8",
    )
    (role_path / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: demo\n"
        "  prepared_include_vars: extra.yml\n"
        '  debug:\n    msg: "{{ from_prepared_jinja }}"\n',
        encoding="utf-8",
    )

    class _PreparedTaskLinePolicy:
        TASK_INCLUDE_KEYS = {"include_tasks"}
        ROLE_INCLUDE_KEYS = {"include_role"}
        INCLUDE_VARS_KEYS = {"prepared_include_vars"}
        SET_FACT_KEYS = {"set_fact"}
        TASK_BLOCK_KEYS = {"block"}
        TASK_META_KEYS = {"meta"}

        @staticmethod
        def detect_task_module(_task: dict) -> str:
            return "debug"

    class _PreparedJinjaPolicy:
        @staticmethod
        def collect_undeclared_jinja_variables(_text: str) -> set[str]:
            return {"from_prepared_jinja"}

    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        scan_request = importlib.import_module("prism.scanner_core.scan_request")
        discovery_module = importlib.import_module(
            "prism.scanner_core.variable_discovery"
        )

        monkeypatch.setattr(
            discovery_module,
            "resolve_task_line_parsing_policy_plugin",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("task-line resolver should not be called")
            ),
            raising=False,
        )
        monkeypatch.setattr(
            discovery_module,
            "resolve_jinja_analysis_policy_plugin",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("jinja resolver should not be called")
            ),
            raising=False,
        )

        options = {
            "role_path": str(role_path),
            "include_vars_main": True,
            "exclude_path_patterns": None,
            "vars_seed_paths": None,
            "ignore_unresolved_internal_underscore_references": False,
            "prepared_policy_bundle": {
                "task_line_parsing": _PreparedTaskLinePolicy(),
                "jinja_analysis": _PreparedJinjaPolicy(),
            },
        }
        container = di_module.DIContainer(
            role_path=str(role_path),
            scan_options=options,
        )
        scan_request.ensure_prepared_policy_bundle(scan_options=options, di=container)
        discovery = discovery_module.VariableDiscovery(
            container,
            str(role_path),
            options,
        )

        static_rows = discovery.discover_static()
        referenced = discovery.discover_referenced()

    static_names = {row["name"] for row in static_rows}
    assert "from_prepared_include" in static_names
    assert "from_prepared_jinja" in referenced


def test_fsrc_variable_discovery_requires_ingress_prepared_policy_bundle(
    tmp_path,
) -> None:
    role_path = tmp_path
    (role_path / "tasks").mkdir()
    (role_path / "vars").mkdir()
    (role_path / "vars" / "extra.yml").write_text(
        "---\nfrom_scan_request_include: true\n",
        encoding="utf-8",
    )
    (role_path / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: demo\n"
        "  scan_request_include_vars: extra.yml\n"
        '  debug:\n    msg: "{{ from_scan_request_jinja }}"\n',
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
            role_path=str(role_path),
            scan_options=options,
        )
        discovery = discovery_module.VariableDiscovery(
            container,
            str(role_path),
            options,
        )

        with pytest.raises(ValueError, match="prepared_policy_bundle"):
            discovery.discover_static()

    assert "prepared_policy_bundle" not in options


def test_fsrc_variable_discovery_discover_referenced_requires_ingress_prepared_jinja_policy(
    tmp_path,
) -> None:
    role_path = tmp_path
    (role_path / "tasks").mkdir()
    (role_path / "tasks" / "main.yml").write_text(
        '---\n- name: demo\n  debug:\n    msg: "{{ missing_ingress_policy }}"\n',
        encoding="utf-8",
    )
    task_line_policy = object()

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
            "prepared_policy_bundle": {
                "task_line_parsing": task_line_policy,
            },
        }
        container = di_module.DIContainer(
            role_path=str(role_path),
            scan_options=options,
        )
        discovery = discovery_module.VariableDiscovery(
            container,
            str(role_path),
            options,
        )

        with pytest.raises(
            ValueError,
            match=(
                "prepared_policy_bundle.jinja_analysis must be provided before "
                "VariableDiscovery native execution"
            ),
        ):
            discovery.discover_referenced()

    assert options["prepared_policy_bundle"] == {"task_line_parsing": task_line_policy}
