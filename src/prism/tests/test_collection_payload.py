"""Unit tests for prism.scanner_io.collection_payload (FIND-13 closure)."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from prism.errors import PrismRuntimeError
from prism.scanner_data import CollectionIdentity, CollectionRoleEntry
from prism.scanner_io.collection_payload import (
    ROLE_CONTENT_YAML_INVALID,
    build_collection_failure_record,
    build_collection_identity,
    build_collection_role_entry,
    build_collection_scan_result,
    empty_collection_dependencies,
    empty_plugin_catalog,
    normalize_collection_role_payload,
    render_collection_role_readme,
)


def test_normalize_promotes_display_aliases() -> None:
    payload = {
        "display_variables": {"x": 1},
        "requirements_display": [{"src": "r"}],
        "undocumented_default_filters": ["f"],
    }
    out = normalize_collection_role_payload(payload)
    assert out["variables"] == {"x": 1}
    assert out["requirements"] == [{"src": "r"}]
    assert out["default_filters"] == ["f"]


def test_normalize_does_not_overwrite_existing_canonical_keys() -> None:
    out = normalize_collection_role_payload(
        {"variables": {"a": 1}, "display_variables": {"b": 2}}
    )
    assert out["variables"] == {"a": 1}


def test_empty_collection_dependencies_shape() -> None:
    deps = empty_collection_dependencies()
    assert deps == {"collections": [], "roles": [], "conflicts": []}


def test_empty_plugin_catalog_shape() -> None:
    cat = empty_plugin_catalog()
    assert cat["schema_version"] == 1
    assert cat["summary"]["total_plugins"] == 0
    assert cat["failures"] == []
    assert isinstance(cat["by_type"], dict)


def test_build_collection_role_entry_includes_normalized_payload(
    tmp_path: Path,
) -> None:
    role_dir = tmp_path / "r"
    role_dir.mkdir()
    entry = build_collection_role_entry(
        role_dir=role_dir,
        payload={"display_variables": {"v": 1}},
        rendered_readme="# r",
    )
    assert entry["role"] == "r"
    assert entry["payload"]["variables"] == {"v": 1}
    assert entry["rendered_readme"] == "# r"


def test_render_collection_role_readme_passes_normalized_kwargs() -> None:
    captured: dict = {}

    def fake_render(**kwargs):
        captured.update(kwargs)
        return "rendered"

    out = render_collection_role_readme(
        role_name="fallback",
        payload={
            "role_name": "explicit",
            "display_variables": {"a": 1},
            "requirements_display": [{"src": "r"}],
            "undocumented_default_filters": ["f"],
            "metadata": {"k": "v"},
        },
        render_readme_fn=fake_render,
    )
    assert out == "rendered"
    assert captured["role_name"] == "explicit"
    assert captured["variables"] == {"a": 1}
    assert captured["requirements"] == [{"src": "r"}]
    assert captured["default_filters"] == ["f"]
    assert captured["write"] is False


def test_render_collection_role_readme_uses_fallback_role_name() -> None:
    captured: dict = {}
    render_collection_role_readme(
        role_name="fallback",
        payload={},
        render_readme_fn=lambda **kw: captured.update(kw) or "",
    )
    assert captured["role_name"] == "fallback"


def test_build_collection_failure_record_for_io_error(tmp_path: Path) -> None:
    role_dir = tmp_path / "r"
    role_dir.mkdir()
    record = build_collection_failure_record(
        role_dir=role_dir,
        exc=FileNotFoundError("missing"),
        include_traceback=False,
    )
    assert record["role"] == "r"
    assert record["error_category"] == "io"
    assert "traceback" not in record


def test_build_collection_failure_record_includes_traceback_when_requested(
    tmp_path: Path,
) -> None:
    role_dir = tmp_path / "r"
    role_dir.mkdir()
    try:
        raise ValueError("boom")
    except ValueError as exc:
        record = build_collection_failure_record(
            role_dir=role_dir, exc=exc, include_traceback=True
        )
    assert "traceback" in record
    assert "ValueError" in record["traceback"]


def test_build_collection_failure_record_for_prism_runtime_error(
    tmp_path: Path,
) -> None:
    role_dir = tmp_path / "r"
    role_dir.mkdir()
    exc = PrismRuntimeError(
        code=ROLE_CONTENT_YAML_INVALID, category="parser", message="m", detail={}
    )
    record = build_collection_failure_record(
        role_dir=role_dir, exc=exc, include_traceback=False
    )
    assert record["error_code"] == ROLE_CONTENT_YAML_INVALID
    assert record["error_category"] == "parser"
    assert record["error_detail_code"] == ROLE_CONTENT_YAML_INVALID


def test_build_collection_scan_result_uses_provided_collection_identity(
    tmp_path: Path,
) -> None:
    result = build_collection_scan_result(
        collection_root=tmp_path,
        collection_identity=cast(
            CollectionIdentity,
            {"path": "/x", "metadata": {"name": "n"}},
        ),
        dependencies={"collections": [{"key": "k"}], "roles": [], "conflicts": []},
        plugin_catalog={
            "schema_version": 1,
            "summary": {},
            "by_type": {},
            "failures": [],
        },
        roles=[
            cast(
                CollectionRoleEntry,
                {
                    "role": "a",
                    "path": "/r",
                    "payload": {
                        "role_name": "a",
                        "description": "",
                        "display_variables": {},
                        "requirements_display": [],
                        "undocumented_default_filters": [],
                        "metadata": {},
                    },
                    "rendered_readme": None,
                },
            )
        ],
        failures=[{"role": "b"}],
    )
    assert result["collection"]["path"] == "/x"
    assert result["dependencies"]["collections"] == [{"key": "k"}]
    assert result["summary"]["total_roles"] == 2
    assert result["summary"]["scanned_roles"] == 1
    assert result["summary"]["failed_roles"] == 1


def test_build_collection_identity_reads_galaxy_yaml(tmp_path: Path) -> None:
    galaxy = tmp_path / "galaxy.yml"
    galaxy.write_text("namespace: ns\nname: col\nversion: 1.0\n")
    identity = build_collection_identity(tmp_path)
    assert identity["metadata"]["namespace"] == "ns"
    assert identity["metadata"]["name"] == "col"


def test_build_collection_identity_raises_for_missing_galaxy(tmp_path: Path) -> None:
    with pytest.raises(PrismRuntimeError) as exc_info:
        build_collection_identity(tmp_path)
    assert exc_info.value.code == "collection_galaxy_metadata_io_error"


def test_build_collection_identity_raises_for_invalid_yaml(tmp_path: Path) -> None:
    galaxy = tmp_path / "galaxy.yml"
    galaxy.write_text("this:\n  is:\n bad: indent")
    with pytest.raises(PrismRuntimeError) as exc_info:
        build_collection_identity(tmp_path)
    assert exc_info.value.code == "collection_galaxy_metadata_yaml_invalid"


def test_build_collection_identity_raises_for_non_mapping_galaxy(
    tmp_path: Path,
) -> None:
    galaxy = tmp_path / "galaxy.yml"
    galaxy.write_text("- just\n- a\n- list\n")
    with pytest.raises(PrismRuntimeError) as exc_info:
        build_collection_identity(tmp_path)
    assert exc_info.value.code == "collection_galaxy_metadata_invalid"
