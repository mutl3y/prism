"""README composition and template rendering helpers extracted from scanner."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import jinja2

from .guide import _render_guide_section_body
from .style import format_heading
from ..scanner_submodules.scan_context import StyleGuideConfig

DEFAULT_SECTION_SPECS = [
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
]

SCANNER_STATS_SECTION_IDS = {
    "task_summary",
    "role_contents",
    "features",
    "comparison",
    "default_filters",
}


def _generated_merge_markers(section_id: str) -> list[tuple[str, str]]:
    """Return supported hidden marker pairs for generated merge payloads."""
    return [
        (
            f"<!-- prism:generated:start:{section_id} -->",
            f"<!-- prism:generated:end:{section_id} -->",
        ),
        (
            f"<!-- ansible-role-doc:generated:start:{section_id} -->",
            f"<!-- ansible-role-doc:generated:end:{section_id} -->",
        ),
    ]


def _strip_prior_generated_merge_block(section: dict, guide_body: str) -> str:
    """Remove previously generated merge payload for a section, if present."""
    section_id = str(section.get("id") or "")
    cleaned = guide_body
    for start_marker, end_marker in _generated_merge_markers(section_id):
        start_idx = cleaned.find(start_marker)
        end_idx = cleaned.find(end_marker)
        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            prefix = cleaned[:start_idx].rstrip()
            suffix = cleaned[end_idx + len(end_marker) :].lstrip()
            if prefix and suffix:
                cleaned = f"{prefix}\n\n{suffix}"
            else:
                cleaned = prefix or suffix

    legacy_labels = ["\n\nGenerated content:\n"]
    if section_id == "requirements":
        legacy_labels.append("\n\nDetected requirements from scanner:\n")
    for label in legacy_labels:
        if label in cleaned:
            cleaned = cleaned.split(label, 1)[0].rstrip()

    return cleaned


def _resolve_section_content_mode(section: dict, modes: dict[str, str]) -> str:
    """Resolve content handling mode for a style section."""
    section_id = str(section.get("id") or "")
    guide_body = str(section.get("body") or "").strip()
    configured = str(modes.get(section_id) or "").strip().lower()
    if configured in {"generate", "replace", "merge"}:
        return configured
    if section_id == "requirements":
        return "merge"
    if guide_body and section_id in {
        "purpose",
        "task_summary",
        "local_testing",
        "handlers",
        "template_overrides",
        "faq_pitfalls",
        "contributing",
    }:
        return "merge"
    return "generate"


def _merge_section_body(
    section: dict,
    generated_body: str,
    guide_body: str,
) -> str:
    """Merge scanner-generated and style-guide content for a section."""
    cleaned_guide_body = _strip_prior_generated_merge_block(section, guide_body)
    if not cleaned_guide_body:
        return generated_body
    if not generated_body:
        return cleaned_guide_body
    if generated_body in cleaned_guide_body:
        return cleaned_guide_body
    section_id = str(section.get("id") or "")
    start_marker, end_marker = _generated_merge_markers(section_id)[0]
    if section_id == "requirements":
        return (
            f"{cleaned_guide_body}\n\n"
            "Detected requirements from scanner:\n"
            f"{start_marker}\n"
            f"{generated_body}\n"
            f"{end_marker}"
        )
    return (
        f"{cleaned_guide_body}\n\n"
        "Generated content:\n"
        f"{start_marker}\n"
        f"{generated_body}\n"
        f"{end_marker}"
    )


def _compose_section_body(section: dict, generated_body: str, mode: str) -> str:
    """Compose final section body according to configured mode."""
    guide_body = str(section.get("body") or "").strip()
    if mode == "replace":
        return guide_body or generated_body
    if mode == "merge":
        return _merge_section_body(section, generated_body, guide_body)
    return generated_body


def _default_ordered_style_sections() -> list[dict]:
    """Return default style sections when no style guide sections are supplied."""
    return [
        {"id": section_id, "title": title}
        for section_id, title in DEFAULT_SECTION_SPECS
    ]


def _apply_section_title_overrides(
    ordered_sections: list[dict],
    section_title_overrides: dict[str, str],
) -> list[dict]:
    """Apply metadata-driven section title overrides to a copied section list."""
    overridden_sections = [dict(section) for section in ordered_sections]
    for section in overridden_sections:
        section_id = section.get("id")
        override_title = (
            section_title_overrides.get(str(section_id))
            if section_id is not None
            else None
        )
        if override_title:
            section["title"] = override_title
    return overridden_sections


def _filter_ordered_sections_by_metadata(
    ordered_sections: list[dict],
    enabled_sections: set[str],
    keep_unknown_style_sections: bool,
) -> list[dict]:
    """Filter sections by unknown/enabled metadata controls."""
    filtered_sections = ordered_sections
    if not keep_unknown_style_sections:
        filtered_sections = [
            section for section in filtered_sections if section.get("id") != "unknown"
        ]
    if enabled_sections:
        filtered_sections = [
            section
            for section in filtered_sections
            if section.get("id") in enabled_sections
        ]
    return filtered_sections


def _filter_concise_readme_sections(ordered_sections: list[dict]) -> list[dict]:
    """Drop verbose sections and duplicate variable detail rows for concise output."""
    concise_sections = [
        section
        for section in ordered_sections
        if section.get("id") not in SCANNER_STATS_SECTION_IDS
    ]
    section_ids = [section.get("id") for section in concise_sections]
    if "variable_summary" in section_ids and "role_variables" in section_ids:
        concise_sections = [
            section
            for section in concise_sections
            if section.get("id") != "role_variables"
        ]
    return concise_sections


def _resolve_ordered_style_sections(
    style_guide: StyleGuideConfig,
    metadata: dict,
) -> tuple[list[dict], set[str], dict[str, str], bool]:
    """Resolve ordered style-guide sections after scanner/readme config filters."""
    ordered_sections = [dict(section) for section in style_guide.get("sections") or []]
    enabled_sections = set(metadata.get("enabled_sections") or [])
    section_title_overrides = metadata.get("section_title_overrides") or {}
    keep_unknown_style_sections = bool(metadata.get("keep_unknown_style_sections"))

    if not ordered_sections:
        ordered_sections = _default_ordered_style_sections()

    ordered_sections = _apply_section_title_overrides(
        ordered_sections,
        section_title_overrides,
    )
    ordered_sections = _filter_ordered_sections_by_metadata(
        ordered_sections,
        enabled_sections,
        keep_unknown_style_sections,
    )

    if metadata.get("concise_readme"):
        ordered_sections = _filter_concise_readme_sections(ordered_sections)

    return (
        ordered_sections,
        enabled_sections,
        metadata.get("section_content_modes") or {},
        bool(metadata.get("style_guide_skeleton")),
    )


def _append_style_guide_section_heading(
    parts: list[str],
    section: dict,
    style_guide: StyleGuideConfig,
) -> None:
    """Append a formatted heading for a style-guide section."""
    heading_level = int(section.get("level") or style_guide.get("section_level") or 2)
    parts.append(
        format_heading(
            section["title"],
            heading_level,
            style_guide.get("section_style", "setext"),
        )
    )
    parts.append("")


def _resolve_rendered_style_guide_section_body(
    section: dict,
    section_content_modes: dict[str, str],
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
) -> str:
    """Return rendered section body after merge/unknown handling."""
    body = _render_guide_section_body(
        section["id"],
        role_name,
        description,
        variables,
        requirements,
        default_filters,
        metadata,
    ).strip()
    mode = _resolve_section_content_mode(section, section_content_modes)
    body = _compose_section_body(section, body, mode)
    if section["id"] != "unknown":
        return body
    unknown_guide_body = str(section.get("body") or "").strip()
    if unknown_guide_body:
        return unknown_guide_body
    return "Style section retained from guide; scanner does not map this section yet."


def _render_style_guide_sections_into_parts(
    parts: list[str],
    ordered_sections: list[dict],
    style_guide: StyleGuideConfig,
    style_guide_skeleton: bool,
    section_content_modes: dict[str, str],
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
) -> None:
    """Append rendered style-guide sections into the markdown parts list."""
    for section in ordered_sections:
        _append_style_guide_section_heading(parts, section, style_guide)

        if style_guide_skeleton:
            continue

        body = _resolve_rendered_style_guide_section_body(
            section,
            section_content_modes,
            role_name,
            description,
            variables,
            requirements,
            default_filters,
            metadata,
        )
        if not body:
            continue
        parts.append(body)
        parts.append("")


def _append_scanner_report_section_if_enabled(
    parts: list[str],
    style_guide: StyleGuideConfig,
    style_guide_skeleton: bool,
    scanner_report_relpath: str | None,
    include_scanner_report_link: bool,
    enabled_sections: set[str],
) -> None:
    """Append scanner report section when concise/section settings allow it."""
    if (
        style_guide_skeleton
        or not scanner_report_relpath
        or not include_scanner_report_link
        or (enabled_sections and "scanner_report" not in enabled_sections)
    ):
        return
    parts.append(
        format_heading(
            "Scanner report",
            int(style_guide.get("section_level") or 2),
            style_guide.get("section_style", "setext"),
        )
    )
    parts.append("")
    parts.append(
        f"Detailed scanner output is available in `{scanner_report_relpath}`. It includes task/module statistics, role-content inventory, baseline comparison details, and undocumented `default()` findings."
    )
    parts.append("")


def _render_readme_with_style_guide(
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    metadata: dict,
) -> str:
    """Render markdown following the structure of a guide README."""
    style_guide = cast(StyleGuideConfig, metadata.get("style_guide") or {})
    (
        ordered_sections,
        enabled_sections,
        section_content_modes,
        style_guide_skeleton,
    ) = _resolve_ordered_style_sections(style_guide, metadata)

    rendered_title = role_name
    if style_guide.get("title_text"):
        rendered_title = role_name

    parts = [
        format_heading(rendered_title, 1, style_guide.get("title_style", "setext")),
        "",
        description,
        "",
    ]
    _render_style_guide_sections_into_parts(
        parts=parts,
        ordered_sections=ordered_sections,
        style_guide=style_guide,
        style_guide_skeleton=style_guide_skeleton,
        section_content_modes=section_content_modes,
        role_name=role_name,
        description=description,
        variables=variables,
        requirements=requirements,
        default_filters=default_filters,
        metadata=metadata,
    )

    _append_scanner_report_section_if_enabled(
        parts=parts,
        style_guide=style_guide,
        style_guide_skeleton=style_guide_skeleton,
        scanner_report_relpath=metadata.get("scanner_report_relpath"),
        include_scanner_report_link=bool(
            metadata.get("include_scanner_report_link", True)
        ),
        enabled_sections=enabled_sections,
    )
    return "\n".join(parts).strip() + "\n"


def render_readme(
    output: str,
    role_name: str,
    description: str,
    variables: dict,
    requirements: list,
    default_filters: list,
    template: str | None = None,
    metadata: dict | None = None,
    write: bool = True,
) -> str:
    """Render README markdown using either a style guide or Jinja template."""
    metadata = metadata or {}
    if metadata.get("style_guide"):
        rendered = _render_readme_with_style_guide(
            role_name,
            description,
            variables,
            requirements,
            default_filters,
            metadata,
        )
        if write:
            Path(output).write_text(rendered, encoding="utf-8")
            return str(Path(output).resolve())
        return rendered

    tpl_file = (
        Path(template)
        if template
        else Path(__file__).resolve().parent.parent / "templates" / "README.md.j2"
    )
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(tpl_file.parent)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template_obj = env.get_template(tpl_file.name)
    rendered = template_obj.render(
        role_name=role_name,
        description=description,
        variables=variables,
        requirements=requirements,
        default_filters=default_filters,
        metadata=metadata,
    )
    if write:
        Path(output).write_text(rendered, encoding="utf-8")
        return str(Path(output).resolve())
    return rendered
