"""Guide section/body rendering helpers for the fsrc lane."""

from __future__ import annotations

from typing import Any

from prism.scanner_extract.requirements import normalize_requirements


def _render_identity_galaxy_info_section(
    role_name: str,
    description: str,
    galaxy: dict[str, Any],
) -> str:
    """Render Galaxy metadata section details."""
    if not galaxy:
        return "No Galaxy metadata found."
    lines = [
        f"- **Role name**: {galaxy.get('role_name', role_name)}",
        f"- **Description**: {galaxy.get('description', description)}",
        f"- **License**: {galaxy.get('license', 'N/A')}",
        f"- **Min Ansible Version**: {galaxy.get('min_ansible_version', 'N/A')}",
    ]
    tags = galaxy.get("galaxy_tags")
    if tags:
        lines.append(f"- **Tags**: {', '.join(tags)}")
    return "\n".join(lines)


def _render_identity_requirements_section(requirements: list[Any]) -> str:
    """Render normalized requirements bullet list."""
    requirement_lines = normalize_requirements(requirements)
    if not requirement_lines:
        return "No additional requirements."
    return "\n".join(f"- {line}" for line in requirement_lines)


def _render_identity_installation_section(
    role_name: str, galaxy: dict[str, Any]
) -> str:
    """Render installation guidance using Ansible Galaxy and requirements.yml."""
    install_name = str(galaxy.get("role_name") or role_name)
    return (
        "Install the role with Ansible Galaxy:\n\n"
        "```bash\n"
        f"ansible-galaxy install {install_name}\n"
        "```\n\n"
        "Or pin it in `requirements.yml`:\n\n"
        "```yaml\n"
        f"- src: {install_name}\n"
        "```"
    )


def _render_identity_license_section(galaxy: dict[str, Any]) -> str:
    """Render license value from Galaxy metadata when present."""
    if galaxy and galaxy.get("license"):
        return str(galaxy.get("license"))
    return "N/A"


def _render_identity_author_section(galaxy: dict[str, Any]) -> str:
    """Render author value from Galaxy metadata when present."""
    if galaxy and galaxy.get("author"):
        return str(galaxy.get("author"))
    return "N/A"


def _render_identity_license_author_section(galaxy: dict[str, Any]) -> str:
    """Render combined license/author identity section."""
    license_value = str(galaxy.get("license", "N/A")) if galaxy else "N/A"
    author_value = str(galaxy.get("author", "N/A")) if galaxy else "N/A"
    return f"License: {license_value}\n\nAuthor: {author_value}"


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
    if section_id == "galaxy_info":
        return _render_identity_galaxy_info_section(role_name, description, galaxy)
    if section_id == "requirements":
        return _render_identity_requirements_section(requirements)
    if section_id == "installation":
        return _render_identity_installation_section(role_name, galaxy)
    if section_id == "license":
        return _render_identity_license_section(galaxy)
    if section_id == "author_information":
        return _render_identity_author_section(galaxy)
    if section_id == "license_author":
        return _render_identity_license_author_section(galaxy)
    if section_id == "sponsors":
        return "No sponsorship metadata detected for this role."
    if section_id == "purpose":
        return _render_identity_purpose_section(metadata)
    if section_id == "role_notes":
        return _render_identity_role_notes_section(metadata.get("role_notes"))
    return None


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
