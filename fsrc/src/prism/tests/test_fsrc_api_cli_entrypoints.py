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


def test_fsrc_scan_payload_builder_preserves_metadata_features() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        scanner_data_module = importlib.import_module("prism.scanner_data")

        payload = (
            scanner_data_module.ScanPayloadBuilder()
            .role_name("demo-role")
            .description("demo")
            .display_variables({})
            .requirements_display([])
            .undocumented_default_filters([])
            .metadata({"features": {"task_files_scanned": 3}})
            .build()
        )

    assert payload["role_name"] == "demo-role"
    assert payload["metadata"]["features"]["task_files_scanned"] == 3


def test_fsrc_api_run_scan_delegates_to_non_collection_api_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        captured: dict[str, object] = {}

        def _fake_run_scan(role_path: str, **kwargs: object) -> dict[str, object]:
            captured["role_path"] = role_path
            captured["kwargs"] = dict(kwargs)
            return {
                "role_name": "tiny_role",
                "description": "delegated",
                "requirements_display": [],
                "undocumented_default_filters": [],
                "display_variables": {},
                "metadata": {"features": {"task_files_scanned": 1}},
            }

        monkeypatch.setattr(api_module.api_non_collection, "run_scan", _fake_run_scan)
        payload = api_module.run_scan(
            str(role_path),
            policy_config_path="/tmp/policy.yml",
            scan_pipeline_plugin="custom",
        )

    assert payload["role_name"] == "tiny_role"
    assert api_module.API_RETAINED_COMPATIBILITY_SEAMS == ("run_scan",)
    assert captured["role_path"] == str(role_path)
    assert captured["kwargs"]["policy_config_path"] == "/tmp/policy.yml"
    assert captured["kwargs"]["scan_pipeline_plugin"] == "custom"


def test_fsrc_api_scan_role_delegates_to_non_collection_api_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        captured: dict[str, object] = {}

        def _fake_run_scan(role_path: str, **kwargs: object) -> dict[str, object]:
            captured["delegated_run_scan_role_path"] = role_path
            captured["delegated_run_scan_kwargs"] = dict(kwargs)
            return {"role_name": "delegated-role"}

        def _fake_scan_role(role_path: str, **kwargs: object) -> dict[str, object]:
            captured["role_path"] = role_path
            captured["kwargs"] = dict(kwargs)
            run_scan_fn = kwargs["run_scan_fn"]
            assert callable(run_scan_fn)
            return run_scan_fn(role_path, role_name_override="delegated-role")

        monkeypatch.setattr(api_module, "run_scan", _fake_run_scan)
        monkeypatch.setattr(
            api_module.api_non_collection,
            "scan_role",
            _fake_scan_role,
        )
        payload = api_module.scan_role(
            "/tmp/demo-role",
            policy_config_path="/tmp/policy.yml",
        )

    assert payload["role_name"] == "delegated-role"
    assert captured["role_path"] == "/tmp/demo-role"
    assert captured["kwargs"]["policy_config_path"] == "/tmp/policy.yml"
    assert captured["delegated_run_scan_role_path"] == "/tmp/demo-role"
    assert (
        captured["delegated_run_scan_kwargs"]["role_name_override"] == "delegated-role"
    )


def test_fsrc_api_scan_repo_delegates_to_non_collection_api_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        captured: dict[str, object] = {}

        def _fake_scan_role(role_path: str, **kwargs: object) -> dict[str, object]:
            captured["delegated_scan_role_role_path"] = role_path
            captured["delegated_scan_role_kwargs"] = dict(kwargs)
            return {"role_name": "repo-role"}

        def _fake_scan_repo(repo_url: str, **kwargs: object) -> dict[str, object]:
            captured["repo_url"] = repo_url
            captured["kwargs"] = dict(kwargs)
            scan_role_fn = kwargs["scan_role_fn"]
            assert callable(scan_role_fn)
            return scan_role_fn("/tmp/repo-role", role_name_override="repo-role")

        monkeypatch.setattr(api_module, "scan_role", _fake_scan_role)
        monkeypatch.setattr(
            api_module.api_non_collection,
            "scan_repo",
            _fake_scan_repo,
        )
        payload = api_module.scan_repo(
            "https://example.invalid/demo.git",
            policy_config_path="/tmp/policy.yml",
        )

    assert payload["role_name"] == "repo-role"
    assert captured["repo_url"] == "https://example.invalid/demo.git"
    assert captured["kwargs"]["policy_config_path"] == "/tmp/policy.yml"
    assert captured["delegated_scan_role_role_path"] == "/tmp/repo-role"
    assert captured["delegated_scan_role_kwargs"]["role_name_override"] == "repo-role"


