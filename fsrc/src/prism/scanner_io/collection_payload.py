"""Helpers for fsrc collection payload normalization."""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any

import yaml

from prism.errors import (
    ERROR_CATEGORY_RUNTIME,
    PrismRuntimeError,
    ROLE_CONTENT_ENCODING_INVALID,
    ROLE_CONTENT_INVALID,
    ROLE_CONTENT_IO_ERROR,
    ROLE_CONTENT_JSON_INVALID,
    ROLE_CONTENT_MISSING,
    ROLE_CONTENT_YAML_INVALID,
    ROLE_SCAN_RUNTIME_ERROR,
    to_failure_detail,
)


_PLUGIN_TYPES: tuple[str, ...] = (
    "filter",
    "modules",
    "lookup",
    "inventory",
    "callback",
    "connection",
    "strategy",
    "test",
    "doc_fragments",
    "module_utils",
)

_PLUGIN_CATALOG_SCHEMA_VERSION = 1

_COLLECTION_ROLE_FAILURE_CODES: tuple[tuple[type[Exception], str, str], ...] = (
    (FileNotFoundError, ROLE_CONTENT_MISSING, "io"),
    (UnicodeDecodeError, ROLE_CONTENT_ENCODING_INVALID, "io"),
    (json.JSONDecodeError, ROLE_CONTENT_JSON_INVALID, "parser"),
    (yaml.YAMLError, ROLE_CONTENT_YAML_INVALID, "parser"),
    (OSError, ROLE_CONTENT_IO_ERROR, "io"),
    (ValueError, ROLE_CONTENT_INVALID, "validation"),
)


def normalize_collection_role_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if "variables" not in normalized and "display_variables" in normalized:
        normalized["variables"] = normalized["display_variables"]
    if "requirements" not in normalized and "requirements_display" in normalized:
        normalized["requirements"] = normalized["requirements_display"]
    if (
        "default_filters" not in normalized
        and "undocumented_default_filters" in normalized
    ):
        normalized["default_filters"] = normalized["undocumented_default_filters"]
    return normalized


def _load_collection_metadata(galaxy_path: Path) -> dict[str, Any]:
    try:
        galaxy_text = galaxy_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PrismRuntimeError(
            code="collection_galaxy_metadata_io_error",
            category="io",
            message=f"collection galaxy metadata is unreadable: {galaxy_path}",
            detail={"galaxy_path": str(galaxy_path)},
        ) from exc

    try:
        galaxy_payload = yaml.safe_load(galaxy_text)
    except (yaml.YAMLError, ValueError) as exc:
        raise PrismRuntimeError(
            code="collection_galaxy_metadata_yaml_invalid",
            category="parser",
            message=f"collection galaxy metadata is invalid YAML: {galaxy_path}",
            detail={"galaxy_path": str(galaxy_path)},
        ) from exc

    if not isinstance(galaxy_payload, dict):
        raise PrismRuntimeError(
            code="collection_galaxy_metadata_invalid",
            category="validation",
            message=f"collection galaxy metadata must be a mapping: {galaxy_path}",
            detail={"galaxy_path": str(galaxy_path)},
        )

    return galaxy_payload


def build_collection_identity(collection_root: Path) -> dict[str, Any]:
    return {
        "path": str(collection_root.resolve()),
        "metadata": _load_collection_metadata(collection_root / "galaxy.yml"),
    }


def empty_collection_dependencies() -> dict[str, list[dict[str, Any]]]:
    return {
        "collections": [],
        "roles": [],
        "conflicts": [],
    }


def empty_plugin_catalog() -> dict[str, Any]:
    return {
        "schema_version": _PLUGIN_CATALOG_SCHEMA_VERSION,
        "summary": {
            "total_plugins": 0,
            "types_present": [],
            "files_scanned": 0,
            "files_failed": 0,
        },
        "by_type": {plugin_type: [] for plugin_type in _PLUGIN_TYPES},
        "failures": [],
    }


def build_collection_role_entry(
    *,
    role_dir: Path,
    payload: dict[str, Any],
    rendered_readme: str | None,
) -> dict[str, Any]:
    normalized_payload = normalize_collection_role_payload(payload)

    return {
        "role": role_dir.name,
        "path": str(role_dir.resolve()),
        "payload": normalized_payload,
        "rendered_readme": rendered_readme,
    }


def render_collection_role_readme(
    *,
    role_name: str,
    payload: dict[str, Any],
    render_readme_fn,
) -> str:
    normalized_payload = normalize_collection_role_payload(payload)
    return render_readme_fn(
        output="README.md",
        role_name=str(normalized_payload.get("role_name") or role_name),
        description=str(normalized_payload.get("description") or ""),
        variables=(normalized_payload.get("variables") or {}),
        requirements=(normalized_payload.get("requirements") or []),
        default_filters=(normalized_payload.get("default_filters") or []),
        metadata=(normalized_payload.get("metadata") or {}),
        write=False,
    )


def _collection_role_failure_details(exc: Exception) -> tuple[str, str, str | None]:
    if isinstance(exc, PrismRuntimeError):
        return exc.code, exc.category, exc.code

    for error_type, code, category in _COLLECTION_ROLE_FAILURE_CODES:
        if isinstance(exc, error_type):
            return code, category, None
    return ROLE_SCAN_RUNTIME_ERROR, ERROR_CATEGORY_RUNTIME, None


def build_collection_failure_record(
    *,
    role_dir: Path,
    exc: Exception,
    include_traceback: bool,
) -> dict[str, Any]:
    error_code, error_category, error_detail_code = _collection_role_failure_details(
        exc
    )
    traceback_text = (
        "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        if include_traceback
        else None
    )
    detail = to_failure_detail(
        code=error_code,
        message=str(exc),
        detail_code=error_detail_code,
        source=str(role_dir.resolve()),
        cause=exc,
        traceback_text=traceback_text,
    )

    failure = {
        "role": role_dir.name,
        "path": str(role_dir.resolve()),
        "error_code": detail["code"],
        "error_category": detail["category"],
        "error_type": detail.get("cause_type", type(exc).__name__),
        "error": detail["message"],
    }
    if error_detail_code is not None:
        failure["error_detail_code"] = error_detail_code
        failure["detail_code"] = error_detail_code
    if traceback_text:
        failure["traceback"] = traceback_text
    return failure


def build_collection_scan_result(
    *,
    collection_root: Path,
    collection_identity: dict[str, Any] | None = None,
    dependencies: dict[str, Any] | None = None,
    plugin_catalog: dict[str, Any] | None = None,
    roles: list[dict[str, Any]],
    failures: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "collection": (
            dict(collection_identity)
            if isinstance(collection_identity, dict)
            else build_collection_identity(collection_root)
        ),
        "dependencies": (
            dict(dependencies)
            if isinstance(dependencies, dict)
            else empty_collection_dependencies()
        ),
        "plugin_catalog": (
            dict(plugin_catalog)
            if isinstance(plugin_catalog, dict)
            else empty_plugin_catalog()
        ),
        "roles": roles,
        "failures": failures,
        "summary": {
            "total_roles": len(roles) + len(failures),
            "scanned_roles": len(roles),
            "failed_roles": len(failures),
        },
    }
