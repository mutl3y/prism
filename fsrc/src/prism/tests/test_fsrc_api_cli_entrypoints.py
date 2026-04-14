"""Focused fsrc tests for top-level API and CLI entrypoint behavior."""

from __future__ import annotations

import importlib
import json
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


def _build_tiny_role(role_path: Path) -> None:
    (role_path / "defaults").mkdir(parents=True)
    (role_path / "tasks").mkdir(parents=True)
    (role_path / "defaults" / "main.yml").write_text(
        "---\nexample_name: prism\n", encoding="utf-8"
    )
    (role_path / "tasks" / "main.yml").write_text(
        '---\n- name: Use a variable\n  debug:\n    msg: "{{ example_name }} {{ runtime_name }}"\n',
        encoding="utf-8",
    )
    (role_path / "README.md").write_text(
        "Role for API entrypoint tests.\n\nInput variable: {{ example_name }}\n",
        encoding="utf-8",
    )


def test_fsrc_api_run_scan_returns_structured_payload(tmp_path: Path) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        payload = api_module.run_scan(str(role_path), include_vars_main=True)

    assert payload["role_name"] == "tiny_role"
    assert isinstance(payload["description"], str)
    assert payload["description"]
    assert "example_name" in payload["display_variables"]
    assert payload["display_variables"]["example_name"]["default"] == "prism"
    assert "requirements_display" in payload
    assert "undocumented_default_filters" in payload
    assert payload["metadata"]["features"]["task_files_scanned"] == 1