def test_fsrc_api_scan_collection_delegates_to_collection_api_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        captured: dict[str, object] = {}

        def _fake_scan_role(role_path: str, **kwargs: object) -> dict[str, object]:
            captured["delegated_scan_role_role_path"] = role_path
            captured["delegated_scan_role_kwargs"] = dict(kwargs)
            return {"role_name": str(kwargs.get("role_name_override") or "role")}

        def _fake_scan_collection(
            collection_path: str,
            **kwargs: object,
        ) -> dict[str, object]:
            captured["collection_path"] = collection_path
            captured["kwargs"] = dict(kwargs)
            scan_role_fn = kwargs["scan_role_fn"]
            assert callable(scan_role_fn)
            return {
                "roles": [
                    scan_role_fn(
                        "/tmp/collection-role",
                        role_name_override="collection-role",
                    )
                ],
                "summary": {
                    "total_roles": 1,
                    "scanned_roles": 1,
                    "failed_roles": 0,
                },
            }

        monkeypatch.setattr(api_module, "scan_role", _fake_scan_role)
        monkeypatch.setattr(
            api_module.api_collection,
            "scan_collection",
            _fake_scan_collection,
        )
        payload = api_module.scan_collection(
            "/tmp/demo-collection",
            concise_readme=True,
            scanner_report_output="reports/scanner.json",
            include_scanner_report_link=False,
        )

    assert payload["summary"] == {
        "total_roles": 1,
        "scanned_roles": 1,
        "failed_roles": 0,
    }
    assert captured["collection_path"] == "/tmp/demo-collection"
    assert captured["kwargs"]["concise_readme"] is True
    assert captured["kwargs"]["scanner_report_output"] == "reports/scanner.json"
    assert captured["kwargs"]["include_scanner_report_link"] is False
    assert captured["delegated_scan_role_role_path"] == "/tmp/collection-role"
    assert (
        captured["delegated_scan_role_kwargs"]["role_name_override"]
        == "collection-role"
    )


