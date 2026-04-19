"""Focused integration regressions for Gilfoyle runtime blocker remediation."""

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


def _build_role_with_nested_task_include(role_path: Path) -> None:
    (role_path / "tasks").mkdir(parents=True)
    (role_path / "tasks" / "main.yml").write_text(
        "---\n" "- name: include nested\n" "  include_tasks: nested.yml\n",
        encoding="utf-8",
    )
    (role_path / "tasks" / "nested.yml").write_text(
        "---\n" "- name: nested task\n" "  debug:\n" '    msg: "{{ nested_ref }}"\n',
        encoding="utf-8",
    )
    (role_path / "README.md").write_text("Role nested include demo\n", encoding="utf-8")


def _build_role_with_custom_include_vars_key(role_path: Path) -> None:
    (role_path / "tasks").mkdir(parents=True)
    (role_path / "vars").mkdir(parents=True)
    (role_path / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: include vars via policy-defined key\n"
        "  custom_include_vars:\n"
        "    file: policy_vars.yml\n",
        encoding="utf-8",
    )
    (role_path / "vars" / "policy_vars.yml").write_text(
        "---\npolicy_loaded_var: 42\n",
        encoding="utf-8",
    )
    (role_path / "README.md").write_text(
        "Role policy include vars demo\n", encoding="utf-8"
    )


def _build_role_with_dynamic_include(role_path: Path) -> None:
    (role_path / "tasks").mkdir(parents=True)
    (role_path / "tasks" / "main.yml").write_text(
        "---\n" "- name: dynamic include\n" '  include_tasks: "{{ include_target }}"\n',
        encoding="utf-8",
    )
    (role_path / "README.md").write_text(
        "Role dynamic include demo\n", encoding="utf-8"
    )


def _build_role_with_yaml_like_task_annotation(role_path: Path) -> None:
    (role_path / "tasks").mkdir(parents=True)
    (role_path / "tasks" / "main.yml").write_text(
        "---\n"
        "# prism~runbook: key: value\n"
        "- name: demo\n"
        "  debug:\n"
        "    msg: ok\n",
        encoding="utf-8",
    )
    (role_path / "README.md").write_text(
        "Role yaml-like annotation demo\n", encoding="utf-8"
    )


def _build_role_with_underscore_reference(role_path: Path) -> None:
    (role_path / "tasks").mkdir(parents=True)
    (role_path / "tasks" / "main.yml").write_text(
        "---\n"
        "- name: underscore ref\n"
        "  debug:\n"
        '    msg: "{{ _private_runtime_ref }}"\n',
        encoding="utf-8",
    )
    (role_path / "README.md").write_text("Role underscore ref demo\n", encoding="utf-8")


def _build_role_with_annotation_marker(role_path: Path) -> None:
    (role_path / "tasks").mkdir(parents=True)
    (role_path / "tasks" / "main.yml").write_text(
        "---\n"
        "# prism~runbook: use custom remediation path\n"
        "- name: annotated task\n"
        "  debug:\n"
        '    msg: "ok"\n',
        encoding="utf-8",
    )
    (role_path / "README.md").write_text(
        "Role annotation marker demo\n", encoding="utf-8"
    )


def _build_role_with_debug_task(role_path: Path) -> None:
    (role_path / "tasks").mkdir(parents=True)
    (role_path / "tasks" / "main.yml").write_text(
        "---\n" "- name: module detection task\n" "  debug:\n" '    msg: "hello"\n',
        encoding="utf-8",
    )
    (role_path / "README.md").write_text(
        "Role module detection demo\n", encoding="utf-8"
    )