def test_fsrc_api_run_scan_uses_runtime_route_orchestration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        called = {"route": False}

        def _route(
            *,
            role_path,
            scan_options,
            legacy_orchestrator_fn,
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            called["route"] = True
            return legacy_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(api_module, "route_scan_payload_orchestration", _route)
        payload = api_module.run_scan(str(role_path), include_vars_main=True)

    assert called["route"] is True
    assert payload["role_name"] == "tiny_role"


def test_fsrc_api_run_scan_reuses_router_preflight_without_second_plugin_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        def _route(
            *,
            role_path,
            scan_options,
            legacy_orchestrator_fn,
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del legacy_orchestrator_fn
            del registry
            return kernel_orchestrator_fn(
                role_path="/tmp/ignored",
                scan_options={
                    "_scan_pipeline_preflight_context": {
                        "plugin_runtime_marker": "preflight-used",
                        "features": {"task_files_scanned": 999},
                    }
                },
            )

        class _Plugin:
            def process_scan_pipeline(
                self,
                scan_options: dict[str, object],
                scan_context: dict[str, object],
            ) -> dict[str, object]:
                del scan_options
                del scan_context
                raise AssertionError(
                    "plugin should not be called when preflight exists"
                )

        class _Registry:
            def get_scan_pipeline_plugin(self, _name: str):
                return _Plugin

        monkeypatch.setattr(api_module, "route_scan_payload_orchestration", _route)
        monkeypatch.setattr(api_module, "DEFAULT_PLUGIN_REGISTRY", _Registry())
        payload = api_module.run_scan(str(role_path), include_vars_main=True)

    assert payload["metadata"]["plugin_runtime_marker"] == "preflight-used"
    assert payload["metadata"]["features"]["task_files_scanned"] == 1


def test_fsrc_api_run_scan_consumes_registered_scan_pipeline_plugin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        def _route(
            *,
            role_path,
            scan_options,
            legacy_orchestrator_fn,
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del legacy_orchestrator_fn
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(api_module, "route_scan_payload_orchestration", _route)

        class _Plugin:
            called = False

            def process_scan_pipeline(
                self,
                scan_options: dict[str, object],
                scan_context: dict[str, object],
            ) -> dict[str, object]:
                del scan_context
                _Plugin.called = True
                assert str(scan_options["role_path"]) == str(role_path)
                return {
                    "plugin_runtime_marker": "applied",
                    "features": {"task_files_scanned": 999},
                }

        class _Registry:
            def get_scan_pipeline_plugin(self, name: str):
                if name == "default":
                    return _Plugin
                return None

        monkeypatch.setattr(api_module, "DEFAULT_PLUGIN_REGISTRY", _Registry())
        payload = api_module.run_scan(str(role_path), include_vars_main=True)

    assert _Plugin.called is True
    assert payload["metadata"]["plugin_runtime_marker"] == "applied"
    assert payload["metadata"]["features"]["task_files_scanned"] == 1


def test_fsrc_api_run_scan_falls_back_when_scan_pipeline_plugin_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        def _route(
            *,
            role_path,
            scan_options,
            legacy_orchestrator_fn,
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del legacy_orchestrator_fn
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(api_module, "route_scan_payload_orchestration", _route)

        class _Registry:
            def get_scan_pipeline_plugin(self, _name: str):
                return None

        monkeypatch.setattr(api_module, "DEFAULT_PLUGIN_REGISTRY", _Registry())
        payload = api_module.run_scan(str(role_path), include_vars_main=True)

    assert payload["metadata"]["features"]["task_files_scanned"] == 1
    assert "plugin_runtime_marker" not in payload["metadata"]


def test_fsrc_api_run_scan_plugin_failure_raises_when_strict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        errors_module = importlib.import_module("prism.errors")

        def _route(
            *,
            role_path,
            scan_options,
            legacy_orchestrator_fn,
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del legacy_orchestrator_fn
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(api_module, "route_scan_payload_orchestration", _route)

        class _Plugin:
            def process_scan_pipeline(
                self,
                scan_options: dict[str, object],
                scan_context: dict[str, object],
            ) -> dict[str, object]:
                del scan_options
                del scan_context
                raise RuntimeError("plugin boom")

        class _Registry:
            def get_scan_pipeline_plugin(self, _name: str):
                return _Plugin

        monkeypatch.setattr(api_module, "DEFAULT_PLUGIN_REGISTRY", _Registry())

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            api_module.run_scan(str(role_path), include_vars_main=True)

    assert "scan-pipeline plugin execution failed" in str(exc_info.value)


def test_fsrc_api_run_scan_plugin_failure_falls_back_when_not_strict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        def _route(
            *,
            role_path,
            scan_options,
            legacy_orchestrator_fn,
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del legacy_orchestrator_fn
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(api_module, "route_scan_payload_orchestration", _route)

        class _Plugin:
            def process_scan_pipeline(
                self,
                scan_options: dict[str, object],
                scan_context: dict[str, object],
            ) -> dict[str, object]:
                del scan_options
                del scan_context
                raise RuntimeError("plugin boom")

        class _Registry:
            def get_scan_pipeline_plugin(self, _name: str):
                return _Plugin

        monkeypatch.setattr(api_module, "DEFAULT_PLUGIN_REGISTRY", _Registry())
        payload = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            strict_phase_failures=False,
        )

    warnings = payload["metadata"].get("plugin_runtime_warnings")
    assert isinstance(warnings, list)
    assert warnings
    assert warnings[0]["code"] == "scan_pipeline_plugin_failed"
    assert payload["metadata"]["features"]["task_files_scanned"] == 1


def test_fsrc_api_run_scan_registry_lookup_failure_falls_back_when_not_strict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        def _route(
            *,
            role_path,
            scan_options,
            legacy_orchestrator_fn,
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del legacy_orchestrator_fn
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(api_module, "route_scan_payload_orchestration", _route)

        class _Registry:
            def get_scan_pipeline_plugin(self, _name: str):
                raise RuntimeError("registry boom")

        monkeypatch.setattr(api_module, "DEFAULT_PLUGIN_REGISTRY", _Registry())
        payload = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            strict_phase_failures=False,
        )

    warnings = payload["metadata"].get("plugin_runtime_warnings")
    assert isinstance(warnings, list)
    assert warnings
    assert warnings[0]["code"] == "scan_pipeline_plugin_failed"
    assert payload["metadata"]["features"]["task_files_scanned"] == 1


def test_fsrc_api_run_scan_registry_lookup_failure_raises_when_strict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        errors_module = importlib.import_module("prism.errors")

        def _route(
            *,
            role_path,
            scan_options,
            legacy_orchestrator_fn,
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del legacy_orchestrator_fn
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(api_module, "route_scan_payload_orchestration", _route)

        class _Registry:
            def get_scan_pipeline_plugin(self, _name: str):
                raise RuntimeError("registry boom")

        monkeypatch.setattr(api_module, "DEFAULT_PLUGIN_REGISTRY", _Registry())

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            api_module.run_scan(str(role_path), include_vars_main=True)

    assert "scan-pipeline plugin execution failed" in str(exc_info.value)


def test_fsrc_api_run_scan_plugin_scan_context_mutation_does_not_leak(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        def _route(
            *,
            role_path,
            scan_options,
            legacy_orchestrator_fn,
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del legacy_orchestrator_fn
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(api_module, "route_scan_payload_orchestration", _route)

        class _Plugin:
            def process_scan_pipeline(
                self,
                scan_options: dict[str, object],
                scan_context: dict[str, object],
            ) -> dict[str, object]:
                del scan_options
                features = scan_context.get("features")
                if isinstance(features, dict):
                    features["task_files_scanned"] = 999
                return {"plugin_runtime_marker": "mutated-context"}

        class _Registry:
            def get_scan_pipeline_plugin(self, _name: str):
                return _Plugin

        monkeypatch.setattr(api_module, "DEFAULT_PLUGIN_REGISTRY", _Registry())
        payload = api_module.run_scan(str(role_path), include_vars_main=True)

    assert payload["metadata"]["plugin_runtime_marker"] == "mutated-context"
    assert payload["metadata"]["features"]["task_files_scanned"] == 1


def test_fsrc_api_run_scan_plugin_scan_options_mutation_cannot_downgrade_strict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        errors_module = importlib.import_module("prism.errors")

        def _route(
            *,
            role_path,
            scan_options,
            legacy_orchestrator_fn,
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del legacy_orchestrator_fn
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(api_module, "route_scan_payload_orchestration", _route)

        class _Plugin:
            def process_scan_pipeline(
                self,
                scan_options: dict[str, object],
                scan_context: dict[str, object],
            ) -> dict[str, object]:
                del scan_context
                scan_options["strict_phase_failures"] = False
                raise RuntimeError("plugin boom")

        class _Registry:
            def get_scan_pipeline_plugin(self, _name: str):
                return _Plugin

        monkeypatch.setattr(api_module, "DEFAULT_PLUGIN_REGISTRY", _Registry())

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            api_module.run_scan(str(role_path), include_vars_main=True)

    assert "scan-pipeline plugin execution failed" in str(exc_info.value)


def test_fsrc_cli_main_runs_scan_and_emits_json(tmp_path: Path, capsys) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")
        exit_code = cli_module.main(["role", str(role_path), "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["role_name"] == "tiny_role"
    assert "example_name" in payload["display_variables"]


def test_fsrc_cli_main_returns_nonzero_on_failure(monkeypatch, capsys) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")

        def _raise_failure(*_args: object, **_kwargs: object) -> dict[str, object]:
            raise RuntimeError("boom")

        monkeypatch.setattr(cli_module.api, "scan_role", _raise_failure)
        exit_code = cli_module.main(["role", "/tmp/role-that-does-not-matter"])

    captured = capsys.readouterr()
    assert exit_code != 0
    assert "boom" in captured.err


def test_fsrc_api_run_scan_rejects_invalid_or_missing_role_path(tmp_path: Path) -> None:
    missing_role = tmp_path / "missing_role"

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        errors_module = importlib.import_module("prism.errors")

        with pytest.raises(errors_module.PrismRuntimeError) as empty_error:
            api_module.run_scan("   ")
        with pytest.raises(errors_module.PrismRuntimeError) as missing_error:
            api_module.run_scan(str(missing_role))

    assert "role_path" in str(empty_error.value)
    assert "not exist" in str(missing_error.value)


def test_fsrc_cli_main_returns_nonzero_for_invalid_role_path(capsys) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")
        exit_code = cli_module.main(["role", "/tmp/prism-definitely-missing-role"])

    captured = capsys.readouterr()
    assert isinstance(exit_code, int)
    assert exit_code != 0
    assert "Error:" in captured.err


def test_fsrc_cli_main_parse_error_returns_nonzero_int(capsys) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")
        exit_code = cli_module.main([])

    captured = capsys.readouterr()
    assert isinstance(exit_code, int)
    assert exit_code != 0
    assert "usage:" in captured.err.lower()


def test_fsrc_api_run_scan_uses_scan_pipeline_plugin_selector(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        def _route(
            *,
            role_path,
            scan_options,
            legacy_orchestrator_fn,
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del legacy_orchestrator_fn
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(api_module, "route_scan_payload_orchestration", _route)

        class _Plugin:
            def process_scan_pipeline(
                self,
                scan_options: dict[str, object],
                scan_context: dict[str, object],
            ) -> dict[str, object]:
                del scan_context
                assert scan_options.get("scan_pipeline_plugin") == "custom"
                return {
                    "plugin_enabled": True,
                    "plugin_runtime_marker": "custom-selector",
                }

        class _Registry:
            def get_scan_pipeline_plugin(self, name: str):
                if name == "custom":
                    return _Plugin
                return None

        monkeypatch.setattr(api_module, "DEFAULT_PLUGIN_REGISTRY", _Registry())
        payload = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            scan_pipeline_plugin="custom",
        )

    assert payload["metadata"]["plugin_runtime_marker"] == "custom-selector"
