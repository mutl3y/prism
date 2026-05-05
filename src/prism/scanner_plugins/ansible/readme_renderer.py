"""Ansible README renderer plugin for the prism scanner."""

from __future__ import annotations

import pathlib
from typing import Any

from prism.scanner_plugins.ansible.extract_utils import normalize_requirements

_DEFAULT_SECTION_SPECS: tuple[tuple[str, str], ...] = (
    ("galaxy_info", "Galaxy Info"),
    ("requirements", "Requirements"),
    ("purpose", "Role purpose and capabilities"),
    ("role_notes", "Role notes"),
    ("variable_summary", "Inputs / variables summary"),
    ("task_summary", "Task/module usage summary"),
    ("example_usage", "Inferred example usage"),
    ("role_variables", "Role Variables"),
    ("role_contents", "Role contents summary"),
    ("features", "Auto-detected role features"),
    ("comparison", "Comparison against local baseline role"),
    ("default_filters", "Detected usages of the default() filter"),
)

_EXTRA_SECTION_IDS: frozenset[str] = frozenset(
    {
        "basic_authorization",
        "handlers",
        "installation",
        "license",
        "author_information",
        "license_author",
        "sponsors",
        "template_overrides",
        "variable_guidance",
        "local_testing",
        "faq_pitfalls",
        "contributing",
        "scanner_report",
        "role_notes",
    }
)

_SCANNER_STATS_SECTION_IDS: frozenset[str] = frozenset(
    {
        "task_summary",
        "role_contents",
        "features",
        "comparison",
        "default_filters",
    }
)

_MERGE_ELIGIBLE_SECTION_IDS: frozenset[str] = frozenset(
    {
        "requirements",
        "purpose",
        "task_summary",
        "local_testing",
        "handlers",
        "template_overrides",
        "faq_pitfalls",
        "contributing",
    }
)


class AnsibleReadmeRendererPlugin:
    """Ansible-platform README renderer plugin.

    Owns the full Ansible README rendering vertical: section taxonomy,
    identity blocks, legacy marker prefixes, Jinja template path, and
    scanner-report blurb. All logic is Ansible-specific; the protocol
    contract is platform-neutral.
    """

    PRISM_PLUGIN_API_VERSION: tuple[int, int] = (1, 0)
    PLUGIN_IS_STATELESS: bool = True

    def default_section_specs(self) -> tuple[tuple[str, str], ...]:
        return _DEFAULT_SECTION_SPECS

    def extra_section_ids(self) -> frozenset[str]:
        return _EXTRA_SECTION_IDS

    def scanner_stats_section_ids(self) -> frozenset[str]:
        return _SCANNER_STATS_SECTION_IDS

    def merge_eligible_section_ids(self) -> frozenset[str]:
        return _MERGE_ELIGIBLE_SECTION_IDS

    def legacy_merge_marker_prefixes(self) -> tuple[str, ...]:
        return ("prism", "ansible-role-doc")

    def render_section_body(
        self,
        section_id: str,
        role_name: str,
        description: str,
        variables: dict[str, Any],
        requirements: list[Any],
        default_filters: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> str | None:
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
            return "\n".join(
                f"- `{entry.get('target', '')}`" for entry in default_filters
            )
        if section_id == "role_notes":
            role_notes = (
                metadata.get("role_notes") if isinstance(metadata, dict) else None
            )
            if not isinstance(role_notes, list) or not role_notes:
                return "No role notes detected."
            return "\n".join(f"- {note}" for note in role_notes)
        return None

    def render_identity_section(
        self,
        section_id: str,
        role_name: str,
        description: str,
        requirements: list[Any],
        identity_metadata: dict[str, Any],
        metadata: dict[str, Any],
    ) -> str | None:
        galaxy = identity_metadata
        if section_id == "galaxy_info":
            return _render_galaxy_info(role_name, description, galaxy)
        if section_id == "requirements":
            return _render_identity_requirements(requirements)
        if section_id == "installation":
            return _render_installation(role_name, galaxy)
        if section_id == "license":
            return _render_license(galaxy)
        if section_id == "author_information":
            return _render_author(galaxy)
        if section_id == "license_author":
            return _render_license_author(galaxy)
        if section_id == "sponsors":
            return "No sponsorship metadata detected for this role."
        if section_id == "purpose":
            return _render_purpose(metadata)
        if section_id == "role_notes":
            return _render_role_notes(metadata.get("role_notes"))
        return None

    def default_template_path(self) -> pathlib.Path | None:
        return pathlib.Path(__file__).parent / "templates" / "README.md.j2"

    def scanner_report_blurb(self, scanner_report_relpath: str) -> str:
        return (
            f"Detailed scanner output is available in `{scanner_report_relpath}`. "
            "It includes task/module statistics, role-content inventory, "
            "baseline comparison details, and undocumented `default()` findings."
        )


def _render_galaxy_info(
    role_name: str,
    description: str,
    galaxy: dict[str, Any],
) -> str:
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


def _render_identity_requirements(requirements: list[Any]) -> str:
    requirement_lines = normalize_requirements(requirements)
    if not requirement_lines:
        return "No additional requirements."
    return "\n".join(f"- {line}" for line in requirement_lines)


def _render_installation(role_name: str, galaxy: dict[str, Any]) -> str:
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


def _render_license(galaxy: dict[str, Any]) -> str:
    if galaxy and galaxy.get("license"):
        return str(galaxy.get("license"))
    return "N/A"


def _render_author(galaxy: dict[str, Any]) -> str:
    if galaxy and galaxy.get("author"):
        return str(galaxy.get("author"))
    return "N/A"


def _render_license_author(galaxy: dict[str, Any]) -> str:
    license_value = str(galaxy.get("license", "N/A")) if galaxy else "N/A"
    author_value = str(galaxy.get("author", "N/A")) if galaxy else "N/A"
    return f"License: {license_value}\n\nAuthor: {author_value}"


def _render_purpose(metadata: dict[str, Any]) -> str:
    insights = metadata.get("doc_insights") or {}
    lines = [insights.get("purpose_summary", "No inferred role summary available.")]
    capabilities = insights.get("capabilities", [])
    if capabilities:
        lines.extend(["", "Capabilities:"])
        lines.extend(f"- {capability}" for capability in capabilities)
    return "\n".join(lines)


def _render_role_notes(role_notes: Any) -> str:
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
