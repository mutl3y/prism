"""Focused parity checks for fsrc scanner_extract compatibility exports."""

from __future__ import annotations

import importlib
import re
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[4]
SRC_SOURCE_ROOT = PROJECT_ROOT / "src"
FSRC_SOURCE_ROOT = PROJECT_ROOT / "fsrc" / "src"


@contextmanager
def _prefer_prism_lane(lane_root: Path) -> Iterator[None]:
    original_path = list(sys.path)
    original_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == "prism" or key.startswith("prism.")
    }
    lane_roots = {SRC_SOURCE_ROOT.resolve(), FSRC_SOURCE_ROOT.resolve()}

    try:
        sys.path[:] = [str(lane_root.resolve())] + [
            path for path in original_path if Path(path).resolve() not in lane_roots
        ]
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


def _build_dynamic_fixture_role(role_root: Path) -> None:
    (role_root / "tasks").mkdir(parents=True)
    (role_root / "defaults").mkdir(parents=True)
    (role_root / "molecule" / "default").mkdir(parents=True)

    (role_root / "tasks" / "main.yml").write_text(
        """---
# prism~warning: first warning
# and continuation
- name: dynamic task include
  include_tasks: "{{ task_selector }}.yml"

- name: dynamic role include
  include_role:
    name: "{{ role_selector }}"

- name: static include task
  include_tasks: setup.yml
""",
        encoding="utf-8",
    )
    (role_root / "tasks" / "setup.yml").write_text(
        """---
# prism~note: setup note
- name: setup
  ansible.builtin.debug:
    msg: ok
""",
        encoding="utf-8",
    )
    (role_root / "defaults" / "main.yml").write_text(
        "# prism~deprecated: use role_selector instead\n",
        encoding="utf-8",
    )
    (role_root / "molecule" / "default" / "molecule.yml").write_text(
        """---
driver:
  name: docker
verifier:
  name: ansible
platforms:
  - name: instance
    image: docker.io/library/alpine:3.20
""",
        encoding="utf-8",
    )


def _snapshot_scanner_extract(lane_root: Path, role_path: str) -> dict[str, object]:
    with _prefer_prism_lane(lane_root):
        module = importlib.import_module("prism.scanner_extract")
        return {
            "role_notes": module.extract_role_notes_from_comments(role_path),
            "molecule_scenarios": module.collect_molecule_scenarios(role_path),
            "dynamic_task_includes": module.collect_unconstrained_dynamic_task_includes(
                role_path
            ),
            "dynamic_role_includes": module.collect_unconstrained_dynamic_role_includes(
                role_path
            ),
        }


def test_fsrc_scanner_extract_compatibility_exports_match_src_behavior(
    tmp_path: Path,
) -> None:
    role_root = tmp_path / "fixture-role"
    _build_dynamic_fixture_role(role_root)
    role_path = str(role_root)

    src_snapshot = _snapshot_scanner_extract(SRC_SOURCE_ROOT, role_path)
    fsrc_snapshot = _snapshot_scanner_extract(FSRC_SOURCE_ROOT, role_path)

    assert fsrc_snapshot == src_snapshot

    role_notes = fsrc_snapshot["role_notes"]
    assert isinstance(role_notes, dict)
    assert role_notes["warnings"] == ["first warning and continuation"]

    molecule_scenarios = fsrc_snapshot["molecule_scenarios"]
    assert isinstance(molecule_scenarios, list)
    assert molecule_scenarios[0]["name"] == "default"

    dynamic_task_includes = fsrc_snapshot["dynamic_task_includes"]
    assert dynamic_task_includes == [
        {
            "file": "tasks/main.yml",
            "task": "dynamic task include",
            "module": "include_tasks",
            "target": "{{ task_selector }}.yml",
        }
    ]

    dynamic_role_includes = fsrc_snapshot["dynamic_role_includes"]
    assert dynamic_role_includes == [
        {
            "file": "tasks/main.yml",
            "task": "dynamic role include",
            "module": "include_role",
            "target": "{{ role_selector }}",
        }
    ]


def test_task_line_parsing_marker_helpers_route_through_defaults() -> None:
    with _prefer_prism_lane(FSRC_SOURCE_ROOT):
        module = importlib.import_module("prism.scanner_extract.task_line_parsing")
        marker_utils = importlib.import_module(
            "prism.scanner_plugins.parsers.comment_doc.marker_utils"
        )
        default_prefix = marker_utils.DEFAULT_DOC_MARKER_PREFIX

        normalized = module._normalize_marker_prefix(None)
        marker_re = module.get_marker_line_re(default_prefix)

    assert normalized == default_prefix
    assert isinstance(marker_re, re.Pattern)


def test_w3_t01_task_catalog_assembly_no_longer_owns_role_notes_parsing() -> None:
    with _prefer_prism_lane(FSRC_SOURCE_ROOT):
        module = importlib.import_module("prism.scanner_extract.task_catalog_assembly")

    assert not hasattr(module, "_extract_role_notes_from_comments")
