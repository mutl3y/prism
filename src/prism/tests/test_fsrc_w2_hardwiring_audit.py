"""Wave W2 hardwiring-audit regression tests for fsrc lane."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "src"


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


def test_fsrc_variable_discovery_ignores_jinja_local_bindings(tmp_path) -> None:
    role_path = tmp_path
    (role_path / "tasks").mkdir()
    (role_path / "templates").mkdir()
    (role_path / "tasks" / "main.yml").write_text(
        "---\n- name: demo\n  debug:\n    msg: ok\n",
        encoding="utf-8",
    )
    (role_path / "templates" / "main.j2").write_text(
        "{% for item in users %}{{ item }} {{ owner }}{% endfor %}\n",
        encoding="utf-8",
    )

    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        discovery_module = importlib.import_module(
            "prism.scanner_core.variable_discovery"
        )
        bundle_resolver = importlib.import_module(
            "prism.scanner_plugins.bundle_resolver"
        )
        plugins_module = importlib.import_module("prism.scanner_plugins")
        options = {
            "role_path": str(role_path),
            "include_vars_main": True,
            "exclude_path_patterns": None,
        }
        container = di_module.DIContainer(
            role_path=str(role_path),
            scan_options=options,
            registry=plugins_module.DEFAULT_PLUGIN_REGISTRY,
        )
        bundle_resolver.ensure_prepared_policy_bundle(
            scan_options=options, di=container
        )
        discovery = discovery_module.VariableDiscovery(
            container,
            str(role_path),
            options,
        )
        referenced = discovery.discover_referenced()

    assert "users" in referenced
    assert "owner" in referenced
    assert "item" not in referenced


def test_fsrc_variable_discovery_collects_yaml_parse_failure_metadata(tmp_path) -> None:
    role_path = tmp_path
    (role_path / "defaults").mkdir()
    (role_path / "tasks").mkdir()
    (role_path / "defaults" / "main.yml").write_text(
        "bad: [\n",
        encoding="utf-8",
    )
    (role_path / "tasks" / "main.yml").write_text(
        "---\n- name: demo\n  debug:\n    msg: ok\n",
        encoding="utf-8",
    )

    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        discovery_module = importlib.import_module(
            "prism.scanner_core.variable_discovery"
        )
        bundle_resolver = importlib.import_module(
            "prism.scanner_plugins.bundle_resolver"
        )
        plugins_module = importlib.import_module("prism.scanner_plugins")
        options = {
            "role_path": str(role_path),
            "include_vars_main": True,
            "exclude_path_patterns": None,
        }
        container = di_module.DIContainer(
            role_path=str(role_path),
            scan_options=options,
            registry=plugins_module.DEFAULT_PLUGIN_REGISTRY,
        )
        bundle_resolver.ensure_prepared_policy_bundle(
            scan_options=options, di=container
        )
        discovery = discovery_module.VariableDiscovery(
            container,
            str(role_path),
            options,
        )
        _ = discovery.discover_static()

    failures = options.get("yaml_parse_failures")
    assert isinstance(failures, list)
    assert failures
    assert failures[0]["file"] == "defaults/main.yml"
    assert isinstance(failures[0].get("error"), str)
    assert failures[0]["error"]


def test_fsrc_task_file_traversal_exposes_unresolved_include_edges(tmp_path) -> None:
    role_path = tmp_path
    (role_path / "tasks").mkdir()
    (role_path / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: dynamic include\n"
        '  include_tasks: "{{ include_file }}"\n'
        "- name: static include\n"
        "  include_tasks: static.yml\n",
        encoding="utf-8",
    )
    (role_path / "tasks" / "static.yml").write_text(
        "---\n- name: nested\n  debug:\n    msg: nested\n",
        encoding="utf-8",
    )

    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        bundle_resolver = importlib.import_module(
            "prism.scanner_plugins.bundle_resolver"
        )
        plugins_module = importlib.import_module("prism.scanner_plugins")
        traversal_module = importlib.import_module(
            "prism.scanner_extract.task_file_traversal"
        )
        options: dict = {
            "role_path": str(role_path),
            "exclude_path_patterns": None,
        }
        container = di_module.DIContainer(
            role_path=str(role_path),
            scan_options=options,
            registry=plugins_module.DEFAULT_PLUGIN_REGISTRY,
        )
        bundle_resolver.ensure_prepared_policy_bundle(
            scan_options=options, di=container
        )
        task_files, unresolved_edges = (
            traversal_module._collect_task_files_with_unresolved_includes(
                role_path.resolve(),
                di=container,
            )
        )

    relpaths = {path.relative_to(role_path).as_posix() for path in task_files}
    assert relpaths == {"tasks/main.yml", "tasks/static.yml"}
    assert len(unresolved_edges) == 1
    assert unresolved_edges[0]["include_target"] == "{{ include_file }}"
    assert unresolved_edges[0]["task_file"] == "tasks/main.yml"


def test_fsrc_task_file_traversal_load_yaml_records_failure_metadata(tmp_path) -> None:
    role_path = tmp_path
    (role_path / "tasks").mkdir()
    bad_file = role_path / "tasks" / "broken.yml"
    bad_file.write_text("bad: [\n", encoding="utf-8")

    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        bundle_resolver = importlib.import_module(
            "prism.scanner_plugins.bundle_resolver"
        )
        plugins_module = importlib.import_module("prism.scanner_plugins")
        traversal_module = importlib.import_module(
            "prism.scanner_extract.task_file_traversal"
        )
        options: dict = {
            "role_path": str(role_path),
            "exclude_path_patterns": None,
        }
        container = di_module.DIContainer(
            role_path=str(role_path),
            scan_options=options,
            registry=plugins_module.DEFAULT_PLUGIN_REGISTRY,
        )
        bundle_resolver.ensure_prepared_policy_bundle(
            scan_options=options, di=container
        )
        failures: list[dict[str, object]] = []
        loaded = traversal_module._load_yaml_file(
            bad_file,
            yaml_failure_collector=failures,
            role_root=role_path.resolve(),
            di=container,
        )

    assert loaded is None
    assert failures
    assert failures[0]["file"] == "tasks/broken.yml"
