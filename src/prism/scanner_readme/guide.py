"""Guide section/body rendering helpers for the fsrc lane."""

from __future__ import annotations

import logging
from typing import Any

from prism.scanner_plugins.defaults import resolve_readme_renderer_plugin

logger = logging.getLogger(__name__)


def _render_identity_purpose_section(metadata: dict[str, Any]) -> str:
    """Render inferred purpose and capabilities from doc insights."""
    insights = metadata.get("doc_insights") or {}
    lines = [insights.get("purpose_summary", "No inferred role summary available.")]
    capabilities = insights.get("capabilities", [])
    if capabilities:
        lines.extend(["", "Capabilities:"])
        lines.extend(f"- {capability}" for capability in capabilities)
    return "\n".join(lines)


def _render_identity_role_notes_section(role_notes: Any) -> str:
    """Render role notes from metadata; handles dict or list form."""
    if isinstance(role_notes, list):
        if not role_notes:
            return "No role notes detected."
        return "\n".join(f"- {note}" for note in role_notes)
    notes = role_notes or {}
    warnings = notes.get("warnings") or []
    deprecations = notes.get("deprecations") or []
    general = notes.get("notes") or []
    additionals = notes.get("additionals") or []
    if not warnings and not deprecations and not general and not additionals:
        return "No role notes were found in comment annotations."
    lines: list[str] = []
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"- {item}" for item in warnings)
    if deprecations:
        if lines:
            lines.append("")
        lines.append("Deprecations:")
        lines.extend(f"- {item}" for item in deprecations)
    if general:
        if lines:
            lines.append("")
        lines.append("Notes:")
        lines.extend(f"- {item}" for item in general)
    if additionals:
        if lines:
            lines.append("")
        lines.append("Additional notes:")
        lines.extend(f"- {item}" for item in additionals)
    return "\n".join(lines)


def _render_guide_identity_sections(
    section_id: str,
    role_name: str,
    description: str,
    requirements: list[Any],
    galaxy: dict[str, Any],
    metadata: dict[str, Any],
) -> str | None:
    """Render style-guide sections focused on role identity and metadata."""
    raw_platform_key = (metadata or {}).get("platform_key")
    if not raw_platform_key:
        logger.warning(
            "platform_key missing or empty (value=%r); defaulting to 'ansible' in render_guide_identity_section",
            raw_platform_key,
        )
    platform_key = str(raw_platform_key or "ansible")
    return resolve_readme_renderer_plugin(platform_key).render_identity_section(
        section_id,
        role_name,
        description,
        requirements,
        galaxy,
        metadata or {},
    )


def render_guide_section_body(
    section_id: str,
    role_name: str,
    description: str,
    variables: dict[str, Any],
    requirements: list[Any],
    default_filters: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> str:
    """Render foundational README section body content for known section IDs."""
    raw_platform_key = (metadata or {}).get("platform_key")
    if not raw_platform_key:
        logger.warning(
            "platform_key missing or empty (value=%r); defaulting to 'ansible' in render_guide_section_body",
            raw_platform_key,
        )
    platform_key = str(raw_platform_key or "ansible")
    result = resolve_readme_renderer_plugin(platform_key).render_section_body(
        section_id,
        role_name,
        description,
        variables,
        requirements,
        default_filters,
        metadata or {},
    )
    return result if result is not None else ""
