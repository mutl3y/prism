"""Guide section/body rendering helpers for the fsrc lane."""

from __future__ import annotations

from typing import Any


def refresh_policy_derived_state(_policy: dict[str, Any]) -> None:
    """Compatibility no-op for parity with src scanner_readme guide API."""
    return None


def _render_guide_section_body(
    section_id: str,
    role_name: str,
    description: str,
    variables: dict[str, Any],
    requirements: list[Any],
    default_filters: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> str:
    """Render foundational README section body content for known section IDs."""
    if section_id == "purpose":
        return description or f"Role `{role_name}`"

    if section_id == "requirements":
        if not requirements:
            return "No additional requirements."
        return "\n".join(f"- {item}" for item in requirements)

    if section_id == "role_variables":
        if not variables:
            return "No role variables detected."
        lines = []
        for name, detail in variables.items():
            default_value = ""
            if isinstance(detail, dict):
                default_value = str(detail.get("default", ""))
            lines.append(f"- `{name}`: `{default_value}`")
        return "\n".join(lines)

    if section_id == "default_filters":
        if not default_filters:
            return "No default() filter usage detected."
        return "\n".join(f"- `{entry.get('target', '')}`" for entry in default_filters)

    if section_id == "role_notes":
        role_notes = metadata.get("role_notes") if isinstance(metadata, dict) else None
        if not isinstance(role_notes, list) or not role_notes:
            return "No role notes detected."
        return "\n".join(f"- {note}" for note in role_notes)

    return ""
