"""Compatibility wrapper surface for extracted README/guide render helpers."""

from __future__ import annotations

from prism.scanner_readme.render import (
    _compose_section_body,
    _generated_merge_markers,
    _render_readme_with_style_guide,
    _resolve_ordered_style_sections,
    _resolve_section_content_mode,
    _strip_prior_generated_merge_block,
    append_scanner_report_section_if_enabled as _append_scanner_report_section_if_enabled,
)
from prism.scanner_readme.guide import (
    _render_guide_identity_sections,
    render_guide_section_body as _render_guide_section_body,
)


def render_guide_identity_sections(
    section_id: str,
    role_name: str,
    description: str,
    requirements: list,
    galaxy: dict,
    metadata: dict,
) -> str | None:
    return _render_guide_identity_sections(
        section_id, role_name, description, requirements, galaxy, metadata
    )


def render_guide_section_body(
    section_id: str,
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
    *,
    variable_guidance_keywords: list[str] | None = None,
) -> str:
    return _render_guide_section_body(
        section_id,
        role_name,
        description,
        variables,
        requirements,
        default_filters,
        metadata,
    )


def generated_merge_markers(section_id: str) -> list[tuple[str, str]]:
    return _generated_merge_markers(section_id)


def strip_prior_generated_merge_block(section: dict, guide_body: str) -> str:
    return _strip_prior_generated_merge_block(section, guide_body)


def resolve_section_content_mode(section: dict, modes: dict[str, str]) -> str:
    return _resolve_section_content_mode(section, modes)


def compose_section_body(
    section: dict,
    generated_body: str,
    mode: str,
    metadata: dict | None = None,
) -> str:
    return _compose_section_body(section, generated_body, mode, metadata or {})


def resolve_ordered_style_sections(
    style_guide: dict,
    metadata: dict,
) -> tuple:
    return _resolve_ordered_style_sections(style_guide, metadata)


def append_scanner_report_section_if_enabled(
    parts: list[str],
    style_guide: dict,
    style_guide_skeleton: bool,
    scanner_report_relpath: str | None,
    include_scanner_report_link: bool,
    enabled_sections: set[str],
) -> None:
    _append_scanner_report_section_if_enabled(
        parts,
        style_guide,
        style_guide_skeleton,
        scanner_report_relpath,
        include_scanner_report_link,
        enabled_sections,
    )


def render_readme_with_style_guide(
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
) -> str:
    return _render_readme_with_style_guide(
        role_name, description, variables, requirements, default_filters, metadata
    )
