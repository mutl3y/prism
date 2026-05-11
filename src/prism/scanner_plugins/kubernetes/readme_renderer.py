"""Minimal Kubernetes README renderer plugin for the bootstrap support lane."""

from __future__ import annotations

import pathlib
from typing import Any

_DEFAULT_SECTION_SPECS: tuple[tuple[str, str], ...] = (
    ("purpose", "Workload purpose and capabilities"),
    ("resources", "Kubernetes resources"),
    ("scanner_report", "Scanner report"),
)

_EXTRA_SECTION_IDS: frozenset[str] = frozenset(
    {
        "operational_notes",
        "scanner_report",
    }
)

_SCANNER_STATS_SECTION_IDS: frozenset[str] = frozenset({"resources"})

_MERGE_ELIGIBLE_SECTION_IDS: frozenset[str] = frozenset(
    {
        "purpose",
        "resources",
        "operational_notes",
    }
)


class KubernetesReadmeRendererPlugin:
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
        return ("prism", "kubernetes-doc")

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
        del requirements, default_filters
        if section_id == "purpose":
            # Purpose section: use description if available, fallback to role name
            return description or f"Kubernetes workload `{role_name}`"
        
        if section_id == "resources":
            # Resources section: format list of Kubernetes resource kinds from metadata
            resources = metadata.get("resource_kinds")
            if isinstance(resources, list) and resources:
                formatted = "\n".join(f"- `{resource}`" for resource in resources)
                return formatted
            return "No Kubernetes resource inventory is available yet."
        
        if section_id == "operational_notes":
            # Operational notes section: list notes from metadata or bootstrap indicator
            notes = metadata.get("operational_notes")
            if isinstance(notes, list) and notes:
                formatted = "\n".join(f"- {note}" for note in notes)
                return formatted
            # Indicate bootstrap status if variables are present
            if variables:
                return "Bootstrap slice only: variable-level operational guidance is not emitted yet."
            return "No operational notes detected."
        
        if section_id == "scanner_report":
            # Scanner report section: link to report path or indicate bootstrap status
            report_relpath = metadata.get("scanner_report_relpath")
            if isinstance(report_relpath, str) and report_relpath:
                return self.scanner_report_blurb(report_relpath)
            return "Scanner report output is not wired for the Kubernetes bootstrap slice yet."
        
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
        del requirements, metadata
        if section_id == "purpose":
            # Purpose: combine description with namespace if available
            namespace = identity_metadata.get("namespace")
            if isinstance(namespace, str) and namespace:
                base_desc = description or role_name
                return f"{base_desc}\n\nTarget namespace: `{namespace}`"
            return description or role_name
        
        if section_id == "resources":
            # Resources: show cluster target if available
            cluster = identity_metadata.get("cluster")
            if isinstance(cluster, str) and cluster:
                return f"Cluster target: `{cluster}`"
            return "Cluster target is not declared."
        
        return None

    def default_template_path(self) -> pathlib.Path | None:
        return None

    def scanner_report_blurb(self, scanner_report_relpath: str) -> str:
        return (
            f"Detailed scanner output is available in `{scanner_report_relpath}`. "
            "This bootstrap Kubernetes slice currently exposes renderer and "
            "execution-bundle seams without full platform parity."
        )