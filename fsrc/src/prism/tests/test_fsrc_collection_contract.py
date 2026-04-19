"""Focused fsrc collection contract and CLI behavior tests."""

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


def _build_collection_root(collection_root: Path) -> None:
    (collection_root / "roles" / "role_a").mkdir(parents=True)
    (collection_root / "roles" / "role_b").mkdir(parents=True)
    (collection_root / "galaxy.yml").write_text(
        "---\nnamespace: demo\nname: toolkit\nversion: 1.2.3\n",
        encoding="utf-8",
    )


def _write_collection_dependency_fixtures(collection_root: Path) -> None:
    (collection_root / "collections").mkdir(parents=True, exist_ok=True)
    (collection_root / "roles" / "requirements.yml").write_text(
        "---\nroles:\n  - name: geerlingguy.mysql\n    version: 3.3.0\n",
        encoding="utf-8",
    )
    (collection_root / "collections" / "requirements.yml").write_text(
        "---\ncollections:\n  - name: community.general\n    version: 8.0.0\n",
        encoding="utf-8",
    )


def _write_collection_plugin_fixtures(collection_root: Path) -> None:
    (collection_root / "plugins" / "filter").mkdir(parents=True, exist_ok=True)
    (collection_root / "plugins" / "lookup").mkdir(parents=True, exist_ok=True)
    (collection_root / "plugins" / "filter" / "network.py").write_text(
        '"""Network filter helpers."""\n\n'
        "class FilterModule:\n"
        "    def filters(self):\n"
        "        return {\n"
        '            "cidr_contains": cidr_contains,\n'
        '            "ip_version": ip_version,\n'
        "        }\n",
        encoding="utf-8",
    )
    (collection_root / "plugins" / "lookup" / "service.py").write_text(
        "class LookupModule:\n"
        "    def run(self, terms, variables=None, **kwargs):\n"
        "        return terms\n\n"
        "    def helper(self):\n"
        "        return []\n",
        encoding="utf-8",
    )


