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
        scan_request = importlib.import_module("prism.scanner_core.scan_request")
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
        scan_request.ensure_prepared_policy_bundle(scan_options=options, di=container)
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
        di_module = importlib.import_module("prism.scanner_core.di")
        scan_request = importlib.import_module("prism.scanner_core.scan_request")
        feature_detector_module = importlib.import_module(
            "prism.scanner_core.feature_detector"
        )
        scanner_extract_module = importlib.import_module(
            "prism.scanner_extract.task_parser"
        )
        options: dict = {
            "role_path": str(role_path),
            "exclude_path_patterns": None,
        }
        container = di_module.DIContainer(
            role_path=str(role_path),
            scan_options=options,
        )
        scan_request.ensure_prepared_policy_bundle(scan_options=options, di=container)

        task_entries, handler_entries = (
            scanner_extract_module._collect_task_handler_catalog(
                str(role_path), di=container
            )
        )
        detector = feature_detector_module.FeatureDetector(
            di=container,
            role_path=str(role_path),
            options=options,
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


def test_fsrc_feature_detector_routes_via_plugin_when_available() -> None:
    class _Plugin:
        def detect_features(self, role_path: str, options: dict) -> dict:
            return {
                "task_files_scanned": 99,
                "tasks_scanned": 77,
                "recursive_task_includes": 0,
                "unique_modules": "plugin.module",
                "external_collections": "none",
                "handlers_notified": "none",
                "privileged_tasks": 0,
                "conditional_tasks": 0,
                "tagged_tasks": 0,
                "included_role_calls": 0,
                "included_roles": "none",
                "dynamic_included_role_calls": 0,
                "dynamic_included_roles": "none",
                "disabled_task_annotations": 0,
                "yaml_like_task_annotations": 0,
            }

        def analyze_task_catalog(self, role_path: str, options: dict) -> dict:
            return {
                "plugin/tasks.yml": {
                    "task_count": 1,
                    "async_count": 0,
                    "modules_used": ["plugin.module"],
                    "collections_used": [],
                    "handlers_notified": [],
                    "privileged_tasks": 0,
                    "conditional_tasks": 0,
                    "tagged_tasks": 0,
                }
            }

    class _DI:
        def factory_feature_detection_plugin(self) -> _Plugin:
            return _Plugin()

    with _prefer_fsrc_prism_on_sys_path():
        feature_detector_module = importlib.import_module(
            "prism.scanner_core.feature_detector"
        )
        detector = feature_detector_module.FeatureDetector(
            di=_DI(),
            role_path="/tmp/role",
            options={"exclude_path_patterns": None},
        )
        features = detector.detect()
        catalog = detector.analyze_task_catalog()

    assert features["task_files_scanned"] == 99
    assert features["unique_modules"] == "plugin.module"
    assert "plugin/tasks.yml" in catalog


def test_fsrc_feature_detector_annotation_hot_path_uses_canonical_comment_doc_marker_prefix(
    monkeypatch,
    tmp_path: Path,
) -> None:
    role_path = tmp_path
    (role_path / "tasks").mkdir()
    (role_path / "tasks" / "main.yml").write_text(
        "# ignored\n- name: demo\n  debug:\n    msg: ok\n",
        encoding="utf-8",
    )

    captured_prefixes: list[str] = []

    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        feature_detector_module = importlib.import_module(
            "prism.scanner_core.feature_detector"
        )
        adapters_module = importlib.import_module(
            "prism.scanner_core.task_extract_adapters"
        )

        def _capture_extract(
            _raw_lines,
            *,
            marker_prefix: str = "prism",
            include_task_index: bool = False,
            di=None,
        ):
            del include_task_index, di
            captured_prefixes.append(marker_prefix)
            return [], {}

        monkeypatch.setattr(
            adapters_module, "_extract_task_annotations_for_file", _capture_extract
        )

        options = {
            "role_path": str(role_path),
            "exclude_path_patterns": None,
            "comment_doc_marker_prefix": "canonical.hot.path",
            "policy_context": {
                "comment_doc": {"marker": {"prefix": "nested.ignore"}},
            },
        }
        container = di_module.DIContainer(
            role_path=str(role_path),
            scan_options=options,
        )
        scan_request_module = importlib.import_module("prism.scanner_core.scan_request")
        scan_request_module.ensure_prepared_policy_bundle(
            scan_options=options, di=container
        )
        detector = feature_detector_module.FeatureDetector(
            container,
            str(role_path),
            options,
        )
        detector.detect()

    assert captured_prefixes == ["canonical.hot.path"]


def test_fsrc_feature_detector_collect_task_handler_catalog_hot_path_uses_canonical_comment_doc_marker_prefix(
    monkeypatch,
    tmp_path: Path,
) -> None:
    role_path = tmp_path
    (role_path / "tasks").mkdir()
    (role_path / "handlers").mkdir()

    captured_prefixes: list[str] = []

    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        feature_detector_module = importlib.import_module(
            "prism.scanner_core.feature_detector"
        )
        adapters_module = importlib.import_module(
            "prism.scanner_core.task_extract_adapters"
        )

        def _capture_catalog(
            _role_path,
            exclude_paths=None,
            marker_prefix: str = "prism",
            *,
            di=None,
        ):
            del exclude_paths, di
            captured_prefixes.append(marker_prefix)
            return [], []

        monkeypatch.setattr(
            adapters_module, "_collect_task_handler_catalog", _capture_catalog
        )

        options = {
            "role_path": str(role_path),
            "exclude_path_patterns": None,
            "comment_doc_marker_prefix": "canonical.catalog",
            "policy_context": {
                "comment_doc": {"marker": {"prefix": "nested.ignore"}},
            },
        }
        container = di_module.DIContainer(
            role_path=str(role_path),
            scan_options=options,
        )
        scan_request_module = importlib.import_module("prism.scanner_core.scan_request")
        scan_request_module.ensure_prepared_policy_bundle(
            scan_options=options, di=container
        )
        detector = feature_detector_module.FeatureDetector(
            container,
            str(role_path),
            options,
        )
        detector.collect_task_handler_catalog()

    assert captured_prefixes == ["canonical.catalog"]
