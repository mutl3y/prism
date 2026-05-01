"""Focused integration regressions for Gilfoyle runtime blocker remediation."""

from __future__ import annotations

import importlib
import logging
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

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
            def normalize_marker_prefix(marker_prefix: str | None) -> str:
                return marker_prefix or "prism"

            @staticmethod
            def get_marker_line_re(marker_prefix: str = "prism") -> object:
                return __import__("re").compile(marker_prefix)

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


def test_runtime_blockers_preserve_strict_failures(
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

        plugins_module = importlib.import_module("prism.scanner_plugins")
        _real = plugins_module.DEFAULT_PLUGIN_REGISTRY

        class _Registry:
            @staticmethod
            def get_scan_pipeline_plugin(name: str):
                if name == "default":
                    return _RuntimeFailingPlugin
                return None

            def __getattr__(self, name: str):
                return getattr(_real, name)

            get_default_platform_key = _real.get_default_platform_key
            get_variable_discovery_plugin = _real.get_variable_discovery_plugin
            get_feature_detection_plugin = _real.get_feature_detection_plugin

        monkeypatch.setattr(
            api_module.plugin_facade, "get_default_plugin_registry", lambda: _Registry()
        )

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            api_module.run_scan(
                str(role_path),
                include_vars_main=True,
                scan_pipeline_plugin="default",
                strict_phase_failures=True,
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


def test_g30_cf003_pattern_load_yaml_logs_corrupt_yaml_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """CF003: _load_yaml logs warning for corrupt YAML instead of silent empty dict."""
    from prism.scanner_config.patterns import _load_yaml

    corrupt_file = tmp_path / "corrupt.yml"
    corrupt_file.write_text("key: [unclosed", encoding="utf-8")

    caplog.set_level(logging.WARNING, logger="prism.scanner_config.patterns")
    result = _load_yaml(corrupt_file)

    assert result == {}
    assert any(
        "Pattern file YAML parse error" in record.message
        and str(corrupt_file) in record.message
        for record in caplog.records
    )


def test_g30_cf003_pattern_load_yaml_logs_missing_file_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """CF003: _load_yaml logs warning for missing file."""
    from prism.scanner_config.patterns import _load_yaml

    missing_file = tmp_path / "missing.yml"

    caplog.set_level(logging.WARNING, logger="prism.scanner_config.patterns")
    result = _load_yaml(missing_file)

    assert result == {}
    assert any(
        "Pattern file IO error" in record.message
        and str(missing_file) in record.message
        for record in caplog.records
    )


def test_g30_cf003_pattern_load_yaml_logs_encoding_error_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """CF003: _load_yaml logs warning for encoding error."""
    from prism.scanner_config.patterns import _load_yaml

    bad_encoding_file = tmp_path / "bad_encoding.yml"
    bad_encoding_file.write_bytes(b"key: \xff\xfe value")

    caplog.set_level(logging.WARNING, logger="prism.scanner_config.patterns")
    result = _load_yaml(bad_encoding_file)

    assert result == {}
    assert any(
        "Pattern file encoding error" in record.message
        and str(bad_encoding_file) in record.message
        for record in caplog.records
    )


def test_g30_cf003_pattern_load_yaml_returns_empty_for_valid_empty(
    tmp_path: Path,
) -> None:
    """CF003: _load_yaml returns empty dict for valid empty YAML (not an error)."""
    from prism.scanner_config.patterns import _load_yaml

    empty_file = tmp_path / "empty.yml"
    empty_file.write_text("", encoding="utf-8")

    result = _load_yaml(empty_file)

    assert result == {}


def test_g30_cf002_seed_variables_handles_corrupt_yaml_gracefully(
    tmp_path: Path,
) -> None:
    """CF002: load_seed_variables returns empty for corrupt seed file (graceful degradation)."""
    from prism.scanner_extract.variable_extractor import load_seed_variables

    corrupt_seed = tmp_path / "corrupt_seed.yml"
    corrupt_seed.write_text("key: [unclosed", encoding="utf-8")

    seed_values, _, _ = load_seed_variables([str(corrupt_seed)])

    # Corrupt seed files are optional inputs - should return empty, not crash
    assert seed_values == {}


def test_g30_cf002_seed_variables_handles_missing_file_gracefully(
    tmp_path: Path,
) -> None:
    """CF002: load_seed_variables returns empty for missing seed file (graceful degradation)."""
    from prism.scanner_extract.variable_extractor import load_seed_variables

    missing_seed = tmp_path / "missing_seed.yml"

    seed_values, _, _ = load_seed_variables([str(missing_seed)])

    # Missing seed files are skipped silently (not an error)
    assert seed_values == {}


def test_g30_cf004_remote_policy_logs_http_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """CF004: fetch_remote_policy logs warning for HTTP error."""
    from prism.scanner_config.patterns import fetch_remote_policy

    bad_url = "https://raw.githubusercontent.com/nonexistent/repo/main/missing.yml"
    cache_file = tmp_path / "cache.yml"

    caplog.set_level(logging.WARNING, logger="prism.scanner_config.patterns")
    with pytest.raises(RuntimeError, match="Failed to fetch remote patterns"):
        fetch_remote_policy(url=bad_url, cache_path=str(cache_file), timeout=2)

    assert any(
        "Remote policy" in record.message and bad_url in record.message
        for record in caplog.records
    )


def test_g30_cf006_discovery_load_meta_logs_yaml_parse_failure(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """CF006: load_meta logs warning for YAML parsing failures in non-strict mode."""
    from prism.scanner_extract.discovery import load_meta

    role_path = tmp_path / "role"
    role_path.mkdir()
    meta_dir = role_path / "meta"
    meta_dir.mkdir()
    meta_file = meta_dir / "main.yml"
    meta_file.write_text("invalid: yaml: [unclosed", encoding="utf-8")

    caplog.set_level(logging.WARNING, logger="prism.scanner_extract.discovery")
    result = load_meta(str(role_path), strict=False)

    assert result == {}
    assert any(
        "YAML parsing failed" in record.message and "non-strict mode" in record.message
        for record in caplog.records
    )


def test_g30_cf006_discovery_load_meta_logs_io_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CF006: load_meta logs warning for IO errors in non-strict mode."""
    from prism.scanner_extract.discovery import load_meta

    role_path = tmp_path / "role"
    role_path.mkdir()
    meta_dir = role_path / "meta"
    meta_dir.mkdir()
    meta_file = meta_dir / "main.yml"
    meta_file.write_text("---\nvalid: yaml\n", encoding="utf-8")

    def _failing_load_yaml_file(path, di=None):
        raise OSError("Simulated IO error")

    monkeypatch.setattr(
        "prism.scanner_extract.discovery.load_yaml_file", _failing_load_yaml_file
    )

    caplog.set_level(logging.WARNING, logger="prism.scanner_extract.discovery")
    result = load_meta(str(role_path), strict=False)

    assert result == {}
    assert any(
        "Failed to load" in record.message
        and "non-strict mode" in record.message
        and "OSError" in record.message
        for record in caplog.records
    )


def test_g30_cf006_discovery_load_requirements_logs_io_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CF006: load_requirements logs warning for IO errors in non-strict mode."""
    from prism.scanner_extract.discovery import load_requirements

    role_path = tmp_path / "role"
    role_path.mkdir()
    meta_dir = role_path / "meta"
    meta_dir.mkdir()
    req_file = meta_dir / "requirements.yml"
    req_file.write_text("---\n- name: sample\n", encoding="utf-8")

    def _failing_load_yaml_file(path, di=None):
        raise OSError("Simulated IO error")

    monkeypatch.setattr(
        "prism.scanner_extract.discovery.load_yaml_file", _failing_load_yaml_file
    )

    caplog.set_level(logging.WARNING, logger="prism.scanner_extract.discovery")
    result = load_requirements(str(role_path), strict=False)

    assert result == []
    assert any(
        "Failed to load requirements" in record.message
        and "non-strict mode" in record.message
        and "OSError" in record.message
        for record in caplog.records
    )


def test_g30_cf006_discovery_load_variables_logs_io_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CF006: load_variables logs warning for IO errors in non-strict mode."""
    from prism.scanner_extract.discovery import load_variables

    role_path = tmp_path / "role"
    role_path.mkdir()
    defaults_dir = role_path / "defaults"
    defaults_dir.mkdir()
    main_yml = defaults_dir / "main.yml"
    main_yml.write_text("---\nvar: value\n", encoding="utf-8")

    def _failing_load_yaml_file(path, di=None):
        raise OSError("Simulated IO error")

    monkeypatch.setattr(
        "prism.scanner_extract.discovery.load_yaml_file", _failing_load_yaml_file
    )

    caplog.set_level(logging.WARNING, logger="prism.scanner_extract.discovery")
    result = load_variables(
        str(role_path),
        include_vars_main=False,
        collect_include_vars_files=lambda role, excl: [],
        strict=False,
    )

    assert result == {}
    assert any(
        "Failed to load variable file" in record.message
        and "non-strict mode" in record.message
        and "OSError" in record.message
        for record in caplog.records
    )


def test_g30_cf007_defaults_plugin_fallback_logs_diagnostic(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CF007: plugin construction fallback logs warning in non-strict mode."""
    from prism.scanner_plugins.defaults import (
        resolve_task_line_parsing_policy_plugin,
    )
    from prism.scanner_plugins.registry import PluginRegistry

    class _FailingPlugin:
        PLUGIN_API_VERSION = 1
        PLUGIN_IS_STATELESS = True

        def __init__(self):
            raise ValueError("Simulated plugin construction failure")

    registry = PluginRegistry()
    registry.register_extract_policy_plugin(
        name="task_line_parsing", plugin_class=_FailingPlugin
    )

    caplog.set_level(logging.WARNING, logger="prism.scanner_plugins.defaults")
    plugin = resolve_task_line_parsing_policy_plugin(
        di=None, strict_mode=False, registry=registry
    )

    assert plugin is not None
    assert any(
        "Failed to construct" in record.message and "falling back" in record.message
        for record in caplog.records
    )


def test_g30_cf008_guide_warns_on_missing_platform_key(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CF008: guide.py warns when platform_key is missing."""
    from prism.scanner_readme.guide import render_guide_section_body

    caplog.set_level(logging.WARNING, logger="prism.scanner_readme.guide")
    result = render_guide_section_body(
        section_id="identity",
        role_name="test",
        description="test",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={},
    )

    assert result is not None
    assert any(
        "platform_key missing or empty" in record.message
        and "defaulting to 'ansible'" in record.message
        for record in caplog.records
    )


def test_g30_cf008_guide_warns_on_empty_platform_key(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """CF008: guide.py warns when platform_key is empty string."""
    from prism.scanner_readme.guide import render_guide_section_body

    caplog.set_level(logging.WARNING, logger="prism.scanner_readme.guide")
    result = render_guide_section_body(
        section_id="identity",
        role_name="test",
        description="test",
        variables={},
        requirements=[],
        default_filters=[],
        metadata={"platform_key": ""},
    )

    assert result is not None
    assert any(
        "platform_key missing or empty" in record.message
        and "value=''" in record.message
        and "defaulting to 'ansible'" in record.message
        for record in caplog.records
    )
