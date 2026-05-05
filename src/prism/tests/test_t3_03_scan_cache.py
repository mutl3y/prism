"""T3-03: Scan cache backend tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, IO, cast

import pytest

from prism.scanner_core.di import DIContainer
from prism.scanner_core.feature_detector import FeatureDetector
from prism.scanner_core.scan_cache import (
    InMemoryLRUScanCache,
    build_runtime_wiring_identity,
    compute_path_content_hash,
    compute_scan_cache_key,
)
from prism.scanner_core.variable_discovery import VariableDiscovery
from prism.scanner_data.contracts_request import ScanOptionsDict
from prism.scanner_plugins.registry import PluginRegistry


class _OpaquePolicy:
    pass


class _RuntimeRegistry:
    pass


class _MutatingFeatureDetectionPlugin:
    def __init__(self) -> None:
        self.received_options: list[dict[str, object]] = []

    def detect_features(
        self,
        role_path: str,
        options: dict[str, object],
    ) -> dict[str, object]:
        del role_path
        self.received_options.append(options)
        options.setdefault("exclude_path_patterns", [])
        exclude_paths = options["exclude_path_patterns"]
        assert isinstance(exclude_paths, list)
        exclude_paths.append("mutated-by-plugin")
        policy_context = options.get("policy_context")
        assert isinstance(policy_context, dict)
        policy_context["mutated"] = True
        return {"received": True}

    def analyze_task_catalog(
        self,
        role_path: str,
        options: dict[str, object],
    ) -> dict[str, dict[str, object]]:
        del role_path, options
        return {}


class _MutatingVariableDiscoveryPlugin:
    def __init__(self) -> None:
        self.received_options: list[dict[str, object]] = []

    def discover_static_variables(
        self,
        role_path: str,
        options: dict[str, object],
    ) -> tuple[dict[str, object], ...]:
        del role_path, options
        return ()

    def discover_referenced_variables(
        self,
        role_path: str,
        options: dict[str, object],
    ) -> frozenset[str]:
        del role_path, options
        return frozenset()

    def resolve_unresolved_variables(
        self,
        static_names: frozenset[str],
        referenced: frozenset[str],
        options: dict[str, object],
    ) -> dict[str, str]:
        del static_names, referenced
        self.received_options.append(options)
        vars_seed_paths = options.get("vars_seed_paths")
        assert isinstance(vars_seed_paths, list)
        vars_seed_paths.append("mutated-by-plugin.yml")
        policy_context = options.get("policy_context")
        assert isinstance(policy_context, dict)
        policy_context["mutated"] = True
        return {}


def _build_scan_options(**overrides: object) -> ScanOptionsDict:
    scan_options: ScanOptionsDict = {
        "role_path": "role",
        "role_name_override": None,
        "readme_config_path": None,
        "policy_config_path": None,
        "include_vars_main": True,
        "exclude_path_patterns": None,
        "detailed_catalog": False,
        "include_task_parameters": True,
        "include_task_runbooks": True,
        "inline_task_runbooks": True,
        "include_collection_checks": False,
        "keep_unknown_style_sections": True,
        "adopt_heading_mode": None,
        "vars_seed_paths": None,
        "style_readme_path": None,
        "style_source_path": None,
        "style_guide_skeleton": False,
        "compare_role_path": None,
        "fail_on_unconstrained_dynamic_includes": None,
        "fail_on_yaml_like_task_annotations": None,
        "ignore_unresolved_internal_underscore_references": None,
    }
    return cast(ScanOptionsDict, {**scan_options, **overrides})


def test_lru_cache_get_returns_none_on_miss() -> None:
    cache = InMemoryLRUScanCache()
    assert cache.get("absent") is None
    assert cache.misses == 1
    assert cache.hits == 0


def test_lru_cache_set_then_get_hits() -> None:
    cache = InMemoryLRUScanCache()
    cache.set("k", {"result": 1})
    assert cache.get("k") == {"result": 1}
    assert cache.hits == 1
    assert cache.misses == 0


def test_lru_cache_evicts_oldest_when_full() -> None:
    cache = InMemoryLRUScanCache(maxsize=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3
    assert len(cache) == 2


def test_lru_cache_get_promotes_recency() -> None:
    cache = InMemoryLRUScanCache(maxsize=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.get("a")
    cache.set("c", 3)
    assert cache.get("a") == 1
    assert cache.get("b") is None


def test_lru_cache_invalidate_and_clear() -> None:
    cache = InMemoryLRUScanCache()
    cache.set("a", 1)
    cache.invalidate("a")
    assert cache.get("a") is None
    cache.set("b", 2)
    cache.clear()
    assert len(cache) == 0
    assert cache.hits == 0
    assert cache.misses == 0


def test_lru_cache_maxsize_zero_disables() -> None:
    cache = InMemoryLRUScanCache(maxsize=0)
    cache.set("a", 1)
    assert cache.get("a") is None
    assert len(cache) == 0


def test_lru_cache_negative_maxsize_rejected() -> None:
    with pytest.raises(ValueError):
        InMemoryLRUScanCache(maxsize=-1)


def test_lru_cache_set_copies_mutable_values() -> None:
    cache = InMemoryLRUScanCache()
    payload = {"outer": [{"inner": ["original"]}]}

    cache.set("k", payload)
    payload["outer"][0]["inner"].append("caller-mutation")

    assert cache.get("k") == {"outer": [{"inner": ["original"]}]}


def test_lru_cache_get_returns_defensive_copy() -> None:
    cache = InMemoryLRUScanCache()
    cache.set("k", {"outer": [{"inner": ["original"]}]})

    cached = cache.get("k")
    assert isinstance(cached, dict)
    outer = cached["outer"]
    assert isinstance(outer, list)
    first = outer[0]
    assert isinstance(first, dict)
    inner = first["inner"]
    assert isinstance(inner, list)
    inner.append("retrieval-mutation")

    assert cache.get("k") == {"outer": [{"inner": ["original"]}]}


def test_compute_scan_cache_key_is_stable_and_options_sensitive() -> None:
    bundle1 = {"task_line": _OpaquePolicy(), "yaml": _OpaquePolicy()}
    bundle2 = {"yaml": _OpaquePolicy(), "task_line": _OpaquePolicy()}

    key1 = compute_scan_cache_key(
        role_content_hash="abc123",
        scan_options={"a": 1, "b": 2, "prepared_policy_bundle": bundle1},
    )
    key2 = compute_scan_cache_key(
        role_content_hash="abc123",
        scan_options={"b": 2, "a": 1, "prepared_policy_bundle": bundle2},
    )
    key3 = compute_scan_cache_key(
        role_content_hash="abc123",
        scan_options={"a": 1, "b": 3, "prepared_policy_bundle": bundle1},
    )
    assert key1 == key2
    assert key1 != key3


def test_compute_scan_cache_key_requires_content_hash() -> None:
    with pytest.raises(ValueError):
        compute_scan_cache_key(role_content_hash="", scan_options={})


def test_compute_scan_cache_key_distinguishes_role_content() -> None:
    k1 = compute_scan_cache_key(role_content_hash="aaa", scan_options={})
    k2 = compute_scan_cache_key(role_content_hash="bbb", scan_options={})
    assert k1 != k2


def test_build_runtime_wiring_identity_distinguishes_registry_instances() -> None:
    def _route(**kwargs: object) -> dict[str, object]:
        del kwargs
        return {}

    def _orchestrate(**kwargs: object) -> dict[str, object]:
        del kwargs
        return {}

    first = build_runtime_wiring_identity(
        route_scan_payload_orchestration_fn=_route,
        orchestrate_scan_payload_with_selected_plugin_fn=_orchestrate,
        runtime_registry=_RuntimeRegistry(),
    )
    second = build_runtime_wiring_identity(
        route_scan_payload_orchestration_fn=_route,
        orchestrate_scan_payload_with_selected_plugin_fn=_orchestrate,
        runtime_registry=_RuntimeRegistry(),
    )

    assert (
        first["route_scan_payload_orchestration_fn"]
        == second["route_scan_payload_orchestration_fn"]
    )
    assert (
        first["orchestrate_scan_payload_with_selected_plugin_fn"]
        == second["orchestrate_scan_payload_with_selected_plugin_fn"]
    )
    assert first["runtime_registry"] != second["runtime_registry"]


def test_build_runtime_wiring_identity_tracks_registry_state_revision() -> None:
    def _route(**kwargs: object) -> dict[str, object]:
        del kwargs
        return {}

    def _orchestrate(**kwargs: object) -> dict[str, object]:
        del kwargs
        return {}

    registry = PluginRegistry()
    first = build_runtime_wiring_identity(
        route_scan_payload_orchestration_fn=_route,
        orchestrate_scan_payload_with_selected_plugin_fn=_orchestrate,
        runtime_registry=registry,
    )

    registry.register_reserved_unsupported_platform("terraform")

    second = build_runtime_wiring_identity(
        route_scan_payload_orchestration_fn=_route,
        orchestrate_scan_payload_with_selected_plugin_fn=_orchestrate,
        runtime_registry=registry,
    )

    assert first["runtime_registry"] != second["runtime_registry"]
    assert isinstance(second["runtime_registry"], str)
    assert second["runtime_registry"].endswith(":r1")


def test_compute_path_content_hash_is_stable_for_readable_single_file(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "tasks.yml"
    file_path.write_text("- name: example\n", encoding="utf-8")

    assert compute_path_content_hash(str(file_path)) == compute_path_content_hash(
        str(file_path)
    )


def test_compute_path_content_hash_distinguishes_unreadable_single_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = tmp_path / "tasks-a.yml"
    second = tmp_path / "tasks-b.yml"
    first.write_text("- name: first\n", encoding="utf-8")
    second.write_text("- name: second\n", encoding="utf-8")

    original_open = open
    blocked_paths = {str(first.resolve()), str(second.resolve())}

    def raising_open(
        file: int | str | bytes | Any,
        *args: Any,
        **kwargs: Any,
    ) -> IO[Any]:
        if isinstance(file, (str, Path)):
            candidate = str(Path(file).resolve())
            if candidate in blocked_paths:
                raise OSError("permission denied")
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", raising_open)

    assert compute_path_content_hash(str(first)) != compute_path_content_hash(
        str(second)
    )


def test_di_container_exposes_scan_options_as_snapshots() -> None:
    source_options = _build_scan_options(
        exclude_path_patterns=["tasks/generated"],
        policy_context={"selection": {"plugin": "ansible"}},
    )
    container = DIContainer("role", source_options)

    exposed = container.scan_options
    exclude_path_patterns = exposed["exclude_path_patterns"]
    assert exclude_path_patterns is not None
    exclude_path_patterns.append("mutated-by-caller")
    policy_context = exposed["policy_context"]
    assert policy_context is not None
    policy_context["selection"] = {"plugin": "terraform"}

    assert source_options == _build_scan_options(
        exclude_path_patterns=["tasks/generated"],
        policy_context={"selection": {"plugin": "ansible"}},
    )
    assert container.scan_options == source_options


def test_feature_detector_passes_fresh_option_snapshots_to_plugin() -> None:
    source_options = _build_scan_options(
        exclude_path_patterns=["tasks/generated"],
        policy_context={"selection": {"plugin": "ansible"}},
    )
    container = DIContainer("role", source_options)
    plugin = _MutatingFeatureDetectionPlugin()
    container.inject_mock("feature_detection_plugin", plugin)
    detector = FeatureDetector(container, "role", source_options)

    detector.detect()
    detector.detect()

    assert source_options == _build_scan_options(
        exclude_path_patterns=["tasks/generated"],
        policy_context={"selection": {"plugin": "ansible"}},
    )
    assert plugin.received_options[0] == plugin.received_options[1]
    assert plugin.received_options[0] is not plugin.received_options[1]
    assert container.scan_options == source_options


def test_variable_discovery_passes_fresh_option_snapshots_to_plugin() -> None:
    source_options = _build_scan_options(
        vars_seed_paths=["vars/main.yml"],
        policy_context={"selection": {"plugin": "ansible"}},
    )
    container = DIContainer("role", source_options)
    plugin = _MutatingVariableDiscoveryPlugin()
    container.inject_mock("variable_discovery_plugin", plugin)
    discovery = VariableDiscovery(container, "role", source_options)

    discovery.resolve_unresolved(
        static_names=frozenset({"known"}),
        referenced=frozenset({"known", "missing"}),
    )
    discovery.resolve_unresolved(
        static_names=frozenset({"known"}),
        referenced=frozenset({"known", "missing"}),
    )

    assert source_options == _build_scan_options(
        vars_seed_paths=["vars/main.yml"],
        policy_context={"selection": {"plugin": "ansible"}},
    )
    assert plugin.received_options[0] == plugin.received_options[1]
    assert plugin.received_options[0] is not plugin.received_options[1]
    assert container.scan_options == source_options