def test_fsrc_api_scan_collection_returns_canonical_collection_envelope(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_root = tmp_path / "demo_collection"
    _build_collection_root(collection_root)
    _write_collection_dependency_fixtures(collection_root)
    _write_collection_plugin_fixtures(collection_root)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        captured_kwargs: list[dict[str, object]] = []

        def _fake_scan_role(role_path: str, **kwargs: object) -> dict[str, object]:
            captured_kwargs.append(dict(kwargs))
            role_name = Path(role_path).name
            if role_name == "role_b":
                raise ValueError("invalid role content")
            return {
                "role_name": role_name,
                "metadata": {"scanner_counters": {"task_files": 1, "templates": 0}},
            }

        monkeypatch.setattr(api_module, "scan_role", _fake_scan_role)
        payload = api_module.scan_collection(str(collection_root))

    assert payload["collection"] == {
        "path": str(collection_root.resolve()),
        "metadata": {
            "namespace": "demo",
            "name": "toolkit",
            "version": "1.2.3",
        },
    }
    assert payload["summary"] == {
        "total_roles": 2,
        "scanned_roles": 1,
        "failed_roles": 1,
    }
    assert captured_kwargs == [
        {
            "compare_role_path": None,
            "style_readme_path": None,
            "role_name_override": "role_a",
            "vars_seed_paths": None,
            "concise_readme": False,
            "scanner_report_output": None,
            "include_vars_main": True,
            "include_scanner_report_link": True,
            "readme_config_path": None,
            "adopt_heading_mode": None,
            "style_guide_skeleton": False,
            "keep_unknown_style_sections": True,
            "exclude_path_patterns": None,
            "style_source_path": None,
            "policy_config_path": None,
            "fail_on_unconstrained_dynamic_includes": None,
            "fail_on_yaml_like_task_annotations": None,
            "ignore_unresolved_internal_underscore_references": None,
            "detailed_catalog": False,
            "include_collection_checks": False,
            "include_task_parameters": True,
            "include_task_runbooks": True,
            "inline_task_runbooks": True,
        },
        {
            "compare_role_path": None,
            "style_readme_path": None,
            "role_name_override": "role_b",
            "vars_seed_paths": None,
            "concise_readme": False,
            "scanner_report_output": None,
            "include_vars_main": True,
            "include_scanner_report_link": True,
            "readme_config_path": None,
            "adopt_heading_mode": None,
            "style_guide_skeleton": False,
            "keep_unknown_style_sections": True,
            "exclude_path_patterns": None,
            "style_source_path": None,
            "policy_config_path": None,
            "fail_on_unconstrained_dynamic_includes": None,
            "fail_on_yaml_like_task_annotations": None,
            "ignore_unresolved_internal_underscore_references": None,
            "detailed_catalog": False,
            "include_collection_checks": False,
            "include_task_parameters": True,
            "include_task_runbooks": True,
            "inline_task_runbooks": True,
        },
    ]
    assert payload["roles"] == [
        {
            "role": "role_a",
            "path": str((collection_root / "roles" / "role_a").resolve()),
            "payload": {
                "role_name": "role_a",
                "metadata": {"scanner_counters": {"task_files": 1, "templates": 0}},
            },
            "rendered_readme": None,
        }
    ]
    assert payload["failures"] == [
        {
            "role": "role_b",
            "path": str((collection_root / "roles" / "role_b").resolve()),
            "error_code": "role_content_invalid",
            "error_category": "validation",
            "error_type": "ValueError",
            "error": "invalid role content",
        }
    ]
    assert payload["dependencies"] == {
        "collections": [
            {
                "key": "community.general",
                "type": "collection",
                "name": "community.general",
                "src": None,
                "version": "8.0.0",
                "versions": ["8.0.0"],
                "sources": ["collections/requirements.yml"],
            }
        ],
        "roles": [
            {
                "key": "geerlingguy.mysql",
                "type": "role",
                "name": "geerlingguy.mysql",
                "src": None,
                "version": "3.3.0",
                "versions": ["3.3.0"],
                "sources": ["roles/requirements.yml"],
            }
        ],
        "conflicts": [],
    }
    assert payload["plugin_catalog"]["schema_version"] == 1
    assert payload["plugin_catalog"]["summary"] == {
        "total_plugins": 2,
        "types_present": ["filter", "lookup"],
        "files_scanned": 2,
        "files_failed": 0,
    }
    assert payload["plugin_catalog"]["failures"] == []
    assert payload["plugin_catalog"]["by_type"]["filter"] == [
        {
            "type": "filter",
            "name": "network",
            "relative_path": "plugins/filter/network.py",
            "language": "python",
            "symbols": ["cidr_contains", "ip_version"],
            "summary": "Network filter helpers.",
            "doc_source": "module_docstring",
            "confidence": "high",
            "confidence_score": 0.95,
            "extraction": {
                "method": "ast",
                "ast_version": "py3",
                "fallback_used": False,
            },
            "capability_hints": ["cidr_contains", "ip_version"],
        }
    ]
    assert payload["plugin_catalog"]["by_type"]["lookup"] == [
        {
            "type": "lookup",
            "name": "service",
            "relative_path": "plugins/lookup/service.py",
            "language": "python",
            "symbols": ["LookupModule", "helper", "run"],
            "summary": "Capability hints: LookupModule.helper, LookupModule.run.",
            "doc_source": "class_method_hints",
            "confidence": "medium",
            "confidence_score": 0.65,
            "extraction": {
                "method": "ast",
                "ast_version": "py3",
                "fallback_used": False,
            },
            "capability_hints": ["LookupModule.helper", "LookupModule.run"],
        }
    ]
    assert sorted(payload["plugin_catalog"]["by_type"].keys()) == [
        "callback",
        "connection",
        "doc_fragments",
        "filter",
        "inventory",
        "lookup",
        "module_utils",
        "modules",
        "strategy",
        "test",
    ]


def test_fsrc_api_scan_collection_reraises_collection_dependency_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_root = tmp_path / "demo_collection"
    _build_collection_root(collection_root)
    (collection_root / "collections").mkdir(parents=True, exist_ok=True)
    (collection_root / "collections" / "requirements.yml").write_text(
        "collections: [unterminated\n",
        encoding="utf-8",
    )

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        errors_module = importlib.import_module("prism.errors")

        scan_calls = {"count": 0}

        def _fake_scan_role(role_path: str, **kwargs: object) -> dict[str, object]:
            del role_path
            del kwargs
            scan_calls["count"] += 1
            return {"role_name": "role_a", "metadata": {}}

        monkeypatch.setattr(api_module, "scan_role", _fake_scan_role)

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            api_module.scan_collection(str(collection_root))

    assert scan_calls["count"] == 2
    assert exc_info.value.code == "role_content_yaml_invalid"
    assert exc_info.value.category == "parser"


def test_fsrc_api_scan_collection_demotes_recoverable_role_content_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_root = tmp_path / "demo_collection"
    _build_collection_root(collection_root)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        def _fake_scan_role(role_path: str, **kwargs: object) -> dict[str, object]:
            del kwargs
            role_name = Path(role_path).name
            if role_name == "role_b":
                raise ValueError("invalid role content")
            return {"role_name": role_name, "metadata": {}}

        monkeypatch.setattr(api_module, "scan_role", _fake_scan_role)

        payload = api_module.scan_collection(str(collection_root))

    assert [entry["role"] for entry in payload["roles"]] == ["role_a"]
    assert payload["summary"] == {
        "total_roles": 2,
        "scanned_roles": 1,
        "failed_roles": 1,
    }
    assert payload["failures"] == [
        {
            "role": "role_b",
            "path": str((collection_root / "roles" / "role_b").resolve()),
            "error_code": "role_content_invalid",
            "error_category": "validation",
            "error_type": "ValueError",
            "error": "invalid role content",
        }
    ]


def test_fsrc_api_scan_collection_reraises_nonrecoverable_role_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_root = tmp_path / "demo_collection"
    _build_collection_root(collection_root)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        def _fake_scan_role(role_path: str, **kwargs: object) -> dict[str, object]:
            del role_path
            del kwargs
            raise KeyError("unexpected failure")

        monkeypatch.setattr(api_module, "scan_role", _fake_scan_role)

        with pytest.raises(KeyError, match="unexpected failure"):
            api_module.scan_collection(str(collection_root))


def test_fsrc_api_scan_collection_demotes_role_scan_runtime_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_root = tmp_path / "demo_collection"
    _build_collection_root(collection_root)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        def _fake_scan_role(role_path: str, **kwargs: object) -> dict[str, object]:
            del kwargs
            role_name = Path(role_path).name
            if role_name == "role_b":
                raise RuntimeError("scan boom")
            return {"role_name": role_name, "metadata": {}}

        monkeypatch.setattr(api_module, "scan_role", _fake_scan_role)

        payload = api_module.scan_collection(str(collection_root))

    assert [entry["role"] for entry in payload["roles"]] == ["role_a"]
    assert payload["summary"] == {
        "total_roles": 2,
        "scanned_roles": 1,
        "failed_roles": 1,
    }
    assert payload["failures"] == [
        {
            "role": "role_b",
            "path": str((collection_root / "roles" / "role_b").resolve()),
            "error_code": "role_scan_runtime_error",
            "error_category": "runtime",
            "error_type": "RuntimeError",
            "error": "scan boom",
        }
    ]


def test_fsrc_api_scan_collection_rejects_root_without_galaxy_metadata(
    tmp_path: Path,
) -> None:
    collection_root = tmp_path / "demo_collection"
    (collection_root / "roles" / "role_a").mkdir(parents=True)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        with pytest.raises(FileNotFoundError, match="collection root must include"):
            api_module.scan_collection(str(collection_root))


def test_fsrc_api_scan_collection_rejects_missing_root_like_src(
    tmp_path: Path,
) -> None:
    missing_root = tmp_path / "missing_collection"

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        with pytest.raises(FileNotFoundError, match="collection path not found"):
            api_module.scan_collection(str(missing_root))


def test_fsrc_api_scan_collection_rejects_invalid_galaxy_metadata(
    tmp_path: Path,
) -> None:
    collection_root = tmp_path / "demo_collection"
    (collection_root / "roles" / "role_a").mkdir(parents=True)
    (collection_root / "galaxy.yml").write_text(
        "namespace: demo\nname: [unterminated\n",
        encoding="utf-8",
    )

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        errors_module = importlib.import_module("prism.errors")

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            api_module.scan_collection(str(collection_root))

    assert exc_info.value.code == "collection_galaxy_metadata_yaml_invalid"
    assert exc_info.value.category == "parser"


def test_fsrc_api_scan_collection_rejects_unreadable_galaxy_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_root = tmp_path / "demo_collection"
    _build_collection_root(collection_root)
    galaxy_path = collection_root / "galaxy.yml"
    original_read_text = Path.read_text

    def _fake_read_text(self: Path, *args: object, **kwargs: object) -> str:
        if self == galaxy_path:
            raise UnicodeDecodeError("utf-8", b"\x80", 0, 1, "invalid start byte")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _fake_read_text)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        errors_module = importlib.import_module("prism.errors")

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            api_module.scan_collection(str(collection_root))

    assert exc_info.value.code == "collection_galaxy_metadata_io_error"
    assert exc_info.value.category == "io"


