"""README composition and template rendering helpers for the fsrc lane."""

from __future__ import annotations

from pathlib import Path
from typing import Any, NamedTuple

from prism.scanner_plugins.interfaces import ReadmeRendererPlugin
from prism.scanner_readme.guide import render_guide_section_body
from prism.scanner_plugins.defaults import resolve_readme_renderer_plugin
from prism.scanner_readme.rendering_seams import build_render_jinja_environment
from prism.scanner_readme.style import format_heading


DEFAULT_MERGE_GENERATED_CONTENT_LABEL = "Generated content"


def _get_readme_renderer_plugin(metadata: dict[str, Any]) -> ReadmeRendererPlugin:
    platform_key = str(metadata.get("platform_key") or "ansible")
    return resolve_readme_renderer_plugin(platform_key)


def _generated_merge_markers(
    section_id: str,
    prefixes: tuple[str, ...] | None = None,
) -> list[tuple[str, str]]:
    """Return supported hidden marker pairs for generated merge payloads."""
    active_prefixes = prefixes or ("prism",)
    return [
        (
            f"<!-- {prefix}:generated:start:{section_id} -->",
            f"<!-- {prefix}:generated:end:{section_id} -->",
        )
        for prefix in active_prefixes
    ]


def _strip_prior_generated_merge_block(
    section: dict[str, Any],
    guide_body: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Remove previously generated merge payload for a section, if present."""
    section_id = str(section.get("id") or "")
    cleaned = guide_body
    prefixes = None
    if metadata:
        prefixes = _get_readme_renderer_plugin(metadata).legacy_merge_marker_prefixes()
    for start_marker, end_marker in _generated_merge_markers(section_id, prefixes):
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


def _resolve_section_content_mode(
    section: dict[str, Any],
    modes: dict[str, str],
    plugin: ReadmeRendererPlugin | None = None,
) -> str:
    """Resolve content handling mode for a style section."""
    section_id = str(section.get("id") or "")
    guide_body = str(section.get("body") or "").strip()
    configured = str(modes.get(section_id) or "").strip().lower()
    if configured in {"generate", "replace", "merge"}:
        return configured
    merge_eligible_ids = (
        plugin.merge_eligible_section_ids()
        if plugin is not None
        else frozenset(
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
    )
    if section_id == "requirements" or (
        guide_body and section_id in merge_eligible_ids
    ):
        return "merge"
    return "generate"


def _resolve_merge_generated_content_label(
    section: dict[str, Any],
    metadata: dict[str, Any],
) -> str:
    """Resolve merge generated-content label from section/style metadata."""
    section_label = str(section.get("merge_generated_content_label") or "").strip()
    if section_label:
        return section_label

    style_guide = metadata.get("style_guide") or {}
    style_label = str(style_guide.get("merge_generated_content_label") or "").strip()
    if style_label:
        return style_label

    metadata_label = str(metadata.get("merge_generated_content_label") or "").strip()
    if metadata_label:
        return metadata_label

    return DEFAULT_MERGE_GENERATED_CONTENT_LABEL


def _compose_section_body(
    section: dict[str, Any],
    generated_body: str,
    mode: str,
    metadata: dict[str, Any],
) -> str:
    """Compose final section body according to configured mode."""
    guide_body = str(section.get("body") or "").strip()
    if mode == "replace":
        return guide_body or generated_body
    if mode == "merge":
        merge_label = _resolve_merge_generated_content_label(section, metadata)
        if guide_body and generated_body:
            return f"{guide_body}\n\n{merge_label}:\n{generated_body}"
        return guide_body or generated_body
    return generated_body


def _default_ordered_style_sections(plugin: Any) -> list[dict[str, Any]]:
    """Return default style sections sourced from the platform plugin."""
    return [
        {"id": section_id, "title": title}
        for section_id, title in plugin.default_section_specs()
    ]


class OrderedStyleSections(NamedTuple):
    sections: list[dict[str, Any]]
    enabled_sections: set[str]
    content_modes: dict[str, str]
    skeleton: bool


def _resolve_ordered_style_sections(
    style_guide: dict[str, Any],
    metadata: dict[str, Any],
) -> OrderedStyleSections:
    """Resolve ordered style-guide sections after scanner/readme config filters."""
    ordered_sections = [dict(section) for section in style_guide.get("sections") or []]
    enabled_sections = set(metadata.get("enabled_sections") or [])
    section_content_modes = metadata.get("section_content_modes") or {}
    keep_unknown_style_sections = bool(metadata.get("keep_unknown_style_sections"))
    plugin = _get_readme_renderer_plugin(metadata)

    if not ordered_sections:
        ordered_sections = _default_ordered_style_sections(plugin)

    if not keep_unknown_style_sections:
        ordered_sections = [
            section for section in ordered_sections if section.get("id") != "unknown"
        ]

    if enabled_sections:
        ordered_sections = [
            section
            for section in ordered_sections
            if section.get("id") in enabled_sections
        ]

    return OrderedStyleSections(
        ordered_sections,
        enabled_sections,
        section_content_modes,
        bool(metadata.get("style_guide_skeleton")),
    )


def append_scanner_report_section_if_enabled(
    parts: list[str],
    style_guide: dict[str, Any],
    style_guide_skeleton: bool,
    scanner_report_relpath: str | None,
    include_scanner_report_link: bool,
    enabled_sections: set[str],
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append scanner report section when concise/section settings allow it."""
    if (
        style_guide_skeleton
        or not scanner_report_relpath
        or not include_scanner_report_link
        or (enabled_sections and "scanner_report" not in enabled_sections)
    ):
        return

    plugin = _get_readme_renderer_plugin(metadata or {})
    parts.append(
        format_heading(
            "Scanner report",
            int(style_guide.get("section_level") or 2),
            style_guide.get("section_style", "setext"),
        )
    )
    parts.append("")
    parts.append(plugin.scanner_report_blurb(scanner_report_relpath))
    parts.append("")


def _render_readme_with_style_guide(
    role_name: str,
    description: str,
    variables: dict[str, Any],
    requirements: list[Any],
    default_filters: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> str:
    """Render markdown following the structure of a guide README."""
    style_guide = metadata.get("style_guide") or {}
    (
        ordered_sections,
        enabled_sections,
        section_content_modes,
        style_guide_skeleton,
    ) = _resolve_ordered_style_sections(style_guide, metadata)
    plugin = _get_readme_renderer_plugin(metadata)

    rendered_title = role_name
    if style_guide.get("title_text"):
        rendered_title = role_name

    parts = [
        format_heading(rendered_title, 1, style_guide.get("title_style", "setext")),
        "",
        description,
        "",
    ]

    for section in ordered_sections:
        heading_level = int(
            section.get("level") or style_guide.get("section_level") or 2
        )
        parts.append(
            format_heading(
                str(section.get("title") or ""),
                heading_level,
                style_guide.get("section_style", "setext"),
            )
        )
        parts.append("")

        if style_guide_skeleton:
            continue

        body = render_guide_section_body(
            str(section.get("id") or ""),
            role_name,
            description,
            variables,
            requirements,
            default_filters,
            metadata,
        ).strip()
        mode = _resolve_section_content_mode(
            section,
            section_content_modes,
            plugin,
        )
        body = _compose_section_body(section, body, mode, metadata)
        if not body:
            continue
        parts.append(body)
        parts.append("")

    append_scanner_report_section_if_enabled(
        parts=parts,
        style_guide=style_guide,
        style_guide_skeleton=style_guide_skeleton,
        scanner_report_relpath=metadata.get("scanner_report_relpath"),
        include_scanner_report_link=bool(
            metadata.get("include_scanner_report_link", True)
        ),
        enabled_sections=enabled_sections,
        metadata=metadata,
    )
    return "\n".join(parts).strip() + "\n"


def render_readme(
    output: str,
    role_name: str,
    description: str,
    variables: dict[str, Any],
    requirements: list[Any],
    default_filters: list[dict[str, Any]],
    template: str | None = None,
    metadata: dict[str, Any] | None = None,
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

    if template:
        tpl_file = Path(template)
    else:
        plugin = _get_readme_renderer_plugin(metadata)
        plugin_path = plugin.default_template_path()
        tpl_file = (
            plugin_path
            if plugin_path is not None
            else Path(__file__).resolve().parent.parent / "templates" / "README.md.j2"
        )
    env = build_render_jinja_environment(
        template_dir=tpl_file.parent,
        metadata=metadata,
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
    return str(rendered)
