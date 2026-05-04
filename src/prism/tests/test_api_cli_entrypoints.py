"""Focused fsrc tests for top-level API and CLI entrypoint behavior."""

from __future__ import annotations

import importlib
import json
import sys
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest

if TYPE_CHECKING:
    from prism.api_layer.non_collection import _NormalizedNonCollectionResult

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FSRC_SOURCE_ROOT = PROJECT_ROOT / "src"


@contextmanager
def _prefer_fsrc_prism_on_sys_path() -> Iterator[None]:
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


def _expect_mapping(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return value


def _stub_non_collection_result(
    **overrides: object,
) -> "_NormalizedNonCollectionResult":
    payload: dict[str, object] = {
        "role_name": "tiny_role",
        "description": "delegated",
        "display_variables": {},
        "variables": {},
        "requirements_display": [],
        "requirements": [],
        "undocumented_default_filters": [],
        "default_filters": [],
        "metadata": {"features": {"task_files_scanned": 1}},
    }
    payload.update(overrides)
    return cast("_NormalizedNonCollectionResult", payload)


def _make_test_registry(real_registry, scan_pipeline_fn):
    """Wrap a scan-pipeline-plugin function with DI-compatible registry delegation."""

    class _TestRegistry:
        def get_scan_pipeline_plugin(self, name):
            return scan_pipeline_fn(name)

        def __getattr__(self, name):
            return getattr(real_registry, name)

        def get_default_platform_key(self):
            return real_registry.get_default_platform_key()

        def get_variable_discovery_plugin(self, key):
            result = real_registry.get_variable_discovery_plugin(key)
            if result is not None:
                return result
            fallback_key = real_registry.get_default_platform_key()
            if fallback_key and fallback_key != key:
                return real_registry.get_variable_discovery_plugin(fallback_key)
            return None

        def get_feature_detection_plugin(self, key):
            result = real_registry.get_feature_detection_plugin(key)
            if result is not None:
                return result
            fallback_key = real_registry.get_default_platform_key()
            if fallback_key and fallback_key != key:
                return real_registry.get_feature_detection_plugin(fallback_key)
            return None

    return _TestRegistry()


def _patch_api_default_registry(monkeypatch, api_module, registry) -> None:
    plugin_facade = api_module.plugin_facade
    monkeypatch.setattr(plugin_facade, "get_default_plugin_registry", lambda: registry)
    monkeypatch.setattr(
        plugin_facade,
        "get_default_scan_pipeline_registry",
        lambda: plugin_facade.isolate_scan_pipeline_registry(registry),
    )


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


def test_run_scan_basic(tmp_path: Path) -> None:
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


def test_fsrc_api_non_collection_run_scan_centralizes_default_class_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        non_collection_module = importlib.import_module(
            "prism.api_layer.non_collection"
        )
        scanner_context_module = importlib.import_module(
            "prism.scanner_core.scanner_context"
        )

        captured: dict[str, object] = {}

        class _ResolvedDIContainer:
            pass

        class _ResolvedFeatureDetector:
            pass

        class _ResolvedScannerContext:
            pass

        class _ResolvedVariableDiscovery:
            pass

        def _fake_resolve_run_scan_default_classes(
            **kwargs: object,
        ) -> tuple[object, ...]:
            captured["resolver_kwargs"] = kwargs
            return (
                _ResolvedDIContainer,
                _ResolvedFeatureDetector,
                _ResolvedScannerContext,
                _ResolvedVariableDiscovery,
            )

        def _fake_build_non_collection_run_scan_execution_request(
            **kwargs: object,
        ) -> SimpleNamespace:
            captured["builder_kwargs"] = kwargs
            return SimpleNamespace(
                role_path=str(role_path),
                scan_options={},
                strict_mode=True,
                runtime_registry=None,
                build_payload_fn=lambda: {
                    "role_name": "tiny_role",
                    "description": "desc",
                    "requirements_display": [],
                    "undocumented_default_filters": [],
                    "display_variables": {},
                    "metadata": {"features": {"task_files_scanned": 1}},
                },
            )

        monkeypatch.setattr(
            non_collection_module,
            "_resolve_run_scan_default_classes",
            _fake_resolve_run_scan_default_classes,
        )
        monkeypatch.setattr(
            scanner_context_module,
            "build_non_collection_run_scan_execution_request",
            _fake_build_non_collection_run_scan_execution_request,
        )

        payload = non_collection_module.run_scan(
            str(role_path),
            route_scan_payload_orchestration_fn=(
                lambda **kwargs: kwargs["kernel_orchestrator_fn"](
                    role_path=str(role_path),
                    scan_options={},
                )
            ),
            orchestrate_scan_payload_with_selected_plugin_fn=(
                lambda **kwargs: kwargs["build_payload_fn"]()
            ),
        )

    assert payload["role_name"] == "tiny_role"
    assert captured["resolver_kwargs"] == {
        "di_container_cls": None,
        "feature_detector_cls": None,
        "scanner_context_cls": None,
        "variable_discovery_cls": None,
    }
    builder_kwargs = _expect_mapping(captured["builder_kwargs"])
    assert builder_kwargs["di_container_cls"] is _ResolvedDIContainer
    assert builder_kwargs["feature_detector_cls"] is _ResolvedFeatureDetector
    assert builder_kwargs["scanner_context_cls"] is _ResolvedScannerContext
    assert builder_kwargs["variable_discovery_cls"] is _ResolvedVariableDiscovery


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
    metadata = _expect_mapping(payload["metadata"])
    features = _expect_mapping(metadata["features"])
    assert features["task_files_scanned"] == 3


def test_fsrc_api_run_scan_delegates_to_non_collection_api_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    policy_path = tmp_path / "policy.yml"
    _build_tiny_role(role_path)
    policy_path.write_text("policy: true\n", encoding="utf-8")

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        captured: dict[str, object] = {}

        def _fake_run_scan(
            role_path: str, **kwargs: object
        ) -> "_NormalizedNonCollectionResult":
            captured["role_path"] = role_path
            captured["kwargs"] = dict(kwargs)
            return _stub_non_collection_result()

        monkeypatch.setattr(api_module.api_non_collection, "run_scan", _fake_run_scan)
        payload = api_module.run_scan(
            str(role_path),
            policy_config_path=str(policy_path),
            scan_pipeline_plugin="custom",
        )

    assert payload["role_name"] == "tiny_role"
    assert api_module.API_RETAINED_COMPATIBILITY_SEAMS == ("run_scan",)
    assert captured["role_path"] == str(role_path)
    delegated_kwargs = _expect_mapping(captured["kwargs"])
    assert delegated_kwargs["policy_config_path"] == str(policy_path)
    assert delegated_kwargs["scan_pipeline_plugin"] == "custom"
    assert not hasattr(api_module, "NormalizedNonCollectionResult")


def test_fsrc_api_run_scan_threads_scanner_context_cls_without_di_backfill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        scanner_core_di_module = importlib.import_module("prism.scanner_core.di")
        monkeypatch.delattr(
            scanner_core_di_module,
            "ScannerContext",
            raising=False,
        )

        captured: dict[str, object] = {}

        def _fake_run_scan(
            role_path: str, **kwargs: object
        ) -> "_NormalizedNonCollectionResult":
            captured["role_path"] = role_path
            captured["kwargs"] = dict(kwargs)
            captured["di_has_scanner_context"] = hasattr(
                scanner_core_di_module,
                "ScannerContext",
            )
            return _stub_non_collection_result()

        monkeypatch.setattr(api_module.api_non_collection, "run_scan", _fake_run_scan)
        payload = api_module.run_scan(str(role_path), include_vars_main=True)

    assert payload["role_name"] == "tiny_role"
    assert captured["role_path"] == str(role_path)
    assert captured["di_has_scanner_context"] is False
    delegated_kwargs = _expect_mapping(captured["kwargs"])
    assert delegated_kwargs["scanner_context_cls"] is api_module.ScannerContext
    assert not hasattr(scanner_core_di_module, "ScannerContext")


def test_fsrc_api_run_scan_normalizes_payload_shape_from_non_collection_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        def _route(
            *,
            role_path: str,
            scan_options: dict[str, object],
            kernel_orchestrator_fn: object,
            registry: object | None = None,
        ) -> dict[str, object]:
            del role_path
            del scan_options
            del registry
            del kernel_orchestrator_fn
            return {
                "role_name": "tiny_role",
                "description": "desc",
                "display_variables": {"demo_var": {"default": "value"}},
                "requirements_display": [{"name": "ansible-core"}],
                "undocumented_default_filters": ["default"],
                "metadata": {"features": {"task_files_scanned": 1}},
            }

        monkeypatch.setattr(
            api_module.api_non_collection, "route_scan_payload_orchestration", _route
        )

        payload = api_module.run_scan(str(role_path), include_vars_main=True)

    display_variables = _expect_mapping(payload["display_variables"])
    demo_var = _expect_mapping(display_variables["demo_var"])
    assert demo_var["default"] == "value"
    variables = _expect_mapping(payload["variables"])
    normalized_demo_var = _expect_mapping(variables["demo_var"])
    assert normalized_demo_var["default"] == "value"
    assert payload["requirements"] == [{"name": "ansible-core"}]
    assert payload["default_filters"] == ["default"]


def test_fsrc_api_scan_role_delegates_to_non_collection_api_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy_path = tmp_path / "policy.yml"
    policy_path.write_text("policy: true\n", encoding="utf-8")

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        captured: dict[str, object] = {}

        def _fake_run_scan(
            role_path: str, **kwargs: object
        ) -> "_NormalizedNonCollectionResult":
            captured["delegated_run_scan_role_path"] = role_path
            captured["delegated_run_scan_kwargs"] = dict(kwargs)
            return _stub_non_collection_result(role_name="delegated-role")

        def _fake_scan_role(
            role_path: str, **kwargs: object
        ) -> "_NormalizedNonCollectionResult":
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
            policy_config_path=str(policy_path),
        )

    assert payload["role_name"] == "delegated-role"
    assert captured["role_path"] == "/tmp/demo-role"
    delegated_kwargs = _expect_mapping(captured["kwargs"])
    assert delegated_kwargs["policy_config_path"] == str(policy_path)
    assert captured["delegated_run_scan_role_path"] == "/tmp/demo-role"
    assert (
        _expect_mapping(captured["delegated_run_scan_kwargs"])["role_name_override"]
        == "delegated-role"
    )