@pytest.mark.parametrize(
    ("galaxy_contents", "read_failure", "expected_code"),
    [
        (
            "namespace: demo\nname: [unterminated\n",
            None,
            "collection_galaxy_metadata_yaml_invalid",
        ),
        (
            None,
            UnicodeDecodeError("utf-8", b"\x80", 0, 1, "invalid start byte"),
            "collection_galaxy_metadata_io_error",
        ),
    ],
)
def test_fsrc_api_scan_collection_fails_before_role_scans_or_artifact_writes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    galaxy_contents: str | None,
    read_failure: Exception | None,
    expected_code: str,
) -> None:
    collection_root = tmp_path / "demo_collection"
    _build_collection_root(collection_root)
    galaxy_path = collection_root / "galaxy.yml"
    runbook_dir = tmp_path / "runbooks"
    runbook_csv_dir = tmp_path / "runbooks_csv"

    if galaxy_contents is not None:
        galaxy_path.write_text(galaxy_contents, encoding="utf-8")

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")
        errors_module = importlib.import_module("prism.errors")

        scan_role_calls: list[str] = []
        artifact_calls: list[str] = []

        def _fake_scan_role(role_path: str, **kwargs: object) -> dict[str, object]:
            del kwargs
            scan_role_calls.append(role_path)
            return {"role_name": Path(role_path).name, "metadata": {}}

        def _fake_write_collection_runbook_artifacts(**kwargs: object) -> None:
            artifact_calls.append(str(kwargs.get("role_name") or "<unknown>"))

        monkeypatch.setattr(api_module, "scan_role", _fake_scan_role)
        monkeypatch.setattr(
            api_module,
            "write_collection_runbook_artifacts",
            _fake_write_collection_runbook_artifacts,
        )

        if read_failure is not None:
            original_read_text = Path.read_text

            def _fake_read_text(self: Path, *args: object, **kwargs: object) -> str:
                if self == galaxy_path:
                    raise read_failure
                return original_read_text(self, *args, **kwargs)

            monkeypatch.setattr(Path, "read_text", _fake_read_text)

        with pytest.raises(errors_module.PrismRuntimeError) as exc_info:
            api_module.scan_collection(
                str(collection_root),
                runbook_output_dir=str(runbook_dir),
                runbook_csv_output_dir=str(runbook_csv_dir),
            )

    assert exc_info.value.code == expected_code
    assert scan_role_calls == []
    assert artifact_calls == []
    assert not runbook_dir.exists()
    assert not runbook_csv_dir.exists()


