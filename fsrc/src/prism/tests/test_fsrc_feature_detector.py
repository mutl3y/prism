"""Focused fsrc tests for feature detector and task catalog parity foundations."""

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


def test_fsrc_feature_detector_detects_feature_counter_shape(tmp_path) -> None:
    role_path = tmp_path
    (role_path / "tasks").mkdir()
    (role_path / "handlers").mkdir()
    (role_path / "tasks" / "main.yml").write_text(
        """---
- name: include static
  include_tasks: more.yml

- name: include role static
  include_role:
    name: demo.role

- name: include role dynamic
  include_role:
    name: "{{ dynamic_role_name }}"

- name: module task
  ansible.builtin.debug:
    msg: hi
  become: true
  when: demo_enabled
  tags:
    - demo
  notify:
    - restart service
""",
        encoding="utf-8",
    )
    (role_path / "tasks" / "more.yml").write_text(
        """---
- name: nested module
  ansible.builtin.command: echo ok
""",
        encoding="utf-8",
    )

    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        feature_detector_module = importlib.import_module(
            "prism.scanner_core.feature_detector"
        )
        options = {
            "role_path": str(role_path),
            "exclude_path_patterns": None,
        }
        container = di_module.DIContainer(
            role_path=str(role_path),
            scan_options=options,
        )
        detector = feature_detector_module.FeatureDetector(
            container,
            str(role_path),
            options,
        )
        features = detector.detect()

    assert features["task_files_scanned"] == 2
    assert features["tasks_scanned"] == 5
    assert features["recursive_task_includes"] == 1
    assert features["privileged_tasks"] == 1
    assert features["conditional_tasks"] == 1
    assert features["tagged_tasks"] == 1
    assert features["included_role_calls"] == 1
    assert features["dynamic_included_role_calls"] == 1
    assert features["handlers_notified"] == "restart service"


def test_fsrc_feature_detector_task_catalog_shape_parity(tmp_path) -> None:
    role_path = tmp_path
    (role_path / "tasks").mkdir()
    (role_path / "handlers").mkdir()
    (role_path / "tasks" / "main.yml").write_text(
        """---
# prism~runbook: restart after update
- name: task one
  ansible.builtin.debug:
    msg: one

- name: include nested
  include_tasks: nested.yml
""",
        encoding="utf-8",
    )
    (role_path / "tasks" / "nested.yml").write_text(
        """---
- name: task two
  ansible.builtin.command: echo two
""",
        encoding="utf-8",
    )
    (role_path / "handlers" / "main.yml").write_text(
        """---
- name: restart service
  ansible.builtin.service:
    name: demo
    state: restarted
""",
        encoding="utf-8",
    )

    with _prefer_fsrc_prism_on_sys_path():
        feature_detector_module = importlib.import_module(
            "prism.scanner_core.feature_detector"
        )
        scanner_extract_module = importlib.import_module(
            "prism.scanner_extract.task_parser"
        )

        task_entries, handler_entries = (
            scanner_extract_module._collect_task_handler_catalog(str(role_path))
        )
        detector = feature_detector_module.FeatureDetector(
            di=object(),
            role_path=str(role_path),
            options={"role_path": str(role_path), "exclude_path_patterns": None},
        )
        catalog = detector.analyze_task_catalog()

    assert len(task_entries) == 3
    assert len(handler_entries) == 1
    assert set(task_entries[0]) == {
        "file",
        "name",
        "module",
        "parameters",
        "anchor",
        "runbook",
        "annotations",
    }
    assert set(handler_entries[0]) == {
        "file",
        "name",
        "module",
        "parameters",
        "anchor",
    }
    assert "tasks/main.yml" in catalog
    assert set(catalog["tasks/main.yml"]) == {
        "task_count",
        "async_count",
        "modules_used",
        "collections_used",
        "handlers_notified",
        "privileged_tasks",
        "conditional_tasks",
        "tagged_tasks",
    }
