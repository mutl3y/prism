"""Collection dependency aggregation for the fsrc package lane."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from prism.errors import (
    PrismRuntimeError,
    ROLE_CONTENT_ENCODING_INVALID,
    ROLE_CONTENT_IO_ERROR,
    ROLE_CONTENT_YAML_INVALID,
)


def aggregate_collection_dependencies(collection_root: Path) -> dict[str, Any]:
    collection_bucket: dict[str, dict[str, Any]] = {}
    role_bucket: dict[str, dict[str, Any]] = {}

    sources: list[tuple[Path, str]] = [
        (
            collection_root / "collections" / "requirements.yml",
            "collections/requirements.yml",
        ),
        (
            collection_root / "roles" / "requirements.yml",
            "roles/requirements.yml",
        ),
    ]

    roles_dir = collection_root / "roles"
    if roles_dir.is_dir():
        for role_dir in sorted(path for path in roles_dir.iterdir() if path.is_dir()):
            sources.append(
                (
                    role_dir / "meta" / "requirements.yml",
                    f"roles/{role_dir.name}/meta/requirements.yml",
                )
            )

    for req_path, source_label in sources:
        document = _load_yaml_document(req_path)
        entries = _requirements_entries_from_document(document)
        for index, entry in enumerate(entries):
            entry_type = str(entry.get("type") or "").strip().lower()
            if req_path.parts[-2:] == ("collections", "requirements.yml"):
                entry_type = "collection"
            elif req_path.parts[-2:] == ("roles", "requirements.yml"):
                entry_type = "role"

            if entry_type == "collection":
                key = _collection_dependency_key(entry)
                if key:
                    _merge_dependency_entry(
                        collection_bucket,
                        key=key,
                        dep_type="collection",
                        entry=entry,
                        source=source_label,
                    )
                continue

            key = _role_dependency_key(entry, index)
            _merge_dependency_entry(
                role_bucket,
                key=key,
                dep_type="role",
                entry=entry,
                source=source_label,
            )

    collections, collection_conflicts = _finalize_dependency_bucket(
        collection_bucket,
        "version_conflict",
    )
    roles, role_conflicts = _finalize_dependency_bucket(
        role_bucket,
        "dependency_conflict",
    )

    return {
        "collections": collections,
        "roles": roles,
        "conflicts": [*collection_conflicts, *role_conflicts],
    }


def _load_yaml_document(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.is_file():
        return None
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise PrismRuntimeError(
            code=ROLE_CONTENT_ENCODING_INVALID,
            category="io",
            message=f"failed to decode YAML document: {path}",
            detail={"path": str(path)},
        ) from exc
    except yaml.YAMLError as exc:
        raise PrismRuntimeError(
            code=ROLE_CONTENT_YAML_INVALID,
            category="parser",
            message=f"failed to parse YAML document: {path}",
            detail={"path": str(path)},
        ) from exc
    except OSError as exc:
        raise PrismRuntimeError(
            code=ROLE_CONTENT_IO_ERROR,
            category="io",
            message=f"failed to read YAML document: {path}",
            detail={"path": str(path)},
        ) from exc
    if isinstance(loaded, (dict, list)):
        return loaded
    return None


def _requirements_entries_from_document(document: Any) -> list[dict[str, Any]]:
    if isinstance(document, list):
        return [item for item in document if isinstance(item, dict)]
    if isinstance(document, dict):
        entries: list[dict[str, Any]] = []
        for key in ("collections", "roles"):
            value = document.get(key)
            if isinstance(value, list):
                entries.extend(item for item in value if isinstance(item, dict))
        return entries
    return []


def _collection_dependency_key(entry: dict[str, Any]) -> str | None:
    name = str(entry.get("name") or "").strip()
    if name and "." in name:
        return name
    src = str(entry.get("src") or "").strip()
    if src and "." in src and "/" not in src:
        return src
    return None


def _role_dependency_key(entry: dict[str, Any], index: int) -> str:
    name = str(entry.get("name") or "").strip()
    if name:
        return name
    src = str(entry.get("src") or "").strip()
    if src:
        return src
    return f"unknown:{index}"


def _merge_dependency_entry(
    bucket: dict[str, dict[str, Any]],
    *,
    key: str,
    dep_type: str,
    entry: dict[str, Any],
    source: str,
) -> None:
    item = bucket.setdefault(
        key,
        {
            "key": key,
            "type": dep_type,
            "name": str(entry.get("name") or "").strip() or None,
            "src": str(entry.get("src") or "").strip() or None,
            "versions": set(),
            "sources": set(),
            "raw": [],
        },
    )
    version = str(entry.get("version") or "").strip()
    if version:
        item["versions"].add(version)
    item["sources"].add(source)
    item["raw"].append(dict(entry))


def _finalize_dependency_bucket(
    bucket: dict[str, dict[str, Any]],
    conflict_label: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    conflicts: list[dict[str, Any]] = []
    items: list[dict[str, Any]] = []
    for key in sorted(bucket):
        item = bucket[key]
        versions = sorted(item["versions"])
        sources = sorted(item["sources"])
        items.append(
            {
                "key": item["key"],
                "type": item["type"],
                "name": item["name"],
                "src": item["src"],
                "version": versions[0] if len(versions) == 1 else None,
                "versions": versions,
                "sources": sources,
            }
        )
        if len(versions) > 1:
            conflicts.append(
                {
                    "conflict": conflict_label,
                    "key": key,
                    "versions": versions,
                    "sources": sources,
                }
            )
    return items, conflicts
