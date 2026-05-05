"""G-03: Integration tests for InMemoryLRUScanCache wired into the scan dispatch path."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pytest

from prism import api as public_api
from prism.api_layer import non_collection as non_collection_module
from prism.api_layer import plugin_facade
from prism.api_layer.non_collection import run_scan
from prism.scanner_data.contracts_request import ScanOptionsDict
from prism.scanner_kernel.orchestrator import RoutePreflightRuntimeCarrier
from prism.scanner_core.scan_cache import InMemoryLRUScanCache


class _KernelOrchestratorFn(Protocol):
    def __call__(
        self,
        *,
        role_path: str,
        scan_options: ScanOptionsDict,
        route_preflight_runtime: RoutePreflightRuntimeCarrier | None = None,
    ) -> dict[str, object]: ...


def _build_tiny_role(role_path: Path) -> None:
    (role_path / "defaults").mkdir(parents=True)
    (role_path / "tasks").mkdir(parents=True)
    (role_path / "defaults" / "main.yml").write_text(
        "---\ncache_test_var: hello\n", encoding="utf-8"
    )
    (role_path / "tasks" / "main.yml").write_text(
        '---\n- name: Cache test task\n  debug:\n    msg: "{{ cache_test_var }}"\n',
        encoding="utf-8",
    )
    (role_path / "README.md").write_text(
        "Role for scan cache integration tests.\n",
        encoding="utf-8",
    )


def _cache_test_route(
    *,
    role_path: str,
    scan_options: ScanOptionsDict,
    kernel_orchestrator_fn: _KernelOrchestratorFn,
    registry: object | None = None,
) -> dict[str, object]:
    del kernel_orchestrator_fn, registry
    return {
        "role_name": Path(role_path).name,
        "description": "cache integration payload",
        "metadata": {},
        "scan_options": {
            "include_vars_main": scan_options.get("include_vars_main"),
        },
    }


def test_cache_hit_on_second_identical_scan(tmp_path: Path) -> None:
    """Two consecutive scans of the same role with the cache enabled: second is a hit."""
    role_path = tmp_path / "cache_role"
    _build_tiny_role(role_path)

    backend = InMemoryLRUScanCache()

    result1 = run_scan(
        str(role_path),
        include_vars_main=True,
        cache_backend=backend,
        route_scan_payload_orchestration_fn=_cache_test_route,
    )
    assert backend.hits == 0
    assert backend.misses == 1

    result2 = run_scan(
        str(role_path),
        include_vars_main=True,
        cache_backend=backend,
        route_scan_payload_orchestration_fn=_cache_test_route,
    )
    assert backend.hits == 1
    assert backend.misses == 1

    assert result1 == result2


def test_cache_miss_on_content_change(tmp_path: Path) -> None:
    """Two scans with different role content produce two misses (zero hits)."""
    role_path_a = tmp_path / "role_a"
    _build_tiny_role(role_path_a)

    role_path_b = tmp_path / "role_b"
    _build_tiny_role(role_path_b)
    (role_path_b / "defaults" / "main.yml").write_text(
        "---\ncache_test_var: different_content\n", encoding="utf-8"
    )

    backend = InMemoryLRUScanCache()

    run_scan(
        str(role_path_a),
        include_vars_main=True,
        cache_backend=backend,
        route_scan_payload_orchestration_fn=_cache_test_route,
    )
    run_scan(
        str(role_path_b),
        include_vars_main=True,
        cache_backend=backend,
        route_scan_payload_orchestration_fn=_cache_test_route,
    )

    assert backend.hits == 0
    assert backend.misses == 2


def test_cache_miss_on_same_path_style_guide_content_change(tmp_path: Path) -> None:
    """Changing an external style guide at the same path must invalidate cache."""
    role_path = tmp_path / "cache_role"
    _build_tiny_role(role_path)
    style_readme_path = tmp_path / "style-guide.md"
    style_readme_path.write_text(
        "# Style Guide\n\n## Variables\n\n- first version\n",
        encoding="utf-8",
    )

    backend = InMemoryLRUScanCache()

    run_scan(
        str(role_path),
        include_vars_main=True,
        style_readme_path=str(style_readme_path),
        cache_backend=backend,
        route_scan_payload_orchestration_fn=_cache_test_route,
    )

    style_readme_path.write_text(
        "# Style Guide\n\n## Variables\n\n- second version\n",
        encoding="utf-8",
    )

    run_scan(
        str(role_path),
        include_vars_main=True,
        style_readme_path=str(style_readme_path),
        cache_backend=backend,
        route_scan_payload_orchestration_fn=_cache_test_route,
    )

    assert backend.hits == 0
    assert backend.misses == 2


def test_cache_hits_return_isolated_result_payloads(tmp_path: Path) -> None:
    role_path = tmp_path / "cache_role"
    _build_tiny_role(role_path)

    backend = InMemoryLRUScanCache()

    result1 = run_scan(
        str(role_path),
        include_vars_main=True,
        cache_backend=backend,
        route_scan_payload_orchestration_fn=_cache_test_route,
    )
    original_role_name = result1["role_name"]
    result1["role_name"] = "mutated-after-store"

    result2 = run_scan(
        str(role_path),
        include_vars_main=True,
        cache_backend=backend,
        route_scan_payload_orchestration_fn=_cache_test_route,
    )
    assert backend.hits == 1
    assert backend.misses == 1
    assert result2["role_name"] == original_role_name

    result2["role_name"] = "mutated-after-get"
    result3 = run_scan(
        str(role_path),
        include_vars_main=True,
        cache_backend=backend,
        route_scan_payload_orchestration_fn=_cache_test_route,
    )

    assert backend.hits == 2
    assert backend.misses == 1
    assert result3["role_name"] == original_role_name


def test_cache_backend_none_is_zero_overhead(tmp_path: Path) -> None:
    """cache_backend=None (default) path has no overhead — no cache_backend attribute checked."""
    role_path = tmp_path / "nocache_role"
    _build_tiny_role(role_path)

    result = run_scan(
        str(role_path),
        include_vars_main=True,
        route_scan_payload_orchestration_fn=_cache_test_route,
    )
    assert isinstance(result, dict)
    assert result["role_name"] == "nocache_role"


def test_cache_miss_when_route_wiring_changes(tmp_path: Path) -> None:
    role_path = tmp_path / "cache_role"
    _build_tiny_role(role_path)

    backend = InMemoryLRUScanCache()

    def _route_a(
        *,
        role_path: str,
        scan_options: ScanOptionsDict,
        kernel_orchestrator_fn: _KernelOrchestratorFn,
        registry: object | None = None,
    ) -> dict[str, object]:
        del role_path, scan_options, kernel_orchestrator_fn, registry
        return {
            "role_name": "route-a",
            "description": "payload from route a",
            "metadata": {},
            "display_variables": {},
            "requirements_display": [],
            "undocumented_default_filters": [],
        }

    def _route_b(
        *,
        role_path: str,
        scan_options: ScanOptionsDict,
        kernel_orchestrator_fn: _KernelOrchestratorFn,
        registry: object | None = None,
    ) -> dict[str, object]:
        del role_path, scan_options, kernel_orchestrator_fn, registry
        return {
            "role_name": "route-b",
            "description": "payload from route b",
            "metadata": {},
            "display_variables": {},
            "requirements_display": [],
            "undocumented_default_filters": [],
        }

    result_a = run_scan(
        str(role_path),
        include_vars_main=True,
        cache_backend=backend,
        route_scan_payload_orchestration_fn=_route_a,
    )
    result_b = run_scan(
        str(role_path),
        include_vars_main=True,
        cache_backend=backend,
        route_scan_payload_orchestration_fn=_route_b,
    )

    assert backend.hits == 0
    assert backend.misses == 2
    assert result_a["role_name"] == "route-a"
    assert result_b["role_name"] == "route-b"


def test_public_run_scan_reuses_cache_with_stable_default_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    role_path = tmp_path / "cache_role"
    _build_tiny_role(role_path)

    backend = InMemoryLRUScanCache()
    default_registry = plugin_facade.get_default_plugin_registry()
    route_calls = 0

    def _public_route(
        *,
        role_path: str,
        scan_options: ScanOptionsDict,
        kernel_orchestrator_fn: _KernelOrchestratorFn,
        registry: object | None = None,
    ) -> dict[str, object]:
        nonlocal route_calls
        del role_path, scan_options, kernel_orchestrator_fn
        route_calls += 1
        assert registry is not None
        return {
            "role_name": "public-cache-role",
            "description": "payload from public api route",
            "metadata": {},
            "display_variables": {},
            "requirements_display": [],
            "undocumented_default_filters": [],
        }

    monkeypatch.setattr(
        plugin_facade,
        "get_default_plugin_registry",
        lambda: default_registry,
    )
    monkeypatch.setattr(
        non_collection_module,
        "route_scan_payload_orchestration",
        _public_route,
    )

    result1 = public_api.run_scan(
        str(role_path),
        include_vars_main=True,
        cache_backend=backend,
    )
    result2 = public_api.run_scan(
        str(role_path),
        include_vars_main=True,
        cache_backend=backend,
    )

    assert backend.hits == 1
    assert backend.misses == 1
    assert route_calls == 1
    assert result1 == result2
