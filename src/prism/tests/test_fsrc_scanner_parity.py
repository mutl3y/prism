"""Scanner-core parity matrix checks between src and fsrc lanes."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_LANE_ROOT = PROJECT_ROOT / "src"
FSRC_LANE_ROOT = PROJECT_ROOT / "fsrc" / "src"

_VARIABLE_ROW_REQUIRED_KEYS = {
    "name",
    "type",
    "default",
    "source",
    "documented",
    "required",
    "secret",
    "provenance_source_file",
    "provenance_line",
    "provenance_confidence",
    "is_unresolved",
    "is_ambiguous",
}


@contextmanager
def _prefer_prism_lane(lane_root: Path) -> Iterator[None]:
    original_path = list(sys.path)
    original_modules = {
        key: value
        for key, value in sys.modules.items()
        if key == "prism" or key.startswith("prism.")
    }
    lane_roots = {SRC_LANE_ROOT.resolve(), FSRC_LANE_ROOT.resolve()}

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


def _canonical_scan_options(role_path: str) -> dict[str, Any]:
    return {
        "role_path": role_path,
        "role_name_override": None,
        "readme_config_path": None,
        "include_vars_main": True,
        "exclude_path_patterns": None,
        "detailed_catalog": False,
        "include_task_parameters": True,
        "include_task_runbooks": True,
        "inline_task_runbooks": True,
        "include_collection_checks": True,
        "keep_unknown_style_sections": True,
        "adopt_heading_mode": None,
        "vars_seed_paths": None,
        "style_readme_path": None,
        "style_source_path": None,
        "style_guide_skeleton": False,
        "compare_role_path": None,
        "fail_on_unconstrained_dynamic_includes": None,
        "fail_on_yaml_like_task_annotations": None,
        "ignore_unresolved_internal_underscore_references": False,
    }


def _fixture_role_path(role_name: str) -> str:
    return str(PROJECT_ROOT / "src" / "prism" / "tests" / "roles" / role_name)


def _variable_discovery_snapshot(lane_root: Path, role_path: str) -> dict[str, Any]:
    options = _canonical_scan_options(role_path)
    with _prefer_prism_lane(lane_root):
        di_module = importlib.import_module("prism.scanner_core.di")
        discovery_module = importlib.import_module(
            "prism.scanner_core.variable_discovery"
        )

        container = di_module.DIContainer(role_path=role_path, scan_options=options)
        discovery = discovery_module.VariableDiscovery(container, role_path, options)

        static_rows = discovery.discover_static()
        referenced = discovery.discover_referenced()
        discovered_rows = discovery.discover()

    unresolved_names = sorted(
        row["name"] for row in discovered_rows if row.get("is_unresolved")
    )
    set_fact_names = sorted(
        row["name"] for row in static_rows if row.get("source") == "set_fact"
    )
    row_by_name = {row["name"]: row for row in discovered_rows}

    return {
        "static_count": len(static_rows),
        "referenced_count": len(referenced),
        "discovered_count": len(discovered_rows),
        "unresolved_names": unresolved_names,
        "set_fact_names": set_fact_names,
        "row_by_name": row_by_name,
    }


def _write_synthetic_role(role_root: Path) -> None:
    role_root.mkdir(parents=True, exist_ok=True)
    (role_root / "defaults").mkdir()
    (role_root / "vars").mkdir()
    (role_root / "tasks").mkdir()
    (role_root / "handlers").mkdir()

    (role_root / "defaults" / "main.yml").write_text(
        "---\ndefault_only: from_defaults\n",
        encoding="utf-8",
    )
    (role_root / "vars" / "main.yml").write_text(
        "---\nvars_only: from_vars\n",
        encoding="utf-8",
    )
    (role_root / "tasks" / "main.yml").write_text(
        """---
- name: include extra
  include_tasks: extra.yml

- name: include role static
  include_role:
    name: demo.role

- name: include role dynamic
  include_role:
    name: "{{ dyn_role }}"

- name: main task
  ansible.builtin.debug:
    msg: "{{ default_only }} {{ runtime_only }}"
  become: true
  when: default_only is defined
  tags:
    - demo
  notify:
    - restart service