def test_fsrc_api_scan_collection_renders_collection_readme_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_root = tmp_path / "demo_collection"
    _build_collection_root(collection_root)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        monkeypatch.setattr(
            api_module,
            "scan_role",
            lambda role_path, **kwargs: {
                "role_name": Path(role_path).name,
                "description": "Role description",
                "variables": {},
                "requirements": [],
                "default_filters": [],
                "metadata": {},
            },
        )

        render_calls: list[str] = []

        def _fake_render_readme(
            output: str,
            role_name: str,
            description: str,
            variables: dict[str, object],
            requirements: list[object],
            default_filters: list[object],
            template: str | None = None,
            metadata: dict[str, object] | None = None,
            write: bool = True,
        ) -> str:
            del variables, requirements, default_filters, template, metadata
            render_calls.append(role_name)
            assert output == "README.md"
            assert description == "Role description"
            assert write is False
            return f"# {role_name}\n"

        monkeypatch.setattr(api_module, "render_readme", _fake_render_readme)

        payload = api_module.scan_collection(
            str(collection_root),
            include_rendered_readme=True,
        )

    assert render_calls == ["role_a", "role_b"]
    assert payload["roles"] == [
        {
            "role": "role_a",
            "path": str((collection_root / "roles" / "role_a").resolve()),
            "payload": {
                "role_name": "role_a",
                "description": "Role description",
                "variables": {},
                "requirements": [],
                "default_filters": [],
                "metadata": {},
            },
            "rendered_readme": "# role_a\n",
        },
        {
            "role": "role_b",
            "path": str((collection_root / "roles" / "role_b").resolve()),
            "payload": {
                "role_name": "role_b",
                "description": "Role description",
                "variables": {},
                "requirements": [],
                "default_filters": [],
                "metadata": {},
            },
            "rendered_readme": "# role_b\n",
        },
    ]


