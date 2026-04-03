"""Compatibility wrapper surface for extracted README/guide render helpers."""

from __future__ import annotations

from prism.scanner_data.contracts_request import StyleGuideConfig

from ..scanner_readme import (
    _append_scanner_report_section_if_enabled,
    _compose_section_body,
    _generated_merge_markers,
    _render_readme_with_style_guide,
    _resolve_ordered_style_sections,
    _resolve_section_content_mode,
    _strip_prior_generated_merge_block,
)
from ..scanner_readme.guide import (
    _render_guide_identity_sections,
    _render_guide_section_body,
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
        section_id,
        role_name,
        description,
        requirements,
        galaxy,
        metadata,
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
    variable_guidance_keywords: list[str],
) -> str:
    return _render_guide_section_body(
        section_id,
        role_name,
        description,
        variables,
        requirements,
        default_filters,
        metadata,
        variable_guidance_keywords=variable_guidance_keywords,
    )


def generated_merge_markers(section_id: str) -> list[tuple[str, str]]:
    return _generated_merge_markers(section_id)


def strip_prior_generated_merge_block(section: dict, guide_body: str) -> str:
    return _strip_prior_generated_merge_block(section, guide_body)


def resolve_section_content_mode(section: dict, modes: dict[str, str]) -> str:
    return _resolve_section_content_mode(section, modes)


def compose_section_body(section: dict, generated_body: str, mode: str) -> str:
    return _compose_section_body(section, generated_body, mode)


def resolve_ordered_style_sections(
    style_guide: StyleGuideConfig,
    metadata: dict,
) -> tuple[list[dict], set[str], dict[str, str], bool]:
    return _resolve_ordered_style_sections(style_guide, metadata)


def append_scanner_report_section_if_enabled(
    parts: list[str],
    style_guide: StyleGuideConfig,
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
        role_name,
        description,
        variables,
        requirements,
        default_filters,
        metadata,
    )