""",
        encoding="utf-8",
    )
    (role_root / "tasks" / "extra.yml").write_text(
        "---\n- name: nested\n  ansible.builtin.command: echo ok\n",
        encoding="utf-8",
    )
    (role_root / "handlers" / "main.yml").write_text(
        "---\n- name: restart service\n  ansible.builtin.debug:\n    msg: restart\n",
        encoding="utf-8",
    )
    (role_root / "README.md").write_text(
        "Role input: {{ readme_input }}\n",
        encoding="utf-8",
    )


class _DiscoveryStub:
    def __init__(self, payload: tuple[Any, ...] | Exception) -> None:
        self._payload = payload

    def discover(self) -> tuple[Any, ...]:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class _FeatureStub:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def detect(self) -> dict[str, Any]:
        return dict(self._payload)


class _PreparedTaskLinePolicy:
    TASK_INCLUDE_KEYS = {"include_tasks"}
    ROLE_INCLUDE_KEYS = {"include_role"}
    INCLUDE_VARS_KEYS = {"include_vars"}
    SET_FACT_KEYS = {"set_fact"}
    TASK_BLOCK_KEYS = {"block"}
    TASK_META_KEYS = {"meta"}

    @staticmethod
    def detect_task_module(_task: dict[str, Any]) -> str:
        return "debug"


class _PreparedJinjaPolicy:
    @staticmethod
    def collect_undeclared_jinja_variables(_text: str) -> set[str]:
        return set()


def _prepared_policy_bundle() -> dict[str, Any]:
    return {
        "task_line_parsing": _PreparedTaskLinePolicy(),
        "jinja_analysis": _PreparedJinjaPolicy(),
    }


def test_w2_t05_variable_discovery_parity_matrix(tmp_path: Path) -> None:
    role_root = tmp_path / "role"
    _write_synthetic_role(role_root)
    role_path = str(role_root)
    options = _canonical_scan_options(role_path)

    lane_summaries: dict[str, dict[str, Any]] = {}
    for lane_name, lane_root in (
        ("src", SRC_LANE_ROOT),
        ("fsrc", FSRC_LANE_ROOT),
    ):
        with _prefer_prism_lane(lane_root):
            di_module = importlib.import_module("prism.scanner_core.di")
            discovery_module = importlib.import_module(
                "prism.scanner_core.variable_discovery"
            )

            container = di_module.DIContainer(role_path=role_path, scan_options=options)
            discovery = discovery_module.VariableDiscovery(
                container, role_path, options
            )

            static_rows = discovery.discover_static()
            referenced_names = discovery.discover_referenced()
            discovered_rows = discovery.discover()

        lane_summaries[lane_name] = {
            "static_names": {row["name"] for row in static_rows},
            "referenced_names": set(referenced_names),
            "unresolved_names": {
                row["name"] for row in discovered_rows if row.get("is_unresolved")
            },
            "runtime_row": next(
                (row for row in discovered_rows if row.get("name") == "runtime_only"),
                None,
            ),
            "all_rows_have_required_keys": all(
                _VARIABLE_ROW_REQUIRED_KEYS.issubset(row.keys())
                for row in discovered_rows
            ),
        }

    for lane_name, summary in lane_summaries.items():
        assert summary[
            "all_rows_have_required_keys"
        ], f"{lane_name} lane returned variable rows missing required keys"
        assert "default_only" in summary["static_names"]
        assert "runtime_only" in summary["referenced_names"]
        assert "runtime_only" in summary["unresolved_names"]
        assert summary["runtime_row"] is not None
        assert bool(summary["runtime_row"].get("uncertainty_reason"))

    assert (
        lane_summaries["src"]["static_names"] == lane_summaries["fsrc"]["static_names"]
    )


def test_w2_t05_feature_detector_parity_matrix(tmp_path: Path) -> None:
    role_root = tmp_path / "role"
    _write_synthetic_role(role_root)
    role_path = str(role_root)
    options = _canonical_scan_options(role_path)

    lane_features: dict[str, dict[str, Any]] = {}
    lane_catalogs: dict[str, dict[str, Any]] = {}

    for lane_name, lane_root in (
        ("src", SRC_LANE_ROOT),
        ("fsrc", FSRC_LANE_ROOT),
    ):
        with _prefer_prism_lane(lane_root):
            di_module = importlib.import_module("prism.scanner_core.di")
            feature_module = importlib.import_module(
                "prism.scanner_core.feature_detector"
            )

            container = di_module.DIContainer(role_path=role_path, scan_options=options)
            detector = feature_module.FeatureDetector(container, role_path, options)

            lane_features[lane_name] = detector.detect()
            lane_catalogs[lane_name] = detector.analyze_task_catalog()

    expected_feature_keys = {
        "task_files_scanned",
        "tasks_scanned",
        "recursive_task_includes",
        "unique_modules",
        "external_collections",
        "handlers_notified",
        "privileged_tasks",
        "conditional_tasks",
        "tagged_tasks",
        "included_role_calls",
        "included_roles",
        "dynamic_included_role_calls",
        "dynamic_included_roles",
        "disabled_task_annotations",
        "yaml_like_task_annotations",
    }
    expected_catalog_keys = {
        "task_count",
        "async_count",
        "modules_used",
        "collections_used",
        "handlers_notified",
        "privileged_tasks",
        "conditional_tasks",
        "tagged_tasks",
    }

    for lane_name in ("src", "fsrc"):
        features = lane_features[lane_name]
        assert expected_feature_keys.issubset(features.keys())
        assert features["task_files_scanned"] >= 2
        assert features["tasks_scanned"] >= 5
        assert features["privileged_tasks"] >= 1
        assert features["conditional_tasks"] >= 1
        assert features["tagged_tasks"] >= 1

        catalog = lane_catalogs[lane_name]
        assert "tasks/main.yml" in catalog
        assert expected_catalog_keys.issubset(catalog["tasks/main.yml"].keys())

    assert set(lane_features["src"].keys()) == set(lane_features["fsrc"].keys())


def test_w2_t05_scanner_context_payload_shape_parity() -> None:
    options = _canonical_scan_options("/tmp/role")
    options["prepared_policy_bundle"] = _prepared_policy_bundle()
    payload_template = {
        "rp": "/tmp/role",
        "role_name": "demo",
        "description": "demo role",
        "requirements_display": [{"name": "ansible-core"}],
        "undocumented_default_filters": [],
        "display_variables": {"demo_var": {"default": "x"}},
        "metadata": {},
    }
    lane_payloads: dict[str, dict[str, Any]] = {}

    for lane_name, lane_root in (
        ("src", SRC_LANE_ROOT),
        ("fsrc", FSRC_LANE_ROOT),
    ):
        with _prefer_prism_lane(lane_root):
            di_module = importlib.import_module("prism.scanner_core.di")
            scanner_context_module = importlib.import_module(
                "prism.scanner_core.scanner_context"
            )

            container = di_module.DIContainer(
                role_path="/tmp/role", scan_options=options
            )
            container.inject_mock_variable_discovery(_DiscoveryStub(({"name": "x"},)))
            container.inject_mock_feature_detector(
                _FeatureStub({"task_files_scanned": 1, "tasks_scanned": 2})
            )
            context = scanner_context_module.ScannerContext(
                di=container,
                role_path="/tmp/role",
                scan_options=options,
                prepare_scan_context_fn=lambda _scan_options: dict(payload_template),
            )
            lane_payloads[lane_name] = context.orchestrate_scan()

    expected_output_keys = {
        "role_name",
        "description",
        "display_variables",
        "requirements_display",
        "undocumented_default_filters",
        "metadata",
    }
    for lane_name, payload in lane_payloads.items():
        assert set(payload.keys()) == expected_output_keys
        assert payload["role_name"] == "demo"
        assert payload["metadata"]["features"]["task_files_scanned"] == 1

    assert set(lane_payloads["src"]["metadata"].keys()) == set(
        lane_payloads["fsrc"]["metadata"].keys()
    )


def test_w2_t05_scanner_context_error_envelope_parity() -> None:
    options = _canonical_scan_options("/tmp/role")
    options["strict_phase_failures"] = False
    options["prepared_policy_bundle"] = _prepared_policy_bundle()
    payload_template = {
        "rp": "/tmp/role",
        "role_name": "demo",
        "description": "demo role",
        "requirements_display": [],
        "undocumented_default_filters": [],
        "display_variables": {},
        "metadata": {},
    }
    lane_metadata: dict[str, dict[str, Any]] = {}

    for lane_name, lane_root in (
        ("src", SRC_LANE_ROOT),
        ("fsrc", FSRC_LANE_ROOT),
    ):
        with _prefer_prism_lane(lane_root):
            di_module = importlib.import_module("prism.scanner_core.di")
            errors_module = importlib.import_module("prism.errors")
            scanner_context_module = importlib.import_module(
                "prism.scanner_core.scanner_context"
            )

            container = di_module.DIContainer(
                role_path="/tmp/role", scan_options=options
            )
            container.inject_mock_variable_discovery(
                _DiscoveryStub(
                    errors_module.PrismRuntimeError(
                        code="role_scan_runtime_error",
                        category="runtime",
                        message="boom",
                    )
                )
            )
            container.inject_mock_feature_detector(
                _FeatureStub({"task_files_scanned": 0, "tasks_scanned": 0})
            )

            context = scanner_context_module.ScannerContext(
                di=container,
                role_path="/tmp/role",
                scan_options=options,
                prepare_scan_context_fn=lambda _scan_options: dict(payload_template),
            )
            lane_metadata[lane_name] = context.orchestrate_scan()["metadata"]

    for lane_name, metadata in lane_metadata.items():
        assert metadata["scan_degraded"] is True
        assert isinstance(metadata["scan_errors"], list)
        assert metadata["scan_errors"]
        first = metadata["scan_errors"][0]
        assert set(first.keys()) == {"phase", "error_type", "message"}
        assert first["phase"] == "discovery"
        assert first["error_type"] == "PrismRuntimeError"
        assert "role_scan_runtime_error" in first["message"]

    assert set(lane_metadata["src"]["scan_errors"][0].keys()) == set(
        lane_metadata["fsrc"]["scan_errors"][0].keys()
    )


def test_w2_t05_fixture_backed_base_role_variable_discovery_parity() -> None:
    role_path = _fixture_role_path("base_mock_role")
    src_snapshot = _variable_discovery_snapshot(SRC_LANE_ROOT, role_path)
    fsrc_snapshot = _variable_discovery_snapshot(FSRC_LANE_ROOT, role_path)

    assert fsrc_snapshot["static_count"] == src_snapshot["static_count"]
    assert fsrc_snapshot["unresolved_names"] == src_snapshot["unresolved_names"]
    assert fsrc_snapshot["referenced_count"] == src_snapshot["referenced_count"]

    for expected in (
        "required_input_var",
        "required_endpoint",
        "required_api_token",
        "some_other_var",
    ):
        row = fsrc_snapshot["row_by_name"][expected]
        assert row["is_unresolved"] is True
        assert isinstance(row.get("uncertainty_reason"), str)
        assert bool(row.get("uncertainty_reason"))


def test_w2_t05_fixture_backed_enhanced_role_variable_discovery_parity() -> None:
    role_path = _fixture_role_path("enhanced_mock_role")
    src_snapshot = _variable_discovery_snapshot(SRC_LANE_ROOT, role_path)
    fsrc_snapshot = _variable_discovery_snapshot(FSRC_LANE_ROOT, role_path)

    assert fsrc_snapshot["static_count"] == src_snapshot["static_count"]
    assert fsrc_snapshot["unresolved_names"] == src_snapshot["unresolved_names"]

    for expected in ("mock_role_debug", "mock_role_configure_ini"):
        row = fsrc_snapshot["row_by_name"][expected]
        assert row["source"] == "referenced"
        assert row["is_unresolved"] is True


def test_w2_t05_fixture_backed_dynamic_role_set_fact_parity() -> None:
    role_path = _fixture_role_path("test_dynamic_role")
    src_snapshot = _variable_discovery_snapshot(SRC_LANE_ROOT, role_path)
    fsrc_snapshot = _variable_discovery_snapshot(FSRC_LANE_ROOT, role_path)

    assert fsrc_snapshot["static_count"] == src_snapshot["static_count"]
    assert fsrc_snapshot["set_fact_names"] == src_snapshot["set_fact_names"]
    assert fsrc_snapshot["unresolved_names"] == src_snapshot["unresolved_names"]

    for variable_name in fsrc_snapshot["set_fact_names"]:
        row = fsrc_snapshot["row_by_name"][variable_name]
        assert row["source"] == "set_fact"
        assert row["type"] == "dynamic"
        assert row["is_ambiguous"] is True
