"""Minimal Terraform README renderer plugin for the kickoff slice."""

from __future__ import annotations

import pathlib
from typing import Any

_DEFAULT_SECTION_SPECS: tuple[tuple[str, str], ...] = (
    ("purpose", "Module purpose"),
    ("requirements", "Provider requirements"),
    ("resources", "Managed resources"),
    ("operational_constraints", "Operational constraints"),
    ("scanner_report", "Scanner report"),
)

_EXTRA_SECTION_IDS: frozenset[str] = frozenset(
    {"scanner_report", "resources", "operational_constraints"}
)
_SCANNER_STATS_SECTION_IDS: frozenset[str] = frozenset({"resources"})
_MERGE_ELIGIBLE_SECTION_IDS: frozenset[str] = frozenset(
    {"requirements", "purpose", "operational_constraints"}
)


class TerraformReadmeRendererPlugin:
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
        return ("prism", "terraform-doc")

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
        del default_filters
        if section_id == "purpose":
            # Use metadata description if available; fall back to description param
            module_description = metadata.get("module_description")
            if isinstance(module_description, str) and module_description:
                return module_description
            return description or f"Terraform module `{role_name}`"
        if section_id == "requirements":
            # Check metadata for provider requirements first
            provider_reqs = metadata.get("provider_requirements")
            if isinstance(provider_reqs, list) and provider_reqs:
                return "\n".join(f"- {item}" for item in provider_reqs)
            if not requirements:
                return "No additional requirements."
            return "\n".join(f"- {item}" for item in requirements)
        if section_id == "resources":
            # Prioritize metadata managed_resources over variables
            managed_resources = metadata.get("managed_resources")
            if isinstance(managed_resources, list) and managed_resources:
                return "\n".join(f"- {name}" for name in managed_resources)
            # Fall back to variables.resources
            resource_names = variables.get("resources")
            if not isinstance(resource_names, list) or not resource_names:
                return "No managed resources detected in this slice."
            return "\n".join(f"- {name}" for name in resource_names)
        if section_id == "operational_constraints":
            # Render operational constraints from metadata
            constraints = metadata.get("operational_constraints")
            if isinstance(constraints, list) and constraints:
                return "\n".join(f"- {constraint}" for constraint in constraints)
            return "No operational constraints detected."
        if section_id == "scanner_report":
            # Render scanner report section from metadata
            report_relpath = metadata.get("scanner_report_relpath")
            if isinstance(report_relpath, str) and report_relpath:
                return self.scanner_report_blurb(report_relpath)
            return None
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
        del metadata
        if section_id == "requirements":
            if not requirements:
                return "No additional requirements."
            return "\n".join(f"- {item}" for item in requirements)
        if section_id == "purpose":
            # Include workspace information if available
            workspace = identity_metadata.get("workspace")
            if isinstance(workspace, str) and workspace:
                return f"{description or role_name}\n\nWorkspace: `{workspace}`"
            return description or role_name
        return None

    def default_template_path(self) -> pathlib.Path | None:
        return None

    def scanner_report_blurb(self, scanner_report_relpath: str) -> str:
        return (
            "Detailed scanner-report output is available in "
            f"`{scanner_report_relpath}` for this Terraform slice."
        )


__all__ = ["TerraformReadmeRendererPlugin"]