def test_fsrc_api_scan_repo_delegates_to_non_collection_api_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy_path = tmp_path / "policy.yml"
    policy_path.write_text("policy: true\n", encoding="utf-8")

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        captured: dict[str, object] = {}

        def _fake_scan_role(
            role_path: str, **kwargs: object
        ) -> "_NormalizedNonCollectionResult":
            captured["delegated_scan_role_role_path"] = role_path
            captured["delegated_scan_role_kwargs"] = dict(kwargs)
            return _stub_non_collection_result(role_name="repo-role")

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
            policy_config_path=str(policy_path),
        )

    assert payload["role_name"] == "repo-role"
    assert captured["repo_url"] == "https://example.invalid/demo.git"
    delegated_kwargs = _expect_mapping(captured["kwargs"])
    assert delegated_kwargs["policy_config_path"] == str(policy_path)
    assert captured["delegated_scan_role_role_path"] == "/tmp/repo-role"
    assert (
        _expect_mapping(captured["delegated_scan_role_kwargs"])["role_name_override"]
        == "repo-role"
    )


def test_fsrc_api_scan_collection_delegates_to_collection_api_layer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        captured: dict[str, object] = {}

        def _fake_scan_role(
            role_path: str, **kwargs: object
        ) -> "_NormalizedNonCollectionResult":
            captured["delegated_scan_role_role_path"] = role_path
            captured["delegated_scan_role_kwargs"] = dict(kwargs)
            return _stub_non_collection_result(
                role_name=str(kwargs.get("role_name_override") or "role")
            )

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
    delegated_kwargs = _expect_mapping(captured["kwargs"])
    assert delegated_kwargs["concise_readme"] is True
    assert delegated_kwargs["scanner_report_output"] == "reports/scanner.json"
    assert delegated_kwargs["include_scanner_report_link"] is False
    assert captured["delegated_scan_role_role_path"] == "/tmp/collection-role"
    assert (
        _expect_mapping(captured["delegated_scan_role_kwargs"])["role_name_override"]
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
            kernel_orchestrator_fn = cast(object, kwargs["kernel_orchestrator_fn"])
            assert callable(kernel_orchestrator_fn)
            return kernel_orchestrator_fn(
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
            api_module.api_non_collection,
            "build_run_scan_options_canonical",
            _fake_build_run_scan_options_canonical,
        )
        monkeypatch.setattr(
            api_module.api_non_collection,
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


@pytest.mark.parametrize(
    ("api_name", "kwargs"),
    [
        (
            "run_scan",
            {
                "role_path": "/tmp/demo-role",
                "style_readme_path": "../../../tmp/style.md",
                "policy_config_path": "/tmp/policy.yml",
                "readme_config_path": "/tmp/readme.yml",
                "style_source_path": "/tmp/style-source.md",
                "compare_role_path": "/tmp/compare-role",
                "vars_seed_paths": ["/tmp/vars.yml"],
            },
        ),
        (
            "scan_role",
            {
                "role_path": "/tmp/demo-role",
                "style_readme_path": "../../../tmp/style.md",
                "policy_config_path": "/tmp/policy.yml",
                "readme_config_path": "/tmp/readme.yml",
                "style_source_path": "/tmp/style-source.md",
                "compare_role_path": "/tmp/compare-role",
                "vars_seed_paths": ["/tmp/vars.yml"],
            },
        ),
        (
            "scan_collection",
            {
                "collection_path": "/tmp/demo-collection",
                "style_readme_path": "../../../tmp/style.md",
                "policy_config_path": "/tmp/policy.yml",
                "readme_config_path": "/tmp/readme.yml",
                "style_source_path": "/tmp/style-source.md",
                "compare_role_path": "/tmp/compare-role",
                "vars_seed_paths": ["/tmp/vars.yml"],
            },
        ),
        (
            "scan_repo",
            {
                "repo_url": "https://example.invalid/demo.git",
                "repo_role_path": "/tmp/repo-role",
                "repo_style_readme_path": "../../../tmp/repo-style.md",
                "style_readme_path": "/tmp/style.md",
                "policy_config_path": "/tmp/policy.yml",
                "readme_config_path": "/tmp/readme.yml",
                "style_source_path": "/tmp/style-source.md",
                "compare_role_path": "/tmp/compare-role",
                "vars_seed_paths": ["/tmp/vars.yml"],
            },
        ),
    ],
)
def test_fsrc_api_public_entrypoints_reject_unsafe_sibling_file_inputs(
    api_name: str,
    kwargs: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readme_path = tmp_path / "readme.yml"
    policy_path = tmp_path / "policy.yml"
    readme_path.write_text("readme: true\n", encoding="utf-8")
    policy_path.write_text("policy: true\n", encoding="utf-8")
    kwargs = dict(kwargs)
    kwargs["readme_config_path"] = str(readme_path)
    kwargs["policy_config_path"] = str(policy_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        errors_module = importlib.import_module("prism.errors")

        if api_name == "run_scan":
            monkeypatch.setattr(
                api_module.api_non_collection,
                "run_scan",
                lambda *args, **inner_kwargs: (_ for _ in ()).throw(
                    AssertionError("delegation should not run")
                ),
            )
        elif api_name == "scan_role":
            monkeypatch.setattr(
                api_module.api_non_collection,
                "scan_role",
                lambda *args, **inner_kwargs: (_ for _ in ()).throw(
                    AssertionError("delegation should not run")
                ),
            )
        elif api_name == "scan_collection":
            monkeypatch.setattr(
                api_module.api_collection,
                "scan_collection",
                lambda *args, **inner_kwargs: (_ for _ in ()).throw(
                    AssertionError("delegation should not run")
                ),
            )
        else:
            monkeypatch.setattr(
                api_module.api_non_collection,
                "scan_repo",
                lambda *args, **inner_kwargs: (_ for _ in ()).throw(
                    AssertionError("delegation should not run")
                ),
            )

        api_fn = getattr(api_module, api_name)
        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            api_fn(**kwargs)

    assert exc_info.value.code == "role_path_traversal_rejected"


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
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            called["route"] = True
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(
            api_module.api_non_collection, "route_scan_payload_orchestration", _route
        )
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
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
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

        monkeypatch.setattr(
            api_module.api_non_collection, "route_scan_payload_orchestration", _route
        )
        _registry = _make_test_registry(
            api_module.plugin_facade.get_default_plugin_registry(), lambda _n: _Plugin
        )
        _patch_api_default_registry(monkeypatch, api_module, _registry)
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
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(
            api_module.api_non_collection, "route_scan_payload_orchestration", _route
        )

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

        _registry = _make_test_registry(
            api_module.plugin_facade.get_default_plugin_registry(),
            lambda name: _Plugin if name == "default" else None,
        )
        _patch_api_default_registry(monkeypatch, api_module, _registry)
        payload = api_module.run_scan(str(role_path), include_vars_main=True)

    assert _Plugin.called is True
    assert payload["metadata"]["plugin_runtime_marker"] == "applied"
    assert payload["metadata"]["features"]["task_files_scanned"] == 1


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
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(
            api_module.api_non_collection, "route_scan_payload_orchestration", _route
        )

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

        _registry = _make_test_registry(
            api_module.plugin_facade.get_default_plugin_registry(), lambda _n: _Plugin
        )
        _patch_api_default_registry(monkeypatch, api_module, _registry)

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
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(
            api_module.api_non_collection, "route_scan_payload_orchestration", _route
        )

        def _boom(_name):
            raise RuntimeError("registry boom")

        _registry = _make_test_registry(
            api_module.plugin_facade.get_default_plugin_registry(), _boom
        )
        _patch_api_default_registry(monkeypatch, api_module, _registry)

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
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(
            api_module.api_non_collection, "route_scan_payload_orchestration", _route
        )

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

        _registry = _make_test_registry(
            api_module.plugin_facade.get_default_plugin_registry(), lambda _n: _Plugin
        )
        _patch_api_default_registry(monkeypatch, api_module, _registry)
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
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(
            api_module.api_non_collection, "route_scan_payload_orchestration", _route
        )

        class _Plugin:
            def process_scan_pipeline(
                self,
                scan_options: dict[str, object],
                scan_context: dict[str, object],
            ) -> dict[str, object]:
                del scan_context
                scan_options["strict_phase_failures"] = False
                raise RuntimeError("plugin boom")

        _registry = _make_test_registry(
            api_module.plugin_facade.get_default_plugin_registry(), lambda _n: _Plugin
        )
        _patch_api_default_registry(monkeypatch, api_module, _registry)

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


def test_fsrc_api_run_scan_plugin_nested_policy_context_mutation_is_isolated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    caller_policy_context = {
        "selection": {"plugin": "default"},
        "nested": {"original": True},
    }

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        class _Plugin:
            def process_scan_pipeline(
                self,
                scan_options: dict[str, object],
                scan_context: dict[str, object],
            ) -> dict[str, object]:
                del scan_context
                policy_context = scan_options.get("policy_context")
                assert isinstance(policy_context, dict)
                nested = policy_context.get("nested")
                assert isinstance(nested, dict)
                nested["mutated_by_plugin"] = True
                return {"plugin_enabled": True, "plugin_name": "default"}

        _registry = _make_test_registry(
            api_module.plugin_facade.get_default_plugin_registry(),
            lambda _n: _Plugin,
        )
        _patch_api_default_registry(monkeypatch, api_module, _registry)

        payload = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            policy_context=caller_policy_context,
        )

    assert payload["role_name"] == "tiny_role"
    assert caller_policy_context == {
        "selection": {"plugin": "default"},
        "nested": {"original": True},
    }


def test_fsrc_api_run_scan_strict_phase_failures_rejects_malformed_value(
    tmp_path: Path,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        with pytest.raises(ValueError, match="strict_phase_failures"):
            api_module.run_scan(
                str(role_path),
                include_vars_main=True,
                strict_phase_failures="false",
            )


def test_fsrc_api_run_scan_strict_phase_failures_preserves_false_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        captured: dict[str, object] = {}

        def _fake_run_scan(
            delegated_role_path: str,
            **kwargs: object,
        ) -> "_NormalizedNonCollectionResult":
            captured["role_path"] = delegated_role_path
            captured["strict_phase_failures"] = kwargs["strict_phase_failures"]
            return _stub_non_collection_result()

        monkeypatch.setattr(api_module.api_non_collection, "run_scan", _fake_run_scan)

        payload = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            strict_phase_failures=False,
        )

    assert payload["role_name"] == "tiny_role"
    assert captured["role_path"] == str(role_path)
    assert captured["strict_phase_failures"] is False


def test_fsrc_cli_main_runs_scan_and_emits_json(tmp_path: Path, capsys) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")
        exit_code = cli_module.main(
            ["role", str(role_path), "--format", "json", "--dry-run"]
        )

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


@pytest.mark.parametrize(
    ("field_name", "kwargs"),
    [
        ("readme_config_path", {"readme_config_path": "missing-readme.yml"}),
        ("policy_config_path", {"policy_config_path": "missing-policy.yml"}),
    ],
)
def test_fsrc_api_run_scan_rejects_missing_config_paths(
    tmp_path: Path,
    field_name: str,
    kwargs: dict[str, str],
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        errors_module = importlib.import_module("prism.errors")

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            api_module.run_scan(
                str(role_path),
                include_vars_main=True,
                **kwargs,
            )

    assert exc_info.value.code == "scan_input_path_not_found"
    assert exc_info.value.detail == {
        "field": field_name,
        "value": kwargs[field_name],
    }


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
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(
            api_module.api_non_collection, "route_scan_payload_orchestration", _route
        )

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

        _registry = _make_test_registry(
            api_module.plugin_facade.get_default_plugin_registry(),
            lambda name: _Plugin if name == "custom" else None,
        )
        _patch_api_default_registry(monkeypatch, api_module, _registry)
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
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(
            api_module.api_non_collection, "route_scan_payload_orchestration", _route
        )

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

        _registry = _make_test_registry(
            api_module.plugin_facade.get_default_plugin_registry(),
            lambda name: _Plugin if name == "custom" else None,
        )
        _patch_api_default_registry(monkeypatch, api_module, _registry)
        payload = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            policy_context={"selection": {"plugin": "custom"}},
        )

    assert payload["metadata"]["plugin_runtime_marker"] == "policy-selector"


def test_fsrc_api_run_scan_uses_per_call_default_registry_resolver(
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
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(
            api_module.api_non_collection, "route_scan_payload_orchestration", _route
        )

        class _Plugin:
            def process_scan_pipeline(
                self,
                scan_options: dict[str, object],
                scan_context: dict[str, object],
            ) -> dict[str, object]:
                del scan_options
                del scan_context
                return {"plugin_runtime_marker": "resolver-used"}

        real_registry = api_module.plugin_facade.get_default_plugin_registry()
        _registry = _make_test_registry(
            real_registry,
            lambda name: _Plugin if name == "default" else None,
        )

        class _PoisonRegistry:
            def get_scan_pipeline_plugin(self, name: str):
                raise AssertionError(
                    f"plugin_facade registry should not be bypassed for {name}"
                )

            def __getattr__(self, name: str):
                return getattr(real_registry, name)

        monkeypatch.setattr(
            api_module.plugin_facade,
            "get_default_plugin_registry",
            lambda: _PoisonRegistry(),
        )
        _patch_api_default_registry(monkeypatch, api_module, _registry)

        payload = api_module.run_scan(str(role_path), include_vars_main=True)

    assert payload["metadata"]["plugin_runtime_marker"] == "resolver-used"


def test_fsrc_api_run_scan_uses_plugin_facade_scan_pipeline_registry_seam(
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
            kernel_orchestrator_fn,
            registry=None,
        ):
            del role_path
            del scan_options
            del registry
            return kernel_orchestrator_fn(role_path="/tmp/ignored", scan_options={})

        monkeypatch.setattr(
            api_module.api_non_collection, "route_scan_payload_orchestration", _route
        )

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
                return {"plugin_runtime_marker": "facade-isolation"}

        real_registry = api_module.plugin_facade.get_default_plugin_registry()
        isolated_registry = _make_test_registry(
            real_registry,
            lambda name: _Plugin if name == "default" else None,
        )
        seam_calls: list[str] = []

        class _PoisonRegistry:
            def get_scan_pipeline_plugin(self, name: str):
                raise AssertionError(f"api.py bypassed plugin_facade seam for {name}")

            def __getattr__(self, name: str):
                return getattr(real_registry, name)

        monkeypatch.setattr(
            api_module.plugin_facade,
            "get_default_plugin_registry",
            lambda: _PoisonRegistry(),
        )

        def _fake_get_default_scan_pipeline_registry():
            seam_calls.append("used")
            return api_module.plugin_facade.isolate_scan_pipeline_registry(
                isolated_registry
            )

        monkeypatch.setattr(
            api_module.plugin_facade,
            "get_default_scan_pipeline_registry",
            _fake_get_default_scan_pipeline_registry,
        )

        payload = api_module.run_scan(str(role_path), include_vars_main=True)

    assert seam_calls == ["used"]
    assert not hasattr(api_module, "_isolate_scan_pipeline_registry")
    assert not hasattr(api_module, "_wrap_scan_pipeline_plugin_factory")
    assert payload["metadata"]["plugin_runtime_marker"] == "facade-isolation"
    assert payload["metadata"]["features"]["task_files_scanned"] == 1


def test_fsrc_plugin_facade_isolates_orchestrated_payload_mutation() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        class _Plugin:
            def orchestrate_scan_payload(
                self,
                *,
                payload: dict[str, object],
                scan_options: dict[str, object],
                strict_mode: bool,
                preflight_context: dict[str, object] | None = None,
            ) -> dict[str, object]:
                del scan_options
                del strict_mode
                del preflight_context
                metadata = payload.get("metadata")
                assert isinstance(metadata, dict)
                features = metadata.get("features")
                assert isinstance(features, dict)
                features["task_files_scanned"] = 999
                payload["plugin_runtime_marker"] = "facade-payload-isolation"
                return payload

            def process_scan_pipeline(
                self,
                scan_options: dict[str, object],
                scan_context: dict[str, object],
            ) -> dict[str, object]:
                del scan_options
                del scan_context
                return {"plugin_enabled": True, "plugin_name": "default"}

        isolated_registry = _make_test_registry(
            api_module.plugin_facade.get_default_plugin_registry(),
            lambda name: _Plugin if name == "default" else None,
        )
        registry = api_module.plugin_facade.isolate_scan_pipeline_registry(
            isolated_registry
        )
        plugin_factory = registry.get_scan_pipeline_plugin("default")

    assert plugin_factory is not None
    plugin = plugin_factory()
    payload = {
        "metadata": {"features": {"task_files_scanned": 1}},
        "results": {"items": ["kept"]},
    }

    result = plugin.orchestrate_scan_payload(
        payload=payload,
        scan_options={},
        strict_mode=True,
    )

    assert result["plugin_runtime_marker"] == "facade-payload-isolation"
    assert result["metadata"]["features"]["task_files_scanned"] == 999
    assert payload == {
        "metadata": {"features": {"task_files_scanned": 1}},
        "results": {"items": ["kept"]},
    }


def test_fsrc_plugin_facade_preserves_orchestration_for_callable_factories() -> None:
    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        class _Plugin:
            def orchestrate_scan_payload(
                self,
                *,
                payload: dict[str, object],
                scan_options: dict[str, object],
                strict_mode: bool,
                preflight_context: dict[str, object] | None = None,
            ) -> dict[str, object]:
                del scan_options
                del strict_mode
                del preflight_context
                payload["plugin_runtime_marker"] = "callable-factory-orchestrated"
                return payload

            def process_scan_pipeline(
                self,
                scan_options: dict[str, object],
                scan_context: dict[str, object],
            ) -> dict[str, object]:
                del scan_options
                del scan_context
                return {"plugin_enabled": True, "plugin_name": "default"}

        def _factory() -> _Plugin:
            return _Plugin()

        isolated_registry = _make_test_registry(
            api_module.plugin_facade.get_default_plugin_registry(),
            lambda name: _factory if name == "default" else None,
        )
        registry = api_module.plugin_facade.isolate_scan_pipeline_registry(
            isolated_registry
        )
        plugin_factory = registry.get_scan_pipeline_plugin("default")

    assert plugin_factory is not None
    plugin = plugin_factory()
    payload = {
        "metadata": {"features": {"task_files_scanned": 1}},
        "results": {"items": ["kept"]},
    }

    result = plugin.orchestrate_scan_payload(
        payload=payload,
        scan_options={},
        strict_mode=True,
    )

    assert result["plugin_runtime_marker"] == "callable-factory-orchestrated"
    assert payload == {
        "metadata": {"features": {"task_files_scanned": 1}},
        "results": {"items": ["kept"]},
    }


def test_fsrc_api_run_scan_preserves_reserved_platform_classification_through_scan_pipeline_registry_seam(
    tmp_path: Path,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        errors_module = importlib.import_module("prism.errors")

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            api_module.run_scan(
                str(role_path),
                include_vars_main=True,
                scan_pipeline_plugin="terraform",
            )

    assert exc_info.value.code == "platform_not_supported"


def test_fsrc_api_run_scan_cache_key_preserves_missing_prepared_policy_bundle_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        scanner_context_module = importlib.import_module(
            "prism.scanner_core.scanner_context"
        )
        scan_cache_module = importlib.import_module("prism.scanner_core.scan_cache")

        captured: dict[str, object] = {}

        def _build_execution_request(**kwargs: object) -> SimpleNamespace:
            del kwargs
            return SimpleNamespace(
                role_path=str(role_path),
                scan_options={
                    "role_path": str(role_path),
                    "strict_phase_failures": True,
                },
                build_payload_fn=None,
                strict_mode=True,
                runtime_registry=object(),
            )

        def _route(
            *,
            role_path: str,
            scan_options: dict[str, object],
            kernel_orchestrator_fn,
            registry=None,
        ) -> dict[str, object]:
            del role_path
            del scan_options
            del kernel_orchestrator_fn
            del registry
            return {
                "role_name": "tiny_role",
                "description": "desc",
                "display_variables": {},
                "requirements_display": [],
                "undocumented_default_filters": [],
                "metadata": {"features": {"task_files_scanned": 1}},
            }

        class _CacheBackend:
            def get(self, key: str) -> None:
                captured["cache_get_key"] = key
                return None

            def set(self, key: str, value: dict[str, object]) -> None:
                captured["cache_set_key"] = key
                captured["cache_set_value"] = value

        def _compute_scan_cache_key(
            *,
            role_content_hash: str,
            scan_options: dict[str, object],
        ) -> str:
            captured["role_content_hash"] = role_content_hash
            captured["scan_options"] = dict(scan_options)
            return "cache-key"

        monkeypatch.setattr(
            scanner_context_module,
            "build_non_collection_run_scan_execution_request",
            _build_execution_request,
        )
        monkeypatch.setattr(
            api_module.api_non_collection, "route_scan_payload_orchestration", _route
        )
        monkeypatch.setattr(
            scan_cache_module,
            "compute_role_content_hash",
            lambda path: "role-hash",
        )
        monkeypatch.setattr(
            scan_cache_module,
            "compute_scan_cache_key",
            _compute_scan_cache_key,
        )
        monkeypatch.setattr(
            scan_cache_module,
            "compute_path_content_hash",
            lambda path: "path-hash",
        )

        payload = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            cache_backend=_CacheBackend(),
        )

    assert payload["role_name"] == "tiny_role"
    scan_options = captured["scan_options"]
    assert isinstance(scan_options, dict)
    assert scan_options["__prepared_policy_bundle_state__"] == "missing"
    assert "__bundle_fingerprint__" not in scan_options
    assert "prepared_policy_bundle" not in scan_options


def test_fsrc_api_run_scan_cache_key_marks_malformed_prepared_policy_bundle_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        scanner_context_module = importlib.import_module(
            "prism.scanner_core.scanner_context"
        )
        scan_cache_module = importlib.import_module("prism.scanner_core.scan_cache")

        captured: dict[str, object] = {}

        def _build_execution_request(**kwargs: object) -> SimpleNamespace:
            del kwargs
            return SimpleNamespace(
                role_path=str(role_path),
                scan_options={
                    "role_path": str(role_path),
                    "strict_phase_failures": True,
                    "prepared_policy_bundle": {
                        "task_line_parsing": {},
                        "jinja_analysis": {},
                    },
                },
                build_payload_fn=None,
                strict_mode=True,
                runtime_registry=object(),
            )

        def _route(
            *,
            role_path: str,
            scan_options: dict[str, object],
            kernel_orchestrator_fn,
            registry=None,
        ) -> dict[str, object]:
            del role_path
            del scan_options
            del kernel_orchestrator_fn
            del registry
            return {
                "role_name": "tiny_role",
                "description": "desc",
                "display_variables": {},
                "requirements_display": [],
                "undocumented_default_filters": [],
                "metadata": {"features": {"task_files_scanned": 1}},
            }

        class _CacheBackend:
            def get(self, key: str) -> None:
                captured["cache_get_key"] = key
                return None

            def set(self, key: str, value: dict[str, object]) -> None:
                captured["cache_set_key"] = key
                captured["cache_set_value"] = value

        def _compute_scan_cache_key(
            *,
            role_content_hash: str,
            scan_options: dict[str, object],
        ) -> str:
            captured["role_content_hash"] = role_content_hash
            captured["scan_options"] = dict(scan_options)
            return "cache-key"

        monkeypatch.setattr(
            scanner_context_module,
            "build_non_collection_run_scan_execution_request",
            _build_execution_request,
        )
        monkeypatch.setattr(
            api_module.api_non_collection, "route_scan_payload_orchestration", _route
        )
        monkeypatch.setattr(
            scan_cache_module,
            "compute_role_content_hash",
            lambda path: "role-hash",
        )
        monkeypatch.setattr(
            scan_cache_module,
            "compute_scan_cache_key",
            _compute_scan_cache_key,
        )
        monkeypatch.setattr(
            scan_cache_module,
            "compute_path_content_hash",
            lambda path: "path-hash",
        )

        payload = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            cache_backend=_CacheBackend(),
        )

    assert payload["role_name"] == "tiny_role"
    scan_options = captured["scan_options"]
    assert isinstance(scan_options, dict)
    assert scan_options["__prepared_policy_bundle_state__"] == "malformed"
    assert "__bundle_fingerprint__" not in scan_options
    assert "prepared_policy_bundle" not in scan_options


def test_fsrc_api_run_scan_bypasses_cache_for_uncacheable_prepared_policy_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        scanner_context_module = importlib.import_module(
            "prism.scanner_core.scanner_context"
        )
        scan_cache_module = importlib.import_module("prism.scanner_core.scan_cache")

        class _StatefulTaskLinePolicy:
            TASK_INCLUDE_KEYS = ("include_tasks",)
            ROLE_INCLUDE_KEYS = ("include_role",)
            INCLUDE_VARS_KEYS = ("include_vars",)
            SET_FACT_KEYS = ("set_fact",)
            TASK_BLOCK_KEYS = ("block",)
            TASK_META_KEYS = ("name",)

            def __init__(self, marker: str) -> None:
                self.marker = marker

            def detect_task_module(self, task: dict[str, object]) -> str | None:
                del task
                return self.marker

        class _StatefulJinjaPolicy:
            def __init__(self, marker: str) -> None:
                self.marker = marker

            def collect_undeclared_jinja_variables(self, text: str) -> set[str]:
                del text
                return {self.marker}

        cache_calls: list[str] = []

        def _build_execution_request(**kwargs: object) -> SimpleNamespace:
            del kwargs
            return SimpleNamespace(
                role_path=str(role_path),
                scan_options={
                    "role_path": str(role_path),
                    "strict_phase_failures": True,
                    "prepared_policy_bundle": {
                        "task_line_parsing": _StatefulTaskLinePolicy("first"),
                        "jinja_analysis": _StatefulJinjaPolicy("first"),
                    },
                },
                build_payload_fn=None,
                strict_mode=True,
                runtime_registry=object(),
            )

        def _route(
            *,
            role_path: str,
            scan_options: dict[str, object],
            kernel_orchestrator_fn,
            registry=None,
        ) -> dict[str, object]:
            del role_path
            del scan_options
            del kernel_orchestrator_fn
            del registry
            return {
                "role_name": "tiny_role",
                "description": "desc",
                "display_variables": {},
                "requirements_display": [],
                "undocumented_default_filters": [],
                "metadata": {"features": {"task_files_scanned": 1}},
            }

        class _CacheBackend:
            def get(self, key: str) -> None:
                cache_calls.append(f"get:{key}")
                return None

            def set(self, key: str, value: dict[str, object]) -> None:
                del value
                cache_calls.append(f"set:{key}")

        monkeypatch.setattr(
            scanner_context_module,
            "build_non_collection_run_scan_execution_request",
            _build_execution_request,
        )
        monkeypatch.setattr(
            api_module.api_non_collection, "route_scan_payload_orchestration", _route
        )
        monkeypatch.setattr(
            scan_cache_module,
            "compute_role_content_hash",
            lambda path: "role-hash",
        )
        monkeypatch.setattr(
            scan_cache_module,
            "compute_scan_cache_key",
            lambda **kwargs: (_ for _ in ()).throw(
                AssertionError(
                    "uncacheable prepared_policy_bundle should skip cache key computation"
                )
            ),
        )

        payload = api_module.run_scan(
            str(role_path),
            include_vars_main=True,
            cache_backend=_CacheBackend(),
        )

    assert payload["role_name"] == "tiny_role"
    assert cache_calls == []


def test_fsrc_api_run_scan_cache_key_tracks_runtime_wiring_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        scanner_context_module = importlib.import_module(
            "prism.scanner_core.scanner_context"
        )
        scan_cache_module = importlib.import_module("prism.scanner_core.scan_cache")

        runtime_registry = object()
        captured: dict[str, object] = {}

        def _build_execution_request(**kwargs: object) -> SimpleNamespace:
            del kwargs
            return SimpleNamespace(
                role_path=str(role_path),
                scan_options={
                    "role_path": str(role_path),
                    "strict_phase_failures": True,
                },
                build_payload_fn=None,
                strict_mode=True,
                runtime_registry=runtime_registry,
            )

        def _route(
            *,
            role_path: str,
            scan_options: dict[str, object],
            kernel_orchestrator_fn,
            registry=None,
        ) -> dict[str, object]:
            del role_path
            del scan_options
            del kernel_orchestrator_fn
            del registry
            return {
                "role_name": "tiny_role",
                "description": "desc",
                "display_variables": {},
                "requirements_display": [],
                "undocumented_default_filters": [],
                "metadata": {"features": {"task_files_scanned": 1}},
            }

        def _orchestrate(**kwargs: object) -> dict[str, object]:
            del kwargs
            return {}

        class _CacheBackend:
            def get(self, key: str) -> None:
                captured["cache_get_key"] = key
                return None

            def set(self, key: str, value: dict[str, object]) -> None:
                captured["cache_set_key"] = key
                captured["cache_set_value"] = value

        def _compute_scan_cache_key(
            *,
            role_content_hash: str,
            scan_options: dict[str, object],
        ) -> str:
            captured["role_content_hash"] = role_content_hash
            captured["scan_options"] = dict(scan_options)
            return "cache-key"

        monkeypatch.setattr(
            scanner_context_module,
            "build_non_collection_run_scan_execution_request",
            _build_execution_request,
        )
        monkeypatch.setattr(
            scan_cache_module,
            "compute_role_content_hash",
            lambda path: "role-hash",
        )
        monkeypatch.setattr(
            scan_cache_module,
            "compute_scan_cache_key",
            _compute_scan_cache_key,
        )
        monkeypatch.setattr(
            scan_cache_module,
            "compute_path_content_hash",
            lambda path: "path-hash",
        )

        payload = api_module.api_non_collection.run_scan(
            str(role_path),
            include_vars_main=True,
            cache_backend=_CacheBackend(),
            route_scan_payload_orchestration_fn=_route,
            orchestrate_scan_payload_with_selected_plugin_fn=_orchestrate,
        )

    assert payload["role_name"] == "tiny_role"
    scan_options = captured["scan_options"]
    assert isinstance(scan_options, dict)
    runtime_wiring = scan_options["__runtime_wiring_identity__"]
    assert isinstance(runtime_wiring, dict)
    route_identity = runtime_wiring["route_scan_payload_orchestration_fn"]
    assert isinstance(route_identity, str)
    assert "_route@" in route_identity
    orchestrate_identity = runtime_wiring[
        "orchestrate_scan_payload_with_selected_plugin_fn"
    ]
    assert isinstance(orchestrate_identity, str)
    assert "_orchestrate@" in orchestrate_identity
    runtime_registry_identity = runtime_wiring["runtime_registry"]
    assert isinstance(runtime_registry_identity, str)
    assert runtime_registry_identity.endswith(f"@{id(runtime_registry)}")


def test_fsrc_non_collection_run_scan_uses_canonical_policy_bundle_fn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_non_collection = importlib.import_module("prism.api_layer.non_collection")
        scanner_context_module = importlib.import_module(
            "prism.scanner_core.scanner_context"
        )

        captured: dict[str, object] = {}
        canonical_calls: list[tuple[dict[str, object], object]] = []

        def _canonical_ensure(
            *,
            scan_options: dict[str, object],
            di: object,
        ) -> dict[str, object]:
            canonical_calls.append((scan_options, di))
            return {"prepared": True}

        monkeypatch.setattr(
            api_non_collection.plugin_facade,
            "ensure_prepared_policy_bundle",
            _canonical_ensure,
        )

        def _build_execution_request(**kwargs: object) -> SimpleNamespace:
            captured["ensure_prepared_policy_bundle_fn"] = kwargs[
                "ensure_prepared_policy_bundle_fn"
            ]
            return SimpleNamespace(
                role_path=str(role_path),
                scan_options={"role_path": str(role_path)},
                build_payload_fn=lambda: {
                    "role_name": "tiny_role",
                    "description": "desc",
                    "display_variables": {},
                    "requirements_display": [],
                    "undocumented_default_filters": [],
                    "metadata": {"features": {"task_files_scanned": 1}},
                },
                strict_mode=True,
                runtime_registry=object(),
            )

        def _route(
            *,
            role_path: str,
            scan_options: dict[str, object],
            kernel_orchestrator_fn,
            registry: object | None = None,
        ) -> dict[str, object]:
            del registry
            return kernel_orchestrator_fn(
                role_path=str(role_path),
                scan_options=scan_options,
            )

        def _orchestrate(
            *,
            build_payload_fn,
            scan_options: dict[str, object],
            strict_mode: bool,
            preflight_context: dict[str, object] | None = None,
            route_preflight_runtime=None,
            registry: object | None = None,
        ) -> dict[str, object]:
            del scan_options
            del strict_mode
            del preflight_context
            del route_preflight_runtime
            del registry
            return build_payload_fn()

        monkeypatch.setattr(
            scanner_context_module,
            "build_non_collection_run_scan_execution_request",
            _build_execution_request,
        )

        payload = api_non_collection.run_scan(
            str(role_path),
            route_scan_payload_orchestration_fn=_route,
            orchestrate_scan_payload_with_selected_plugin_fn=_orchestrate,
        )

    forwarded_ensure_fn = captured["ensure_prepared_policy_bundle_fn"]
    assert callable(forwarded_ensure_fn)
    forwarded_ensure_fn(scan_options={"role_path": str(role_path)}, di="di")
    assert canonical_calls == [({"role_path": str(role_path)}, "di")]
    assert payload["role_name"] == "tiny_role"
    assert payload["requirements"] == []


def test_fsrc_non_collection_run_scan_uses_scan_pipeline_registry_seam_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "tiny_role"
    _build_tiny_role(role_path)

    with _prefer_fsrc_prism_on_sys_path():
        api_non_collection = importlib.import_module("prism.api_layer.non_collection")
        scanner_context_module = importlib.import_module(
            "prism.scanner_core.scanner_context"
        )

        real_registry = api_non_collection.plugin_facade.get_default_plugin_registry()
        isolated_registry = _make_test_registry(
            real_registry,
            lambda name: object() if name == "default" else None,
        )
        seam_calls: list[str] = []
        captured: dict[str, object] = {}

        class _PoisonRegistry:
            def get_scan_pipeline_plugin(self, name: str):
                raise AssertionError(
                    f"non_collection.run_scan bypassed plugin_facade seam for {name}"
                )

            def __getattr__(self, name: str):
                return getattr(real_registry, name)

        def _fake_get_default_scan_pipeline_registry():
            seam_calls.append("used")
            return api_non_collection.plugin_facade.isolate_scan_pipeline_registry(
                isolated_registry
            )

        def _build_execution_request(**kwargs: object) -> SimpleNamespace:
            captured["default_plugin_registry"] = kwargs["default_plugin_registry"]
            return SimpleNamespace(
                role_path=str(role_path),
                scan_options={"role_path": str(role_path)},
                build_payload_fn=lambda: _stub_non_collection_result(),
                strict_mode=True,
                runtime_registry=None,
            )

        def _route(
            *,
            role_path: str,
            scan_options: dict[str, object],
            kernel_orchestrator_fn,
            registry: object | None = None,
        ) -> _NormalizedNonCollectionResult:
            del role_path
            del scan_options
            del kernel_orchestrator_fn
            del registry
            return _stub_non_collection_result()

        monkeypatch.setattr(
            api_non_collection.plugin_facade,
            "get_default_plugin_registry",
            lambda: _PoisonRegistry(),
        )
        monkeypatch.setattr(
            api_non_collection.plugin_facade,
            "get_default_scan_pipeline_registry",
            _fake_get_default_scan_pipeline_registry,
        )
        monkeypatch.setattr(
            scanner_context_module,
            "build_non_collection_run_scan_execution_request",
            _build_execution_request,
        )

        payload = api_non_collection.run_scan(
            str(role_path),
            route_scan_payload_orchestration_fn=_route,
            orchestrate_scan_payload_with_selected_plugin_fn=(
                lambda **kwargs: _stub_non_collection_result()
            ),
        )

    assert seam_calls == ["used"]
    assert captured["default_plugin_registry"] is not real_registry
    assert payload["role_name"] == "tiny_role"