def test_fsrc_api_run_scan_forwards_policy_config_path_to_canonical_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)
    policy_config_path = tmp_path / "policy.yml"
    policy_config_path.write_text("rules: []\n", encoding="utf-8")

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        captured: dict[str, object] = {}

        def _fake_build_run_scan_options_canonical(
            **kwargs: object,
        ) -> dict[str, object]:
            captured.update(kwargs)
            return {
                "role_path": str(role_path),
                "policy_config_path": kwargs.get("policy_config_path"),
                "strict_phase_failures": True,
            }

        def _fake_route_scan_payload_orchestration(
            **kwargs: object,
        ) -> dict[str, object]:
            return kwargs["legacy_orchestrator_fn"](
                role_path=str(role_path),
                scan_options=kwargs["scan_options"],
            )

        class _FakeContext:
            def __init__(self, **kwargs: object) -> None:
                del kwargs

            def orchestrate_scan(self) -> dict[str, object]:
                return {
                    "role_name": "tiny_role",
                    "description": "desc",
                    "requirements_display": [],
                    "undocumented_default_filters": [],
                    "display_variables": {},
                    "metadata": {"features": {"task_files_scanned": 1}},
                }

        monkeypatch.setattr(
            api_module,
            "build_run_scan_options_canonical",
            _fake_build_run_scan_options_canonical,
        )
        monkeypatch.setattr(
            api_module,
            "route_scan_payload_orchestration",
            _fake_route_scan_payload_orchestration,
        )
        monkeypatch.setattr(api_module, "ScannerContext", _FakeContext)

        payload = api_module.run_scan(
            str(role_path),
            policy_config_path=str(policy_config_path),
        )

    assert payload["role_name"] == "tiny_role"
    assert captured["policy_config_path"] == str(policy_config_path)


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
                scan_options={},
                route_preflight_runtime=(
                    api_module.api_non_collection.RoutePreflightRuntimeCarrier(
                        plugin_name="default",
                        preflight_context={
                            "plugin_runtime_marker": "preflight-used",
                            "features": {"task_files_scanned": 999},
                        },
                        routing={
                            "mode": "scan_pipeline_plugin",
                            "selected_plugin": "default",
                            "selection_order": [
                                "request.option.scan_pipeline_plugin",
                                "policy_context.selection.plugin",
                                "platform",
                                "registry_default",
                            ],
                        },
                    )
                ),
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

        class _Registry:
            def get_scan_pipeline_plugin(self, name: str):
                assert name == "custom"
                return None

        monkeypatch.setattr(api_module, "DEFAULT_PLUGIN_REGISTRY", _Registry())
        payload = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            strict_phase_failures=False,
            scan_pipeline_plugin="custom",
        )

    routing = payload["metadata"]["routing"]
    warnings = payload["metadata"].get("plugin_runtime_warnings")

    assert payload["metadata"]["features"]["task_files_scanned"] == 1
    assert "plugin_runtime_marker" not in payload["metadata"]
    assert routing == {
        "mode": "legacy_orchestrator",
        "selection_order": [
            "request.option.scan_pipeline_plugin",
            "policy_context.selection.plugin",
            "platform",
            "registry_default",
        ],
        "selected_plugin": "custom",
        "failure_mode": "selected_plugin_missing",
        "fallback_reason": "selected_plugin_missing",
        "fallback_applied": True,
    }
    assert isinstance(warnings, list)
    assert warnings
    assert warnings[0]["code"] == "scan_pipeline_plugin_missing"
    assert warnings[0]["metadata"]["routing"] == routing


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
                raise RuntimeError("plugin boom")

            def process_scan_pipeline(
                self,
                scan_options: dict[str, object],
                scan_context: dict[str, object],
            ) -> dict[str, object]:
                del scan_options
                del scan_context
                return {"plugin_enabled": True, "plugin_name": "default"}

        class _Registry:
            def get_scan_pipeline_plugin(self, _name: str):
                return _Plugin

        monkeypatch.setattr(api_module, "DEFAULT_PLUGIN_REGISTRY", _Registry())

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            api_module.run_scan(str(role_path), include_vars_main=True)

    assert exc_info.value.code == "scan_pipeline_execution_failed"
    assert exc_info.value.message == "scan-pipeline runtime execution failed"
    assert exc_info.value.detail["metadata"]["routing"]["failure_mode"] == (
        "runtime_execution_exception"
    )
    assert exc_info.value.detail["metadata"]["routing"]["selected_plugin"] == (
        "default"
    )


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
                raise RuntimeError("plugin boom")

            def process_scan_pipeline(
                self,
                scan_options: dict[str, object],
                scan_context: dict[str, object],
            ) -> dict[str, object]:
                del scan_options
                del scan_context
                return {"plugin_enabled": True, "plugin_name": "default"}

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
    assert payload["metadata"]["routing"] == {
        "failure_mode": "runtime_execution_exception",
        "selected_plugin": "default",
        "fallback_reason": "runtime_execution_exception",
        "fallback_applied": True,
    }
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

    assert exc_info.value.code == "scan_pipeline_execution_failed"
    assert exc_info.value.message == "scan-pipeline runtime execution failed"
    assert exc_info.value.detail["metadata"]["routing"]["failure_mode"] == (
        "runtime_execution_exception"
    )


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

    assert exc_info.value.code == "scan_pipeline_execution_failed"
    assert exc_info.value.message == "scan-pipeline runtime execution failed"
    assert exc_info.value.detail["metadata"]["routing"]["failure_mode"] == (
        "runtime_execution_exception"
    )
    assert exc_info.value.detail["metadata"]["routing"]["selected_plugin"] == (
        "default"
    )


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


def test_fsrc_api_run_scan_uses_policy_context_selection_plugin(
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
                policy_context = scan_options.get("policy_context")
                assert isinstance(policy_context, dict)
                assert policy_context.get("selection") == {"plugin": "custom"}
                return {
                    "plugin_enabled": True,
                    "plugin_runtime_marker": "policy-selector",
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
            policy_context={"selection": {"plugin": "custom"}},
        )

    assert payload["metadata"]["plugin_runtime_marker"] == "policy-selector"
