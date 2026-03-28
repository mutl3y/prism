"""Scanner requirements and collection handling.

This module contains requirements and collection-related functions
extracted from scanner.py for improved organization.
"""

from __future__ import annotations

from . import (
    build_collection_compliance_notes as _requirements_build_collection_compliance_notes,
    build_requirements_display as _requirements_build_display,
    extract_declared_collections_from_meta as _requirements_extract_declared_meta,
    extract_declared_collections_from_requirements as _requirements_extract_declared_requirements,
    format_requirement_line as _requirements_format_line,
    normalize_included_role_dependencies as _requirements_normalize_included_roles,
    normalize_meta_role_dependencies as _requirements_normalize_meta_deps,
    normalize_requirements as _requirements_normalize,
)


def format_requirement_line(item: object) -> str:
    """Format one requirement entry into a markdown-safe display line.

    Args:
        item: Requirement item from requirements list

    Returns:
        Formatted display string
    """
    return _requirements_format_line(item)


def normalize_requirements(requirements: list) -> list[str]:
    """Normalize requirements entries to display strings.

    Args:
        requirements: List of requirement entries

    Returns:
        List of normalized requirement strings
    """
    return _requirements_normalize(requirements)


def normalize_meta_role_dependencies(meta: dict) -> list[str]:
    """Normalize role dependencies from ``meta/main.yml`` for README output.

    Args:
        meta: Role metadata dictionary

    Returns:
        List of normalized role dependencies
    """
    return _requirements_normalize_meta_deps(meta)


def normalize_included_role_dependencies(features: dict) -> list[str]:
    """Normalize static role includes detected from task parsing features.

    Args:
        features: Task parsing features dictionary

    Returns:
        List of normalized included role dependencies
    """
    return _requirements_normalize_included_roles(features)


def extract_declared_collections_from_meta(meta: dict) -> set[str]:
    """Extract declared non-ansible collections from ``meta/main.yml`` content.

    Args:
        meta: Role metadata dictionary

    Returns:
        Set of declared collection names
    """
    return _requirements_extract_declared_meta(meta)


def extract_declared_collections_from_requirements(requirements: list) -> set[str]:
    """Extract declared non-ansible collections from ``meta/requirements.yml``.

    Args:
        requirements: Requirements list

    Returns:
        Set of declared collection names
    """
    return _requirements_extract_declared_requirements(requirements)


def build_collection_compliance_notes(
    *,
    features: dict,
    meta: dict,
    requirements: list,
) -> list[str]:
    """Build human-readable notes about collection declaration coverage.

    Args:
        features: Task parsing features dictionary
        meta: Role metadata dictionary
        requirements: Requirements list

    Returns:
        List of compliance notes
    """
    return _requirements_build_collection_compliance_notes(
        features=features,
        meta=meta,
        requirements=requirements,
    )


def build_requirements_display(
    *,
    requirements: list,
    meta: dict,
    features: dict,
    include_collection_checks: bool,
) -> tuple[list[str], list[str]]:
    """Build requirements display strings and collection compliance notes.

    Args:
        requirements: Requirements list
        meta: Role metadata dictionary
        features: Task parsing features dictionary
        include_collection_checks: Whether to include collection compliance checks

    Returns:
        Tuple of (requirements_display, collection_compliance_notes)
    """
    return _requirements_build_display(
        requirements=requirements,
        meta=meta,
        features=features,
        include_collection_checks=include_collection_checks,
    )
