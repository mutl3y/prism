"""Requirement and collection-compliance helpers for README rendering."""

from __future__ import annotations

import re


def format_requirement_line(item: object) -> str:
    """Format one requirement entry into a markdown-safe display line."""
    if isinstance(item, dict):
        source_value = item.get("src") or item.get("name") or ""
        line = str(source_value)
        version = item.get("version")
        if version:
            line += f" (version: {version})"
        return line
    return str(item)


def normalize_requirements(requirements: list) -> list[str]:
    """Normalize requirements entries to display strings."""
    lines = [format_requirement_line(item).strip() for item in requirements]
    return [line for line in lines if line]


def normalize_meta_role_dependencies(meta: dict) -> list[str]:
    """Normalize role dependencies from meta/main.yml for README output."""
    dependencies = meta.get("dependencies") if isinstance(meta, dict) else None
    if not isinstance(dependencies, list):
        return []
    lines = [format_requirement_line(item).strip() for item in dependencies]
    return [line for line in lines if line]


def normalize_included_role_dependencies(features: dict) -> list[str]:
    """Normalize static role includes detected from task parsing features."""
    raw = str((features or {}).get("included_roles", "none")).strip()
    if not raw or raw == "none":
        return []
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return sorted(set(values))


def extract_declared_collections_from_meta(
    meta: dict,
    builtin_collection_prefixes: frozenset[str] = frozenset(),
) -> set[str]:
    """Extract declared collections from meta/main.yml, excluding built-in platform prefixes."""
    declared: set[str] = set()
    galaxy = meta.get("galaxy_info") if isinstance(meta, dict) else None
    if not isinstance(galaxy, dict):
        return declared
    collections_raw = galaxy.get("collections")
    if not isinstance(collections_raw, list):
        return declared
    for item in collections_raw:
        if not isinstance(item, str):
            continue
        candidate = item.strip()
        if not candidate or any(
            candidate.startswith(p) for p in builtin_collection_prefixes
        ):
            continue
        if re.match(r"^[A-Za-z0-9_]+\.[A-Za-z0-9_]+$", candidate):
            declared.add(candidate)
    return declared


def extract_declared_collections_from_requirements(
    requirements: list,
    builtin_collection_prefixes: frozenset[str] = frozenset(),
) -> set[str]:
    """Extract declared collections from meta/requirements.yml, excluding built-in platform prefixes."""
    declared: set[str] = set()
    for item in requirements:
        raw: object = item
        if isinstance(item, dict):
            raw = item.get("src") or item.get("name") or ""
        if not isinstance(raw, str):
            continue
        candidate = raw.strip().split()[0]
        if not candidate or any(
            candidate.startswith(p) for p in builtin_collection_prefixes
        ):
            continue
        if re.match(r"^[A-Za-z0-9_]+\.[A-Za-z0-9_]+$", candidate):
            declared.add(candidate)
    return declared


def build_collection_compliance_notes(
    *,
    features: dict,
    meta: dict,
    requirements: list,
    builtin_collection_prefixes: frozenset[str] = frozenset(),
) -> list[str]:
    """Build human-readable notes about collection declaration coverage."""
    raw_collections = str(features.get("external_collections", "none")).strip()
    if not raw_collections or raw_collections == "none":
        return []

    detected = {item.strip() for item in raw_collections.split(",") if item.strip()}
    if not detected:
        return []

    declared_meta = extract_declared_collections_from_meta(
        meta, builtin_collection_prefixes=builtin_collection_prefixes
    )
    declared_requirements = extract_declared_collections_from_requirements(
        requirements, builtin_collection_prefixes=builtin_collection_prefixes
    )
    missing_meta = sorted(detected - declared_meta)
    missing_requirements = sorted(detected - declared_requirements)

    notes = [
        "Detected external collections from task usage: "
        + ", ".join(sorted(detected))
        + "."
    ]
    if missing_meta:
        notes.append(
            "Missing from meta/main.yml galaxy_info.collections: "
            + ", ".join(missing_meta)
            + "."
        )
    if missing_requirements:
        notes.append(
            "Missing from meta/requirements.yml: "
            + ", ".join(missing_requirements)
            + "."
        )
    return notes


def build_requirements_display(
    *,
    requirements: list,
    meta: dict,
    features: dict,
    include_collection_checks: bool = True,
    builtin_collection_prefixes: frozenset[str] = frozenset(),
) -> tuple[list[str], list[str]]:
    """Build rendered requirements lines and collection compliance notes."""
    collection_compliance_notes = []
    if include_collection_checks:
        collection_compliance_notes = build_collection_compliance_notes(
            features=features,
            meta=meta,
            requirements=requirements,
            builtin_collection_prefixes=builtin_collection_prefixes,
        )
    requirements_display = normalize_requirements(requirements)
    meta_dependencies_display = normalize_meta_role_dependencies(meta)
    for dep in meta_dependencies_display:
        if dep not in requirements_display:
            requirements_display.append(dep)
    included_role_dependencies = normalize_included_role_dependencies(features)
    for dep in included_role_dependencies:
        rendered = f"[Role include] {dep}"
        if rendered not in requirements_display:
            requirements_display.append(rendered)
    if include_collection_checks:
        requirements_display.extend(
            f"[Collection check] {note}" for note in collection_compliance_notes
        )
    return requirements_display, collection_compliance_notes