def test_fsrc_api_scan_collection_writes_runbook_outputs_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_root = tmp_path / "demo_collection"
    _build_collection_root(collection_root)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        monkeypatch.setattr(
            api_module,
            "scan_role",
            lambda role_path, **kwargs: {
                "role_name": Path(role_path).name,
                "metadata": {"task_catalog": [{"name": "task"}]},
            },
        )
        monkeypatch.setattr(
            api_module,
            "render_runbook",
            lambda role_name, metadata: f"# {role_name} runbook\n",
        )
        monkeypatch.setattr(
            api_module,
            "render_runbook_csv",
            lambda metadata: "file,task_name,step\n",
        )

        runbook_dir = tmp_path / "runbooks"
        runbook_csv_dir = tmp_path / "runbooks_csv"
        payload = api_module.scan_collection(
            str(collection_root),
            runbook_output_dir=str(runbook_dir),
            runbook_csv_output_dir=str(runbook_csv_dir),
        )

    assert payload["summary"] == {
        "total_roles": 2,
        "scanned_roles": 2,
        "failed_roles": 0,
    }
    assert (runbook_dir / "role_a.runbook.md").read_text(encoding="utf-8") == (
        "# role_a runbook\n"
    )
    assert (runbook_dir / "role_b.runbook.md").read_text(encoding="utf-8") == (
        "# role_b runbook\n"
    )
    assert (runbook_csv_dir / "role_a.runbook.csv").read_text(encoding="utf-8") == (
        "file,task_name,step\n"
    )
    assert (runbook_csv_dir / "role_b.runbook.csv").read_text(encoding="utf-8") == (
        "file,task_name,step\n"
    )


def test_fsrc_api_scan_collection_demotes_rendered_readme_runtime_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_root = tmp_path / "demo_collection"
    _build_collection_root(collection_root)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        monkeypatch.setattr(
            api_module,
            "scan_role",
            lambda role_path, **kwargs: {
                "role_name": Path(role_path).name,
                "description": "Role description",
                "variables": {},
                "requirements": [],
                "default_filters": [],
                "metadata": {},
            },
        )

        def _fake_render_readme(**kwargs: object) -> str:
            role_name = str(kwargs.get("role_name") or "")
            if role_name == "role_b":
                raise OSError("render boom")
            return f"# {role_name}\n"

        monkeypatch.setattr(api_module, "render_readme", _fake_render_readme)

        payload = api_module.scan_collection(
            str(collection_root),
            include_rendered_readme=True,
        )

    assert payload["summary"] == {
        "total_roles": 2,
        "scanned_roles": 1,
        "failed_roles": 1,
    }
    assert payload["roles"] == [
        {
            "role": "role_a",
            "path": str((collection_root / "roles" / "role_a").resolve()),
            "payload": {
                "role_name": "role_a",
                "description": "Role description",
                "variables": {},
                "requirements": [],
                "default_filters": [],
                "metadata": {},
            },
            "rendered_readme": "# role_a\n",
        }
    ]
    assert payload["failures"] == [
        {
            "role": "role_b",
            "path": str((collection_root / "roles" / "role_b").resolve()),
            "error_code": "role_content_io_error",
            "error_category": "io",
            "error_type": "OSError",
            "error": "render boom",
        }
    ]