def test_fsrc_runtime_di_override_changes_task_traversal_outcome(
    tmp_path: Path,
) -> None:
    role_path = tmp_path / "role"
    _build_role_with_nested_task_include(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        class _NoIncludeTraversalPolicy:
            def iter_task_mappings(self, data: object):
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            yield item

            @staticmethod
            def iter_task_include_targets(data: object) -> list[str]:
                del data
                return []

            @staticmethod
            def iter_task_include_edges(data: object) -> list[dict[str, str]]:
                del data
                return []

            @staticmethod
            def expand_include_target_candidates(
                task: dict, include_target: str
            ) -> list[str]:
                del task
                return [include_target.strip()] if include_target.strip() else []

            @staticmethod
            def iter_role_include_targets(task: dict) -> list[str]:
                del task
                return []

            @staticmethod
            def iter_dynamic_role_include_targets(task: dict) -> list[str]:
                del task
                return []

            @staticmethod
            def collect_unconstrained_dynamic_task_includes(
                *, role_root, task_files, load_yaml_file
            ):
                del role_root
                del task_files
                del load_yaml_file
                return []

            @staticmethod
            def collect_unconstrained_dynamic_role_includes(
                *, role_root, task_files, load_yaml_file
            ):
                del role_root
                del task_files
                del load_yaml_file
                return []

        original_container = api_module.DIContainer

        class _DIContainerWithTraversalOverride(original_container):
            def factory_task_traversal_policy_plugin(self):
                return _NoIncludeTraversalPolicy()

        api_module.DIContainer = _DIContainerWithTraversalOverride
        try:
            payload = api_module.run_scan(str(role_path), include_vars_main=True)
        finally:
            api_module.DIContainer = original_container

    assert payload["metadata"]["features"]["task_files_scanned"] == 1


def test_fsrc_runtime_di_override_changes_include_vars_resolution(
    tmp_path: Path,
) -> None:
    role_path = tmp_path / "role"
    _build_role_with_custom_include_vars_key(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        task_line_parsing_module = importlib.import_module(
            "prism.scanner_plugins.ansible.task_line_parsing"
        )

        class _CustomLineParsingPolicy:
            TASK_INCLUDE_KEYS = {
                "include_tasks",
                "import_tasks",
                "ansible.builtin.include_tasks",
                "ansible.builtin.import_tasks",
            }
            ROLE_INCLUDE_KEYS = {
                "include_role",
                "import_role",
                "ansible.builtin.include_role",
                "ansible.builtin.import_role",
            }
            INCLUDE_VARS_KEYS = {"custom_include_vars"}
            SET_FACT_KEYS = {"set_fact", "ansible.builtin.set_fact"}
            TASK_BLOCK_KEYS = {"block", "rescue", "always"}
            TASK_META_KEYS = task_line_parsing_module.TASK_META_KEYS

            @staticmethod
            def detect_task_module(task: dict) -> str | None:
                del task
                return None

        original_container = api_module.DIContainer

        class _DIContainerWithLinePolicyOverride(original_container):
            def factory_task_line_parsing_policy_plugin(self):
                return _CustomLineParsingPolicy()

        api_module.DIContainer = _DIContainerWithLinePolicyOverride
        try:
            payload = api_module.run_scan(str(role_path), include_vars_main=True)
        finally:
            api_module.DIContainer = original_container

    assert "policy_loaded_var" in payload["display_variables"]


def test_fsrc_runtime_policy_flag_fails_dynamic_include_in_strict_mode(
    tmp_path: Path,
) -> None:
    role_path = tmp_path / "role"
    _build_role_with_dynamic_include(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        errors_module = importlib.import_module("prism.errors")

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            api_module.run_scan(
                str(role_path),
                include_vars_main=True,
                fail_on_unconstrained_dynamic_includes=True,
                strict_phase_failures=True,
            )

    assert "dynamic include" in str(exc_info.value).lower()


def test_fsrc_runtime_policy_flag_warns_dynamic_include_in_non_strict_mode(
    tmp_path: Path,
) -> None:
    role_path = tmp_path / "role"
    _build_role_with_dynamic_include(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        payload = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            fail_on_unconstrained_dynamic_includes=True,
            strict_phase_failures=False,
        )

    warnings = payload["metadata"].get("scan_policy_warnings")
    assert isinstance(warnings, list)
    assert warnings
    assert warnings[0]["code"] == "unconstrained_dynamic_includes_detected"


def test_fsrc_runtime_policy_flag_fails_yaml_like_annotation_in_strict_mode(
    tmp_path: Path,
) -> None:
    role_path = tmp_path / "role"
    _build_role_with_yaml_like_task_annotation(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        errors_module = importlib.import_module("prism.errors")

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            api_module.run_scan(
                str(role_path),
                include_vars_main=True,
                fail_on_yaml_like_task_annotations=True,
                strict_phase_failures=True,
            )

    assert "yaml-like task annotations" in str(exc_info.value).lower()


def test_fsrc_runtime_blocker_translation_after_payload_construction_preserves_strict_and_non_strict_outcomes(
    tmp_path: Path,
) -> None:
    dynamic_role_path = tmp_path / "dynamic_role"
    yaml_like_role_path = tmp_path / "yaml_like_role"
    _build_role_with_dynamic_include(dynamic_role_path)
    _build_role_with_yaml_like_task_annotation(yaml_like_role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        errors_module = importlib.import_module("prism.errors")

        with pytest.raises(errors_module.PrismRuntimeError) as dynamic_exc_info:
            api_module.run_scan(
                str(dynamic_role_path),
                include_vars_main=True,
                fail_on_unconstrained_dynamic_includes=True,
                strict_phase_failures=True,
            )

        payload = api_module.run_scan(
            str(yaml_like_role_path),
            include_vars_main=True,
            fail_on_yaml_like_task_annotations=True,
            strict_phase_failures=False,
        )

    assert dynamic_exc_info.value.code == "unconstrained_dynamic_includes_detected"
    assert dynamic_exc_info.value.detail == {
        "dynamic_task_includes": 1,
        "dynamic_role_includes": 0,
    }
    warnings = payload["metadata"].get("scan_policy_warnings")
    assert warnings == [
        {
            "code": "yaml_like_task_annotations_detected",
            "message": "Scan policy warning: yaml-like task annotations were detected.",
            "detail": {"yaml_like_task_annotations": 1},
        }
    ]


def test_fsrc_runtime_blocker_translation_runs_before_route_specific_warning_injection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "role"
    _build_role_with_dynamic_include(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        class _RuntimeFailingPlugin:
            def process_scan_pipeline(
                self,
                scan_options: dict[str, object],
                scan_context: dict[str, object],
            ) -> dict[str, object]:
                del scan_options
                del scan_context
                return {"plugin_enabled": True, "plugin_name": "default"}

            def orchestrate_scan_payload(
                self,
                *,
                payload: dict[str, object],
                scan_options: dict[str, object],
                strict_mode: bool,
                preflight_context: dict[str, object] | None = None,
            ) -> dict[str, object]:
                del payload
                del scan_options
                del strict_mode
                del preflight_context
                raise RuntimeError("runtime boom")

        class _Registry:
            @staticmethod
            def get_scan_pipeline_plugin(name: str):
                if name == "default":
                    return _RuntimeFailingPlugin
                return None

        monkeypatch.setattr(api_module, "DEFAULT_PLUGIN_REGISTRY", _Registry())
        payload = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            fail_on_unconstrained_dynamic_includes=True,
            strict_phase_failures=False,
            scan_pipeline_plugin="default",
        )

    assert payload["metadata"]["scan_policy_warnings"] == [
        {
            "code": "unconstrained_dynamic_includes_detected",
            "message": "Scan policy warning: unconstrained dynamic include targets were detected.",
            "detail": {
                "dynamic_task_includes": 1,
                "dynamic_role_includes": 0,
            },
        }
    ]
    plugin_runtime_warnings = payload["metadata"]["plugin_runtime_warnings"]
    assert plugin_runtime_warnings[0]["code"] == "scan_pipeline_plugin_failed"
    assert plugin_runtime_warnings[0]["message"] == (
        "scan-pipeline runtime execution failed"
    )
    assert plugin_runtime_warnings[0]["metadata"]["routing"] == {
        "mode": "scan_pipeline_plugin",
        "selection_order": [
            "request.option.scan_pipeline_plugin",
            "policy_context.selection.plugin",
            "platform",
            "registry_default",
        ],
        "selected_plugin": "default",
        "failure_mode": "runtime_execution_exception",
        "fallback_reason": "runtime_execution_exception",
        "fallback_applied": True,
    }


def test_fsrc_runtime_fallback_route_preserves_blocker_translation_before_legacy_warning_injection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "role"
    _build_role_with_dynamic_include(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        class _Registry:
            @staticmethod
            def get_scan_pipeline_plugin(_name: str):
                return None

        monkeypatch.setattr(api_module, "DEFAULT_PLUGIN_REGISTRY", _Registry())
        payload = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            fail_on_unconstrained_dynamic_includes=True,
            strict_phase_failures=False,
            scan_pipeline_plugin="custom",
        )

    assert (
        payload.get("metadata", {}).get("platform_routing_outcome", {}).get("outcome")
        == "PLATFORM_NOT_REGISTERED"
    )
    assert "scan_policy_warnings" not in payload.get("metadata", {})
    assert "plugin_runtime_warnings" not in payload.get("metadata", {})


def test_fsrc_runtime_underscore_ignore_toggle_filters_unresolved_output(
    tmp_path: Path,
) -> None:
    role_path = tmp_path / "role"
    _build_role_with_underscore_reference(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        included = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            ignore_unresolved_internal_underscore_references=False,
        )
        ignored = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            ignore_unresolved_internal_underscore_references=True,
        )

    assert "_private_runtime_ref" in included["display_variables"]
    assert "_private_runtime_ref" not in ignored["display_variables"]


def test_fsrc_runtime_di_override_changes_annotation_parsing_behavior(
    tmp_path: Path,
) -> None:
    role_path = tmp_path / "role"
    _build_role_with_annotation_marker(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        class _CustomAnnotationPolicy:
            @staticmethod
            def split_task_annotation_label(text: str) -> tuple[str, str]:
                return "runbook", text.strip()

            @staticmethod
            def split_task_target_payload(text: str) -> tuple[str, str]:
                return "", text.strip()

            @staticmethod
            def annotation_payload_looks_yaml(payload: str) -> bool:
                return "custom remediation" in payload

            @staticmethod
            def extract_task_annotations_for_file(
                lines: list[str],
                marker_prefix: str = "prism",
                include_task_index: bool = False,
            ) -> tuple[list[dict[str, object]], dict[str, list[dict[str, object]]]]:
                del marker_prefix
                del include_task_index
                annotations: list[dict[str, object]] = []
                for line in lines:
                    if "prism~runbook:" not in line:
                        continue
                    text = line.split("prism~runbook:", 1)[1].strip()
                    annotations.append(
                        {
                            "kind": "runbook",
                            "text": text,
                            "format_warning": "forced-by-di",
                        }
                    )
                return annotations, {}

            @staticmethod
            def task_anchor(file_path: str, task_name: str, index: int) -> str:
                return f"{file_path}-{task_name}-{index}".replace(" ", "-")

        original_container = api_module.DIContainer

        class _DIContainerWithAnnotationPolicyOverride(original_container):
            def factory_task_annotation_policy_plugin(self):
                return _CustomAnnotationPolicy()

        api_module.DIContainer = _DIContainerWithAnnotationPolicyOverride
        try:
            payload = api_module.run_scan(str(role_path), include_vars_main=True)
        finally:
            api_module.DIContainer = original_container

    assert payload["metadata"]["features"]["yaml_like_task_annotations"] == 1


def test_fsrc_runtime_di_override_changes_task_module_detection_behavior(
    tmp_path: Path,
) -> None:
    role_path = tmp_path / "role"
    _build_role_with_debug_task(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        task_line_parsing_module = importlib.import_module(
            "prism.scanner_plugins.ansible.task_line_parsing"
        )

        class _CustomTaskLineParsingPolicy:
            TASK_INCLUDE_KEYS = {
                "include_tasks",
                "import_tasks",
                "ansible.builtin.include_tasks",
                "ansible.builtin.import_tasks",
            }
            ROLE_INCLUDE_KEYS = {
                "include_role",
                "import_role",
                "ansible.builtin.include_role",
                "ansible.builtin.import_role",
            }
            INCLUDE_VARS_KEYS = {
                "include_vars",
                "ansible.builtin.include_vars",
            }
            SET_FACT_KEYS = {"set_fact", "ansible.builtin.set_fact"}
            TASK_BLOCK_KEYS = {"block", "rescue", "always"}
            TASK_META_KEYS = task_line_parsing_module.TASK_META_KEYS

            @staticmethod
            def detect_task_module(task: dict) -> str | None:
                if "debug" in task:
                    return "acme.collection.custom_debug"
                return None

        original_container = api_module.DIContainer

        class _DIContainerWithLinePolicyOverride(original_container):
            def factory_task_line_parsing_policy_plugin(self):
                return _CustomTaskLineParsingPolicy()

        api_module.DIContainer = _DIContainerWithLinePolicyOverride
        try:
            payload = api_module.run_scan(str(role_path), include_vars_main=True)
        finally:
            api_module.DIContainer = original_container

    assert (
        payload["metadata"]["features"]["unique_modules"]
        == "acme.collection.custom_debug"
    )
    assert payload["metadata"]["features"]["external_collections"] == "acme.collection"


def test_runtime_blockers_preserve_strict_failures_and_non_strict_warnings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "role"
    _build_role_with_debug_task(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        errors_module = importlib.import_module("prism.errors")

        class _RuntimeFailingPlugin:
            def process_scan_pipeline(
                self,
                scan_options: dict[str, object],
                scan_context: dict[str, object],
            ) -> dict[str, object]:
                del scan_options
                del scan_context
                return {"plugin_enabled": True, "plugin_name": "default"}

            def orchestrate_scan_payload(
                self,
                *,
                payload: dict[str, object],
                scan_options: dict[str, object],
                strict_mode: bool,
                preflight_context: dict[str, object] | None = None,
            ) -> dict[str, object]:
                del payload
                del scan_options
                del strict_mode
                del preflight_context
                raise RuntimeError("runtime boom")

        class _Registry:
            @staticmethod
            def get_scan_pipeline_plugin(name: str):
                if name == "default":
                    return _RuntimeFailingPlugin
                return None

        monkeypatch.setattr(api_module, "DEFAULT_PLUGIN_REGISTRY", _Registry())

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            api_module.run_scan(
                str(role_path),
                include_vars_main=True,
                scan_pipeline_plugin="default",
                strict_phase_failures=True,
            )

        payload = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            scan_pipeline_plugin="default",
            strict_phase_failures=False,
        )

    assert exc_info.value.code == "scan_pipeline_execution_failed"
    assert exc_info.value.detail == {
        "metadata": {
            "routing": {
                "failure_mode": "runtime_execution_exception",
                "selected_plugin": "default",
            }
        }
    }
    warnings = payload["metadata"].get("plugin_runtime_warnings")
    assert isinstance(warnings, list)
    assert warnings
    assert warnings[0]["code"] == "scan_pipeline_plugin_failed"
    assert payload["metadata"]["routing"] == {
        "mode": "scan_pipeline_plugin",
        "selection_order": [
            "request.option.scan_pipeline_plugin",
            "policy_context.selection.plugin",
            "platform",
            "registry_default",
        ],
        "failure_mode": "runtime_execution_exception",
        "selected_plugin": "default",
        "fallback_reason": "runtime_execution_exception",
        "fallback_applied": True,
    }
