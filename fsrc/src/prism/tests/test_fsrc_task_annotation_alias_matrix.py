"""Focused alias-matrix checks for task annotation parsing via scanner_extract shims."""

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


def _alias_matrix_lines() -> list[str]:
    return [
        "# prism ~ task: Deploy service | notes: notes value",
        "# prism ~ task: Deploy service | note: note value",
        "# prism ~ task: Deploy service | additional: additional value",
        "# prism ~ task: Deploy service | additionals: additionals value",
        "# prism ~ task: Deploy service | deprecation: deprecated value",
        "# prism ~ task: Deploy service | deprecations: deprecated plural value",
        "- name: Deploy service",
    ]


def test_task_annotation_alias_matrix_via_task_annotation_parsing_shim() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        bundle_resolver = importlib.import_module(
            "prism.scanner_plugins.bundle_resolver"
        )
        module = importlib.import_module(
            "prism.scanner_extract.task_annotation_parsing"
        )
        options: dict = {"role_path": "/tmp", "exclude_path_patterns": None}
        container = di_module.DIContainer(role_path="/tmp", scan_options=options)
        bundle_resolver.ensure_prepared_policy_bundle(
            scan_options=options, di=container
        )
        marker_prefix = options["prepared_policy_bundle"]["comment_doc_marker_prefix"]
        implicit, explicit = module._extract_task_annotations_for_file(
            _alias_matrix_lines(), marker_prefix=marker_prefix, di=container
        )

    assert implicit == []
    deploy_annotations = explicit["Deploy service"]
    assert [item["kind"] for item in deploy_annotations] == [
        "note",
        "note",
        "additional",
        "additional",
        "note",
        "note",
    ]
    assert [item["text"] for item in deploy_annotations] == [
        "notes value",
        "note value",
        "additional value",
        "additionals value",
        "deprecation: deprecated value",
        "deprecations: deprecated plural value",
    ]


def test_task_annotation_alias_matrix_via_task_parser_shim_exports() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        di_module = importlib.import_module("prism.scanner_core.di")
        bundle_resolver = importlib.import_module(
            "prism.scanner_plugins.bundle_resolver"
        )
        parser_module = importlib.import_module("prism.scanner_extract.task_parser")
        options: dict = {"role_path": "/tmp", "exclude_path_patterns": None}
        container = di_module.DIContainer(role_path="/tmp", scan_options=options)
        bundle_resolver.ensure_prepared_policy_bundle(
            scan_options=options, di=container
        )
        marker_prefix = options["prepared_policy_bundle"]["comment_doc_marker_prefix"]
        implicit, explicit = parser_module._extract_task_annotations_for_file(
            _alias_matrix_lines(), marker_prefix=marker_prefix, di=container
        )

    assert implicit == []
    deploy_annotations = explicit["Deploy service"]
    assert [item["kind"] for item in deploy_annotations] == [
        "note",
        "note",
        "additional",
        "additional",
        "note",
        "note",
    ]