def test_fsrc_api_scan_collection_demotes_runbook_runtime_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_root = tmp_path / "demo_collection"
    _build_collection_root(collection_root)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        monkeypatch.setattr(
            api_module,
            "scan_role",
            lambda role_path, **kwargs: {
                "role_name": Path(role_path).name,
                "metadata": {},
            },
        )

        def _fake_render_runbook(role_name: str, metadata: dict[str, object]) -> str:
            del metadata
            if role_name == "role_b":
                raise OSError("runbook boom")
            return f"# {role_name} runbook\n"

        monkeypatch.setattr(api_module, "render_runbook", _fake_render_runbook)

        payload = api_module.scan_collection(
            str(collection_root),
            runbook_output_dir=str(tmp_path / "runbooks"),
        )

    assert payload["summary"] == {
        "total_roles": 2,
        "scanned_roles": 1,
        "failed_roles": 1,
    }
    assert payload["roles"] == [
        {
            "role": "role_a",
            "path": str((collection_root / "roles" / "role_a").resolve()),
            "payload": {
                "role_name": "role_a",
                "metadata": {},
            },
            "rendered_readme": None,
        }
    ]
    assert payload["failures"] == [
        {
            "role": "role_b",
            "path": str((collection_root / "roles" / "role_b").resolve()),
            "error_code": "role_content_io_error",
            "error_category": "io",
            "error_type": "OSError",
            "error": "runbook boom",
        }
    ]


def test_fsrc_api_scan_collection_forwards_policy_config_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_root = tmp_path / "demo_collection"
    _build_collection_root(collection_root)
    policy_config_path = tmp_path / "policy.yml"
    policy_config_path.write_text("rules: []\n", encoding="utf-8")

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        captured_policy_paths: list[str | None] = []

        def _fake_scan_role(role_path: str, **kwargs: object) -> dict[str, object]:
            del role_path
            captured_policy_paths.append(kwargs.get("policy_config_path"))
            return {"role_name": "ok", "metadata": {}}

        monkeypatch.setattr(api_module, "scan_role", _fake_scan_role)

        payload = api_module.scan_collection(
            str(collection_root),
            policy_config_path=str(policy_config_path),
        )

    assert payload["summary"] == {
        "total_roles": 2,
        "scanned_roles": 2,
        "failed_roles": 0,
    }
    assert captured_policy_paths == [str(policy_config_path), str(policy_config_path)]


def test_fsrc_api_scan_collection_forwards_collection_role_options(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_root = tmp_path / "demo_collection"
    _build_collection_root(collection_root)

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        captured_kwargs: list[dict[str, object]] = []

        def _fake_scan_role(role_path: str, **kwargs: object) -> dict[str, object]:
            del role_path
            captured_kwargs.append(dict(kwargs))
            return {"role_name": "ok", "metadata": {}}

        monkeypatch.setattr(api_module, "scan_role", _fake_scan_role)

        payload = api_module.scan_collection(
            str(collection_root),
            concise_readme=True,
            scanner_report_output="reports/scanner.json",
            include_scanner_report_link=False,
        )

    assert payload["summary"] == {
        "total_roles": 2,
        "scanned_roles": 2,
        "failed_roles": 0,
    }
    assert captured_kwargs == [
        {
            "compare_role_path": None,
            "style_readme_path": None,
            "role_name_override": "role_a",
            "vars_seed_paths": None,
            "concise_readme": True,
            "scanner_report_output": "reports/scanner.json",
            "include_vars_main": True,
            "include_scanner_report_link": False,
            "readme_config_path": None,
            "adopt_heading_mode": None,
            "style_guide_skeleton": False,
            "keep_unknown_style_sections": True,
            "exclude_path_patterns": None,
            "style_source_path": None,
            "policy_config_path": None,
            "fail_on_unconstrained_dynamic_includes": None,
            "fail_on_yaml_like_task_annotations": None,
            "ignore_unresolved_internal_underscore_references": None,
            "detailed_catalog": False,
            "include_collection_checks": False,
            "include_task_parameters": True,
            "include_task_runbooks": True,
            "inline_task_runbooks": True,
        },
        {
            "compare_role_path": None,
            "style_readme_path": None,
            "role_name_override": "role_b",
            "vars_seed_paths": None,
            "concise_readme": True,
            "scanner_report_output": "reports/scanner.json",
            "include_vars_main": True,
            "include_scanner_report_link": False,
            "readme_config_path": None,
            "adopt_heading_mode": None,
            "style_guide_skeleton": False,
            "keep_unknown_style_sections": True,
            "exclude_path_patterns": None,
            "style_source_path": None,
            "policy_config_path": None,
            "fail_on_unconstrained_dynamic_includes": None,
            "fail_on_yaml_like_task_annotations": None,
            "ignore_unresolved_internal_underscore_references": None,
            "detailed_catalog": False,
            "include_collection_checks": False,
            "include_task_parameters": True,
            "include_task_runbooks": True,
            "inline_task_runbooks": True,
        },
    ]


def test_fsrc_api_scan_role_forwards_policy_config_path_to_run_scan(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    role_path = tmp_path / "role"
    role_path.mkdir()
    policy_config_path = tmp_path / "policy.yml"
    policy_config_path.write_text("rules: []\n", encoding="utf-8")

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        captured: dict[str, object] = {}

        def _fake_run_scan(role_path_arg: str, **kwargs: object) -> dict[str, object]:
            captured["role_path"] = role_path_arg
            captured.update(kwargs)
            return {"role_name": "demo", "metadata": {}}

        monkeypatch.setattr(api_module, "run_scan", _fake_run_scan)

        payload = api_module.scan_role(
            str(role_path),
            policy_config_path=str(policy_config_path),
        )

    assert payload == {"role_name": "demo", "metadata": {}}
    assert captured["role_path"] == str(role_path)
    assert captured["policy_config_path"] == str(policy_config_path)


def test_fsrc_api_scan_collection_ignores_plugin_support_and_debris_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    collection_root = tmp_path / "demo_collection"
    _build_collection_root(collection_root)
    lookup_dir = collection_root / "plugins" / "lookup"
    lookup_dir.mkdir(parents=True, exist_ok=True)
    (lookup_dir / "service.py").write_text(
        "class LookupModule:\n"
        "    def run(self, terms, variables=None, **kwargs):\n"
        "        return terms\n",
        encoding="utf-8",
    )
    (lookup_dir / "README.md").write_text("lookup notes\n", encoding="utf-8")
    (lookup_dir / "helpers").mkdir()
    (lookup_dir / "helpers" / "shared.py").write_text(
        "def helper():\n" "    return []\n",
        encoding="utf-8",
    )

    with _prefer_fsrc_prism_on_sys_path():
        api_module = importlib.import_module("prism.api")

        monkeypatch.setattr(
            api_module,
            "scan_role",
            lambda role_path, **kwargs: {
                "role_name": Path(role_path).name,
                "metadata": {},
            },
        )

        payload = api_module.scan_collection(str(collection_root))

    assert payload["plugin_catalog"]["summary"] == {
        "total_plugins": 1,
        "types_present": ["lookup"],
        "files_scanned": 1,
        "files_failed": 0,
    }
    assert payload["plugin_catalog"]["by_type"]["lookup"] == [
        {
            "type": "lookup",
            "name": "service",
            "relative_path": "plugins/lookup/service.py",
            "language": "python",
            "symbols": ["LookupModule", "run"],
            "summary": "Capability hints: LookupModule.run.",
            "doc_source": "class_method_hints",
            "confidence": "medium",
            "confidence_score": 0.65,
            "extraction": {
                "method": "ast",
                "ast_version": "py3",
                "fallback_used": False,
            },
            "capability_hints": ["LookupModule.run"],
        }
    ]


def test_fsrc_cli_collection_text_output_uses_normalized_collection_envelope(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")

        def _fake_scan_collection(
            collection_path: str,
            **kwargs: object,
        ) -> dict[str, object]:
            del collection_path
            del kwargs
            return {
                "collection": {
                    "path": "/tmp/demo-collection",
                    "metadata": {"namespace": "demo", "name": "toolkit"},
                },
                "summary": {
                    "total_roles": 3,
                    "scanned_roles": 2,
                    "failed_roles": 1,
                },
                "roles": [],
                "failures": [],
                "dependencies": {
                    "collections": [],
                    "roles": [],
                    "conflicts": [],
                },
                "plugin_catalog": {
                    "summary": {
                        "total_plugins": 0,
                        "types_present": [],
                        "files_scanned": 0,
                        "files_failed": 0,
                    },
                    "by_type": {
                        "filter": [],
                        "modules": [],
                        "lookup": [],
                        "inventory": [],
                        "callback": [],
                        "connection": [],
                        "strategy": [],
                        "test": [],
                        "doc_fragments": [],
                        "module_utils": [],
                    },
                    "failures": [],
                },
            }

        monkeypatch.setattr(cli_module.api, "scan_collection", _fake_scan_collection)
        rc = cli_module.main(["collection", "/tmp/demo-collection"])

    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.splitlines() == [
        "Collection: demo.toolkit",
        "Roles scanned: 2",
        "Roles failed: 1",
    ]


def test_fsrc_cli_collection_text_output_falls_back_to_windows_safe_basename(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")

        def _fake_scan_collection(
            collection_path: str,
            **kwargs: object,
        ) -> dict[str, object]:
            del collection_path
            del kwargs
            return {
                "collection": {
                    "path": r"C:\\work\\demo_collection",
                    "metadata": {},
                },
                "summary": {
                    "total_roles": 1,
                    "scanned_roles": 1,
                    "failed_roles": 0,
                },
                "roles": [],
                "failures": [],
                "dependencies": {
                    "collections": [],
                    "roles": [],
                    "conflicts": [],
                },
                "plugin_catalog": {
                    "summary": {
                        "total_plugins": 0,
                        "types_present": [],
                        "files_scanned": 0,
                        "files_failed": 0,
                    },
                    "by_type": {
                        "filter": [],
                        "modules": [],
                        "lookup": [],
                        "inventory": [],
                        "callback": [],
                        "connection": [],
                        "strategy": [],
                        "test": [],
                        "doc_fragments": [],
                        "module_utils": [],
                    },
                    "failures": [],
                },
            }

        monkeypatch.setattr(cli_module.api, "scan_collection", _fake_scan_collection)
        rc = cli_module.main(["collection", r"C:\\work\\demo_collection"])

    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.splitlines() == [
        "Collection: demo_collection",
        "Roles scanned: 1",
        "Roles failed: 0",
    ]


def test_fsrc_cli_collection_text_output_uses_metadata_namespace_and_name(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with _prefer_fsrc_prism_on_sys_path():
        cli_module = importlib.import_module("prism.cli")

        def _fake_scan_collection(
            collection_path: str,
            **kwargs: object,
        ) -> dict[str, object]:
            del collection_path
            del kwargs
            return {
                "collection": {
                    "path": "/tmp/fallback-name",
                    "metadata": {
                        "namespace": "typed",
                        "name": "payload",
                    },
                },
                "summary": {
                    "total_roles": 2,
                    "scanned_roles": 2,
                    "failed_roles": 0,
                },
                "roles": [],
                "failures": [],
                "dependencies": {
                    "collections": [],
                    "roles": [],
                    "conflicts": [],
                },
                "plugin_catalog": {
                    "summary": {
                        "total_plugins": 0,
                        "types_present": [],
                        "files_scanned": 0,
                        "files_failed": 0,
                    },
                    "by_type": {
                        "filter": [],
                        "modules": [],
                        "lookup": [],
                        "inventory": [],
                        "callback": [],
                        "connection": [],
                        "strategy": [],
                        "test": [],
                        "doc_fragments": [],
                        "module_utils": [],
                    },
                    "failures": [],
                },
            }

        monkeypatch.setattr(cli_module.api, "scan_collection", _fake_scan_collection)
        rc = cli_module.main(["collection", "/tmp/fallback-name"])

    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out.splitlines() == [
        "Collection: typed.payload",
        "Roles scanned: 2",
        "Roles failed: 0",
    ]
